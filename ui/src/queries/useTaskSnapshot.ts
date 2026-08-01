// TanStack Query owns backend snapshots and records — the client never invents this shape or
// caches it past its declared staleness window. Mirrors
// factory.ui_studio.data_contracts.builder_task_snapshot_contract().

import { useQuery } from "@tanstack/react-query";
import { fetchTaskSnapshot } from "@/api/snapshot";

export interface TaskSnapshot {
  task_id: string;
  state: string;
  /** UTC Unix epoch in MILLISECONDS (integer). Mirrors factory.api.mapping.to_task_snapshot on
   *  the backend — do not treat this as seconds. */
  updated_at: number;
}

const STALE_AFTER_MS = 15_000;

export function useTaskSnapshot(workstreamId: string) {
  return useQuery({
    queryKey: ["tasks", "byWorkstream", workstreamId] as const,
    queryFn: () => fetchTaskSnapshot(workstreamId),
    staleTime: STALE_AFTER_MS,
  });
}
