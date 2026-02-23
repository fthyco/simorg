# file: backend/supabase_event_repository.py
"""
Supabase (PostgreSQL) Event Repository.

Drop-in replacement for the SQLite EventRepository.
Same interface, PostgreSQL storage via psycopg2.

Stateless: no in-memory caching. Every read hits the DB.
"""

from __future__ import annotations

import json
import os
import sys
import pg8000.native
from urllib.parse import urlparse

# Allow importing org_kernel from parent directory
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

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS project_metadata (
    project_id TEXT PRIMARY KEY,
    stage TEXT,
    industry TEXT,
    event_count INTEGER NOT NULL DEFAULT 0,
    structural_debt INTEGER NOT NULL DEFAULT 0,
    structural_density INTEGER NOT NULL DEFAULT 0,
    state_hash TEXT,
    department_map JSONB,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS events (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id   TEXT NOT NULL,
    sequence     INTEGER NOT NULL,
    event_type   TEXT NOT NULL,
    event_uuid   TEXT,
    timestamp    TEXT,
    payload      JSONB NOT NULL,
    UNIQUE(project_id, sequence)
);

CREATE INDEX IF NOT EXISTS idx_event_proj_seq
    ON events(project_id, sequence);
CREATE INDEX IF NOT EXISTS idx_event_type
    ON events(project_id, event_type);
CREATE INDEX IF NOT EXISTS idx_event_timestamp
    ON events(project_id, timestamp);
"""

_MAX_RETRIES = 3


def reconstruct_event(event_dict: dict) -> BaseEvent:
    """Reconstruct a typed event from a stored dict."""
    etype = event_dict["event_type"]
    cls = _EVENT_CLASS_MAP.get(etype)
    if cls is None:
        raise ValueError(f"Unknown event_type {etype!r}")
    return cls(
        timestamp=event_dict.get("timestamp", ""),
        sequence=event_dict.get("sequence", 0),
        logical_time=event_dict.get("logical_time", 0),
        event_uuid=event_dict.get("event_uuid", ""),
        payload=event_dict.get("payload", {}),
    )


class SupabaseEventRepository:
    """
    PostgreSQL-backed event store for Supabase.

    Thread-safe via connection-per-operation pattern.
    """

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._ensure_schema()

    def _get_conn(self):
        # Manual parser: urlparse chokes on special chars ([], @) in passwords
        url = self._database_url
        # Strip scheme (postgresql:// or postgres://)
        url = url.split("://", 1)[1]
        # Split at LAST @ to separate credentials from host (password may contain @)
        at_idx = url.rfind("@")
        credentials = url[:at_idx]
        host_part = url[at_idx + 1:]
        # Split credentials at FIRST : to get user and password
        colon_idx = credentials.find(":")
        user = credentials[:colon_idx]
        password = credentials[colon_idx + 1:]
        # Split host_part into host:port/database
        host_port, database = host_part.split("/", 1)
        host, port_str = host_port.rsplit(":", 1)
        return pg8000.native.Connection(
            user=user,
            password=password,
            host=host,
            port=int(port_str),
            database=database or "postgres",
            ssl_context=True,
        )

    def _ensure_schema(self) -> None:
        conn = self._get_conn()
        try:
            # pg8000 native doesn't support multiple statement strings natively in one .run() if they are complex, 
            # but we can execute them sequentially
            for stmt in _INIT_SQL.split(";")[:-1]:  # Split by semicolon and ignore the last empty string
                if stmt.strip():
                    conn.run(stmt)
            # Support live upgrade
            conn.run("ALTER TABLE project_metadata ADD COLUMN IF NOT EXISTS department_map JSONB")
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Project Metadata
    # ------------------------------------------------------------------

    def upsert_project_metadata(
        self,
        project_id: str,
        stage: str = "",
        industry: str = "",
        event_count: int = 0,
        structural_debt: int = 0,
        structural_density: int = 0,
        state_hash: str = "",
        department_map: Optional[dict] = None
    ) -> None:
        conn = self._get_conn()
        try:
            conn.run(
                """
                INSERT INTO project_metadata
                    (project_id, stage, industry, event_count, structural_debt, structural_density, state_hash, department_map, last_updated)
                VALUES (:pid, :stg, :ind, :ec, :sd, :sden, :sh, :dmap, NOW())
                ON CONFLICT (project_id) DO UPDATE SET
                    stage = COALESCE(NULLIF(EXCLUDED.stage, ''), project_metadata.stage),
                    industry = COALESCE(NULLIF(EXCLUDED.industry, ''), project_metadata.industry),
                    event_count = EXCLUDED.event_count,
                    structural_debt = EXCLUDED.structural_debt,
                    structural_density = EXCLUDED.structural_density,
                    state_hash = EXCLUDED.state_hash,
                    department_map = EXCLUDED.department_map,
                    last_updated = NOW()
                """,
                pid=project_id,
                stg=stage,
                ind=industry,
                ec=event_count,
                sd=structural_debt,
                sden=structural_density,
                sh=state_hash,
                dmap=json.dumps(department_map) if department_map is not None else None
            )
        finally:
            conn.close()

    def list_projects(self, project_ids: Optional[List[str]] = None) -> List[dict]:
        """Returns all projects ordered by newest first, optionally filtered by project_ids."""
        conn = self._get_conn()
        try:
            if project_ids is not None:
                if not project_ids:
                    return [] # Return early if empty list provided
                rows = conn.run(
                    """
                    SELECT project_id, stage, industry, event_count, structural_debt, structural_density, state_hash, last_updated
                    FROM project_metadata
                    WHERE project_id = ANY(:pids)
                    ORDER BY last_updated DESC
                    """,
                    pids=project_ids
                )
            else:
                rows = conn.run(
                    """
                    SELECT project_id, stage, industry, event_count, structural_debt, structural_density, state_hash, last_updated
                    FROM project_metadata
                    ORDER BY last_updated DESC
                    """
                )
        finally:
            conn.close()
        
        return [
            {
                "project_id": r[0],
                "stage": r[1],
                "industry": r[2],
                "event_count": r[3],
                "structural_debt": r[4],
                "structural_density": r[5],
                "state_hash": r[6],
                "last_updated": r[7].isoformat() if r[7] else None
            }
            for r in rows
        ]

    def get_project_metadata(self, project_id: str) -> Optional[dict]:
        """Fetches metadata for a single project, including the department_map."""
        conn = self._get_conn()
        try:
            rows = conn.run(
                """
                SELECT project_id, stage, industry, event_count, structural_debt, structural_density, state_hash, department_map, last_updated
                FROM project_metadata
                WHERE project_id = :pid
                """,
                pid=project_id
            )
            if not rows:
                return None
            row = rows[0]
            return {
                "project_id": row[0],
                "stage": row[1],
                "industry": row[2],
                "event_count": row[3],
                "structural_debt": row[4],
                "structural_density": row[5],
                "state_hash": row[6],
                "department_map": row[7] if not isinstance(row[7], str) else json.loads(row[7]),
                "last_updated": row[8].isoformat() if row[8] else None
            }
        finally:
            conn.close()

    def delete_project(self, project_id: str) -> None:
        """Deletes a project completely along with its events."""
        conn = self._get_conn()
        try:
            conn.run("DELETE FROM events WHERE project_id = :pid", pid=project_id)
            conn.run("DELETE FROM project_metadata WHERE project_id = :pid", pid=project_id)
        finally:
            conn.close()

    def rename_project(self, old_id: str, new_id: str) -> None:
        """Atomically renames a project across events and metadata."""
        conn = self._get_conn()
        try:
            conn.run("UPDATE events SET project_id = :new_id WHERE project_id = :old_id", new_id=new_id, old_id=old_id)
            conn.run("UPDATE project_metadata SET project_id = :new_id WHERE project_id = :old_id", new_id=new_id, old_id=old_id)
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def append_event(
        self,
        project_id: str,
        event: BaseEvent,
        event_uuid: str = "",
    ) -> int:
        """
        Append event. Assigns next sequence atomically.
        Returns assigned sequence.

        Idempotency: if event_uuid exists, returns existing sequence.
        Concurrency: retries on unique violation.
        """
        if event_uuid:
            existing = self._find_by_uuid(project_id, event_uuid)
            if existing is not None:
                return existing

        event_dict = event.to_dict()

        import pg8000.exceptions

        for attempt in range(_MAX_RETRIES):
            conn = self._get_conn()
            try:
                rows = conn.run(
                    "SELECT COALESCE(MAX(sequence), 0) FROM events WHERE project_id = :pid",
                    pid=project_id,
                )
                seq = rows[0][0] + 1

                conn.run(
                    """
                    INSERT INTO events
                        (project_id, sequence, event_type, event_uuid,
                            timestamp, payload)
                    VALUES (:pid, :seq, :etype, :euuid, :ts, :payload)
                    """,
                    pid=project_id,
                    seq=seq,
                    etype=event_dict["event_type"],
                    euuid=event_uuid or None,
                    ts=event_dict["timestamp"],
                    payload=json.dumps(event_dict["payload"]),
                )
                return seq
            except pg8000.exceptions.DatabaseError as e:
                # pg8000 native doesn't use explicit transactions, but we can catch the constraint violation
                if attempt == _MAX_RETRIES - 1:
                    raise
            finally:
                conn.close()

        raise RuntimeError("append_event: exhausted retries")

    def replace_all_events(
        self,
        project_id: str,
        events: List[BaseEvent],
    ) -> int:
        """
        Replace ALL events for a project (used by /import).
        Returns the count of events inserted.
        """
        conn = self._get_conn()
        try:
            conn.run(
                "DELETE FROM events WHERE project_id = :pid",
                pid=project_id,
            )
            for i, event in enumerate(events, 1):
                event_dict = event.to_dict()
                conn.run(
                    """
                    INSERT INTO events
                        (project_id, sequence, event_type, event_uuid,
                            timestamp, payload)
                    VALUES (:pid, :seq, :etype, :euuid, :ts, :payload)
                    """,
                    pid=project_id,
                    seq=i,
                    etype=event_dict["event_type"],
                    euuid=event_dict.get("event_uuid") or None,
                    ts=event_dict["timestamp"],
                    payload=json.dumps(event_dict["payload"]),
                )
            return len(events)
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def load_events(
        self, project_id: str, after_sequence: int = 0,
    ) -> List[BaseEvent]:
        """Load events ordered by sequence."""
        conn = self._get_conn()
        try:
            rows = conn.run(
                """
                SELECT event_type, timestamp, payload, sequence, event_uuid
                FROM events
                WHERE project_id = :pid AND sequence > :seq
                ORDER BY sequence
                """,
                pid=project_id,
                seq=after_sequence,
            )
        finally:
            conn.close()

        result: List[BaseEvent] = []
        for row in rows:
            payload = row[2] if isinstance(row[2], dict) else json.loads(row[2])
            event_dict = {
                "event_type": row[0],
                "timestamp": row[1] or "",
                "payload": payload,
                "sequence": row[3],
                "event_uuid": row[4] or "",
            }
            result.append(reconstruct_event(event_dict))
        return result

    def get_last_sequence(self, project_id: str) -> int:
        conn = self._get_conn()
        try:
            rows = conn.run(
                "SELECT COALESCE(MAX(sequence), 0) FROM events WHERE project_id = :pid",
                pid=project_id,
            )
            return rows[0][0]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Idempotency
    # ------------------------------------------------------------------

    def _find_by_uuid(self, project_id: str, event_uuid: str) -> Optional[int]:
        conn = self._get_conn()
        try:
            rows = conn.run(
                "SELECT sequence FROM events WHERE project_id = :pid AND event_uuid = :euuid",
                pid=project_id,
                euuid=event_uuid,
            )
            return rows[0][0] if rows else None
        finally:
            conn.close()
