// TanStack Query mutation for task cancellation (Phase 3A). On success, invalidates the
// existing read-only snapshot query so the CANCELLED state appears without a manual reload.

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { cancelTask } from "@/api/orchestrator";

export interface CancelTaskArgs {
  taskId: string;
  reason?: string;
}

export function useCancelTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, reason }: CancelTaskArgs) => cancelTask(taskId, reason),
    onSuccess: (_data, { taskId }) => {
      void queryClient.invalidateQueries({ queryKey: ["tasks", "byWorkstream"] });
      // Also invalidate this task's own detail query -- otherwise a details panel already open
      // for the task being cancelled would keep showing its pre-cancellation state.
      void queryClient.invalidateQueries({ queryKey: ["tasks", "detail", taskId] });
    },
  });
}
