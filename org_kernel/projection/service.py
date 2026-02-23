"""
Department Projection Service v0.2

Orchestrates the three-layer architecture:
  Layer 2: Clustering Engine → structural partition
  Layer 3: Classification DB → semantic labeling (optional)
  Analytics: Drift Detection (optional)

Integrates TopologyTracker for incremental recompute.

The service never modifies kernel state.
The DB never influences clustering.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from ..domain_types import DependencyEdge, OrgState, SCALE, checked_mul
from .department_types import Cluster, Department, DepartmentView
from .clustering import cluster_roles, canonical_cluster_hash, _build_edge_set, _internal_density
from .metrics import compute_boundary_heat, compute_inter_department_edges
from .topology_tracker import (
    TopologyFingerprint,
    RecomputeThresholds,
    compute_fingerprint,
    should_recompute,
)
from .classification_db import ClassificationDB
from .semantic_labeler import LabeledCluster, label_clusters


class DepartmentProjectionService:
    """
    Stateful service that builds and caches DepartmentView projections.

    Caching strategy:
      - Topology fingerprint determines whether clusters need recomputation.
      - Cache key = (event_count, cluster_hash) — never mutable state.
      - If topology hasn't changed, cached view is returned.
    """

    def __init__(
        self,
        db: ClassificationDB | None = None,
        thresholds: RecomputeThresholds | None = None,
    ) -> None:
        self._db: ClassificationDB | None = db
        self._thresholds = thresholds or RecomputeThresholds()
        self._prev_fingerprint: TopologyFingerprint | None = None
        self._cached_clusters: List[Cluster] | None = None
        self._cached_cluster_hash: str = ""
        self._cache: Dict[int, DepartmentView] = {}

    def build(self, state: OrgState) -> DepartmentView:
        """
        Build a DepartmentView projection from OrgState.

        Uses topology fingerprint to decide whether to recompute clusters.
        If DB is provided, applies semantic labels; otherwise Unclassified.
        """
        version = len(state.event_history)

        # Check event-version cache first
        if version in self._cache:
            return self._cache[version]

        # Compute topology fingerprint
        fingerprint = compute_fingerprint(state)

        # Decide whether to recompute clusters
        if should_recompute(self._prev_fingerprint, fingerprint, self._thresholds):
            clusters = cluster_roles(state)
            cluster_hash = canonical_cluster_hash(clusters)
            self._cached_clusters = clusters
            self._cached_cluster_hash = cluster_hash
            self._prev_fingerprint = fingerprint
        else:
            clusters = self._cached_clusters or cluster_roles(state)
            cluster_hash = self._cached_cluster_hash

        view = _build_view(state, clusters, cluster_hash, version, self._db)
        self._cache[version] = view
        return view


def _build_view(
    state: OrgState,
    clusters: List[Cluster],
    cluster_hash: str,
    version: int,
    db: ClassificationDB | None,
) -> DepartmentView:
    """Assemble a DepartmentView from clusters and optional DB."""

    if not state.roles:
        return DepartmentView(
            version=version,
            departments=[],
            clusters=[],
            role_to_department={},
            role_to_cluster={},
            inter_department_edges=[],
            boundary_heat={},
            cluster_hash="",
        )

    # Semantic labeling (optional)
    labeled: List[LabeledCluster] | None = None
    if db is not None:
        labeled = label_clusters(clusters, db)

    # Build departments from clusters
    departments: List[Department] = []
    role_to_department: Dict[str, str] = {}
    role_to_cluster: Dict[str, str] = {}

    for idx, cluster in enumerate(clusters):
        dept_id = f"dept_{idx}"
        scale_stage = state.roles[cluster.role_ids[0]].scale_stage

        # Find semantic label if available
        semantic_label = "Unclassified"
        label_confidence = 0
        if labeled is not None:
            for lc in labeled:
                if lc.cluster_id == cluster.id:
                    semantic_label = lc.dominant_label
                    label_confidence = lc.label_confidence
                    break

        dept = Department(
            id=dept_id,
            role_ids=list(cluster.role_ids),
            internal_density=cluster.internal_density,
            external_dependencies=cluster.external_edge_count,
            scale_stage=scale_stage,
            semantic_label=semantic_label,
            label_confidence=label_confidence,
        )
        departments.append(dept)

        for rid in cluster.role_ids:
            role_to_department[rid] = dept_id
            role_to_cluster[rid] = cluster.id

    inter_edges = compute_inter_department_edges(role_to_department, state.dependencies)
    boundary = compute_boundary_heat(departments, role_to_department, state.dependencies)

    view = DepartmentView(
        version=version,
        departments=departments,
        clusters=clusters,
        role_to_department=role_to_department,
        role_to_cluster=role_to_cluster,
        inter_department_edges=inter_edges,
        boundary_heat=boundary,
        cluster_hash=cluster_hash,
    )

    _validate(view, state)
    return view


def _validate(view: DepartmentView, state: OrgState) -> None:
    """Validate integrity of the projection."""
    # All active roles must be assigned
    active_roles = {rid for rid, r in state.roles.items() if r.active}
    assigned_roles = set(view.role_to_department.keys())

    if active_roles != assigned_roles:
        raise ValueError(
            f"role_to_department keys {assigned_roles} "
            f"!= active roles {active_roles}"
        )

    for dept in view.departments:
        if not dept.role_ids:
            raise ValueError(f"Empty department: {dept.id}")

    valid_ids = {d.id for d in view.departments}
    for src, dst in view.inter_department_edges:
        if src not in valid_ids or dst not in valid_ids:
            raise ValueError(
                f"Inter-department edge ({src}, {dst}) references invalid department id"
            )
