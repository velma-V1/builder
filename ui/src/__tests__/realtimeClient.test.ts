// Client-side mirror of tests/ui_studio/test_realtime_contracts.py — same guarantees, same shape.
import { describe, expect, it } from "vitest";
import { RealtimeChannelClient } from "@/realtime/client";
import type { RealtimeEvent } from "@/realtime/types";

function event(sequence: number, payload: Record<string, string> = {}): RealtimeEvent {
  return { channel: "workstream:t1", sequence, eventType: "PROGRESS", occurredAt: 1000 + sequence, payload };
}

describe("RealtimeChannelClient", () => {
  it("applies a monotonic stream in full", () => {
    const client = new RealtimeChannelClient("workstream:t1");
    for (let i = 0; i < 4; i += 1) {
      expect(client.applyEvent(event(i))).toBe("applied");
    }
  });

  it("treats an exact duplicate as an idempotent no-op", () => {
    const client = new RealtimeChannelClient("workstream:t1");
    const e = event(0);
    expect(client.applyEvent(e)).toBe("applied");
    expect(client.applyEvent(e)).toBe("duplicate_noop");
  });

  it("rejects an out-of-order event", () => {
    const client = new RealtimeChannelClient("workstream:t1");
    client.applyEvent(event(0));
    client.applyEvent(event(2));
    expect(() => client.applyEvent(event(1))).toThrow(/arrived after/);
  });

  it("detects a missing-sequence gap that never gets filled", () => {
    const client = new RealtimeChannelClient("workstream:t1");
    client.applyEvent(event(0));
    client.applyEvent(event(2));
    expect(client.detectMissingSequence()).toBe(1);
    expect(() => client.assertNoMissingSequence()).toThrow(/never received/);
  });

  it("reports no gap once every sequence below the highest has arrived", () => {
    const client = new RealtimeChannelClient("workstream:t1");
    client.applyEvent(event(0));
    client.applyEvent(event(1));
    client.applyEvent(event(2));
    expect(client.detectMissingSequence()).toBeNull();
    expect(() => client.assertNoMissingSequence()).not.toThrow();
  });

  it("rejects a client-invented authoritative state claim", () => {
    const client = new RealtimeChannelClient("workstream:t1");
    const bad = event(0, { client_asserted_authoritative: "true" });
    expect(() => client.applyEvent(bad)).toThrow(/authoritative state/);
  });

  it("requires a full snapshot on restart with no persisted cursor", () => {
    const client = new RealtimeChannelClient("workstream:t1");
    expect(client.connect(null)).toBe("full_snapshot_required");
  });

  it("resumes via replay on restart with a persisted cursor still inside the window", () => {
    const client = new RealtimeChannelClient("workstream:t1", 2);
    for (let i = 0; i < 5; i += 1) {
      client.applyEvent(event(i));
    }
    // Window is 2, so only sequences 3,4 remain buffered; cursor 3 is still coverable.
    expect(client.connect(3)).toBe("resume");
  });

  it("requires a full snapshot on restart with a persisted cursor outside the window", () => {
    const client = new RealtimeChannelClient("workstream:t1", 2);
    for (let i = 0; i < 5; i += 1) {
      client.applyEvent(event(i));
    }
    // Window is 2, so a cursor of 0 is long evicted from the buffer.
    expect(client.connect(0)).toBe("full_snapshot_required");
  });

  describe("staleness", () => {
    it("flags an old snapshot as stale", () => {
      const client = new RealtimeChannelClient("workstream:t1");
      client.applyEvent(event(0));
      const indicator = client.staleness(1000 + 40_000, 30_000);
      expect(indicator.stale).toBe(true);
      expect(indicator.ageS).toBe(40);
    });

    it("does not flag a fresh snapshot as stale", () => {
      const client = new RealtimeChannelClient("workstream:t1");
      client.applyEvent(event(0));
      const indicator = client.staleness(1000 + 10_000, 30_000);
      expect(indicator.stale).toBe(false);
    });
  });

  describe("reconcileIfNeeded", () => {
    it("reports up_to_date only when the local stream is actually contiguous", () => {
      const client = new RealtimeChannelClient("workstream:t1");
      client.applyEvent(event(0));
      client.applyEvent(event(1));
      client.applyEvent(event(2));
      expect(client.reconcileIfNeeded(2)).toBe("up_to_date");
    });

    it("never reports up_to_date when an internal gap exists, even if the backend snapshot sequence matches highestSeen", () => {
      const client = new RealtimeChannelClient("workstream:t1");
      client.applyEvent(event(0));
      client.applyEvent(event(2));
      // Before the fix this returned "up_to_date" because it only compared backendSnapshotSequence
      // against highestSeen (2) and never checked whether the locally-seen set was contiguous.
      expect(client.reconcileIfNeeded(2)).not.toBe("up_to_date");
    });

    it("returns replayable when the missing range is still inside the retained replay window", () => {
      const client = new RealtimeChannelClient("workstream:t1", 5);
      client.applyEvent(event(0));
      client.applyEvent(event(2));
      expect(client.reconcileIfNeeded(2)).toBe("replayable");
    });

    it("returns full_snapshot_required when the missing range has fallen outside the replay window", () => {
      const client = new RealtimeChannelClient("workstream:t1", 2);
      client.applyEvent(event(0));
      client.applyEvent(event(2));
      // Push the window past the gap's position (0) before anyone reconciles.
      client.applyEvent(event(3));
      client.applyEvent(event(4));
      expect(client.reconcileIfNeeded(4)).toBe("full_snapshot_required");
    });

    it("does not invent, discard, or mark the missing event as applied while reconciling", () => {
      const client = new RealtimeChannelClient("workstream:t1", 5);
      client.applyEvent(event(0));
      client.applyEvent(event(2));
      client.reconcileIfNeeded(2);
      // The gap must still be reported afterwards — reconciliation only classifies the gap, it
      // never fabricates the missing event or marks it as if it had arrived.
      expect(client.detectMissingSequence()).toBe(1);
      expect(() => client.assertNoMissingSequence()).toThrow(/never received/);
    });
  });
});
