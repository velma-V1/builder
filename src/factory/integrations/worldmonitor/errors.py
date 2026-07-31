"""WorldMonitor integration error taxonomy (fail-closed)."""

from __future__ import annotations

from enum import StrEnum


class WorldMonitorErrorCode(StrEnum):
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"   # not discovered/supported → denied
    NETWORK_DENIED = "NETWORK_DENIED"                   # broker refused
    SECRET_UNAVAILABLE = "SECRET_UNAVAILABLE"  # noqa: S105 - error code; secret lease missing
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"           # bad JSON / schema / timestamp / geography
    RESPONSE_TOO_LARGE = "RESPONSE_TOO_LARGE"           # exceeded byte ceiling
    SOURCE_URL_DENIED = "SOURCE_URL_DENIED"             # source/output URL outside approved domains
    TIMED_OUT = "TIMED_OUT"
    UNAVAILABLE = "UNAVAILABLE"                         # service unhealthy/unreachable
    UI_MESSAGE_REJECTED = "UI_MESSAGE_REJECTED"         # unknown/unsafe UI message
    MODEL_AUTHORITY_VIOLATION = "MODEL_AUTHORITY_VIOLATION"  # attempted to bypass Builder router


class WorldMonitorError(Exception):
    """Raised inside internals; the adapter converts it to a typed result, never leaks."""

    __slots__ = ("code", "detail")

    def __init__(self, code: WorldMonitorErrorCode, detail: str) -> None:
        super().__init__(f"{code.value}: {detail}")
        self.code = code
        self.detail = detail
