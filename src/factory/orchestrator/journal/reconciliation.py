"""Startup reconciliation over the append-only journal (PH-2, CMP-JOURNAL).

The append-only ``task_state_events`` table IS the durable journal (written inside the same atomic
transaction as each state change), so a transition is never reported before it is durably committed.
At startup, each task's state is reconstructed by folding its accepted events in order; a stored
state that disagrees with the replayed history is corruption, not a resumable task (→ QUARANTINED).
Consistent tasks are mapped to exactly one 01M §5 outcome, honoring "no blind task resume"
(01M §11): this phase has no worker/Watchdog layer to prove a running task is safe to resume, so
non-terminal states reconcile to BLOCKED (PH-3 performs the fuller reconciliation).

Scope limit (recorded known limitation): PH-2 has no containers, model workers, or worktrees, so
reconciliation covers task/journal consistency only — not the full 01M §20 resource list.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from factory.orchestrator.models import ReconciliationOutcome, TaskState
from factory.orchestrator.store.runtime_state import OrchestratorStateReader

# Verbatim from recovery-journal-spec.md "Reconciliation mapping" (applied only when replay is
# consistent; a replay mismatch overrides to QUARANTINED).
_RECONCILIATION_MAP: Mapping[TaskState, ReconciliationOutcome] = {
    TaskState.QUEUED: ReconciliationOutcome.RESUMABLE,
    TaskState.PLANNING: ReconciliationOutcome.BLOCKED,
    TaskState.RUNNING: ReconciliationOutcome.BLOCKED,
    TaskState.AWAITING_APPROVAL: ReconciliationOutcome.BLOCKED,
    TaskState.VERIFYING: ReconciliationOutcome.BLOCKED,
    TaskState.PAUSED: ReconciliationOutcome.BLOCKED,
    TaskState.STOPPING: ReconciliationOutcome.BLOCKED,
    TaskState.QUARANTINED: ReconciliationOutcome.BLOCKED,
    TaskState.BLOCKED: ReconciliationOutcome.BLOCKED,
    TaskState.FAILED: ReconciliationOutcome.FAILED,
    TaskState.CANCELLED: ReconciliationOutcome.CANCELLED,
    TaskState.COMPLETE: ReconciliationOutcome.COMPLETED,
    TaskState.ROLLED_BACK: ReconciliationOutcome.COMPLETED,
}


def _replay_state(reader: OrchestratorStateReader, task_id: str) -> TaskState | None:
    """Fold the accepted events for a task, in order, to reconstruct its authoritative state."""
    replayed: TaskState | None = None
    for event in reader.get_events(task_id):
        if event.accepted:
            replayed = event.new_state
    return replayed


def reconcile_startup(
    reader: OrchestratorStateReader, task_ids: Sequence[str]
) -> Mapping[str, ReconciliationOutcome]:
    """Assign exactly one ReconciliationOutcome to each task; never silently resume.

    An unknown task, or one whose stored ``current_state`` disagrees with its replayed
    accepted-event history, fails closed to QUARANTINED. A consistent task maps by the table.
    """
    result: dict[str, ReconciliationOutcome] = {}
    for task_id in task_ids:
        record = reader.get_task(task_id)
        if record is None:
            result[task_id] = ReconciliationOutcome.QUARANTINED
            continue
        replayed = _replay_state(reader, task_id)
        if replayed != record.current_state:
            result[task_id] = ReconciliationOutcome.QUARANTINED
        else:
            result[task_id] = _RECONCILIATION_MAP[record.current_state]
    return result


__all__ = ["reconcile_startup"]
