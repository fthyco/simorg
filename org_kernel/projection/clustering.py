"""
Clustering Engine v0.2 — Pure Graph-Based Partitioning

Deterministic structural clustering over OrgState.
No semantic signals. No randomness. No external DB access.

Algorithm:
  1. Build undirected adjacency from dependencies
  2. Discover connected components (BFS, sorted iteration)
  3. Within each component: recursive bipartition via modularity gain
     - Score = internal_edges - external_edges
     - Split only if both partitions improve over single cluster
     - Recursion depth capped
     - Early exit on score gain <= 0
  4. Isolated roles → singleton clusters

Cluster IDs: SHA-256 of sorted role IDs (deterministic, no counters).

All density values: int64 fixed-point (real * SCALE).
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Set, Tuple

from ..domain_types import DependencyEdge, OrgState, SCALE, checked_mul
from .department_types import Cluster


# ── Configuration ─────────────────────────────────────────────

MAX_BIPARTITION_DEPTH: int = 10

# Minimum component density before attempting bipartition.
# Below this, the component is already sparse — splitting gains nothing.
MIN_DENSITY_FOR_SPLIT: int = 1000  # 0.1 * SCALE


# ── Public API ────────────────────────────────────────────────

def cluster_roles(state: OrgState) -> List[Cluster]:
    """
    Deterministic clustering of roles into structural groups.

    Pure function: cluster(state: OrgState) → List[Cluster]
    No randomness. No semantic data. No DB access.
    """
    if not state.roles:
        return []

    active_roles = sorted(rid for rid, r in state.roles.items() if r.active)
    if not active_roles:
        return []

    # Build undirected adjacency (only between active roles)
    active_set = set(active_roles)
    adj = _build_undirected_adjacency(state.dependencies, active_set)

    # Build directed edge set for density calculations
    edge_set = _build_edge_set(state.dependencies, active_set)

    # Discover connected components
    components = _find_connected_components(active_roles, adj)

    # Partition each component
    clusters: List[Cluster] = []
    for component in components:
        if len(component) == 1:
            clusters.append(_make_cluster(component, edge_set))
        else:
            density = _internal_density(component, edge_set)
            if density < MIN_DENSITY_FOR_SPLIT:
                # Too sparse to split meaningfully
                clusters.append(_make_cluster(component, edge_set))
            else:
                sub_clusters = _bipartition_recursive(
                    component, adj, edge_set, depth=0,
                )
                clusters.extend(sub_clusters)

    # Sort clusters for deterministic output order
    clusters.sort(key=lambda c: c.role_ids)
    return clusters


def canonical_cluster_hash(clusters: List[Cluster]) -> str:
    """
    SHA-256 of canonical cluster representation.
    Deterministic given identical cluster output.
    """
    canonical = []
    for c in sorted(clusters, key=lambda c: c.role_ids):
        canonical.append({
            "id": c.id,
            "role_ids": list(c.role_ids),
            "internal_density": c.internal_density,
            "external_edge_count": c.external_edge_count,
        })
    raw = json.dumps(
        canonical, ensure_ascii=True, separators=(",", ":"), sort_keys=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ── Cluster Construction ──────────────────────────────────────

def _make_cluster_id(role_ids: Tuple[str, ...]) -> str:
    """SHA-256 of sorted role IDs. Deterministic."""
    raw = json.dumps(
        list(role_ids), ensure_ascii=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _make_cluster(
    role_ids: List[str],
    edge_set: Set[Tuple[str, str]],
) -> Cluster:
    """Build a Cluster from a list of role IDs."""
    sorted_ids = tuple(sorted(role_ids))
    members = set(sorted_ids)
    density = _internal_density(list(sorted_ids), edge_set)
    ext_count = _external_edge_count(members, edge_set)
    return Cluster(
        id=_make_cluster_id(sorted_ids),
        role_ids=sorted_ids,
        internal_density=density,
        external_edge_count=ext_count,
    )


# ── Graph Primitives ──────────────────────────────────────────

def _build_undirected_adjacency(
    dependencies: List[DependencyEdge],
    active_roles: Set[str],
) -> Dict[str, Set[str]]:
    """Build undirected adjacency map for active roles only."""
    adj: Dict[str, Set[str]] = {rid: set() for rid in active_roles}
    for edge in dependencies:
        if edge.from_role_id in active_roles and edge.to_role_id in active_roles:
            adj[edge.from_role_id].add(edge.to_role_id)
            adj[edge.to_role_id].add(edge.from_role_id)
    return adj


def _build_edge_set(
    dependencies: List[DependencyEdge],
    active_roles: Set[str],
) -> Set[Tuple[str, str]]:
    """Build directed edge set for O(1) lookup."""
    return {
        (e.from_role_id, e.to_role_id)
        for e in dependencies
        if e.from_role_id in active_roles and e.to_role_id in active_roles
    }


def _find_connected_components(
    role_ids: List[str],
    adj: Dict[str, Set[str]],
) -> List[List[str]]:
    """
    BFS-based connected component discovery.
    Deterministic via sorted iteration at every step.
    """
    visited: Set[str] = set()
    components: List[List[str]] = []

    for rid in role_ids:  # already sorted
        if rid in visited:
            continue
        component: List[str] = []
        queue = [rid]
        visited.add(rid)
        while queue:
            node = queue.pop(0)
            component.append(node)
            for neighbor in sorted(adj.get(node, set())):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        component.sort()
        components.append(component)

    return components


# ── Bipartition ───────────────────────────────────────────────

def _internal_density(
    group: List[str], edge_set: Set[Tuple[str, str]],
) -> int:
    """
    (edges_inside_group * SCALE) // max_possible_edges
    Returns 0 if fewer than 2 members. int64 fixed-point.
    """
    n = len(group)
    if n < 2:
        return 0
    members = set(group)
    internal = sum(
        1 for (a, b) in edge_set if a in members and b in members
    )
    max_possible = n * (n - 1)
    if max_possible == 0:
        return 0
    return checked_mul(internal, SCALE) // max_possible


def _external_edge_count(
    members: Set[str],
    edge_set: Set[Tuple[str, str]],
) -> int:
    """Count directed edges crossing the cluster boundary."""
    return sum(
        1 for (a, b) in edge_set
        if (a in members) != (b in members)
    )


def _partition_quality(
    part_a: List[str],
    part_b: List[str],
    edge_set: Set[Tuple[str, str]],
) -> int:
    """
    Density-normalized partition quality score (int64 fixed-point).

    Score = density(A) + density(B).

    This favours splits where both partitions are internally dense,
    even if the combined component has many edges. A fully connected
    6-node component (density=SCALE) scores SCALE, but splitting into
    two fully connected 3-node cliques scores 2*SCALE.

    Higher is better. Returns 0..2*SCALE.
    """
    return _internal_density(part_a, edge_set) + _internal_density(part_b, edge_set)


def _bipartition_recursive(
    component: List[str],
    adj: Dict[str, Set[str]],
    edge_set: Set[Tuple[str, str]],
    depth: int,
) -> List[Cluster]:
    """
    Recursive bipartition of a connected component.

    Uses density-normalized scoring with greedy vertex-moving refinement
    (Kernighan-Lin inspired):
      1. Start with lexicographic split (first half / second half)
      2. Try moving each vertex to the other side
      3. Accept move if combined density score improves
      4. Repeat until no improving move found
      5. Recurse on each partition if split density > single density

    Scoring: compare sum of partition densities vs 2 * single density.
    A split is accepted when avg partition density > single density.

    Deterministic: sorted iteration, lexicographic tie-breaking.
    """
    if len(component) <= 1 or depth >= MAX_BIPARTITION_DEPTH:
        return [_make_cluster(component, edge_set)]

    # Density of keeping as single cluster
    single_density = _internal_density(component, edge_set)

    # For comparison: split must beat 2 * single_density (sum of two partitions)
    single_baseline = checked_mul(single_density, 2)

    # Initial split: lexicographic midpoint
    mid = len(component) // 2
    part_a = list(component[:mid])
    part_b = list(component[mid:])

    # Greedy improvement
    part_a, part_b = _greedy_refine(part_a, part_b, edge_set)

    # If either partition is empty after refinement, no valid split
    if not part_a or not part_b:
        return [_make_cluster(component, edge_set)]

    # Density score of the split
    split_quality = _partition_quality(part_a, part_b, edge_set)

    # Only accept split if avg partition density strictly exceeds single density
    if split_quality <= single_baseline:
        return [_make_cluster(component, edge_set)]

    # Recurse on each partition
    result: List[Cluster] = []
    result.extend(_bipartition_recursive(part_a, adj, edge_set, depth + 1))
    result.extend(_bipartition_recursive(part_b, adj, edge_set, depth + 1))
    return result


def _greedy_refine(
    part_a: List[str],
    part_b: List[str],
    edge_set: Set[Tuple[str, str]],
) -> Tuple[List[str], List[str]]:
    """
    Greedy vertex-moving refinement.
    Try moving each vertex; accept if combined partition quality improves.
    Deterministic: iterate in sorted order.
    """
    improved = True
    while improved:
        improved = False
        current_score = _partition_quality(part_a, part_b, edge_set)

        # Try moving from A to B
        for rid in sorted(part_a):
            if len(part_a) <= 1:
                break
            new_a = [r for r in part_a if r != rid]
            new_b = sorted(part_b + [rid])
            new_score = _partition_quality(new_a, new_b, edge_set)
            if new_score > current_score:
                part_a = new_a
                part_b = new_b
                current_score = new_score
                improved = True
                break

        if improved:
            continue

        # Try moving from B to A
        for rid in sorted(part_b):
            if len(part_b) <= 1:
                break
            new_b = [r for r in part_b if r != rid]
            new_a = sorted(part_a + [rid])
            new_score = _partition_quality(new_a, new_b, edge_set)
            if new_score > current_score:
                part_a = new_a
                part_b = new_b
                current_score = new_score
                improved = True
                break

    return sorted(part_a), sorted(part_b)
