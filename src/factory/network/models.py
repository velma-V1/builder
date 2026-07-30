"""Value objects for the PH-5 network broker (``01E §3.3``, CTR-NETWORK-APPROVAL).

Network is denied by default; access exists only under a task-scoped :class:`NetworkApproval` that
bounds destinations, protocols, methods, expiry, transfer, redirects, and inbound policy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Direction(StrEnum):
    OUTBOUND = "OUTBOUND"
    INBOUND = "INBOUND"


@dataclass(frozen=True, slots=True)
class NetworkApproval:
    """Task-scoped network approval contract (CTR-NETWORK-APPROVAL, ``01E §3.3``)."""

    approval_id: str
    task_id: str
    destinations: frozenset[str]
    protocols: frozenset[str]
    methods: frozenset[str]
    expires_at: int
    max_total_bytes: int
    allow_inbound: bool = False
    # Redirects may only target destinations already in the allowlist (containment, §3.3).
    follow_redirects: bool = True


@dataclass(frozen=True, slots=True)
class NetworkRequest:
    destination: str
    protocol: str
    method: str
    direction: Direction = Direction.OUTBOUND
    bytes_estimate: int = 0


@dataclass(frozen=True, slots=True)
class NetworkDecision:
    allowed: bool
    reason: str
    code: str = ""


@dataclass(frozen=True, slots=True)
class TransferState:
    approval_id: str
    total_bytes: int = 0
    charges: tuple[int, ...] = field(default_factory=tuple)
