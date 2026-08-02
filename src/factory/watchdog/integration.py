"""Repository-defined Lane A / Lane B wiring for roadmap PH-3.

This is an adapter inside CMP-WATCH, not a new component or execution subsystem. It consumes the
accepted Lane B public result models by value, propagates ordinary denials as terminal denials,
routes declared degradation to the accepted Safe Mode, and delivers only core-control failures to
the internal WIR. It never invokes tools, performs file operations, writes Lane B stores, or gains
an authoritative-state connection.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import StrEnum
from threading import Lock
from types import TracebackType
from typing import Protocol

from factory.approval import ApprovalRecord, ApprovalState
from factory.audit import AuditValidator
from factory.fileops import FileOpError
from factory.orchestrator.store.runtime_state import OrchestratorStateReader
from factory.permission import (
    DecisionKind as PermissionDecisionKind,
)
from factory.permission import (
    PermissionDecision,
)
from factory.safemode import SafeMode, SafeModeSession
from factory.tools import Denial as ToolDenial
from factory.tools import ToolResult
from factory.watchdog.control import WatchdogControl
from factory.watchdog.errors import WatchdogError
from factory.watchdog.interventions import WatchdogInterventionReceiver
from factory.watchdog.models import (
    Clock,
    InterventionCommand,
    InterventionOutcome,
    InterventionResult,
    task_state_hash,
)

_SEP = "\x1f"


class LaneBSignalKind(StrEnum):
    HEALTHY = "HEALTHY"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVAL_DENIED = "APPROVAL_DENIED"
    APPROVAL_EXPIRED = "APPROVAL_EXPIRED"
    APPROVAL_REPLAY = "APPROVAL_REPLAY"
    TOOL_GATEWAY_DENIED = "TOOL_GATEWAY_DENIED"
    FILEOP_DENIED = "FILEOP_DENIED"
    AUDIT_BREAK = "AUDIT_BREAK"
    DEPENDENCY_FAILURE = "DEPENDENCY_FAILURE"
    SAFE_MODE_REQUIRED = "SAFE_MODE_REQUIRED"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"


class CrossLaneOutcome(StrEnum):
    HEALTHY = "HEALTHY"
    DENIED = "DENIED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    SAFE_MODE = "SAFE_MODE"
    INTERVENED = "INTERVENED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class LaneBSignal:
    kind: LaneBSignalKind
    source: str
    target_ref: str
    expected_state: str
    detail: str
    op_key: str

    def fingerprint(self) -> str:
        canonical = _SEP.join(
            (
                str(self.kind),
                self.source,
                self.target_ref,
                self.expected_state,
                self.detail,
                self.op_key,
            )
        )
        return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class CrossLaneResult:
    outcome: CrossLaneOutcome
    source: str
    target_ref: str
    op_key: str
    detail: str
    intervention: InterventionResult | None = None
    safe_mode_session: SafeModeSession | None = None


class _BridgeLock(Protocol):
    def __enter__(self) -> bool: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class RPH3CrossLaneBridge:
    """Typed, fail-closed integration seam between CMP-WATCH and accepted Lane B."""

    receiver: WatchdogInterventionReceiver
    control: WatchdogControl
    task_reader: OrchestratorStateReader
    safe_mode: SafeMode
    audit_validator: AuditValidator
    clock: Clock
    _seen: dict[str, tuple[str, CrossLaneResult]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _lock: _BridgeLock = field(default_factory=Lock, init=False, repr=False, compare=False)

    def handle(self, signal: LaneBSignal) -> CrossLaneResult:
        with self._lock:
            invalid = self._validate(signal)
            if invalid is not None:
                return self._result(signal, CrossLaneOutcome.FAILED, invalid)
            fingerprint = signal.fingerprint()
            seen = self._seen.get(signal.op_key)
            if seen is not None:
                if seen[0] == fingerprint:
                    return seen[1]
                return self._result(
                    signal,
                    CrossLaneOutcome.FAILED,
                    "conflicting cross-lane message for existing op_key",
                )
            result = self._route(signal)
            self._seen[signal.op_key] = (fingerprint, result)
            return result

    def from_permission(self, decision: PermissionDecision, op_key: str) -> CrossLaneResult:
        if decision.decision is PermissionDecisionKind.ALLOW:
            kind = LaneBSignalKind.HEALTHY
        elif decision.decision is PermissionDecisionKind.REQUIRES_APPROVAL:
            kind = LaneBSignalKind.APPROVAL_REQUIRED
        else:
            kind = LaneBSignalKind.PERMISSION_DENIED
        return self.handle(
            self._signal(
                kind,
                "CMP-PERM",
                decision.request.task_id,
                decision.cause,
                op_key,
            )
        )

    def from_approval(self, record: ApprovalRecord, op_key: str) -> CrossLaneResult:
        now = self.clock.now_ts()
        if now >= record.expires_at:
            kind = LaneBSignalKind.APPROVAL_EXPIRED
            detail = "approval expired"
        elif record.state is ApprovalState.PENDING:
            kind = LaneBSignalKind.APPROVAL_REQUIRED
            detail = "operator approval required"
        elif record.state is ApprovalState.GRANTED:
            kind = LaneBSignalKind.HEALTHY
            detail = "approval granted and current"
        elif record.state is ApprovalState.CONSUMED:
            kind = LaneBSignalKind.APPROVAL_REPLAY
            detail = "approval already consumed; replay denied"
        else:
            kind = LaneBSignalKind.APPROVAL_DENIED
            detail = f"approval state {record.state} is not authoritative for use"
        return self.handle(self._signal(kind, "CMP-APPROVAL", record.task_id, detail, op_key))

    def from_tool_gateway(
        self, result: ToolResult | ToolDenial, target_ref: str, op_key: str
    ) -> CrossLaneResult:
        if isinstance(result, ToolDenial):
            kind = LaneBSignalKind.TOOL_GATEWAY_DENIED
            detail = f"{result.reason_code}: {result.message}"
        else:
            kind = LaneBSignalKind.HEALTHY
            detail = "tool result validated by CMP-TOOLGW"
        return self.handle(self._signal(kind, "CMP-TOOLGW", target_ref, detail, op_key))

    def from_fileop(self, error: FileOpError, target_ref: str, op_key: str) -> CrossLaneResult:
        return self.handle(
            self._signal(
                LaneBSignalKind.FILEOP_DENIED,
                "CMP-FILEOP",
                target_ref,
                f"{error.code}: {error.message}",
                op_key,
            )
        )

    def audit_health(self, target_ref: str, expected_state: str, op_key: str) -> CrossLaneResult:
        try:
            verdict = self.audit_validator.verify_chain()
        except Exception as exc:
            kind = LaneBSignalKind.AUDIT_BREAK
            detail = f"audit validator unavailable: {type(exc).__name__}"
        else:
            kind = LaneBSignalKind.HEALTHY if verdict.valid else LaneBSignalKind.AUDIT_BREAK
            detail = (
                "audit chain verified"
                if verdict.valid
                else f"audit chain break: {verdict.break_class}"
            )
        return self.handle(
            LaneBSignal(
                kind=kind,
                source="CMP-AUDITV",
                target_ref=target_ref,
                expected_state=expected_state,
                detail=detail,
                op_key=op_key,
            )
        )

    def dependency_failure(
        self,
        *,
        source: str,
        target_ref: str,
        expected_state: str,
        detail: str,
        op_key: str,
    ) -> CrossLaneResult:
        return self.handle(
            LaneBSignal(
                LaneBSignalKind.DEPENDENCY_FAILURE,
                source,
                target_ref,
                expected_state,
                detail,
                op_key,
            )
        )

    def request_safe_mode(self, *, target_ref: str, detail: str, op_key: str) -> CrossLaneResult:
        return self.handle(
            self._signal(
                LaneBSignalKind.SAFE_MODE_REQUIRED,
                "CMP-WATCH",
                target_ref,
                detail,
                op_key,
            )
        )

    def _route(self, signal: LaneBSignal) -> CrossLaneResult:
        if signal.kind is LaneBSignalKind.HEALTHY:
            return self._result(signal, CrossLaneOutcome.HEALTHY, signal.detail)
        if signal.kind is LaneBSignalKind.APPROVAL_REQUIRED:
            return self._result(signal, CrossLaneOutcome.APPROVAL_REQUIRED, signal.detail)
        if signal.kind in {
            LaneBSignalKind.PERMISSION_DENIED,
            LaneBSignalKind.APPROVAL_DENIED,
            LaneBSignalKind.APPROVAL_EXPIRED,
            LaneBSignalKind.APPROVAL_REPLAY,
            LaneBSignalKind.TOOL_GATEWAY_DENIED,
            LaneBSignalKind.FILEOP_DENIED,
        }:
            return self._result(signal, CrossLaneOutcome.DENIED, signal.detail)
        if signal.kind is LaneBSignalKind.SAFE_MODE_REQUIRED:
            session = self.safe_mode.enter(signal.detail)
            return CrossLaneResult(
                outcome=CrossLaneOutcome.SAFE_MODE,
                source=signal.source,
                target_ref=signal.target_ref,
                op_key=signal.op_key,
                detail=signal.detail,
                safe_mode_session=session,
            )

        command = (
            InterventionCommand.PAUSE_TASK
            if signal.kind is LaneBSignalKind.DEPENDENCY_FAILURE
            else InterventionCommand.CONTAIN_TASK
        )
        task = self.task_reader.get_task(signal.target_ref)
        if task is None:
            return self._result(
                signal, CrossLaneOutcome.FAILED, "cross-lane task target does not exist"
            )
        request = self.control.request(
            command,
            signal.target_ref,
            signal.expected_state,
            signal.detail,
            signal.op_key,
        )
        try:
            intervention = self.receiver.intervene(request)
        except WatchdogError as exc:
            return self._result(
                signal,
                CrossLaneOutcome.FAILED,
                f"WIR delivery failed closed: {exc.code}",
            )
        outcome = {
            InterventionOutcome.APPLIED: CrossLaneOutcome.INTERVENED,
            InterventionOutcome.REJECTED: CrossLaneOutcome.DENIED,
            InterventionOutcome.INERT: CrossLaneOutcome.FAILED,
            InterventionOutcome.FAILED: CrossLaneOutcome.FAILED,
        }[intervention.outcome]
        return CrossLaneResult(
            outcome=outcome,
            source=signal.source,
            target_ref=signal.target_ref,
            op_key=signal.op_key,
            detail=intervention.cause,
            intervention=intervention,
        )

    def _signal(
        self,
        kind: LaneBSignalKind,
        source: str,
        target_ref: str,
        detail: str,
        op_key: str,
    ) -> LaneBSignal:
        return LaneBSignal(
            kind,
            source,
            target_ref,
            task_state_hash(self.task_reader.get_task(target_ref)),
            detail,
            op_key,
        )

    @staticmethod
    def _validate(signal: LaneBSignal) -> str | None:
        if (
            not signal.op_key
            or len(signal.op_key) > 256
            or not signal.source
            or len(signal.source) > 128
            or not signal.target_ref
            or len(signal.target_ref) > 256
            or any(marker in signal.target_ref for marker in ("*", ",", "\n", "\x00"))
            or not signal.detail
            or len(signal.detail) > 512
        ):
            return "invalid or unbounded cross-lane message"
        return None

    @staticmethod
    def _result(signal: LaneBSignal, outcome: CrossLaneOutcome, detail: str) -> CrossLaneResult:
        return CrossLaneResult(
            outcome=outcome,
            source=signal.source,
            target_ref=signal.target_ref,
            op_key=signal.op_key,
            detail=detail,
        )


__all__ = [
    "CrossLaneOutcome",
    "CrossLaneResult",
    "LaneBSignal",
    "LaneBSignalKind",
    "RPH3CrossLaneBridge",
]
