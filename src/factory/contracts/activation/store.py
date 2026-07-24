from __future__ import annotations

import hashlib
import re
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from factory.contracts.errors import ContractError
from factory.contracts.models import ActivationRecord, ErrorCode

# Pinned integrity hashes for each migration file. A migration whose content does not match
# its pinned hash fails closed rather than being silently applied (defends against tampering
# with a file that is otherwise just a git-tracked, human-editable SQL script).
_EXPECTED_MIGRATION_HASHES: Mapping[str, str] = {
    "0001_activation_store.sql": "21d41f6d954fc92ef15c114ee847b81ca8d17eb83d5895823fd57ca6f337ffa1",
}

_MIGRATION_FILENAME = re.compile(r"^(\d+)_.*\.sql$")

_DENIED_AUTHORIZER_ACTIONS = frozenset(
    {
        sqlite3.SQLITE_INSERT,
        sqlite3.SQLITE_UPDATE,
        sqlite3.SQLITE_DELETE,
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

# Pragma names that change database/connection state. Read-only introspection pragmas that
# happen to take an argument (e.g. `table_info(some_table)`) are deliberately not in this set.
_WRITABLE_PRAGMA_NAMES = frozenset(
    {
        "journal_mode",
        "synchronous",
        "foreign_keys",
        "user_version",
        "application_id",
        "auto_vacuum",
        "cache_size",
        "locking_mode",
        "page_size",
        "secure_delete",
        "temp_store",
        "wal_checkpoint",
        "writable_schema",
        "schema_version",
        "recursive_triggers",
        "busy_timeout",
        "case_sensitive_like",
        "defer_foreign_keys",
        "ignore_check_constraints",
        "legacy_alter_table",
        "mmap_size",
        "query_only",
        "optimize",
        "incremental_vacuum",
    }
)


def _reader_authorizer(
    action: int, arg1: str | None, arg2: str | None, db_name: str | None, trigger_name: str | None
) -> int:
    if action in _DENIED_AUTHORIZER_ACTIONS:
        return sqlite3.SQLITE_DENY
    is_writable_pragma_set = (
        action == sqlite3.SQLITE_PRAGMA
        and arg1 is not None
        and arg2
        and arg1.lower() in _WRITABLE_PRAGMA_NAMES
    )
    if is_writable_pragma_set:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone()
    return row is not None


def _apply_single_migration(connection: sqlite3.Connection, content: bytes) -> None:
    script = content.decode("utf-8")
    lines = script.splitlines(keepends=True)
    remainder_start = 0
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "" or stripped.upper().startswith("PRAGMA"):
            if stripped.upper().startswith("PRAGMA"):
                connection.execute(stripped.rstrip(";"))
            remainder_start = index + 1
        else:
            break
    remainder = "".join(lines[remainder_start:])
    connection.executescript(f"BEGIN;\n{remainder}\nCOMMIT;")


def apply_migrations(database_path: Path, migrations_root: Path) -> None:
    files = sorted(migrations_root.glob("*.sql"))
    if not files:
        message = f"no activation store migrations found under {migrations_root}"
        raise ContractError(ErrorCode.PARSE_REJECTED, message)

    connection = sqlite3.connect(str(database_path))
    try:
        applied_versions: set[int] = set()
        if _table_exists(connection, "schema_migrations"):
            applied_versions = {
                row[0] for row in connection.execute("SELECT version FROM schema_migrations")
            }

        for path in files:
            match = _MIGRATION_FILENAME.match(path.name)
            if not match:
                raise ContractError(
                    ErrorCode.PARSE_REJECTED, f"malformed migration filename: {path.name}"
                )
            version = int(match.group(1))
            if version in applied_versions:
                continue

            content = path.read_bytes()
            actual_hash = hashlib.sha256(content).hexdigest()
            expected_hash = _EXPECTED_MIGRATION_HASHES.get(path.name)
            if expected_hash is None or actual_hash != expected_hash:
                raise ContractError(
                    ErrorCode.SECURITY_DENIED,
                    f"migration integrity check failed for {path.name}",
                )

            _apply_single_migration(connection, content)
            connection.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")),
            )
            connection.commit()
            applied_versions.add(version)
    finally:
        connection.close()


class ActivationReader(Protocol):
    def get_active(self, project_id: str, contract_id: str) -> ActivationRecord | None: ...
    def get_generation(self, project_id: str) -> int: ...


def _connect_readonly(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.set_authorizer(_reader_authorizer)
    return connection


@dataclass(frozen=True, slots=True)
class SQLiteActivationReader:
    database_path: Path

    def get_active(self, project_id: str, contract_id: str) -> ActivationRecord | None:
        connection = _connect_readonly(self.database_path)
        try:
            row = connection.execute(
                "SELECT contract_version, schema_version, generation, content_hash "
                "FROM active_contracts WHERE project_id = ? AND contract_id = ? AND enabled = 1",
                (project_id, contract_id),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        return ActivationRecord(
            project_id=project_id,
            contract_id=contract_id,
            contract_version=row["contract_version"],
            schema_version=row["schema_version"],
            generation=row["generation"],
            content_hash=row["content_hash"],
            runtime_status="ACTIVE",
        )

    def get_generation(self, project_id: str) -> int:
        connection = _connect_readonly(self.database_path)
        try:
            row = connection.execute(
                "SELECT last_generation FROM project_generations WHERE project_id = ?",
                (project_id,),
            ).fetchone()
        finally:
            connection.close()
        return int(row["last_generation"]) if row is not None else 0


@dataclass(frozen=True, slots=True)
class _SQLiteActivationWriter:
    database_path: Path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path))
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        return connection

    def activate_transactionally(
        self,
        *,
        project_id: str,
        contract_id: str,
        contract_version: int,
        schema_version: str,
        content_hash: str,
        canonical_json: bytes,
        validation_report_json: str,
        impact_report_json: str,
        policy_decision_json: str,
        evidence_json: str,
        expected_generation: int,
        rollback_contract_version: int | None,
    ) -> ActivationRecord:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            current_row = connection.execute(
                "SELECT last_generation FROM project_generations WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            current_generation = int(current_row["last_generation"]) if current_row else 0
            if current_generation != expected_generation:
                connection.rollback()
                message = (
                    f"generation conflict: expected {expected_generation}, "
                    f"found {current_generation}"
                )
                raise ContractError(ErrorCode.ACTIVATION_ROLLED_BACK, message)

            next_generation = current_generation + 1
            now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

            previous_active = connection.execute(
                "SELECT contract_version FROM active_contracts "
                "WHERE project_id = ? AND contract_id = ?",
                (project_id, contract_id),
            ).fetchone()
            if previous_active is not None:
                connection.execute(
                    "UPDATE contract_activations SET runtime_status = 'SUPERSEDED' "
                    "WHERE project_id = ? AND contract_id = ? AND contract_version = ?",
                    (project_id, contract_id, previous_active["contract_version"]),
                )

            if current_row is None:
                connection.execute(
                    "INSERT INTO project_generations (project_id, last_generation) VALUES (?, ?)",
                    (project_id, next_generation),
                )
            else:
                connection.execute(
                    "UPDATE project_generations SET last_generation = ? WHERE project_id = ?",
                    (next_generation, project_id),
                )

            connection.execute(
                "INSERT INTO contract_activations ("
                "project_id, contract_id, contract_version, schema_version, generation, "
                "content_hash, runtime_status, canonical_json, validation_report_json, "
                "impact_report_json, policy_decision_json, evidence_json, "
                "rollback_contract_version, activated_at"
                ") VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?, ?, ?, ?)",
                (
                    project_id,
                    contract_id,
                    contract_version,
                    schema_version,
                    next_generation,
                    content_hash,
                    canonical_json,
                    validation_report_json,
                    impact_report_json,
                    policy_decision_json,
                    evidence_json,
                    rollback_contract_version,
                    now,
                ),
            )

            connection.execute(
                "INSERT INTO active_contracts ("
                "project_id, contract_id, contract_version, generation, schema_version, "
                "content_hash, enabled"
                ") VALUES (?, ?, ?, ?, ?, ?, 1) "
                "ON CONFLICT(project_id, contract_id) DO UPDATE SET "
                "contract_version = excluded.contract_version, "
                "generation = excluded.generation, "
                "schema_version = excluded.schema_version, "
                "content_hash = excluded.content_hash, "
                "enabled = 1",
                (
                    project_id,
                    contract_id,
                    contract_version,
                    next_generation,
                    schema_version,
                    content_hash,
                ),
            )

            connection.execute(
                "INSERT INTO activation_events "
                "(project_id, contract_id, generation, event_type, payload_json, created_at) "
                "VALUES (?, ?, ?, 'ACTIVATED', ?, ?)",
                (project_id, contract_id, next_generation, policy_decision_json, now),
            )

            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            message = f"activation transaction failed: {exc}"
            raise ContractError(ErrorCode.ACTIVATION_ROLLED_BACK, message) from exc
        finally:
            connection.close()

        return ActivationRecord(
            project_id=project_id,
            contract_id=contract_id,
            contract_version=contract_version,
            schema_version=schema_version,
            generation=next_generation,
            content_hash=content_hash,
            runtime_status="ACTIVE",
        )

    def rollback_transactionally(
        self,
        *,
        project_id: str,
        contract_id: str,
        target_version: int,
        expected_generation: int,
        reason: str,
    ) -> ActivationRecord:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            current_row = connection.execute(
                "SELECT last_generation FROM project_generations WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            current_generation = int(current_row["last_generation"]) if current_row else 0
            if current_generation != expected_generation:
                connection.rollback()
                message = (
                    f"generation conflict: expected {expected_generation}, "
                    f"found {current_generation}"
                )
                raise ContractError(ErrorCode.ACTIVATION_ROLLED_BACK, message)

            target_row = connection.execute(
                "SELECT schema_version, content_hash, canonical_json, validation_report_json, "
                "impact_report_json, policy_decision_json, evidence_json "
                "FROM contract_activations "
                "WHERE project_id = ? AND contract_id = ? AND contract_version = ?",
                (project_id, contract_id, target_version),
            ).fetchone()
            if target_row is None:
                connection.rollback()
                raise ContractError(
                    ErrorCode.REFERENCE_REJECTED,
                    f"rollback target not found: {contract_id} v{target_version}",
                )

            next_generation = current_generation + 1
            now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

            previous_active = connection.execute(
                "SELECT contract_version FROM active_contracts "
                "WHERE project_id = ? AND contract_id = ?",
                (project_id, contract_id),
            ).fetchone()
            if previous_active is not None:
                connection.execute(
                    "UPDATE contract_activations SET runtime_status = 'SUPERSEDED' "
                    "WHERE project_id = ? AND contract_id = ? AND contract_version = ?",
                    (project_id, contract_id, previous_active["contract_version"]),
                )
            connection.execute(
                "UPDATE contract_activations SET runtime_status = 'ROLLED_BACK' "
                "WHERE project_id = ? AND contract_id = ? AND contract_version = ?",
                (project_id, contract_id, target_version),
            )

            connection.execute(
                "UPDATE project_generations SET last_generation = ? WHERE project_id = ?",
                (next_generation, project_id),
            )
            connection.execute(
                "INSERT INTO active_contracts ("
                "project_id, contract_id, contract_version, generation, schema_version, "
                "content_hash, enabled"
                ") VALUES (?, ?, ?, ?, ?, ?, 1) "
                "ON CONFLICT(project_id, contract_id) DO UPDATE SET "
                "contract_version = excluded.contract_version, "
                "generation = excluded.generation, "
                "schema_version = excluded.schema_version, "
                "content_hash = excluded.content_hash, "
                "enabled = 1",
                (
                    project_id,
                    contract_id,
                    target_version,
                    next_generation,
                    target_row["schema_version"],
                    target_row["content_hash"],
                ),
            )
            connection.execute(
                "INSERT INTO activation_events "
                "(project_id, contract_id, generation, event_type, payload_json, created_at) "
                "VALUES (?, ?, ?, 'ROLLED_BACK', ?, ?)",
                (project_id, contract_id, next_generation, reason, now),
            )

            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            message = f"rollback transaction failed: {exc}"
            raise ContractError(ErrorCode.ACTIVATION_ROLLED_BACK, message) from exc
        finally:
            connection.close()

        return ActivationRecord(
            project_id=project_id,
            contract_id=contract_id,
            contract_version=target_version,
            schema_version=target_row["schema_version"],
            generation=next_generation,
            content_hash=target_row["content_hash"],
            runtime_status="ACTIVE",
        )
