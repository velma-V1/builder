"""Orchestrator-side bounded Watchdog Intervention Receiver (WIR)."""

from __future__ import annotations

import hmac
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from types import TracebackType
from typing import Protocol

from factory.audit import AuditError, AuditEvent, AuditRecord, AuditWriter, RecordKind
from factory.orchestrator.journal.reconciliation import reconcile_startup
from factory.orchestrator.models import ReconciliationOutcome, TaskState
from factory.watchdog.errors import WatchdogError
from factory.watchdog.failures import ServiceSupervisor
from factory.watchdog.models import (
    ALL_INTERVENTION_COMMANDS,
    AuthorityGate,
    Clock,
    InterventionCommand,
    InterventionOutcome,
    InterventionRecord,
    InterventionRequest,
    InterventionResult,
    InterventionStatus,
    ReconciliationState,
    TaskReader,
    TaskWriter,
    task_state_hash,
)
from factory.watchdog.store import SQLiteInterventionReader
from factory.watchdog.writer import _InterventionWriter

_TASK_COMMANDS = frozenset(
    {
        InterventionCommand.PAUSE_TASK,
        InterventionCommand.CONTAIN_TASK,
        InterventionCommand.RECONCILE_STATE,
        InterventionCommand.QUARANTINE_RESOURCE,
    }
)
_INERT_COMMANDS = frozenset(
    {
        InterventionCommand.RESTORE_APPROVED_STATE,
        InterventionCommand.ACTIVATE_VERIFIED_SNAPSHOT,
    }
)


