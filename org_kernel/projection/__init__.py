"""
Department Projection Layer v0.2

Three-layer architecture:
  Layer 2: Clustering Engine (structural)
  Layer 3: Classification DB + Semantic Labeler (enrichment)
  Analytics: Drift Detection (observational)
"""

from .department_types import Cluster, Department, DepartmentView
from .service import DepartmentProjectionService
from .classification_db import ClassificationDB, RoleClassification
from .semantic_labeler import LabeledCluster, label_clusters
from .cluster_drift import DriftEntry, DriftReport, compute_cluster_drift
from .topology_tracker import (
    TopologyFingerprint,
    RecomputeThresholds,
    compute_fingerprint,
    should_recompute,
)
from .clustering import cluster_roles, canonical_cluster_hash

__all__ = [
    # Types
    "Cluster",
    "Department",
    "DepartmentView",
    "LabeledCluster",
    "DriftEntry",
    "DriftReport",
    "TopologyFingerprint",
    "RecomputeThresholds",
    "RoleClassification",
    # Services
    "DepartmentProjectionService",
    "ClassificationDB",
    # Functions
    "cluster_roles",
    "canonical_cluster_hash",
    "label_clusters",
    "compute_cluster_drift",
    "compute_fingerprint",
    "should_recompute",
]
