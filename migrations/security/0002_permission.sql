PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- Shared security-spine version ledger (created by whichever domain migration applies first;
-- IF NOT EXISTS so this migration is valid both standalone and against the shared store).
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

-- Roadmap PH-3 security-spine store (PH-3-owned; DEP-RPH3 §2 boundary — NOT the frozen runtime-state
-- DB, R1 preserved). This RPH3-T2 migration carries the PERMISSION domain only (CMP-PERM sole writer),
-- as the second ordered per-domain SHA-pinned migration (DEP-RPH3 §3, operator-adopted model).

-- CTR-PERMISSION-GRANT: scoped / expiring / revocable least-privilege grants. `state` is the grant's
-- current state; `commit_state` marks whether that state is authoritative (XSC-RPH3 Class-1: a mutation
-- is PENDING and non-authoritative until its completion audit is durable). Readers honor only COMMITTED.
-- `resource` is the CANONICAL, validated relative path (or NULL for a non-path resource); a raw path is
-- never stored — PathAuthority canonicalizes + contains it before a grant is issued (path authority).
CREATE TABLE permission_grants (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    grant_id TEXT NOT NULL UNIQUE,
    state TEXT NOT NULL CHECK (state IN ('ACTIVE', 'REVOKED', 'EXPIRED')),
    commit_state TEXT NOT NULL CHECK (commit_state IN ('PENDING', 'COMMITTED')),
    prior_state TEXT CHECK (prior_state IN ('ACTIVE', 'REVOKED', 'EXPIRED')),
    task_id TEXT NOT NULL,
    tool TEXT NOT NULL,
    action TEXT NOT NULL,
    permission_class TEXT NOT NULL,
    resource TEXT,
    scope TEXT NOT NULL,
    purpose TEXT NOT NULL,
    grant_fingerprint TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    created_ts INTEGER NOT NULL,
    updated_ts INTEGER NOT NULL
);

-- Operation-intent table (XSC-RPH3 §2/§3.1). `op_key` is the immutable join key K; `requested_action`
-- deterministically encodes the target transition for roll-forward. Class-1 permission operations only.
CREATE TABLE permission_intents (
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

CREATE INDEX idx_permission_intents_status ON permission_intents (status);
CREATE INDEX idx_permission_intents_class_status ON permission_intents (operation_class, status);
CREATE INDEX idx_permission_intents_target ON permission_intents (target_ref);
