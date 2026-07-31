"""Preinstall unit — local-only network policy (hosted egress disabled by default)."""

from __future__ import annotations

import pytest

from factory.preinstall.network_policy import (
    HOSTED_EGRESS_DEFAULT_ENABLED,
    NetworkPolicy,
    default_policy,
)


def test_hosted_egress_disabled_by_default() -> None:
    assert HOSTED_EGRESS_DEFAULT_ENABLED is False
    assert default_policy().hosted_egress_enabled is False


@pytest.mark.parametrize(
    "dest", ["127.0.0.1", "10.0.0.5", "192.168.1.2", "localhost", "169.254.0.1"]
)
def test_local_destinations_allowed(dest: str) -> None:
    allowed, reason = default_policy().evaluate(dest)
    assert allowed and reason == "LOCAL_ALLOWED"


def test_hosted_destination_denied_when_egress_disabled() -> None:
    allowed, reason = default_policy().evaluate("api.groq.com")
    assert not allowed and reason == "HOSTED_EGRESS_DISABLED"


def test_hosted_destination_requires_explicit_approval() -> None:
    policy = NetworkPolicy(hosted_egress_enabled=True,
                           approved_hosted_destinations=frozenset({"api.groq.com"}))
    assert policy.evaluate("api.groq.com")[0] is True
    denied, reason = policy.evaluate("evil.example.com")
    assert not denied and reason == "HOSTED_DESTINATION_NOT_APPROVED"
