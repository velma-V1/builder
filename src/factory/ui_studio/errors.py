"""UI Studio error taxonomy (fail-closed).

UI Studio compiles a requirement into a generation plan and renders it through a deterministic fake
renderer — it never installs a frontend package, invokes a real build tool, starts a preview server,
or performs live network I/O. Every gap in a generated artifact (missing contract, invented
authoritative state, a real-time event that arrives out of order) is a denial here, not a silent
best-effort.
"""

from __future__ import annotations

from enum import StrEnum


class UIStudioErrorCode(StrEnum):
    # Requirements / compilation
    REQUIREMENT_UNPARSEABLE = "REQUIREMENT_UNPARSEABLE"
    TEMPLATE_UNKNOWN = "TEMPLATE_UNKNOWN"
    COMPONENT_UNKNOWN = "COMPONENT_UNKNOWN"          # not in the component registry → denied
    PAGE_UNKNOWN = "PAGE_UNKNOWN"
    WIDGET_UNKNOWN = "WIDGET_UNKNOWN"

    # Design tokens
    TOKEN_SET_INCOMPLETE = "TOKEN_SET_INCOMPLETE"  # noqa: S105 - error code, not a credential
    TOKEN_CONTRAST_FLOOR_VIOLATION = "TOKEN_CONTRAST_FLOOR_VIOLATION"  # noqa: S105

    # State/data contract boundaries
    STATE_OWNER_VIOLATION = "STATE_OWNER_VIOLATION"  # authoritative state claimed outside backend
    ILLEGAL_TRANSITION = "ILLEGAL_TRANSITION"
    DATA_CONTRACT_INCOMPLETE = "DATA_CONTRACT_INCOMPLETE"

    # Real-time event stream integrity
    DUPLICATE_EVENT = "DUPLICATE_EVENT"
    OUT_OF_ORDER_EVENT = "OUT_OF_ORDER_EVENT"
    MISSING_SEQUENCE = "MISSING_SEQUENCE"
    REPLAY_WINDOW_EXCEEDED = "REPLAY_WINDOW_EXCEEDED"
    STALE_SNAPSHOT = "STALE_SNAPSHOT"
    CLIENT_INVENTED_STATE = "CLIENT_INVENTED_STATE"  # a client tried to assert authoritative state

    # Rendering / preview / artifact
    RENDER_FAILED = "RENDER_FAILED"
    RENDER_TIMED_OUT = "RENDER_TIMED_OUT"
    PREVIEW_TRANSITION_ILLEGAL = "PREVIEW_TRANSITION_ILLEGAL"
    ARTIFACT_INCOMPLETE = "ARTIFACT_INCOMPLETE"       # missing a required artifact section
    UNRESOLVED_RISK_UNACKNOWLEDGED = "UNRESOLVED_RISK_UNACKNOWLEDGED"

    # Activation boundary
    INSTALL_DENIED = "INSTALL_DENIED"                 # any attempt to install/activate is refused


class UIStudioError(Exception):
    """Raised inside internals; callers convert it to a typed result, never leaks."""

    __slots__ = ("code", "detail")

    def __init__(self, code: UIStudioErrorCode, detail: str) -> None:
        super().__init__(f"{code.value}: {detail}")
        self.code = code
        self.detail = detail
