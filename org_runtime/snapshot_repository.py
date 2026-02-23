# file: org_runtime/snapshot_repository.py
"""
Snapshot Repository — sqlite3-backed state snapshots.

Snapshots capture OrgState.to_dict() AFTER a given event sequence.
They exist for:
  1. Drift comparison between time points
  2. Consistency verification (compare replay result vs stored snapshot)
  3. Future optimization (fast state reconstruction)

Snapshots are NEVER used for direct state injection —
state reconstruction always goes through engine.replay().
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class SnapshotRepository:
    """
    Snapshot store backed by sqlite3.
    Shares the same DB file as EventRepository.
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
    # Write
    # ------------------------------------------------------------------

    def save_snapshot(
        self,
        project_id: str,
        sequence: int,
        state_dict: dict,
    ) -> None:
        """
        Persist a state snapshot at the given sequence.

        Uses INSERT OR REPLACE to allow overwriting if re-snapshotting
        the same sequence (e.g. during replay verification).
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO snapshots
                    (project_id, sequence, state_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    project_id,
                    sequence,
                    json.dumps(state_dict, ensure_ascii=False),
                    now,
                ),
            )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def load_latest_snapshot(
        self, project_id: str,
    ) -> Optional[Tuple[int, dict]]:
        """
        Load the most recent snapshot for a project.

        Returns (sequence, state_dict) or None if no snapshots exist.
        """
        cursor = self._conn.execute(
            """
            SELECT sequence, state_json
            FROM snapshots
            WHERE project_id = ?
            ORDER BY sequence DESC
            LIMIT 1
            """,
            (project_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return (row[0], json.loads(row[1]))

    def load_snapshot_at(
        self, project_id: str, sequence: int,
    ) -> Optional[dict]:
        """
        Load a snapshot at an exact sequence number.
        Returns state_dict or None.
        """
        cursor = self._conn.execute(
            "SELECT state_json FROM snapshots WHERE project_id = ? AND sequence = ?",
            (project_id, sequence),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def close(self) -> None:
        self._conn.close()
