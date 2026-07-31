"""Dry-run-by-default installer framework (STEP 4 — future installer hardening).

Any future *mutating* installer inherits these guardrails so a mutation can never happen by
accident:

* **dry-run by default** — nothing mutates unless ``apply=True`` is passed explicitly;
* **plan printed before apply** — the redacted plan is always produced first;
* **OS/version validated** and **prerequisites checked** — a failed check stops before mutation;
* **rollback captured before change** — a mutating step will not run without a recorded rollback;
* **no silent/optional install** — only declared steps run, only in apply mode;
* **no security weakening** — a step that would weaken security is refused unless allowed.

The framework itself performs **no host action**: each step's mutation is a caller-supplied callable
that is invoked only under all the guards above. In this repository no real host mutation is wired —
`DO_NOT_RUN_ON_HOST`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from factory.livegate.redaction import redact_text


class StepOutcome(StrEnum):
    PLANNED = "PLANNED"
    APPLIED = "APPLIED"
    BLOCKED = "BLOCKED"
    SKIPPED_DRY_RUN = "SKIPPED_DRY_RUN"


def _always_ok() -> tuple[bool, str]:
    return (True, "ok")


def _noop() -> None:
    return None


@dataclass(frozen=True, slots=True)
class InstallStep:
    step_id: str
    description: str
    mutating: bool
    rollback: str = ""
    weakens_security: bool = False
    #: Returns ``(ok, reason)``. A failed validation stops the run before this step mutates.
    validate: Callable[[], tuple[bool, str]] = _always_ok
    #: The mutation, invoked only in apply mode under all guards. Default is a no-op.
    action: Callable[[], None] = _noop


@dataclass(frozen=True, slots=True)
class StepResult:
    step_id: str
    outcome: StepOutcome
    detail: str


@dataclass(frozen=True, slots=True)
class InstallReport:
    installer: str
    applied: bool
    results: tuple[StepResult, ...] = field(default_factory=tuple)

    @property
    def mutated(self) -> bool:
        return any(r.outcome is StepOutcome.APPLIED for r in self.results)

    @property
    def blocked(self) -> tuple[StepResult, ...]:
        return tuple(r for r in self.results if r.outcome is StepOutcome.BLOCKED)


class Installer:
    """A planned, guarded installer. Construct with steps; ``run()`` is dry-run unless ``apply``."""

    __slots__ = ("_allow_security_weakening", "_name", "_os_ok", "_steps")

    def __init__(
        self,
        name: str,
        steps: tuple[InstallStep, ...],
        *,
        os_ok: bool = True,
        allow_security_weakening: bool = False,
    ) -> None:
        self._name = name
        self._steps = steps
        self._os_ok = os_ok
        self._allow_security_weakening = allow_security_weakening

    def format_plan(self) -> str:
        """Return the redacted, human-readable plan (always produced before any apply)."""
        lines = [f"INSTALL PLAN: {self._name} (dry-run unless --apply)"]
        for step in self._steps:
            tag = "MUTATING" if step.mutating else "read-only"
            lines.append(f"  [{tag}] {step.step_id}: {step.description}")
            if step.mutating:
                lines.append(f"      rollback: {step.rollback or '(MISSING)'}")
        return redact_text("\n".join(lines))

    def run(
        self,
        *,
        apply: bool = False,
        rollback_recorder: Callable[[InstallStep], bool] | None = None,
    ) -> InstallReport:
        """Execute the plan. Dry-run (default) mutates nothing.

        In apply mode each mutating step runs only if: OS is ok, its ``validate()`` passes, it does
        not weaken security (unless explicitly allowed), it declares a rollback, and the
        ``rollback_recorder`` records the rollback state first. Any failure blocks that step; later
        steps still report but a blocked mutating step short-circuits nothing already applied.
        """
        results: list[StepResult] = []
        for step in self._steps:
            if not step.mutating:
                results.append(StepResult(step.step_id, StepOutcome.PLANNED, "read-only step"))
                continue
            if not apply:
                results.append(
                    StepResult(step.step_id, StepOutcome.SKIPPED_DRY_RUN, "dry-run: not applied")
                )
                continue
            blocked = self._blocking_reason(step, rollback_recorder)
            if blocked is not None:
                results.append(StepResult(step.step_id, StepOutcome.BLOCKED, blocked))
                continue
            step.action()
            results.append(StepResult(step.step_id, StepOutcome.APPLIED, "applied"))
        return InstallReport(self._name, apply, tuple(results))

    def _blocking_reason(
        self, step: InstallStep, rollback_recorder: Callable[[InstallStep], bool] | None
    ) -> str | None:
        if not self._os_ok:
            return "OS_VALIDATION_FAILED"
        if step.weakens_security and not self._allow_security_weakening:
            return "SECURITY_WEAKENING_REFUSED"
        if not step.rollback.strip():
            return "NO_ROLLBACK_DECLARED"
        ok, reason = step.validate()
        if not ok:
            return f"PREREQUISITE_FAILED:{reason}"
        if rollback_recorder is None or not rollback_recorder(step):
            return "ROLLBACK_NOT_RECORDED"
        return None
