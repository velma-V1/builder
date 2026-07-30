"""Task 3.3 — StateIntegration routes execution results via the PH-2 single writer."""

from __future__ import annotations

import pytest

from factory.orchestrator.models import TaskState
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
)
from factory.workers.errors import WorkerEngineError
from factory.workers.models import ExecutionResult
from factory.workers.state_integration import StateIntegration


def _result(task_id: str, *, exit_code: int | None, cause: str | None) -> ExecutionResult:
    return ExecutionResult(
        task_id=task_id,
        exit_code=exit_code,
        output_hash="deadbeef",
        events_captured=3,
        truncated=cause == "output_overflow",
        failure_cause=cause,
    )


@pytest.fixture
def integration(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> StateIntegration:
    return StateIntegration(writer=writer, reader=reader)


def _seed_running(
    integration: StateIntegration, writer: _OrchestratorStateWriter, task_id: str
) -> None:
    writer.create_task(task_id=task_id, project_id="PROJ-001", contract_version=1)
    integration.start_execution(task_id, actor="worker-0")


def test_start_execution_drives_queued_to_running(
    integration: StateIntegration,
    writer: _OrchestratorStateWriter,
    reader: SQLiteOrchestratorStateReader,
) -> None:
    writer.create_task(task_id="TASK-001", project_id="PROJ-001", contract_version=1)
    event = integration.start_execution("TASK-001", actor="worker-0")
    assert event.new_state is TaskState.RUNNING
    assert reader.get_task("TASK-001").current_state is TaskState.RUNNING


def test_start_execution_rejects_already_running(
    integration: StateIntegration, writer: _OrchestratorStateWriter
) -> None:
    _seed_running(integration, writer, "TASK-001")
    with pytest.raises(WorkerEngineError, match="ALREADY_RUNNING"):
        integration.start_execution("TASK-001", actor="worker-0")


def test_finalize_success_goes_to_verifying_not_complete(
    integration: StateIntegration,
    writer: _OrchestratorStateWriter,
    reader: SQLiteOrchestratorStateReader,
) -> None:
    _seed_running(integration, writer, "TASK-001")
    event = integration.finalize(
        "TASK-001", _result("TASK-001", exit_code=0, cause=None), actor="w0"
    )
    # worker cannot self-certify COMPLETE; success hands off to VERIFYING
    assert event.new_state is TaskState.VERIFYING
    assert reader.get_task("TASK-001").current_state is TaskState.VERIFYING


def test_finalize_nonzero_exit_fails(
    integration: StateIntegration,
    writer: _OrchestratorStateWriter,
    reader: SQLiteOrchestratorStateReader,
) -> None:
    _seed_running(integration, writer, "TASK-001")
    event = integration.finalize(
        "TASK-001", _result("TASK-001", exit_code=1, cause="nonzero_exit"), actor="w0"
    )
    assert event.new_state is TaskState.FAILED
    assert event.cause == "nonzero_exit"


def test_finalize_output_overflow_fails_with_cause(
    integration: StateIntegration, writer: _OrchestratorStateWriter
) -> None:
    _seed_running(integration, writer, "TASK-001")
    event = integration.finalize(
        "TASK-001", _result("TASK-001", exit_code=None, cause="output_overflow"), actor="w0"
    )
    assert event.new_state is TaskState.FAILED
    assert event.cause == "output_overflow"


def test_finalize_cancelled_reaches_cancelled_via_stopping(
    integration: StateIntegration,
    writer: _OrchestratorStateWriter,
    reader: SQLiteOrchestratorStateReader,
) -> None:
    _seed_running(integration, writer, "TASK-001")
    event = integration.finalize(
        "TASK-001", _result("TASK-001", exit_code=None, cause="cancelled"), actor="w0"
    )
    assert event.new_state is TaskState.CANCELLED
    assert reader.get_task("TASK-001").current_state is TaskState.CANCELLED


def test_finalize_is_idempotent_on_replay(
    integration: StateIntegration,
    writer: _OrchestratorStateWriter,
    reader: SQLiteOrchestratorStateReader,
) -> None:
    _seed_running(integration, writer, "TASK-001")
    result = _result("TASK-001", exit_code=0, cause=None)
    first = integration.finalize("TASK-001", result, actor="w0")
    second = integration.finalize("TASK-001", result, actor="w0")  # replay
    assert first.sequence == second.sequence  # deduped, not a second transition
    assert reader.get_task("TASK-001").current_state is TaskState.VERIFYING


def test_finalize_unknown_task_raises(integration: StateIntegration) -> None:
    with pytest.raises(WorkerEngineError, match="TASK_NOT_FOUND"):
        integration.finalize("TASK-404", _result("TASK-404", exit_code=0, cause=None), actor="w0")
