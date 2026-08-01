// TanStack Query for a single task's detail (Phase 3A) -- submission metadata + current state.

import { useQuery } from "@tanstack/react-query";
import { getTaskDetail } from "@/api/orchestrator";

export function useTaskDetail(taskId: string | null) {
  return useQuery({
    queryKey: ["tasks", "detail", taskId] as const,
    queryFn: () => getTaskDetail(taskId as string),
    enabled: taskId !== null,
  });
}
