"""Factory Worker Engine (PH-3, CMP-WORKER).

Manages worker-process lifecycle and task execution. Exports only read-safe types and the pool /
lifecycle surface. The PH-2 authoritative writer (`_OrchestratorStateWriter`) is NOT re-exported
here (R1): all state mutation stays routed through StateIntegration → the single writer.
"""

from factory.workers.dispatcher import Dispatcher, DispatchRecord
from factory.workers.errors import WorkerEngineError
from factory.workers.execution import CancelToken, RawWorkerEvent, TaskExecutor
from factory.workers.lease_coordinator import LeaseCoordinator
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
from factory.workers.state_integration import StateIntegration
from factory.workers.streaming import ExecutionStream, OutputAccumulator

__all__ = [
    "TERMINAL_WORKER_STATES",
    "CancelToken",
    "DispatchRecord",
    "Dispatcher",
    "ExecutionEvent",
    "ExecutionEventType",
    "ExecutionResult",
    "ExecutionStream",
    "LeaseCoordinator",
    "OutputAccumulator",
    "ProcessHandle",
    "ProcessSpawner",
    "RawWorkerEvent",
    "StateIntegration",
    "SubprocessHandle",
    "SubprocessSpawner",
    "TaskExecutor",
    "WorkerEngineError",
    "WorkerPool",
    "WorkerProcess",
    "WorkerState",
    "WorkerStatus",
    "is_legal",
]
