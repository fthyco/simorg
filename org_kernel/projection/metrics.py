from __future__ import annotations

from typing import Dict, List, Set, Tuple

from ..domain_types import DependencyEdge, Role, SCALE, checked_mul


def compute_boundary_heat(
    departments: List,
    role_to_dept: Dict[str, str],
    dependencies: List[DependencyEdge],
) -> Dict[str, int]:
    """
    Per department (int64 fixed-point):
      boundary_heat = (external_edges * SCALE) // total_edges_touching_dept

    Range 0..SCALE.  0 = closed cluster, SCALE = fully externally dependent.
    Returns 0 for departments with no edges at all.
    """
    dept_external: Dict[str, int] = {}
    dept_total: Dict[str, int] = {}

    for d in departments:
        dept_external[d.id] = 0
        dept_total[d.id] = 0

    for edge in dependencies:
        dept_from = role_to_dept.get(edge.from_role_id)
        dept_to = role_to_dept.get(edge.to_role_id)
        if dept_from is None or dept_to is None:
            continue

        dept_total[dept_from] = dept_total.get(dept_from, 0) + 1
        dept_total[dept_to] = dept_total.get(dept_to, 0) + 1

        if dept_from != dept_to:
            dept_external[dept_from] = dept_external.get(dept_from, 0) + 1
            dept_external[dept_to] = dept_external.get(dept_to, 0) + 1

    result: Dict[str, int] = {}
    for d in departments:
        total = dept_total.get(d.id, 0)
        if total == 0:
            result[d.id] = 0
        else:
            result[d.id] = checked_mul(dept_external.get(d.id, 0), SCALE) // total
    return result


def compute_inter_department_edges(
    role_to_dept: Dict[str, str],
    dependencies: List[DependencyEdge],
) -> List[Tuple[str, str]]:
    """
    Collapse role-level edges into department-level edges.
    No duplicates. Returns sorted list of (dept_x, dept_y) tuples.
    """
    seen: Set[Tuple[str, str]] = set()
    for edge in dependencies:
        dept_from = role_to_dept.get(edge.from_role_id)
        dept_to = role_to_dept.get(edge.to_role_id)
        if dept_from is None or dept_to is None:
            continue
        if dept_from != dept_to:
            seen.add((dept_from, dept_to))
    return sorted(seen)
