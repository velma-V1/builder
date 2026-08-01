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
});
