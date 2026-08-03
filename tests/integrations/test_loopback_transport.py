import urllib.error
from collections.abc import Callable
from typing import cast

import pytest

from factory.integrations.loopback_transport import LoopbackHttpTransport
from factory.providers.transport import HttpRequest, TransportFailure


def test_loopback_transport_rejects_non_loopback_destinations_before_opening() -> None:
    transport = LoopbackHttpTransport()

    with pytest.raises(TransportFailure, match="loopback"):
        transport.send(HttpRequest("GET", "https://example.com"))


def test_loopback_transport_disables_redirects() -> None:
    transport = LoopbackHttpTransport()

    redirect = cast(Callable[..., object], transport.redirect_handler.redirect_request)
    result = redirect(None, None, 302, "Found", {}, "http://x")
    assert result is None


def test_loopback_transport_maps_url_errors_without_exposing_request_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = LoopbackHttpTransport()

    def fail(*_args: object, **_kwargs: object) -> None:
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(transport.opener, "open", fail)
    with pytest.raises(TransportFailure, match="offline") as raised:
        transport.send(
            HttpRequest(
                "GET",
                "http://127.0.0.1:50080/api/health",
                headers={"X-API-KEY": "do-not-print"},
            )
        )
    assert "do-not-print" not in str(raised.value)
