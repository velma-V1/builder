"""Task 2.5 — dependency-gated readiness + cancellation mechanics (CMP-TASKENG)."""

from __future__ import annotations

from factory.orchestrator.models import TaskState
from factory.orchestrator.queue.scheduler import (
    TaskScheduler,
    finalize_cancellation,
    request_cancellation,
)
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
)


def test_task_with_incomplete_dependency_is_not_ready() -> None:
    graph = {"TASK-002": frozenset({"TASK-001"})}
    states = {"TASK-001": TaskState.RUNNING, "TASK-002": TaskState.QUEUED}
    assert TaskScheduler().ready_tasks(graph, states) == ()


def test_task_with_no_dependencies_is_always_ready() -> None:
    graph = {"TASK-001": frozenset()}
    states = {"TASK-001": TaskState.QUEUED}
    assert TaskScheduler().ready_tasks(graph, states) == ("TASK-001",)


def test_task_with_completed_dependency_is_ready() -> None:
    graph = {"TASK-002": frozenset({"TASK-001"})}
    states = {"TASK-001": TaskState.COMPLETE, "TASK-002": TaskState.QUEUED}
    assert TaskScheduler().ready_tasks(graph, states) == ("TASK-002",)


def test_ordering_is_deterministic_by_dependency_count_then_id() -> None:
    graph = {
        "TASK-C": frozenset({"TASK-X", "TASK-Y"}),
        "TASK-A": frozenset(),
        "TASK-B": frozenset(),
    }
    states = {
        "TASK-X": TaskState.COMPLETE,
        "TASK-Y": TaskState.COMPLETE,
        "TASK-A": TaskState.QUEUED,
        "TASK-B": TaskState.QUEUED,
        "TASK-C": TaskState.QUEUED,
    }
    result = TaskScheduler().ready_tasks(graph, states)
    # TASK-A, TASK-B (0 deps, id-ascending) before TASK-C (2 deps).
    assert result == ("TASK-A", "TASK-B", "TASK-C")


def test_ordering_is_stable_across_repeated_calls() -> None:
    graph = {"TASK-B": frozenset(), "TASK-A": frozenset()}
    states = {"TASK-A": TaskState.QUEUED, "TASK-B": TaskState.QUEUED}
    scheduler = TaskScheduler()
    first = scheduler.ready_tasks(graph, states)
    second = scheduler.ready_tasks(graph, states)
    assert first == second == ("TASK-A", "TASK-B")


def test_request_then_finalize_cancellation_drives_stopping_then_cancelled(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    writer.create_task(task_id="TASK-001", project_id="PROJ-001", contract_version=1)
    # Transition to PLANNING first (QUEUED → PLANNING is allowed)
    writer.apply_transition(
        task_id="TASK-001",
        expected_current_state=TaskState.QUEUED,
        new_state=TaskState.PLANNING,
        cause="planning",
        actor="system",
    )
    # Then request cancellation (PLANNING → STOPPING is allowed)
    stopping_event = request_cancellation(writer, reader, "TASK-001", "user requested", "operator")
    assert stopping_event.accepted is True
    assert stopping_event.new_state is TaskState.STOPPING

    cancelled_event = finalize_cancellation(writer, reader, "TASK-001", "operator")
    assert cancelled_event.accepted is True
    assert cancelled_event.new_state is TaskState.CANCELLED
    record = reader.get_task("TASK-001")
    assert record is not None and record.current_state is TaskState.CANCELLED


def test_cancellation_of_terminal_task_is_rejected(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    writer.create_task(task_id="TASK-001", project_id="PROJ-001", contract_version=1)
    request_cancellation(writer, reader, "TASK-001", "r", "a")
    finalize_cancellation(writer, reader, "TASK-001", "a")  # now CANCELLED (terminal)
    event = request_cancellation(writer, reader, "TASK-001", "r2", "a")
    assert event.accepted is False  # CANCELLED has no legal outgoing transitions
