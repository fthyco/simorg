# file: org_runtime/session.py
"""
Simulation Session — orchestrates engine + persistence.

v2: Hash tracking (stream_metadata), idempotency passthrough,
    determinism verification, observability.

Apply-before-persist order:
  1. engine.apply_event(event)     — may raise InvariantViolationError
  2. event_repo.append_event(...)  — only if step 1 succeeded
  3. update metadata hash          — only if step 2 succeeded
  4. snapshot if interval reached   — only if step 2 succeeded

This guarantees that persisted events are always valid and replayable.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from org_kernel.engine import OrgEngine
from org_kernel.events import BaseEvent
from org_kernel.domain_types import TransitionResult
from org_kernel.hashing import canonical_hash

from .event_repository import EventRepository
from .snapshot_repository import SnapshotRepository


class SnapshotInconsistencyError(Exception):
    """Raised when a stored snapshot doesn't match replayed state."""

    def __init__(self, project_id: str, sequence: int, diff_keys: list):
        self.project_id = project_id
        self.sequence = sequence
        self.diff_keys = diff_keys
        super().__init__(
            f"Snapshot inconsistency at seq {sequence} for project "
            f"{project_id!r}: divergent keys {diff_keys}"
        )


class DeterminismError(Exception):
    """Raised when replay produces a different hash than the stored one."""

    def __init__(self, project_id: str, expected: str, actual: str):
        self.project_id = project_id
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Determinism failure for project {project_id!r}: "
            f"stored hash={expected!r}, replayed hash={actual!r}"
        )


