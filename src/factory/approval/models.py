"""Models for the roadmap PH-3 Approval Engine (CMP-APPROVAL).

CMP-APPROVAL owns CTR-APPROVAL-RECORD in the PH-3 security-spine store (ODI-RPH3-01; not the frozen
runtime-state DB, R1 preserved). An approval is issued only *bound* (to task/tool/action/resource/
scope), *expiring*, and *revocable* — never reusable, permanent, or unbounded (01K §2.8-9). Every
approval-card scope field required by 01L §3.2 is carried on the card and record so a consumer can
bind against it.

Two orthogonal state axes live on a record:

* ``state`` — the approval lifecycle (``PENDING`` awaiting an operator decision → ``GRANTED`` /
  ``DENIED`` → ``CONSUMED`` / ``REVOKED`` / ``EXPIRED``).
* ``commit_state`` — the XSC-RPH3 Class-1 durability marker. A mutation is written ``PENDING`` and
  is **non-authoritative** until its completion audit is durable, then flipped to ``COMMITTED``
  (INV-1/INV-2). A reader honors **only** ``COMMITTED`` rows.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

# Canonical separator for fingerprint/payload serialization (ASCII unit separator).
_SEP = "\x1f"


class ApprovalState(StrEnum):
    PENDING = "PENDING"
    GRANTED = "GRANTED"
    DENIED = "DENIED"
    CONSUMED = "CONSUMED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class CommitState(StrEnum):
    """XSC-RPH3 Class-1 durability marker for a security-spine mutation."""

    PENDING = "PENDING"
    COMMITTED = "COMMITTED"


class DecisionKind(StrEnum):
    GRANT = "GRANT"
    DENY = "DENY"


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
    """Injected clock. ``now_ts`` drives expiry; ``now_iso`` stamps audit ``occurred_at``."""

    def now_ts(self) -> int: ...
    def now_iso(self) -> str: ...


def action_fingerprint(
    *, task_id: str, tool: str, action: str, resource: str | None, scope: str
) -> str:
    """Deterministic binding fingerprint over the approvable scope (01L §3.2 subset).

    A consume request is authorized only if the caller's fingerprint over the *actual* action equals
    the record's bound fingerprint — an approval bound to (task, action, path, scope) rejects any
    other action (01K acceptance: scope binding).
    """
    canonical = _SEP.join((task_id, tool, action, resource or "", scope))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    """An untrusted request to enqueue an approval (typically from CMP-PERM).

    ``security_violation`` marks a request that must never be offered as an approvable card — it is
    denied + audited, never queued (01K acceptance). ``destructive`` marks a destructive or
    real-world external action that requires a *separate* explicit confirmation at decision time
    beyond ordinary code-execution approval (01K §2.10-11).
    """

    task_id: str
    tool: str
    action: str
    scope: str
    purpose: str
    consequences: str
    autonomy_level: str
    ttl_seconds: int
    resource: str | None = None
    repetition_limit: int = 1
    actor: str = "cmp-perm"
    security_violation: bool = False
    destructive: bool = False


@dataclass(frozen=True, slots=True)
class ApprovalCard:
    """Complete operator-facing card (full 01L §3.2 scope + autonomy level + consequences).

    A card is invalid unless every scope field is present (see :meth:`is_complete`).
    """

    approval_id: str
    task_id: str
    tool: str
    action: str
    resource: str | None
    scope: str
    purpose: str
    repetition_limit: int
    expires_at: int
    consequences: str
    autonomy_level: str
    state: ApprovalState
    requires_separate_confirmation: bool

    def is_complete(self) -> bool:
        """True iff the card carries the full 01L §3.2 scope (path/resource optional)."""
        required = (
            self.approval_id,
            self.task_id,
            self.tool,
            self.action,
            self.scope,
            self.purpose,
            self.consequences,
            self.autonomy_level,
        )
        return (
            all(bool(field) for field in required)
            and self.repetition_limit >= 1
            and self.expires_at > 0
        )


@dataclass(frozen=True, slots=True)
class OperatorDecision:
    """An operator's grant/deny decision. ``confirmed_destructive`` is the separate confirmation."""

    decision: DecisionKind
    operator: str
    confirmed_destructive: bool = False


@dataclass(frozen=True, slots=True)
class ApprovalRecord:
    """A bound, expiring, revocable approval record (CTR-APPROVAL-RECORD).

    ``commit_state`` is the XSC Class-1 authority marker: a reader honors this record only when it
    is ``COMMITTED``. ``action_fingerprint`` is the scope binding set at grant time.
    """

    approval_id: str
    task_id: str
    tool: str
    action: str
    resource: str | None
    scope: str
    purpose: str
    consequences: str
    autonomy_level: str
    repetition_limit: int
    uses_consumed: int
    requires_confirmation: bool
    expires_at: int
    action_fingerprint: str | None
    state: ApprovalState
    commit_state: CommitState
    created_ts: int
    updated_ts: int


@dataclass(frozen=True, slots=True)
class Denial:
    """A non-approval outcome — a request refused (never a bound authority)."""

    reason_code: str
    message: str
    approval_id: str | None = None


__all__ = [
    "ApprovalCard",
    "ApprovalRecord",
    "ApprovalRequest",
    "ApprovalState",
    "Clock",
    "CommitState",
    "DecisionKind",
    "Denial",
    "IntentStatus",
    "OperatorDecision",
    "ReconciliationState",
    "action_fingerprint",
]
