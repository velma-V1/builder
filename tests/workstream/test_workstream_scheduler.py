"""PH-6 unit — priority/interruption scheduler + three-failure quarantine (``01D §3.5/§3.7``)."""

from __future__ import annotations

from factory.workstream.scheduler import (
    FailureCounter,
    InterruptOutcome,
    ResumeCategory,
    ResumeItem,
    WorkstreamScheduler,
    normalize_signature,
)


def _sig(root: str = "rc") -> str:
    return normalize_signature(
        component="c", operation="o", phase="p", error_code="E1", resource="r", root_cause=root
    )


def test_three_same_signature_failures_quarantine() -> None:
    fc = FailureCounter()
    assert fc.record("W1", _sig()) is False  # 1
    assert fc.record("W1", _sig()) is False  # 2
    assert fc.record("W1", _sig()) is True  # 3 -> quarantine
    assert fc.is_quarantined("W1")
    assert fc.count("W1") == 3


def test_different_signature_resets_sequence() -> None:
    fc = FailureCounter()
    fc.record("W1", _sig("a"))
    fc.record("W1", _sig("a"))
    fc.record("W1", _sig("b"))  # different root cause -> reset to 1
    assert fc.count("W1") == 1
    assert not fc.is_quarantined("W1")


def test_transient_failures_are_excluded() -> None:
    fc = FailureCounter()
    fc.record("W1", _sig())
    fc.record("W1", _sig(), transient=True)  # excluded; does not advance
    fc.record("W1", _sig())
    assert fc.count("W1") == 2
    assert not fc.is_quarantined("W1")


def test_reset_clears_state() -> None:
    fc = FailureCounter()
    fc.record("W1", _sig())
    fc.reset("W1")
    assert fc.count("W1") == 0


def test_interrupt_only_via_checkpointed_pause() -> None:
    s = WorkstreamScheduler()
    assert (
        s.interrupt(
            requester_priority=9,
            holder_priority=1,
            non_preemptible=False,
            checkpoint_within_deadline=True,
        )
        is InterruptOutcome.CHECKPOINTED_PAUSE
    )
    assert (
        s.interrupt(
            requester_priority=9,
            holder_priority=1,
            non_preemptible=False,
            checkpoint_within_deadline=False,
        )
        is InterruptOutcome.BLOCKED
    )
    assert (
        s.interrupt(
            requester_priority=9,
            holder_priority=1,
            non_preemptible=True,
            checkpoint_within_deadline=True,
        )
        is InterruptOutcome.NON_PREEMPTIBLE
    )
    assert (
        s.interrupt(
            requester_priority=1,
            holder_priority=5,
            non_preemptible=False,
            checkpoint_within_deadline=True,
        )
        is InterruptOutcome.NOT_HIGHER_PRIORITY
    )


def test_resume_order_follows_policy() -> None:
    s = WorkstreamScheduler()
    items = (
        ResumeItem("norm", ResumeCategory.NORMAL, priority=5, checkpoint_age=1, fifo_seq=1),
        ResumeItem("cont", ResumeCategory.CONTAINMENT, priority=1, checkpoint_age=0, fifo_seq=2),
        ResumeItem("crit", ResumeCategory.CRITICAL, priority=9, checkpoint_age=0, fifo_seq=3),
        ResumeItem("cp-old", ResumeCategory.CHECKPOINT, priority=5, checkpoint_age=10, fifo_seq=4),
        ResumeItem("cp-new", ResumeCategory.CHECKPOINT, priority=5, checkpoint_age=1, fifo_seq=5),
    )
    order = [i.lane_id for i in s.resume_order(items)]
    assert order == ["cont", "crit", "cp-old", "cp-new", "norm"]


def test_starvation_escalation() -> None:
    s = WorkstreamScheduler()
    assert s.starvation_priority(3, waiting_ticks=5) == 3
    assert s.starvation_priority(3, waiting_ticks=15) == 4
    assert not s.guaranteed_admission(10)
    assert s.guaranteed_admission(30)
