from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from factory.git.manager import GitManager
from factory.orchestrator.models import TaskState
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
)
from factory.verification.engine import VerificationEngine
from factory.verification.errors import VerificationStoreError
from factory.verification.store import SQLiteVerificationReader, _VerificationWriter
from factory.worker_engine.execution_policy import ExecutionMode
from factory.worker_engine.models import WorkerRunOutcome, WorkerRunRecord


def _prepare_task(database: Path, task_id: str, expected: str | None) -> None:
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE task_requests SET expected_result = ? WHERE task_id = ?", (expected, task_id)
        )
    writer = _OrchestratorStateWriter(database)
    for current, target in (
        (TaskState.QUEUED, TaskState.PLANNING),
        (TaskState.PLANNING, TaskState.RUNNING),
        (TaskState.RUNNING, TaskState.VERIFYING),
    ):
        writer.apply_transition(
            task_id=task_id,
            expected_current_state=current,
            new_state=target,
            cause="test",
            actor="test",
        )


def _run(
    task_id: str, output: Path, mode: ExecutionMode = ExecutionMode.STAGED_WRITE
) -> WorkerRunRecord:
    return WorkerRunRecord(
        run_id="run-1",
        task_id=task_id,
        attempt=1,
        requested_mode=mode,
        selected_mode=mode,
        mode_reason="test",
        policy_rule="test",
        sandbox_path=None if mode is ExecutionMode.DIRECT_READ_ONLY else str(output),
        branch_ref=None,
        base_sha=None,
        staging_id="staging" if mode is ExecutionMode.STAGED_WRITE else None,
        work_order_json=json.dumps({"allowed_path_globs": ["**"]}),
        model_route_token="",
        started_at="2026-08-02T00:00:00Z",
        finished_at="2026-08-02T00:00:01Z",
        outcome=WorkerRunOutcome.SUCCESS,
        reason="worker claim is not verification",
    )


def _engine(database: Path, repo: Path) -> VerificationEngine:
    return VerificationEngine(
        orchestrator_writer=_OrchestratorStateWriter(database),
        orchestrator_reader=SQLiteOrchestratorStateReader(database),
        verification_writer=_VerificationWriter(database),
        git=GitManager(),
        repo_root=repo,
    )


def test_staged_output_verifies_and_replay_is_idempotent(
    verification_db: tuple[Path, str], tmp_path: Path
) -> None:
    database, task_id = verification_db
    output = tmp_path / "output"
    output.mkdir()
    result = output / "result.txt"
    result.write_text("complete")
    expected = json.dumps(
        {
            "required_files": ["result.txt"],
            "required_sha256": {"result.txt": hashlib.sha256(result.read_bytes()).hexdigest()},
        }
    )
    _prepare_task(database, task_id, expected)
    engine = _engine(database, tmp_path)

    first = engine.verify(task_id, _run(task_id, output))
    second = engine.verify(task_id, _run(task_id, output))

    assert first.passed and second.passed
    assert (
        SQLiteOrchestratorStateReader(database).get_task(task_id).current_state
        is TaskState.AWAITING_APPROVAL
    )
    assert SQLiteVerificationReader(database).get_latest_manifest(task_id) is not None


def test_direct_read_only_with_acceptance_fails_closed(
    verification_db: tuple[Path, str], tmp_path: Path
) -> None:
    database, task_id = verification_db
    _prepare_task(database, task_id, '{"required_files":["report.txt"]}')
    outcome = _engine(database, tmp_path).verify(
        task_id, _run(task_id, tmp_path, ExecutionMode.DIRECT_READ_ONLY)
    )
    assert not outcome.passed
    assert (
        SQLiteOrchestratorStateReader(database).get_task(task_id).current_state is TaskState.FAILED
    )


def test_changed_artifact_after_verified_replay_is_rejected(
    verification_db: tuple[Path, str], tmp_path: Path
) -> None:
    database, task_id = verification_db
    output = tmp_path / "output"
    output.mkdir()
    result = output / "result.txt"
    result.write_text("first")
    expected = json.dumps(
        {
            "required_files": ["result.txt"],
            "required_sha256": {"result.txt": hashlib.sha256(result.read_bytes()).hexdigest()},
        }
    )
    _prepare_task(database, task_id, expected)
    engine = _engine(database, tmp_path)
    engine.verify(task_id, _run(task_id, output))
    result.write_text("tampered")
    with pytest.raises(VerificationStoreError, match="VERIFICATION_REPLAY_CONFLICT"):
        engine.verify(task_id, _run(task_id, output))
