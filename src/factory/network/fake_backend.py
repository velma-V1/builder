"""Deterministic fake network backend (preinstallation stand-in for Task 5.3).

Fully offline — no sockets, no DNS resolution. It enforces the ``01E §3.3`` contract semantics:
default-deny, explicit destination/protocol/method allowlists, expiry, no unsolicited inbound,
redirect containment (a redirect target must itself be allowed), destination syntax validation, and
per-contract transfer limits. Live network-namespace enforcement is LIVE_SANDBOX_PENDING.
"""

from __future__ import annotations

import ipaddress

from factory.network.errors import NetworkError
from factory.network.models import (
    Direction,
    NetworkApproval,
    NetworkDecision,
    NetworkRequest,
)

_ALLOWED_HOST = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-"
)

# Names that resolve to host/orchestration infrastructure and must not be reachable by default.
_INFRA_HOSTNAMES = frozenset({"localhost", "host.docker.internal", "metadata.google.internal"})


def _valid_destination(host: str) -> bool:
    """Reject empty, scheme/path-bearing, wildcard, or otherwise malformed destinations."""
    if not host or len(host) > 253:
        return False
    if any(ch not in _ALLOWED_HOST for ch in host):
        return False
    return not (host.startswith(".") or host.endswith(".") or ".." in host)


def _is_infra_destination(host: str) -> bool:
    """True for loopback / private / link-local / metadata / host-gateway destinations."""
    if host.lower() in _INFRA_HOSTNAMES:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved


class FakeNetworkBackend:
    """Deterministic default-deny network broker for tests and the preinstallation core."""

    __slots__ = ("_transferred",)

    def __init__(self) -> None:
        self._transferred: dict[str, int] = {}

    def _deny(self, code: str, reason: str) -> NetworkDecision:
        return NetworkDecision(allowed=False, reason=reason, code=code)

    def evaluate(
        self, approval: NetworkApproval | None, request: NetworkRequest, now: int
    ) -> NetworkDecision:
        if approval is None:
            return self._deny("NO_CONTRACT", "network denied by default (no approval contract)")
        if request.direction is Direction.INBOUND and not approval.allow_inbound:
            return self._deny("INBOUND_DENIED", "unsolicited inbound access is denied")
        if now >= approval.expires_at:
            return self._deny("EXPIRED", "network approval has expired")
        if not _valid_destination(request.destination):
            return self._deny(
                "DESTINATION_INVALID", f"malformed destination {request.destination!r}"
            )
        if request.destination not in approval.destinations:
            return self._deny("DESTINATION_DENIED", f"{request.destination} not allowlisted")
        if request.protocol not in approval.protocols:
            return self._deny("PROTOCOL_DENIED", f"protocol {request.protocol} not permitted")
        if request.method not in approval.methods:
            return self._deny("METHOD_DENIED", f"method {request.method} not permitted")
        if _is_infra_destination(request.destination) and not approval.allow_infrastructure:
            return self._deny(
                "INFRA_DENIED",
                "loopback/private/link-local/metadata/host-gateway destination denied",
            )
        return NetworkDecision(allowed=True, reason="permitted by contract")

    def evaluate_redirect(
        self, approval: NetworkApproval, target: str, now: int
    ) -> NetworkDecision:
        if not approval.follow_redirects:
            return self._deny("REDIRECT_DENIED", "redirects are not permitted by contract")
        # Containment: a redirect target is subject to the same allowlist as a fresh request.
        redirect = NetworkRequest(
            target, next(iter(approval.protocols)), next(iter(approval.methods))
        )
        return self.evaluate(approval, redirect, now)

    def charge(self, approval: NetworkApproval, nbytes: int) -> NetworkDecision:
        if nbytes < 0:
            raise NetworkError("TRANSFER_NEGATIVE", "transfer bytes must be non-negative")
        projected = self._transferred.get(approval.approval_id, 0) + nbytes
        if projected > approval.max_total_bytes:
            return self._deny("TRANSFER_LIMIT", "total-transfer limit exceeded")
        self._transferred[approval.approval_id] = projected
        return NetworkDecision(allowed=True, reason="within transfer limit")

    def transferred(self, approval_id: str) -> int:
        return self._transferred.get(approval_id, 0)
