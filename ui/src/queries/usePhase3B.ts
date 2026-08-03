import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  approvePromotion,
  getPhase3BDetail,
  rejectPromotion,
  requestPromotionApproval,
} from "@/api/orchestrator";

export function usePhase3BDetail(taskId: string) {
  return useQuery({
    queryKey: ["tasks", "phase3b", taskId] as const,
    queryFn: () => getPhase3BDetail(taskId),
    refetchInterval: 2_000,
  });
}

export function usePhase3BActions(taskId: string) {
  const client = useQueryClient();
  const reconcile = () => {
    void client.invalidateQueries({ queryKey: ["tasks", "phase3b", taskId] });
    void client.invalidateQueries({ queryKey: ["tasks", "detail", taskId] });
    void client.invalidateQueries({ queryKey: ["tasks", "byWorkstream"] });
  };
  return {
    requestApproval: useMutation({
      mutationFn: (targetRef: string) => requestPromotionApproval(taskId, targetRef),
      onSuccess: reconcile,
    }),
    approve: useMutation({
      mutationFn: (approvalId: string) => approvePromotion(taskId, approvalId),
      onSuccess: reconcile,
    }),
    reject: useMutation({
      mutationFn: ({ approvalId, reason }: { approvalId: string; reason: string }) =>
        rejectPromotion(taskId, approvalId, reason),
      onSuccess: reconcile,
    }),
  };
}
