"""Rollback-plan modelling + completeness check (preinstall preparation).

Every mutating step in a future installer must carry an explicit rollback. This module models a plan
and validates its *completeness* — no mutating step may lack a rollback, and a rollback record must
be captured before the change. It performs no host actions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Step:
    step_id: str
    description: str
    mutating: bool
    rollback: str = ""
    capture_before: bool = False


@dataclass(frozen=True, slots=True)
class RollbackPlan:
    steps: tuple[Step, ...] = ()

    def incompleteness(self) -> tuple[str, ...]:
        """Return reasons the plan is incomplete. Empty ⇒ every mutating step is reversible.

        A mutating step must (a) declare a non-empty rollback and (b) capture rollback state before
        the change. Non-mutating steps have no such obligation.
        """
        problems: list[str] = []
        for step in self.steps:
            if not step.mutating:
                continue
            if not step.rollback.strip():
                problems.append(f"{step.step_id}: mutating step has no rollback")
            if not step.capture_before:
                problems.append(f"{step.step_id}: mutating step does not capture state beforehand")
        return tuple(problems)

    @property
    def is_complete(self) -> bool:
        return not self.incompleteness()
