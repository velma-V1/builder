"""PH-5 (Task 5.3) — network broker (preinstallation).

Broker interface + deterministic fake backend: default-deny, explicit destination/protocol/method
allowlists, expiry, no unsolicited inbound, redirect containment, destination validation, and
per-contract transfer limits (``01E §3.3``, CTR-NETWORK-APPROVAL). Live network-namespace
enforcement is LIVE_SANDBOX_PENDING.
"""

from __future__ import annotations

from factory.network.broker import NetworkBroker
from factory.network.errors import NetworkError
from factory.network.fake_backend import FakeNetworkBackend
from factory.network.models import (
    Direction,
    NetworkApproval,
    NetworkDecision,
    NetworkRequest,
    TransferState,
)

__all__ = [
    "Direction",
    "FakeNetworkBackend",
    "NetworkApproval",
    "NetworkBroker",
    "NetworkDecision",
    "NetworkError",
    "NetworkRequest",
    "TransferState",
]
