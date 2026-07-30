"""Dependency-aware readiness and cancellation mechanics (PH-2, CMP-TASKENG).

`TaskScheduler.ready_tasks` is a pure function decoupled from PH-1's contract system: it accepts an
already-built dependency graph (as PH-1's `ReferenceResolver.resolve_dependency_graph` — reused, not
reimplemented — would supply once adapted at the call site) and the current state of every task, and
returns which tasks are ready, deterministically ordered.

`request_cancellation`/`finalize_cancellation` provide only the state-machine mechanics for
cancellation via `CMP-ORCH.apply_transition`; actually halting a running worker process is out of
scope until PH-3/PH-5, which will call these same primitives.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from factory.orchestrator.errors import OrchestratorError
from factory.orchestrator.models import StateTransitionEvent, TaskState
from factory.orchestrator.store.runtime_state import (
    OrchestratorStateReader,
    _OrchestratorStateWriter,
)


@dataclass(slots=True)
class TaskScheduler:
    def ready_tasks(
        self,
        dependency_graph: Mapping[str, frozenset[str]],
        states: Mapping[str, TaskState],
    ) -> tuple[str, ...]:
        ready = [
            task_id
            for task_id, deps in dependency_graph.items()
            if all(states.get(dep) is TaskState.COMPLETE for dep in deps)
        ]
        # Deterministic order: dependency-count ascending, then task ID ascending — never
        # insertion order, so results are reproducible run-to-run.
        ready.sort(key=lambda task_id: (len(dependency_graph[task_id]), task_id))
        return tuple(ready)


def request_cancellation(
    writer: _OrchestratorStateWriter,
    reader: OrchestratorStateReader,
    task_id: str,
    reason: str,
    actor: str,
) -> StateTransitionEvent:
    """Transition the task to STOPPING. Rejected (illegal transition) if already terminal."""
    record = reader.get_task(task_id)
    if record is None:
        raise OrchestratorError("TASK_NOT_FOUND", f"task {task_id} does not exist")
    return writer.apply_transition(
        task_id=task_id,
        expected_current_state=record.current_state,
        new_state=TaskState.STOPPING,
        cause=reason,
        actor=actor,
    )


def finalize_cancellation(
    writer: _OrchestratorStateWriter,
    reader: OrchestratorStateReader,
    task_id: str,
    actor: str,
) -> StateTransitionEvent:
    """Transition STOPPING -> CANCELLED, once the caller has confirmed the task halted."""
    record = reader.get_task(task_id)
    if record is None:
        raise OrchestratorError("TASK_NOT_FOUND", f"task {task_id} does not exist")
    return writer.apply_transition(
        task_id=task_id,
        expected_current_state=record.current_state,
        new_state=TaskState.CANCELLED,
        cause="cancellation_finalized",
        actor=actor,
    )


__all__ = ["TaskScheduler", "finalize_cancellation", "request_cancellation"]
