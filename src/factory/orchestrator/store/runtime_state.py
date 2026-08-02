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
import uuid
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
    TaskRequestRecord,
    TaskRuntimeRecord,
    TaskState,
    TaskSubmissionResult,
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
    "0005_task_requests.sql": ("a68ca07b5c48d494fc42e714828e6c54c3e13f9415b247db1965690b7aa65bc8"),
    "0006_worker_runs.sql": ("38d36efe4cdbb2397da486271dce79d40fc88a737cca9fc6c8883f6134e0ba71"),
    "0007_verification_promotion.sql": (
        "f0f8441120ae50e2732ccb7e3d74899a897b70db33ded820e36ed26697458556"
    ),
}


def _utcnow() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_migration_filename(path: Path) -> int:
    """The numeric version prefix of a migration filename — fails closed on a bad name.

    The single filename-validation rule shared by ``apply_migrations`` (the writable path)
    and ``expected_migration_versions`` (the read-only discovery path), so the two can never
    silently diverge on what counts as a valid migration filename.
    """
    match = _MIGRATION_FILENAME.match(path.name)
    if not match:
        raise OrchestratorError("MIGRATION_MALFORMED", f"malformed migration filename: {path.name}")
    return int(match.group(1))


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
            version = _parse_migration_filename(path)
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


def expected_migration_versions(migrations_root: Path) -> tuple[int, ...]:
    """The complete, ascending set of migration versions expected on disk.

    Parses filenames only — never opens or executes anything — so it is safe to call from a
    process that must remain read-only (see ``applied_migration_versions`` and
    ``scripts/run_api.py``, which compares the two full sets to fail closed rather than
    self-migrating). A version count or maximum alone cannot detect a gap — e.g. ``{1, 2, 4}``
    has the same maximum as ``{1, 2, 3, 4}`` — so callers must compare the full sets, not just
    a count or a maximum, for a correct "is this schema current" decision.

    Every ``*.sql`` file must have a valid migration filename (shares ``apply_migrations``'s
    own parser, so the two can never silently disagree on what's malformed) and every version
    number must be unique; either violation fails closed with ``OrchestratorError``.
    """
    versions: list[int] = []
    seen: set[int] = set()
    for path in sorted(migrations_root.glob("*.sql")):
        version = _parse_migration_filename(path)
        if version in seen:
            raise OrchestratorError(
                "MIGRATION_MALFORMED",
                f"duplicate migration version {version} in {migrations_root}",
            )
        seen.add(version)
        versions.append(version)
    if not versions:
        raise OrchestratorError(
            "MIGRATION_MISSING", f"no runtime migrations found under {migrations_root}"
        )
    return tuple(sorted(versions))


def applied_migration_versions(database_path: Path) -> tuple[int, ...]:
    """The complete, ascending set of migration versions recorded in an existing database.

    Read-only (``mode=ro``). Returns an empty tuple for an existing-but-unmigrated database
    (no ``schema_migrations`` table yet). Raises ``sqlite3.OperationalError`` if
    ``database_path`` does not exist at all (a ``mode=ro`` connection cannot create one) —
    callers that want a clear "run setup first" message should catch that themselves rather
    than have this function paper over it.
    """
    connection = _connect_readonly(database_path)
    try:
        if not _table_exists(connection, "schema_migrations"):
            return ()
        rows = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version ASC"
        ).fetchall()
    finally:
        connection.close()
    return tuple(int(row[0]) for row in rows)


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


