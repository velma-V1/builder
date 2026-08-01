"""Factory Orchestrator (PH-2) — deterministic control-plane state machine.

Exports only read-safe types. The transactional writer (`_OrchestratorStateWriter`) is added in
Task 2.2 and is intentionally NOT exported (R1: the Orchestrator is the sole authoritative writer).
"""

from factory.orchestrator.errors import OrchestratorError
from factory.orchestrator.models import (
    TERMINAL_STATES,
    Lease,
    LeaseResourceType,
    MemoryRecord,
    MemoryRecordStatus,
    ProcessEpoch,
    ReconciliationOutcome,
    StateTransitionEvent,
    TaskRequestRecord,
    TaskRuntimeRecord,
    TaskState,
    TaskSubmissionResult,
)
from factory.orchestrator.state.transitions import ALLOWED_TRANSITIONS, TransitionPolicy

__all__ = [
    "ALLOWED_TRANSITIONS",
    "TERMINAL_STATES",
    "Lease",
    "LeaseResourceType",
    "MemoryRecord",
    "MemoryRecordStatus",
    "OrchestratorError",
    "ProcessEpoch",
    "ReconciliationOutcome",
    "StateTransitionEvent",
    "TaskRequestRecord",
    "TaskRuntimeRecord",
    "TaskState",
    "TaskSubmissionResult",
    "TransitionPolicy",
]
