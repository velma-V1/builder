PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE project_generations (
    project_id TEXT PRIMARY KEY,
    last_generation INTEGER NOT NULL CHECK (last_generation >= 0)
);

CREATE TABLE contract_activations (
    project_id TEXT NOT NULL,
    contract_id TEXT NOT NULL,
    contract_version INTEGER NOT NULL CHECK (contract_version > 0),
    schema_version TEXT NOT NULL,
    generation INTEGER NOT NULL CHECK (generation > 0),
    content_hash TEXT NOT NULL CHECK (length(content_hash) = 64),
    runtime_status TEXT NOT NULL CHECK (runtime_status IN ('ACTIVE', 'SUPERSEDED', 'DISABLED', 'ROLLED_BACK')),
    canonical_json BLOB NOT NULL,
    validation_report_json TEXT NOT NULL,
    impact_report_json TEXT NOT NULL,
    policy_decision_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    rollback_contract_version INTEGER,
    activated_at TEXT NOT NULL,
    PRIMARY KEY (project_id, contract_id, contract_version),
    UNIQUE (project_id, generation)
);

CREATE TABLE active_contracts (
    project_id TEXT NOT NULL,
    contract_id TEXT NOT NULL,
    contract_version INTEGER NOT NULL,
    generation INTEGER NOT NULL,
    schema_version TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
    PRIMARY KEY (project_id, contract_id),
    FOREIGN KEY (project_id, contract_id, contract_version)
      REFERENCES contract_activations(project_id, contract_id, contract_version)
);

CREATE TABLE activation_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    contract_id TEXT NOT NULL,
    generation INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TRIGGER activation_events_no_update
BEFORE UPDATE ON activation_events
BEGIN SELECT RAISE(ABORT, 'activation_events are append-only'); END;

CREATE TRIGGER activation_events_no_delete
BEFORE DELETE ON activation_events
BEGIN SELECT RAISE(ABORT, 'activation_events are append-only'); END;
