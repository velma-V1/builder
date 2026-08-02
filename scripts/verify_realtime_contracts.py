#!/usr/bin/env python3
"""Verification suite for the real-time UI event contract layer (deterministic; no connection).

Confirms, by direct functional exercise rather than inspection alone, that every required guarantee
actually holds: monotonic sequencing, idempotent duplicates, out-of-order rejection, gap detection,
bounded replay, reconnect cursors, snapshot reconciliation, stale-state indicators, pending
optimistic commands, restart reconstruction, and no client-invented authoritative state. Opens no
WebSocket/SSE connection. Not a phase-promotion gate.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

sys.path.insert(0, "src")

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


@dataclass(frozen=True)
class VerificationResult:
    name: str
    passed: bool
    detail: str


def _event(seq: int, **payload: str) -> RealtimeEvent:
    return RealtimeEvent("verify:channel", seq, "PROGRESS", occurred_at=1000 + seq, payload=payload)


def _expect_code(fn: object, code: UIStudioErrorCode) -> bool:
    try:
        fn()  # type: ignore[operator]
    except UIStudioError as exc:
        return exc.code is code
    return False


def verify_monotonic_sequencing() -> VerificationResult:
    stream = validate_realtime_stream(tuple(_event(i) for i in range(5)))
    ok = len(stream.accepted) == 5 and [e.sequence for e in stream.accepted] == list(range(5))
    return VerificationResult(
        "monotonic sequence numbers respected", ok, f"accepted={len(stream.accepted)}"
    )


def verify_idempotent_duplicate() -> VerificationResult:
    e = _event(0)
    stream = validate_realtime_stream((e, e))
    ok = len(stream.accepted) == 1 and stream.duplicates_skipped == 1
    return VerificationResult(
        "duplicate events are idempotent", ok, f"duplicates_skipped={stream.duplicates_skipped}"
    )


def verify_out_of_order_rejection() -> VerificationResult:
    ok = _expect_code(
        lambda: validate_realtime_stream((_event(0), _event(2), _event(1))),
        UIStudioErrorCode.OUT_OF_ORDER_EVENT,
    )
    return VerificationResult("out-of-order events are rejected", ok, "OUT_OF_ORDER_EVENT raised")


def verify_gap_detection() -> VerificationResult:
    ok = _expect_code(
        lambda: validate_realtime_stream((_event(0), _event(2))), UIStudioErrorCode.MISSING_SEQUENCE
    )
    return VerificationResult("missing-sequence gaps are detected", ok, "MISSING_SEQUENCE raised")


def verify_bounded_replay() -> VerificationResult:
    contract = RealtimeChannelContract("verify:channel", event_types=("PROGRESS",), replay_window=3)
    buffer = ReplayBuffer(contract)
    for i in range(10):
        buffer.append(_event(i))
    ok = buffer.oldest_available_sequence == 7
    exceeded = _expect_code(
        lambda: buffer.events_since(0), UIStudioErrorCode.REPLAY_WINDOW_EXCEEDED
    )
    return VerificationResult(
        "replay is bounded and rejects a cursor outside the window",
        ok and exceeded,
        f"oldest={buffer.oldest_available_sequence}",
    )


def verify_reconnect_cursor() -> VerificationResult:
    cursor = issue_reconnect_cursor("verify:channel", last_applied_sequence=9, now=1000)
    ok = cursor.last_applied_sequence == 9 and cursor.channel == "verify:channel"
    return VerificationResult("reconnect cursors are issued", ok, f"cursor={cursor}")


def verify_snapshot_reconciliation() -> VerificationResult:
    contract = RealtimeChannelContract("verify:channel", event_types=("PROGRESS",), replay_window=2)
    buffer = ReplayBuffer(contract)
    for i in range(10):
        buffer.append(_event(i))
    result = reconcile_snapshot(
        "verify:channel", local_last_sequence=0, backend_snapshot_sequence=9, buffer=buffer
    )
    ok = result.full_snapshot_required and not result.reconciled
    return VerificationResult(
        "snapshot reconciliation requires a full resync beyond the replay window", ok, str(result)
    )


def verify_stale_state_indicator() -> VerificationResult:
    indicator = compute_staleness("verify:channel", last_event_at=0, now=1000, stale_after_s=30)
    return VerificationResult(
        "stale-state indicator flags an old snapshot", indicator.stale, str(indicator)
    )


def verify_pending_optimistic_commands() -> VerificationResult:
    command = OptimisticCommand("cmd-verify", submitted_at=0)
    pending_before = command.is_pending
    confirmed = command.confirm(5)
    ok = pending_before and command.is_pending and not confirmed.is_pending
    return VerificationResult(
        "optimistic commands stay pending until explicitly confirmed",
        ok,
        f"original_still_pending={command.is_pending}",
    )


def verify_restart_reconstruction() -> VerificationResult:
    contract = RealtimeChannelContract(
        "verify:channel", event_types=("PROGRESS",), replay_window=10
    )
    buffer = ReplayBuffer(contract)
    for i in range(5):
        buffer.append(_event(i))
    no_cursor = plan_restart_reconstruction(
        "verify:channel", persisted_last_sequence=None, buffer=buffer
    )
    with_cursor = plan_restart_reconstruction(
        "verify:channel", persisted_last_sequence=2, buffer=buffer
    )
    ok = no_cursor.requires_full_snapshot and with_cursor.can_replay
    return VerificationResult(
        "restart reconstruction never invents a starting point",
        ok,
        f"no_cursor_requires_snapshot={no_cursor.requires_full_snapshot}; "
        f"with_cursor_can_replay={with_cursor.can_replay}",
    )


def verify_no_client_invented_authoritative_state() -> VerificationResult:
    bad_event = _event(0, client_asserted_authoritative="true")
    ok = _expect_code(
        lambda: deny_client_invented_state(bad_event), UIStudioErrorCode.CLIENT_INVENTED_STATE
    )
    return VerificationResult(
        "client-invented authoritative state is denied", ok, "CLIENT_INVENTED_STATE raised"
    )


def main() -> int:
    checks = [
        verify_monotonic_sequencing,
        verify_idempotent_duplicate,
        verify_out_of_order_rejection,
        verify_gap_detection,
        verify_bounded_replay,
        verify_reconnect_cursor,
        verify_snapshot_reconciliation,
        verify_stale_state_indicator,
        verify_pending_optimistic_commands,
        verify_restart_reconstruction,
        verify_no_client_invented_authoritative_state,
    ]
    results = [c() for c in checks]
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print("\n" + "=" * 80)
    print("REAL-TIME UI EVENT CONTRACT VERIFICATION SUITE (deterministic; no connection opened)")
    print("=" * 80 + "\n")
    for r in results:
        print(f"{'PASS' if r.passed else 'FAIL':5} | {r.name:65} | {r.detail}")
    print("\n" + "=" * 80)
    print(f"TOTAL: {passed}/{total} checks passed")
    print("=" * 80 + "\n")
    if passed == total:
        print("Real-time contract gate: PASS. Contract complete; not activated.\n")
        return 0
    print("Real-time contract gate: INCOMPLETE — fix failures above.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
