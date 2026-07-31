"""Local-only network policy for preinstall (hosted egress disabled by default).

The live substrate is local-first: workers run on an internal-only network and reach nothing off-box
directly. Hosted (cloud) egress is **disabled by default** and may be enabled only per approved
destination through the broker. This module models that policy and validates a proposed destination
set against it — statically, with no live network access.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field

#: Hosted egress is off unless the operator explicitly enables specific destinations.
HOSTED_EGRESS_DEFAULT_ENABLED = False


def _is_local(host: str) -> bool:
    """True for loopback / private / link-local / unspecified addresses and bare local names."""
    name = host.strip().lower()
    if name in ("localhost", "host.docker.internal", ""):
        return True
    try:
        ip = ipaddress.ip_address(name)
    except ValueError:
        # A non-IP hostname is treated as non-local (must go through the broker if allowed at all).
        return False
    return ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_unspecified


@dataclass(frozen=True, slots=True)
class NetworkPolicy:
    """Default-deny local-only policy. Hosted egress requires explicit per-destination allow."""

    hosted_egress_enabled: bool = HOSTED_EGRESS_DEFAULT_ENABLED
    approved_hosted_destinations: frozenset[str] = field(default_factory=frozenset)

    def evaluate(self, destination: str) -> tuple[bool, str]:
        """Return ``(allowed, reason)`` for a proposed outbound destination (no live access)."""
        if _is_local(destination):
            return True, "LOCAL_ALLOWED"
        if not self.hosted_egress_enabled:
            return False, "HOSTED_EGRESS_DISABLED"
        approved = {d.lower() for d in self.approved_hosted_destinations}
        if destination.strip().lower() not in approved:
            return False, "HOSTED_DESTINATION_NOT_APPROVED"
        return True, "HOSTED_APPROVED"


def default_policy() -> NetworkPolicy:
    """The shipped default: local-only, hosted egress disabled, no approved destinations."""
    return NetworkPolicy()
