"""Roadmap PH-3 tamper-evident audit chain (CMP-AUDITW writer + CMP-AUDITV validator).

Separate append-only, hash-chained store (not the frozen runtime-state DB). CMP-AUDITW is the sole
appender; CMP-AUDITV is a read-only integrity verifier. Public surface for RPH3-T4.
"""

from __future__ import annotations

from factory.audit.errors import AuditError
from factory.audit.models import (
    GENESIS_ANCHOR,
    AuditEvent,
    AuditRecord,
    BreakClass,
    ChainHead,
    IntegrityVerdict,
    RecordKind,
)
from factory.audit.validator import AuditValidator
from factory.audit.writer import AuditWriter, apply_audit_migrations

__all__ = [
    "GENESIS_ANCHOR",
    "AuditError",
    "AuditEvent",
    "AuditRecord",
    "AuditValidator",
    "AuditWriter",
    "BreakClass",
    "ChainHead",
    "IntegrityVerdict",
    "RecordKind",
    "apply_audit_migrations",
]
