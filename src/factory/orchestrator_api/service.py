"""``TaskOperatorService`` — Phase 3A write-path composition facade (CMP-ORCH-API).

Same shape already established by ``FileOpService``/``ToolGateway``/``SafeMode``: a frozen
dataclass holding the writer + reader, composing existing primitives in a fixed order. This is
the ONLY module in the orchestrator API allowed to hold the writer — mirrors
``StateIntegration``'s "sole holder of the writer" role in the Worker Engine.

No approval/promotion logic exists here (Phase 3A has none — nothing can legitimately be
approved before a real worker produces results, which doesn't happen until Phase 3B/3C).
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.orchestrator.models import (
    TERMINAL_STATES,
    TaskRequestRecord,
    TaskRuntimeRecord,
    TaskState,
    TaskSubmissionResult,
)
from factory.orchestrator.queue.scheduler import finalize_cancellation, request_cancellation
from factory.orchestrator.store.runtime_state import (
    OrchestratorStateReader,
    _OrchestratorStateWriter,
)
from factory.orchestrator_api.errors import OrchestratorApiError
from factory.orchestrator_api.lifecycle import Phase3BLifecycleService


@dataclass(frozen=True, slots=True)
class TaskDetail:
    """Joined view for the dashboard's detail panel: authoritative state + submission metadata.

    ``request`` is ``None`` only for tasks created before Phase 3A existed (no submission record
    was ever captured for them) — it is never fabricated to fill the gap.
    """

    task: TaskRuntimeRecord
    request: TaskRequestRecord | None


@dataclass(frozen=True, slots=True)
class TaskOperatorService:
    writer: _OrchestratorStateWriter
    reader: OrchestratorStateReader
    phase3b: Phase3BLifecycleService | None = None

    def submit(
        self,
        *,
        project_ref: str,
        workstream_id: str,
        description: str,
        priority: str,
        model_preference: str | None,
        expected_result: str | None,
        submitted_by: str,
        idempotency_key: str,
    ) -> TaskSubmissionResult:
        return self.writer.submit_task_request(
            project_ref=project_ref,
            workstream_id=workstream_id,
            description=description,
            priority=priority,
            model_preference=model_preference,
            expected_result=expected_result,
            submitted_by=submitted_by,
            idempotency_key=idempotency_key,
        )

    def get_detail(self, task_id: str) -> TaskDetail | None:
        task = self.reader.get_task(task_id)
        if task is None:
            return None
        return TaskDetail(task=task, request=self.reader.get_task_request(task_id))

    def cancel(self, task_id: str, *, actor: str, reason: str) -> TaskRuntimeRecord:
        """Cancel a task, walking whatever legal 01L §3.1 path reaches CANCELLED.

        ``QUEUED``'s only legal edge is ``PLANNING`` — so a never-yet-started task is walked
        ``QUEUED->PLANNING->STOPPING->CANCELLED`` rather than requiring a direct edge that
        doesn't exist in the frozen transition table. Every other cancellable state reuses the
        existing ``request_cancellation``/``finalize_cancellation`` primitives unchanged.
        """
        record = self.reader.get_task(task_id)
        if record is None:
            raise OrchestratorApiError("TASK_NOT_FOUND", f"task {task_id} does not exist")
        if record.current_state in TERMINAL_STATES:
            raise OrchestratorApiError(
                "ACTION_REJECTED",
                f"task {task_id} is already terminal ({record.current_state.value})",
            )

        if record.current_state is TaskState.QUEUED:
            pre_step = self.writer.apply_transition(
                task_id=task_id,
                expected_current_state=TaskState.QUEUED,
                new_state=TaskState.PLANNING,
                cause="pre_cancel_planning",
                actor=actor,
            )
            if not pre_step.accepted:
                raise OrchestratorApiError(
                    "ACTION_REJECTED",
                    f"task {task_id} could not be moved out of QUEUED to cancel",
                )

        stopping_event = request_cancellation(
            self.writer, self.reader, task_id, reason=reason, actor=actor
        )
        if not stopping_event.accepted:
            raise OrchestratorApiError(
                "ACTION_REJECTED", f"task {task_id} cannot be cancelled from its current state"
            )
        finalize_cancellation(self.writer, self.reader, task_id, actor=actor)

        updated = self.reader.get_task(task_id)
        if updated is None:
            raise OrchestratorApiError(
                "ORCHESTRATOR_UNAVAILABLE", f"task {task_id} disappeared after cancellation"
            )
        return updated
