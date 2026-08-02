CREATE TABLE task_requests (
    task_id TEXT PRIMARY KEY REFERENCES tasks(task_id),
    project_ref TEXT NOT NULL,
    workstream_id TEXT NOT NULL,
    description TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'normal',
    model_preference TEXT,
    expected_result TEXT,
    submitted_by TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE
);
