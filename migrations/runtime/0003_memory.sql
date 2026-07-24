CREATE TABLE memory_records (
    record_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    memory_class TEXT NOT NULL CHECK (memory_class = 'PROJECT_AUTHORITY'),
    status TEXT NOT NULL,
    source TEXT NOT NULL,
    scope TEXT NOT NULL,
    summary TEXT NOT NULL CHECK (length(summary) <= 65536),
    evidence_ref TEXT,
    supersedes TEXT REFERENCES memory_records(record_id),
    created_at TEXT NOT NULL
);
