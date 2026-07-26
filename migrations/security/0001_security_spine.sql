PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

-- Roadmap PH-3 security-spine store (PH-3-owned; DEP-RPH3 §2 boundary — NOT the frozen runtime-state
-- DB, R1 preserved). This RPH3-T3 migration carries the APPROVAL domain only (CMP-APPROVAL sole
-- writer). It is a BOUNDED, RECORDED deviation from DEP-RPH3 §3/§3.1's single all-tables 0001: the
-- permission/tool/watchdog schemas are T2/T5/WIR work outside the T3 boundary, so they arrive in later
-- SHA-pinned migrations. Rationale + reconciliation debt: docs/planning/RPH3-T3-IMPLEMENTATION-NOTE.md.

-- CTR-APPROVAL-RECORD: bound / expiring / revocable approvals. `state` is the record's current state;
-- `commit_state` marks whether that state is authoritative (XSC-RPH3 Class-1: a mutation is PENDING and
-- non-authoritative until its completion audit is durable). Readers honor only COMMITTED rows.
CREATE TABLE approval_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    approval_id TEXT NOT NULL UNIQUE,
    state TEXT NOT NULL CHECK (state IN ('PENDING', 'GRANTED', 'DENIED', 'CONSUMED', 'REVOKED', 'EXPIRED')),
    commit_state TEXT NOT NULL CHECK (commit_state IN ('PENDING', 'COMMITTED')),
    prior_state TEXT CHECK (prior_state IN ('PENDING', 'GRANTED', 'DENIED', 'CONSUMED', 'REVOKED', 'EXPIRED')),
    task_id TEXT NOT NULL,
    tool TEXT NOT NULL,
    action TEXT NOT NULL,
    resource TEXT,
    scope TEXT NOT NULL,
    purpose TEXT NOT NULL,
    consequences TEXT NOT NULL,
    autonomy_level TEXT NOT NULL,
    repetition_limit INTEGER NOT NULL CHECK (repetition_limit >= 1),
    uses_consumed INTEGER NOT NULL DEFAULT 0 CHECK (uses_consumed >= 0),
    -- Destructive/irreversible or real-world external actions need a SEPARATE explicit confirmation
    -- at decision time beyond ordinary code-execution approval (01K §2.10-11).
    requires_confirmation INTEGER NOT NULL DEFAULT 0 CHECK (requires_confirmation IN (0, 1)),
    expires_at INTEGER NOT NULL,
    action_fingerprint TEXT,
    created_ts INTEGER NOT NULL,
    updated_ts INTEGER NOT NULL
);

CREATE TABLE approval_queue (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    approval_id TEXT NOT NULL UNIQUE,
    enqueued_ts INTEGER NOT NULL
);

-- Operation-intent table (XSC-RPH3 §2/§3.1). `op_key` is the immutable join key K; `requested_action`
-- deterministically encodes the target transition for roll-forward. Class-1 approval operations only.
CREATE TABLE approval_intents (
    op_key TEXT PRIMARY KEY,
    operation_class INTEGER NOT NULL CHECK (operation_class IN (1, 2, 3)),
    domain TEXT NOT NULL,
    target_ref TEXT,
    requested_action TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'COMMITTED', 'ABORTED', 'UNCERTAIN', 'QUARANTINED')),
    reconciliation_state TEXT NOT NULL CHECK (reconciliation_state IN ('NONE', 'ROLL_FORWARD', 'ROLL_BACK', 'QUARANTINE')),
    audit_seq INTEGER,
    failure_code TEXT,
    quarantine_state TEXT,
    created_ts INTEGER NOT NULL,
    updated_ts INTEGER NOT NULL,
    completed_ts INTEGER
);

CREATE INDEX idx_approval_intents_status ON approval_intents (status);
CREATE INDEX idx_approval_intents_class_status ON approval_intents (operation_class, status);
CREATE INDEX idx_approval_intents_target ON approval_intents (target_ref);
