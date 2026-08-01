"""Runtime-state store and the transactional Orchestrator writer (PH-2, CMP-ORCH).

R1: the Orchestrator is the SOLE authoritative writer. Every authoritative state change is one
atomic transaction (BEGIN IMMEDIATE → validate expected state → check legality → append an
append-only journal event → conditionally update the task → commit); any failure rolls the whole
transition back (02 §7). Readers use a ``mode=ro`` connection with the same read-only authorizer
established in PH-1 (`factory.contracts.activation.store`), so no other component can write state.
Migrations are SHA-256-pinned and transactional (01O §2.19), mirroring the PH-1 runner.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

# Reuse the exact PH-1 read-only enforcement + migration mechanics (plan: "reuse PH-1
# _reader_authorizer"). These are stable, verified security-critical helpers shared across the
# repository's SQLite stores.
from factory.contracts.activation.store import (
    _MIGRATION_FILENAME,
    _apply_single_migration,
    _reader_authorizer,
    _table_exists,
)
from factory.orchestrator.errors import OrchestratorError
from factory.orchestrator.models import (
    StateTransitionEvent,
    TaskRuntimeRecord,
    TaskState,
)
from factory.orchestrator.state.transitions import TransitionPolicy

# Pinned integrity hash for each runtime migration. A migration whose bytes do not match its
# pinned hash fails closed rather than being applied (defends against tampering with a
# git-tracked, human-editable SQL script).
_EXPECTED_MIGRATION_HASHES: Mapping[str, str] = {
    "0001_state.sql": "2fd4ecda34c05265be99de9c8aa36518cc9ac540c4038286c5da9cfb1fbd5f4c",
    "0002_leases.sql": "a3a143e4b225655b68aadb5bc677acae7a99cf99b8c047e6c3113deb34b32ba6",
    "0003_memory.sql": "65e0a4d16b84a49b205b1f2e48c91e11ae6dc48e9c179e318da3026283e10587",
    "0004_workstream_membership.sql": (
        "0274e9f2933b543277a4c50e556f8cc87762a69291e6b882d173c89811c4dc5f"
    ),
}


def _utcnow() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def apply_migrations(database_path: Path, migrations_root: Path) -> None:
    """Apply pending runtime migrations transactionally; record the version only on success.

    Each migration's SHA-256 is verified against its pinned value before it is applied. The body
    runs inside a single transaction; the ``schema_migrations`` version row is inserted only after
    the body commits, so a migration that fails mid-apply leaves no partial schema and no version
    row (REGR-0003 / T-PH2-MIG1).
    """
    files = sorted(migrations_root.glob("*.sql"))
    if not files:
        raise OrchestratorError(
            "MIGRATION_MISSING", f"no runtime migrations found under {migrations_root}"
        )

    connection = sqlite3.connect(str(database_path))
    try:
        applied_versions: set[int] = set()
        if _table_exists(connection, "schema_migrations"):
            applied_versions = {
                int(row[0]) for row in connection.execute("SELECT version FROM schema_migrations")
            }

        for path in files:
            match = _MIGRATION_FILENAME.match(path.name)
            if not match:
                raise OrchestratorError(
                    "MIGRATION_MALFORMED", f"malformed migration filename: {path.name}"
                )
            version = int(match.group(1))
            if version in applied_versions:
                continue

            content = path.read_bytes()
            actual_hash = hashlib.sha256(content).hexdigest()
            expected_hash = _EXPECTED_MIGRATION_HASHES.get(path.name)
            if expected_hash is None or actual_hash != expected_hash:
                raise OrchestratorError(
                    "MIGRATION_INTEGRITY", f"migration integrity check failed for {path.name}"
                )

            try:
                _apply_single_migration(connection, content)
                connection.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (version, _utcnow()),
                )
                connection.commit()
            except sqlite3.Error as exc:
                connection.rollback()
                raise OrchestratorError(
                    "MIGRATION_FAILED", f"migration {path.name} failed to apply: {exc}"
                ) from exc
            applied_versions.add(version)
    finally:
        connection.close()


def latest_migration_version(migrations_root: Path) -> int:
    """The highest version number among migration files on disk.

    Parses filenames only — never opens or executes anything — so it is safe to call from a
    process that must remain read-only (see ``applied_schema_version`` and
    ``scripts/run_api.py``, which uses both to fail closed rather than self-migrating).
    """
    versions = []
    for path in sorted(migrations_root.glob("*.sql")):
        match = _MIGRATION_FILENAME.match(path.name)
        if match:
            versions.append(int(match.group(1)))
    if not versions:
        raise OrchestratorError(
            "MIGRATION_MISSING", f"no runtime migrations found under {migrations_root}"
        )
    return max(versions)


def applied_schema_version(database_path: Path) -> int:
    """The highest migration version recorded in an existing database — read-only.

    Returns 0 for an existing-but-unmigrated database (no ``schema_migrations`` table yet).
    Raises ``sqlite3.OperationalError`` if ``database_path`` does not exist at all (a
    ``mode=ro`` connection cannot create one) — callers that want a clear "run setup first"
    message should catch that themselves rather than have this function paper over it.
    """
    connection = _connect_readonly(database_path)
    try:
        if not _table_exists(connection, "schema_migrations"):
            return 0
        row = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
    finally:
        connection.close()
    return int(row[0]) if row is not None and row[0] is not None else 0


def _connect_readonly(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.set_authorizer(_reader_authorizer)
    return connection


def _row_to_task(row: sqlite3.Row) -> TaskRuntimeRecord:
    return TaskRuntimeRecord(
        task_id=row["task_id"],
        project_id=row["project_id"],
        contract_version=int(row["contract_version"]),
        current_state=TaskState(row["current_state"]),
        sequence=int(row["sequence"]),
        updated_at=row["updated_at"],
        workstream_id=row["workstream_id"],
    )


def _row_to_event(row: sqlite3.Row) -> StateTransitionEvent:
    prev = row["prev_state"]
    return StateTransitionEvent(
        task_id=row["task_id"],
        sequence=int(row["sequence"]),
        prev_state=TaskState(prev) if prev is not None else None,
        new_state=TaskState(row["new_state"]),
        cause=row["cause"],
        actor=row["actor"],
        accepted=bool(row["accepted"]),
        occurred_at=row["occurred_at"],
        linked_reference=row["linked_reference"],
        idempotency_key=row["idempotency_key"],
    )


# Fully-literal SQL (no interpolation) so the read-only/append-only guarantees are the only trust
# surface and static analysis needs no exceptions.
_SELECT_TASK_BY_ID_SQL = (
    "SELECT task_id, project_id, contract_version, current_state, sequence, updated_at, "
    "workstream_id FROM tasks WHERE task_id = ?"
)
_SELECT_TASKS_BY_WORKSTREAM_SQL = (
    "SELECT task_id, project_id, contract_version, current_state, sequence, updated_at, "
    "workstream_id FROM tasks WHERE workstream_id = ? ORDER BY updated_at ASC, task_id ASC"
)
_SELECT_EVENTS_BY_TASK_SQL = (
    "SELECT task_id, sequence, prev_state, new_state, cause, actor, accepted, "
    "occurred_at, linked_reference, idempotency_key FROM task_state_events "
    "WHERE task_id = ? ORDER BY event_id"
)
_SELECT_EVENT_BY_IDEMPOTENCY_SQL = (
    "SELECT task_id, sequence, prev_state, new_state, cause, actor, accepted, "
    "occurred_at, linked_reference, idempotency_key FROM task_state_events "
    "WHERE task_id = ? AND idempotency_key = ?"
)
_INSERT_EVENT_SQL = (
    "INSERT INTO task_state_events (task_id, sequence, prev_state, new_state, cause, actor, "
    "accepted, occurred_at, linked_reference, idempotency_key) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


class OrchestratorStateReader(Protocol):
    def get_task(self, task_id: str) -> TaskRuntimeRecord | None: ...
    def get_events(self, task_id: str) -> tuple[StateTransitionEvent, ...]: ...
    def list_tasks_by_workstream(self, workstream_id: str) -> tuple[TaskRuntimeRecord, ...]: ...


@dataclass(frozen=True, slots=True)
class SQLiteOrchestratorStateReader:
    """Read-only view over the runtime-state DB (``mode=ro`` + denial authorizer)."""

    database_path: Path

    def get_task(self, task_id: str) -> TaskRuntimeRecord | None:
        connection = _connect_readonly(self.database_path)
        try:
            row = connection.execute(_SELECT_TASK_BY_ID_SQL, (task_id,)).fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        return _row_to_task(row)

    def get_events(self, task_id: str) -> tuple[StateTransitionEvent, ...]:
        connection = _connect_readonly(self.database_path)
        try:
            rows = connection.execute(_SELECT_EVENTS_BY_TASK_SQL, (task_id,)).fetchall()
        finally:
            connection.close()
        return tuple(_row_to_event(row) for row in rows)

    def list_tasks_by_workstream(self, workstream_id: str) -> tuple[TaskRuntimeRecord, ...]:
        """Tasks explicitly assigned to ``workstream_id``, ordered by (updated_at, task_id).

        Unassigned tasks (``workstream_id IS NULL``) and tasks assigned to a different
        workstream are excluded — membership is never inferred from ``project_id``.
        """
        connection = _connect_readonly(self.database_path)
        try:
            rows = connection.execute(
                _SELECT_TASKS_BY_WORKSTREAM_SQL, (workstream_id,)
            ).fetchall()
        finally:
            connection.close()
        return tuple(_row_to_task(row) for row in rows)


@dataclass(frozen=True, slots=True)
class _OrchestratorStateWriter:
    """The single authoritative writer (R1). Not exported from the package."""

    database_path: Path
    policy: TransitionPolicy = field(default_factory=TransitionPolicy)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path))
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        return connection

    def create_task(
        self,
        *,
        task_id: str,
        project_id: str,
        contract_version: int,
        workstream_id: str | None = None,
    ) -> StateTransitionEvent:
        """Seed a task at QUEUED (genesis) with a matching accepted genesis event at sequence 0.

        ``workstream_id`` is an explicit, optional identity distinct from ``project_id`` (01L) —
        it is never fabricated or inferred here. Omitting it (the default) leaves the task
        unassigned, which is the correct state for existing/legacy callers.
        """
        connection = self._connect()
        now = _utcnow()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT task_id FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            if existing is not None:
                connection.rollback()
                raise OrchestratorError("TASK_EXISTS", f"task {task_id} already exists")
            connection.execute(
                "INSERT INTO tasks "
                "(task_id, project_id, contract_version, current_state, sequence, updated_at, "
                "workstream_id) VALUES (?, ?, ?, ?, 0, ?, ?)",
                (task_id, project_id, contract_version, TaskState.QUEUED.value, now, workstream_id),
            )
            connection.execute(
                _INSERT_EVENT_SQL,
                (
                    task_id,
                    0,
                    None,
                    TaskState.QUEUED.value,
                    "genesis",
                    "orchestrator",
                    1,
                    now,
                    None,
                    None,
                ),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise OrchestratorError("STATE_TX_FAILED", f"create_task failed: {exc}") from exc
        finally:
            connection.close()
        return StateTransitionEvent(
            task_id=task_id,
            sequence=0,
            prev_state=None,
            new_state=TaskState.QUEUED,
            cause="genesis",
            actor="orchestrator",
            accepted=True,
            occurred_at=now,
            linked_reference=None,
            idempotency_key=None,
        )

    def apply_transition(
        self,
        *,
        task_id: str,
        expected_current_state: TaskState | None,
        new_state: TaskState,
        cause: str,
        actor: str,
        linked_reference: str | None = None,
        idempotency_key: str | None = None,
    ) -> StateTransitionEvent:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")

            if idempotency_key is not None:
                existing = connection.execute(
                    _SELECT_EVENT_BY_IDEMPOTENCY_SQL,
                    (task_id, idempotency_key),
                ).fetchone()
                if existing is not None:
                    connection.rollback()
                    return _row_to_event(existing)

            task_row = connection.execute(
                "SELECT current_state, sequence FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            if task_row is None:
                connection.rollback()
                raise OrchestratorError("TASK_NOT_FOUND", f"task {task_id} does not exist")

            current_state = TaskState(task_row["current_state"])
            current_sequence = int(task_row["sequence"])
            expected_matches = expected_current_state == current_state
            legal = self.policy.is_legal(current_state, new_state)
            accepted = expected_matches and legal
            event_sequence = current_sequence + 1 if accepted else current_sequence
            now = _utcnow()

            connection.execute(
                _INSERT_EVENT_SQL,
                (
                    task_id,
                    event_sequence,
                    current_state.value,
                    new_state.value,
                    cause,
                    actor,
                    1 if accepted else 0,
                    now,
                    linked_reference,
                    idempotency_key,
                ),
            )
            if accepted:
                connection.execute(
                    "UPDATE tasks SET current_state = ?, sequence = ?, updated_at = ? "
                    "WHERE task_id = ?",
                    (new_state.value, event_sequence, now, task_id),
                )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise OrchestratorError("STATE_TX_FAILED", f"transition failed: {exc}") from exc
        finally:
            connection.close()

        return StateTransitionEvent(
            task_id=task_id,
            sequence=event_sequence,
            prev_state=current_state,
            new_state=new_state,
            cause=cause,
            actor=actor,
            accepted=accepted,
            occurred_at=now,
            linked_reference=linked_reference,
            idempotency_key=idempotency_key,
        )


__all__ = [
    "OrchestratorStateReader",
    "SQLiteOrchestratorStateReader",
    "applied_schema_version",
    "apply_migrations",
    "latest_migration_version",
]
