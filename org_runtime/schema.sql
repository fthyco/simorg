-- Organizational Runtime — Persistence Schema v2
-- sqlite3

CREATE TABLE IF NOT EXISTS events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id    TEXT    NOT NULL,
    sequence      INTEGER NOT NULL,
    event_type    TEXT    NOT NULL,
    timestamp     TEXT,
    event_uuid    TEXT,
    payload_json  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id    TEXT    NOT NULL,
    sequence      INTEGER NOT NULL,
    state_json    TEXT    NOT NULL,
    created_at    TEXT    NOT NULL
);

-- Stream metadata: tracks last known state hash for determinism verification
CREATE TABLE IF NOT EXISTS stream_metadata (
    project_id      TEXT    PRIMARY KEY,
    last_sequence   INTEGER NOT NULL DEFAULT 0,
    last_state_hash TEXT    NOT NULL DEFAULT '',
    updated_at      TEXT    NOT NULL
);

-- === Indexes ===

-- Concurrency: prevents duplicate (project_id, sequence) inserts
CREATE UNIQUE INDEX IF NOT EXISTS idx_event_sequence
    ON events(project_id, sequence);

-- Idempotency: prevents duplicate event_uuid per project
CREATE UNIQUE INDEX IF NOT EXISTS idx_event_uuid
    ON events(project_id, event_uuid);

CREATE UNIQUE INDEX IF NOT EXISTS idx_snapshot_sequence
    ON snapshots(project_id, sequence);

-- Secondary indexes for analytics / future queries
CREATE INDEX IF NOT EXISTS idx_event_type
    ON events(project_id, event_type);

CREATE INDEX IF NOT EXISTS idx_event_timestamp
    ON events(project_id, timestamp);
