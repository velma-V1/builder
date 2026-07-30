"""The Permission Enforcement engine (CMP-PERM, roadmap PH-3 / RPH3-T2).

Computes **least-privilege, deny-by-default** decisions, issues **scoped / expiring / revocable**
grants, and revalidates authority at the point of use (TOCTOU). It never auto-approves a deletion
(Decision B) or an out-of-envelope action (Decision A) — those return ``REQUIRES_APPROVAL``. Path
authority is delegated to the tested ``factory.contracts.validation.paths.PathAuthority``
(canonicalize + contain; raises on escape).

A grant issue / revoke / expire is a XSC-RPH3 **Class-1** cross-store op: durable intent →
a non-authoritative ``PENDING`` mutation → a durable completion audit (CMP-AUDITW, the commit point,
INV-1) → flip to ``COMMITTED`` (INV-2). A crash before the audit rolls the never-authoritative
mutation back; after the audit, forward. Audit-append failure fails closed (no authority granted).
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from factory.audit import (
    AuditError,
    AuditEvent,
    AuditRecord,
    AuditValidator,
    AuditWriter,
    RecordKind,
)
from factory.contracts.validation.paths import PathAuthority
from factory.permission.autonomy import AutonomyEnvelope, EnvelopeOutcome
from factory.permission.errors import PermissionError
from factory.permission.models import (
    APPROVAL_REQUIRED_CLASSES,
    ActionRequest,
    Clock,
    CommitState,
    DecisionKind,
    PermissionClass,
    PermissionDecision,
    PermissionGrant,
    PermissionState,
    TaskAuthority,
    grant_fingerprint,
)
from factory.permission.store import (
    SQLitePermissionReader,
    audit_completion_seq,
)
from factory.permission.writer import _PermissionWriter

_SEP = "\x1f"

# Permission class → PathAuthority operation (write-like classes are contained against read-only /
# exclusive leases). Non-path classes still map to a read-ish operation but skip path validation.
_CLASS_OPERATION: dict[PermissionClass, str] = {
    PermissionClass.READ: "read",
    PermissionClass.WRITE: "write",
    PermissionClass.DELETE: "delete",
    PermissionClass.EXECUTE: "execute",
    PermissionClass.NETWORK: "read",
    PermissionClass.EXTERNAL: "read",
}


class SystemClock:
    """Default wall clock. Epoch seconds drive expiry; ISO-8601 UTC stamps audit ``occurred_at``."""

    def now_ts(self) -> int:
        return int(datetime.now(UTC).timestamp())

    def now_iso(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_op_key(verb: str, subject: str) -> str:
    return hashlib.sha256(f"{verb}{_SEP}{subject}{_SEP}{uuid.uuid4().hex}".encode()).hexdigest()


def _payload_hash(*parts: str) -> str:
    return hashlib.sha256(_SEP.join(parts).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PermissionEngine:
    """Sole owner/writer of CTR-PERMISSION-GRANT instances in the security-spine store."""

    security_database_path: Path
    audit_database_path: Path
    clock: Clock

    @property
    def _writer(self) -> _PermissionWriter:
        return _PermissionWriter(database_path=self.security_database_path)

    @property
    def reader(self) -> SQLitePermissionReader:
        return SQLitePermissionReader(database_path=self.security_database_path)

    @property
    def _audit(self) -> AuditWriter:
        return AuditWriter(database_path=self.audit_database_path)

    @property
    def _validator(self) -> AuditValidator:
        return AuditValidator(database_path=self.audit_database_path)

    # --- decision (least-privilege, deny-by-default, Decision A/B) --------------------------------

    def decide(self, request: ActionRequest, authority: TaskAuthority) -> PermissionDecision:
        """Compute allow / deny / requires-approval for one action vs the authority ceiling."""
        if request.task_id != authority.task_id:
            return self._deny(request, "grant cannot exceed the current task (task mismatch)")
        if request.permission_class not in authority.allowed_classes:
            return self._deny(
                request, f"least-privilege: class {request.permission_class} not permitted"
            )

        canonical: str | None = None
        if request.resource is not None:
            path_authority = PathAuthority(project_root=Path(authority.project_root))
            result = path_authority.evaluate(
                request.resource,
                operation=_CLASS_OPERATION[request.permission_class],
                allowed=authority.allowed_paths,
                forbidden=authority.forbidden_paths,
                read_only=authority.read_only_paths,
                active_exclusive_paths=authority.exclusive_paths,
            )
            if not result.allowed:
                return self._deny(request, f"path denied: {result.reason}")
            canonical = result.normalized_relative

        if request.permission_class in APPROVAL_REQUIRED_CLASSES:
            return PermissionDecision(
                decision=DecisionKind.REQUIRES_APPROVAL,
                cause="deletion/external action is approval-required (Decision B / external)",
                request=request,
                canonical_resource=canonical,
            )
        if (
            AutonomyEnvelope.classify(request.permission_class, authority.autonomy_level)
            is EnvelopeOutcome.REQUIRES_CARD
        ):
            return PermissionDecision(
                decision=DecisionKind.REQUIRES_APPROVAL,
                cause="action is outside the task's autonomy envelope (Decision A)",
                request=request,
                canonical_resource=canonical,
            )
        return PermissionDecision(
            decision=DecisionKind.ALLOW,
            cause="least-privilege allow (in-envelope, path-contained)",
            request=request,
            canonical_resource=canonical,
        )

    @staticmethod
    def _deny(request: ActionRequest, cause: str) -> PermissionDecision:
        return PermissionDecision(
            decision=DecisionKind.DENY, cause=cause, request=request, canonical_resource=None
        )

    def canonicalize(self, raw_path: str, authority: TaskAuthority) -> str:
        """Canonicalize + contain a raw path against the task ownership; raise on any escape."""
        path_authority = PathAuthority(project_root=Path(authority.project_root))
        result = path_authority.evaluate(
            raw_path,
            operation="read",
            allowed=authority.allowed_paths or ("**",),
            forbidden=authority.forbidden_paths,
            read_only=authority.read_only_paths,
            active_exclusive_paths=(),
        )
        if not result.allowed:
            raise PermissionError("PERMISSION_PATH_ESCAPE", f"path denied: {result.reason}")
        return result.normalized_relative

    # --- grant issue (Class-1) -------------------------------------------------------------------

    def issue_grant(
        self, decision: PermissionDecision, ttl_seconds: int, *, actor: str = "cmp-perm"
    ) -> PermissionGrant:
        """Issue a scoped/expiring/revocable grant for an ALLOW decision (fails closed on audit)."""
        if decision.decision is not DecisionKind.ALLOW:
            raise PermissionError(
                "PERMISSION_NOT_ALLOWED",
                f"cannot issue a grant for a {decision.decision} decision",
            )
        if ttl_seconds <= 0:
            raise PermissionError("PERMISSION_INVALID_TTL", "ttl_seconds must be positive")

        request = decision.request
        grant_id = f"grn-{uuid.uuid4().hex}"
        ts = self.clock.now_ts()
        expires_at = ts + ttl_seconds
        fingerprint = grant_fingerprint(
            task_id=request.task_id, tool=request.tool, action=request.action,
            resource=decision.canonical_resource, scope=request.scope,
        )
        op_key = _new_op_key("issue", grant_id)
        self._writer.stage_issue(
            grant_id=grant_id, op_key=op_key, task_id=request.task_id, tool=request.tool,
            action=request.action, permission_class=request.permission_class,
            resource=decision.canonical_resource, scope=request.scope, purpose=request.purpose,
            grant_fingerprint=fingerprint, expires_at=expires_at, ts=ts,
        )
        payload = _payload_hash(grant_id, request.task_id, request.action, request.scope)
        try:
            audit = self._audit_completion(
                op_key=op_key, actor=actor, action_class="permission.issue",
                payload_hash=payload, target_ref=grant_id,
            )
        except AuditError as exc:
            self._writer.rollback_operation(
                grant_id=grant_id, op_key=op_key, verb="issue",
                failure_code="AUDIT_APPEND_FAILED", ts=self.clock.now_ts(),
            )
            raise PermissionError(
                "PERMISSION_AUDIT_FAILED", f"grant issue failed closed (audit unavailable): {exc}"
            ) from exc
        self._writer.commit_operation(
            grant_id=grant_id, op_key=op_key, audit_seq=audit.sequence, ts=ts
        )
        issued = self.reader.get_grant(grant_id)
        if issued is None:  # pragma: no cover - defensive; the row was just committed
            raise PermissionError("PERMISSION_NOT_FOUND", f"issued grant {grant_id} vanished")
        return issued

    # --- TOCTOU revalidation ---------------------------------------------------------------------

    def revalidate(self, grant: PermissionGrant, at_use_time: int) -> bool:
        """Pre-use recheck: honored only if still authoritative, active, unexpired, unchanged."""
        fresh = self.reader.get_grant(grant.grant_id)
        if fresh is None:
            return False
        return (
            fresh.commit_state is CommitState.COMMITTED
            and fresh.state is PermissionState.ACTIVE
            and at_use_time < fresh.expires_at
            and fresh.grant_fingerprint == grant.grant_fingerprint
        )

    # --- revoke / expire (Class-1) ---------------------------------------------------------------

    def revoke(self, grant_id: str) -> None:
        """Revoke an active grant (terminal). Each operation carries its own ``op_key``."""
        grant = self.reader.get_grant(grant_id)
        if grant is None:
            raise PermissionError("PERMISSION_NOT_FOUND", f"no grant {grant_id}")
        if grant.commit_state is not CommitState.COMMITTED:
            raise PermissionError("PERMISSION_INFLIGHT", f"grant {grant_id} is not settled")
        if grant.state is not PermissionState.ACTIVE:
            raise PermissionError(
                "PERMISSION_NOT_REVOCABLE", f"grant {grant_id} is terminal ({grant.state})"
            )
        self._run_transition(
            grant_id=grant_id, verb="revoke", new_state=PermissionState.REVOKED,
            actor="operator", action_class="permission.revoke",
        )

    def expire(self) -> tuple[str, ...]:
        """Auto-expire every committed active grant past its expiry (each audited)."""
        now = self.clock.now_ts()
        expired: list[str] = []
        for grant in self.reader.list_expirable(now):
            self._run_transition(
                grant_id=grant.grant_id, verb="expire", new_state=PermissionState.EXPIRED,
                actor="cmp-perm", action_class="permission.expire", ts=now,
            )
            expired.append(grant.grant_id)
        return tuple(expired)

    # --- startup reconciliation ------------------------------------------------------------------

    def reconcile_startup(self) -> None:
        """XSC-RPH3 §5: verify the audit chain, then roll each PENDING intent forward or back."""
        verdict = self._validator.verify_chain()
        if not verdict.valid:
            raise PermissionError(
                "PERMISSION_AUDIT_CHAIN_INVALID",
                f"audit chain not authoritative ({verdict.break_class}); refusing roll-forward",
            )
        now = self.clock.now_ts()
        for intent in self.reader.list_pending_intents():
            seq = audit_completion_seq(self.audit_database_path, intent.op_key)
            if seq is not None:
                self._writer.commit_operation(
                    grant_id=intent.grant_id, op_key=intent.op_key, audit_seq=seq, ts=now
                )
            else:
                self._writer.rollback_operation(
                    grant_id=intent.grant_id, op_key=intent.op_key, verb=intent.verb,
                    failure_code="RECONCILE_NO_AUDIT", ts=now,
                )

    # --- internals -------------------------------------------------------------------------------

    def _audit_completion(
        self, *, op_key: str, actor: str, action_class: str, payload_hash: str, target_ref: str
    ) -> AuditRecord:
        return self._audit.append(
            AuditEvent(
                op_key=op_key, record_kind=RecordKind.COMPLETION, operation_class=1, actor=actor,
                action_class=action_class, payload_hash=payload_hash,
                occurred_at=self.clock.now_iso(), target_ref=target_ref,
            )
        )

    def _run_transition(
        self, *, grant_id: str, verb: str, new_state: PermissionState, actor: str,
        action_class: str, ts: int | None = None,
    ) -> None:
        at = self.clock.now_ts() if ts is None else ts
        op_key = _new_op_key(verb, grant_id)
        self._writer.stage_transition(
            grant_id=grant_id, op_key=op_key, verb=verb, new_state=new_state, ts=at
        )
        payload = _payload_hash(grant_id, verb, str(new_state))
        try:
            audit = self._audit_completion(
                op_key=op_key, actor=actor, action_class=action_class,
                payload_hash=payload, target_ref=grant_id,
            )
        except AuditError as exc:
            self._writer.rollback_operation(
                grant_id=grant_id, op_key=op_key, verb=verb,
                failure_code="AUDIT_APPEND_FAILED", ts=self.clock.now_ts(),
            )
            raise PermissionError(
                "PERMISSION_AUDIT_FAILED", f"{verb} failed closed (audit unavailable): {exc}"
            ) from exc
        self._writer.commit_operation(
            grant_id=grant_id, op_key=op_key, audit_seq=audit.sequence, ts=at
        )


__all__ = ["PermissionEngine", "SystemClock"]
