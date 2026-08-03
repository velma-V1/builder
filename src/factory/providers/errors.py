"""Provider error taxonomy + HTTP→error normalization (fail-closed).

A provider *failure is never converted into success*. Every adapter maps transport/HTTP/schema
failures onto a stable ``ProviderErrorCode`` and a coarse ``ExecutionStatus``.
The router — not the adapter — owns fallback, so an adapter never retries against another
model/provider internally.
"""

from __future__ import annotations

from enum import StrEnum

from factory.routing.models import ExecutionStatus


class ProviderErrorCode(StrEnum):
    AUTH_UNAVAILABLE = "AUTH_UNAVAILABLE"  # 401 / 403
    MODEL_MISSING = "MODEL_MISSING"  # 404
    TIMED_OUT = "TIMED_OUT"  # 408 / transport timeout
    PROVIDER_CONFLICT = "PROVIDER_CONFLICT"  # 409
    RATE_LIMITED = "RATE_LIMITED"  # 429
    RUNTIME_UNAVAILABLE = "RUNTIME_UNAVAILABLE"  # 5xx / transport failure
    MALFORMED_OUTPUT = "MALFORMED_OUTPUT"  # bad JSON / schema
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"  # unsupported feature
    RETURNED_MODEL_MISMATCH = "RETURNED_MODEL_MISMATCH"  # server returned a different model
    PROVIDER_MISMATCH = "PROVIDER_MISMATCH"  # unexpected upstream provider
    HIDDEN_FALLBACK = "HIDDEN_FALLBACK"  # provider silently substituted
    NETWORK_DENIED = "NETWORK_DENIED"  # broker refused
    SECRET_UNAVAILABLE = "SECRET_UNAVAILABLE"  # noqa: S105 - error code, not a secret
    RESPONSE_TOO_LARGE = "RESPONSE_TOO_LARGE"  # exceeded byte ceiling
    OUTPUT_URL_DENIED = "OUTPUT_URL_DENIED"  # output referenced an unapproved URL/domain


class ProviderError(Exception):
    """Raised inside adapter internals; adapters convert it to a ``CallResult``, never leak it."""

    __slots__ = ("code", "detail")

    def __init__(self, code: ProviderErrorCode, detail: str) -> None:
        super().__init__(f"{code.value}: {detail}")
        self.code = code
        self.detail = detail


#: HTTP status → error code. Unmapped 4xx fail closed as PROVIDER_CONFLICT (never as success).
def map_http_status(status: int) -> ProviderErrorCode:
    if status in (401, 403):
        return ProviderErrorCode.AUTH_UNAVAILABLE
    if status == 404:
        return ProviderErrorCode.MODEL_MISSING
    if status == 408:
        return ProviderErrorCode.TIMED_OUT
    if status == 409:
        return ProviderErrorCode.PROVIDER_CONFLICT
    if status == 429:
        return ProviderErrorCode.RATE_LIMITED
    if status >= 500:
        return ProviderErrorCode.RUNTIME_UNAVAILABLE
    if status >= 400:
        return ProviderErrorCode.PROVIDER_CONFLICT
    # A non-error status reaching this map is itself a contract violation → fail closed.
    return ProviderErrorCode.MALFORMED_OUTPUT


#: Error code → coarse execution status carried on the CallResult (preserves the existing contract).
def status_for(code: ProviderErrorCode) -> ExecutionStatus:
    if code is ProviderErrorCode.TIMED_OUT:
        return ExecutionStatus.TIMED_OUT
    if code in (ProviderErrorCode.RUNTIME_UNAVAILABLE, ProviderErrorCode.RATE_LIMITED):
        return ExecutionStatus.RUNTIME_UNAVAILABLE
    return ExecutionStatus.FAILED
