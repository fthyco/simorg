# file: org_runtime/__init__.py
"""
Organizational Runtime — Persistence Layer v2

Non-invasive persistence around the Organizational Kernel v1.1.

v2: Concurrency control, idempotency, hash validation, observability.
"""

from .event_repository import EventRepository, reconstruct_event
from .snapshot_repository import SnapshotRepository
from .session import SimulationSession, SnapshotInconsistencyError, DeterminismError
from .drift import compare_states
from .observability import SessionMetrics, collect_metrics

__all__ = [
    "EventRepository",
    "SnapshotRepository",
    "SimulationSession",
    "SnapshotInconsistencyError",
    "DeterminismError",
    "compare_states",
    "reconstruct_event",
    "SessionMetrics",
    "collect_metrics",
]
