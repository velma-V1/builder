PRAGMA foreign_keys = ON;

CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE integration_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    state TEXT NOT NULL,
    detail TEXT NOT NULL,
    occurred_at INTEGER NOT NULL
);

CREATE TABLE integration_operations (
    operation_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN (
        'PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED', 'INTERRUPTED'
    )),
    context_id TEXT,
    request_json TEXT NOT NULL,
    result_json TEXT,
    reason TEXT,
    actor TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE INDEX integration_operations_name_state
ON integration_operations(name, state);

CREATE TRIGGER integration_events_no_update
BEFORE UPDATE ON integration_events BEGIN
    SELECT RAISE(ABORT, 'integration events are append-only');
END;

CREATE TRIGGER integration_events_no_delete
BEFORE DELETE ON integration_events BEGIN
    SELECT RAISE(ABORT, 'integration events are append-only');
END;
