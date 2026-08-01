"""Maps authoritative orchestrator runtime records to the frontend snapshot contract.

Mirrors ``factory.ui_studio.data_contracts.builder_task_snapshot_contract()`` and
``ui/src/queries/useTaskSnapshot.ts`` exactly: ``{task_id: string, state: string,
updated_at: number}``. ``updated_at`` is a **UTC Unix epoch in milliseconds**, as an
integer — documented explicitly here and on the TypeScript side so the unit is never
ambiguous between the two languages.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TypedDict

from factory.orchestrator.models import TaskRuntimeRecord

_UPDATED_AT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class TaskSnapshot(TypedDict):
    task_id: str
    state: str
    updated_at: int


def to_task_snapshot(record: TaskRuntimeRecord) -> TaskSnapshot:
    """Convert one authoritative ``TaskRuntimeRecord`` into the exact wire shape."""
    parsed = datetime.strptime(record.updated_at, _UPDATED_AT_FORMAT).replace(tzinfo=UTC)
    epoch_ms = int(parsed.timestamp() * 1000)
    return TaskSnapshot(
        task_id=record.task_id,
        state=record.current_state.value,
        updated_at=epoch_ms,
    )
