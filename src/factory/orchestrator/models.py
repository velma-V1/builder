"""Immutable models and enums for the Orchestrator (PH-2).

The state set and vocabulary are the authoritative 01L §3.1 / 01M §5 / 01F definitions.
These shapes are the frozen public interface for PH-2 (change = Change Contract, 01D §3.2).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum


class TaskState(StrEnum):
    """Authoritative task/workstream state set (01L §3.1).

    Phase 3B additive extension: ``PROMOTING`` and ``REJECTED`` were added to carry the
    explicitly-specified Phase 3B lifecycle (``AWAITING_APPROVAL -> PROMOTING -> COMPLETE``, with
    ``REJECTED`` as an explicit approval-denied terminal state) through this same authoritative
    state field, rather than introducing a parallel side-channel status. See
    ``state/transitions.py`` for the corresponding ``ALLOWED_TRANSITIONS`` additions.
    """

    QUEUED = "QUEUED"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    VERIFYING = "VERIFYING"
    PROMOTING = "PROMOTING"
    BLOCKED = "BLOCKED"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"
    STOPPING = "STOPPING"
    CANCELLED = "CANCELLED"
    COMPLETE = "COMPLETE"
    ROLLED_BACK = "ROLLED_BACK"
    REJECTED = "REJECTED"


TERMINAL_STATES: frozenset[TaskState] = frozenset(
    {TaskState.CANCELLED, TaskState.COMPLETE, TaskState.ROLLED_BACK, TaskState.REJECTED}
)


class ReconciliationOutcome(StrEnum):
    """The only outcomes a reconciled task may receive (01M §5)."""

    RESUMABLE = "RESUMABLE"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class LeaseResourceType(StrEnum):
    """Lease resource kinds meaningful before PH-4/PH-5 exist.

    Extending this set is a shared-contract change (01D §3.2) for a later phase.
    """

    TASK = "TASK"
    RESOURCE = "RESOURCE"


class MemoryRecordStatus(StrEnum):
    """Project-authority memory record status lifecycle (01F §2.6)."""

    PROPOSED = "PROPOSED"
    VERIFIED = "VERIFIED"
    SUPERSEDED = "SUPERSEDED"
    REFUTED = "REFUTED"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True, slots=True)
class StateTransitionEvent:
    task_id: str
    sequence: int
    prev_state: TaskState | None
    new_state: TaskState
    cause: str
    actor: str
    accepted: bool
    occurred_at: str
    linked_reference: str | None
    idempotency_key: str | None


@dataclass(frozen=True, slots=True)
class TaskRuntimeRecord:
    task_id: str
    project_id: str
    contract_version: int
    current_state: TaskState
    sequence: int
    updated_at: str
    # Distinct from project_id (01L): the workstream a task belongs to, if assigned. Never
    # inferred/aliased from project_id — only ever set explicitly via the writer (PH-2A).
    workstream_id: str | None = None


@dataclass(frozen=True, slots=True)
class TaskRequestRecord:
    """Human-submission metadata for a task (Phase 3A, CMP-ORCH-API).

    Distinct from ``TaskRuntimeRecord``: this is operator-provided intake data (what was asked
    for), never authoritative execution state (what's actually happening) — the two are joined
    by ``task_id`` but live in separate tables and are never conflated.
    """

    task_id: str
    project_ref: str
    workstream_id: str
    description: str
    priority: str
    model_preference: str | None
    expected_result: str | None
    submitted_by: str
    submitted_at: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class TaskSubmissionResult:
    """Result of submitting a task request (Phase 3A).

    ``created`` distinguishes a fresh submission from an idempotent replay (same
    ``idempotency_key`` submitted again returns the original ``task_id``/``state`` with
    ``created=False`` instead of creating a duplicate task).
    """

    task_id: str
    state: TaskState
    created: bool


@dataclass(frozen=True, slots=True)
class Lease:
    resource_type: LeaseResourceType
    resource_id: str
    owner_id: str
    fencing_token: int
    process_epoch: str
    acquired_at: str
    expires_at: str
    released: bool


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    record_id: str
    project_id: str
    memory_class: str  # fixed "PROJECT_AUTHORITY" in this phase
    status: MemoryRecordStatus
    source: str
    scope: str
    summary: str
    evidence_ref: str | None
    supersedes: str | None
    created_at: str


@dataclass(frozen=True, slots=True)
class ProcessEpoch:
    """A fresh identity generated once per Orchestrator process run.

    A lease acquired under a prior epoch is treated as stale at reconciliation regardless of
    its wall-clock expiry (a new process cannot trust an old process's in-flight bookkeeping).
    """

    value: str

    @classmethod
    def generate(cls) -> ProcessEpoch:
        return cls(value=uuid.uuid4().hex)
