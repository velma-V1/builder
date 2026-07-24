PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    contract_version INTEGER NOT NULL CHECK (contract_version > 0),
    current_state TEXT NOT NULL,
    sequence INTEGER NOT NULL CHECK (sequence >= 0),
    updated_at TEXT NOT NULL
);

CREATE TABLE task_state_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    prev_state TEXT,
    new_state TEXT NOT NULL,
    cause TEXT NOT NULL,
    actor TEXT NOT NULL,
    accepted INTEGER NOT NULL CHECK (accepted IN (0, 1)),
    occurred_at TEXT NOT NULL,
    linked_reference TEXT,
    idempotency_key TEXT,
    UNIQUE (task_id, idempotency_key)
);

CREATE TRIGGER task_state_events_no_update
BEFORE UPDATE ON task_state_events
BEGIN SELECT RAISE(ABORT, 'task_state_events are append-only'); END;

CREATE TRIGGER task_state_events_no_delete
BEFORE DELETE ON task_state_events
BEGIN SELECT RAISE(ABORT, 'task_state_events are append-only'); END;
