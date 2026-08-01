"""Phase 3A — TaskOperatorService: submit / cancel / get_detail.

No approve/reject method exists anywhere in this service -- nothing to test.
"""

from __future__ import annotations

import pytest

from factory.orchestrator.models import TaskState, TaskSubmissionResult
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
)
from factory.orchestrator_api import OrchestratorApiError, TaskOperatorService


def _submit(
    service: TaskOperatorService, *, idempotency_key: str, **overrides: object
) -> TaskSubmissionResult:
    defaults: dict[str, object] = {
        "project_ref": "proj-1",
        "workstream_id": "ws-1",
        "description": "add feature X",
        "priority": "normal",
        "model_preference": None,
        "expected_result": None,
        "submitted_by": "operator",
    }
    defaults.update(overrides)
    return service.submit(idempotency_key=idempotency_key, **defaults)  # type: ignore[arg-type]


def test_submit_creates_a_queued_task(service: TaskOperatorService) -> None:
    result = _submit(service, idempotency_key="k1")
    assert result.created is True
    assert result.state is TaskState.QUEUED


def test_submit_is_idempotent_on_repeat_key(service: TaskOperatorService) -> None:
    first = _submit(service, idempotency_key="k2")
    second = _submit(service, idempotency_key="k2")
    assert second.created is False
    assert second.task_id == first.task_id


def test_get_detail_for_known_task_includes_request_metadata(
    service: TaskOperatorService,
) -> None:
    result = _submit(service, idempotency_key="k3", description="do the thing")
    detail = service.get_detail(result.task_id)
    assert detail is not None
    assert detail.task.current_state is TaskState.QUEUED
    assert detail.request is not None
    assert detail.request.description == "do the thing"


def test_get_detail_for_unknown_task_returns_none(service: TaskOperatorService) -> None:
    assert service.get_detail("no-such-task") is None


def test_get_detail_for_pre_phase3a_task_has_no_request_record(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    writer.create_task(task_id="LEGACY-1", project_id="proj-x", contract_version=1)
    service = TaskOperatorService(writer=writer, reader=reader)
    detail = service.get_detail("LEGACY-1")
    assert detail is not None
    assert detail.request is None  # never fabricated to fill the gap


def test_cancel_from_queued_walks_through_planning_and_stopping(
    service: TaskOperatorService,
) -> None:
    result = _submit(service, idempotency_key="k4")
    updated = service.cancel(result.task_id, actor="operator", reason="test_cancel")
    assert updated.current_state is TaskState.CANCELLED


def test_cancel_from_a_later_cancellable_state(
    service: TaskOperatorService, writer: _OrchestratorStateWriter
) -> None:
    result = _submit(service, idempotency_key="k5")
    writer.apply_transition(
        task_id=result.task_id,
        expected_current_state=TaskState.QUEUED,
        new_state=TaskState.PLANNING,
        cause="advance",
        actor="test",
    )
    writer.apply_transition(
        task_id=result.task_id,
        expected_current_state=TaskState.PLANNING,
        new_state=TaskState.RUNNING,
        cause="advance",
        actor="test",
    )
    updated = service.cancel(result.task_id, actor="operator", reason="test_cancel")
    assert updated.current_state is TaskState.CANCELLED


def test_cancel_unknown_task_is_rejected(service: TaskOperatorService) -> None:
    with pytest.raises(OrchestratorApiError) as excinfo:
        service.cancel("no-such-task", actor="operator", reason="x")
    assert excinfo.value.code == "TASK_NOT_FOUND"


_LEGAL_PATH_TO_TERMINAL = {
    # Each hop must be a legal 01L §3.1 edge (state/transitions.py).
    TaskState.COMPLETE: (
        TaskState.PLANNING,
        TaskState.RUNNING,
        TaskState.VERIFYING,
        TaskState.COMPLETE,
    ),
    TaskState.FAILED: (TaskState.PLANNING, TaskState.FAILED),
}


def _walk_to(writer: _OrchestratorStateWriter, task_id: str, path: tuple[TaskState, ...]) -> None:
    current = TaskState.QUEUED
    for next_state in path:
        event = writer.apply_transition(
            task_id=task_id,
            expected_current_state=current,
            new_state=next_state,
            cause="advance",
            actor="test",
        )
        assert event.accepted, f"expected {current} -> {next_state} to be a legal transition"
        current = next_state


@pytest.mark.parametrize(
    "terminal_state", [TaskState.COMPLETE, TaskState.FAILED, TaskState.CANCELLED]
)
def test_cancel_an_already_terminal_task_is_rejected(
    service: TaskOperatorService,
    writer: _OrchestratorStateWriter,
    terminal_state: TaskState,
) -> None:
    result = _submit(service, idempotency_key=f"k-terminal-{terminal_state.value}")
    if terminal_state is TaskState.CANCELLED:
        service.cancel(result.task_id, actor="operator", reason="setup")
    else:
        _walk_to(writer, result.task_id, _LEGAL_PATH_TO_TERMINAL[terminal_state])

    with pytest.raises(OrchestratorApiError) as excinfo:
        service.cancel(result.task_id, actor="operator", reason="too_late")
    assert excinfo.value.code == "ACTION_REJECTED"
