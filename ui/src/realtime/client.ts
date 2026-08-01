// The real-time client: WebSocket primary transport, Server-Sent Events fallback, and every
// guarantee described in factory.ui_studio.realtime_contracts (that module is the source of truth
// — this file is the client-side mirror, not an independent design). No connection is ever opened
// from this repository state (openTransport() only selects a transport class); this is the
// contract, not the activation.
//
// Guarantees implemented here, each traceable to the backend module of the same name:
//   - monotonic sequence numbers + idempotent duplicates + out-of-order rejection -> applyEvent()
//   - gap detection -> detectMissingSequence()/assertNoMissingSequence(), mirroring the backend's
//     end-of-batch judgment rather than rejecting every out-of-sequence arrival on the spot; also
//     folded into reconcileIfNeeded() directly, so a known gap can never read as up_to_date
//   - bounded replay -> ReplayBuffer
//   - reconnect cursors -> connect()'s persisted-cursor branch, ReplayBuffer.eventsSince()
//   - snapshot reconciliation -> reconcileIfNeeded(), which checks for an internal gap before ever
//     trusting the backend-reported sequence
//   - stale-state indicators -> the staleness getter
//   - pending optimistic commands until backend confirmation -> OptimisticCommand (types.ts);
//     wiring a command queue through this client is not needed by anything in this repository
//     state yet and is left for the page/hook that first issues one
//   - restart reconstruction -> connect()'s persisted-cursor branch
//   - no client-invented authoritative state -> applyEvent() only ever accepts an event that
//     arrived from the transport; there is no code path that synthesizes one locally.

import type { RealtimeEvent, StaleIndicator } from "@/realtime/types";

const RESERVED_AUTHORITATIVE_KEYS = new Set([
  "client_asserted_authoritative",
  "authoritative_override",
  "server_state_override",
]);

class ClientInventedStateError extends Error {}
class OutOfOrderEventError extends Error {}
class MissingSequenceError extends Error {}
class ReplayWindowExceededError extends Error {}

class ReplayBuffer {
  private readonly events: RealtimeEvent[] = [];
  constructor(private readonly window: number) {}

  append(event: RealtimeEvent): void {
    this.events.push(event);
    if (this.events.length > this.window) {
      this.events.shift();
    }
  }

  get oldestAvailableSequence(): number | null {
    return this.events.length > 0 ? (this.events[0]?.sequence ?? null) : null;
  }

  eventsSince(cursor: number): RealtimeEvent[] {
    const oldest = this.oldestAvailableSequence;
    if (oldest !== null && cursor < oldest - 1) {
      throw new ReplayWindowExceededError(
        `cursor ${cursor} is older than the retained window (oldest=${oldest})`,
      );
    }
    return this.events.filter((e) => e.sequence > cursor);
  }
}

function denyClientInventedState(event: RealtimeEvent): void {
  for (const key of Object.keys(event.payload)) {
    if (RESERVED_AUTHORITATIVE_KEYS.has(key)) {
      throw new ClientInventedStateError(
        `event on channel ${event.channel} sets reserved key ${key}; only the backend may assert ` +
          "authoritative state",
      );
    }
  }
}

export class RealtimeChannelClient {
  private highestSeen = -1;
  private readonly seen = new Map<number, RealtimeEvent>();
  private readonly replay: ReplayBuffer;
  private transport: "websocket" | "sse" | "disconnected" = "disconnected";
  private lastEventAt = 0;

  constructor(
    private readonly channel: string,
    private readonly replayWindow = 500,
  ) {
    this.replay = new ReplayBuffer(replayWindow);
  }

  /** Restart reconstruction: resume from a persisted cursor via replay, or request a full snapshot. */
  connect(persistedLastSequence: number | null): "resume" | "full_snapshot_required" {
    if (persistedLastSequence === null) {
      return "full_snapshot_required";
    }
    try {
      this.replay.eventsSince(persistedLastSequence);
      this.highestSeen = persistedLastSequence;
      return "resume";
    } catch (err) {
      if (err instanceof ReplayWindowExceededError) {
        return "full_snapshot_required";
      }
      throw err;
    }
  }

