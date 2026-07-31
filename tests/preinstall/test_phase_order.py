"""Preinstall unit — phase-order enforcement PH-4 → PH-5 → PH-6."""

from __future__ import annotations

from factory.preinstall.phase_order import LivePhase, is_authorization_allowed, next_phase


def test_next_phase_progression() -> None:
    assert next_phase(frozenset()) is LivePhase.PH4
    assert next_phase(frozenset({LivePhase.PH4})) is LivePhase.PH5
    assert next_phase(frozenset({LivePhase.PH4, LivePhase.PH5})) is LivePhase.PH6
    assert next_phase(frozenset({LivePhase.PH4, LivePhase.PH5, LivePhase.PH6})) is None


def test_gap_is_not_skippable() -> None:
    # PH-6 complete but PH-5 not → the next eligible is still PH-5, never a skip.
    assert next_phase(frozenset({LivePhase.PH4, LivePhase.PH6})) is LivePhase.PH5


def test_authorization_blocks_out_of_order() -> None:
    ok, reason = is_authorization_allowed(LivePhase.PH5, frozenset())
    assert not ok and reason.startswith("BLOCKED_PRIOR_PHASES")
    assert "PH4" in reason


def test_authorization_allows_in_order() -> None:
    ok, reason = is_authorization_allowed(LivePhase.PH4, frozenset())
    assert ok and reason == "ELIGIBLE"
    ok2, _ = is_authorization_allowed(LivePhase.PH5, frozenset({LivePhase.PH4}))
    assert ok2


def test_already_complete_is_rejected() -> None:
    ok, reason = is_authorization_allowed(LivePhase.PH4, frozenset({LivePhase.PH4}))
    assert not ok and reason == "ALREADY_COMPLETE"
