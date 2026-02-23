"""
Organizational Kernel — Graph Utilities v1.1

Pure dict-based graph analysis. No external dependencies.
All density values: int64 fixed-point (real * SCALE).
"""

from __future__ import annotations

from typing import Dict, List, Set, Tuple

from .domain_types import DependencyEdge, OrgState, SCALE, checked_mul


# ---------------------------------------------------------------------------
# Adjacency
# ---------------------------------------------------------------------------

def build_adjacency_map(
    dependencies: List[DependencyEdge],
) -> Dict[str, List[str]]:
    """Build a forward adjacency map: from_role -> [to_roles]."""
    adj: Dict[str, List[str]] = {}
    for edge in dependencies:
        adj.setdefault(edge.from_role_id, []).append(edge.to_role_id)
    return adj


# ---------------------------------------------------------------------------
# Structural Density (fixed-point int64)
# ---------------------------------------------------------------------------

def compute_structural_density(state: OrgState) -> int:
    """
    Structural density = (edges * SCALE) // max_possible_edges.
    Returns 0 if fewer than 2 roles or no max edges.
    """
    n = len(state.roles)
    if n < 2:
        return 0
    max_edges = n * (n - 1)  # directed graph
    if max_edges == 0:
        return 0
    return checked_mul(len(state.dependencies), SCALE) // max_edges


def compute_role_structural_density(
    role_id: str, state: OrgState,
) -> int:
    """
    Local structural density for a single role (fixed-point int64).
    = (connected_edges * SCALE) // total_edges.
    Returns 0 if no edges exist.
    """
    if not state.dependencies:
        return 0
    count = sum(
        1
        for d in state.dependencies
        if d.from_role_id == role_id or d.to_role_id == role_id
    )
    total = len(state.dependencies)
    if total == 0:
        return 0
    return checked_mul(count, SCALE) // total


# ---------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------

def find_isolated_roles(state: OrgState) -> List[str]:
    """Return role IDs that have zero incoming AND zero outgoing edges."""
    connected: Set[str] = set()
    for edge in state.dependencies:
        connected.add(edge.from_role_id)
        connected.add(edge.to_role_id)
    return sorted(rid for rid in state.roles if rid not in connected)


# ---------------------------------------------------------------------------
# Degree helpers
# ---------------------------------------------------------------------------

def count_incoming(role_id: str, dependencies: List[DependencyEdge]) -> int:
    return sum(1 for d in dependencies if d.to_role_id == role_id)


def count_outgoing(role_id: str, dependencies: List[DependencyEdge]) -> int:
    return sum(1 for d in dependencies if d.from_role_id == role_id)


# ---------------------------------------------------------------------------
# Critical-cycle detection
# ---------------------------------------------------------------------------

def detect_critical_cycles(state: OrgState) -> List[List[str]]:
    """
    Detect cycles in the dependency graph where **every** edge in the
    cycle has ``critical=True``.

    Returns a list of cycles (each cycle is a list of role IDs).
    Uses iterative DFS with explicit colour tracking.
    """
    critical_adj: Dict[str, List[str]] = {}
    for edge in state.dependencies:
        if edge.critical:
            critical_adj.setdefault(edge.from_role_id, []).append(edge.to_role_id)

    WHITE, GREY, BLACK = 0, 1, 2
    colour: Dict[str, int] = {rid: WHITE for rid in sorted(state.roles)}
    parent: Dict[str, str | None] = {}
    cycles: List[List[str]] = []

    def _dfs(start: str) -> None:
        stack: List[Tuple[str, int]] = [(start, 0)]
        colour[start] = GREY
        parent[start] = None

        while stack:
            node, idx = stack[-1]
            neighbours = sorted(critical_adj.get(node, []))
            if idx < len(neighbours):
                stack[-1] = (node, idx + 1)
                nbr = neighbours[idx]
                if colour.get(nbr, WHITE) == GREY:
                    cycle = [nbr]
                    for sn, _ in reversed(stack):
                        cycle.append(sn)
                        if sn == nbr:
                            break
                    cycles.append(cycle)
                elif colour.get(nbr, WHITE) == WHITE:
                    colour[nbr] = GREY
                    parent[nbr] = node
                    stack.append((nbr, 0))
            else:
                colour[node] = BLACK
                stack.pop()

    for rid in sorted(state.roles):
        if colour.get(rid, WHITE) == WHITE:
            _dfs(rid)

    return cycles
