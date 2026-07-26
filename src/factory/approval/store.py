"""Security-spine persistence for CMP-APPROVAL (roadmap PH-3, RPH3-T3).

Realizes the approval domain of the PH-3 security-spine store (DEP-RPH3 §3, incremental per-task
migration ``0001_security_spine.sql``). CMP-APPROVAL is the **sole writer** of ``approval_records``,
``approval_queue`` and ``approval_intents`` (the R1-analogue for this domain, DEP-RPH3 §4A): the
writable connection is encapsulated in the private ``_ApprovalWriter`` and never exported; consumers
get a read-only reader. A structural SQLite authorizer denies the writer any write outside its three
tables and denies the reader every write (mode=ro), so cross-domain isolation is enforced
structurally, not by convention.

The migration is applied under the exact PH-1 SHA-256-pinned transactional runner (as CMP-ORCH /
CMP-AUDITW do): a migration whose content does not match its pinned hash fails closed.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from factory.approval.errors import ApprovalError
from factory.approval.models import (
    ApprovalRecord,
    ApprovalState,
    CommitState,
)

# Reuse the exact PH-1 SHA-256-pinned transactional migration mechanics + the read-only authorizer.
from factory.contracts.activation.store import (
    _MIGRATION_FILENAME,
    _apply_single_migration,
    _reader_authorizer,
    _table_exists,
)

_EXPECTED_MIGRATION_HASHES: Mapping[str, str] = {
    "0001_security_spine.sql": "099ae959d6f06c6b944925af151d8fa8dd2b65fdffd63660cf2a4355b7878a51",
}

# The only tables CMP-APPROVAL may write (DEP-RPH3 §4A authorizer partition).
_APPROVAL_WRITE_TABLES = frozenset({"approval_records", "approval_queue", "approval_intents"})

_WRITE_ACTIONS = frozenset(
    {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE}
)

# DDL / schema-mutating actions the domain writer must never perform at runtime (migrations use a
# separate, un-authorized connection). Mirrors the reader's denied set minus the DML verbs.
_WRITER_DENIED_ACTIONS = frozenset(
    {
        sqlite3.SQLITE_CREATE_INDEX,
        sqlite3.SQLITE_CREATE_TABLE,
        sqlite3.SQLITE_CREATE_TEMP_INDEX,
        sqlite3.SQLITE_CREATE_TEMP_TABLE,
        sqlite3.SQLITE_CREATE_TEMP_TRIGGER,
        sqlite3.SQLITE_CREATE_TEMP_VIEW,
        sqlite3.SQLITE_CREATE_TRIGGER,
        sqlite3.SQLITE_CREATE_VIEW,
        sqlite3.SQLITE_DROP_INDEX,
        sqlite3.SQLITE_DROP_TABLE,
        sqlite3.SQLITE_DROP_TEMP_INDEX,
        sqlite3.SQLITE_DROP_TEMP_TABLE,
        sqlite3.SQLITE_DROP_TEMP_TRIGGER,
        sqlite3.SQLITE_DROP_TEMP_VIEW,
        sqlite3.SQLITE_DROP_TRIGGER,
        sqlite3.SQLITE_DROP_VIEW,
        sqlite3.SQLITE_ALTER_TABLE,
        sqlite3.SQLITE_ATTACH,
        sqlite3.SQLITE_DETACH,
    }
)


def _approval_writer_authorizer(
    action: int, arg1: str | None, arg2: str | None, db_name: str | None, trigger_name: str | None
) -> int:
    """Permit DML only on the three approval tables; deny all DDL / cross-table writes."""
    if action in _WRITE_ACTIONS:
        return sqlite3.SQLITE_OK if arg1 in _APPROVAL_WRITE_TABLES else sqlite3.SQLITE_DENY
    if action in _WRITER_DENIED_ACTIONS:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def apply_security_migrations(database_path: Path, migrations_root: Path) -> None:
    """Apply the security-spine migrations transactionally with SHA-256 pinning (like CMP-ORCH)."""
    files = sorted(migrations_root.glob("*.sql"))
    if not files:
        raise ApprovalError(
            "MIGRATION_MISSING", f"no security migrations found under {migrations_root}"
        )

    connection = sqlite3.connect(str(database_path))
    try:
        applied: set[int] = set()
        if _table_exists(connection, "schema_migrations"):
            applied = {
                int(r[0]) for r in connection.execute("SELECT version FROM schema_migrations")
            }

        for path in files:
            match = _MIGRATION_FILENAME.match(path.name)
            if not match:
                raise ApprovalError(
                    "MIGRATION_MALFORMED", f"malformed migration filename: {path.name}"
                )
            version = int(match.group(1))
            if version in applied:
                continue

            content = path.read_bytes()
            actual = hashlib.sha256(content).hexdigest()
            expected = _EXPECTED_MIGRATION_HASHES.get(path.name)
            if expected is None or actual != expected:
                raise ApprovalError(
                    "MIGRATION_INTEGRITY", f"migration integrity check failed for {path.name}"
                )
            try:
                _apply_single_migration(connection, content)
                connection.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (version, path.name),
                )
                connection.commit()
            except sqlite3.Error as exc:
                connection.rollback()
                raise ApprovalError(
                    "MIGRATION_FAILED", f"migration {path.name} failed to apply: {exc}"
                ) from exc
            applied.add(version)
    finally:
        connection.close()


# --- cross-store audit lookup (op_key is the sanctioned by-value link, XSC-RPH3 §2) ---------------


def audit_completion_seq(audit_database_path: Path, op_key: str) -> int | None:
    """Return the sequence of the COMPLETION audit for ``op_key`` if durable, else ``None``.

    Read-only over CMP-AUDITW's store (mode=ro + reader authorizer). The approval domain never
    writes the audit store; it only joins by ``op_key`` (the documented cross-store link).
    """
    connection = sqlite3.connect(f"file:{audit_database_path}?mode=ro", uri=True)
    connection.set_authorizer(_reader_authorizer)
    try:
        row = connection.execute(
            "SELECT sequence FROM audit_records WHERE op_key = ? AND record_kind = 'COMPLETION' "
            "ORDER BY sequence LIMIT 1",
            (op_key,),
        ).fetchone()
    finally:
        connection.close()
    return int(row[0]) if row is not None else None


# --- read-only reader -----------------------------------------------------------------------------

# Fully-literal SQL (no f-string interpolation) so static analysis needs no S608 exception — the
# reader never composes SQL from input (mirrors CMP-AUDITW's store convention).
_RECORD_COLUMNS = (
    "approval_id, task_id, tool, action, resource, scope, purpose, consequences, autonomy_level, "
    "repetition_limit, uses_consumed, requires_confirmation, expires_at, action_fingerprint, "
    "state, commit_state, created_ts, updated_ts"
)
_SELECT_BY_ID_SQL = (
    "SELECT approval_id, task_id, tool, action, resource, scope, purpose, consequences, "
    "autonomy_level, repetition_limit, uses_consumed, requires_confirmation, expires_at, "
    "action_fingerprint, state, commit_state, created_ts, updated_ts "
    "FROM approval_records WHERE approval_id = ?"
)
_SELECT_COMMITTED_PENDING_SQL = (
    "SELECT approval_id, task_id, tool, action, resource, scope, purpose, consequences, "
    "autonomy_level, repetition_limit, uses_consumed, requires_confirmation, expires_at, "
    "action_fingerprint, state, commit_state, created_ts, updated_ts "
    "FROM approval_records WHERE state = 'PENDING' AND commit_state = 'COMMITTED' "
    "ORDER BY created_ts, approval_id"
)
_SELECT_EXPIRABLE_SQL = (
    "SELECT approval_id, task_id, tool, action, resource, scope, purpose, consequences, "
    "autonomy_level, repetition_limit, uses_consumed, requires_confirmation, expires_at, "
    "action_fingerprint, state, commit_state, created_ts, updated_ts "
    "FROM approval_records WHERE commit_state = 'COMMITTED' AND state IN ('PENDING', 'GRANTED') "
    "AND expires_at <= ? ORDER BY expires_at, approval_id"
)


def _row_to_record(row: sqlite3.Row) -> ApprovalRecord:
    return ApprovalRecord(
        approval_id=str(row["approval_id"]),
        task_id=str(row["task_id"]),
        tool=str(row["tool"]),
        action=str(row["action"]),
        resource=None if row["resource"] is None else str(row["resource"]),
        scope=str(row["scope"]),
        purpose=str(row["purpose"]),
        consequences=str(row["consequences"]),
        autonomy_level=str(row["autonomy_level"]),
        repetition_limit=int(row["repetition_limit"]),
        uses_consumed=int(row["uses_consumed"]),
        requires_confirmation=bool(row["requires_confirmation"]),
        expires_at=int(row["expires_at"]),
        action_fingerprint=(
            None if row["action_fingerprint"] is None else str(row["action_fingerprint"])
        ),
        state=ApprovalState(row["state"]),
        commit_state=CommitState(row["commit_state"]),
        created_ts=int(row["created_ts"]),
        updated_ts=int(row["updated_ts"]),
    )


@dataclass(frozen=True, slots=True)
class PendingIntent:
    """A non-terminal (``PENDING``) operation-intent row, for startup reconciliation."""

    op_key: str
    approval_id: str
    verb: str


@dataclass(frozen=True, slots=True)
class SQLiteApprovalReader:
    """Read-only view over the approval domain (mode=ro + reader authorizer)."""

    database_path: Path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(f"file:{self.database_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.set_authorizer(_reader_authorizer)
        return connection

    def get_record(self, approval_id: str) -> ApprovalRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(_SELECT_BY_ID_SQL, (approval_id,)).fetchone()
        finally:
            connection.close()
        return _row_to_record(row) if row is not None else None

    def list_committed_pending(self) -> tuple[ApprovalRecord, ...]:
        """Authoritative approvals still awaiting an operator decision (state+commit settled)."""
        connection = self._connect()
        try:
            rows = connection.execute(_SELECT_COMMITTED_PENDING_SQL).fetchall()
        finally:
            connection.close()
        return tuple(_row_to_record(r) for r in rows)

    def list_expirable(self, now_ts: int) -> tuple[ApprovalRecord, ...]:
        """Committed non-terminal approvals whose expiry has passed (auto-expiry sweep set)."""
        connection = self._connect()
        try:
            rows = connection.execute(_SELECT_EXPIRABLE_SQL, (now_ts,)).fetchall()
        finally:
            connection.close()
        return tuple(_row_to_record(r) for r in rows)

    def list_pending_intents(self) -> tuple[PendingIntent, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT op_key, target_ref, requested_action FROM approval_intents "
                "WHERE status = 'PENDING' ORDER BY created_ts, op_key"
            ).fetchall()
        finally:
            connection.close()
        return tuple(
            PendingIntent(
                op_key=str(r["op_key"]),
                approval_id=str(r["target_ref"]),
                verb=str(r["requested_action"]),
            )
            for r in rows
        )

    def queue_ids(self) -> tuple[str, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT approval_id FROM approval_queue ORDER BY enqueued_ts, queue_id"
            ).fetchall()
        finally:
            connection.close()
        return tuple(str(r["approval_id"]) for r in rows)


__all__ = [
    "PendingIntent",
    "SQLiteApprovalReader",
    "apply_security_migrations",
    "audit_completion_seq",
]