class _ReceiverLock(Protocol):
    def __enter__(self) -> bool: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class WatchdogInterventionReceiver:
    """Internal mediator; the Watchdog itself receives no authoritative write capability."""

    intervention_database_path: Path
    audit_database_path: Path
    task_reader: TaskReader
    task_writer: TaskWriter
    authority_gate: AuthorityGate
    supervisor: ServiceSupervisor
    clock: Clock
    supervised_identity: str
    auth_token: str
    _lock: _ReceiverLock = field(default_factory=Lock, init=False, repr=False, compare=False)

    @property
    def _writer(self) -> _InterventionWriter:
        return _InterventionWriter(self.intervention_database_path)

    @property
    def reader(self) -> SQLiteInterventionReader:
        return SQLiteInterventionReader(self.intervention_database_path)

    @property
    def _audit(self) -> AuditWriter:
        return AuditWriter(self.audit_database_path)

    def service_state_hash(self, service_id: str) -> str:
        return self.supervisor.state_hash(service_id)

    def intervene(self, request: InterventionRequest) -> InterventionResult:
        with self._lock:
            return self._intervene(request)

    def _intervene(self, request: InterventionRequest) -> InterventionResult:
        existing = self.reader.get(request.idempotency_key)
        if existing is not None:
            if existing.request_hash != request.request_hash():
                return self._result(
                    request,
                    InterventionOutcome.REJECTED,
                    None,
                    "idempotency-key collision",
                )
            if existing.result_outcome is not None:
                return self._recorded_result(request, existing)
            self.reconcile_startup()
            reconciled = self.reader.get(request.idempotency_key)
            if reconciled is not None and reconciled.result_outcome is not None:
                return self._recorded_result(request, reconciled)
            raise WatchdogError(
                "INTERVENTION_UNSETTLED", "intervention remains unsettled after reconciliation"
            )

        command = self._parse_command(request)
        if command is None:
            return self._terminal(
                request, InterventionOutcome.REJECTED, "command failed immutable allowlist"
            )
        if not self._authenticated(request):
            return self._terminal(request, InterventionOutcome.REJECTED, "authentication failed")
        if command in _INERT_COMMANDS:
            return self._terminal(request, InterventionOutcome.INERT, "command is inert until PH-7")
        if (
            command is InterventionCommand.QUARANTINE_RESOURCE
            and self.task_reader.get_task(request.target_ref) is None
        ):
            return self._terminal(
                request,
                InterventionOutcome.INERT,
                "non-task resource quarantine is inert until PH-5",
            )
        if not self._bounded(request):
            return self._terminal(
                request, InterventionOutcome.REJECTED, "bounded target validation failed"
            )
        if not self._expected_matches(command, request):
            return self._terminal(request, InterventionOutcome.REJECTED, "expected-state mismatch")
        if not self.authority_gate.authorize(request):
            return self._terminal(
                request,
                InterventionOutcome.REJECTED,
                "approval/permission authority gate denied intervention",
            )

        if command is InterventionCommand.RESTART_SERVICE:
            return self._restart(request)
        return self._task_intervention(command, request)

    def reconcile_startup(self) -> None:
        for record in self.reader.pending():
            if record.operation_class == 3:
                self._reconcile_restart(record)
                continue
            applied = any(
                event.accepted
                and event.idempotency_key == record.op_key
                and str(event.new_state) == record.desired_state
                for event in self.task_reader.get_events(record.target_ref)
            )
            outcome = InterventionOutcome.APPLIED if applied else InterventionOutcome.FAILED
            audit = self._audit_record(record.op_key, RecordKind.COMPLETION)
            if audit is None:
                audit = self._append_completion(
                    record.op_key,
                    record.operation_class,
                    record.request_hash,
                    record.target_ref,
                    "watchdog.reconcile",
                )
            self._writer.finish(
                record.op_key,
                status=(InterventionStatus.COMMITTED if applied else InterventionStatus.ABORTED),
                reconciliation=(
                    ReconciliationState.ROLL_FORWARD if applied else ReconciliationState.ROLL_BACK
                ),
                outcome=outcome,
                cause=(
                    "committed task transition audit rolled forward"
                    if applied
                    else "no committed task transition to roll forward"
                ),
                audit_seq=audit.sequence,
                failure_code=None if applied else "TRANSITION_NOT_COMMITTED",
                now=self.clock.now_ts(),
            )

    def _reconcile_restart(self, record: InterventionRecord) -> None:
        completion = self._audit_record(record.op_key, RecordKind.COMPLETION)
        if completion is not None and completion.action_class == "watchdog.restart_service":
            self._writer.finish(
                record.op_key,
                status=InterventionStatus.COMMITTED,
                reconciliation=ReconciliationState.ROLL_FORWARD,
                outcome=InterventionOutcome.APPLIED,
                cause="durable restart completion reconciled",
                audit_seq=completion.sequence,
                failure_code=None,
                now=self.clock.now_ts(),
            )
            return

        intent = self._audit_record(record.op_key, RecordKind.INTENT)
        if intent is None:
            self._audit.append(
                AuditEvent(
                    op_key=record.op_key,
                    record_kind=RecordKind.INTENT,
                    operation_class=3,
                    actor="watchdog-intervention-receiver",
                    action_class="watchdog.restart_aborted",
                    payload_hash=record.request_hash,
                    occurred_at=self.clock.now_iso(),
                    target_ref=record.target_ref,
                )
            )
            completion = self._append_completion(
                record.op_key,
                3,
                record.request_hash,
                record.target_ref,
                "watchdog.restart_aborted",
            )
            self._writer.finish(
                record.op_key,
                status=InterventionStatus.ABORTED,
                reconciliation=ReconciliationState.ROLL_BACK,
                outcome=InterventionOutcome.FAILED,
                cause="restart had no durable audit intent and was not issued",
                audit_seq=completion.sequence,
                failure_code="RESTART_NOT_ISSUED",
                now=self.clock.now_ts(),
            )
            return

        completion = self._append_completion(
            record.op_key,
            3,
            record.request_hash,
            record.target_ref,
            "watchdog.restart_uncertain",
        )
        self._writer.finish(
            record.op_key,
            status=InterventionStatus.QUARANTINED,
            reconciliation=ReconciliationState.QUARANTINE,
            outcome=InterventionOutcome.FAILED,
            cause="uncertain external restart quarantined; never retried",
            audit_seq=completion.sequence,
            failure_code="RESTART_OUTCOME_UNPROVEN",
            now=self.clock.now_ts(),
        )

    @staticmethod
    def _parse_command(request: InterventionRequest) -> InterventionCommand | None:
        try:
            parsed = InterventionCommand(str(request.command))
        except ValueError:
            return None
        return parsed if parsed in ALL_INTERVENTION_COMMANDS else None

    def _authenticated(self, request: InterventionRequest) -> bool:
        return hmac.compare_digest(
            request.requestor, self.supervised_identity
        ) and hmac.compare_digest(request.auth_token, self.auth_token)

    @staticmethod
    def _bounded(request: InterventionRequest) -> bool:
        return (
            bool(request.target_ref)
            and len(request.target_ref) <= 256
            and len(request.reason) <= 512
            and not any(marker in request.target_ref for marker in ("*", ",", "\n", "\x00"))
        )

    def _expected_matches(self, command: InterventionCommand, request: InterventionRequest) -> bool:
        if command in _TASK_COMMANDS:
            return request.expected_state == task_state_hash(
                self.task_reader.get_task(request.target_ref)
            )
        return request.expected_state == self.supervisor.state_hash(request.target_ref)

    def _task_intervention(
        self, command: InterventionCommand, request: InterventionRequest
    ) -> InterventionResult:
        current = self.task_reader.get_task(request.target_ref)
        if current is None:
            return self._terminal(
                request, InterventionOutcome.REJECTED, "task target does not exist"
            )
        desired = self._desired_task_state(command, current.current_state, request.target_ref)
        self._writer.stage(request, 2, self.clock.now_ts(), desired_state=str(desired))
        try:
            event = self.task_writer.apply_transition(
                task_id=request.target_ref,
                expected_current_state=current.current_state,
                new_state=desired,
                cause=request.reason,
                actor="watchdog-intervention-receiver",
                linked_reference=request.idempotency_key,
                idempotency_key=request.idempotency_key,
            )
        except Exception as exc:
            return self._finish_failure(request, 2, f"task transition failed: {exc}")
        if not event.accepted:
            return self._finish_failure(request, 2, "task transition was not legal")
        audit = self._append_completion(
            request.idempotency_key,
            2,
            request.request_hash(),
            request.target_ref,
            f"watchdog.{command.value.lower()}",
        )
        self._writer.finish(
            request.idempotency_key,
            status=InterventionStatus.COMMITTED,
            reconciliation=ReconciliationState.ROLL_FORWARD,
            outcome=InterventionOutcome.APPLIED,
            cause="intervention applied and audit durable",
            audit_seq=audit.sequence,
            failure_code=None,
            now=self.clock.now_ts(),
        )
        return self._result(
            request,
            InterventionOutcome.APPLIED,
            audit.sequence,
            "intervention applied and audit durable",
        )

    def _desired_task_state(
        self, command: InterventionCommand, current: TaskState, task_id: str
    ) -> TaskState:
        if command is InterventionCommand.PAUSE_TASK:
            return TaskState.PAUSED
        if command in (
            InterventionCommand.CONTAIN_TASK,
            InterventionCommand.QUARANTINE_RESOURCE,
        ):
            return TaskState.QUARANTINED
        outcomes = reconcile_startup(self.task_reader, [task_id])
        outcome = outcomes[task_id]
        mapping = {
            ReconciliationOutcome.BLOCKED: TaskState.BLOCKED,
            ReconciliationOutcome.FAILED: TaskState.FAILED,
            ReconciliationOutcome.QUARANTINED: TaskState.QUARANTINED,
        }
        return mapping.get(outcome, current)

    def _restart(self, request: InterventionRequest) -> InterventionResult:
        self._writer.stage(request, 3, self.clock.now_ts())
        try:
            intent = self._audit.append(
                AuditEvent(
                    op_key=request.idempotency_key,
                    record_kind=RecordKind.INTENT,
                    operation_class=3,
                    actor="watchdog-intervention-receiver",
                    action_class="watchdog.restart_service",
                    payload_hash=request.request_hash(),
                    occurred_at=self.clock.now_iso(),
                    target_ref=request.target_ref,
                )
            )
            self._writer.mark_audit_intent(
                request.idempotency_key, intent.sequence, self.clock.now_ts()
            )
            restarted = self.supervisor.restart(request.target_ref)
        except (AuditError, WatchdogError) as exc:
            return self._finish_failure(request, 3, f"service restart failed closed: {exc}")
        if not restarted:
            return self._finish_failure(request, 3, "service restart exhausted bounded retries")
        completion = self._append_completion(
            request.idempotency_key,
            3,
            request.request_hash(),
            request.target_ref,
            "watchdog.restart_service",
        )
        self._writer.finish(
            request.idempotency_key,
            status=InterventionStatus.COMMITTED,
            reconciliation=ReconciliationState.ROLL_FORWARD,
            outcome=InterventionOutcome.APPLIED,
            cause="service restart applied and audit durable",
            audit_seq=completion.sequence,
            failure_code=None,
            now=self.clock.now_ts(),
        )
        return self._result(
            request,
            InterventionOutcome.APPLIED,
            completion.sequence,
            "service restart applied and audit durable",
        )

    def _finish_failure(
        self, request: InterventionRequest, operation_class: int, cause: str
    ) -> InterventionResult:
        audit_seq: int | None = None
        try:
            audit = self._append_completion(
                request.idempotency_key,
                operation_class,
                request.request_hash(),
                request.target_ref,
                "watchdog.intervention_failed",
            )
            audit_seq = audit.sequence
        except AuditError as exc:
            if operation_class == 2:
                raise WatchdogError(
                    "WIR_AUDIT_UNAVAILABLE",
                    "audit finalize unavailable; intervention is not APPLIED",
                ) from exc
        self._writer.finish(
            request.idempotency_key,
            status=(
                InterventionStatus.QUARANTINED
                if operation_class == 3
                else InterventionStatus.ABORTED
            ),
            reconciliation=(
                ReconciliationState.QUARANTINE
                if operation_class == 3
                else ReconciliationState.ROLL_BACK
            ),
            outcome=InterventionOutcome.FAILED,
            cause=cause,
            audit_seq=audit_seq,
            failure_code="EXECUTION_FAILED",
            now=self.clock.now_ts(),
        )
        return self._result(request, InterventionOutcome.FAILED, None, cause)

    def _terminal(
        self,
        request: InterventionRequest,
        outcome: InterventionOutcome,
        cause: str,
    ) -> InterventionResult:
        self._writer.stage(request, 1, self.clock.now_ts())
        audit = self._append_completion(
            request.idempotency_key,
            1,
            request.request_hash(),
            request.target_ref,
            "watchdog.validation",
        )
        self._writer.finish(
            request.idempotency_key,
            status=InterventionStatus.ABORTED,
            reconciliation=ReconciliationState.ROLL_BACK,
            outcome=outcome,
            cause=cause,
            audit_seq=audit.sequence,
            failure_code=None,
            now=self.clock.now_ts(),
        )
        return self._result(request, outcome, None, cause)

    def _append_completion(
        self,
        op_key: str,
        operation_class: int,
        payload_hash: str,
        target_ref: str,
        action_class: str,
    ) -> AuditRecord:
        return self._audit.append(
            AuditEvent(
                op_key=op_key,
                record_kind=RecordKind.COMPLETION,
                operation_class=operation_class,
                actor="watchdog-intervention-receiver",
                action_class=action_class,
                payload_hash=payload_hash,
                occurred_at=self.clock.now_iso(),
                target_ref=target_ref,
            )
        )

    def _audit_record(self, op_key: str, record_kind: RecordKind) -> AuditRecord | None:
        return next(
            (
                record
                for record in self._audit.export()
                if record.op_key == op_key and record.record_kind is record_kind
            ),
            None,
        )

    @staticmethod
    def _result(
        request: InterventionRequest,
        outcome: InterventionOutcome,
        audit_seq: int | None,
        cause: str,
    ) -> InterventionResult:
        return InterventionResult(
            command=request.command,
            target_ref=request.target_ref,
            idempotency_key=request.idempotency_key,
            outcome=outcome,
            audit_seq=audit_seq,
            cause=cause,
        )

    @staticmethod
    def _recorded_result(
        request: InterventionRequest, record: InterventionRecord
    ) -> InterventionResult:
        outcome = record.result_outcome
        if outcome is None:
            raise WatchdogError("INTERVENTION_UNSETTLED", "record has no terminal outcome")
        return WatchdogInterventionReceiver._result(
            request,
            outcome,
            record.audit_seq if outcome is InterventionOutcome.APPLIED else None,
            record.result_cause or "",
        )


__all__ = ["WatchdogInterventionReceiver"]
