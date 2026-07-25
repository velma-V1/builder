"""State integration: route execution results to the PH-2 writer (PH-3, CMP-WORKER, Task 3.3).

This is the ONLY place in the Worker Engine that holds an `_OrchestratorStateWriter` (R1
single-writer). Workers and every other PH-3 component reach authoritative task state exclusively
through this module — the writer is never handed to a worker process and is never re-exported from
`factory.workers` (threat T-01). Each finalize links to an idempotency key so a duplicated result
(e.g. a retried finalize after an ambiguous crash) dedups instead of double-transitioning.

Success path is RUNNING → VERIFYING, NOT RUNNING → COMPLETE: per the authoritative 01L §3.1 table a
worker cannot mark its own task COMPLETE — completion is gated by verification (a later phase). This
enforces "no model/worker certifies its own work".
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.orchestrator.models import StateTransitionEvent, TaskRuntimeRecord, TaskState
from factory.orchestrator.queue.scheduler import finalize_cancellation, request_cancellation
from factory.orchestrator.store.runtime_state import (
    OrchestratorStateReader,
    _OrchestratorStateWriter,
)
from factory.workers.errors import WorkerEngineError
from factory.workers.models import ExecutionResult


@dataclass(slots=True)
class StateIntegration:
    """Sole Worker-Engine holder of the authoritative writer. Routes results to state changes."""

    writer: _OrchestratorStateWriter
    reader: OrchestratorStateReader

    def start_execution(self, task_id: str, actor: str) -> StateTransitionEvent:
        """Advance a dispatched task to RUNNING (QUEUED→PLANNING→RUNNING as needed).

        Idempotent-ish: if already RUNNING, returns the current head via a no-op legal check failure
        guard. Only QUEUED/PLANNING are valid entry points; anything else is a programming error.
        """
        record = self._require(task_id)
        state = record.current_state
        if state is TaskState.RUNNING:
            raise WorkerEngineError("ALREADY_RUNNING", f"task {task_id} already RUNNING")
        if state is TaskState.QUEUED:
            self._apply(
                task_id, TaskState.QUEUED, TaskState.PLANNING, cause="dispatch", actor=actor
            )
            state = TaskState.PLANNING
        if state is not TaskState.PLANNING:
            raise WorkerEngineError(
                "INVALID_START_STATE", f"task {task_id} in {state}, cannot begin execution"
            )
        return self._apply(
            task_id, TaskState.PLANNING, TaskState.RUNNING, cause="worker_ready", actor=actor
        )

    def finalize(self, task_id: str, result: ExecutionResult, actor: str) -> StateTransitionEvent:
        """Apply a completed execution's outcome to task state via the single writer.

        - clean (exit 0, no failure)      → RUNNING → VERIFYING  (hand off to verification)
        - cancelled                       → RUNNING → STOPPING → CANCELLED
        - any other failure_cause         → RUNNING → FAILED

        The transition is stamped with an idempotency key derived from the result, so replaying the
        same finalize returns the already-recorded event instead of transitioning again.
        """
        record = self._require(task_id)
        current = record.current_state
        idem = self._idempotency_key(result)

        if result.failure_cause == "cancelled":
            return self._finalize_cancelled(task_id, current, actor)

        if result.failure_cause is None and result.exit_code == 0:
            return self._apply(
                task_id, current, TaskState.VERIFYING, cause="worker_success", actor=actor,
                idempotency_key=idem,
            )

        cause = result.failure_cause or "nonzero_exit"
        return self._apply(
            task_id, current, TaskState.FAILED, cause=cause, actor=actor, idempotency_key=idem
        )

    # ---- cancellation (reuses PH-2 primitives) -------------------------------------------

    def _finalize_cancelled(
        self, task_id: str, current: TaskState, actor: str
    ) -> StateTransitionEvent:
        if current is TaskState.STOPPING:
            return finalize_cancellation(self.writer, self.reader, task_id, actor)
        if current is TaskState.CANCELLED:
            raise WorkerEngineError("ALREADY_CANCELLED", f"task {task_id} already CANCELLED")
        # RUNNING/other non-terminal → STOPPING, then STOPPING → CANCELLED.
        request_cancellation(
            self.writer, self.reader, task_id, reason="worker_cancelled", actor=actor
        )
        return finalize_cancellation(self.writer, self.reader, task_id, actor)

    # ---- internals -----------------------------------------------------------------------

    @staticmethod
    def _idempotency_key(result: ExecutionResult) -> str:
        return f"{result.task_id}:{result.exit_code}:{result.output_hash}"

    def _require(self, task_id: str) -> TaskRuntimeRecord:
        record = self.reader.get_task(task_id)
        if record is None:
            raise WorkerEngineError("TASK_NOT_FOUND", f"task {task_id} does not exist")
        return record

    def _apply(
        self,
        task_id: str,
        expected: TaskState,
        new_state: TaskState,
        *,
        cause: str,
        actor: str,
        idempotency_key: str | None = None,
    ) -> StateTransitionEvent:
        event = self.writer.apply_transition(
            task_id=task_id,
            expected_current_state=expected,
            new_state=new_state,
            cause=cause,
            actor=actor,
            idempotency_key=idempotency_key,
        )
        if not event.accepted:
            raise WorkerEngineError(
                "STATE_TRANSITION_REJECTED",
                f"task {task_id}: {expected} → {new_state} rejected by the writer",
            )
        return event
