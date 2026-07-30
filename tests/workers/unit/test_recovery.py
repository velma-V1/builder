"""Task 3.4 — recovery, retry policy, quarantine, startup reconciliation (CMP-WORKER)."""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.orchestrator.models import ProcessEpoch, ReconciliationOutcome, TaskState
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
)
from factory.workers.errors import WorkerEngineError
from factory.workers.models import WorkerState
from factory.workers.pool import WorkerPool
from factory.workers.quarantine import QuarantineRegistry
from factory.workers.recovery import RetryPolicy, StartupRecovery, WorkerRecovery
from factory.workers.state_integration import StateIntegration
from tests.workers.conftest import FakeSpawner


def _integration(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> StateIntegration:
    return StateIntegration(writer=writer, reader=reader)


def _running(integration: StateIntegration, writer: _OrchestratorStateWriter, task_id: str) -> None:
    writer.create_task(task_id=task_id, project_id="PROJ-001", contract_version=1)
    integration.start_execution(task_id, actor="w0")


# ---- RetryPolicy --------------------------------------------------------------------------


def test_retry_backoff_is_exponential() -> None:
    policy = RetryPolicy(max_attempts=3, base_delay_seconds=1.0)
    assert [policy.backoff_for(a) for a in (1, 2, 3)] == [1.0, 2.0, 4.0]


def test_retry_exhausted_after_max_attempts() -> None:
    policy = RetryPolicy(max_attempts=3)
    assert policy.is_exhausted(3) is False
    assert policy.is_exhausted(4) is True


def test_retry_rejects_invalid_attempt() -> None:
    with pytest.raises(WorkerEngineError, match="RETRY_ATTEMPT_INVALID"):
        RetryPolicy().backoff_for(0)


# ---- QuarantineRegistry -------------------------------------------------------------------


def test_quarantine_records_and_dedups() -> None:
    reg = QuarantineRegistry()
    first = reg.record("TASK-001", "state_replay_mismatch")
    dup = reg.record("TASK-001", "state_replay_mismatch")
    assert first is dup
    assert len(reg.entries) == 1


def test_quarantine_is_quarantined() -> None:
    reg = QuarantineRegistry()
    reg.record("TASK-001", "reason")
    assert reg.is_quarantined("TASK-001") is True
    assert reg.is_quarantined("TASK-999") is False


# ---- WorkerRecovery -----------------------------------------------------------------------


def test_recover_crashed_fails_bound_task_and_reclaims(
    runtime_db: Path,
    writer: _OrchestratorStateWriter,
    reader: SQLiteOrchestratorStateReader,
    spawner: FakeSpawner,
) -> None:
    integration = _integration(writer, reader)
    pool = WorkerPool(spawner=spawner, size=2, process_epoch=ProcessEpoch.generate())
    _running(integration, writer, "TASK-001")
    pool.assign_task("worker-0", "TASK-001")
    pool.mark_running("worker-0")
    spawner.handles[0].crash()

    failed = WorkerRecovery(pool=pool, integration=integration).recover_crashed()

    assert failed == ("TASK-001",)
    assert reader.get_task("TASK-001").current_state is TaskState.FAILED
    assert pool.get_worker_status("worker-0").state is WorkerState.IDLE  # slot reclaimed
    assert pool.get_available_worker() is not None


def test_recover_crashed_reclaims_untasked_slot_silently(
    runtime_db: Path,
    writer: _OrchestratorStateWriter,
    reader: SQLiteOrchestratorStateReader,
    spawner: FakeSpawner,
) -> None:
    integration = _integration(writer, reader)
    pool = WorkerPool(spawner=spawner, size=1, process_epoch=ProcessEpoch.generate())
    spawner.handles[0].crash(exit_code=0)  # IDLE slot's stub exits; no bound task → not a crash
    failed = WorkerRecovery(pool=pool, integration=integration).recover_crashed()
    assert failed == ()


# ---- StartupRecovery ----------------------------------------------------------------------


def test_startup_running_reconciles_to_blocked_no_resume(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    integration = _integration(writer, reader)
    _running(integration, writer, "TASK-001")  # RUNNING

    outcomes = StartupRecovery(integration=integration, quarantine=QuarantineRegistry()).recover(
        ["TASK-001"]
    )

    assert outcomes["TASK-001"] is ReconciliationOutcome.BLOCKED
    # R3: never silently back to RUNNING
    assert reader.get_task("TASK-001").current_state is TaskState.BLOCKED


def test_startup_queued_stays_queued(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    integration = _integration(writer, reader)
    writer.create_task(task_id="TASK-001", project_id="PROJ-001", contract_version=1)  # QUEUED
    outcomes = StartupRecovery(integration=integration, quarantine=QuarantineRegistry()).recover(
        ["TASK-001"]
    )
    assert outcomes["TASK-001"] is ReconciliationOutcome.RESUMABLE
    assert reader.get_task("TASK-001").current_state is TaskState.QUEUED
