PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- Shared security-spine version ledger (IF NOT EXISTS so this migration composes with 0001/0002 in
-- canonical order and is also valid standalone).
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

-- Roadmap PH-3 security-spine store (PH-3-owned; DEP-RPH3 §2 boundary — NOT the frozen runtime-state
-- DB, R1 preserved). This RPH3-T5 migration carries the TOOL domain (CMP-TOOLREG sole writer), as the
-- third ordered per-domain SHA-pinned migration (DEP-RPH3 §3, operator-adopted model).

-- CTR-TOOL-DECLARATION registration: one row per (tool_id, version). Default-DENY — a tool absent here
-- is uncallable. `state` is the registry state; `commit_state` marks XSC-RPH3 Class-1 authority
-- (PENDING until the completion audit is durable). Provenance (source + integrity checksum + license)
-- is recorded for downloaded components (01K-AC-09). `failure_count` drives repeated-failure quarantine.
CREATE TABLE tool_registry (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_id TEXT NOT NULL,
    version TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('REGISTERED', 'QUARANTINED', 'RELEASED')),
    commit_state TEXT NOT NULL CHECK (commit_state IN ('PENDING', 'COMMITTED')),
    prior_state TEXT CHECK (prior_state IN ('REGISTERED', 'QUARANTINED', 'RELEASED')),
    declaration_hash TEXT NOT NULL,
    provenance_source TEXT NOT NULL,
    provenance_checksum TEXT NOT NULL,
    license TEXT NOT NULL,
    failure_count INTEGER NOT NULL DEFAULT 0 CHECK (failure_count >= 0),
    created_ts INTEGER NOT NULL,
    updated_ts INTEGER NOT NULL,
    UNIQUE (tool_id, version)
);

-- The complete tool declaration content (capabilities/inputs/outputs/side-effects/permission-classes/
-- env/resource-profile/failure-behavior), stored canonically as JSON, 1:1 with a registry row.
CREATE TABLE tool_declarations (
    tool_id TEXT NOT NULL,
    version TEXT NOT NULL,
    declaration_json TEXT NOT NULL,
    output_schema_json TEXT NOT NULL,
    created_ts INTEGER NOT NULL,
    PRIMARY KEY (tool_id, version)
);

-- Durable quarantine history (survives restart; no auto-release). A release records the review_ref.
CREATE TABLE tool_quarantine (
    quarantine_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_id TEXT NOT NULL,
    version TEXT NOT NULL,
    reason TEXT NOT NULL,
    review_ref TEXT,
    quarantined_ts INTEGER NOT NULL,
    released_ts INTEGER
);

-- Operation-intent table (XSC-RPH3 §2/§3.1). Class-1 tool-registry operations only.
CREATE TABLE tool_registry_intents (
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

CREATE INDEX idx_tool_registry_intents_status ON tool_registry_intents (status);
CREATE INDEX idx_tool_registry_intents_class_status ON tool_registry_intents (operation_class, status);
CREATE INDEX idx_tool_registry_intents_target ON tool_registry_intents (target_ref);
