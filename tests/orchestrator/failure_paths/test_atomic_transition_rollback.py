"""Task 2.2 (failure-path) — atomic transition rollback.

A transition forced to fail before commit must leave the task state and sequence unchanged and
must append no event row (the whole transaction rolls back). F-PH2-01/02 / RB-PH2-TX.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from factory.orchestrator.errors import OrchestratorError
from factory.orchestrator.models import TaskState
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
)

pytestmark = pytest.mark.failure_path


class _FailingCommitConnection:
    """Delegates to a real connection but raises on commit(), to force a pre-commit failure."""

    def __init__(self, real: sqlite3.Connection) -> None:
        self._real = real

    def execute(self, *args: object, **kwargs: object) -> sqlite3.Cursor:
        return self._real.execute(*args, **kwargs)  # type: ignore[arg-type]

    def commit(self) -> None:
        raise sqlite3.OperationalError("injected commit failure")

    def rollback(self) -> None:
        self._real.rollback()

    def close(self) -> None:
        self._real.close()


def test_forced_precommit_failure_leaves_state_and_appends_no_event(
    db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    writer = _OrchestratorStateWriter(database_path=db_path)
    reader = SQLiteOrchestratorStateReader(database_path=db_path)
    writer.create_task(task_id="TASK-001", project_id="PROJ-001", contract_version=1)

    before = reader.get_task("TASK-001")
    assert before is not None and before.current_state is TaskState.QUEUED
    events_before = len(reader.get_events("TASK-001"))

    def failing_connect(self: _OrchestratorStateWriter) -> _FailingCommitConnection:
        real = sqlite3.connect(str(self.database_path))
        real.execute("PRAGMA foreign_keys = ON")
        real.row_factory = sqlite3.Row
        return _FailingCommitConnection(real)

    monkeypatch.setattr(_OrchestratorStateWriter, "_connect", failing_connect)

    with pytest.raises(OrchestratorError, match="transition failed"):
        writer.apply_transition(
            task_id="TASK-001",
            expected_current_state=TaskState.QUEUED,
            new_state=TaskState.PLANNING,
            cause="start",
            actor="orchestrator",
        )

    # State and sequence unchanged; no event row was persisted by the failed transition.
    after = reader.get_task("TASK-001")
    assert after is not None
    assert after.current_state is TaskState.QUEUED
    assert after.sequence == 0
    assert len(reader.get_events("TASK-001")) == events_before
