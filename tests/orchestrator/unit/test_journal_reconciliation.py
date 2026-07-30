"""Task 2.3 — startup reconciliation (CMP-JOURNAL)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from factory.orchestrator.journal.reconciliation import reconcile_startup
from factory.orchestrator.models import ReconciliationOutcome, TaskState
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
)

# state -> the legal accepted path from QUEUED needed to reach it (excluding the genesis QUEUED).
_PATH_TO: dict[TaskState, list[TaskState]] = {
    TaskState.QUEUED: [],
    TaskState.PLANNING: [TaskState.PLANNING],
    TaskState.RUNNING: [TaskState.PLANNING, TaskState.RUNNING],
    TaskState.VERIFYING: [TaskState.PLANNING, TaskState.RUNNING, TaskState.VERIFYING],
    TaskState.COMPLETE: [
        TaskState.PLANNING,
        TaskState.RUNNING,
        TaskState.VERIFYING,
        TaskState.COMPLETE,
    ],
    TaskState.FAILED: [TaskState.PLANNING, TaskState.FAILED],
    TaskState.CANCELLED: [TaskState.PLANNING, TaskState.STOPPING, TaskState.CANCELLED],
    TaskState.BLOCKED: [TaskState.PLANNING, TaskState.BLOCKED],
}


def _drive(writer: _OrchestratorStateWriter, task_id: str, target: TaskState) -> None:
    writer.create_task(task_id=task_id, project_id="PROJ-001", contract_version=1)
    current = TaskState.QUEUED
    for nxt in _PATH_TO[target]:
        event = writer.apply_transition(
            task_id=task_id,
            expected_current_state=current,
            new_state=nxt,
            cause="drive",
            actor="test",
        )
        assert event.accepted is True, f"failed to drive {current} -> {nxt}"
        current = nxt


def test_queued_task_reconciles_resumable(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    _drive(writer, "TASK-001", TaskState.QUEUED)
    assert reconcile_startup(reader, ["TASK-001"]) == {"TASK-001": ReconciliationOutcome.RESUMABLE}


def test_running_task_reconciles_blocked_no_blind_resume(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    _drive(writer, "TASK-001", TaskState.RUNNING)
    assert reconcile_startup(reader, ["TASK-001"]) == {"TASK-001": ReconciliationOutcome.BLOCKED}


def test_terminal_states_reconcile_to_resolved_outcomes(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    _drive(writer, "T-COMPLETE", TaskState.COMPLETE)
    _drive(writer, "T-CANCELLED", TaskState.CANCELLED)
    _drive(writer, "T-FAILED", TaskState.FAILED)
    outcomes = reconcile_startup(reader, ["T-COMPLETE", "T-CANCELLED", "T-FAILED"])
    assert outcomes == {
        "T-COMPLETE": ReconciliationOutcome.COMPLETED,
        "T-CANCELLED": ReconciliationOutcome.CANCELLED,
        "T-FAILED": ReconciliationOutcome.FAILED,
    }


def test_stored_state_disagreeing_with_replay_is_quarantined(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader, db_path: Path
) -> None:
    # Task genuinely folds to QUEUED; tamper the stored current_state directly (bypassing the
    # writer) to simulate corruption/an unclean write.
    _drive(writer, "TASK-001", TaskState.QUEUED)
    connection = sqlite3.connect(str(db_path))
    try:
        connection.execute(
            "UPDATE tasks SET current_state = ? WHERE task_id = ?",
            (TaskState.RUNNING.value, "TASK-001"),
        )
        connection.commit()
    finally:
        connection.close()
    assert reconcile_startup(reader, ["TASK-001"]) == {
        "TASK-001": ReconciliationOutcome.QUARANTINED
    }


def test_unknown_task_is_quarantined(reader: SQLiteOrchestratorStateReader) -> None:
    assert reconcile_startup(reader, ["TASK-404"]) == {
        "TASK-404": ReconciliationOutcome.QUARANTINED
    }
