"""Task 2.3 (failure-path) — crash consistency + no blind resume.

Simulates an unclean shutdown mid-lifecycle: after driving a task to a non-terminal state, a fresh
reader (new connections, as a restarted process would open) reconciles the task without ever
silently resuming it. SQLite's WAL crash-consistency guarantees each committed transition is
fully applied or not at all; reconciliation then fails closed to BLOCKED. F-PH2-01/09.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.orchestrator.journal.reconciliation import reconcile_startup
from factory.orchestrator.models import ReconciliationOutcome, TaskState
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
)

pytestmark = pytest.mark.failure_path


def test_restart_does_not_silently_resume_inflight_tasks(db_path: Path) -> None:
    writer = _OrchestratorStateWriter(database_path=db_path)
    # Two in-flight tasks at non-terminal states, one queued.
    writer.create_task(task_id="T-RUN", project_id="P", contract_version=1)
    writer.apply_transition(
        task_id="T-RUN",
        expected_current_state=TaskState.QUEUED,
        new_state=TaskState.PLANNING,
        cause="c",
        actor="a",
    )
    writer.apply_transition(
        task_id="T-RUN",
        expected_current_state=TaskState.PLANNING,
        new_state=TaskState.RUNNING,
        cause="c",
        actor="a",
    )
    writer.create_task(task_id="T-QUEUED", project_id="P", contract_version=1)

    # Simulate a restart: brand-new reader over the same on-disk DB.
    fresh_reader = SQLiteOrchestratorStateReader(database_path=db_path)
    outcomes = reconcile_startup(fresh_reader, ["T-RUN", "T-QUEUED"])

    # The in-flight RUNNING task is never RESUMABLE (no blind resume); only the untouched QUEUED
    # task may resume.
    assert outcomes["T-RUN"] == ReconciliationOutcome.BLOCKED
    assert outcomes["T-QUEUED"] == ReconciliationOutcome.RESUMABLE
    assert ReconciliationOutcome.RESUMABLE not in {
        outcomes[t] for t in ("T-RUN",)
    }  # explicit: no in-flight resume
