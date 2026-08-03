CREATE TABLE evidence_packages (
    package_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    run_id TEXT NOT NULL UNIQUE REFERENCES worker_runs(run_id),
    package_json TEXT NOT NULL,
    package_digest TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('PASSED', 'FAILED')),
    created_at TEXT NOT NULL
);

CREATE INDEX evidence_packages_task_id ON evidence_packages(task_id);

CREATE TRIGGER evidence_packages_no_update
BEFORE UPDATE ON evidence_packages
BEGIN SELECT RAISE(ABORT, 'evidence_packages are append-only'); END;

CREATE TRIGGER evidence_packages_no_delete
BEFORE DELETE ON evidence_packages
BEGIN SELECT RAISE(ABORT, 'evidence_packages are append-only'); END;

-- Only created when the corresponding evidence package's outcome is PASSED.
CREATE TABLE promotion_manifests (
    manifest_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    run_id TEXT NOT NULL UNIQUE REFERENCES worker_runs(run_id),
    manifest_json TEXT NOT NULL,
    manifest_digest TEXT NOT NULL,
    base_sha TEXT NOT NULL,
    branch_ref TEXT NOT NULL,
    checkpoint_commit_sha TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX promotion_manifests_task_id ON promotion_manifests(task_id);

CREATE TRIGGER promotion_manifests_no_update
BEFORE UPDATE ON promotion_manifests
BEGIN SELECT RAISE(ABORT, 'promotion_manifests are append-only'); END;

CREATE TRIGGER promotion_manifests_no_delete
BEFORE DELETE ON promotion_manifests
BEGIN SELECT RAISE(ABORT, 'promotion_manifests are append-only'); END;

-- Audit trail of every promotion attempt (including automatic rollbacks and rejections),
-- independent of factory.audit's hash-chained log -- this is the task-scoped promotion history.
CREATE TABLE promotion_records (
    promotion_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    run_id TEXT NOT NULL REFERENCES worker_runs(run_id),
    approval_card_id TEXT NOT NULL,
    decided_by TEXT NOT NULL,
    promoted_branch TEXT,
    promoted_commit_sha TEXT,
    outcome TEXT NOT NULL CHECK (outcome IN ('PROMOTED', 'ROLLED_BACK', 'REJECTED')),
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX promotion_records_task_id ON promotion_records(task_id);

CREATE TRIGGER promotion_records_no_update
BEFORE UPDATE ON promotion_records
BEGIN SELECT RAISE(ABORT, 'promotion_records are append-only'); END;

CREATE TRIGGER promotion_records_no_delete
BEFORE DELETE ON promotion_records
BEGIN SELECT RAISE(ABORT, 'promotion_records are append-only'); END;
