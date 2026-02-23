"""
Semantic Labeler — Post-Cluster Label Assignment

Runs AFTER structural partitioning is complete.
Consumes cluster output + Classification DB.
Never influences partitioning.

Label assignment: majority vote of department_label across roles in cluster.
Tie-breaking: lexicographic (deterministic).
Confidence denominator: total roles in cluster (not just labeled roles).

All confidence values: int64 fixed-point (real * SCALE).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from ..domain_types import SCALE, checked_mul
from .department_types import Cluster
from .classification_db import ClassificationDB


@dataclass(frozen=True)
class LabeledCluster:
    """
    A structural cluster enriched with semantic label.

    dominant_label: majority-vote label from DB.
    label_confidence: (dominant_count * SCALE) // total_roles_in_cluster.
    label_distribution: label → count mapping (sorted keys).
    """

    cluster_id: str
    role_ids: tuple[str, ...]
    dominant_label: str
    label_confidence: int           # fixed-point * SCALE
    label_distribution: dict[str, int]  # label → count


def label_clusters(
    clusters: List[Cluster],
    db: ClassificationDB,
) -> List[LabeledCluster]:
    """
    Assign semantic labels to structural clusters.

    For each cluster:
      1. Query DB for each role_id in the cluster.
      2. Count occurrences of each department_label.
      3. Dominant label = most frequent. Ties → lexicographic first.
      4. Confidence = dominant_count * SCALE // total_roles_in_cluster.
         (denominator is total roles, not just labeled roles)
      5. If no DB entries → label = "Unclassified", confidence = 0.

    Returns: sorted list of LabeledCluster (by cluster_id).
    """
    result: List[LabeledCluster] = []

    for cluster in clusters:
        label_counts: Dict[str, int] = {}
        for rid in cluster.role_ids:
            classification = db.get(rid)
            if classification is not None:
                label = classification.department_label
                label_counts[label] = label_counts.get(label, 0) + 1

        total_roles = len(cluster.role_ids)

        if not label_counts:
            # No DB entries for any role in this cluster
            result.append(LabeledCluster(
                cluster_id=cluster.id,
                role_ids=cluster.role_ids,
                dominant_label="Unclassified",
                label_confidence=0,
                label_distribution={},
            ))
        else:
            # Majority vote with lexicographic tie-breaking
            dominant_label = max(
                sorted(label_counts.keys()),
                key=lambda lbl: label_counts[lbl],
            )
            dominant_count = label_counts[dominant_label]

            # Confidence: dominant_count / total_roles (not just labeled ones)
            confidence = checked_mul(dominant_count, SCALE) // total_roles

            result.append(LabeledCluster(
                cluster_id=cluster.id,
                role_ids=cluster.role_ids,
                dominant_label=dominant_label,
                label_confidence=confidence,
                label_distribution=dict(sorted(label_counts.items())),
            ))

    result.sort(key=lambda lc: lc.cluster_id)
    return result
