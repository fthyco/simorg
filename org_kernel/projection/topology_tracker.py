"""
Topology Tracker — Incremental Recompute Triggers

Tracks topology fingerprint between projection builds.
Recompute only when graph structure changes meaningfully.

Pure constraint changes (capital/talent/time/political_cost) do NOT
trigger recompute — they do not affect the dependency graph.

All density values: int64 fixed-point (real * SCALE).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..domain_types import OrgState, SCALE
from ..graph import compute_structural_density


@dataclass(frozen=True)
class TopologyFingerprint:
    """Snapshot of topology-relevant metrics."""

    role_count: int
    dependency_count: int
    density: int  # fixed-point (real * SCALE)


@dataclass(frozen=True)
class RecomputeThresholds:
    """
    Thresholds that trigger cluster recomputation.
    Any single threshold breach → recompute.
    """

    role_count_delta: int = 1
    dependency_count_delta: int = 1
    density_delta: int = 500  # 0.05 * SCALE


def compute_fingerprint(state: OrgState) -> TopologyFingerprint:
    """Extract topology fingerprint from current state."""
    return TopologyFingerprint(
        role_count=len(state.roles),
        dependency_count=len(state.dependencies),
        density=compute_structural_density(state),
    )


def should_recompute(
    prev: TopologyFingerprint | None,
    curr: TopologyFingerprint,
    thresholds: RecomputeThresholds | None = None,
) -> bool:
    """
    Determine whether clustering should be recomputed.

    Returns True if:
      - No previous fingerprint exists (first computation)
      - Any topology delta exceeds its threshold
    """
    if prev is None:
        return True

    if thresholds is None:
        thresholds = RecomputeThresholds()

    if abs(curr.role_count - prev.role_count) >= thresholds.role_count_delta:
        return True

    if abs(curr.dependency_count - prev.dependency_count) >= thresholds.dependency_count_delta:
        return True

    if abs(curr.density - prev.density) >= thresholds.density_delta:
        return True

    return False
