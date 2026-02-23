"""Test all industry × stage × success_level combinations generate without error."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generator.compiler import compile_from_template
from generator.template_spec import TemplateSpec
from generator.industry_templates import get_template

industries = ["tech_saas", "manufacturing", "marketplace"]
stages = ["seed", "growth", "structured", "mature"]
success_levels = [10, 30, 50, 70, 90]

passed = 0
failed = 0

for ind in industries:
    for stage in stages:
        for sl in success_levels:
            ratio = sl / 100.0
            template = get_template(ind, stage)
            role_count = sum(len(d.roles) for d in template.departments)
            domain_count = len(template.departments)

            intra = int(2500 + ratio * 1500)
            inter = int(500 + ratio * 1000)

            fragility = ratio < 0.5 or ind == "manufacturing"
            shock = 3 if ratio < 0.3 else (1 if ratio < 0.6 else 0)

            if ratio < 0.33:
                cap = "low"
            elif ratio > 0.66:
                cap = "high"
            else:
                cap = "balanced"

            spec = TemplateSpec(
                role_count=role_count,
                domain_count=domain_count,
                intra_density_target=intra,
                inter_density_target=inter,
                capacity_profile=cap,
                fragility_mode=fragility,
                drift_mode=False,
                shock_magnitude=shock,
                differentiation_pressure=max(0, int(3 - ratio * 2)),
            )

            try:
                events, dept_map = compile_from_template(template, spec, seed=42)
                role_events = [e for e in events if e.event_type == "add_role"]
                print(f"  OK  {ind:15s} {stage:12s} sl={sl:3d}  roles={len(role_events):2d}  events={len(events):3d}")
                passed += 1
            except Exception as e:
                print(f"  FAIL {ind:15s} {stage:12s} sl={sl:3d}  {e}")
                failed += 1

print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
if failed:
    sys.exit(1)
