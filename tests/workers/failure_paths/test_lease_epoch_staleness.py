"""Task 3.5 failure-paths — cross-restart lease staleness (CMP-WORKER, R4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.orchestrator.models import ProcessEpoch
from factory.workers.lease_coordinator import LeaseCoordinator

pytestmark = pytest.mark.failure_path


def test_prior_epoch_lease_rejected_after_restart(runtime_db: Path) -> None:
    # Pool A acquires a lease, then the process restarts as Pool B with a NEW epoch.
    epoch_a = ProcessEpoch.generate()
    coord_a = LeaseCoordinator.for_pool(runtime_db, epoch_a)
    lease = coord_a.acquire_task_lease("TASK-001", worker_pid=1, ttl_seconds=3600)

    epoch_b = ProcessEpoch.generate()
    coord_b = LeaseCoordinator.for_pool(runtime_db, epoch_b)

    # Even though the lease is far from wall-clock expiry, epoch B must reject epoch A's lease:
    # fencing is primary, expiry secondary (01M "no blind resume").
    assert coord_b.validate_current(lease) is False


def test_same_epoch_lease_survives_new_coordinator_instance(runtime_db: Path) -> None:
    epoch = ProcessEpoch.generate()
    coord = LeaseCoordinator.for_pool(runtime_db, epoch)
    lease = coord.acquire_task_lease("TASK-001", worker_pid=1, ttl_seconds=3600)

    # A fresh coordinator object under the SAME epoch is still the same logical owner.
    same_epoch = LeaseCoordinator.for_pool(runtime_db, epoch)
    assert same_epoch.validate_current(lease) is True
