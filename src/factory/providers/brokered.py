"""The brokered security envelope every hosted adapter must use.

A single authorized request enforces, in order:

1. **Privacy** — the task must be ``CLOUD_ALLOWED`` (a ``LOCAL_ONLY`` task can never reach a host).
2. **Network approval** — a task-scoped :class:`NetworkApproval` must permit the exact host/method
   under its byte ceiling (default-deny via the :class:`NetworkBroker`).
3. **Secret lease** — the API key is leased from the :class:`SecretBroker` for this call, put on
   the ``Authorization`` header, and **revoked in ``finally``**. It is never read from the
   environment, never persisted, and never placed in a log, error, or record.
4. **Redirect containment** — any redirect's final host is re-validated by the broker.
5. **Byte accounting** — the response size is charged to the approval.
6. **Redaction** — every surfaced string is passed through ``SecretBroker.redact``.

The concrete network I/O is the injected :class:`HttpTransport` (only a fake exists in preparation),
so no live call is possible here.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from factory.network.broker import NetworkBroker
from factory.network.models import Direction, NetworkApproval, NetworkRequest
from factory.providers.errors import ProviderError, ProviderErrorCode
from factory.providers.transport import (
    HttpRequest,
    HttpResponse,
    HttpTransport,
    TransportFailure,
    TransportTimeout,
)
from factory.routing.models import Privacy
from factory.secret.broker import SecretBroker
from factory.secret.errors import SecretError
from factory.secret.models import SecretRef


@dataclass(frozen=True, slots=True)
class BrokeredContext:
    task_id: str
    privacy: Privacy
    network: NetworkBroker
    approval: NetworkApproval
    secret: SecretBroker
    secret_ref: SecretRef
    now: int
    #: Authorization scheme: "Bearer" (OpenAI-style) or "Token" (Replicate-style).
    auth_scheme: str = "Bearer"


def _host(url: str) -> str:
    return urlsplit(url).hostname or ""


class BrokeredHttp:
    """Wraps an :class:`HttpTransport` with the full security envelope. Adapters use only this."""

    __slots__ = ("_ctx", "_transport")

    def __init__(self, transport: HttpTransport, context: BrokeredContext) -> None:
        self._transport = transport
        self._ctx = context

    def redact(self, text: str) -> str:
        return self._ctx.secret.redact(text, self._ctx.now)

    def request(
        self,
        method: str,
        url: str,
        *,
        body: bytes = b"",
        headers: dict[str, str] | None = None,
        protocol: str = "https",
        bytes_estimate: int = 0,
    ) -> HttpResponse:
        ctx = self._ctx
        if ctx.privacy is not Privacy.CLOUD_ALLOWED:
            raise ProviderError(
                ProviderErrorCode.NETWORK_DENIED, "task privacy is LOCAL_ONLY; hosted call refused"
            )
        host = _host(url)
        decision = ctx.network.evaluate(
            ctx.approval,
            NetworkRequest(host, protocol, method, Direction.OUTBOUND, bytes_estimate),
            ctx.now,
        )
        if not decision.allowed:
            raise ProviderError(
                ProviderErrorCode.NETWORK_DENIED,
                f"network denied: {decision.code or decision.reason}",
            )

        try:
            lease = ctx.secret.inject(ctx.secret_ref, ctx.now)
        except SecretError as exc:
            raise ProviderError(
                ProviderErrorCode.SECRET_UNAVAILABLE, f"secret lease unavailable: {exc.code}"
            ) from exc
        try:
            if not lease.is_active(ctx.now):
                raise ProviderError(ProviderErrorCode.SECRET_UNAVAILABLE, "secret lease not active")
            request_headers = dict(headers or {})
            request_headers["Authorization"] = f"{ctx.auth_scheme} {lease.value}"
            http_request = HttpRequest(method, url, request_headers, body)
            try:
                response = self._transport.send(http_request)
            except TransportTimeout as exc:
                raise ProviderError(ProviderErrorCode.TIMED_OUT, self.redact(str(exc))) from exc
            except TransportFailure as exc:
                raise ProviderError(
                    ProviderErrorCode.RUNTIME_UNAVAILABLE, self.redact(str(exc))
                ) from exc

            final = response.final_url or url
            if _host(final) != host:
                redirect = ctx.network.evaluate_redirect(ctx.approval, _host(final), ctx.now)
                if not redirect.allowed:
                    raise ProviderError(
                        ProviderErrorCode.NETWORK_DENIED,
                        f"redirect denied to {_host(final)}: {redirect.code or redirect.reason}",
                    )

            charge = ctx.network.charge(ctx.approval, len(response.body))
            if not charge.allowed:
                raise ProviderError(
                    ProviderErrorCode.RESPONSE_TOO_LARGE,
                    f"transfer denied: {charge.code or charge.reason}",
                )
            return response
        finally:
            ctx.secret.revoke(ctx.secret_ref.ref_id)
