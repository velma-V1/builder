"""LeaseCoordinator: task-lease acquisition for the Worker Engine (PH-3, CMP-WORKER, Task 3.5).

A thin, typed wrapper over the PH-2 `LeaseManager`. It exists so the pool acquires a TASK lease
BEFORE dispatch (fencing before execution) and validates it BEFORE any state transition, using the
SAME process epoch as the owning `WorkerPool` (R4). Fencing is the PRIMARY validity check;
wall-clock expiry is secondary. The coordinator adds no persistence of its own — the lease store is
single source of truth for token/epoch/released.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from factory.orchestrator.leases.fencing import LeaseManager
from factory.orchestrator.models import Lease, LeaseResourceType, ProcessEpoch
from factory.workers.errors import WorkerEngineError

_DEFAULT_TTL_SECONDS = 300


@dataclass(slots=True)
class LeaseCoordinator:
    """Acquire/renew/validate/release TASK leases under a pool's process epoch.

    Construct with the OWNING pool's ``ProcessEpoch`` so a lease minted here is rejected as stale
    by any pool from a later epoch (cross-restart fencing).
    """

    lease_manager: LeaseManager

    @classmethod
    def for_pool(cls, database_path: Path, process_epoch: ProcessEpoch) -> LeaseCoordinator:
        """Build a coordinator bound to ``process_epoch`` (typically the WorkerPool's epoch)."""
        return cls(
            lease_manager=LeaseManager(
                database_path=database_path, process_epoch=process_epoch
            )
        )

    @property
    def process_epoch(self) -> ProcessEpoch:
        return self.lease_manager.process_epoch

    def acquire_task_lease(
        self, task_id: str, worker_pid: int, ttl_seconds: int = _DEFAULT_TTL_SECONDS
    ) -> Lease:
        """Acquire a TASK lease for ``task_id`` owned by ``worker_pid``. Fencing before dispatch."""
        if ttl_seconds < 1:
            raise WorkerEngineError(
                "LEASE_TTL_INVALID", f"ttl_seconds must be >= 1, got {ttl_seconds}"
            )
        return self.lease_manager.acquire(
            resource_type=LeaseResourceType.TASK,
            resource_id=task_id,
            owner_id=str(worker_pid),
            ttl_seconds=ttl_seconds,
        )

    def renew_lease(self, lease: Lease, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> Lease:
        """Refresh a lease's TTL before expiry. Renew at ttl/2 during long-running tasks."""
        if ttl_seconds < 1:
            raise WorkerEngineError(
                "LEASE_TTL_INVALID", f"ttl_seconds must be >= 1, got {ttl_seconds}"
            )
        return self.lease_manager.renew(lease, ttl_seconds=ttl_seconds)

    def validate_current(self, lease: Lease) -> bool:
        """True iff ``lease`` is the current highest token, this epoch, and not released.

        Called BEFORE routing a state transition: a stale lease (superseded token, prior epoch, or
        released) must not be allowed to finalize task state (spec §Lease Expiry Recovery).
        """
        return self.lease_manager.validate_token(
            lease.resource_type, lease.resource_id, lease.fencing_token
        )

    def release_task_lease(self, lease: Lease) -> None:
        """Release on task end (success/failure/cancel). Idempotent in the PH-2 store."""
        self.lease_manager.release(lease)
