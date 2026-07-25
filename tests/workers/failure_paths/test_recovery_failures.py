"""Task 3.4 failure-paths — reconciliation application edge cases (CMP-WORKER, R3)."""

from __future__ import annotations

import pytest

from factory.orchestrator.models import ReconciliationOutcome, TaskState
from factory.orchestrator.queue.scheduler import request_cancellation
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
)
from factory.workers.quarantine import QuarantineRegistry
from factory.workers.recovery import StartupRecovery
from factory.workers.state_integration import StateIntegration

pytestmark = pytest.mark.failure_path


def _integration(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> StateIntegration:
    return StateIntegration(writer=writer, reader=reader)


def _running(integration: StateIntegration, writer: _OrchestratorStateWriter, task_id: str) -> None:
    writer.create_task(task_id=task_id, project_id="PROJ-001", contract_version=1)
    integration.start_execution(task_id, actor="w0")


def test_stopping_task_reconciles_to_cancelled(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    integration = _integration(writer, reader)
    _running(integration, writer, "TASK-001")
    request_cancellation(writer, reader, "TASK-001", reason="op", actor="op")  # RUNNING→STOPPING

    StartupRecovery(integration=integration, quarantine=QuarantineRegistry()).recover(["TASK-001"])

    # an interrupted cancellation is safe to finish, not resume
    assert reader.get_task("TASK-001").current_state is TaskState.CANCELLED


def test_planning_task_reconciles_to_blocked(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    integration = _integration(writer, reader)
    writer.create_task(task_id="TASK-001", project_id="PROJ-001", contract_version=1)
    writer.apply_transition(
        task_id="TASK-001",
        expected_current_state=TaskState.QUEUED,
        new_state=TaskState.PLANNING,
        cause="start",
        actor="w0",
    )
    StartupRecovery(integration=integration, quarantine=QuarantineRegistry()).recover(["TASK-001"])
    assert reader.get_task("TASK-001").current_state is TaskState.BLOCKED


def test_unknown_task_is_quarantined(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    integration = _integration(writer, reader)
    registry = QuarantineRegistry()
    outcomes = StartupRecovery(integration=integration, quarantine=registry).recover(["TASK-404"])
    assert outcomes["TASK-404"] is ReconciliationOutcome.QUARANTINED
    assert registry.is_quarantined("TASK-404")


def test_blocked_task_not_resumed_on_reconcile(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    integration = _integration(writer, reader)
    _running(integration, writer, "TASK-001")
    # first reconcile → BLOCKED
    StartupRecovery(integration=integration, quarantine=QuarantineRegistry()).recover(["TASK-001"])
    assert reader.get_task("TASK-001").current_state is TaskState.BLOCKED
    # a second reconcile must keep it BLOCKED (already blocked → no-op), never RUNNING
    StartupRecovery(integration=integration, quarantine=QuarantineRegistry()).recover(["TASK-001"])
    assert reader.get_task("TASK-001").current_state is TaskState.BLOCKED


def test_crashed_task_stays_failed_across_recovery(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    integration = _integration(writer, reader)
    _running(integration, writer, "TASK-001")
    integration.fail_crashed("TASK-001", actor="rec")  # RUNNING→FAILED
    outcomes = StartupRecovery(
        integration=integration, quarantine=QuarantineRegistry()
    ).recover(["TASK-001"])
    assert outcomes["TASK-001"] is ReconciliationOutcome.FAILED
    assert reader.get_task("TASK-001").current_state is TaskState.FAILED
