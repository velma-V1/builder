// TanStack Query poll for the orchestrator API's health (Phase 3A) -- feeds the dashboard's
// health badge. Never throws on a degraded response -- getOrchestratorHealth() always resolves
// with the reported status/database fields, since that's exactly what the badge needs to show.

import { useQuery } from "@tanstack/react-query";
import { getOrchestratorHealth } from "@/api/orchestrator";

const POLL_INTERVAL_MS = 10_000;

export function useOrchestratorHealth() {
  return useQuery({
    queryKey: ["orchestrator", "health"] as const,
    queryFn: () => getOrchestratorHealth(),
    refetchInterval: POLL_INTERVAL_MS,
    retry: false,
  });
}
