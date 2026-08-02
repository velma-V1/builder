"""The Approval Engine (CMP-APPROVAL, roadmap PH-3 / RPH3-T3).

Maintains the central approval queue and issues **bound, expiring, revocable** approvals — never
reusable, permanent, or unbounded (01K §2.8-9). A security-violating request is denied + audited and
**never queued** (01K acceptance). Every issue / decide / consume / revoke / expire is a XSC-RPH3
**Class-1** cross-store operation:

* ``S1`` durable intent (``PENDING``) + ``S2`` a non-authoritative ``PENDING`` mutation
  (``_ApprovalWriter``),
* ``S3`` a **durable completion audit** via CMP-AUDITW — the point after which success may be
  reported (INV-1), and
* ``S4`` flip the mutation to ``COMMITTED`` (INV-2: a reader honors only ``COMMITTED`` rows).

If a crash falls between ``S2`` and ``S3`` the intent is ``PENDING`` with no audit and startup
reconciliation rolls the never-authoritative mutation back (``ABORTED``); between ``S3`` and ``S4``
the audit is durable and reconciliation rolls forward to ``COMMITTED``. If the audit append itself
fails the operation fails closed (no authority is granted).
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

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
    OperatorDecision,
    action_fingerprint,
)
from factory.approval.store import (
    SQLiteApprovalReader,
    audit_completion_seq,
)
from factory.approval.writer import _ApprovalWriter
from factory.audit import (
    AuditError,
    AuditEvent,
    AuditRecord,
    AuditValidator,
    AuditWriter,
    RecordKind,
)

_SEP = "\x1f"


class SystemClock:
    """Default wall clock. Epoch seconds drive expiry; ISO-8601 UTC stamps audit ``occurred_at``."""

    def now_ts(self) -> int:
        return int(datetime.now(UTC).timestamp())

    def now_iso(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_op_key(verb: str, subject: str) -> str:
    """A fresh idempotency key K for one operation instance (unique per call, tied to subject)."""
    return hashlib.sha256(f"{verb}{_SEP}{subject}{_SEP}{uuid.uuid4().hex}".encode()).hexdigest()


def _payload_hash(*parts: str) -> str:
    return hashlib.sha256(_SEP.join(parts).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ApprovalEngine:
    """Sole owner/writer of the approval queue + CTR-APPROVAL-RECORD instances."""

    security_database_path: Path
    audit_database_path: Path
    clock: Clock

    @property
    def _writer(self) -> _ApprovalWriter:
        return _ApprovalWriter(database_path=self.security_database_path)

    @property
    def reader(self) -> SQLiteApprovalReader:
        return SQLiteApprovalReader(database_path=self.security_database_path)

    @property
    def _audit(self) -> AuditWriter:
        return AuditWriter(database_path=self.audit_database_path)

    @property
    def _validator(self) -> AuditValidator:
        return AuditValidator(database_path=self.audit_database_path)

    # --- audit helper (Class-1 completion only) --------------------------------------------------

    def _audit_completion(
        self, *, op_key: str, actor: str, action_class: str, payload_hash: str, target_ref: str
    ) -> AuditRecord:
        return self._audit.append(
            AuditEvent(
                op_key=op_key,
                record_kind=RecordKind.COMPLETION,
                operation_class=1,
                actor=actor,
                action_class=action_class,
                payload_hash=payload_hash,
                occurred_at=self.clock.now_iso(),
                target_ref=target_ref,
            )
        )

    # --- issue -----------------------------------------------------------------------------------

    def enqueue(self, request: ApprovalRequest) -> ApprovalCard:
        """Enqueue an approval request and return its complete operator card (01L §3.2).

        A security-violating request is **denied + audited and never queued** — this raises
        ``APPROVAL_SECURITY_VIOLATION`` after recording the denial (fails closed).
        """
        self._validate_request(request)

        if request.security_violation:
            op_key = _new_op_key("security_violation", request.task_id)
            payload = _payload_hash(
                request.task_id, request.tool, request.action, request.scope, "security_violation"
            )
            try:
                self._audit_completion(
                    op_key=op_key,
                    actor=request.actor,
                    action_class="approval.security_violation_denied",
                    payload_hash=payload,
                    target_ref=request.task_id,
                )
            except AuditError as exc:  # fail closed either way — never queued
                raise ApprovalError(
                    "APPROVAL_SECURITY_VIOLATION",
                    f"security-violating request denied (audit also failed: {exc})",
                ) from exc
            raise ApprovalError(
                "APPROVAL_SECURITY_VIOLATION",
                "a security violation is never offered as an approvable action (denied + audited)",
            )

        approval_id = f"apr-{uuid.uuid4().hex}"
        ts = self.clock.now_ts()
        expires_at = ts + request.ttl_seconds
        op_key = _new_op_key("enqueue", approval_id)

        self._writer.stage_enqueue(
            approval_id=approval_id,
            op_key=op_key,
            task_id=request.task_id,
            tool=request.tool,
            action=request.action,
            resource=request.resource,
            scope=request.scope,
            purpose=request.purpose,
            consequences=request.consequences,
            autonomy_level=request.autonomy_level,
            repetition_limit=request.repetition_limit,
            requires_confirmation=request.destructive,
            expires_at=expires_at,
            ts=ts,
        )
        payload = _payload_hash(approval_id, request.task_id, request.action, request.scope)
        try:
            audit = self._audit_completion(
                op_key=op_key,
                actor=request.actor,
                action_class="approval.enqueue",
                payload_hash=payload,
                target_ref=approval_id,
            )
        except AuditError as exc:
            self._writer.rollback_operation(
                approval_id=approval_id,
                op_key=op_key,
                verb="enqueue",
                failure_code="AUDIT_APPEND_FAILED",
                ts=self.clock.now_ts(),
            )
            raise ApprovalError(
                "APPROVAL_AUDIT_FAILED", f"enqueue failed closed (audit unavailable): {exc}"
            ) from exc

        self._writer.commit_operation(
            approval_id=approval_id,
            op_key=op_key,
            audit_seq=audit.sequence,
            ts=ts,
            drop_queue=False,
        )
        return ApprovalCard(
            approval_id=approval_id,
            task_id=request.task_id,
            tool=request.tool,
            action=request.action,
            resource=request.resource,
            scope=request.scope,
            purpose=request.purpose,
            repetition_limit=request.repetition_limit,
            expires_at=expires_at,
            consequences=request.consequences,
            autonomy_level=request.autonomy_level,
            state=ApprovalState.PENDING,
            requires_separate_confirmation=request.destructive,
        )

    # --- decide ----------------------------------------------------------------------------------

    def decide(self, card_id: str, decision: OperatorDecision) -> ApprovalRecord | Denial:
        """Apply an operator grant/deny to a pending card. Grant issues a bound/expiring record."""
        record = self.reader.get_record(card_id)
        if record is None:
            raise ApprovalError("APPROVAL_NOT_FOUND", f"no approval card {card_id}")
        is_awaiting = (
            record.commit_state is CommitState.COMMITTED and record.state is ApprovalState.PENDING
        )
        if not is_awaiting:
            raise ApprovalError(
                "APPROVAL_NOT_PENDING",
                f"card {card_id} is not awaiting a decision ({record.state})",
            )

        if decision.decision is DecisionKind.DENY:
            self._run_transition(
                approval_id=card_id,
                verb="deny",
                new_state=ApprovalState.DENIED,
                actor=decision.operator,
                action_class="approval.deny",
            )
            return Denial(
                reason_code="OPERATOR_DENIED",
                message="operator denied the request",
                approval_id=card_id,
            )

        # GRANT — a destructive/external action needs the separate explicit confirmation.
        if record.requires_confirmation and not decision.confirmed_destructive:
            return Denial(
                reason_code="CONFIRMATION_REQUIRED",
                message="destructive/external action needs a separate explicit confirmation",
                approval_id=card_id,
            )

        fingerprint = action_fingerprint(
            task_id=record.task_id,
            tool=record.tool,
            action=record.action,
            resource=record.resource,
            scope=record.scope,
        )
        self._run_transition(
            approval_id=card_id,
            verb="grant",
            new_state=ApprovalState.GRANTED,
            actor=decision.operator,
            action_class="approval.grant",
            fingerprint=fingerprint,
        )
        granted = self.reader.get_record(card_id)
        if granted is None:  # pragma: no cover - defensive; the row was just committed
            raise ApprovalError("APPROVAL_NOT_FOUND", f"granted record {card_id} vanished")
        return granted

    # --- consume ---------------------------------------------------------------------------------

    def consume(self, record: ApprovalRecord, action_fingerprint_value: str) -> bool:
        """Consume one use of a bound approval iff it is valid and the fingerprint matches scope.

        Returns ``False`` (denied) for an expired / revoked / exhausted / out-of-scope attempt — a
        consumed/expired/revoked record can never be reused (01K-AC-03). Fails closed (raises) only
        on an audit-infrastructure failure.
        """
        fresh = self.reader.get_record(record.approval_id)
        if fresh is None:
            return False
        at = self.clock.now_ts()
        if not self.is_valid(fresh, at):
            return False
        if fresh.action_fingerprint != action_fingerprint_value:
            return False  # scope binding: bound to (task, action, path, scope), rejects any other

        uses_after = fresh.uses_consumed + 1
        exhausted = uses_after >= fresh.repetition_limit
        new_state = ApprovalState.CONSUMED if exhausted else ApprovalState.GRANTED
        self._run_transition(
            approval_id=fresh.approval_id,
            verb="consume",
            new_state=new_state,
            actor="cmp-approval",
            action_class="approval.consume",
            increment_use=True,
            ts=at,
        )
        return True

    # --- revoke ----------------------------------------------------------------------------------

    def revoke(self, record_id: str) -> None:
        """Revoke a pending or granted approval (terminal). Each op carries its own ``op_key``."""
        record = self.reader.get_record(record_id)
        if record is None:
            raise ApprovalError("APPROVAL_NOT_FOUND", f"no approval record {record_id}")
        if record.commit_state is not CommitState.COMMITTED:
            raise ApprovalError("APPROVAL_INFLIGHT", f"record {record_id} is not settled")
        if record.state not in (ApprovalState.PENDING, ApprovalState.GRANTED):
            raise ApprovalError(
                "APPROVAL_NOT_REVOCABLE", f"record {record_id} is terminal ({record.state})"
            )
        self._run_transition(
            approval_id=record_id,
            verb="revoke",
            new_state=ApprovalState.REVOKED,
            actor="operator",
            action_class="approval.revoke",
        )

    # --- expire ----------------------------------------------------------------------------------

    def expire(self) -> tuple[str, ...]:
        """Auto-expire every committed pending/granted approval past its expiry (each audited)."""
        now = self.clock.now_ts()
        expired: list[str] = []
        for record in self.reader.list_expirable(now):
            self._run_transition(
                approval_id=record.approval_id,
                verb="expire",
                new_state=ApprovalState.EXPIRED,
                actor="cmp-approval",
                action_class="approval.expire",
                ts=now,
            )
            expired.append(record.approval_id)
        return tuple(expired)

    # --- validity predicate ----------------------------------------------------------------------

    def is_valid(self, record: ApprovalRecord, at: int) -> bool:
        """Scope+expiry+repetition check: authoritative, granted, unexpired, uses remaining."""
        return (
            record.commit_state is CommitState.COMMITTED
            and record.state is ApprovalState.GRANTED
            and at < record.expires_at
            and record.uses_consumed < record.repetition_limit
        )

    # --- startup reconciliation ------------------------------------------------------------------

    def reconcile_startup(self) -> None:
        """XSC-RPH3 §5: verify the audit chain, then roll each PENDING intent forward or back.

        No roll-forward is attempted against an invalid audit chain (Safe Mode / fail closed).
        """
        verdict = self._validator.verify_chain()
        if not verdict.valid:
            raise ApprovalError(
                "APPROVAL_AUDIT_CHAIN_INVALID",
                f"audit chain not authoritative ({verdict.break_class}); refusing roll-forward",
            )
        now = self.clock.now_ts()
        for intent in self.reader.list_pending_intents():
            seq = audit_completion_seq(self.audit_database_path, intent.op_key)
            if seq is not None:
                self._writer.commit_operation(
                    approval_id=intent.approval_id,
                    op_key=intent.op_key,
                    audit_seq=seq,
                    ts=now,
                    drop_queue=intent.verb != "enqueue",
                )
            else:
                self._writer.rollback_operation(
                    approval_id=intent.approval_id,
                    op_key=intent.op_key,
                    verb=intent.verb,
                    failure_code="RECONCILE_NO_AUDIT",
                    ts=now,
                )

    # --- internals -------------------------------------------------------------------------------

    def _run_transition(
        self,
        *,
        approval_id: str,
        verb: str,
        new_state: ApprovalState,
        actor: str,
        action_class: str,
        fingerprint: str | None = None,
        increment_use: bool = False,
        ts: int | None = None,
    ) -> None:
        """Stage → completion-audit → commit for one Class-1 lifecycle transition (fail closed)."""
        at = self.clock.now_ts() if ts is None else ts
        op_key = _new_op_key(verb, approval_id)
        self._writer.stage_transition(
            approval_id=approval_id,
            op_key=op_key,
            verb=verb,
            new_state=new_state,
            ts=at,
            action_fingerprint=fingerprint,
            increment_use=increment_use,
        )
        payload = _payload_hash(approval_id, verb, str(new_state))
        try:
            audit = self._audit_completion(
                op_key=op_key,
                actor=actor,
                action_class=action_class,
                payload_hash=payload,
                target_ref=approval_id,
            )
        except AuditError as exc:
            self._writer.rollback_operation(
                approval_id=approval_id,
                op_key=op_key,
                verb=verb,
                failure_code="AUDIT_APPEND_FAILED",
                ts=self.clock.now_ts(),
            )
            raise ApprovalError(
                "APPROVAL_AUDIT_FAILED", f"{verb} failed closed (audit unavailable): {exc}"
            ) from exc
        self._writer.commit_operation(
            approval_id=approval_id, op_key=op_key, audit_seq=audit.sequence, ts=at, drop_queue=True
        )

    @staticmethod
    def _validate_request(request: ApprovalRequest) -> None:
        if request.ttl_seconds <= 0:
            raise ApprovalError("APPROVAL_INVALID_REQUEST", "ttl_seconds must be positive")
        if request.repetition_limit < 1:
            raise ApprovalError("APPROVAL_INVALID_REQUEST", "repetition_limit must be >= 1")
        required = (
            request.task_id,
            request.tool,
            request.action,
            request.scope,
            request.purpose,
            request.consequences,
            request.autonomy_level,
        )
        if not all(bool(field) for field in required):
            raise ApprovalError(
                "APPROVAL_INVALID_REQUEST", "card scope incomplete (01L §3.2 fields required)"
            )


__all__ = ["ApprovalEngine", "SystemClock"]
