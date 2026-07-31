"""UI workspace bridge contract (Builder-side only; no duplicate map is built).

Messages between Builder and the WorldMonitor webview are **typed and versioned**. The bridge:
rejects unknown message types, rejects arbitrary URLs, blocks navigation outside the approved
origin, never carries secrets, and never executes arbitrary JavaScript or exposes a filesystem
bridge. CSP is documented in the integration docs.
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.integrations.worldmonitor.errors import WorldMonitorError, WorldMonitorErrorCode
from factory.integrations.worldmonitor.models import ViewCommandType, WorldMonitorViewCommand

SUPPORTED_MESSAGE_VERSION = 1
_KNOWN = {c.value for c in ViewCommandType}
_SECRET_HINTS = ("authorization", "token", "api_key", "apikey", "secret", "password")


@dataclass(frozen=True, slots=True)
class UiMessage:
    type: str
    version: int
    argument: str = ""
    origin: str = ""


def validate_ui_message(
    message: UiMessage, *, allowed_origins: frozenset[str]
) -> WorldMonitorViewCommand:
    """Validate an inbound UI message and map it to a typed view command (fail closed)."""
    if message.origin not in allowed_origins:
        raise WorldMonitorError(
            WorldMonitorErrorCode.UI_MESSAGE_REJECTED, f"origin not allowed: {message.origin!r}"
        )
    if message.version != SUPPORTED_MESSAGE_VERSION:
        raise WorldMonitorError(
            WorldMonitorErrorCode.UI_MESSAGE_REJECTED,
            f"unsupported message version {message.version}",
        )
    if message.type not in _KNOWN:
        raise WorldMonitorError(
            WorldMonitorErrorCode.UI_MESSAGE_REJECTED, f"unknown message type {message.type!r}"
        )
    lowered = message.argument.lower()
    if "://" in message.argument:
        raise WorldMonitorError(
            WorldMonitorErrorCode.UI_MESSAGE_REJECTED, "arbitrary URLs not permitted in messages"
        )
    if any(hint in lowered for hint in _SECRET_HINTS):
        raise WorldMonitorError(
            WorldMonitorErrorCode.UI_MESSAGE_REJECTED, "secret-bearing messages are rejected"
        )
    return WorldMonitorViewCommand(ViewCommandType(message.type), message.argument)
