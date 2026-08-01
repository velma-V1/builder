"""Task 2.2 (security) — read-only state access + append-only journal enforcement.

SEC-PH2-01: a mode=ro reader cannot mutate the runtime-state DB.
SEC-PH2-02: the append-only triggers reject UPDATE/DELETE on task_state_events even via a
writable connection (THR-PH2-02, REGR-0002).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from factory.orchestrator.models import TaskState
from factory.orchestrator.store.runtime_state import (
    _connect_readonly,
    _OrchestratorStateWriter,
)

pytestmark = pytest.mark.security


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO tasks (task_id, project_id, contract_version, current_state, sequence, "
        "updated_at) VALUES ('X', 'P', 1, 'QUEUED', 0, 'now')",
        "UPDATE tasks SET current_state = 'RUNNING' WHERE task_id = 'TASK-001'",
        "DELETE FROM tasks WHERE task_id = 'TASK-001'",
        "CREATE TABLE evil (x)",
        "DROP TABLE tasks",
        "ALTER TABLE tasks ADD COLUMN evil TEXT",
        "UPDATE tasks SET workstream_id = 'ws-evil' WHERE task_id = 'TASK-001'",
    ],
)
def test_read_only_reader_denies_mutation(
    writer: _OrchestratorStateWriter, db_path: Path, statement: str
) -> None:
    writer.create_task(task_id="TASK-001", project_id="PROJ-001", contract_version=1)
    connection = _connect_readonly(db_path)
    try:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute(statement)
    finally:
        connection.close()


def test_append_only_trigger_rejects_update_on_events(
    writer: _OrchestratorStateWriter, db_path: Path
) -> None:
    # SEC-PH2-02: even a fully writable connection cannot rewrite an event row.
    writer.create_task(task_id="TASK-001", project_id="PROJ-001", contract_version=1)
    connection = sqlite3.connect(str(db_path))
    try:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("UPDATE task_state_events SET new_state = 'RUNNING'")
    finally:
        connection.close()


def test_append_only_trigger_rejects_delete_on_events(
    writer: _OrchestratorStateWriter, db_path: Path
) -> None:
    writer.create_task(task_id="TASK-001", project_id="PROJ-001", contract_version=1)
    writer.apply_transition(
        task_id="TASK-001",
        expected_current_state=TaskState.QUEUED,
        new_state=TaskState.PLANNING,
        cause="c",
        actor="a",
    )
    connection = sqlite3.connect(str(db_path))
    try:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM task_state_events")
    finally:
        connection.close()
