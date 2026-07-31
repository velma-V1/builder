"""Preinstall unit — rollback-plan completeness."""

from __future__ import annotations

from factory.preinstall.rollback import RollbackPlan, Step


def test_complete_plan_has_no_gaps() -> None:
    plan = RollbackPlan((
        Step("s1", "read state", mutating=False),
        Step("s2", "upgrade lib", mutating=True, rollback="downgrade lib", capture_before=True),
    ))
    assert plan.is_complete
    assert plan.incompleteness() == ()


def test_mutating_step_without_rollback_is_incomplete() -> None:
    plan = RollbackPlan((Step("s2", "upgrade", mutating=True, capture_before=True),))
    problems = plan.incompleteness()
    assert any("no rollback" in p for p in problems)
    assert not plan.is_complete


def test_mutating_step_without_capture_before_is_incomplete() -> None:
    plan = RollbackPlan((Step("s2", "upgrade", mutating=True, rollback="downgrade"),))
    assert any("before" in p for p in plan.incompleteness())


def test_non_mutating_steps_have_no_obligation() -> None:
    plan = RollbackPlan((Step("s1", "inspect", mutating=False),))
    assert plan.is_complete
