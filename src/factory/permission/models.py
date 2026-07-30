"""Models for the roadmap PH-3 Permission Enforcement engine (CMP-PERM).

CMP-PERM computes **least-privilege, deny-by-default** decisions for every task/tool action, issues
**scoped / expiring / revocable** grants (CTR-PERMISSION-GRANT), and revalidates authority at the
point of use (TOCTOU). It owns path authority (canonicalize + contain every path; reuses the tested
``factory.contracts.validation.paths.PathAuthority``). It never auto-approves a deletion (Dec B)
or an out-of-envelope action (Decision A); those return ``REQUIRES_APPROVAL``.

Grants live in the PH-3 security-spine store (ODI-RPH3-01; not the runtime-state DB, R1 preserved)
and carry a XSC-RPH3 Class-1 durability marker as approvals: a mutation is written ``PENDING``
and is non-authoritative until its completion audit is durable, then flipped to ``COMMITTED``.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

_SEP = "\x1f"


class PermissionState(StrEnum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class CommitState(StrEnum):
    """XSC-RPH3 Class-1 durability marker for a security-spine mutation."""

    PENDING = "PENDING"
    COMMITTED = "COMMITTED"


class DecisionKind(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"


class PermissionClass(StrEnum):
    """The operation class of an action, coarsest authority unit (least-privilege granularity)."""

    READ = "READ"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"
    DELETE = "DELETE"
    NETWORK = "NETWORK"
    EXTERNAL = "EXTERNAL"


# Filesystem-mutating classes whose *path* must be canonicalized + contained before any grant.
WRITE_LIKE_CLASSES = frozenset(
    {PermissionClass.WRITE, PermissionClass.DELETE}
)
# Classes that always require a separate approval card (never auto-allowed): Decision B (delete) +
# real-world/external effects. External/network reach beyond the local envelope.
APPROVAL_REQUIRED_CLASSES = frozenset(
    {PermissionClass.DELETE, PermissionClass.EXTERNAL, PermissionClass.NETWORK}
)


class IntentStatus(StrEnum):
    PENDING = "PENDING"
    COMMITTED = "COMMITTED"
    ABORTED = "ABORTED"
    UNCERTAIN = "UNCERTAIN"
    QUARANTINED = "QUARANTINED"


class ReconciliationState(StrEnum):
    NONE = "NONE"
    ROLL_FORWARD = "ROLL_FORWARD"
    ROLL_BACK = "ROLL_BACK"
    QUARANTINE = "QUARANTINE"


class Clock(Protocol):
    def now_ts(self) -> int: ...
    def now_iso(self) -> str: ...


def grant_fingerprint(
    *, task_id: str, tool: str, action: str, resource: str | None, scope: str
) -> str:
    """Deterministic binding fingerprint over the granted scope (revalidated at point of use)."""
    canonical = _SEP.join((task_id, tool, action, resource or "", scope))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class TaskAuthority:
    """The authority envelope for the active task (validated CTR-TASK/PERMISSION/OWNERSHIP).

    Injected read-only (CMP-ORCH is a read-only reader dependency). It is the ceiling a grant may
    never exceed (01K-AC-02): ``allowed_classes`` is the least-privilege permit set;
    ``autonomy_level`` selects the Decision-A envelope; the path fields feed ``PathAuthority``.
    """

    task_id: str
    autonomy_level: str
    allowed_classes: frozenset[PermissionClass]
    project_root: str
    allowed_paths: tuple[str, ...] = ()
    forbidden_paths: tuple[str, ...] = ()
    read_only_paths: tuple[str, ...] = ()
    exclusive_paths: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ActionRequest:
    """An untrusted request to authorize one task/tool action (action, scope and path untrusted)."""

    task_id: str
    tool: str
    action: str
    permission_class: PermissionClass
    scope: str
    purpose: str
    resource: str | None = None
    actor: str = "cmp-perm"


@dataclass(frozen=True, slots=True)
class PermissionDecision:
    """The computed decision for an action, with a machine cause and the canonical path (if any)."""

    decision: DecisionKind
    cause: str
    request: ActionRequest
    canonical_resource: str | None = None


@dataclass(frozen=True, slots=True)
class PermissionGrant:
    """A scoped, expiring, revocable least-privilege grant (CTR-PERMISSION-GRANT).

    ``commit_state`` is the XSC Class-1 authority marker: a reader honors this grant only when it is
    ``COMMITTED``. ``resource`` is the canonical validated path (never a raw path).
    """

    grant_id: str
    task_id: str
    tool: str
    action: str
    permission_class: PermissionClass
    resource: str | None
    scope: str
    purpose: str
    grant_fingerprint: str
    expires_at: int
    state: PermissionState
    commit_state: CommitState
    created_ts: int
    updated_ts: int


__all__ = [
    "APPROVAL_REQUIRED_CLASSES",
    "WRITE_LIKE_CLASSES",
    "ActionRequest",
    "Clock",
    "CommitState",
    "DecisionKind",
    "IntentStatus",
    "PermissionClass",
    "PermissionDecision",
    "PermissionGrant",
    "PermissionState",
    "ReconciliationState",
    "TaskAuthority",
    "grant_fingerprint",
]
