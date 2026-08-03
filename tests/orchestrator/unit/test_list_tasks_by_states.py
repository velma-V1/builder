"""Phase 3B — ``list_tasks_by_states``: global (cross-workstream) task discovery by state.

Needed by the Worker Engine to find claimable QUEUED tasks and, at startup, every non-terminal
in-flight task for crash reconciliation -- neither is expressible via the existing
``list_tasks_by_workstream`` (which requires a single, already-known workstream id).
"""

from __future__ import annotations

from factory.orchestrator.models import TaskState
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
)


def test_returns_empty_tuple_for_empty_state_set(reader: SQLiteOrchestratorStateReader) -> None:
    assert reader.list_tasks_by_states(frozenset()) == ()


def test_finds_queued_tasks_across_workstreams(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    writer.create_task(task_id="t-1", project_id="p", contract_version=1, workstream_id="ws-a")
    writer.create_task(task_id="t-2", project_id="p", contract_version=1, workstream_id="ws-b")
    writer.create_task(task_id="t-3", project_id="p", contract_version=1, workstream_id=None)

    found = reader.list_tasks_by_states(frozenset({TaskState.QUEUED}))
    assert {r.task_id for r in found} == {"t-1", "t-2", "t-3"}


def test_excludes_tasks_not_in_the_requested_states(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    writer.create_task(task_id="t-queued", project_id="p", contract_version=1)
    writer.create_task(task_id="t-planning", project_id="p", contract_version=1)
    writer.apply_transition(
        task_id="t-planning",
        expected_current_state=TaskState.QUEUED,
        new_state=TaskState.PLANNING,
        cause="test",
        actor="test",
    )

    found = reader.list_tasks_by_states(frozenset({TaskState.QUEUED}))
    assert {r.task_id for r in found} == {"t-queued"}


def test_supports_multiple_states_at_once(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    writer.create_task(task_id="t-queued", project_id="p", contract_version=1)
    writer.create_task(task_id="t-planning", project_id="p", contract_version=1)
    writer.apply_transition(
        task_id="t-planning",
        expected_current_state=TaskState.QUEUED,
        new_state=TaskState.PLANNING,
        cause="test",
        actor="test",
    )

    found = reader.list_tasks_by_states(frozenset({TaskState.QUEUED, TaskState.PLANNING}))
    assert {r.task_id for r in found} == {"t-queued", "t-planning"}


def test_ordered_by_updated_at_then_task_id(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    writer.create_task(task_id="t-b", project_id="p", contract_version=1)
    writer.create_task(task_id="t-a", project_id="p", contract_version=1)

    found = reader.list_tasks_by_states(frozenset({TaskState.QUEUED}))
    # Both created at effectively the same instant -- falls back to task_id ascending.
    assert [r.task_id for r in found] == sorted(r.task_id for r in found)
