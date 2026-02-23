"""
Organizational Kernel v1.1 — Deterministic Cross-Language Test Harness

Seeded random event generator (seed=42).
Generates valid event streams, replays through Python engine,
outputs structural_debt, role_count, active_roles, canonical_hash.

Run:  py -3 -m org_kernel.test_harness
"""

from __future__ import annotations

import json
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from org_kernel.engine import OrgEngine
from org_kernel.events import (
    InitializeConstantsEvent,
    AddRoleEvent,
    RemoveRoleEvent,
    ApplyConstraintChangeEvent,
)
from org_kernel.domain_types import SCALE
from org_kernel.hashing import canonical_hash


def generate_stream(seed: int, n_events: int) -> list:
    """Generate a deterministic stream of valid events."""
    rng = random.Random(seed)
    events = []
    seq = 0

    # Event 1: InitializeConstants (mandatory)
    seq += 1
    events.append(InitializeConstantsEvent(
        timestamp=f"t{seq}",
        sequence=seq,
        payload={},
    ))

    role_counter = 0
    existing_roles: list[str] = []

    for _ in range(n_events):
        seq += 1
        action = rng.choice(["add", "add", "add", "constraint"])

        if action == "add" or not existing_roles:
            role_counter += 1
            rid = f"role_{role_counter}"
            resps = [f"resp_{rng.randint(1, 20)}" for _ in range(rng.randint(1, 3))]
            resps = list(set(resps)) or ["default"]
            events.append(AddRoleEvent(
                timestamp=f"t{seq}",
                sequence=seq,
                payload={
                    "id": rid,
                    "name": f"Role {role_counter}",
                    "purpose": "auto-generated",
                    "responsibilities": resps,
                    "required_inputs": [],
                    "produced_outputs": [],
                },
            ))
            existing_roles.append(rid)
        elif action == "constraint":
            delta = rng.randint(-5000, 5000)
            field = rng.choice(["capital_delta", "talent_delta",
                                "time_delta", "political_cost_delta"])
            events.append(ApplyConstraintChangeEvent(
                timestamp=f"t{seq}",
                sequence=seq,
                payload={field: delta},
            ))

    return events


def run_harness(seed: int = 42, n_events: int = 20) -> None:
    """Generate and replay a deterministic event stream."""
    print(f"Generating stream: seed={seed}, n_events={n_events}")
    events = generate_stream(seed, n_events)

    engine = OrgEngine()
    engine.initialize_state()

    for evt in events:
        engine.apply_event(evt)

    state = engine.state
    h = canonical_hash(state)

    result = {
        "seed": seed,
        "n_events": n_events,
        "structural_debt": state.structural_debt,
        "role_count": len(state.roles),
        "active_roles": sum(1 for r in state.roles.values() if r.active),
        "canonical_hash": h,
    }

    print(json.dumps(result, indent=2))
    print(f"\n[OK] Harness complete. Hash: {h}")


def main() -> None:
    run_harness(seed=42, n_events=20)
    run_harness(seed=42, n_events=20)  # Must produce identical hash

    # Run with different seed
    run_harness(seed=99, n_events=15)


if __name__ == "__main__":
    main()