def _row_to_task_request(row: sqlite3.Row) -> TaskRequestRecord:
    return TaskRequestRecord(
        task_id=row["task_id"],
        project_ref=row["project_ref"],
        workstream_id=row["workstream_id"],
        description=row["description"],
        priority=row["priority"],
        model_preference=row["model_preference"],
        expected_result=row["expected_result"],
        submitted_by=row["submitted_by"],
        submitted_at=row["submitted_at"],
        idempotency_key=row["idempotency_key"],
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
# Placeholder count is filled in at call time (`?` repeated once per requested state).
_SELECT_TASKS_BY_STATES_SQL_TEMPLATE = (
    "SELECT task_id, project_id, contract_version, current_state, sequence, updated_at, "
    "workstream_id FROM tasks WHERE current_state IN ({placeholders}) "
    "ORDER BY updated_at ASC, task_id ASC"
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
_SELECT_TASK_REQUEST_BY_ID_SQL = (
    "SELECT task_id, project_ref, workstream_id, description, priority, model_preference, "
    "expected_result, submitted_by, submitted_at, idempotency_key FROM task_requests "
    "WHERE task_id = ?"
)
_SELECT_TASK_REQUEST_BY_IDEMPOTENCY_KEY_SQL = (
    "SELECT task_id, project_ref, workstream_id, description, priority, model_preference, "
    "expected_result, submitted_by, submitted_at, idempotency_key FROM task_requests "
    "WHERE idempotency_key = ?"
)
_INSERT_TASK_REQUEST_SQL = (
    "INSERT INTO task_requests (task_id, project_ref, workstream_id, description, priority, "
    "model_preference, expected_result, submitted_by, submitted_at, idempotency_key) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
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
    def get_task_request(self, task_id: str) -> TaskRequestRecord | None: ...
    def list_tasks_by_states(
        self, states: frozenset[TaskState]
    ) -> tuple[TaskRuntimeRecord, ...]: ...


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
            rows = connection.execute(_SELECT_TASKS_BY_WORKSTREAM_SQL, (workstream_id,)).fetchall()
        finally:
            connection.close()
        return tuple(_row_to_task(row) for row in rows)

    def get_task_request(self, task_id: str) -> TaskRequestRecord | None:
        """The human-submission metadata for a task (Phase 3A), read-only. ``None`` if unknown."""
        connection = _connect_readonly(self.database_path)
        try:
            row = connection.execute(_SELECT_TASK_REQUEST_BY_ID_SQL, (task_id,)).fetchone()
        finally:
            connection.close()
        return None if row is None else _row_to_task_request(row)

    def list_tasks_by_states(self, states: frozenset[TaskState]) -> tuple[TaskRuntimeRecord, ...]:
        """Every task currently in any of ``states``, across all workstreams (Phase 3B).

        Used by the Worker Engine to discover claimable QUEUED tasks and, at startup, every
        non-terminal in-flight task for crash reconciliation. ``states`` must be non-empty; the
        placeholder count in the generated SQL is exactly ``len(states)`` value markers (``?``),
        never state text itself -- every bound value is still passed through the parameterized
        query, so this remains injection-free despite the dynamic placeholder count.
        """
        if not states:
            return ()
        connection = _connect_readonly(self.database_path)
        try:
            placeholders = ",".join("?" * len(states))
            sql = _SELECT_TASKS_BY_STATES_SQL_TEMPLATE.format(placeholders=placeholders)
            rows = connection.execute(sql, tuple(state.value for state in states)).fetchall()
        finally:
            connection.close()
        return tuple(_row_to_task(row) for row in rows)


def _insert_genesis_task_row(
    connection: sqlite3.Connection,
    *,
    task_id: str,
    project_id: str,
    contract_version: int,
    workstream_id: str | None,
    now: str,
) -> None:
    """Insert the ``tasks`` row and its genesis ``task_state_events`` row for a brand-new task.

    Shared by ``create_task`` and ``submit_task_request`` so the two never diverge on what
    "a task's genesis" means. Caller owns the transaction (``BEGIN IMMEDIATE``/commit/rollback).
    """
    connection.execute(
        "INSERT INTO tasks "
        "(task_id, project_id, contract_version, current_state, sequence, updated_at, "
        "workstream_id) VALUES (?, ?, ?, ?, 0, ?, ?)",
        (task_id, project_id, contract_version, TaskState.QUEUED.value, now, workstream_id),
    )
    connection.execute(
        _INSERT_EVENT_SQL,
        (task_id, 0, None, TaskState.QUEUED.value, "genesis", "orchestrator", 1, now, None, None),
    )


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
            _insert_genesis_task_row(
                connection,
                task_id=task_id,
                project_id=project_id,
                contract_version=contract_version,
                workstream_id=workstream_id,
                now=now,
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

    def submit_task_request(
        self,
        *,
        project_ref: str,
        workstream_id: str,
        description: str,
        priority: str,
        model_preference: str | None,
        expected_result: str | None,
        submitted_by: str,
        idempotency_key: str,
        contract_version: int = 1,
    ) -> TaskSubmissionResult:
        """Submit a human-authored task request (Phase 3A, CMP-ORCH-API).

        Idempotent on ``idempotency_key``: if a request with this key already exists, this is a
        no-op that returns the *original* task's identity/state (``created=False``) instead of
        creating a duplicate task — the check and the insert happen inside the same
        ``BEGIN IMMEDIATE`` transaction the rest of this writer already uses, so two
        near-simultaneous submissions with the same key cannot race past each other.

        ``project_ref`` (the human-submitted project/repository reference) becomes the task's
        authoritative ``project_id`` — there is no separate project registry to resolve against
        in this phase.
        """
        connection = self._connect()
        now = _utcnow()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing_request = connection.execute(
                _SELECT_TASK_REQUEST_BY_IDEMPOTENCY_KEY_SQL, (idempotency_key,)
            ).fetchone()
            if existing_request is not None:
                existing_task_id = existing_request["task_id"]
                task_row = connection.execute(
                    "SELECT current_state FROM tasks WHERE task_id = ?", (existing_task_id,)
                ).fetchone()
                connection.rollback()
                if task_row is None:
                    raise OrchestratorError(
                        "STATE_TX_FAILED",
                        f"task_requests row for idempotency_key exists but task "
                        f"{existing_task_id} is missing",
                    )
                return TaskSubmissionResult(
                    task_id=existing_task_id,
                    state=TaskState(task_row["current_state"]),
                    created=False,
                )

            task_id = str(uuid.uuid4())
            _insert_genesis_task_row(
                connection,
                task_id=task_id,
                project_id=project_ref,
                contract_version=contract_version,
                workstream_id=workstream_id,
                now=now,
            )
            connection.execute(
                _INSERT_TASK_REQUEST_SQL,
                (
                    task_id,
                    project_ref,
                    workstream_id,
                    description,
                    priority,
                    model_preference,
                    expected_result,
                    submitted_by,
                    now,
                    idempotency_key,
                ),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise OrchestratorError(
                "STATE_TX_FAILED", f"submit_task_request failed: {exc}"
            ) from exc
        finally:
            connection.close()
        return TaskSubmissionResult(task_id=task_id, state=TaskState.QUEUED, created=True)

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
    "applied_migration_versions",
    "apply_migrations",
    "expected_migration_versions",
]
