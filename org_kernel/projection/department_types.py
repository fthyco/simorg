"""
Department Projection Layer — Domain Types v0.2

Structural clustering types (Layer 2) and department view types.
All numeric values: int64 fixed-point (real * SCALE).

Cluster is purely structural — no semantic fields.
Department is the enriched view after semantic labeling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class Cluster:
    """
    Pure structural cluster — output of graph-based partitioning.

    id: SHA-256 of sorted role_ids (deterministic, no counter).
    role_ids: tuple of role IDs in this cluster (sorted).
    internal_density: intra-cluster edge density (fixed-point).
    external_edge_count: number of edges crossing cluster boundary.
    """

    id: str
    role_ids: tuple[str, ...]
    internal_density: int       # fixed-point scaled (real * SCALE)
    external_edge_count: int


@dataclass(frozen=True)
class Department:
    """
    Enriched department — structural cluster + semantic label.
    """

    id: str
    role_ids: list[str]
    internal_density: int       # fixed-point scaled (real * SCALE)
    external_dependencies: int
    scale_stage: str
    semantic_label: str = "Unclassified"
    label_confidence: int = 0   # fixed-point: agreement ratio * SCALE


@dataclass(frozen=True)
class DepartmentView:
    version: int
    departments: list[Department]
    clusters: list[Cluster]
    role_to_department: dict[str, str]
    role_to_cluster: dict[str, str]
    inter_department_edges: list[tuple[str, str]]
    boundary_heat: dict[str, int]  # fixed-point scaled (real * SCALE)
    cluster_hash: str              # canonical SHA-256 of cluster output
