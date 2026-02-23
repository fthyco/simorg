"""
Organizational Kernel v1.1 — Test Scenarios

5 executable scenarios + canonical hash verification:
  1. Initialize + Add role
  2. Suppressed differentiation (low capacity)
  3. Shock injection → deactivation + density-proportional debt
  4. Orphaned output → InvariantViolationError
  5. Dangling dep → InvariantViolationError

Run:  py -3 -m org_kernel.test_scenarios
"""

from __future__ import annotations

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from org_kernel.engine import OrgEngine
from org_kernel.events import (
    InitializeConstantsEvent,
    AddRoleEvent,
    DifferentiateRoleEvent,
    InjectShockEvent,
    RemoveRoleEvent,
)
from org_kernel.invariants import InvariantViolationError
from org_kernel.domain_types import DependencyEdge, TransitionResult, SCALE
from org_kernel.hashing import canonical_hash

_SEQ = 0

def _seq() -> int:
    global _SEQ
    _SEQ += 1
    return _SEQ

def _reset_seq() -> None:
    global _SEQ
    _SEQ = 0


def _header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def _dump(label: str, data: dict) -> None:
    print(f"\n--- {label} ---")
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _dump_result(label: str, result: TransitionResult) -> None:
    print(f"\n--- {label} ---")
    import dataclasses
    print(json.dumps(dataclasses.asdict(result), indent=2, ensure_ascii=False))


# ───────────────────────────────────────────────────────────────
# Scenario 1: Initialize + Add Role
# ───────────────────────────────────────────────────────────────

def scenario_1_add_role() -> bool:
    _header("Scenario 1 -- Initialize + Add Role")
    _reset_seq()
    engine = OrgEngine()
    engine.initialize_state()

    # First event: initialize_constants
    init_evt = InitializeConstantsEvent(
        timestamp="2026-01-01T00:00:00Z",
        sequence=_seq(),
        payload={},
    )
    engine.apply_event(init_evt)

    # Add consumer FIRST
    consumer_event = AddRoleEvent(
        timestamp="2026-01-01T00:00:00Z",
        sequence=_seq(),
        payload={
            "id": "mgmt",
            "name": "Management",
            "purpose": "Oversee operations",
            "responsibilities": ["review"],
            "required_inputs": ["daily_report"],
            "produced_outputs": [],
        },
    )
    engine.apply_event(consumer_event)

    # Add producer
    producer_event = AddRoleEvent(
        timestamp="2026-01-01T00:01:00Z",
        sequence=_seq(),
        payload={
            "id": "ops",
            "name": "Operations",
            "purpose": "Run daily operations",
            "responsibilities": ["logistics", "scheduling"],
            "required_inputs": ["strategy_plan"],
            "produced_outputs": ["daily_report"],
        },
    )
    state, result = engine.apply_event(producer_event)

    assert "ops" in state.roles, "Role 'ops' should exist"
    assert state.roles["ops"].active is True
    assert state.roles["ops"].responsibilities == sorted(["logistics", "scheduling"])

    h = canonical_hash(state)
    _dump("State", state.to_dict())
    print(f"\n  canonical_hash = {h}")
    _dump("Diagnostics", engine.get_diagnostics())
    print("\n[PASS] Scenario 1 PASSED")
    return True


# ───────────────────────────────────────────────────────────────
# Scenario 2: Suppressed Differentiation (low capacity)
# ───────────────────────────────────────────────────────────────

def scenario_2_suppressed_differentiation() -> bool:
    _header("Scenario 2 — Suppressed Differentiation")
    _reset_seq()
    engine = OrgEngine()
    # capacity = 20000 (2.0 * SCALE) < min_capacity 60000
    engine.initialize_state(capital=20000, talent=20000, time=20000, political_cost=20000)

    init_evt = InitializeConstantsEvent(
        timestamp="2026-01-01T00:00:00Z",
        sequence=_seq(),
        payload={},
    )
    engine.apply_event(init_evt)

    add_evt = AddRoleEvent(
        timestamp="2026-01-01T00:00:00Z",
        sequence=_seq(),
        payload={
            "id": "overloaded",
            "name": "Overloaded Role",
            "purpose": "Too many things",
            "responsibilities": ["a", "b", "c", "d"],
            "required_inputs": [],
            "produced_outputs": [],
        },
    )
    engine.apply_event(add_evt)

    diff_evt = DifferentiateRoleEvent(
        timestamp="2026-01-01T00:02:00Z",
        sequence=_seq(),
        payload={
            "role_id": "overloaded",
            "new_roles": [
                {"id": "sub_a", "name": "Sub A", "responsibilities": ["a", "b"]},
                {"id": "sub_b", "name": "Sub B", "responsibilities": ["c", "d"]},
            ],
        },
    )
    state, result = engine.apply_event(diff_evt)

    assert result.suppressed_differentiation is True, \
        "Differentiation should be suppressed"
    assert state.structural_debt >= 1, "Debt should have increased"
    assert "overloaded" in state.roles, "Original role should still exist"

    h = canonical_hash(state)
    _dump("State", state.to_dict())
    _dump_result("Transition Result", result)
    print(f"\n  canonical_hash = {h}")
    print("\n[PASS] Scenario 2 PASSED")
    return True


# ───────────────────────────────────────────────────────────────
# Scenario 3: Shock → Deactivation + density-proportional debt
# ───────────────────────────────────────────────────────────────

