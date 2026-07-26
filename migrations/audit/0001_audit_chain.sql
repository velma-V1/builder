PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

-- Tamper-evident privileged-action audit chain (roadmap PH-3, CMP-AUDITW; 01K-AC-19/20).
-- Append-only + hash-chained. An operation (op_key) may carry up to two lifecycle records:
-- one INTENT (Class-3 pre-execution) and one COMPLETION (post-execution / Class-1/2 sole record),
-- enforced by UNIQUE(op_key, record_kind) (XSC-RPH3 §2). The writer (CMP-AUDITW) is the sole
-- appender and computes sequence / predecessor_hash / record_hash itself (forge-resistance);
-- the triggers make UPDATE/DELETE fail closed even through a writable connection.
CREATE TABLE audit_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sequence INTEGER NOT NULL UNIQUE CHECK (sequence >= 1),
    op_key TEXT NOT NULL,
    record_kind TEXT NOT NULL CHECK (record_kind IN ('INTENT', 'COMPLETION')),
    operation_class INTEGER NOT NULL CHECK (operation_class IN (1, 2, 3)),
    actor TEXT NOT NULL,
    action_class TEXT NOT NULL,
    target_ref TEXT,
    payload_hash TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    predecessor_hash TEXT NOT NULL,
    record_hash TEXT NOT NULL UNIQUE,
    signature TEXT,
    UNIQUE (op_key, record_kind)
);

CREATE INDEX idx_audit_op_key ON audit_records (op_key);

CREATE TRIGGER audit_records_no_update
BEFORE UPDATE ON audit_records
BEGIN SELECT RAISE(ABORT, 'audit_records are append-only'); END;

CREATE TRIGGER audit_records_no_delete
BEFORE DELETE ON audit_records
BEGIN SELECT RAISE(ABORT, 'audit_records are append-only'); END;
