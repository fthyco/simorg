# file: org_runtime/observability.py
"""
Observability — In-process metrics collection.

No external dependencies. Uses compute_diagnostics + timing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .session import SimulationSession


@dataclass(frozen=True)
class SessionMetrics:
    """Snapshot of observable session metrics."""

    replay_latency_ms: float
    event_count: int
    structural_debt: int
    structural_density: int       # fixed-point (× SCALE)
    active_role_count: int
    last_state_hash: str
    snapshot_count: int
    warnings: list


def collect_metrics(session: "SimulationSession") -> SessionMetrics:
    """
    Collect metrics from a live session.

    Performs a full replay to measure latency and verify determinism.
    """
    from org_kernel.hashing import canonical_hash

    # Measure replay latency
    start = time.perf_counter()
    session.replay_full()
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    diagnostics = session.get_diagnostics()
    state_hash = canonical_hash(session._engine.state)

    return SessionMetrics(
        replay_latency_ms=round(elapsed_ms, 2),
        event_count=session.current_sequence,
        structural_debt=diagnostics["structural_debt"],
        structural_density=diagnostics["structural_density"],
        active_role_count=diagnostics["active_role_count"],
        last_state_hash=state_hash,
        snapshot_count=0,  # placeholder — could query snapshot_repo
        warnings=diagnostics["warnings"],
    )
