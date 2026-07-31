"""HTTP transport seam (brokered) + deterministic fake.

Adapters never import ``requests``/``httpx``/``urllib`` directly. They speak to an
:class:`HttpTransport`, and the only concrete transport wired in preparation is
:class:`FakeHttpTransport` (deterministic, offline). A real transport (built later) MUST route every
call through the :class:`~factory.network.broker.NetworkBroker`; it is not implemented here so no
live call is possible. A response body is bounded so an oversized response fails closed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

#: Hard ceiling on a single response body the transport will surface (bytes). Fail closed if larger.
DEFAULT_MAX_RESPONSE_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class HttpRequest:
    method: str
    url: str
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes = b""
    timeout_s: float = 30.0


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes
    #: Final URL after any redirects the transport followed (broker-validated). Same as request URL
    #: when no redirect occurred.
    final_url: str = ""

    @property
    def request_id(self) -> str:
        for key in ("x-request-id", "x-openrouter-id", "cf-ray"):
            for header, value in self.headers.items():
                if header.lower() == key:
                    return value
        return ""


class TransportTimeout(Exception):
    """The transport timed out — adapters map this to TIMED_OUT (never a silent success)."""


class TransportFailure(Exception):
    """A transport failure (connection refused, TLS, oversized) — maps to RUNTIME_UNAVAILABLE."""


@runtime_checkable
class HttpTransport(Protocol):
    """Send one already-authorized request and return the response (or raise a transport error).

    A real implementation must send only through the NetworkBroker with a task-scoped approval; a
    redirect must be re-validated by the broker before it is followed.
    """

    def send(self, request: HttpRequest) -> HttpResponse: ...


@dataclass(frozen=True, slots=True)
class FakeExchange:
    """A scripted request→response (or error) for the fake transport."""

    matcher: Callable[[HttpRequest], bool]
    response: HttpResponse | None = None
    raises: Exception | None = None


class FakeHttpTransport:
    """Deterministic, offline transport. Serves scripted exchanges; records the requests it saw.

    It performs NO real network I/O. An unmatched request fails closed (``TransportFailure``) so a
    test can never accidentally reach a live endpoint.
    """

    __slots__ = ("_exchanges", "_max_bytes", "sent")

    def __init__(
        self, exchanges: tuple[FakeExchange, ...], *, max_bytes: int = DEFAULT_MAX_RESPONSE_BYTES
    ) -> None:
        self._exchanges = exchanges
        self._max_bytes = max_bytes
        self.sent: list[HttpRequest] = []

    def send(self, request: HttpRequest) -> HttpResponse:
        self.sent.append(request)
        for exchange in self._exchanges:
            if exchange.matcher(request):
                if exchange.raises is not None:
                    raise exchange.raises
                assert exchange.response is not None
                if len(exchange.response.body) > self._max_bytes:
                    raise TransportFailure("response exceeds byte ceiling")
                return exchange.response
        raise TransportFailure(f"no scripted exchange for {request.method} {request.url}")
