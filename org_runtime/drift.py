# file: org_runtime/drift.py
"""
Drift Comparator — pure function, no side effects.

Computes a structured diff between two state dicts.
No Engine dependency. Structural density is calculated
directly from the dict using the same formula as graph.py:

    density = len(dependencies) / (n * (n - 1))   if n >= 2
            = 0.0                                  otherwise
"""

from __future__ import annotations

from typing import Any, Dict, List, Set


def compare_states(state_a: dict, state_b: dict) -> dict:
    """
    Compare two state dicts and return a structured diff.

    Both inputs are expected to be the output of OrgState.to_dict().

    Returns dict with:
        role_count_delta, active_role_delta, structural_debt_delta,
        structural_density_delta, added_roles, removed_roles,
        activated_roles, deactivated_roles
    """
    roles_a = state_a.get("roles", {})
    roles_b = state_b.get("roles", {})

    ids_a: Set[str] = set(roles_a.keys())
    ids_b: Set[str] = set(roles_b.keys())

    added = sorted(ids_b - ids_a)
    removed = sorted(ids_a - ids_b)

    # Active role counts
    active_a = sum(1 for r in roles_a.values() if r.get("active", True))
    active_b = sum(1 for r in roles_b.values() if r.get("active", True))

    # Activation changes (roles present in both states)
    common = ids_a & ids_b
    activated: List[str] = []
    deactivated: List[str] = []
    for rid in sorted(common):
        was_active = roles_a[rid].get("active", True)
        is_active = roles_b[rid].get("active", True)
        if not was_active and is_active:
            activated.append(rid)
        elif was_active and not is_active:
            deactivated.append(rid)

    # Structural density — computed directly, no Engine
    density_a = _compute_density(state_a)
    density_b = _compute_density(state_b)

    debt_a = state_a.get("structural_debt", 0)
    debt_b = state_b.get("structural_debt", 0)

    return {
        "role_count_a": len(roles_a),
        "role_count_b": len(roles_b),
        "role_count_delta": len(roles_b) - len(roles_a),
        "active_role_a": active_a,
        "active_role_b": active_b,
        "active_role_delta": active_b - active_a,
        "structural_debt_a": debt_a,
        "structural_debt_b": debt_b,
        "structural_debt_delta": debt_b - debt_a,
        "structural_density_a": round(density_a, 4),
        "structural_density_b": round(density_b, 4),
        "structural_density_delta": round(density_b - density_a, 4),
        "added_roles": added,
        "removed_roles": removed,
        "activated_roles": activated,
        "deactivated_roles": deactivated,
    }


def _compute_density(state_dict: dict) -> float:
    """
    Pure density calculation from a state dict.
    Same formula as graph.compute_structural_density:
        edges / (n * (n - 1))   for directed graph, n >= 2
    """
    roles = state_dict.get("roles", {})
    deps = state_dict.get("dependencies", [])
    n = len(roles)
    if n < 2:
        return 0.0
    max_edges = n * (n - 1)
    return len(deps) / max_edges
