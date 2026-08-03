"""Task 3.3 failure-paths — rejected transitions from illegal current state (CMP-WORKER)."""

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

pytestmark = pytest.mark.failure_path


def _result(task_id: str, *, exit_code: int | None, cause: str | None) -> ExecutionResult:
    return ExecutionResult(
        task_id=task_id,
        exit_code=exit_code,
        output_hash="h",
        events_captured=1,
        truncated=False,
        failure_cause=cause,
    )


def test_finalize_success_from_queued_is_rejected(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    # A task still QUEUED cannot jump to VERIFYING — the writer rejects the illegal transition and
    # StateIntegration surfaces it rather than silently corrupting state.
    integration = StateIntegration(writer=writer, reader=reader)
    writer.create_task(task_id="TASK-001", project_id="PROJ-001", contract_version=1)
    with pytest.raises(WorkerEngineError, match="STATE_TRANSITION_REJECTED"):
        integration.finalize("TASK-001", _result("TASK-001", exit_code=0, cause=None), actor="w0")


def test_start_execution_from_terminal_is_rejected(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    integration = StateIntegration(writer=writer, reader=reader)
    writer.create_task(task_id="TASK-001", project_id="PROJ-001", contract_version=1)
    integration.start_execution("TASK-001", actor="w0")
    integration.finalize(
        "TASK-001", _result("TASK-001", exit_code=None, cause="cancelled"), actor="w0"
    )
    # now CANCELLED (terminal); starting again is invalid
    assert reader.get_task("TASK-001").current_state is TaskState.CANCELLED
    with pytest.raises(WorkerEngineError, match="INVALID_START_STATE"):
        integration.start_execution("TASK-001", actor="w0")
