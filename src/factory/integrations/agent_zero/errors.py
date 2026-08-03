"""Agent Zero integration error taxonomy (fail-closed).

Agent Zero is a **managed external worker**. It may execute an assigned work order, use explicitly
granted tools, produce patches/artifacts, stream visible progress, and return evidence — nothing
else. Every attempt to exceed that surface (a provider key, a Docker socket, unrestricted host
filesystem access, direct ``main`` access, merge/approval/promotion authority, self-update, hidden
scheduling, a malformed or out-of-sequence event) is a denial here, never a soft downgrade or a
silently-accepted claim.
"""

from __future__ import annotations

from enum import StrEnum


class AgentZeroErrorCode(StrEnum):
    # Capability / tool surface
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"  # not discovered/supported → denied
    TOOL_DENIED = "TOOL_DENIED"  # tool not explicitly granted for this order

    # Trust boundaries (network / secret / model / sandbox)
    NETWORK_DENIED = "NETWORK_DENIED"  # broker refused
    SECRET_UNAVAILABLE = "SECRET_UNAVAILABLE"  # noqa: S105 - error code; secret lease missing
    MODEL_AUTHORITY_VIOLATION = "MODEL_AUTHORITY_VIOLATION"  # attempted to bypass Builder router
    DOCKER_SOCKET_DENIED = "DOCKER_SOCKET_DENIED"  # host container-runtime socket requested
    PATH_DENIED = "PATH_DENIED"  # PathAuthority rejected a proposed path

    # Authority Agent Zero must never hold
    DIRECT_MAIN_DENIED = "DIRECT_MAIN_DENIED"  # attempted to target the main branch
    MERGE_AUTHORITY_DENIED = "MERGE_AUTHORITY_DENIED"
    APPROVAL_AUTHORITY_DENIED = "APPROVAL_AUTHORITY_DENIED"
    PROMOTION_AUTHORITY_DENIED = "PROMOTION_AUTHORITY_DENIED"
    SELF_CERTIFICATION_DENIED = "SELF_CERTIFICATION_DENIED"  # worker "verified" claim is inert
    SELF_UPDATE_DENIED = "SELF_UPDATE_DENIED"
    HIDDEN_SCHEDULING_DENIED = "HIDDEN_SCHEDULING_DENIED"  # no self-scheduled/recurring work

    # Execution lifecycle
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"
    UNAVAILABLE = "UNAVAILABLE"  # crash / transport unreachable

    # Event stream / result integrity
    MALFORMED_RESULT = "MALFORMED_RESULT"
    INCOMPLETE_RESULT = "INCOMPLETE_RESULT"
    DUPLICATE_EVENT = "DUPLICATE_EVENT"  # same sequence, conflicting content
    OUT_OF_ORDER_EVENT = "OUT_OF_ORDER_EVENT"  # sequence regressed
    MISSING_SEQUENCE = "MISSING_SEQUENCE"  # a gap in the sequence was detected

    # Compatibility / update
    COMPATIBILITY_REJECTED = "COMPATIBILITY_REJECTED"
    UPDATE_FAILED = "UPDATE_FAILED"
    ROLLBACK_FAILED = "ROLLBACK_FAILED"
    MODULE_FAILURE_ISOLATED = "MODULE_FAILURE_ISOLATED"  # a failure was contained, not propagated


class AgentZeroError(Exception):
    """Raised inside internals; the adapter converts it to a typed result, never leaks."""

    __slots__ = ("code", "detail")

    def __init__(self, code: AgentZeroErrorCode, detail: str) -> None:
        super().__init__(f"{code.value}: {detail}")
        self.code = code
        self.detail = detail
