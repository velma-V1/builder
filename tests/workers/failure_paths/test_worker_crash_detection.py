"""Task 3.1 failure-paths — crash detection via health polling (CMP-WORKER)."""

from __future__ import annotations

import pytest

from factory.workers.models import WorkerState
from factory.workers.pool import WorkerPool
from tests.workers.support import FakeSpawner

pytestmark = pytest.mark.failure_path


def test_poll_health_detects_running_worker_crash(pool: WorkerPool, spawner: FakeSpawner) -> None:
    pool.assign_task("worker-1", "TASK-001")
    pool.mark_running("worker-1")
    spawner.handles[1].crash()  # process exits unexpectedly while RUNNING

    crashed = pool.poll_health()

    assert crashed == ("worker-1",)
    assert pool.get_worker_status("worker-1").state is WorkerState.DEAD


def test_poll_health_ignores_idle_and_clean_exit_of_free_slot(
    pool: WorkerPool, spawner: FakeSpawner
) -> None:
    # An IDLE slot whose (stub) process exited is not a task crash: no task is bound, so it is
    # not reported. Only ASSIGNED/RUNNING slots with an exited handle are crashes.
    spawner.handles[0].crash(exit_code=0)
    assert pool.poll_health() == ()
    assert pool.get_worker_status("worker-0").state is WorkerState.IDLE


def test_crashed_worker_reclaimable_after_detection(pool: WorkerPool, spawner: FakeSpawner) -> None:
    pool.assign_task("worker-2", "TASK-007")
    pool.mark_running("worker-2")
    spawner.handles[2].crash()
    pool.poll_health()

    fresh = pool.reclaim("worker-2")
    assert fresh.state is WorkerState.IDLE
    assert pool.get_available_worker() is not None
