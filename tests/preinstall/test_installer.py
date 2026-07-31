"""Preinstall unit — dry-run-by-default installer framework (no host mutation)."""

from __future__ import annotations

from factory.preinstall.installer import Installer, InstallStep, StepOutcome


class _Spy:
    def __init__(self) -> None:
        self.calls = 0

    def action(self) -> None:
        self.calls += 1


def _mutating_step(spy: _Spy, **over: object) -> InstallStep:
    base: dict[str, object] = dict(
        step_id="upgrade", description="upgrade sqlite", mutating=True,
        rollback="downgrade", action=spy.action,
    )
    base.update(over)
    return InstallStep(**base)  # type: ignore[arg-type]


def test_default_run_is_dry_run_and_mutates_nothing() -> None:
    spy = _Spy()
    report = Installer("x", (_mutating_step(spy),)).run()   # no apply flag
    assert not report.applied
    assert not report.mutated
    assert spy.calls == 0
    assert report.results[0].outcome is StepOutcome.SKIPPED_DRY_RUN


def test_plan_is_rendered_and_flags_missing_rollback() -> None:
    spy = _Spy()
    plan = Installer("x", (_mutating_step(spy, rollback=""),)).format_plan()
    assert "dry-run unless --apply" in plan
    assert "(MISSING)" in plan


def test_apply_runs_only_under_all_guards() -> None:
    spy = _Spy()
    report = Installer("x", (_mutating_step(spy),)).run(
        apply=True, rollback_recorder=lambda _s: True
    )
    assert report.mutated and spy.calls == 1
    assert report.results[0].outcome is StepOutcome.APPLIED


def test_apply_blocked_without_rollback_record() -> None:
    spy = _Spy()
    report = Installer("x", (_mutating_step(spy),)).run(apply=True, rollback_recorder=None)
    assert spy.calls == 0
    assert report.blocked[0].detail == "ROLLBACK_NOT_RECORDED"


def test_apply_blocked_on_failed_prerequisite() -> None:
    spy = _Spy()
    step = _mutating_step(spy, validate=lambda: (False, "sqlite below floor"))
    report = Installer("x", (step,)).run(apply=True, rollback_recorder=lambda _s: True)
    assert spy.calls == 0
    assert report.blocked[0].detail.startswith("PREREQUISITE_FAILED")


def test_apply_blocked_on_os_mismatch() -> None:
    spy = _Spy()
    report = Installer("x", (_mutating_step(spy),), os_ok=False).run(
        apply=True, rollback_recorder=lambda _s: True
    )
    assert spy.calls == 0
    assert report.blocked[0].detail == "OS_VALIDATION_FAILED"


def test_security_weakening_refused_by_default() -> None:
    spy = _Spy()
    step = _mutating_step(spy, weakens_security=True)
    report = Installer("x", (step,)).run(apply=True, rollback_recorder=lambda _s: True)
    assert spy.calls == 0
    assert report.blocked[0].detail == "SECURITY_WEAKENING_REFUSED"
