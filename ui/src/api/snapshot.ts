// Structure-only placeholder — not installed, not run in this repository state.
//
// A snapshot fetch is the recovery path when the real-time client needs a full resync (see
// realtime/client.ts's reconcileSnapshot). It is never invoked to invent state the backend hasn't
// actually sent — it only ever asks the backend directly.

import type { TaskSnapshot } from "@/queries/useTaskSnapshot";

export async function fetchTaskSnapshot(workstreamId: string): Promise<TaskSnapshot[]> {
  const response = await fetch(`/api/tasks/snapshot?workstream=${encodeURIComponent(workstreamId)}`);
  if (!response.ok) {
    throw new Error(`snapshot fetch failed: HTTP ${response.status}`);
  }
  return (await response.json()) as TaskSnapshot[];
}
