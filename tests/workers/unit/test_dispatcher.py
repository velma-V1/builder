"""Task 3.2 — Dispatcher: ready → lease → assign (CMP-WORKER)."""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.orchestrator.models import ProcessEpoch, TaskState
from factory.workers.dispatcher import Dispatcher
from factory.workers.lease_coordinator import LeaseCoordinator
from factory.workers.models import WorkerState
from factory.workers.pool import WorkerPool
from tests.workers.conftest import FakeSpawner


@pytest.fixture
def dispatcher(runtime_db: Path, spawner: FakeSpawner) -> Dispatcher:
    epoch = ProcessEpoch.generate()
    pool = WorkerPool(spawner=spawner, size=2, process_epoch=epoch)
    coord = LeaseCoordinator.for_pool(runtime_db, epoch)
    return Dispatcher(pool=pool, coordinator=coord)


def test_dispatch_binds_ready_queued_task(dispatcher: Dispatcher) -> None:
    graph = {"TASK-001": frozenset()}
    states = {"TASK-001": TaskState.QUEUED}
    records = dispatcher.dispatch_ready(graph, states)
    assert len(records) == 1
    rec = records[0]
    assert rec.task_id == "TASK-001"
    assert rec.worker_id == "worker-0"
    assert rec.lease.resource_id == "TASK-001"
    assert dispatcher.pool.get_worker_status("worker-0").state is WorkerState.ASSIGNED


def test_dispatch_respects_capacity(dispatcher: Dispatcher) -> None:
    graph = {t: frozenset() for t in ("TASK-001", "TASK-002", "TASK-003")}
    states = dict.fromkeys(graph, TaskState.QUEUED)
    records = dispatcher.dispatch_ready(graph, states)
    assert len(records) == 2  # only 2 workers in pool; 3rd waits
    assert {r.task_id for r in records} == {"TASK-001", "TASK-002"}


def test_dispatch_skips_non_queued_ready_tasks(dispatcher: Dispatcher) -> None:
    graph = {"TASK-001": frozenset()}
    states = {"TASK-001": TaskState.RUNNING}  # ready (no deps) but not QUEUED
    assert dispatcher.dispatch_ready(graph, states) == ()


def test_dispatch_skips_task_already_bound(dispatcher: Dispatcher) -> None:
    graph = {"TASK-001": frozenset()}
    states = {"TASK-001": TaskState.QUEUED}
    dispatcher.dispatch_ready(graph, states)  # binds worker-0
    second = dispatcher.dispatch_ready(graph, states)  # already bound → skip
    assert second == ()


def test_dispatch_deterministic_order(dispatcher: Dispatcher) -> None:
    graph = {"TASK-B": frozenset(), "TASK-A": frozenset()}
    states = dict.fromkeys(graph, TaskState.QUEUED)
    records = dispatcher.dispatch_ready(graph, states)
    # scheduler orders by (dep-count, task-id) → TASK-A before TASK-B
    assert [r.task_id for r in records] == ["TASK-A", "TASK-B"]


def test_dispatch_waits_on_unmet_dependency(dispatcher: Dispatcher) -> None:
    graph = {"TASK-002": frozenset({"TASK-001"})}
    states = {"TASK-001": TaskState.RUNNING, "TASK-002": TaskState.QUEUED}
    assert dispatcher.dispatch_ready(graph, states) == ()  # dep not COMPLETE