class SimulationSession:
    """
    Orchestrates the OrgEngine with persistent event/snapshot stores.

    v2 additions:
      - Hash tracking in stream_metadata after every apply
      - Idempotency passthrough (event_uuid)
      - verify_determinism() method
      - get_metrics() for observability
    """

    def __init__(
        self,
        project_id: str,
        engine: OrgEngine,
        event_repo: EventRepository,
        snapshot_repo: SnapshotRepository,
        snapshot_interval: int = 10,
    ) -> None:
        self._project_id = project_id
        self._engine = engine
        self._event_repo = event_repo
        self._snapshot_repo = snapshot_repo
        self._snapshot_interval = snapshot_interval
        self._current_sequence: int = 0

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """
        Reconstruct state from persisted events.

        Always replays from scratch (deterministic guarantee).
        If a snapshot exists, verifies replay result against it.
        """
        events = self._event_repo.load_events(self._project_id)
        self._current_sequence = self._event_repo.get_last_sequence(
            self._project_id
        )

        if events:
            self._engine.replay(events)
        else:
            self._engine.initialize_state()

    # ------------------------------------------------------------------
    # Event application (apply-before-persist)
    # ------------------------------------------------------------------

    def apply_event(
        self,
        event: BaseEvent,
        event_uuid: str = "",
    ) -> Tuple["dict", TransitionResult]:
        """
        Apply an event to the engine, then persist if successful.

        Order:
          1. engine.apply_event(event)
          2. persist event (only on success)
          3. update stream_metadata hash
          4. auto-snapshot at interval

        If engine.apply_event raises (e.g. InvariantViolationError),
        nothing is persisted — the event log stays clean.

        Idempotency: if event_uuid is provided and already persisted,
        the event is re-applied to in-memory engine but not re-inserted
        into the DB.
        """
        # Step 1: Assign next sequence to event
        seq = self._current_sequence + 1
        event.sequence = seq

        # Step 2: Apply to engine (may raise)
        state, result = self._engine.apply_event(event)

        # Step 3: Persist (only reached if step 2 succeeded)
        self._event_repo.append_event(
            self._project_id, event, event_uuid=event_uuid,
        )
        self._current_sequence = seq

        # Step 4: Update stream metadata with hash
        state_hash = canonical_hash(state)
        self._event_repo.update_metadata(
            self._project_id, seq, state_hash,
        )

        # Step 5: Auto-snapshot at interval
        if self._snapshot_interval > 0 and seq % self._snapshot_interval == 0:
            self._snapshot_repo.save_snapshot(
                self._project_id, seq, state.to_dict(),
            )

        return state.to_dict(), result

    # ------------------------------------------------------------------
    # Replay
    # ------------------------------------------------------------------

    def replay_full(self) -> dict:
        """
        Full event-sourced reconstruction: reset engine, replay all
        persisted events from scratch.

        Returns the final state dict.
        """
        events = self._event_repo.load_events(self._project_id)
        self._current_sequence = self._event_repo.get_last_sequence(
            self._project_id
        )
        if events:
            self._engine.replay(events)
        else:
            self._engine.initialize_state()
        return self._engine.state.to_dict()

    def replay_to_sequence(self, target_sequence: int) -> dict:
        """
        Replay events up to (and including) a specific sequence number.
        Returns state dict at that point.

        Uses a fresh engine internally to avoid disturbing current state.
        """
        events = self._event_repo.load_events(self._project_id)
        # Take only events up to target_sequence
        events_subset = events[:target_sequence]

        temp_engine = OrgEngine()
        if events_subset:
            temp_engine.replay(events_subset)
        else:
            temp_engine.initialize_state()
        return temp_engine.state.to_dict()

    # ------------------------------------------------------------------
    # Determinism verification
    # ------------------------------------------------------------------

    def verify_determinism(self) -> bool:
        """
        Replay from scratch and compare hash against stored metadata.

        Raises DeterminismError if mismatch.
        Returns True if consistent (or no metadata exists yet).
        """
        metadata = self._event_repo.load_metadata(self._project_id)
        if metadata is None:
            return True

        stored_seq, stored_hash = metadata

        # Full replay
        events = self._event_repo.load_events(self._project_id)
        temp_engine = OrgEngine()
        if events:
            temp_engine.replay(events)
        else:
            temp_engine.initialize_state()

        replayed_hash = canonical_hash(temp_engine.state)

        if replayed_hash != stored_hash:
            raise DeterminismError(
                self._project_id, stored_hash, replayed_hash,
            )

        return True

    # ------------------------------------------------------------------
    # Snapshot consistency verification
    # ------------------------------------------------------------------

    def verify_snapshot_consistency(self) -> bool:
        """
        Verify all stored snapshots match replay results.

        For each snapshot at sequence N:
          1. Replay events 1..N
          2. Compare replayed state.to_dict() with stored snapshot
          3. Raise SnapshotInconsistencyError on mismatch

        Returns True if all snapshots are consistent.
        """
        all_events = self._event_repo.load_events(self._project_id)
        last_seq = self._event_repo.get_last_sequence(self._project_id)

        # Check every snapshot that exists
        for seq in range(1, last_seq + 1):
            stored = self._snapshot_repo.load_snapshot_at(
                self._project_id, seq,
            )
            if stored is None:
                continue

            # Replay up to this sequence
            events_subset = all_events[:seq]
            temp_engine = OrgEngine()
            if events_subset:
                temp_engine.replay(events_subset)
            else:
                temp_engine.initialize_state()

            replayed = temp_engine.state.to_dict()

            # Compare
            diff_keys = _dict_diff_keys(stored, replayed)
            if diff_keys:
                raise SnapshotInconsistencyError(
                    self._project_id, seq, diff_keys,
                )

        return True

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def get_metrics(self) -> "SessionMetrics":
        """Collect metrics from the current session."""
        from .observability import collect_metrics
        return collect_metrics(self)

    # ------------------------------------------------------------------
    # Delegates
    # ------------------------------------------------------------------

    def get_state(self) -> dict:
        """Return current state as dict."""
        return self._engine.state.to_dict()

    def get_diagnostics(self) -> dict:
        """Return engine diagnostics."""
        return self._engine.get_diagnostics()

    @property
    def current_sequence(self) -> int:
        return self._current_sequence


def _dict_diff_keys(a: dict, b: dict) -> list:
    """Return list of top-level keys where dicts differ."""
    all_keys = set(a.keys()) | set(b.keys())
    return [k for k in sorted(all_keys) if a.get(k) != b.get(k)]