def scenario_3_shock_deactivation() -> bool:
    _header("Scenario 3 — Shock Deactivation")
    _reset_seq()
    engine = OrgEngine()
    engine.initialize_state()

    init_evt = InitializeConstantsEvent(
        timestamp="t0",
        sequence=_seq(),
        payload={},
    )
    engine.apply_event(init_evt)

    r1_evt = AddRoleEvent(timestamp="t0", sequence=_seq(), payload={
        "id": "r1", "name": "Role 1", "purpose": "p",
        "responsibilities": ["x"],
        "required_inputs": [],
        "produced_outputs": [],
    })
    r2_evt = AddRoleEvent(timestamp="t1", sequence=_seq(), payload={
        "id": "r2", "name": "Role 2", "purpose": "p",
        "responsibilities": ["y"],
        "required_inputs": [],
        "produced_outputs": [],
    })
    engine.apply_event(r1_evt)
    engine.apply_event(r2_evt)

    # Add dependency edge
    engine.state.dependencies.append(
        DependencyEdge(from_role_id="r1", to_role_id="r2", critical=False)
    )

    debt_before = engine.state.structural_debt

    shock = InjectShockEvent(
        timestamp="t2",
        sequence=_seq(),
        payload={"target_role_id": "r1", "magnitude": 10},
    )
    state, result = engine.apply_event(shock)

    assert state.roles["r1"].active is False, \
        "r1 should be deactivated (magnitude 10 > 8)"
    assert state.structural_debt > debt_before, "Debt should have increased"
    assert result.deactivated is True

    h = canonical_hash(state)
    _dump("State", state.to_dict())
    _dump_result("Transition Result", result)
    print(f"\n  canonical_hash = {h}")
    print("\n[PASS] Scenario 3 PASSED")
    return True


# ───────────────────────────────────────────────────────────────
# Scenario 4: Orphaned output → InvariantViolationError
# ───────────────────────────────────────────────────────────────

def scenario_4_orphaned_output() -> bool:
    _header("Scenario 4 — Orphaned Output (Intentional Failure)")
    _reset_seq()
    engine = OrgEngine()
    engine.initialize_state()

    init_evt = InitializeConstantsEvent(
        timestamp="t0",
        sequence=_seq(),
        payload={},
    )
    engine.apply_event(init_evt)

    evt = AddRoleEvent(
        timestamp="t0",
        sequence=_seq(),
        payload={
            "id": "producer",
            "name": "Producer",
            "purpose": "Produces stuff",
            "responsibilities": ["produce"],
            "required_inputs": [],
            "produced_outputs": ["orphan_output"],
        },
    )

    try:
        engine.apply_event(evt)
        print("\n[FAIL] Scenario 4 FAILED -- expected InvariantViolationError")
        return False
    except InvariantViolationError as e:
        assert e.rule == "orphaned_output"
        print(f"\n  Caught expected error: {e}")
        print("\n[PASS] Scenario 4 PASSED")
        return True


# ───────────────────────────────────────────────────────────────
# Scenario 5: Dangling dependency → InvariantViolationError
# ───────────────────────────────────────────────────────────────

def scenario_5_dangling_dependency() -> bool:
    _header("Scenario 5 -- Dangling Dependency (Intentional Failure)")
    _reset_seq()
    engine = OrgEngine()
    engine.initialize_state()

    init_evt = InitializeConstantsEvent(
        timestamp="t0",
        sequence=_seq(),
        payload={},
    )
    engine.apply_event(init_evt)

    engine.apply_event(AddRoleEvent(timestamp="t0", sequence=_seq(), payload={
        "id": "alpha", "name": "Alpha", "purpose": "p",
        "responsibilities": ["work"],
        "required_inputs": [],
        "produced_outputs": [],
    }))
    engine.apply_event(AddRoleEvent(timestamp="t1", sequence=_seq(), payload={
        "id": "beta", "name": "Beta", "purpose": "p",
        "responsibilities": ["work"],
        "required_inputs": [],
        "produced_outputs": [],
    }))

    engine.apply_event(RemoveRoleEvent(
        timestamp="t2", sequence=_seq(), payload={"role_id": "beta"},
    ))

    # Manually inject a dangling dependency
    engine.state.dependencies.append(
        DependencyEdge(from_role_id="alpha", to_role_id="beta")
    )

    trigger_evt = AddRoleEvent(timestamp="t3", sequence=_seq(), payload={
        "id": "gamma", "name": "Gamma", "purpose": "p",
        "responsibilities": ["support"],
        "required_inputs": [],
        "produced_outputs": [],
    })

    try:
        engine.apply_event(trigger_evt)
        print("\n[FAIL] Scenario 5 FAILED -- expected InvariantViolationError")
        return False
    except InvariantViolationError as e:
        print(f"\n  Caught expected error: {e}")
        print("\n[PASS] Scenario 5 PASSED")
        return True


# ───────────────────────────────────────────────────────────────
# Runner
# ───────────────────────────────────────────────────────────────

def main() -> None:
    results = []
    for fn in [
        scenario_1_add_role,
        scenario_2_suppressed_differentiation,
        scenario_3_shock_deactivation,
        scenario_4_orphaned_output,
        scenario_5_dangling_dependency,
    ]:
        try:
            results.append(fn())
        except Exception as e:
            print(f"\n[ERROR] UNEXPECTED ERROR in {fn.__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    print(f"\n{'='*60}")
    passed = sum(results)
    total = len(results)
    print(f"  RESULTS: {passed}/{total} scenarios passed")
    print(f"{'='*60}")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
