"""Agent Zero event-stream integrity: monotonic sequencing, idempotent dedup, fail-closed gaps.

Events arrive from an untrusted external worker over an unreliable transport. This validator gives
exactly four outcomes:

* an exact repeat of an already-seen event (same sequence, same content) is an **idempotent
  no-op** — accepted silently;
* the same sequence number reappearing with *different* content is a **DUPLICATE_EVENT** conflict —
  rejected, since two different events cannot both be "the" event at that position;
* a never-before-seen sequence number lower than the highest sequence already accepted is an
  **OUT_OF_ORDER_EVENT** — rejected, since accepting it would require silently reordering untrusted
  output back into a position that has already moved past it;
* once the stream is finalized, any integer below the highest accepted sequence that was never
  filled is a **MISSING_SEQUENCE** gap — rejected, since a skipped event might have carried a
  patch/artifact required for evidence integrity.

Accepting a new-highest sequence does not require contiguity at the moment it arrives (polling may
be coarse-grained); gap detection is therefore performed once, over the finalized set, rather than
eagerly on every forward jump — eager gap rejection would make a later out-of-order arrival
unreachable, since the only way a lower sequence can ever arrive is if a forward jump was tolerated
first.

This module does not interpret event *payloads* — only their positions in the stream. Payload/result
completeness is :mod:`result_mapping`'s job.
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.integrations.agent_zero.errors import AgentZeroError, AgentZeroErrorCode
from factory.integrations.agent_zero.models import AgentZeroEvent


@dataclass(frozen=True, slots=True)
class ValidatedEventStream:
    accepted: tuple[AgentZeroEvent, ...]
    duplicates_skipped: int


def validate_event_stream(events: tuple[AgentZeroEvent, ...]) -> ValidatedEventStream:
    """Validate ``events`` in the order given. Raises on the first integrity violation found."""
    seen: dict[int, AgentZeroEvent] = {}
    order: list[int] = []
    highest_seen = -1
    duplicates_skipped = 0

    for candidate in events:
        seq = candidate.sequence
        if seq in seen:
            if seen[seq] == candidate:
                duplicates_skipped += 1
                continue
            raise AgentZeroError(
                AgentZeroErrorCode.DUPLICATE_EVENT,
                f"sequence {seq} received twice with conflicting content",
            )
        if seq < highest_seen:
            raise AgentZeroError(
                AgentZeroErrorCode.OUT_OF_ORDER_EVENT,
                f"sequence {seq} arrived after {highest_seen} was already accepted",
            )
        seen[seq] = candidate
        order.append(seq)
        highest_seen = seq

    if highest_seen >= 0:
        missing = next((s for s in range(highest_seen) if s not in seen), None)
        if missing is not None:
            raise AgentZeroError(
                AgentZeroErrorCode.MISSING_SEQUENCE,
                f"gap detected: sequence {missing} was never received "
                f"(highest received: {highest_seen})",
            )

    accepted = tuple(seen[s] for s in order)
    return ValidatedEventStream(accepted, duplicates_skipped)
