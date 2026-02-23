"""
Comprehensive tests for the Deterministic Organization Generator.

Covers:
  - AddDependencyEvent in isolation
  - Duplicate dependency (no dedup in kernel)
  - Critical cycle rejection (INV-6)
  - Generator determinism (same seed → same hash)
  - Different seeds → different hashes
  - All capacity profiles
  - Fragility mode
  - Differentiation pressure
  - Shock injection
  - Replay hash stability (two independent replays)
  - JSON export round-trip

Run:  py -3 test_generator.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from org_kernel.engine import OrgEngine
from org_kernel.events import (
    AddDependencyEvent,
    AddRoleEvent,
    InitializeConstantsEvent,
)
from org_kernel.invariants import InvariantViolationError
from org_kernel.hashing import canonical_hash

from generator import (
    DeterministicRNG,
    GeneratorInvariantError,
    TemplateSpec,
    compile_template,
    export_event_stream,
    verify_generated_template,
)


_pass = 0
_fail = 0


def _test(name, fn):
    global _pass, _fail
    try:
        fn()
        print(f"  [PASS] {name}")
        _pass += 1
    except Exception as exc:
        print(f"  [FAIL] {name}: {exc}")
        _fail += 1


# ---------------------------------------------------------------------------
# AddDependencyEvent Isolation
# ---------------------------------------------------------------------------

def test_add_dependency_basic():
    engine = OrgEngine()
    engine.initialize_state()
    engine.apply_event(InitializeConstantsEvent(
        timestamp="t1", sequence=1, logical_time=1, payload={}))
    engine.apply_event(AddRoleEvent(
        timestamp="t2", sequence=2, logical_time=2,
        payload={"id": "a", "name": "A", "purpose": "p",
                 "responsibilities": ["r1"],
                 "produced_outputs": ["out1"],
                 "required_inputs": ["out1"]}))
    engine.apply_event(AddRoleEvent(
        timestamp="t3", sequence=3, logical_time=3,
        payload={"id": "b", "name": "B", "purpose": "p",
                 "responsibilities": ["r2"],
                 "produced_outputs": ["out2"],
                 "required_inputs": ["out2"]}))
    engine.apply_event(AddDependencyEvent(
        timestamp="t4", sequence=4, logical_time=4,
        payload={"from_role_id": "a", "to_role_id": "b"}))
    assert len(engine.state.dependencies) == 1
    assert engine.state.dependencies[0].from_role_id == "a"
    assert engine.state.dependencies[0].to_role_id == "b"


def test_add_dependency_duplicate():
    """Duplicate edges are allowed by the kernel (no dedup)."""
    engine = OrgEngine()
    engine.initialize_state()
    engine.apply_event(InitializeConstantsEvent(
        timestamp="t1", sequence=1, logical_time=1, payload={}))
    engine.apply_event(AddRoleEvent(
        timestamp="t2", sequence=2, logical_time=2,
        payload={"id": "a", "name": "A", "purpose": "p",
                 "responsibilities": ["r1"],
                 "produced_outputs": ["o1"],
                 "required_inputs": ["o1"]}))
    engine.apply_event(AddRoleEvent(
        timestamp="t3", sequence=3, logical_time=3,
        payload={"id": "b", "name": "B", "purpose": "p",
                 "responsibilities": ["r2"],
                 "produced_outputs": ["o2"],
                 "required_inputs": ["o2"]}))
    engine.apply_event(AddDependencyEvent(
        timestamp="t4", sequence=4, logical_time=4,
        payload={"from_role_id": "a", "to_role_id": "b"}))
    engine.apply_event(AddDependencyEvent(
        timestamp="t5", sequence=5, logical_time=5,
        payload={"from_role_id": "a", "to_role_id": "b"}))
    assert len(engine.state.dependencies) == 2


def test_add_dependency_self_loop_rejected():
    engine = OrgEngine()
    engine.initialize_state()
    engine.apply_event(InitializeConstantsEvent(
        timestamp="t1", sequence=1, logical_time=1, payload={}))
    engine.apply_event(AddRoleEvent(
        timestamp="t2", sequence=2, logical_time=2,
        payload={"id": "a", "name": "A", "purpose": "p",
                 "responsibilities": ["r1"],
                 "produced_outputs": ["o1"],
                 "required_inputs": ["o1"]}))
    try:
        engine.apply_event(AddDependencyEvent(
            timestamp="t3", sequence=3, logical_time=3,
            payload={"from_role_id": "a", "to_role_id": "a"}))
        raise AssertionError("Expected ValueError for self-loop")
    except ValueError:
        pass  # expected


def test_critical_cycle_rejected():
    """A -> B (critical) + B -> A (critical) must trigger INV-6."""
    engine = OrgEngine()
    engine.initialize_state()
    engine.apply_event(InitializeConstantsEvent(
        timestamp="t1", sequence=1, logical_time=1, payload={}))
    engine.apply_event(AddRoleEvent(
        timestamp="t2", sequence=2, logical_time=2,
        payload={"id": "a", "name": "A", "purpose": "p",
                 "responsibilities": ["r1"],
                 "produced_outputs": ["o1"],
                 "required_inputs": ["o1"]}))
    engine.apply_event(AddRoleEvent(
        timestamp="t3", sequence=3, logical_time=3,
        payload={"id": "b", "name": "B", "purpose": "p",
                 "responsibilities": ["r2"],
                 "produced_outputs": ["o2"],
                 "required_inputs": ["o2"]}))
    engine.apply_event(AddDependencyEvent(
        timestamp="t4", sequence=4, logical_time=4,
        payload={"from_role_id": "a", "to_role_id": "b",
                 "critical": True}))
    try:
        engine.apply_event(AddDependencyEvent(
            timestamp="t5", sequence=5, logical_time=5,
            payload={"from_role_id": "b", "to_role_id": "a",
                     "critical": True}))
        raise AssertionError("Expected InvariantViolationError for critical cycle")
    except InvariantViolationError as exc:
        assert "critical_cycle" in str(exc)


# ---------------------------------------------------------------------------
# Generator Determinism
# ---------------------------------------------------------------------------

def _make_spec(
    role_count: int = 4,
    domain_count: int = 2,
    intra_density_target: int = 5000,
    inter_density_target: int = 2000,
    capacity_profile: str = "balanced",
    fragility_mode: bool = False,
    drift_mode: bool = False,
    shock_magnitude: int = 0,
    differentiation_pressure: int = 0,
) -> TemplateSpec:
    return TemplateSpec(
        role_count=role_count,
        domain_count=domain_count,
        intra_density_target=intra_density_target,
        inter_density_target=inter_density_target,
        capacity_profile=capacity_profile,
        fragility_mode=fragility_mode,
        drift_mode=drift_mode,
        shock_magnitude=shock_magnitude,
        differentiation_pressure=differentiation_pressure,
    )


def test_determinism_same_seed():
    spec = _make_spec()
    r1 = verify_generated_template(spec, seed=42)
    r2 = verify_generated_template(spec, seed=42)
    assert r1["final_state_hash"] == r2["final_state_hash"]


def test_different_seeds():
    spec = _make_spec()
    r1 = verify_generated_template(spec, seed=42)
    r2 = verify_generated_template(spec, seed=99)
    assert r1["final_state_hash"] != r2["final_state_hash"]


def test_replay_hash_stability():
    """Two independent engine.replay calls on the same events produce identical hash."""
    spec = _make_spec()
    events = compile_template(spec, seed=42)

    engine1 = OrgEngine()
    engine1.replay(events)
    h1 = canonical_hash(engine1.state)

    engine2 = OrgEngine()
    engine2.replay(events)
    h2 = canonical_hash(engine2.state)

    assert h1 == h2


# ---------------------------------------------------------------------------
# Capacity Profiles
# ---------------------------------------------------------------------------

def test_capacity_low():
    spec = _make_spec(capacity_profile="low")
    result = verify_generated_template(spec, seed=42)
    assert result["role_count"] == 4


def test_capacity_balanced():
    spec = _make_spec(capacity_profile="balanced")
    result = verify_generated_template(spec, seed=42)
    assert result["role_count"] == 4


def test_capacity_high():
    spec = _make_spec(capacity_profile="high")
    result = verify_generated_template(spec, seed=42)
    assert result["role_count"] == 4


# ---------------------------------------------------------------------------
# Fragility Mode
# ---------------------------------------------------------------------------

def test_fragility_mode():
    spec = _make_spec(role_count=6, domain_count=3, fragility_mode=True)
    result = verify_generated_template(spec, seed=42)
    assert result["role_count"] == 6


# ---------------------------------------------------------------------------
# Differentiation Pressure
# ---------------------------------------------------------------------------

def test_differentiation_pressure():
    spec = _make_spec(differentiation_pressure=3)
    result = verify_generated_template(spec, seed=42)
    assert result["role_count"] == 4


# ---------------------------------------------------------------------------
# Shock Injection
# ---------------------------------------------------------------------------

def test_shock_injection():
    spec = _make_spec(shock_magnitude=5)
    result = verify_generated_template(spec, seed=42)
    assert result["structural_debt"] > 0


def test_shock_high_magnitude():
    spec = _make_spec(shock_magnitude=10)
    result = verify_generated_template(spec, seed=42)
    assert result["structural_debt"] > 0


# ---------------------------------------------------------------------------
# JSON Export
# ---------------------------------------------------------------------------

def test_json_export():
    spec = _make_spec()
    events = compile_template(spec, seed=42)

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        path = f.name

    try:
        export_event_stream(events, path, spec, seed=42)
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)
        assert doc["metadata"]["seed"] == 42
        assert doc["metadata"]["template"]["role_count"] == 4
        assert len(doc["events"]) == len(events)
        assert doc["events"][0]["event_type"] == "initialize_constants"
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

def test_single_role():
    spec = _make_spec(role_count=1, domain_count=1,
                      intra_density_target=0, inter_density_target=0)
    result = verify_generated_template(spec, seed=42)
    assert result["role_count"] == 1


def test_rng_determinism():
    rng1 = DeterministicRNG(42)
    rng2 = DeterministicRNG(42)
    for _ in range(100):
        assert rng1.rand_int(0, 1000) == rng2.rand_int(0, 1000)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main():
    tests = [
        ("AddDependency: basic", test_add_dependency_basic),
        ("AddDependency: duplicate allowed", test_add_dependency_duplicate),
        ("AddDependency: self-loop rejected", test_add_dependency_self_loop_rejected),
        ("AddDependency: critical cycle rejected", test_critical_cycle_rejected),
        ("Determinism: same seed", test_determinism_same_seed),
        ("Determinism: different seeds", test_different_seeds),
        ("Determinism: replay hash stability", test_replay_hash_stability),
        ("Capacity: low", test_capacity_low),
        ("Capacity: balanced", test_capacity_balanced),
        ("Capacity: high", test_capacity_high),
        ("Fragility mode", test_fragility_mode),
        ("Differentiation pressure", test_differentiation_pressure),
        ("Shock: magnitude=5", test_shock_injection),
        ("Shock: magnitude=10", test_shock_high_magnitude),
        ("JSON export", test_json_export),
        ("Edge: single role", test_single_role),
        ("RNG determinism", test_rng_determinism),
    ]

    print(f"\nRunning {len(tests)} tests...\n")
    for name, fn in tests:
        _test(name, fn)

    print(f"\n{'='*60}")
    print(f"  {_pass} passed, {_fail} failed out of {_pass + _fail}")
    print(f"{'='*60}")

    if _fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
