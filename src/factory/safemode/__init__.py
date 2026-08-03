"""Roadmap PH-3 Diagnostic Safe Mode (CMP-DIAG, PH-3 scope; RPH3-T5).

A capability-scoped degraded mode: inspection / evidence export / integrity checks are read-only;
the only write path is ``approved_repair``, requiring a valid CMP-APPROVAL (consumed) **and** a
valid CMP-PERM grant, audited. There is **no autonomous-write path** and no approval bypass;
a capability outside the declared scope is refused; no mandatory control is weakened.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from factory.approval import ApprovalEngine, ApprovalRecord
from factory.audit import AuditEvent, AuditRecord, AuditValidator, AuditWriter, RecordKind
from factory.permission import Clock, PermissionEngine, PermissionGrant

_SEP = "\x1f"

AVAILABLE_CAPABILITIES = frozenset(
    {"inspect", "export_evidence", "integrity_check", "approved_repair"}
)
BLOCKED_CAPABILITIES = frozenset(
    {"autonomous_write", "normal_execution", "approval_bypass", "unrestricted_execution"}
)


class SafeModeError(Exception):
    code: str
    message: str

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message)
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, message={self.message!r})"


class SystemClock:
    def now_ts(self) -> int:
        return int(datetime.now(UTC).timestamp())

    def now_iso(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True, slots=True)
class SafeModeSession:
    reason: str
    available_capabilities: frozenset[str]
    blocked_capabilities: frozenset[str]


@dataclass(frozen=True, slots=True)
class InspectionResult:
    target: str
    valid: bool
    detail: str


@dataclass(frozen=True, slots=True)
class EvidenceExport:
    records: tuple[AuditRecord, ...]
    count: int


@dataclass(frozen=True, slots=True)
class RepairAction:
    capability: str
    description: str
    target: str


@dataclass(frozen=True, slots=True)
class RepairResult:
    applied: bool
    description: str


@dataclass(frozen=True, slots=True)
class SafeMode:
    """PH-3 Safe Mode. Read-only inspect/export; approval+permission-gated audited repair."""

    audit_database_path: Path
    permission_engine: PermissionEngine
    approval_engine: ApprovalEngine
    clock: Clock

    @property
    def _audit(self) -> AuditWriter:
        return AuditWriter(database_path=self.audit_database_path)

    @property
    def _validator(self) -> AuditValidator:
        return AuditValidator(database_path=self.audit_database_path)

    def enter(self, reason: str) -> SafeModeSession:
        """Enter Safe Mode; publish the capability-scope declaration (available vs blocked)."""
        return SafeModeSession(
            reason=reason,
            available_capabilities=AVAILABLE_CAPABILITIES,
            blocked_capabilities=BLOCKED_CAPABILITIES,
        )

    def inspect(self, target: str) -> InspectionResult:
        """Read-only integrity inspection (mutates no authoritative state)."""
        verdict = self._validator.verify_chain()
        return InspectionResult(
            target=target,
            valid=verdict.valid,
            detail="audit chain verified" if verdict.valid else f"break: {verdict.break_class}",
        )

    def export_evidence(self, start: int = 1, end: int | None = None) -> EvidenceExport:
        """Read-only evidence export of audit records in a sequence range."""
        records = self._audit.export(start=start, end=end)
        return EvidenceExport(records=records, count=len(records))

    def approved_repair(
        self,
        action: RepairAction,
        approval: ApprovalRecord,
        action_fingerprint: str,
        grant: PermissionGrant,
    ) -> RepairResult:
        """A repair applies ONLY with a valid consumed approval + a valid permission grant, audited.

        There is no autonomous-write path: an out-of-scope capability is refused; a missing/invalid
        approval or permission is denied (fails closed, no state mutated).
        """
        cap = action.capability
        if cap not in AVAILABLE_CAPABILITIES or cap in BLOCKED_CAPABILITIES:
            raise SafeModeError(
                "SAFEMODE_OUT_OF_SCOPE", f"capability {cap!r} is outside Safe Mode scope"
            )
        if not self.permission_engine.revalidate(grant, self.clock.now_ts()):
            raise SafeModeError("SAFEMODE_UNPERMITTED", "repair needs a valid permission grant")
        if not self.approval_engine.consume(approval, action_fingerprint):
            raise SafeModeError(
                "SAFEMODE_UNAPPROVED", "repair needs a valid CMP-APPROVAL (no autonomous write)"
            )
        self._audit_repair(action)
        return RepairResult(applied=True, description=action.description)

    def _audit_repair(self, action: RepairAction) -> AuditRecord:
        op_key = hashlib.sha256(
            f"repair{_SEP}{action.target}{_SEP}{uuid.uuid4().hex}".encode()
        ).hexdigest()
        payload = hashlib.sha256(
            _SEP.join((action.capability, action.description, action.target)).encode()
        ).hexdigest()
        return self._audit.append(
            AuditEvent(
                op_key=op_key,
                record_kind=RecordKind.COMPLETION,
                operation_class=1,
                actor="cmp-diag",
                action_class="safemode.repair",
                payload_hash=payload,
                occurred_at=self.clock.now_iso(),
                target_ref=action.target,
            )
        )


__all__ = [
    "AVAILABLE_CAPABILITIES",
    "BLOCKED_CAPABILITIES",
    "EvidenceExport",
    "InspectionResult",
    "RepairAction",
    "RepairResult",
    "SafeMode",
    "SafeModeError",
    "SafeModeSession",
    "SystemClock",
]
