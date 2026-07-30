"""Quarantine registry for tasks needing manual review (PH-3, CMP-WORKER, Task 3.4).

An append-only, in-memory record of tasks the Worker Engine could not safely recover automatically
(state/journal mismatch, or an unrecoverable transition). It carries NO authoritative task state —
it is the operator-facing "needs manual intervention" signal that accompanies a QUARANTINED task.
Append-only mirrors the journal discipline: entries are never edited or removed in place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class QuarantineEntry:
    task_id: str
    reason: str
    recorded_at: str


@dataclass(slots=True)
class QuarantineRegistry:
    """Append-only list of quarantined tasks. Deduplicates by (task_id, reason)."""

    _entries: list[QuarantineEntry] = field(default_factory=list)

    def record(self, task_id: str, reason: str) -> QuarantineEntry:
        for existing in self._entries:
            if existing.task_id == task_id and existing.reason == reason:
                return existing
        entry = QuarantineEntry(
            task_id=task_id,
            reason=reason,
            recorded_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        self._entries.append(entry)
        return entry

    @property
    def entries(self) -> tuple[QuarantineEntry, ...]:
        return tuple(self._entries)

    def is_quarantined(self, task_id: str) -> bool:
        return any(e.task_id == task_id for e in self._entries)
