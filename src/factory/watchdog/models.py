"""Frozen public value types for CMP-WATCH and the internal WIR."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from factory.orchestrator.models import StateTransitionEvent, TaskRuntimeRecord, TaskState

_SEP = "\x1f"


class InterventionCommand(StrEnum):
    PAUSE_TASK = "PAUSE_TASK"
    CONTAIN_TASK = "CONTAIN_TASK"
    RESTART_SERVICE = "RESTART_SERVICE"
    RECONCILE_STATE = "RECONCILE_STATE"
    QUARANTINE_RESOURCE = "QUARANTINE_RESOURCE"
    RESTORE_APPROVED_STATE = "RESTORE_APPROVED_STATE"
    ACTIVATE_VERIFIED_SNAPSHOT = "ACTIVATE_VERIFIED_SNAPSHOT"


ALL_INTERVENTION_COMMANDS = frozenset(InterventionCommand)


class InterventionOutcome(StrEnum):
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"
    INERT = "INERT"
    FAILED = "FAILED"


class InterventionStatus(StrEnum):
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


class HealthState(StrEnum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    PAUSE = "PAUSE"
    CRITICAL_CONTAINMENT = "CRITICAL_CONTAINMENT"
    REDUCED_MONITORING = "REDUCED_MONITORING"


class HighRiskDecision(StrEnum):
    ALLOW = "ALLOW"
    BLOCK_NEW = "BLOCK_NEW"
    PAUSE_EXISTING = "PAUSE_EXISTING"


class DegradationRoute(StrEnum):
    CONTINUE = "CONTINUE"
    SAFE_MODE = "SAFE_MODE"
    QUARANTINE = "QUARANTINE"


@dataclass(frozen=True, slots=True)
class InterventionRequest:
    command: InterventionCommand | str
    target_ref: str
    expected_state: str
    reason: str
    requestor: str
    idempotency_key: str
    monotonic_ts: int
    auth_token: str

    def request_hash(self) -> str:
        command = str(self.command)
        canonical = _SEP.join(
            (
                command,
                self.target_ref,
                self.expected_state,
                self.reason,
                self.requestor,
                self.idempotency_key,
                str(self.monotonic_ts),
            )
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class InterventionResult:
    command: InterventionCommand | str
    target_ref: str
    idempotency_key: str
    outcome: InterventionOutcome
    audit_seq: int | None
    cause: str


@dataclass(frozen=True, slots=True)
class InterventionRecord:
    op_key: str
    operation_class: int
    target_ref: str
    requested_action: str
    status: InterventionStatus
    reconciliation_state: ReconciliationState
    request_hash: str
    expected_state: str
    desired_state: str | None
    result_outcome: InterventionOutcome | None
    result_cause: str | None
    audit_seq: int | None
    failure_code: str | None
    created_ts: int
    updated_ts: int
    completed_ts: int | None


@dataclass(frozen=True, slots=True)
class Heartbeat:
    identity: str
    sequence: int
    monotonic_ts: float
    auth_token: str


@dataclass(frozen=True, slots=True)
class SensorSample:
    monotonic_ts: float
    healthy: bool | None
    source: str


@dataclass(frozen=True, slots=True)
class FailureObservation:
    exception_type: str
    action_class: str
    target_ref: str
    stable_code: str
    process_id: int
    wall_clock_ts: int


class Clock(Protocol):
    def now_ts(self) -> int: ...
    def now_iso(self) -> str: ...
    def monotonic(self) -> float: ...


class AuthorityGate(Protocol):
    def authorize(self, request: InterventionRequest) -> bool: ...


class TaskReader(Protocol):
    def get_task(self, task_id: str) -> TaskRuntimeRecord | None: ...
    def get_events(self, task_id: str) -> tuple[StateTransitionEvent, ...]: ...


class TaskWriter(Protocol):
    def apply_transition(
        self,
        *,
        task_id: str,
        expected_current_state: TaskState | None,
        new_state: TaskState,
        cause: str,
        actor: str,
        linked_reference: str | None = None,
        idempotency_key: str | None = None,
    ) -> StateTransitionEvent: ...


class ServiceController(Protocol):
    def restart(self, service_id: str) -> bool: ...
    def state(self, service_id: str) -> str: ...


def task_state_hash(record: TaskRuntimeRecord | None) -> str:
    if record is None:
        return hashlib.sha256(b"missing").hexdigest()
    canonical = _SEP.join((record.task_id, str(record.current_state), str(record.sequence)))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "ALL_INTERVENTION_COMMANDS",
    "AuthorityGate",
    "Clock",
    "DegradationRoute",
    "FailureObservation",
    "HealthState",
    "Heartbeat",
    "HighRiskDecision",
    "InterventionCommand",
    "InterventionOutcome",
    "InterventionRecord",
    "InterventionRequest",
    "InterventionResult",
    "InterventionStatus",
    "ReconciliationState",
    "SensorSample",
    "ServiceController",
    "TaskReader",
    "TaskWriter",
    "task_state_hash",
]
