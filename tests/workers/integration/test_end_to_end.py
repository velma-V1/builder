"""PH-3 integration — end-to-end dispatch→execute→finalize + multi-cycle recovery (CMP-WORKER).

Exercises the whole Worker Engine against a real runtime DB and the PH-2 single writer: the
scheduler/lease/pool read side, the executor, and state integration all cooperating. No real OS
processes (FakeSpawner), but every authoritative state change goes through _OrchestratorStateWriter.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.orchestrator.journal.reconciliation import reconcile_startup
from factory.orchestrator.models import (
    ProcessEpoch,
    ReconciliationOutcome,
    TaskState,
)
from factory.orchestrator.store.runtime_state import (
    SQLiteOrchestratorStateReader,
    _OrchestratorStateWriter,
)
from factory.workers.dispatcher import Dispatcher
from factory.workers.execution import RawWorkerEvent, TaskExecutor
from factory.workers.lease_coordinator import LeaseCoordinator
from factory.workers.models import ExecutionEventType, WorkerState
from factory.workers.pool import WorkerPool
from factory.workers.quarantine import QuarantineRegistry
from factory.workers.recovery import StartupRecovery, WorkerRecovery
from factory.workers.state_integration import StateIntegration
from tests.workers.support import FakeSpawner


def _end(code: int) -> RawWorkerEvent:
    return RawWorkerEvent(kind=ExecutionEventType.END, exit_code=code)


def _out(data: bytes) -> RawWorkerEvent:
    return RawWorkerEvent(kind=ExecutionEventType.STDOUT, data=data)


def _states(reader: SQLiteOrchestratorStateReader, ids: list[str]) -> dict[str, TaskState]:
    return {t: reader.get_task(t).current_state for t in ids}


def test_full_pipeline_dispatch_execute_finalize(
    runtime_db: Path,
    writer: _OrchestratorStateWriter,
    reader: SQLiteOrchestratorStateReader,
    spawner: FakeSpawner,
) -> None:
    epoch = ProcessEpoch.generate()
    pool = WorkerPool(spawner=spawner, size=2, process_epoch=epoch)
    coord = LeaseCoordinator.for_pool(runtime_db, epoch)
    integration = StateIntegration(writer=writer, reader=reader)
    dispatcher = Dispatcher(pool=pool, coordinator=coord)
    executor = TaskExecutor()

    ids = ["TASK-A", "TASK-B"]
    for t in ids:
        writer.create_task(task_id=t, project_id="PROJ-001", contract_version=1)
    graph = {t: frozenset() for t in ids}

    records = dispatcher.dispatch_ready(graph, _states(reader, ids))
    assert len(records) == 2

    for rec in records:
        integration.start_execution(rec.task_id, actor=rec.worker_id)
        pool.mark_running(rec.worker_id)
        assert reader.get_task(rec.task_id).current_state is TaskState.RUNNING

        result = executor.execute(rec.task_id, [_out(b"work"), _end(0)])
        event = integration.finalize(rec.task_id, result, actor=rec.worker_id)
        pool.mark_done(rec.worker_id)
        coord.release_task_lease(rec.lease)

        assert event.new_state is TaskState.VERIFYING  # success hands off, no self-certify
        assert coord.validate_current(rec.lease) is False  # lease released

    for t in ids:
        assert reader.get_task(t).current_state is TaskState.VERIFYING


def test_failed_task_pipeline(
    runtime_db: Path,
    writer: _OrchestratorStateWriter,
    reader: SQLiteOrchestratorStateReader,
    spawner: FakeSpawner,
) -> None:
    epoch = ProcessEpoch.generate()
    pool = WorkerPool(spawner=spawner, size=1, process_epoch=epoch)
    coord = LeaseCoordinator.for_pool(runtime_db, epoch)
    integration = StateIntegration(writer=writer, reader=reader)
    dispatcher = Dispatcher(pool=pool, coordinator=coord)
    executor = TaskExecutor()

    writer.create_task(task_id="TASK-X", project_id="PROJ-001", contract_version=1)
    graph = {"TASK-X": frozenset()}
    (rec,) = dispatcher.dispatch_ready(graph, _states(reader, ["TASK-X"]))
    integration.start_execution(rec.task_id, actor=rec.worker_id)
    pool.mark_running(rec.worker_id)

    result = executor.execute(rec.task_id, [_out(b"boom"), _end(2)])
    integration.finalize(rec.task_id, result, actor=rec.worker_id)
    coord.release_task_lease(rec.lease)

    assert reader.get_task("TASK-X").current_state is TaskState.FAILED


def test_crash_recovery_reclaims_and_frees_capacity(
    runtime_db: Path,
    writer: _OrchestratorStateWriter,
    reader: SQLiteOrchestratorStateReader,
    spawner: FakeSpawner,
) -> None:
    epoch = ProcessEpoch.generate()
    pool = WorkerPool(spawner=spawner, size=1, process_epoch=epoch)
    coord = LeaseCoordinator.for_pool(runtime_db, epoch)
    integration = StateIntegration(writer=writer, reader=reader)
    dispatcher = Dispatcher(pool=pool, coordinator=coord)

    writer.create_task(task_id="TASK-C", project_id="PROJ-001", contract_version=1)
    (rec,) = dispatcher.dispatch_ready({"TASK-C": frozenset()}, _states(reader, ["TASK-C"]))
    integration.start_execution(rec.task_id, actor=rec.worker_id)
    pool.mark_running(rec.worker_id)

    spawner.handles[0].crash()  # worker dies mid-execution
    failed = WorkerRecovery(pool=pool, integration=integration).recover_crashed()

    assert failed == ("TASK-C",)
    assert reader.get_task("TASK-C").current_state is TaskState.FAILED
    assert pool.get_available_worker() is not None
    assert pool.get_worker_status("worker-0").state is WorkerState.IDLE


def test_three_cycle_crash_recovery_keeps_state_consistent(
    writer: _OrchestratorStateWriter, reader: SQLiteOrchestratorStateReader
) -> None:
    integration = StateIntegration(writer=writer, reader=reader)
    writer.create_task(task_id="TASK-1", project_id="PROJ-001", contract_version=1)
    integration.start_execution("TASK-1", actor="w0")  # RUNNING

    for _cycle in range(3):
        # simulate a process restart: reconcile applies RUNNING → BLOCKED (R3, no blind resume)
        outcomes = StartupRecovery(
            integration=integration, quarantine=QuarantineRegistry()
        ).recover(["TASK-1"])
        assert outcomes["TASK-1"] is ReconciliationOutcome.BLOCKED
        assert reader.get_task("TASK-1").current_state is TaskState.BLOCKED

        # journal replay must always agree with stored state — never QUARANTINED
        replay = reconcile_startup(reader, ["TASK-1"])["TASK-1"]
        assert replay is not ReconciliationOutcome.QUARANTINED

        # operator explicitly resumes BLOCKED → RUNNING (legal), setting up the next cycle
        writer.apply_transition(
            task_id="TASK-1",
            expected_current_state=TaskState.BLOCKED,
            new_state=TaskState.RUNNING,
            cause="operator_resume",
            actor="op",
        )
        assert reader.get_task("TASK-1").current_state is TaskState.RUNNING

    # after three full cycles, history is still internally consistent
    events = reader.get_events("TASK-1")
    accepted = [e for e in events if e.accepted]
    assert accepted[-1].new_state is TaskState.RUNNING
    assert [e.sequence for e in accepted] == sorted(e.sequence for e in accepted)


@pytest.mark.security
def test_leases_are_epoch_fenced_across_pool_restart(
    runtime_db: Path,
    writer: _OrchestratorStateWriter,
    reader: SQLiteOrchestratorStateReader,
    spawner: FakeSpawner,
) -> None:
    # Pool A dispatches under epoch A; a restart as epoch B must reject A's live lease (SEC-PH3-02).
    epoch_a = ProcessEpoch.generate()
    pool_a = WorkerPool(spawner=spawner, size=1, process_epoch=epoch_a)
    coord_a = LeaseCoordinator.for_pool(runtime_db, epoch_a)
    dispatcher = Dispatcher(pool=pool_a, coordinator=coord_a)
    writer.create_task(task_id="TASK-F", project_id="PROJ-001", contract_version=1)
    (rec,) = dispatcher.dispatch_ready({"TASK-F": frozenset()}, _states(reader, ["TASK-F"]))

    coord_b = LeaseCoordinator.for_pool(runtime_db, ProcessEpoch.generate())
    assert coord_a.validate_current(rec.lease) is True
    assert coord_b.validate_current(rec.lease) is False  # fenced by epoch
