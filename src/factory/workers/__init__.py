"""Factory Worker Engine (PH-3, CMP-WORKER).

Manages worker-process lifecycle and task execution. Exports only read-safe types and the pool /
lifecycle surface. The PH-2 authoritative writer (`_OrchestratorStateWriter`) is NOT re-exported
here (R1): all state mutation stays routed through StateIntegration → the single writer.
"""

from factory.workers.errors import WorkerEngineError
from factory.workers.lifecycle import is_legal
from factory.workers.models import (
    TERMINAL_WORKER_STATES,
    ExecutionEvent,
    ExecutionEventType,
    ExecutionResult,
    WorkerState,
    WorkerStatus,
)
from factory.workers.pool import WorkerPool
from factory.workers.process import (
    ProcessHandle,
    ProcessSpawner,
    SubprocessHandle,
    SubprocessSpawner,
    WorkerProcess,
)

__all__ = [
    "TERMINAL_WORKER_STATES",
    "ExecutionEvent",
    "ExecutionEventType",
    "ExecutionResult",
    "ProcessHandle",
    "ProcessSpawner",
    "SubprocessHandle",
    "SubprocessSpawner",
    "WorkerEngineError",
    "WorkerPool",
    "WorkerProcess",
    "WorkerState",
    "WorkerStatus",
    "is_legal",
]
