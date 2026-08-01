"""Real-time UI event contracts: sequencing, replay, reconnect, reconciliation — contract complete,
not activated (no WebSocket/SSE connection is opened anywhere in this module).

Guarantees, each backed by a concrete function/type below rather than left as a comment:

* **monotonic sequence numbers** — every event carries a per-channel ``sequence``.
* **idempotent duplicate events** — :func:`validate_realtime_stream` no-ops an exact repeat.
* **gap detection** / **out-of-order rejection** — :func:`validate_realtime_stream` (same shape as
  :mod:`factory.integrations.agent_zero.event_validation`, generalized to a UI channel).
* **bounded replay** — :class:`ReplayBuffer` retains at most ``replay_window`` events per channel.
* **reconnect cursors** — :func:`issue_reconnect_cursor` / :meth:`ReplayBuffer.events_since`.
* **snapshot reconciliation** — :func:`reconcile_snapshot`.
* **stale-state indicators** — :func:`compute_staleness`.
* **pending optimistic commands until backend confirmation** — :class:`OptimisticCommand`.
* **restart reconstruction** — :func:`plan_restart_reconstruction`.
* **no client-invented authoritative state** — :func:`deny_client_invented_state`.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from factory.ui_studio.errors import UIStudioError, UIStudioErrorCode
from factory.ui_studio.models import RealtimeChannelContract

#: Reserved payload keys a client must never set — the backend is the only source of these.
_RESERVED_AUTHORITATIVE_KEYS = frozenset(
    {"client_asserted_authoritative", "authoritative_override", "server_state_override"}
)


@dataclass(frozen=True, slots=True)
class RealtimeEvent:
    channel: str
    sequence: int
    event_type: str
    occurred_at: int
    payload: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ValidatedRealtimeStream:
    accepted: tuple[RealtimeEvent, ...]
    duplicates_skipped: int


def deny_client_invented_state(event: RealtimeEvent) -> None:
    """Raise ``CLIENT_INVENTED_STATE`` if a client-originated event asserts authoritative state."""
    hit = _RESERVED_AUTHORITATIVE_KEYS.intersection(event.payload)
    if hit:
        raise UIStudioError(
            UIStudioErrorCode.CLIENT_INVENTED_STATE,
            f"event on channel {event.channel!r} sets reserved key(s) {sorted(hit)}; only the "
            "backend may assert authoritative state",
        )


def validate_realtime_stream(events: tuple[RealtimeEvent, ...]) -> ValidatedRealtimeStream:
    """Same integrity shape as the Agent Zero event validator: dedup / out-of-order / gap."""
    seen: dict[int, RealtimeEvent] = {}
    order: list[int] = []
    highest_seen = -1
    duplicates_skipped = 0

    for candidate in events:
        deny_client_invented_state(candidate)
        seq = candidate.sequence
        if seq in seen:
            if seen[seq] == candidate:
                duplicates_skipped += 1
                continue
            raise UIStudioError(
                UIStudioErrorCode.DUPLICATE_EVENT,
                f"sequence {seq} on channel {candidate.channel!r} received twice with "
                "conflicting content",
            )
        if seq < highest_seen:
            raise UIStudioError(
                UIStudioErrorCode.OUT_OF_ORDER_EVENT,
                f"sequence {seq} on channel {candidate.channel!r} arrived after {highest_seen}",
            )
        seen[seq] = candidate
        order.append(seq)
        highest_seen = seq

    if highest_seen >= 0:
        missing = next((s for s in range(highest_seen) if s not in seen), None)
        if missing is not None:
            raise UIStudioError(
                UIStudioErrorCode.MISSING_SEQUENCE,
                f"gap detected: sequence {missing} never received (highest: {highest_seen})",
            )

    return ValidatedRealtimeStream(tuple(seen[s] for s in order), duplicates_skipped)


class ReplayBuffer:
    """A bounded, per-channel replay buffer. Retains at most ``contract.replay_window`` events."""

    __slots__ = ("_buffer", "_contract")

    def __init__(self, contract: RealtimeChannelContract) -> None:
        self._contract = contract
        self._buffer: deque[RealtimeEvent] = deque(maxlen=contract.replay_window)

    def append(self, event: RealtimeEvent) -> None:
        deny_client_invented_state(event)
        self._buffer.append(event)

    @property
    def oldest_available_sequence(self) -> int | None:
        return self._buffer[0].sequence if self._buffer else None

    def events_since(self, cursor: int) -> tuple[RealtimeEvent, ...]:
        """Return buffered events after ``cursor``. Raises if the gap exceeds the replay window."""
        oldest = self.oldest_available_sequence
        if oldest is not None and cursor < oldest - 1:
            raise UIStudioError(
                UIStudioErrorCode.REPLAY_WINDOW_EXCEEDED,
                f"cursor {cursor} is older than the retained window (oldest={oldest}); "
                "a full snapshot resync is required",
            )
        return tuple(e for e in self._buffer if e.sequence > cursor)


@dataclass(frozen=True, slots=True)
class ReconnectCursor:
    channel: str
    last_applied_sequence: int
    issued_at: int


def issue_reconnect_cursor(channel: str, last_applied_sequence: int, now: int) -> ReconnectCursor:
    return ReconnectCursor(channel, last_applied_sequence, now)


@dataclass(frozen=True, slots=True)
class SnapshotReconciliationResult:
    channel: str
    reconciled: bool
    resync_from_sequence: int
    full_snapshot_required: bool
    detail: str


def reconcile_snapshot(
    channel: str, *, local_last_sequence: int, backend_snapshot_sequence: int, buffer: ReplayBuffer,
) -> SnapshotReconciliationResult:
    """Decide whether the local sequence can be caught up via replay or needs a full snapshot."""
    if backend_snapshot_sequence <= local_last_sequence:
        return SnapshotReconciliationResult(
            channel, True, local_last_sequence + 1, False, "already up to date"
        )
    try:
        buffer.events_since(local_last_sequence)
    except UIStudioError:
        return SnapshotReconciliationResult(
            channel, False, backend_snapshot_sequence, True,
            "replay window exceeded; full snapshot resync required",
        )
    return SnapshotReconciliationResult(
        channel, True, local_last_sequence + 1, False, "caught up via bounded replay"
    )


@dataclass(frozen=True, slots=True)
class StaleIndicator:
    channel: str
    stale: bool
    age_s: int


def compute_staleness(
    channel: str, *, last_event_at: int, now: int, stale_after_s: int
) -> StaleIndicator:
    age = max(0, now - last_event_at)
    return StaleIndicator(channel, age > stale_after_s, age)


@dataclass(frozen=True, slots=True)
class OptimisticCommand:
    """A client-issued command pending backend confirmation. Never treated as applied until then."""

    command_id: str
    submitted_at: int
    confirmed: bool = False
    confirmed_sequence: int | None = None

    def confirm(self, sequence: int) -> OptimisticCommand:
        return OptimisticCommand(self.command_id, self.submitted_at, True, sequence)

    @property
    def is_pending(self) -> bool:
        return not self.confirmed


@dataclass(frozen=True, slots=True)
class RestartReconstructionPlan:
    channel: str
    can_replay: bool
    resume_from_sequence: int
    requires_full_snapshot: bool
    detail: str


def plan_restart_reconstruction(
    channel: str, *, persisted_last_sequence: int | None, buffer: ReplayBuffer,
) -> RestartReconstructionPlan:
    """Decide how a client rebuilds state after a full restart. Never invents a starting point."""
    if persisted_last_sequence is None:
        return RestartReconstructionPlan(
            channel, False, 0, True, "no persisted cursor; full snapshot required"
        )
    try:
        buffer.events_since(persisted_last_sequence)
    except UIStudioError:
        return RestartReconstructionPlan(
            channel, False, persisted_last_sequence, True,
            "persisted cursor is older than the retained replay window",
        )
    return RestartReconstructionPlan(
        channel, True, persisted_last_sequence + 1, False, "resumable via bounded replay"
    )
