"""WorkerPool: spawn, track, supervise N worker slots (PH-3, CMP-WORKER, Task 3.1).

The pool owns process lifecycle only. It performs NO authoritative task-state writes — those are
routed through the PH-2 single-writer by StateIntegration (Task 3.3). A pool run is stamped with an
immutable ``ProcessEpoch`` at construction so every lease acquired under this pool is rejected as
stale after a restart (R4, cross-restart fencing).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from factory.orchestrator.models import ProcessEpoch
from factory.workers.errors import WorkerEngineError
from factory.workers.lifecycle import is_legal
from factory.workers.models import (
    TERMINAL_WORKER_STATES,
    WorkerState,
    WorkerStatus,
)
from factory.workers.process import ProcessSpawner, WorkerProcess


@dataclass(slots=True)
class WorkerPool:
    """Manages ``size`` worker slots spawned via an injected ``ProcessSpawner``.

    Invariants:
      - one ``ProcessEpoch`` per pool, generated at construction, immutable for its lifetime;
      - a task is bound to at most one live (non-terminal) slot at a time;
      - slot transitions obey ``lifecycle.is_legal`` (no illegal skips or in-place resurrection).
    """

    spawner: ProcessSpawner
    size: int = 4
    process_epoch: ProcessEpoch = field(default_factory=ProcessEpoch.generate)
    _workers: dict[str, WorkerProcess] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if self.size < 1:
            raise WorkerEngineError("POOL_SIZE_INVALID", f"size must be >= 1, got {self.size}")
        for index in range(self.size):
            worker_id = f"worker-{index}"
            handle = self.spawner.spawn(worker_id)
            self._workers[worker_id] = WorkerProcess(
                worker_id=worker_id,
                handle=handle,
                process_epoch=self.process_epoch.value,
            )

    # ---- queries (read-only) -------------------------------------------------------------

    def get_available_worker(self) -> WorkerProcess | None:
        """Return an IDLE worker in deterministic worker-id order, or None if none free."""
        for worker_id in sorted(self._workers):
            worker = self._workers[worker_id]
            if worker.state is WorkerState.IDLE:
                return worker
        return None

    def get_worker_status(self, worker_id: str) -> WorkerStatus:
        worker = self._require(worker_id)
        return WorkerStatus(
            worker_id=worker.worker_id,
            state=worker.state,
            pid=worker.pid,
            task_id=worker.task_id,
            process_epoch=worker.process_epoch,
        )

    def find_by_task(self, task_id: str) -> WorkerProcess | None:
        """Return the live (non-terminal) worker bound to ``task_id``, or None."""
        for worker_id in sorted(self._workers):
            worker = self._workers[worker_id]
            if worker.task_id == task_id and worker.state not in TERMINAL_WORKER_STATES:
                return worker
        return None

    # ---- slot lifecycle transitions ------------------------------------------------------

    def assign_task(self, worker_id: str, task_id: str) -> None:
        """Bind ``task_id`` to an IDLE worker: IDLE → ASSIGNED."""
        worker = self._require(worker_id)
        if self.find_by_task(task_id) is not None:
            raise WorkerEngineError(
                "TASK_ALREADY_ASSIGNED", f"task {task_id} already bound to a live worker"
            )
        self._transition(worker, WorkerState.ASSIGNED)
        worker.task_id = task_id

    def mark_running(self, worker_id: str) -> None:
        """ASSIGNED → RUNNING once the task contract has been dispatched to the process."""
        self._transition(self._require(worker_id), WorkerState.RUNNING)

    def mark_done(self, worker_id: str) -> None:
        """RUNNING → DONE; the slot is terminal and must be reclaimed, not reused in place."""
        self._transition(self._require(worker_id), WorkerState.DONE)

    def mark_dead(self, worker_id: str) -> None:
        """ASSIGNED/RUNNING → DEAD on crash detection; slot is terminal."""
        self._transition(self._require(worker_id), WorkerState.DEAD)

    def reclaim(self, worker_id: str) -> WorkerProcess:
        """Replace a terminal (DONE/DEAD) slot with a fresh IDLE worker + new process handle.

        Reclamation allocates a NEW process handle rather than resurrecting the old one, so a
        crashed process is never silently reused (spec §Worker Crash Recovery).
        """
        worker = self._require(worker_id)
        if worker.state not in TERMINAL_WORKER_STATES:
            raise WorkerEngineError(
                "WORKER_NOT_TERMINAL",
                f"worker {worker_id} in {worker.state}, cannot reclaim a live slot",
            )
        handle = self.spawner.spawn(worker_id)
        fresh = WorkerProcess(
            worker_id=worker_id,
            handle=handle,
            process_epoch=self.process_epoch.value,
        )
        self._workers[worker_id] = fresh
        return fresh

    # ---- health supervision --------------------------------------------------------------

    def poll_health(self) -> tuple[str, ...]:
        """Detect crashed workers (process exited while ASSIGNED/RUNNING).

        Returns the worker-ids transitioned to DEAD, in deterministic order. A worker whose
        handle has exited while it still owns a task is a crash (heartbeat_loss); the slot is
        marked DEAD so the caller can fail the task and reclaim the slot.
        """
        crashed: list[str] = []
        for worker_id in sorted(self._workers):
            worker = self._workers[worker_id]
            live = worker.state in (WorkerState.ASSIGNED, WorkerState.RUNNING)
            if live and worker.handle.poll() is not None:
                self._transition(worker, WorkerState.DEAD)
                crashed.append(worker_id)
        return tuple(crashed)

    # ---- shutdown ------------------------------------------------------------------------

    def shutdown(self, *, graceful: bool = True) -> None:
        """Terminate all live workers. Graceful → terminate(); non-graceful → kill().

        Idempotent: terminal slots are skipped. After shutdown every slot is terminal.
        """
        for worker_id in sorted(self._workers):
            worker = self._workers[worker_id]
            if worker.state in TERMINAL_WORKER_STATES:
                continue
            if graceful:
                worker.handle.terminate()
            else:
                worker.handle.kill()
            # a live slot at shutdown is treated as DEAD (its in-flight work, if any, is not
            # trusted to have completed); ASSIGNED/RUNNING → DEAD is legal, IDLE is forced.
            if worker.state in (WorkerState.ASSIGNED, WorkerState.RUNNING):
                self._transition(worker, WorkerState.DEAD)
            else:
                worker.state = WorkerState.DEAD

    # ---- internals -----------------------------------------------------------------------

    def _require(self, worker_id: str) -> WorkerProcess:
        worker = self._workers.get(worker_id)
        if worker is None:
            raise WorkerEngineError("WORKER_NOT_FOUND", f"no worker {worker_id} in pool")
        return worker

    def _transition(self, worker: WorkerProcess, new_state: WorkerState) -> None:
        if not is_legal(worker.state, new_state):
            raise WorkerEngineError(
                "ILLEGAL_WORKER_TRANSITION",
                f"worker {worker.worker_id}: {worker.state} → {new_state} is not permitted",
            )
        worker.state = new_state
