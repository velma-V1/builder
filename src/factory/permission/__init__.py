"""Roadmap PH-3 Permission Enforcement (CMP-PERM, RPH3-T2).

Least-privilege, deny-by-default permission decisions; scoped/expiring/revocable grants; TOCTOU
revalidation; path authority (canonicalize + contain). Decision B (all deletion approval-gated) and
Decision A (autonomy envelope) are enforced; every grant event is a XSC-RPH3 Class-1 operation
audited via CMP-AUDITW. The writable connection lives in a private, un-exported writer; the public
surface is the engine plus read-only models + reader.
"""

from __future__ import annotations

from factory.permission.autonomy import AutonomyEnvelope, EnvelopeOutcome
from factory.permission.engine import PermissionEngine, SystemClock
from factory.permission.errors import PermissionError
from factory.permission.models import (
    ActionRequest,
    Clock,
    CommitState,
    DecisionKind,
    IntentStatus,
    PermissionClass,
    PermissionDecision,
    PermissionGrant,
    PermissionState,
    ReconciliationState,
    TaskAuthority,
    grant_fingerprint,
)
from factory.permission.store import (
    SQLitePermissionReader,
    apply_permission_migrations,
    audit_completion_seq,
)

__all__ = [
    "ActionRequest",
    "AutonomyEnvelope",
    "Clock",
    "CommitState",
    "DecisionKind",
    "EnvelopeOutcome",
    "IntentStatus",
    "PermissionClass",
    "PermissionDecision",
    "PermissionEngine",
    "PermissionError",
    "PermissionGrant",
    "PermissionState",
    "ReconciliationState",
    "SQLitePermissionReader",
    "SystemClock",
    "TaskAuthority",
    "apply_permission_migrations",
    "audit_completion_seq",
    "grant_fingerprint",
]
