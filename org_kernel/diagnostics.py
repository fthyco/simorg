"""
Organizational Kernel — Diagnostics v1.1

Compute a diagnostic snapshot of the current organizational state.
All density values: int64 fixed-point.
"""

from __future__ import annotations

from .domain_types import OrgState, SCALE
from .graph import compute_structural_density, find_isolated_roles


def compute_diagnostics(state: OrgState) -> dict:
    """
    Return a diagnostic dict summarising the current state health.
    structural_density is int64 fixed-point (real * SCALE).
    """
    density = compute_structural_density(state)
    isolated = find_isolated_roles(state)
    governance_edges = sum(
        1 for d in state.dependencies if d.dependency_type == "governance"
    )

    warnings: list[str] = []

    if density > 7000:  # 0.7 * SCALE
        warnings.append(
            f"High structural density ({density}) — fragile interdependence"
        )
    if state.structural_debt > 5:
        warnings.append(
            f"Structural debt={state.structural_debt} — "
            f"organization accumulating suppressed adaptation"
        )
    if isolated:
        warnings.append(
            f"{len(isolated)} isolated role(s): {', '.join(isolated)}"
        )

    inactive = sorted(r.id for r in state.roles.values() if not r.active)
    if inactive:
        warnings.append(
            f"{len(inactive)} inactive role(s): {', '.join(inactive)}"
        )

    return {
        "role_count": len(state.roles),
        "active_role_count": sum(1 for r in state.roles.values() if r.active),
        "structural_density": density,
        "structural_debt": state.structural_debt,
        "isolated_roles": isolated,
        "governance_edges": governance_edges,
        "warnings": warnings,
    }
