"""Real-time UI event contract: sequencing, replay, reconnect, reconciliation, restart — no
connection is ever opened by any of this."""

from __future__ import annotations

import pytest

from factory.ui_studio.errors import UIStudioError, UIStudioErrorCode
from factory.ui_studio.models import RealtimeChannelContract
from factory.ui_studio.realtime_contracts import (
    OptimisticCommand,
    RealtimeEvent,
    ReplayBuffer,
    compute_staleness,
    deny_client_invented_state,
    issue_reconnect_cursor,
    plan_restart_reconstruction,
    reconcile_snapshot,
    validate_realtime_stream,
)


def _event(seq: int, event_type: str = "PROGRESS", **payload: str) -> RealtimeEvent:
    return RealtimeEvent("workstream:t1", seq, event_type, occurred_at=1000 + seq, payload=payload)


def _contract(replay_window: int = 5) -> RealtimeChannelContract:
    return RealtimeChannelContract(
        "workstream:t1", event_types=("PROGRESS",), replay_window=replay_window
    )


# --- sequencing / dedup / ordering / gaps ----------------------------------------------------


def test_monotonic_stream_is_accepted_in_full() -> None:
    events = tuple(_event(i) for i in range(4))
    stream = validate_realtime_stream(events)
    assert len(stream.accepted) == 4


def test_exact_duplicate_event_is_idempotent() -> None:
    e = _event(0)
    stream = validate_realtime_stream((e, e))
    assert len(stream.accepted) == 1
    assert stream.duplicates_skipped == 1


def test_conflicting_duplicate_is_rejected() -> None:
    with pytest.raises(UIStudioError) as excinfo:
        validate_realtime_stream((_event(0), _event(0, detail="different")))
    assert excinfo.value.code is UIStudioErrorCode.DUPLICATE_EVENT


def test_out_of_order_event_is_rejected() -> None:
    with pytest.raises(UIStudioError) as excinfo:
        validate_realtime_stream((_event(0), _event(2), _event(1)))
    assert excinfo.value.code is UIStudioErrorCode.OUT_OF_ORDER_EVENT


def test_missing_sequence_gap_is_rejected() -> None:
    with pytest.raises(UIStudioError) as excinfo:
        validate_realtime_stream((_event(0), _event(2)))
    assert excinfo.value.code is UIStudioErrorCode.MISSING_SEQUENCE


def test_client_invented_authoritative_state_is_denied() -> None:
    bad = _event(0, client_asserted_authoritative="true")
    with pytest.raises(UIStudioError) as excinfo:
        deny_client_invented_state(bad)
    assert excinfo.value.code is UIStudioErrorCode.CLIENT_INVENTED_STATE


def test_ordinary_event_passes_client_invented_state_check() -> None:
    deny_client_invented_state(_event(0, detail="fine"))  # must not raise


# --- bounded replay + reconnect cursor --------------------------------------------------------


def test_replay_buffer_retains_at_most_the_window() -> None:
    buffer = ReplayBuffer(_contract(replay_window=3))
    for i in range(5):
        buffer.append(_event(i))
    assert buffer.oldest_available_sequence == 2  # events 0,1 evicted


def test_replay_buffer_returns_events_since_cursor() -> None:
    buffer = ReplayBuffer(_contract(replay_window=5))
    for i in range(4):
        buffer.append(_event(i))
    replayed = buffer.events_since(1)
    assert [e.sequence for e in replayed] == [2, 3]


def test_replay_beyond_the_retained_window_is_denied() -> None:
    buffer = ReplayBuffer(_contract(replay_window=2))
    for i in range(5):
        buffer.append(_event(i))
    with pytest.raises(UIStudioError) as excinfo:
        buffer.events_since(0)
    assert excinfo.value.code is UIStudioErrorCode.REPLAY_WINDOW_EXCEEDED


def test_reconnect_cursor_carries_last_applied_sequence() -> None:
    cursor = issue_reconnect_cursor("workstream:t1", last_applied_sequence=7, now=1000)
    assert cursor.last_applied_sequence == 7


# --- snapshot reconciliation --------------------------------------------------------------------


def test_reconciliation_is_noop_when_already_current() -> None:
    buffer = ReplayBuffer(_contract())
    result = reconcile_snapshot(
        "workstream:t1",
        local_last_sequence=5,
        backend_snapshot_sequence=5,
        buffer=buffer,
    )
    assert result.reconciled
    assert not result.full_snapshot_required


def test_reconciliation_via_replay_when_gap_is_covered() -> None:
    buffer = ReplayBuffer(_contract(replay_window=10))
    for i in range(6):
        buffer.append(_event(i))
    result = reconcile_snapshot(
        "workstream:t1",
        local_last_sequence=2,
        backend_snapshot_sequence=5,
        buffer=buffer,
    )
    assert result.reconciled
    assert not result.full_snapshot_required


def test_reconciliation_requires_full_snapshot_when_gap_exceeds_window() -> None:
    buffer = ReplayBuffer(_contract(replay_window=2))
    for i in range(10):
        buffer.append(_event(i))
    result = reconcile_snapshot(
        "workstream:t1",
        local_last_sequence=0,
        backend_snapshot_sequence=9,
        buffer=buffer,
    )
    assert not result.reconciled
    assert result.full_snapshot_required


# --- stale-state indicators ----------------------------------------------------------------------


def test_stale_indicator_flags_old_state() -> None:
    indicator = compute_staleness("workstream:t1", last_event_at=1000, now=1100, stale_after_s=30)
    assert indicator.stale
    assert indicator.age_s == 100


def test_stale_indicator_does_not_flag_fresh_state() -> None:
    indicator = compute_staleness("workstream:t1", last_event_at=1000, now=1010, stale_after_s=30)
    assert not indicator.stale


# --- pending optimistic commands ------------------------------------------------------------------


def test_optimistic_command_starts_pending() -> None:
    command = OptimisticCommand("cmd-1", submitted_at=1000)
    assert command.is_pending
    assert command.confirmed_sequence is None


def test_optimistic_command_confirm_is_immutable_and_returns_new_state() -> None:
    command = OptimisticCommand("cmd-1", submitted_at=1000)
    confirmed = command.confirm(sequence=5)
    assert command.is_pending  # original untouched
    assert not confirmed.is_pending
    assert confirmed.confirmed_sequence == 5


# --- restart reconstruction -----------------------------------------------------------------------


def test_restart_with_no_persisted_cursor_requires_full_snapshot() -> None:
    buffer = ReplayBuffer(_contract())
    plan = plan_restart_reconstruction("workstream:t1", persisted_last_sequence=None, buffer=buffer)
    assert plan.requires_full_snapshot
    assert not plan.can_replay


def test_restart_within_replay_window_resumes_via_replay() -> None:
    buffer = ReplayBuffer(_contract(replay_window=10))
    for i in range(5):
        buffer.append(_event(i))
    plan = plan_restart_reconstruction("workstream:t1", persisted_last_sequence=2, buffer=buffer)
    assert plan.can_replay
    assert plan.resume_from_sequence == 3
    assert not plan.requires_full_snapshot


def test_restart_beyond_replay_window_requires_full_snapshot() -> None:
    buffer = ReplayBuffer(_contract(replay_window=2))
    for i in range(10):
        buffer.append(_event(i))
    plan = plan_restart_reconstruction("workstream:t1", persisted_last_sequence=0, buffer=buffer)
    assert plan.requires_full_snapshot
    assert not plan.can_replay
