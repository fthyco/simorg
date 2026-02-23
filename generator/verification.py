"""
Verification Harness — Compile, replay, and verify generated event streams.

Provides both single-spec verification and a suite of smoke tests when
run as __main__.
"""

from __future__ import annotations

from org_kernel.engine import OrgEngine
from org_kernel.hashing import canonical_hash

from .compiler import compile_template
from .template_spec import TemplateSpec


def verify_generated_template(spec: TemplateSpec, seed: int) -> dict:
    """
    Compile a template, replay it through the engine, and return diagnostics.

    Returns:
        {
            "final_state_hash": str,
            "diagnostics": dict,
            "role_count": int,
            "structural_debt": int,
        }
    """
    events = compile_template(spec, seed)

    engine = OrgEngine()
    engine.replay(events)

    state = engine.state
    diagnostics = engine.get_diagnostics()

    return {
        "final_state_hash": canonical_hash(state),
        "diagnostics": diagnostics,
        "role_count": len(state.roles),
        "structural_debt": state.structural_debt,
    }


# ---------------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------------

def _run_smoke_tests() -> None:
    """Run a suite of deterministic smoke tests."""
    import json

    specs = [
        ("balanced_4", TemplateSpec(
            role_count=4, domain_count=2,
            intra_density_target=5000, inter_density_target=2000,
            capacity_profile="balanced", fragility_mode=False,
            drift_mode=False, shock_magnitude=0,
            differentiation_pressure=0,
        )),
        ("high_6_fragile", TemplateSpec(
            role_count=6, domain_count=3,
            intra_density_target=3000, inter_density_target=1000,
            capacity_profile="high", fragility_mode=True,
            drift_mode=False, shock_magnitude=0,
            differentiation_pressure=0,
        )),
        ("low_3_shock", TemplateSpec(
            role_count=3, domain_count=1,
            intra_density_target=5000, inter_density_target=0,
            capacity_profile="low", fragility_mode=False,
            drift_mode=False, shock_magnitude=5,
            differentiation_pressure=0,
        )),
        ("balanced_5_diff_pressure", TemplateSpec(
            role_count=5, domain_count=2,
            intra_density_target=4000, inter_density_target=2000,
            capacity_profile="balanced", fragility_mode=False,
            drift_mode=False, shock_magnitude=0,
            differentiation_pressure=3,
        )),
    ]

    seed = 42
    all_ok = True

    for label, spec in specs:
        print(f"\n{'-'*60}")
        print(f"  {label}  (seed={seed})")
        print(f"{'-'*60}")

        try:
            result = verify_generated_template(spec, seed)
            print(json.dumps(result, indent=2, default=str))

            # Determinism check: same spec+seed must produce identical hash
            result2 = verify_generated_template(spec, seed)
            if result["final_state_hash"] != result2["final_state_hash"]:
                print("  FAIL: DETERMINISM FAILURE")
                all_ok = False
            else:
                print(f"  OK: Deterministic (hash stable)")
        except Exception as exc:
            print(f"  FAIL: {exc}")
            all_ok = False

    print(f"\n{'='*60}")
    if all_ok:
        print("  ALL SMOKE TESTS PASSED")
    else:
        print("  SOME TESTS FAILED")
    print(f"{'='*60}")


if __name__ == "__main__":
    _run_smoke_tests()
