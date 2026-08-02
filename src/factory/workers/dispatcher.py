"""Task dispatch: ready → lease → assign (PH-3, CMP-WORKER, Task 3.2).

The Dispatcher is the read-side entry into the Worker Engine. It consumes the PH-2 scheduler's
deterministic readiness and, for each dispatchable QUEUED task with free capacity, acquires a TASK
lease BEFORE binding a worker slot (fencing before execution) and returns a `DispatchRecord`. It
writes NO authoritative task state — moving QUEUED→RUNNING is Task 3.3's responsibility via the PH-2
single writer, only AFTER the contract has actually been handed to the process.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from factory.orchestrator.models import Lease, TaskState
from factory.orchestrator.queue.scheduler import TaskScheduler
from factory.workers.lease_coordinator import LeaseCoordinator
from factory.workers.pool import WorkerPool


@dataclass(frozen=True, slots=True)
class DispatchRecord:
    """Result of binding one ready task to one worker under a fresh lease."""

    task_id: str
    worker_id: str
    lease: Lease


@dataclass(slots=True)
class Dispatcher:
    """Binds ready QUEUED tasks to free workers, one lease each, up to available capacity."""

    pool: WorkerPool
    coordinator: LeaseCoordinator
    scheduler: TaskScheduler = field(default_factory=TaskScheduler)

    def dispatch_ready(
        self,
        dependency_graph: Mapping[str, frozenset[str]],
        states: Mapping[str, TaskState],
    ) -> tuple[DispatchRecord, ...]:
        """Dispatch as many ready QUEUED tasks as there are idle workers, deterministically.

        A task already bound to a live worker is skipped (no double dispatch). Capacity is
        exhausted the moment no idle worker remains — remaining ready tasks wait for the next call.
        """
        records: list[DispatchRecord] = []
        for task_id in self.scheduler.ready_tasks(dependency_graph, states):
            if states.get(task_id) is not TaskState.QUEUED:
                continue
            if self.pool.find_by_task(task_id) is not None:
                continue
            worker = self.pool.get_available_worker()
            if worker is None:
                break  # no capacity; leave the rest for a later pass
            lease = self.coordinator.acquire_task_lease(task_id, worker_pid=worker.pid)
            self.pool.assign_task(worker.worker_id, task_id)
            records.append(DispatchRecord(task_id=task_id, worker_id=worker.worker_id, lease=lease))
        return tuple(records)
