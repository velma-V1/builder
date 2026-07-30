"""Task 3.1 — WorkerPool + process lifecycle (CMP-WORKER)."""

from __future__ import annotations

import pytest

from factory.orchestrator.models import ProcessEpoch
from factory.workers.errors import WorkerEngineError
from factory.workers.models import WorkerState
from factory.workers.pool import WorkerPool
from tests.workers.conftest import FakeSpawner


def test_pool_spawns_size_idle_workers(spawner: FakeSpawner) -> None:
    pool = WorkerPool(spawner=spawner, size=4)
    assert len(spawner.handles) == 4
    for index in range(4):
        status = pool.get_worker_status(f"worker-{index}")
        assert status.state is WorkerState.IDLE
        assert status.task_id is None


def test_pool_rejects_zero_size(spawner: FakeSpawner) -> None:
    with pytest.raises(WorkerEngineError, match="POOL_SIZE_INVALID"):
        WorkerPool(spawner=spawner, size=0)


def test_process_epoch_is_immutable_and_stamped_on_workers(spawner: FakeSpawner) -> None:
    epoch = ProcessEpoch.generate()
    pool = WorkerPool(spawner=spawner, size=2, process_epoch=epoch)
    assert pool.process_epoch is epoch
    assert pool.get_worker_status("worker-0").process_epoch == epoch.value


def test_each_pool_generates_distinct_epoch(spawner: FakeSpawner) -> None:
    a = WorkerPool(spawner=FakeSpawner(), size=1)
    b = WorkerPool(spawner=FakeSpawner(), size=1)
    assert a.process_epoch.value != b.process_epoch.value


def test_get_available_worker_returns_deterministic_first_idle(pool: WorkerPool) -> None:
    assert pool.get_available_worker() is not None
    assert pool.get_available_worker().worker_id == "worker-0"


def test_assign_task_moves_idle_to_assigned(pool: WorkerPool) -> None:
    pool.assign_task("worker-0", "TASK-001")
    status = pool.get_worker_status("worker-0")
    assert status.state is WorkerState.ASSIGNED
    assert status.task_id == "TASK-001"


def test_assigned_worker_not_returned_as_available(pool: WorkerPool) -> None:
    pool.assign_task("worker-0", "TASK-001")
    assert pool.get_available_worker().worker_id == "worker-1"


def test_assign_rejects_duplicate_task_on_live_worker(pool: WorkerPool) -> None:
    pool.assign_task("worker-0", "TASK-001")
    with pytest.raises(WorkerEngineError, match="TASK_ALREADY_ASSIGNED"):
        pool.assign_task("worker-1", "TASK-001")


def test_full_slot_lifecycle_idle_to_done(pool: WorkerPool) -> None:
    pool.assign_task("worker-0", "TASK-001")
    pool.mark_running("worker-0")
    assert pool.get_worker_status("worker-0").state is WorkerState.RUNNING
    pool.mark_done("worker-0")
    assert pool.get_worker_status("worker-0").state is WorkerState.DONE


def test_illegal_transition_running_skip_rejected(pool: WorkerPool) -> None:
    with pytest.raises(WorkerEngineError, match="ILLEGAL_WORKER_TRANSITION"):
        pool.mark_running("worker-0")  # IDLE → RUNNING skips ASSIGNED


def test_find_by_task_returns_live_binding(pool: WorkerPool) -> None:
    pool.assign_task("worker-2", "TASK-042")
    found = pool.find_by_task("TASK-042")
    assert found is not None and found.worker_id == "worker-2"


def test_find_by_task_ignores_terminal_slots(pool: WorkerPool) -> None:
    pool.assign_task("worker-0", "TASK-001")
    pool.mark_running("worker-0")
    pool.mark_done("worker-0")
    assert pool.find_by_task("TASK-001") is None


def test_reclaim_replaces_terminal_slot_with_fresh_idle(
    pool: WorkerPool, spawner: FakeSpawner
) -> None:
    pool.assign_task("worker-0", "TASK-001")
    pool.mark_running("worker-0")
    pool.mark_done("worker-0")
    before = len(spawner.handles)
    fresh = pool.reclaim("worker-0")
    assert fresh.state is WorkerState.IDLE
    assert fresh.task_id is None
    assert len(spawner.handles) == before + 1  # a NEW handle, not the old one


def test_reclaim_rejects_live_slot(pool: WorkerPool) -> None:
    pool.assign_task("worker-0", "TASK-001")
    with pytest.raises(WorkerEngineError, match="WORKER_NOT_TERMINAL"):
        pool.reclaim("worker-0")


def test_get_status_unknown_worker_raises(pool: WorkerPool) -> None:
    with pytest.raises(WorkerEngineError, match="WORKER_NOT_FOUND"):
        pool.get_worker_status("worker-999")


def test_shutdown_graceful_terminates_and_marks_terminal(
    pool: WorkerPool, spawner: FakeSpawner
) -> None:
    pool.assign_task("worker-0", "TASK-001")
    pool.mark_running("worker-0")
    pool.shutdown(graceful=True)
    assert all(h.terminated for h in spawner.handles)
    assert all(not h.killed for h in spawner.handles)
    for index in range(4):
        assert pool.get_worker_status(f"worker-{index}").state is WorkerState.DEAD


def test_shutdown_nongraceful_kills(pool: WorkerPool, spawner: FakeSpawner) -> None:
    pool.shutdown(graceful=False)
    assert all(h.killed for h in spawner.handles)


def test_shutdown_is_idempotent(pool: WorkerPool) -> None:
    pool.shutdown(graceful=True)
    pool.shutdown(graceful=True)  # must not raise on already-terminal slots
    assert pool.get_worker_status("worker-0").state is WorkerState.DEAD
