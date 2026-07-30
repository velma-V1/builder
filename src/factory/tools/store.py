"""Security-spine persistence for CMP-TOOLREG (roadmap PH-3, RPH3-T5).

Third ordered per-domain migration (``0003_tools.sql``, DEP-RPH3 §3). CMP-TOOLREG is **sole writer**
of ``tool_registry`` / ``tool_declarations`` / ``tool_quarantine`` / ``tool_registry_intents``
§4A): the writable connection is encapsulated in the private ``_ToolWriter`` and never exported. A
structural SQLite authorizer denies the writer any write outside its four tables (including
approval/permission tables). The runner owns only the tool migration; others are skipped.
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
from factory.tools.errors import ToolError
from factory.tools.models import (
    CommitState,
    OutputSchema,
    ToolDeclaration,
    ToolRecord,
    ToolState,
)

_EXPECTED_MIGRATION_HASHES: Mapping[str, str] = {
    "0003_tools.sql": "0050e74f80932fb58ea15d1f60f95661c7589d57dd623aad7691e26ea73a69b5",
}

_TOOL_WRITE_TABLES = frozenset(
    {"tool_registry", "tool_declarations", "tool_quarantine", "tool_registry_intents"}
)

_WRITE_ACTIONS = frozenset(
    {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE}
)

_WRITER_DENIED_ACTIONS = frozenset(
    {
        sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_CREATE_TEMP_INDEX,
        sqlite3.SQLITE_CREATE_TEMP_TABLE, sqlite3.SQLITE_CREATE_TEMP_TRIGGER,
        sqlite3.SQLITE_CREATE_TEMP_VIEW, sqlite3.SQLITE_CREATE_TRIGGER, sqlite3.SQLITE_CREATE_VIEW,
        sqlite3.SQLITE_DROP_INDEX, sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_DROP_TEMP_INDEX,
        sqlite3.SQLITE_DROP_TEMP_TABLE, sqlite3.SQLITE_DROP_TEMP_TRIGGER,
        sqlite3.SQLITE_DROP_TEMP_VIEW, sqlite3.SQLITE_DROP_TRIGGER, sqlite3.SQLITE_DROP_VIEW,
        sqlite3.SQLITE_ALTER_TABLE, sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH,
    }
)


def _tool_writer_authorizer(
    action: int, arg1: str | None, arg2: str | None, db_name: str | None, trigger_name: str | None
) -> int:
    if action in _WRITE_ACTIONS:
        return sqlite3.SQLITE_OK if arg1 in _TOOL_WRITE_TABLES else sqlite3.SQLITE_DENY
    if action in _WRITER_DENIED_ACTIONS:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def apply_tool_migrations(database_path: Path, migrations_root: Path) -> None:
    """Apply the tool migration transactionally with SHA-256 pinning (like CMP-ORCH)."""
    files = sorted(migrations_root.glob("*.sql"))
    if not files:
        raise ToolError(
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
                raise ToolError("MIGRATION_MALFORMED", f"malformed migration filename: {path.name}")
            version = int(match.group(1))
            if path.name not in _EXPECTED_MIGRATION_HASHES:
                continue  # another domain's migration; applied by that domain's runner
            if version in applied:
                continue
            content = path.read_bytes()
            actual = hashlib.sha256(content).hexdigest()
            expected = _EXPECTED_MIGRATION_HASHES.get(path.name)
            if expected is None or actual != expected:
                raise ToolError(
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
                raise ToolError(
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


_SELECT_RECORD_SQL = (
    "SELECT tool_id, version, state, commit_state, declaration_hash, provenance_source, "
    "provenance_checksum, license, failure_count, created_ts, updated_ts "
    "FROM tool_registry WHERE tool_id = ? AND version = ?"
)


def _row_to_record(row: sqlite3.Row) -> ToolRecord:
    return ToolRecord(
        tool_id=str(row["tool_id"]), version=str(row["version"]),
        state=ToolState(row["state"]), commit_state=CommitState(row["commit_state"]),
        declaration_hash=str(row["declaration_hash"]),
        provenance_source=str(row["provenance_source"]),
        provenance_checksum=str(row["provenance_checksum"]), license=str(row["license"]),
        failure_count=int(row["failure_count"]), created_ts=int(row["created_ts"]),
        updated_ts=int(row["updated_ts"]),
    )


@dataclass(frozen=True, slots=True)
class PendingIntent:
    op_key: str
    target_ref: str
    verb: str


@dataclass(frozen=True, slots=True)
class SQLiteToolReader:
    """Read-only view over the tool domain (mode=ro + reader authorizer)."""

    database_path: Path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(f"file:{self.database_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.set_authorizer(_reader_authorizer)
        return connection

    def get_record(self, tool_id: str, version: str) -> ToolRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(_SELECT_RECORD_SQL, (tool_id, version)).fetchone()
        finally:
            connection.close()
        return _row_to_record(row) if row is not None else None

    def get_declaration(self, tool_id: str, version: str) -> ToolDeclaration | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT declaration_json FROM tool_declarations WHERE tool_id = ? AND version = ?",
                (tool_id, version),
            ).fetchone()
        finally:
            connection.close()
        return None if row is None else ToolDeclaration.from_json(str(row["declaration_json"]))

    def get_output_schema(self, tool_id: str, version: str) -> OutputSchema | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT output_schema_json FROM tool_declarations "
                "WHERE tool_id = ? AND version = ?",
                (tool_id, version),
            ).fetchone()
        finally:
            connection.close()
        return None if row is None else OutputSchema.from_json(str(row["output_schema_json"]))

    def list_pending_intents(self) -> tuple[PendingIntent, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT op_key, target_ref, requested_action FROM tool_registry_intents "
                "WHERE status = 'PENDING' ORDER BY created_ts, op_key"
            ).fetchall()
        finally:
            connection.close()
        return tuple(
            PendingIntent(str(r["op_key"]), str(r["target_ref"]), str(r["requested_action"]))
            for r in rows
        )


__all__ = [
    "PendingIntent",
    "SQLiteToolReader",
    "apply_tool_migrations",
    "audit_completion_seq",
]
