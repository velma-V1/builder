// Mirrors factory.ui_studio.realtime_contracts.RealtimeEvent / ValidatedRealtimeStream exactly —
// keep both in sync by hand until the compiler emits this file from the backend contract.

export interface RealtimeEvent {
  channel: string;
  sequence: number;
  eventType: string;
  occurredAt: number;
  payload: Record<string, string>;
}

export interface ReconnectCursor {
  channel: string;
  lastAppliedSequence: number;
  issuedAt: number;
}

export interface StaleIndicator {
  channel: string;
  stale: boolean;
  ageS: number;
}

export interface OptimisticCommand {
  commandId: string;
  submittedAt: number;
  confirmed: boolean;
  confirmedSequence: number | null;
}

export type ConnectionTransport = "websocket" | "sse" | "disconnected";
