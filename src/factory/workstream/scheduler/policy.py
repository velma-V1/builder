"""Priority / interruption / resume policy (``01D §3.5/§6.14-15/§6.26``).

Urgent work interrupts lower-priority work only through a *verified checkpointed pause*, never
abrupt destructive termination (except immediate containment, which is out of scope here). A lane
that cannot checkpoint within its deadline moves to BLOCKED rather than being unsafely evicted.
Resume order and
starvation escalation follow the versioned scheduler policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

# Versioned launch defaults (``01D §3.5``), expressed in abstract ticks for deterministic tests.
CHECKPOINT_DEADLINE_TICKS = 5
STARVATION_BUMP_TICKS = 15
STARVATION_ADMIT_TICKS = 30


class InterruptOutcome(StrEnum):
    CHECKPOINTED_PAUSE = "CHECKPOINTED_PAUSE"
    BLOCKED = "BLOCKED"
    NON_PREEMPTIBLE = "NON_PREEMPTIBLE"
    NOT_HIGHER_PRIORITY = "NOT_HIGHER_PRIORITY"


class ResumeCategory(StrEnum):
    CONTAINMENT = "CONTAINMENT"
    RECOVERY = "RECOVERY"
    CRITICAL = "CRITICAL"
    CHECKPOINT = "CHECKPOINT"
    NORMAL = "NORMAL"


_RESUME_RANK = {
    ResumeCategory.CONTAINMENT: 0,
    ResumeCategory.RECOVERY: 1,
    ResumeCategory.CRITICAL: 2,
    ResumeCategory.CHECKPOINT: 3,
    ResumeCategory.NORMAL: 4,
}


@dataclass(frozen=True, slots=True)
class ResumeItem:
    lane_id: str
    category: ResumeCategory
    priority: int
    checkpoint_age: int
    fifo_seq: int


class WorkstreamScheduler:
    """Deterministic priority/interruption/resume decisions."""

    def interrupt(
        self,
        *,
        requester_priority: int,
        holder_priority: int,
        non_preemptible: bool,
        checkpoint_within_deadline: bool,
    ) -> InterruptOutcome:
        if non_preemptible:
            return InterruptOutcome.NON_PREEMPTIBLE
        if requester_priority <= holder_priority:
            return InterruptOutcome.NOT_HIGHER_PRIORITY
        if checkpoint_within_deadline:
            return InterruptOutcome.CHECKPOINTED_PAUSE
        # No verified checkpoint in time -> BLOCKED, never unsafe eviction (``§6.14``).
        return InterruptOutcome.BLOCKED

    def resume_order(self, items: tuple[ResumeItem, ...]) -> tuple[ResumeItem, ...]:
        """Order per ``01D §3.5``: containment/recovery, then higher priority, oldest checkpoint,
        then FIFO."""
        return tuple(
            sorted(
                items,
                key=lambda i: (
                    _RESUME_RANK[i.category],
                    -i.priority,
                    -i.checkpoint_age,
                    i.fifo_seq,
                ),
            )
        )

    def starvation_priority(self, base_priority: int, waiting_ticks: int) -> int:
        """One priority increase after the starvation threshold (``§3.5``)."""
        return base_priority + 1 if waiting_ticks >= STARVATION_BUMP_TICKS else base_priority

    def guaranteed_admission(self, waiting_ticks: int) -> bool:
        return waiting_ticks >= STARVATION_ADMIT_TICKS
