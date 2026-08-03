"""Bounded HTTP transport restricted to Builder-managed loopback services."""

from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass, field
from urllib.parse import urlparse

from factory.providers.transport import (
    DEFAULT_MAX_RESPONSE_BYTES,
    HttpRequest,
    HttpResponse,
    TransportFailure,
    TransportTimeout,
)


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> None:
        return None


@dataclass(slots=True)
class LoopbackHttpTransport:
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES
    redirect_handler: NoRedirectHandler = field(default_factory=NoRedirectHandler)
    opener: urllib.request.OpenerDirector = field(init=False)

    def __post_init__(self) -> None:
        self.opener = urllib.request.build_opener(self.redirect_handler)

    def send(self, request: HttpRequest) -> HttpResponse:
        parsed = urlparse(request.url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise TransportFailure("managed integration requests must target HTTP loopback")
        outbound = urllib.request.Request(  # noqa: S310 - loopback validated above
            request.url,
            data=request.body or None,
            headers=dict(request.headers),
            method=request.method,
        )
        try:
            with self.opener.open(outbound, timeout=request.timeout_s) as response:
                body = response.read(self.max_response_bytes + 1)
                if len(body) > self.max_response_bytes:
                    raise TransportFailure("response exceeds byte ceiling")
                return HttpResponse(
                    status=int(response.status),
                    headers=dict(response.headers.items()),
                    body=body,
                    final_url=str(response.url),
                )
        except urllib.error.HTTPError as exc:
            body = exc.read(self.max_response_bytes + 1)
            if len(body) > self.max_response_bytes:
                raise TransportFailure("response exceeds byte ceiling") from exc
            return HttpResponse(exc.code, dict(exc.headers.items()), body, request.url)
        except TimeoutError as exc:
            raise TransportTimeout(f"loopback request timed out: {exc}") from exc
        except urllib.error.URLError as exc:
            raise TransportFailure(f"loopback service unavailable: {exc.reason}") from exc


__all__ = ["LoopbackHttpTransport", "NoRedirectHandler"]
