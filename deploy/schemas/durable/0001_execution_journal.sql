-- Durable execution / idempotency journal (Stage-3 template — UNAPPLIED).
--
-- This schema is a TEMPLATE for the live durable store. It is NOT applied to any live database
-- during preparation and MUST NOT be activated until the SQLite compliance gate passes
-- (engine >= 3.51.3 or an approved backport) AND separate operator authorization is given.
--
-- Design intent:
--   * idempotent writes  -> a repeated (task_id, attempt_seq) is a no-op, not a duplicate row;
--   * replay-safe        -> the journal records terminal outcomes so a crash-then-restart can
--                           reconcile without blindly re-executing an already-terminal attempt;
--   * single authoritative writer -> enforced in application code, mirrored by the UNIQUE key here.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS execution_journal (
    task_id        TEXT    NOT NULL,
    attempt_seq    INTEGER NOT NULL,
    route_key      TEXT    NOT NULL,
    status         TEXT    NOT NULL CHECK (status IN ('RUNNING', 'SUCCEEDED', 'FAILED', 'STALE')),
    process_epoch  INTEGER NOT NULL DEFAULT 0,
    tokens         INTEGER NOT NULL DEFAULT 0 CHECK (tokens >= 0),
    created_at_ms  INTEGER NOT NULL,
    updated_at_ms  INTEGER NOT NULL,
    PRIMARY KEY (task_id, attempt_seq)
);

-- Idempotency guard: a given (task_id, attempt_seq) is unique, so a replayed write collides rather
-- than inserting a duplicate. Application code uses INSERT ... ON CONFLICT DO NOTHING/UPDATE.
CREATE UNIQUE INDEX IF NOT EXISTS ux_execution_journal_attempt
    ON execution_journal (task_id, attempt_seq);

-- Recovery lookup: find non-terminal attempts for a process epoch to reconcile on restart.
CREATE INDEX IF NOT EXISTS ix_execution_journal_recovery
    ON execution_journal (status, process_epoch);
