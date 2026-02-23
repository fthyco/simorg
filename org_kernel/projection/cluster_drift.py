"""
Cluster Drift Detector — Declared vs Structural Divergence

Compares Classification DB labels (declared department) against
structural cluster labels (emergent department).

Produces:
  - Per-role divergence entries
  - Aggregate divergence ratio (fixed-point * SCALE)
  - Phantom departments: declared but no structural match
  - Hidden couplings: different declared depts, same structural cluster

Detection is purely structural:
  If roles from different declared departments fall into the same
  structural cluster → hidden coupling.

Direction is never reversed:
  Structural truth → observed.
  Declared label → claimed.
  Divergence = gap between claim and observation.

All ratio values: int64 fixed-point (real * SCALE).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from ..domain_types import SCALE, checked_mul
from .semantic_labeler import LabeledCluster
from .classification_db import ClassificationDB


@dataclass(frozen=True)
class DriftEntry:
    """Per-role divergence record."""

    role_id: str
    declared_department: str
    structural_cluster_id: str
    structural_cluster_label: str
    is_divergent: bool


@dataclass(frozen=True)
class DriftReport:
    """
    Aggregate drift analysis.

    divergence_ratio: divergent_count * SCALE // total_count.
    phantom_departments: labels declared in DB but not matching
        any structural cluster's dominant label.
    hidden_couplings: pairs of declared departments whose roles
        fall into the same structural cluster.
    """

    entries: tuple[DriftEntry, ...]
    divergent_count: int
    total_count: int
    divergence_ratio: int            # fixed-point * SCALE
    phantom_departments: tuple[str, ...]
    hidden_couplings: tuple[tuple[str, str], ...]


def compute_cluster_drift(
    labeled_clusters: List[LabeledCluster],
    db: ClassificationDB,
) -> DriftReport:
    """
    Compare declared department labels against structural cluster labels.

    For each role that has a DB classification:
      - declared_department = DB label
      - structural_cluster_label = cluster's dominant label
      - is_divergent = (declared != structural)

    Phantom departments: labels that appear in DB but do not appear
    as any cluster's dominant label.

    Hidden couplings: pairs of declared departments where at least one
    role from each department falls into the same structural cluster.
    """
    # Build role → cluster mapping
    role_to_cluster: Dict[str, LabeledCluster] = {}
    for lc in labeled_clusters:
        for rid in lc.role_ids:
            role_to_cluster[rid] = lc

    # Build entries for all classified roles
    entries: List[DriftEntry] = []
    all_db = db.get_all()

    for rid in sorted(all_db.keys()):
        classification = all_db[rid]
        cluster = role_to_cluster.get(rid)
        if cluster is None:
            # Role in DB but not in any cluster (possibly inactive)
            continue

        declared = classification.department_label
        structural_label = cluster.dominant_label
        is_divergent = declared != structural_label

        entries.append(DriftEntry(
            role_id=rid,
            declared_department=declared,
            structural_cluster_id=cluster.cluster_id,
            structural_cluster_label=structural_label,
            is_divergent=is_divergent,
        ))

    total = len(entries)
    divergent = sum(1 for e in entries if e.is_divergent)

    if total == 0:
        divergence_ratio = 0
    else:
        divergence_ratio = checked_mul(divergent, SCALE) // total

    # -- Phantom departments --
    # Labels declared in DB but not matching any cluster dominant label
    declared_labels: Set[str] = {c.department_label for c in all_db.values()}
    structural_labels: Set[str] = {lc.dominant_label for lc in labeled_clusters}
    phantoms = sorted(declared_labels - structural_labels)

    # -- Hidden couplings --
    # Pairs of declared departments whose roles share a structural cluster
    hidden: Set[Tuple[str, str]] = set()
    for lc in labeled_clusters:
        # Collect all declared departments for roles in this cluster
        dept_labels_in_cluster: Set[str] = set()
        for rid in lc.role_ids:
            classification = all_db.get(rid)
            if classification is not None:
                dept_labels_in_cluster.add(classification.department_label)

        # If multiple declared departments map to same cluster → coupling
        labels_list = sorted(dept_labels_in_cluster)
        for i in range(len(labels_list)):
            for j in range(i + 1, len(labels_list)):
                hidden.add((labels_list[i], labels_list[j]))

    return DriftReport(
        entries=tuple(entries),
        divergent_count=divergent,
        total_count=total,
        divergence_ratio=divergence_ratio,
        phantom_departments=tuple(phantoms),
        hidden_couplings=tuple(sorted(hidden)),
    )
