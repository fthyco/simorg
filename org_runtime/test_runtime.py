# file: org_runtime/test_runtime.py
"""
Organizational Runtime v2 -- Integration Test

Scenario:
  Phase 1: Apply 16 events (init constants + add roles, constraint changes, shock)
  Phase 2: Verify events persisted, snapshots created at interval
  Phase 3: Restart session (new engine instance), replay from DB
  Phase 4: Compare state equality
  Phase 5: Verify snapshot consistency
  Phase 6: Drift analysis (seq 6 vs seq 16)
  Phase 7: Idempotency (duplicate event_uuid → single insert)
  Phase 8: Hash validation (stream_metadata matches replay hash)
  Phase 9: Observability (get_metrics returns valid data)
  Phase 10: Determinism verification

Exit 0 on success, 1 on failure.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from org_kernel.engine import OrgEngine
from org_kernel.events import (
    AddRoleEvent,
    ApplyConstraintChangeEvent,
    InitializeConstantsEvent,
    InjectShockEvent,
    RemoveRoleEvent,
)
from org_kernel.domain_types import DependencyEdge
from org_kernel.hashing import canonical_hash

from org_runtime.event_repository import EventRepository
from org_runtime.snapshot_repository import SnapshotRepository
from org_runtime.session import SimulationSession, DeterminismError
from org_runtime.drift import compare_states


def _header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def _dump(label: str, data: dict) -> None:
    print(f"\n--- {label} ---")
    print(json.dumps(data, indent=2, ensure_ascii=False))


def build_events() -> list:
    """Build a sequence of 16 deterministic events."""
    events = []

    # Event 1: Initialize constants (MUST be first)
    events.append(InitializeConstantsEvent(
        timestamp="2026-01-01T00:00:00Z",
        payload={},
    ))

    # Events 2-6: Add 5 roles (no orphaned outputs — use required_inputs only)
    for i in range(1, 6):
        events.append(AddRoleEvent(
            timestamp=f"2026-01-01T00:{i:02d}:00Z",
            payload={
                "id": f"role_{i}",
                "name": f"Role {i}",
                "purpose": f"Purpose of role {i}",
                "responsibilities": [f"resp_{i}_a", f"resp_{i}_b"],
                "required_inputs": [],
                "produced_outputs": [],
            },
        ))

    # Events 6-8: Constraint changes
    events.append(ApplyConstraintChangeEvent(
        timestamp="2026-01-01T00:06:00Z",
        payload={"capital_delta": -1.0, "talent_delta": 0.5},
    ))
    events.append(ApplyConstraintChangeEvent(
        timestamp="2026-01-01T00:07:00Z",
        payload={"time_delta": -2.0, "political_cost_delta": 1.0},
    ))
    events.append(ApplyConstraintChangeEvent(
        timestamp="2026-01-01T00:08:00Z",
        payload={"capital_delta": 1.5, "talent_delta": -0.5},
    ))

    # Events 9-10: Add 2 more roles
    for i in range(6, 8):
        events.append(AddRoleEvent(
            timestamp=f"2026-01-01T00:{i+3:02d}:00Z",
            payload={
                "id": f"role_{i}",
                "name": f"Role {i}",
                "purpose": f"Purpose of role {i}",
                "responsibilities": [f"resp_{i}_a"],
                "required_inputs": [],
                "produced_outputs": [],
            },
        ))

    # Event 11: Inject shock on role_1 (magnitude 5, below deactivation threshold)
    events.append(InjectShockEvent(
        timestamp="2026-01-01T00:11:00Z",
        payload={"target_role_id": "role_1", "magnitude": 5},
    ))

    # Event 12: Another constraint change
    events.append(ApplyConstraintChangeEvent(
        timestamp="2026-01-01T00:12:00Z",
        payload={"talent_delta": 2.0},
    ))

    # Event 13: Add role_8
    events.append(AddRoleEvent(
        timestamp="2026-01-01T00:13:00Z",
        payload={
            "id": "role_8",
            "name": "Role 8",
            "purpose": "Late addition",
            "responsibilities": ["resp_8_a", "resp_8_b", "resp_8_c"],
            "required_inputs": [],
            "produced_outputs": [],
        },
    ))

    # Event 14: Inject strong shock on role_2 (magnitude 10, deactivates)
    events.append(InjectShockEvent(
        timestamp="2026-01-01T00:14:00Z",
        payload={"target_role_id": "role_2", "magnitude": 10},
    ))

    # Event 15: Remove role_3
    events.append(RemoveRoleEvent(
        timestamp="2026-01-01T00:15:00Z",
        payload={"role_id": "role_3"},
    ))

    return events


def main() -> None:
    # Use a temp file for the DB
    db_fd, db_path = tempfile.mkstemp(suffix=".db", prefix="org_runtime_test_")
    os.close(db_fd)

    try:
        _run_test(db_path)
    finally:
        # Clean up
        try:
            os.unlink(db_path)
        except OSError:
            pass


def _run_test(db_path: str) -> None:
    event_repo = EventRepository(db_path)
    snapshot_repo = SnapshotRepository(db_path)

    # ================================================================
    # PHASE 1: Apply 16 events
    # ================================================================
    _header("Phase 1 -- Apply 16 Events")

    engine1 = OrgEngine()
    session1 = SimulationSession(
        project_id="demo",
        engine=engine1,
        event_repo=event_repo,
        snapshot_repo=snapshot_repo,
        snapshot_interval=5,
    )
    session1.initialize()

    events = build_events()
    for i, evt in enumerate(events, 1):
        state_dict, result = session1.apply_event(evt)
        print(f"  Event {i:2d} [{evt.event_type}] applied | "
              f"seq={session1.current_sequence}")

    state_after_16 = session1.get_state()
    diag1 = session1.get_diagnostics()

    _dump("State after 16 events", state_after_16)
    _dump("Diagnostics", diag1)

    # ================================================================
    # PHASE 2: Verify persistence
    # ================================================================
    _header("Phase 2 -- Verify Persistence")

    last_seq = event_repo.get_last_sequence("demo")
    assert last_seq == 16, f"Expected 16 events, got {last_seq}"
    print(f"  Events persisted: {last_seq}")

    loaded_events = event_repo.load_events("demo")
    assert len(loaded_events) == 16, f"Expected 16 loaded events, got {len(loaded_events)}"
    print(f"  Events loaded:    {len(loaded_events)}")

    # Check snapshots exist at intervals (5, 10, 15)
    for seq in [5, 10, 15]:
        snap = snapshot_repo.load_snapshot_at("demo", seq)
        status = "EXISTS" if snap is not None else "MISSING"
        print(f"  Snapshot at seq {seq}: {status}")
        assert snap is not None, f"Snapshot at seq {seq} should exist"

    print("\n  [PASS] Persistence verified")

    # ================================================================
    # PHASE 3: Restart session (new engine), replay from DB
    # ================================================================
    _header("Phase 3 -- Replay from DB (new engine)")

    engine2 = OrgEngine()
    session2 = SimulationSession(
        project_id="demo",
        engine=engine2,
        event_repo=event_repo,
        snapshot_repo=snapshot_repo,
        snapshot_interval=5,
    )
    session2.initialize()  # Replays all events from DB

    state_replayed = session2.get_state()

    # ================================================================
    # PHASE 4: Compare state equality
    # ================================================================
    _header("Phase 4 -- State Equality Check")

    if state_after_16 == state_replayed:
        print("  State after apply == State after replay")
        print("\n  [PASS] Deterministic replay verified")
    else:
        print("  [FAIL] States differ!")
        drift = compare_states(state_after_16, state_replayed)
        _dump("Unexpected drift", drift)
        sys.exit(1)

    # ================================================================
    # PHASE 5: Snapshot consistency verification
    # ================================================================
    _header("Phase 5 -- Snapshot Consistency Verification")

    consistent = session2.verify_snapshot_consistency()
    if consistent:
        print("  All snapshots match replay results")
        print("\n  [PASS] Snapshot consistency verified")
    else:
        print("  [FAIL] Snapshot inconsistency detected")
        sys.exit(1)

    # ================================================================
    # PHASE 6: Drift analysis (event 5 vs event 15)
    # ================================================================
    _header("Phase 6 -- Drift Analysis (seq 6 vs seq 16)")

    state_at_6 = session2.replay_to_sequence(6)
    state_at_16 = session2.get_state()

    drift = compare_states(state_at_6, state_at_16)
    _dump("Drift (seq 6 -> seq 16)", drift)

    # Verify drift makes sense
    assert drift["role_count_delta"] == len(drift["added_roles"]) - len(drift["removed_roles"]), \
        "role_count_delta should match added - removed"
    print("\n  [PASS] Drift analysis verified")

    # ================================================================
    # PHASE 7: Idempotency (event_uuid dedup)
    # ================================================================
    _header("Phase 7 -- Idempotency (event_uuid)")

    # Use a fresh project for isolation
    idem_project = "idempotency_test"
    engine_idem = OrgEngine()
    session_idem = SimulationSession(
        project_id=idem_project,
        engine=engine_idem,
        event_repo=event_repo,
        snapshot_repo=snapshot_repo,
        snapshot_interval=100,
    )
    session_idem.initialize()

    # Apply init event
    session_idem.apply_event(
        InitializeConstantsEvent(timestamp="t1", payload={}),
    )

    # Apply a role event with a UUID
    test_uuid = "test-uuid-abc-123"
    role_event = AddRoleEvent(
        timestamp="t2",
        payload={
            "id": "idem_role",
            "name": "Idempotent Role",
            "purpose": "Testing idempotency",
            "responsibilities": ["resp_a"],
        },
    )
    session_idem.apply_event(role_event, event_uuid=test_uuid)
    seq_after_first = event_repo.get_last_sequence(idem_project)

    # Attempt to insert same UUID again (should be deduped at repo level)
    dup_seq = event_repo.append_event(
        idem_project,
        AddRoleEvent(
            timestamp="t_dup",
            sequence=999,
            payload={
                "id": "idem_role_dup",
                "name": "Dup",
                "purpose": "Should not insert",
                "responsibilities": ["r"],
            },
        ),
        event_uuid=test_uuid,
    )

    seq_after_dup = event_repo.get_last_sequence(idem_project)
    assert seq_after_first == seq_after_dup, (
        f"Idempotency failed: seq went from {seq_after_first} to {seq_after_dup}"
    )
    print(f"  First insert seq:  {seq_after_first}")
    print(f"  Dup attempt seq:   {dup_seq} (returned existing)")
    print(f"  DB last seq:       {seq_after_dup} (unchanged)")

    # Verify by UUID lookup
    loaded = event_repo.load_event_by_uuid(idem_project, test_uuid)
    assert loaded is not None, "Should find event by UUID"
    assert loaded.event_type == "add_role"
    print(f"  UUID lookup:       found event_type={loaded.event_type!r}")

    print("\n  [PASS] Idempotency verified")

    # ================================================================
    # PHASE 8: Hash validation (stream_metadata)
    # ================================================================
    _header("Phase 8 -- Hash Validation (stream_metadata)")

    # Check metadata was written for main project
    metadata = event_repo.load_metadata("demo")
    assert metadata is not None, "Metadata should exist for 'demo'"
    stored_seq, stored_hash = metadata
    print(f"  Stored metadata: seq={stored_seq}, hash={stored_hash[:16]}...")

    # Compute hash independently
    engine_verify = OrgEngine()
    verify_events = event_repo.load_events("demo")
    engine_verify.replay(verify_events)
    computed_hash = canonical_hash(engine_verify.state)

    assert stored_hash == computed_hash, (
        f"Hash mismatch: stored={stored_hash}, computed={computed_hash}"
    )
    print(f"  Computed hash:   {computed_hash[:16]}...")
    print(f"  Match:           YES")

    print("\n  [PASS] Hash validation verified")

    # ================================================================
    # PHASE 9: Observability (get_metrics)
    # ================================================================
    _header("Phase 9 -- Observability (get_metrics)")

    metrics = session2.get_metrics()
    print(f"  replay_latency_ms:   {metrics.replay_latency_ms}")
    print(f"  event_count:         {metrics.event_count}")
    print(f"  structural_debt:     {metrics.structural_debt}")
    print(f"  structural_density:  {metrics.structural_density}")
    print(f"  active_role_count:   {metrics.active_role_count}")
    print(f"  last_state_hash:     {metrics.last_state_hash[:16]}...")
    print(f"  warnings:            {len(metrics.warnings)} warning(s)")

    assert metrics.event_count == 16
    assert metrics.replay_latency_ms >= 0
    assert metrics.structural_debt >= 0
    assert metrics.last_state_hash == computed_hash

    print("\n  [PASS] Observability verified")

    # ================================================================
    # PHASE 10: Determinism verification
    # ================================================================
    _header("Phase 10 -- Determinism Verification")

    deterministic = session2.verify_determinism()
    assert deterministic is True
    print("  verify_determinism() returned True")

    print("\n  [PASS] Determinism verification passed")

    # ================================================================
    # FINAL
    # ================================================================
    print(f"\n{'='*60}")
    print(f"  ALL 10 PHASES PASSED")
    print(f"{'='*60}")

    # Cleanup
    event_repo.close()
    snapshot_repo.close()

    sys.exit(0)


if __name__ == "__main__":
    main()
