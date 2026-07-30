"""Failure recovery + startup reconciliation application (PH-3, CMP-WORKER, Task 3.4).

PH-2's ``reconcile_startup`` CLASSIFIES each task (01M §5) but applies nothing. This module APPLIES
recovery, honoring R3 "no blind resume": an in-flight task from a prior process epoch reconciles to
BLOCKED and is transitioned there — it is never silently returned to RUNNING. Crash-in-flight fails
the task; a state/journal mismatch quarantines it for manual review. All state changes flow through
StateIntegration (the single-writer holder), so the writer stays confined (R1).

`RetryPolicy` bounds automatic retries with deterministic exponential backoff; once exhausted, a
task is failed rather than retried forever (spec §State Writer Contention Recovery).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from factory.orchestrator.journal.reconciliation import reconcile_startup
from factory.orchestrator.models import ReconciliationOutcome, TaskState
from factory.workers.errors import WorkerEngineError
from factory.workers.models import ExecutionResult
from factory.workers.pool import WorkerPool
from factory.workers.quarantine import QuarantineRegistry
from factory.workers.state_integration import StateIntegration

# States from which BLOCKED is a legal transition (01L §3.1) — the "block for review" targets.
_BLOCKABLE: frozenset[TaskState] = frozenset(
    {
        TaskState.PLANNING,
        TaskState.RUNNING,
        TaskState.AWAITING_APPROVAL,
        TaskState.VERIFYING,
        TaskState.PAUSED,
        TaskState.QUARANTINED,
    }
)


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Deterministic bounded retry. Attempts are 1-indexed; backoff is base·2^(attempt-1)."""

    max_attempts: int = 3
    base_delay_seconds: float = 1.0

    def backoff_for(self, attempt: int) -> float:
        if attempt < 1:
            raise WorkerEngineError("RETRY_ATTEMPT_INVALID", f"attempt must be >= 1, got {attempt}")
        multiplier: int = 2 ** (attempt - 1)
        return self.base_delay_seconds * multiplier

    def is_exhausted(self, attempt: int) -> bool:
        return attempt > self.max_attempts


@dataclass(slots=True)
class WorkerRecovery:
    """Recovers tasks whose workers crashed, and fails/reclaims their pool slots."""

    pool: WorkerPool
    integration: StateIntegration

    def recover_crashed(self, actor: str = "worker-recovery") -> tuple[str, ...]:
        """Detect crashed workers, fail their bound tasks (heartbeat_loss), reclaim the slots.

        Returns the task-ids failed. A crashed slot with no bound task is reclaimed silently.
        """
        failed: list[str] = []
        for worker_id in self.pool.poll_health():
            status = self.pool.get_worker_status(worker_id)
            if status.task_id is not None:
                self.integration.fail_crashed(status.task_id, actor=actor)
                failed.append(status.task_id)
            self.pool.reclaim(worker_id)
        return tuple(failed)


@dataclass(slots=True)
class StartupRecovery:
    """Applies startup reconciliation outcomes to task state (R3), quarantining corruption."""

    integration: StateIntegration
    quarantine: QuarantineRegistry

    def recover(
        self, task_ids: Sequence[str], actor: str = "startup-recovery"
    ) -> Mapping[str, ReconciliationOutcome]:
        """Reconcile then APPLY: BLOCKED-classified in-flight tasks → BLOCKED (no blind resume);
        STOPPING → CANCELLED (safe completion of an interrupted cancel); mismatch → QUARANTINED.

        Returns the classification map (from PH-2) so callers can see every task's outcome.
        """
        outcomes = reconcile_startup(self.integration.reader, task_ids)
        for task_id, outcome in outcomes.items():
            self._apply_outcome(task_id, outcome, actor)
        return outcomes

    def _apply_outcome(
        self, task_id: str, outcome: ReconciliationOutcome, actor: str
    ) -> None:
        record = self.integration.reader.get_task(task_id)
        if record is None:
            self.quarantine.record(task_id, "unknown_task_at_reconcile")
            return
        current = record.current_state

        if outcome is ReconciliationOutcome.QUARANTINED:
            self.quarantine.record(task_id, "state_replay_mismatch")
            if current in (TaskState.RUNNING, TaskState.VERIFYING):
                self.integration.quarantine(task_id, actor=actor)
            return

        if outcome is ReconciliationOutcome.BLOCKED:
            if current is TaskState.STOPPING:
                # an interrupted cancellation is safe to finish, not to resume.
                self.integration.finalize(
                    task_id,
                    _crash_result(task_id, cause="cancelled"),
                    actor=actor,
                )
            elif current in _BLOCKABLE:
                self.integration.block_for_review(task_id, actor=actor)
            elif current is not TaskState.BLOCKED:
                # classified BLOCKED but no legal path from here → needs manual review.
                self.quarantine.record(task_id, f"unblockable_from_{current}")
        # RESUMABLE (QUEUED) / FAILED / CANCELLED / COMPLETED are already correct: no-op.


def _crash_result(task_id: str, cause: str) -> ExecutionResult:
    return ExecutionResult(
        task_id=task_id,
        exit_code=None,
        output_hash="",
        events_captured=0,
        truncated=False,
        failure_cause=cause,
    )
