"""PH-5 — network broker (default-deny, allowlists, redirect containment, transfer limits)."""

from __future__ import annotations

import pytest

from factory.network import (
    Direction,
    FakeNetworkBackend,
    NetworkApproval,
    NetworkBroker,
    NetworkError,
    NetworkRequest,
)

pytestmark = pytest.mark.security


def _approval(**over: object) -> NetworkApproval:
    base: dict[str, object] = dict(
        approval_id="A1",
        task_id="T1",
        destinations=frozenset({"example.com"}),
        protocols=frozenset({"https"}),
        methods=frozenset({"GET"}),
        expires_at=100,
        max_total_bytes=1000,
    )
    base.update(over)
    return NetworkApproval(**base)  # type: ignore[arg-type]


def _req(**over: object) -> NetworkRequest:
    base: dict[str, object] = dict(destination="example.com", protocol="https", method="GET")
    base.update(over)
    return NetworkRequest(**base)  # type: ignore[arg-type]


def test_backend_satisfies_protocol() -> None:
    assert isinstance(FakeNetworkBackend(), NetworkBroker)


def test_default_deny_without_contract() -> None:
    d = FakeNetworkBackend().evaluate(None, _req(), now=0)
    assert not d.allowed and d.code == "NO_CONTRACT"


def test_permitted_request_allowed() -> None:
    assert FakeNetworkBackend().evaluate(_approval(), _req(), now=0).allowed


def test_inbound_denied_unless_permitted() -> None:
    b = FakeNetworkBackend()
    assert (
        b.evaluate(_approval(), _req(direction=Direction.INBOUND), now=0).code == "INBOUND_DENIED"
    )
    assert b.evaluate(
        _approval(allow_inbound=True), _req(direction=Direction.INBOUND), now=0
    ).allowed


def test_expired_contract_denied() -> None:
    assert FakeNetworkBackend().evaluate(_approval(expires_at=10), _req(), now=20).code == "EXPIRED"


def test_malformed_and_unlisted_destinations() -> None:
    b = FakeNetworkBackend()
    assert (
        b.evaluate(_approval(), _req(destination="bad host/path"), now=0).code
        == "DESTINATION_INVALID"
    )
    assert (
        b.evaluate(_approval(), _req(destination="other.com"), now=0).code == "DESTINATION_DENIED"
    )


def test_protocol_and_method_denied() -> None:
    b = FakeNetworkBackend()
    assert b.evaluate(_approval(), _req(protocol="ftp"), now=0).code == "PROTOCOL_DENIED"
    assert b.evaluate(_approval(), _req(method="POST"), now=0).code == "METHOD_DENIED"


def test_redirect_containment() -> None:
    b = FakeNetworkBackend()
    assert b.evaluate_redirect(_approval(), "example.com", now=0).allowed
    assert not b.evaluate_redirect(_approval(), "evil.com", now=0).allowed
    assert (
        b.evaluate_redirect(_approval(follow_redirects=False), "example.com", now=0).code
        == "REDIRECT_DENIED"
    )


def test_transfer_limit_and_negative() -> None:
    b = FakeNetworkBackend()
    approval = _approval(max_total_bytes=100)
    assert b.charge(approval, 60).allowed
    assert b.charge(approval, 60).code == "TRANSFER_LIMIT"  # would exceed
    assert b.transferred("A1") == 60
    with pytest.raises(NetworkError):
        b.charge(approval, -1)


@pytest.mark.parametrize(
    "infra",
    [
        "127.0.0.1",
        "10.0.0.5",
        "192.168.1.10",
        "169.254.169.254",
        "host.docker.internal",
        "localhost",
    ],
)
def test_infrastructure_destinations_denied_by_default(infra: str) -> None:
    b = FakeNetworkBackend()
    approval = _approval(destinations=frozenset({infra}))
    assert b.evaluate(approval, _req(destination=infra), now=0).code == "INFRA_DENIED"


def test_infrastructure_allowed_only_with_explicit_authorization() -> None:
    b = FakeNetworkBackend()
    approval = _approval(destinations=frozenset({"10.0.0.5"}), allow_infrastructure=True)
    assert b.evaluate(approval, _req(destination="10.0.0.5"), now=0).allowed


def test_empty_destination_is_invalid() -> None:
    assert FakeNetworkBackend().evaluate(_approval(), _req(destination=""), now=0).code == (
        "DESTINATION_INVALID"
    )


def test_network_error_repr() -> None:
    err = NetworkError("X", "y")
    assert "NetworkError(code='X'" in repr(err)
    assert str(err) == "X: y"
