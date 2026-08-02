"""Phase 3A — _OrchestratorStateWriter.submit_task_request(): idempotent task-request submission.

project_id and workstream_id remain distinct: the submitted project/repository reference
becomes the task's authoritative project_id (no separate project registry exists in this
phase), while workstream_id is passed through explicitly, never inferred.
"""

from __future__ import annotations

import threading

import pytest

from factory.orchestrator.models import TaskState, TaskSubmissionResult
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
)


def _submit(
    writer: _OrchestratorStateWriter,
    *,
    idempotency_key: str,
    project_ref: str = "proj-1",
    workstream_id: str = "ws-1",
    description: str = "add feature X",
    priority: str = "normal",
    model_preference: str | None = None,
    expected_result: str | None = None,
    submitted_by: str = "operator",
) -> TaskSubmissionResult:
    return writer.submit_task_request(
        project_ref=project_ref,
        workstream_id=workstream_id,
        description=description,
        priority=priority,
        model_preference=model_preference,
        expected_result=expected_result,
        submitted_by=submitted_by,
        idempotency_key=idempotency_key,
    )


def test_submit_creates_a_queued_task_and_a_matching_request_record(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    result = _submit(writer, idempotency_key="key-1", project_ref="proj-A", workstream_id="ws-1")
    assert result.created is True
    assert result.state is TaskState.QUEUED

    task = reader.get_task(result.task_id)
    assert task is not None
    assert task.project_id == "proj-A"  # project_ref becomes the authoritative project_id
    assert task.workstream_id == "ws-1"
    assert task.current_state is TaskState.QUEUED

    request = reader.get_task_request(result.task_id)
    assert request is not None
    assert request.description == "add feature X"
    assert request.priority == "normal"
    assert request.idempotency_key == "key-1"


def test_submit_persists_optional_fields(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    result = _submit(
        writer,
        idempotency_key="key-2",
        model_preference="devstral-24b",
        expected_result="a passing test suite",
    )
    request = reader.get_task_request(result.task_id)
    assert request is not None
    assert request.model_preference == "devstral-24b"
    assert request.expected_result == "a passing test suite"


def test_submit_with_same_idempotency_key_returns_the_original_task_not_a_duplicate(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    first = _submit(writer, idempotency_key="repeat-me", description="first attempt")
    second = _submit(writer, idempotency_key="repeat-me", description="a different description")

    assert second.created is False
    assert second.task_id == first.task_id
    assert second.state == first.state

    # No duplicate task and no duplicate request row -- the second call's (different)
    # description was never persisted; the original request is untouched.
    request = reader.get_task_request(first.task_id)
    assert request is not None
    assert request.description == "first attempt"


def test_submit_with_different_idempotency_keys_creates_distinct_tasks(
    writer: _OrchestratorStateWriter,
) -> None:
    first = _submit(writer, idempotency_key="key-a")
    second = _submit(writer, idempotency_key="key-b")
    assert first.task_id != second.task_id
    assert first.created is True
    assert second.created is True


def test_concurrent_submission_with_the_same_idempotency_key_creates_only_one_task(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    results: list[TaskSubmissionResult] = []
    errors: list[BaseException] = []

    def _attempt() -> None:
        try:
            results.append(_submit(writer, idempotency_key="race-key"))
        except BaseException as exc:  # capture for the assertion below
            errors.append(exc)

    threads = [threading.Thread(target=_attempt) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"unexpected errors during concurrent submission: {errors}"
    task_ids = {r.task_id for r in results}
    assert len(task_ids) == 1, "exactly one task must be created despite concurrent submissions"
    assert sum(1 for r in results if r.created) == 1


@pytest.mark.parametrize("priority", ["low", "normal", "high"])
def test_submit_persists_the_requested_priority(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader, priority: str
) -> None:
    result = _submit(writer, idempotency_key=f"key-{priority}", priority=priority)
    request = reader.get_task_request(result.task_id)
    assert request is not None
    assert request.priority == priority
