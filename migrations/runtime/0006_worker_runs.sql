CREATE TABLE worker_runs (
    run_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    attempt INTEGER NOT NULL CHECK (attempt >= 1),
    sandbox_path TEXT NOT NULL,
    branch_ref TEXT NOT NULL,
    base_sha TEXT NOT NULL,
    work_order_json TEXT NOT NULL,
    model_route_token TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL,
    finished_at TEXT,
    outcome TEXT,
    reason TEXT
);

CREATE INDEX worker_runs_task_id ON worker_runs(task_id);

CREATE TABLE worker_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES worker_runs(run_id),
    sequence INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    UNIQUE (run_id, sequence)
);

CREATE TRIGGER worker_events_no_update
BEFORE UPDATE ON worker_events
BEGIN SELECT RAISE(ABORT, 'worker_events are append-only'); END;

CREATE TRIGGER worker_events_no_delete
BEFORE DELETE ON worker_events
BEGIN SELECT RAISE(ABORT, 'worker_events are append-only'); END;

CREATE TABLE worker_artifacts (
    artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES worker_runs(run_id),
    artifact_path TEXT NOT NULL,
    content_digest TEXT NOT NULL,
    media_type TEXT NOT NULL
);

CREATE TRIGGER worker_artifacts_no_update
BEFORE UPDATE ON worker_artifacts
BEGIN SELECT RAISE(ABORT, 'worker_artifacts are append-only'); END;

CREATE TRIGGER worker_artifacts_no_delete
BEFORE DELETE ON worker_artifacts
BEGIN SELECT RAISE(ABORT, 'worker_artifacts are append-only'); END;
