"""SHA-pinned WIR journal migration and read-only intervention view."""

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
from factory.watchdog.errors import WatchdogError
from factory.watchdog.models import (
    InterventionOutcome,
    InterventionRecord,
    InterventionStatus,
    ReconciliationState,
)

_EXPECTED_MIGRATION_HASHES: Mapping[str, str] = {
    "0004_watchdog.sql": "21ad8fa85055e1e55b703a55865a442b4e1af907c39baf668f7fcf34a4488b80",
}

_INTERVENTION_WRITE_TABLES = frozenset({"watchdog_intervention_journal"})
_WRITE_ACTIONS = frozenset(
    {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE}
)
_WRITER_DENIED_ACTIONS = frozenset(
    {
        sqlite3.SQLITE_CREATE_INDEX,
        sqlite3.SQLITE_CREATE_TABLE,
        sqlite3.SQLITE_CREATE_TRIGGER,
        sqlite3.SQLITE_CREATE_VIEW,
        sqlite3.SQLITE_DROP_INDEX,
        sqlite3.SQLITE_DROP_TABLE,
        sqlite3.SQLITE_DROP_TRIGGER,
        sqlite3.SQLITE_DROP_VIEW,
        sqlite3.SQLITE_ALTER_TABLE,
        sqlite3.SQLITE_ATTACH,
        sqlite3.SQLITE_DETACH,
    }
)


def _intervention_writer_authorizer(
    action: int,
    arg1: str | None,
    arg2: str | None,
    db_name: str | None,
    trigger_name: str | None,
) -> int:
    del arg2, db_name, trigger_name
    if action in _WRITE_ACTIONS:
        return (
            sqlite3.SQLITE_OK
            if arg1 in _INTERVENTION_WRITE_TABLES
            else sqlite3.SQLITE_DENY
        )
    if action in _WRITER_DENIED_ACTIONS:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def apply_watchdog_migration(database_path: Path, migrations_root: Path) -> None:
    files = sorted(migrations_root.glob("*.sql"))
    if not files:
        raise WatchdogError(
            "MIGRATION_MISSING", f"no security migrations found under {migrations_root}"
        )
    connection = sqlite3.connect(str(database_path))
    try:
        applied: set[int] = set()
        if _table_exists(connection, "schema_migrations"):
            applied = {
                int(row[0])
                for row in connection.execute("SELECT version FROM schema_migrations")
            }
        for path in files:
            match = _MIGRATION_FILENAME.match(path.name)
            if not match:
                raise WatchdogError(
                    "MIGRATION_MALFORMED", f"malformed migration filename: {path.name}"
                )
            if path.name not in _EXPECTED_MIGRATION_HASHES:
                continue
            version = int(match.group(1))
            if version in applied:
                continue
            content = path.read_bytes()
            actual = hashlib.sha256(content).hexdigest()
            if actual != _EXPECTED_MIGRATION_HASHES[path.name]:
                raise WatchdogError(
                    "MIGRATION_INTEGRITY",
                    f"migration integrity check failed for {path.name}",
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
                raise WatchdogError(
                    "MIGRATION_FAILED", f"migration {path.name} failed to apply: {exc}"
                ) from exc
            applied.add(version)
    finally:
        connection.close()


def _row_to_record(row: sqlite3.Row) -> InterventionRecord:
    outcome = row["result_outcome"]
    return InterventionRecord(
        op_key=str(row["op_key"]),
        operation_class=int(row["operation_class"]),
        target_ref=str(row["target_ref"]),
        requested_action=str(row["requested_action"]),
        status=InterventionStatus(row["status"]),
        reconciliation_state=ReconciliationState(row["reconciliation_state"]),
        request_hash=str(row["request_hash"]),
        expected_state=str(row["expected_state"]),
        desired_state=None if row["desired_state"] is None else str(row["desired_state"]),
        result_outcome=None if outcome is None else InterventionOutcome(outcome),
        result_cause=None if row["result_cause"] is None else str(row["result_cause"]),
        audit_seq=None if row["audit_seq"] is None else int(row["audit_seq"]),
        failure_code=None if row["failure_code"] is None else str(row["failure_code"]),
        created_ts=int(row["created_ts"]),
        updated_ts=int(row["updated_ts"]),
        completed_ts=(
            None if row["completed_ts"] is None else int(row["completed_ts"])
        ),
    )


@dataclass(frozen=True, slots=True)
class SQLiteInterventionReader:
    database_path: Path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(f"file:{self.database_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.set_authorizer(_reader_authorizer)
        return connection

    def get(self, op_key: str) -> InterventionRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM watchdog_intervention_journal WHERE op_key = ?",
                (op_key,),
            ).fetchone()
        finally:
            connection.close()
        return None if row is None else _row_to_record(row)

    def pending(self) -> tuple[InterventionRecord, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM watchdog_intervention_journal "
                "WHERE status IN ('PENDING', 'UNCERTAIN') ORDER BY created_ts, op_key"
            ).fetchall()
        finally:
            connection.close()
        return tuple(_row_to_record(row) for row in rows)


__all__ = ["SQLiteInterventionReader", "apply_watchdog_migration"]
