"""Dump deterministic event streams as JSON for Rust cross-language testing."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from org_kernel.test_harness import generate_stream
from org_kernel.engine import OrgEngine
from org_kernel.hashing import canonical_hash, canonical_serialize

COMBOS = [
    (42, 10), (42, 20), (42, 50),
    (99, 10), (99, 20), (99, 50),
    (123, 10), (123, 20), (123, 50),
]

results = []

for seed, n_events in COMBOS:
    events = generate_stream(seed, n_events)
    engine = OrgEngine()
    engine.initialize_state()
    for evt in events:
        engine.apply_event(evt)
    state = engine.state
    h = canonical_hash(state)
    canon_json = canonical_serialize(state).decode("utf-8")

    event_dicts = [e.to_dict() for e in events]
    results.append({
        "seed": seed,
        "n_events": n_events,
        "events": event_dicts,
        "expected_hash": h,
        "expected_role_count": len(state.roles),
        "expected_active_roles": sum(1 for r in state.roles.values() if r.active),
        "expected_structural_debt": state.structural_debt,
        "expected_canonical_json": canon_json,
    })
    print(f"seed={seed}, n={n_events}: hash={h}, roles={len(state.roles)}, debt={state.structural_debt}")

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "org_engine_replica", "test_fixtures.json")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=True, separators=(",", ":"))

print(f"\nDumped {len(results)} fixtures to {out_path}")