  /** Only ever call this with an event that actually arrived from the transport. */
  applyEvent(event: RealtimeEvent): "applied" | "duplicate_noop" {
    denyClientInventedState(event);
    this.lastEventAt = event.occurredAt;
    const seq = event.sequence;
    const prior = this.seen.get(seq);
    if (prior !== undefined) {
      if (JSON.stringify(prior) === JSON.stringify(event)) {
        return "duplicate_noop";
      }
      throw new Error(`sequence ${seq} received twice with conflicting content`);
    }
    if (seq < this.highestSeen) {
      throw new OutOfOrderEventError(`sequence ${seq} arrived after ${this.highestSeen}`);
    }
    // A higher sequence than expected is accepted, not rejected: the backend mirror
    // (validate_realtime_stream) only judges a gap once the whole batch has settled, since an
    // event that looks like a gap right now may simply be arriving ahead of one still in flight.
    // detectMissingSequence() below performs that same end-of-batch judgment on demand.
    this.seen.set(seq, event);
    this.replay.append(event);
    this.highestSeen = seq;
    return "applied";
  }

  /** Mirrors the backend's end-of-batch gap check: the lowest sequence below `highestSeen` that
   * never arrived, or `null` if the stream seen so far is contiguous. Call this once a burst of
   * events has settled (e.g. from a reconciliation timer) — never as part of every applyEvent. */
  detectMissingSequence(): number | null {
    if (this.highestSeen < 0) {
      return null;
    }
    for (let s = 0; s < this.highestSeen; s += 1) {
      if (!this.seen.has(s)) {
        return s;
      }
    }
    return null;
  }

  /** Throws MissingSequenceError if detectMissingSequence() finds an outstanding gap. */
  assertNoMissingSequence(): void {
    const missing = this.detectMissingSequence();
    if (missing !== null) {
      throw new MissingSequenceError(`gap detected: sequence ${missing} never received (highest: ${this.highestSeen})`);
    }
  }

  reconcileIfNeeded(backendSnapshotSequence: number): "up_to_date" | "replayable" | "full_snapshot_required" {
    // A known internal gap is never up_to_date, no matter what the backend reports: highestSeen
    // only tracks the highest sequence ever accepted, not whether everything below it actually
    // arrived (applyEvent() accepts a forward jump before the gap is judged — see above). This
    // never fabricates or marks the missing event as applied; it only classifies the existing gap
    // as recoverable via the retained replay window or not.
    const missing = this.detectMissingSequence();
    if (missing !== null) {
      try {
        this.replay.eventsSince(missing - 1);
        return "replayable";
      } catch (err) {
        if (err instanceof ReplayWindowExceededError) {
          return "full_snapshot_required";
        }
        throw err;
      }
    }
    if (backendSnapshotSequence <= this.highestSeen) {
      return "up_to_date";
    }
    try {
      this.replay.eventsSince(this.highestSeen);
      return "replayable";
    } catch {
      return "full_snapshot_required";
    }
  }

  get staleness(): (now: number, staleAfterMs: number) => StaleIndicator {
    return (now, staleAfterMs) => {
      const age = Math.max(0, now - this.lastEventAt);
      return { channel: this.channel, stale: age > staleAfterMs, ageS: Math.floor(age / 1000) };
    };
  }

  get currentTransport(): "websocket" | "sse" | "disconnected" {
    return this.transport;
  }

  /** WebSocket primary, SSE fallback. Neither is opened in this repository state. */
  openTransport(url: string): void {
    if (typeof WebSocket !== "undefined") {
      this.transport = "websocket";
      void url; // real implementation: new WebSocket(url), wired to applyEvent() on message
      return;
    }
    this.transport = "sse";
    void url; // real implementation: new EventSource(url), wired to applyEvent() on message
  }
}
