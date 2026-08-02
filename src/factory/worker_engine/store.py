"""Worker-run persistence (Phase 3B): plans, progress, logs, commands, artifacts, results, and
failures for every worker run, in the same authoritative ``runtime.db`` as the orchestrator's own
tables (not a second database) -- ``migrations/runtime/0006_worker_runs.sql`` added these tables
additively; migrations 0001-0005 are untouched.

Mirrors ``factory.orchestrator.store.runtime_state``'s exact pattern: a not-exported, transactional
writer (``BEGIN IMMEDIATE`` per operation) and a read-only reader (``mode=ro`` + the same PH-1
reader authorizer). Nothing here holds the orchestrator's own authoritative writer (R1) -- this
store is additive bookkeeping the Worker Engine owns, never a second authoritative task-state
writer.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from factory.contracts.activation.store import _reader_authorizer
from factory.worker_engine.errors import WorkerEngineRunError
from factory.worker_engine.execution_policy import ExecutionMode
from factory.worker_engine.models import (
    WorkerArtifactRecord,
    WorkerEventRecord,
    WorkerRunOutcome,
    WorkerRunRecord,
)


def _utcnow() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect_readonly(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.set_authorizer(_reader_authorizer)
    return connection


def _row_to_run(row: sqlite3.Row) -> WorkerRunRecord:
    outcome = row["outcome"]
    return WorkerRunRecord(
        run_id=row["run_id"],
        task_id=row["task_id"],
        attempt=int(row["attempt"]),
        requested_mode=ExecutionMode[row["requested_mode"]],
        selected_mode=ExecutionMode[row["selected_mode"]],
        mode_reason=row["mode_reason"],
        policy_rule=row["policy_rule"],
        sandbox_path=row["sandbox_path"],
        branch_ref=row["branch_ref"],
        base_sha=row["base_sha"],
        staging_id=row["staging_id"],
        work_order_json=row["work_order_json"],
        model_route_token=row["model_route_token"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        outcome=WorkerRunOutcome(outcome) if outcome is not None else None,
        reason=row["reason"],
    )


def _row_to_event(row: sqlite3.Row) -> WorkerEventRecord:
    return WorkerEventRecord(
        run_id=row["run_id"],
        sequence=int(row["sequence"]),
        event_type=row["event_type"],
        payload_json=row["payload_json"],
        occurred_at=row["occurred_at"],
    )


def _row_to_artifact(row: sqlite3.Row) -> WorkerArtifactRecord:
    return WorkerArtifactRecord(
        run_id=row["run_id"],
        artifact_path=row["artifact_path"],
        content_digest=row["content_digest"],
        media_type=row["media_type"],
    )


_SELECT_RUN_SQL = (
    "SELECT run_id, task_id, attempt, requested_mode, selected_mode, mode_reason, policy_rule, "
    "sandbox_path, branch_ref, base_sha, staging_id, work_order_json, model_route_token, "
    "started_at, finished_at, outcome, reason FROM worker_runs WHERE run_id = ?"
)
_SELECT_RUNS_BY_TASK_SQL = (
    "SELECT run_id, task_id, attempt, requested_mode, selected_mode, mode_reason, policy_rule, "
    "sandbox_path, branch_ref, base_sha, staging_id, work_order_json, model_route_token, "
    "started_at, finished_at, outcome, reason FROM worker_runs "
    "WHERE task_id = ? ORDER BY attempt ASC"
)
_SELECT_EVENTS_SQL = (
    "SELECT run_id, sequence, event_type, payload_json, occurred_at FROM worker_events "
    "WHERE run_id = ? ORDER BY sequence ASC"
)
_SELECT_ARTIFACTS_SQL = (
    "SELECT run_id, artifact_path, content_digest, media_type FROM worker_artifacts "
    "WHERE run_id = ? ORDER BY artifact_id ASC"
)
_INSERT_RUN_SQL = (
    "INSERT INTO worker_runs (run_id, task_id, attempt, requested_mode, selected_mode, "
    "mode_reason, policy_rule, sandbox_path, branch_ref, base_sha, staging_id, "
    "work_order_json, model_route_token, started_at) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)
_FINISH_RUN_SQL = (
    "UPDATE worker_runs SET finished_at = ?, outcome = ?, reason = ? WHERE run_id = ?"
)
_INSERT_EVENT_SQL = (
    "INSERT INTO worker_events (run_id, sequence, event_type, payload_json, occurred_at) "
    "VALUES (?, ?, ?, ?, ?)"
)
_INSERT_ARTIFACT_SQL = (
    "INSERT INTO worker_artifacts (run_id, artifact_path, content_digest, media_type) "
    "VALUES (?, ?, ?, ?)"
)
_COUNT_ATTEMPTS_SQL = "SELECT COUNT(*) AS n FROM worker_runs WHERE task_id = ?"


class WorkerRunReader(Protocol):
    def get_run(self, run_id: str) -> WorkerRunRecord | None: ...
    def list_runs_for_task(self, task_id: str) -> tuple[WorkerRunRecord, ...]: ...
    def get_events(self, run_id: str) -> tuple[WorkerEventRecord, ...]: ...
    def get_artifacts(self, run_id: str) -> tuple[WorkerArtifactRecord, ...]: ...


@dataclass(frozen=True, slots=True)
class SQLiteWorkerRunReader:
    database_path: Path

    def get_run(self, run_id: str) -> WorkerRunRecord | None:
        connection = _connect_readonly(self.database_path)
        try:
            row = connection.execute(_SELECT_RUN_SQL, (run_id,)).fetchone()
        finally:
            connection.close()
        return None if row is None else _row_to_run(row)

    def list_runs_for_task(self, task_id: str) -> tuple[WorkerRunRecord, ...]:
        connection = _connect_readonly(self.database_path)
        try:
            rows = connection.execute(_SELECT_RUNS_BY_TASK_SQL, (task_id,)).fetchall()
        finally:
            connection.close()
        return tuple(_row_to_run(row) for row in rows)

    def get_events(self, run_id: str) -> tuple[WorkerEventRecord, ...]:
        connection = _connect_readonly(self.database_path)
        try:
            rows = connection.execute(_SELECT_EVENTS_SQL, (run_id,)).fetchall()
        finally:
            connection.close()
        return tuple(_row_to_event(row) for row in rows)

    def get_artifacts(self, run_id: str) -> tuple[WorkerArtifactRecord, ...]:
        connection = _connect_readonly(self.database_path)
        try:
            rows = connection.execute(_SELECT_ARTIFACTS_SQL, (run_id,)).fetchall()
        finally:
            connection.close()
        return tuple(_row_to_artifact(row) for row in rows)


@dataclass(frozen=True, slots=True)
class _WorkerRunWriter:
    """Not exported from the package -- the Worker Engine's own additive-bookkeeping writer,
    never the orchestrator's authoritative task-state writer (R1 stays confined to
    ``factory.orchestrator.store.runtime_state._OrchestratorStateWriter``)."""

    database_path: Path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path))
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        return connection

    def next_attempt(self, task_id: str) -> int:
        """1-indexed attempt number for a new run of ``task_id`` (count of prior runs + 1)."""
        connection = _connect_readonly(self.database_path)
        try:
            row = connection.execute(_COUNT_ATTEMPTS_SQL, (task_id,)).fetchone()
        finally:
            connection.close()
        return int(row["n"]) + 1

    def create_run(
        self,
        *,
        run_id: str,
        task_id: str,
        attempt: int,
        requested_mode: ExecutionMode,
        selected_mode: ExecutionMode,
        mode_reason: str,
        policy_rule: str,
        work_order_json: str,
        model_route_token: str,
        sandbox_path: str | None = None,
        branch_ref: str | None = None,
        base_sha: str | None = None,
        staging_id: str | None = None,
    ) -> WorkerRunRecord:
        now = _utcnow()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                _INSERT_RUN_SQL,
                (
                    run_id, task_id, attempt, requested_mode.name, selected_mode.name,
                    mode_reason, policy_rule, sandbox_path, branch_ref, base_sha, staging_id,
                    work_order_json, model_route_token, now,
                ),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise WorkerEngineRunError("RUN_CREATE_FAILED", f"create_run failed: {exc}") from exc
        finally:
            connection.close()
        return WorkerRunRecord(
            run_id=run_id, task_id=task_id, attempt=attempt,
            requested_mode=requested_mode, selected_mode=selected_mode,
            mode_reason=mode_reason, policy_rule=policy_rule,
            sandbox_path=sandbox_path, branch_ref=branch_ref, base_sha=base_sha,
            staging_id=staging_id, work_order_json=work_order_json,
            model_route_token=model_route_token, started_at=now, finished_at=None,
            outcome=None, reason=None,
        )

    def append_event(
        self, *, run_id: str, sequence: int, event_type: str, payload_json: str
    ) -> None:
        now = _utcnow()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                _INSERT_EVENT_SQL, (run_id, sequence, event_type, payload_json, now)
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise WorkerEngineRunError(
                "EVENT_APPEND_FAILED", f"append_event failed: {exc}"
            ) from exc
        finally:
            connection.close()

    def add_artifact(
        self, *, run_id: str, artifact_path: str, content_digest: str, media_type: str
    ) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                _INSERT_ARTIFACT_SQL, (run_id, artifact_path, content_digest, media_type)
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise WorkerEngineRunError(
                "ARTIFACT_ADD_FAILED", f"add_artifact failed: {exc}"
            ) from exc
        finally:
            connection.close()

    def finish_run(
        self, *, run_id: str, outcome: WorkerRunOutcome, reason: str
    ) -> None:
        now = _utcnow()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                _FINISH_RUN_SQL, (now, outcome.value, reason, run_id)
            )
            if cursor.rowcount == 0:
                connection.rollback()
                raise WorkerEngineRunError("RUN_NOT_FOUND", f"run {run_id} does not exist")
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise WorkerEngineRunError("RUN_FINISH_FAILED", f"finish_run failed: {exc}") from exc
        finally:
            connection.close()


__all__ = ["SQLiteWorkerRunReader", "WorkerRunReader"]
