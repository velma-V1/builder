"""Security-spine persistence for CMP-PERM (roadmap PH-3, RPH3-T2).

Realizes the permission domain of the PH-3 security-spine store as the second ordered per-domain
migration (``0002_permission.sql``, DEP-RPH3 §3). CMP-PERM is the **sole writer** of
``permission_grants`` and ``permission_intents`` (R1-analogue for this domain, DEP-RPH3 §4A): the
writable connection is held in the private ``_PermissionWriter`` and never exported; consumers
get a read-only reader. A structural SQLite authorizer denies the writer any write outside its two
tables — including the approval domain's tables — so cross-domain isolation is structural.

The runner owns only the permission migration; a valid-versioned file of another domain (the
approval ``0001``) is skipped here and applied by that domain's runner (shared dir).
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from factory.contracts.activation.store import (
    _MIGRATION_FILENAME,
    _apply_single_migration,
    _reader_authorizer,
    _table_exists,
)
from factory.permission.errors import PermissionError
from factory.permission.models import (
    CommitState,
    PermissionClass,
    PermissionGrant,
    PermissionState,
)

_EXPECTED_MIGRATION_HASHES: Mapping[str, str] = {
    "0002_permission.sql": "a65d227d9683eb060c834ae8b3cb65f33186ba37420b4065eec8623f8ded88cb",
}

_PERMISSION_WRITE_TABLES = frozenset({"permission_grants", "permission_intents"})

_WRITE_ACTIONS = frozenset({sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE})

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


def _permission_writer_authorizer(
    action: int, arg1: str | None, arg2: str | None, db_name: str | None, trigger_name: str | None
) -> int:
    """Permit DML only on the two permission tables; deny all DDL / cross-table writes."""
    if action in _WRITE_ACTIONS:
        return sqlite3.SQLITE_OK if arg1 in _PERMISSION_WRITE_TABLES else sqlite3.SQLITE_DENY
    if action in _WRITER_DENIED_ACTIONS:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def apply_permission_migrations(database_path: Path, migrations_root: Path) -> None:
    """Apply the permission migration transactionally with SHA-256 pinning (like CMP-ORCH)."""
    files = sorted(migrations_root.glob("*.sql"))
    if not files:
        raise PermissionError(
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
                raise PermissionError(
                    "MIGRATION_MALFORMED", f"malformed migration filename: {path.name}"
                )
            version = int(match.group(1))
            # Shared security-spine dir: this runner owns only the permission migration(s); another
            # domain's valid-versioned file (approval's 0001) is applied by that domain's runner.
            if path.name not in _EXPECTED_MIGRATION_HASHES:
                continue
            if version in applied:
                continue

            content = path.read_bytes()
            actual = hashlib.sha256(content).hexdigest()
            expected = _EXPECTED_MIGRATION_HASHES.get(path.name)
            if expected is None or actual != expected:
                raise PermissionError(
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
                raise PermissionError(
                    "MIGRATION_FAILED", f"migration {path.name} failed to apply: {exc}"
                ) from exc
            applied.add(version)
    finally:
        connection.close()


def audit_completion_seq(audit_database_path: Path, op_key: str) -> int | None:
    """Sequence of the COMPLETION audit for ``op_key`` if durable, else ``None`` (read-only)."""
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


_SELECT_BY_ID_SQL = (
    "SELECT grant_id, task_id, tool, action, permission_class, resource, scope, purpose, "
    "grant_fingerprint, expires_at, state, commit_state, created_ts, updated_ts "
    "FROM permission_grants WHERE grant_id = ?"
)
_SELECT_EXPIRABLE_SQL = (
    "SELECT grant_id, task_id, tool, action, permission_class, resource, scope, purpose, "
    "grant_fingerprint, expires_at, state, commit_state, created_ts, updated_ts "
    "FROM permission_grants WHERE commit_state = 'COMMITTED' AND state = 'ACTIVE' "
    "AND expires_at <= ? ORDER BY expires_at, grant_id"
)
_SELECT_ACTIVE_FOR_TASK_SQL = (
    "SELECT grant_id, task_id, tool, action, permission_class, resource, scope, purpose, "
    "grant_fingerprint, expires_at, state, commit_state, created_ts, updated_ts "
    "FROM permission_grants WHERE task_id = ? AND state = 'ACTIVE' AND commit_state = 'COMMITTED' "
    "ORDER BY created_ts, grant_id"
)


def _row_to_grant(row: sqlite3.Row) -> PermissionGrant:
    return PermissionGrant(
        grant_id=str(row["grant_id"]),
        task_id=str(row["task_id"]),
        tool=str(row["tool"]),
        action=str(row["action"]),
        permission_class=PermissionClass(row["permission_class"]),
        resource=None if row["resource"] is None else str(row["resource"]),
        scope=str(row["scope"]),
        purpose=str(row["purpose"]),
        grant_fingerprint=str(row["grant_fingerprint"]),
        expires_at=int(row["expires_at"]),
        state=PermissionState(row["state"]),
        commit_state=CommitState(row["commit_state"]),
        created_ts=int(row["created_ts"]),
        updated_ts=int(row["updated_ts"]),
    )


@dataclass(frozen=True, slots=True)
class PendingIntent:
    """A non-terminal (``PENDING``) operation-intent row, for startup reconciliation."""

    op_key: str
    grant_id: str
    verb: str


@dataclass(frozen=True, slots=True)
class SQLitePermissionReader:
    """Read-only view over the permission domain (mode=ro + reader authorizer)."""

    database_path: Path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(f"file:{self.database_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.set_authorizer(_reader_authorizer)
        return connection

    def get_grant(self, grant_id: str) -> PermissionGrant | None:
        connection = self._connect()
        try:
            row = connection.execute(_SELECT_BY_ID_SQL, (grant_id,)).fetchone()
        finally:
            connection.close()
        return _row_to_grant(row) if row is not None else None

    def list_active_for_task(self, task_id: str) -> tuple[PermissionGrant, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(_SELECT_ACTIVE_FOR_TASK_SQL, (task_id,)).fetchall()
        finally:
            connection.close()
        return tuple(_row_to_grant(r) for r in rows)

    def list_expirable(self, now_ts: int) -> tuple[PermissionGrant, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(_SELECT_EXPIRABLE_SQL, (now_ts,)).fetchall()
        finally:
            connection.close()
        return tuple(_row_to_grant(r) for r in rows)

    def list_pending_intents(self) -> tuple[PendingIntent, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT op_key, target_ref, requested_action FROM permission_intents "
                "WHERE status = 'PENDING' ORDER BY created_ts, op_key"
            ).fetchall()
        finally:
            connection.close()
        return tuple(
            PendingIntent(
                op_key=str(r["op_key"]),
                grant_id=str(r["target_ref"]),
                verb=str(r["requested_action"]),
            )
            for r in rows
        )


__all__ = [
    "PendingIntent",
    "SQLitePermissionReader",
    "apply_permission_migrations",
    "audit_completion_seq",
]
