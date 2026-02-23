# file: org_runtime/event_repository.py
"""
Event Repository — sqlite3-backed event store.

v2: Concurrency control (retry on IntegrityError),
    Idempotency (event_uuid dedup),
    Stream metadata (last_state_hash tracking).

Stores events as JSON. Reconstructs proper event class instances
on load (strict type dispatch, never generic BaseEvent).

All sequence assignment is transaction-wrapped.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from org_kernel.events import (
    AddDependencyEvent,
    AddRoleEvent,
    ApplyConstraintChangeEvent,
    BaseEvent,
    CompressRolesEvent,
    DifferentiateRoleEvent,
    InitializeConstantsEvent,
    InjectShockEvent,
    RemoveRoleEvent,
)

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Max retries for concurrent sequence conflicts
_MAX_RETRIES: int = 3

# Strict event-type → class mapping.
# Never fall back to generic BaseEvent — preserve polymorphism.
_EVENT_CLASS_MAP = {
    "initialize_constants": InitializeConstantsEvent,
    "add_role": AddRoleEvent,
    "remove_role": RemoveRoleEvent,
    "differentiate_role": DifferentiateRoleEvent,
    "compress_roles": CompressRolesEvent,
    "apply_constraint_change": ApplyConstraintChangeEvent,
    "inject_shock": InjectShockEvent,
    "add_dependency": AddDependencyEvent,
}


def reconstruct_event(event_dict: dict) -> BaseEvent:
    """
    Reconstruct a typed event instance from a stored dict.

    Dispatches on event_type to the correct subclass.
    Raises ValueError for unknown types — never silently degrades.
    """
    etype = event_dict["event_type"]
    cls = _EVENT_CLASS_MAP.get(etype)
    if cls is None:
        raise ValueError(
            f"Unknown event_type {etype!r} — cannot reconstruct. "
            f"Known types: {sorted(_EVENT_CLASS_MAP)}"
        )
    return cls(
        timestamp=event_dict.get("timestamp", ""),
        sequence=event_dict.get("sequence", 0),
        logical_time=event_dict.get("logical_time", 0),
        event_uuid=event_dict.get("event_uuid", ""),
        payload=event_dict.get("payload", {}),
    )


class EventRepository:
    """
    Append-only event store backed by sqlite3.

    v2 additions:
      - Retry on IntegrityError (concurrent sequence conflict)
      - Idempotency via event_uuid (duplicate → return existing sequence)
      - Stream metadata CRUD (last_state_hash tracking)

    Thread-safety: single-writer assumed, but retry provides resilience.
    All writes are transaction-wrapped for atomicity.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        self._conn.executescript(schema_sql)

    # ------------------------------------------------------------------
    # Write (with concurrency + idempotency)
    # ------------------------------------------------------------------

    def append_event(
        self,
        project_id: str,
        event: BaseEvent,
        event_uuid: str = "",
    ) -> int:
        """
        Append a single event. Assigns next sequence atomically.
        Returns the assigned sequence number.

        Idempotency: if event_uuid is provided and already exists,
        returns the existing sequence without inserting a duplicate.

        Concurrency: retries up to _MAX_RETRIES on IntegrityError
        (sequence conflict from concurrent writers).
        """
        # Idempotency check — if uuid already stored, return existing seq
        if event_uuid:
            existing = self._find_by_uuid(project_id, event_uuid)
            if existing is not None:
                return existing

        for attempt in range(_MAX_RETRIES):
            try:
                with self._conn:
                    seq = self._next_sequence(project_id)
                    event_dict = event.to_dict()
                    self._conn.execute(
                        """
                        INSERT INTO events
                            (project_id, sequence, event_type, timestamp,
                             event_uuid, payload_json)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            project_id,
                            seq,
                            event_dict["event_type"],
                            event_dict["timestamp"],
                            event_uuid or None,
                            json.dumps(event_dict["payload"], ensure_ascii=False),
                        ),
                    )
                return seq
            except sqlite3.IntegrityError:
                if attempt == _MAX_RETRIES - 1:
                    raise
                # Retry with fresh sequence on next iteration
                continue

        # Unreachable, but satisfies type checker
        raise RuntimeError("append_event: exhausted retries")  # pragma: no cover

    def append_batch(self, project_id: str, events: List[BaseEvent]) -> List[int]:
        """
        Append multiple events atomically inside a single transaction.
        Returns list of assigned sequence numbers.

        If any insert fails, the entire batch is rolled back —
        sequence integrity is preserved.
        """
        sequences: List[int] = []
        with self._conn:
            base_seq = self._next_sequence(project_id)
            for i, event in enumerate(events):
                seq = base_seq + i
                event_dict = event.to_dict()
                self._conn.execute(
                    """
                    INSERT INTO events
                        (project_id, sequence, event_type, timestamp,
                         event_uuid, payload_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        seq,
                        event_dict["event_type"],
                        event_dict["timestamp"],
                        event_dict.get("event_uuid") or None,
                        json.dumps(event_dict["payload"], ensure_ascii=False),
                    ),
                )
                sequences.append(seq)
        return sequences

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def load_events(
        self, project_id: str, after_sequence: int = 0,
    ) -> List[BaseEvent]:
        """
        Load events ordered by sequence.

        If after_sequence > 0, only events with sequence > after_sequence
        are returned (useful for partial replay after snapshot).

        Returns fully-typed event instances — never raw dicts.
        """
        cursor = self._conn.execute(
            """
            SELECT event_type, timestamp, payload_json, sequence, event_uuid
            FROM events
            WHERE project_id = ? AND sequence > ?
            ORDER BY sequence
            """,
            (project_id, after_sequence),
        )
        result: List[BaseEvent] = []
        for row in cursor:
            event_dict = {
                "event_type": row[0],
                "timestamp": row[1],
                "payload": json.loads(row[2]),
                "sequence": row[3],
                "event_uuid": row[4] or "",
            }
            result.append(reconstruct_event(event_dict))
        return result

    def get_last_sequence(self, project_id: str) -> int:
        """Return the highest sequence number for a project, or 0 if none."""
        cursor = self._conn.execute(
            "SELECT COALESCE(MAX(sequence), 0) FROM events WHERE project_id = ?",
            (project_id,),
        )
        return cursor.fetchone()[0]

    # ------------------------------------------------------------------
    # Idempotency lookup
    # ------------------------------------------------------------------

    def _find_by_uuid(self, project_id: str, event_uuid: str) -> Optional[int]:
        """Return sequence of an event with this uuid, or None."""
        cursor = self._conn.execute(
            "SELECT sequence FROM events WHERE project_id = ? AND event_uuid = ?",
            (project_id, event_uuid),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def load_event_by_uuid(
        self, project_id: str, event_uuid: str,
    ) -> Optional[BaseEvent]:
        """Load a single event by its uuid. Returns None if not found."""
        cursor = self._conn.execute(
            """
            SELECT event_type, timestamp, payload_json, sequence, event_uuid
            FROM events
            WHERE project_id = ? AND event_uuid = ?
            """,
            (project_id, event_uuid),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        event_dict = {
            "event_type": row[0],
            "timestamp": row[1],
            "payload": json.loads(row[2]),
            "sequence": row[3],
            "event_uuid": row[4] or "",
        }
        return reconstruct_event(event_dict)

    # ------------------------------------------------------------------
    # Stream metadata
    # ------------------------------------------------------------------

    def update_metadata(
        self, project_id: str, sequence: int, state_hash: str,
    ) -> None:
        """Upsert stream metadata with the latest known hash."""
        now = datetime.now(timezone.utc).isoformat()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO stream_metadata
                    (project_id, last_sequence, last_state_hash, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    last_sequence = excluded.last_sequence,
                    last_state_hash = excluded.last_state_hash,
                    updated_at = excluded.updated_at
                """,
                (project_id, sequence, state_hash, now),
            )

    def load_metadata(
        self, project_id: str,
    ) -> Optional[Tuple[int, str]]:
        """
        Load stream metadata.
        Returns (last_sequence, last_state_hash) or None.
        """
        cursor = self._conn.execute(
            "SELECT last_sequence, last_state_hash FROM stream_metadata WHERE project_id = ?",
            (project_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return (row[0], row[1])

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _next_sequence(self, project_id: str) -> int:
        """
        Compute next sequence. MUST be called inside a transaction
        (the caller's `with self._conn:` block ensures this).
        """
        cursor = self._conn.execute(
            "SELECT COALESCE(MAX(sequence), 0) FROM events WHERE project_id = ?",
            (project_id,),
        )
        return cursor.fetchone()[0] + 1

    def close(self) -> None:
        self._conn.close()
