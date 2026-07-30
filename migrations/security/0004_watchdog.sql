PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

-- Internal WIR durability journal. CMP-WATCH remains an independent read-only observer; only the
-- orchestrator-side receiver writes this table through its structurally bounded private writer.
CREATE TABLE watchdog_intervention_journal (
    op_key TEXT PRIMARY KEY,
    operation_class INTEGER NOT NULL CHECK (operation_class IN (1, 2, 3)),
    domain TEXT NOT NULL CHECK (domain = 'watchdog'),
    target_ref TEXT NOT NULL,
    requested_action TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('PENDING', 'COMMITTED', 'ABORTED', 'UNCERTAIN', 'QUARANTINED')
    ),
    reconciliation_state TEXT NOT NULL CHECK (
        reconciliation_state IN ('NONE', 'ROLL_FORWARD', 'ROLL_BACK', 'QUARANTINE')
    ),
    request_hash TEXT NOT NULL,
    expected_state TEXT NOT NULL,
    desired_state TEXT,
    result_outcome TEXT CHECK (result_outcome IN ('APPLIED', 'REJECTED', 'INERT', 'FAILED')),
    result_cause TEXT,
    audit_seq INTEGER,
    failure_code TEXT,
    created_ts INTEGER NOT NULL,
    updated_ts INTEGER NOT NULL,
    completed_ts INTEGER
);

CREATE INDEX idx_watchdog_intervention_status
    ON watchdog_intervention_journal (status);
CREATE INDEX idx_watchdog_intervention_target
    ON watchdog_intervention_journal (target_ref);
