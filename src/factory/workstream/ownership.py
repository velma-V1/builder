"""Ownership leases (``01D §2.5/§3.2``).

At most one workstream may hold write ownership of a given file or shared contract at a time. A
second acquirer must wait, hand off, or resolve through the integration gate — it is never granted a
concurrent write lease.
"""

from __future__ import annotations

from factory.workstream.errors import WorkstreamError
from factory.workstream.models import OwnershipLease


class OwnershipRegistry:
    """Single-writer-owner registry over files and shared contracts."""

    __slots__ = ("_leases",)

    def __init__(self) -> None:
        self._leases: dict[str, OwnershipLease] = {}

    def acquire(
        self, resource_id: str, workstream_id: str, *, is_contract: bool = False
    ) -> OwnershipLease:
        existing = self._leases.get(resource_id)
        if existing is not None and existing.workstream_id != workstream_id:
            raise WorkstreamError(
                "OWNERSHIP_CONFLICT",
                f"{resource_id} is write-owned by {existing.workstream_id}, not {workstream_id}",
            )
        lease = OwnershipLease(resource_id, workstream_id, is_contract)
        self._leases[resource_id] = lease
        return lease

    def owner(self, resource_id: str) -> str | None:
        lease = self._leases.get(resource_id)
        return lease.workstream_id if lease is not None else None

    def release(self, resource_id: str) -> bool:
        return self._leases.pop(resource_id, None) is not None

    def leases(self) -> tuple[OwnershipLease, ...]:
        return tuple(self._leases.values())
