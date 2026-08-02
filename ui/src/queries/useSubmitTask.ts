// TanStack Query mutation for task submission (Phase 3A). On success, invalidates the existing
// read-only snapshot query so the new task appears without a manual reload.

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { submitTask, type TaskSubmissionRequest } from "@/api/orchestrator";

export function useSubmitTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: TaskSubmissionRequest) => submitTask(request),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tasks", "byWorkstream"] });
    },
  });
}
