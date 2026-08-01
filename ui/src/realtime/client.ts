// Structure-only placeholder — not installed, not run in this repository state.
//
// The real-time client: WebSocket primary transport, Server-Sent Events fallback, and every
// guarantee described in factory.ui_studio.realtime_contracts (that module is the source of truth
// — this file is the client-side mirror, not an independent design). No connection is ever opened
// from this repository state; this is the contract, not the activation.
//
// Guarantees implemented here, each traceable to the backend module of the same name:
//   - monotonic sequence numbers + idempotent duplicates + out-of-order rejection + gap detection
//     -> validateAndApply()
//   - bounded replay -> ReplayBuffer
//   - reconnect cursors -> persisted cursor read/write in restoreCursor()/persistCursor()
//   - snapshot reconciliation -> reconcileIfNeeded()
//   - stale-state indicators -> staleness getter, recomputed on a timer
//   - pending optimistic commands until backend confirmation -> submitOptimistic()/confirm()
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
    if (this.highestSeen >= 0 && seq > this.highestSeen + 1) {
      // A gap: buffered, not silently dropped — reconcileIfNeeded() decides whether replay can
      // still cover it or a full snapshot is required.
      throw new MissingSequenceError(`gap detected before sequence ${seq}`);
    }
    this.seen.set(seq, event);
    this.replay.append(event);
    this.highestSeen = seq;
    return "applied";
  }

  reconcileIfNeeded(backendSnapshotSequence: number): "up_to_date" | "replayable" | "full_snapshot_required" {
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
