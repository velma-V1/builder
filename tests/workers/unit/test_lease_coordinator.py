"""Task 3.5 — LeaseCoordinator over PH-2 fenced leases (CMP-WORKER)."""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.orchestrator.models import LeaseResourceType, ProcessEpoch
from factory.workers.errors import WorkerEngineError
from factory.workers.lease_coordinator import LeaseCoordinator


def _coordinator(db: Path, epoch: ProcessEpoch | None = None) -> LeaseCoordinator:
    return LeaseCoordinator.for_pool(db, epoch or ProcessEpoch.generate())


def test_acquire_returns_task_lease_owned_by_pid(runtime_db: Path) -> None:
    coord = _coordinator(runtime_db)
    lease = coord.acquire_task_lease("TASK-001", worker_pid=1234)
    assert lease.resource_type is LeaseResourceType.TASK
    assert lease.resource_id == "TASK-001"
    assert lease.owner_id == "1234"
    assert lease.process_epoch == coord.process_epoch.value


def test_acquire_mints_monotonic_tokens(runtime_db: Path) -> None:
    coord = _coordinator(runtime_db)
    first = coord.acquire_task_lease("TASK-001", worker_pid=1)
    second = coord.acquire_task_lease("TASK-001", worker_pid=2)
    assert second.fencing_token > first.fencing_token


def test_validate_current_true_for_fresh_lease(runtime_db: Path) -> None:
    coord = _coordinator(runtime_db)
    lease = coord.acquire_task_lease("TASK-001", worker_pid=1)
    assert coord.validate_current(lease) is True


def test_superseded_lease_invalidated(runtime_db: Path) -> None:
    coord = _coordinator(runtime_db)
    stale = coord.acquire_task_lease("TASK-001", worker_pid=1)
    coord.acquire_task_lease("TASK-001", worker_pid=2)  # supersedes token
    assert coord.validate_current(stale) is False


def test_renew_keeps_lease_valid(runtime_db: Path) -> None:
    coord = _coordinator(runtime_db)
    lease = coord.acquire_task_lease("TASK-001", worker_pid=1, ttl_seconds=10)
    renewed = coord.renew_lease(lease, ttl_seconds=10)
    assert coord.validate_current(renewed) is True


def test_release_invalidates_lease(runtime_db: Path) -> None:
    coord = _coordinator(runtime_db)
    lease = coord.acquire_task_lease("TASK-001", worker_pid=1)
    coord.release_task_lease(lease)
    assert coord.validate_current(lease) is False


def test_acquire_rejects_nonpositive_ttl(runtime_db: Path) -> None:
    coord = _coordinator(runtime_db)
    with pytest.raises(WorkerEngineError, match="LEASE_TTL_INVALID"):
        coord.acquire_task_lease("TASK-001", worker_pid=1, ttl_seconds=0)
