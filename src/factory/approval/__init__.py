"""Roadmap PH-3 Approval Engine (CMP-APPROVAL, RPH3-T3).

Issues bound, expiring, revocable approvals from a central queue; every lifecycle event is a
XSC-RPH3 Class-1 cross-store operation audited via CMP-AUDITW. The writable connection lives inside
a private, un-exported writer; the public surface is the engine plus read-only models + reader.
"""

from __future__ import annotations

from factory.approval.engine import ApprovalEngine, SystemClock
from factory.approval.errors import ApprovalError
from factory.approval.models import (
    ApprovalCard,
    ApprovalRecord,
    ApprovalRequest,
    ApprovalState,
    Clock,
    CommitState,
    DecisionKind,
    Denial,
    IntentStatus,
    OperatorDecision,
    ReconciliationState,
    action_fingerprint,
)
from factory.approval.store import (
    SQLiteApprovalReader,
    apply_security_migrations,
    audit_completion_seq,
)

__all__ = [
    "ApprovalCard",
    "ApprovalEngine",
    "ApprovalError",
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
    "SQLiteApprovalReader",
    "SystemClock",
    "action_fingerprint",
    "apply_security_migrations",
    "audit_completion_seq",
]
