// Phase 3A write path: task submission, detail, and cancellation, through the write-authorized
// orchestrator API only (never the read-only snapshot API at /api/tasks/snapshot). The client
// never invents state -- every field here is exactly what the orchestrator returned. No
// approve/reject call exists anywhere in this module -- nothing can legitimately be approved
// before a real worker produces results (Phase 3B/3C).

export interface TaskSubmissionRequest {
  project_ref: string;
  workstream_id: string;
  description: string;
  priority: "low" | "normal" | "high";
  model_preference?: string;
  expected_result?: string;
  idempotency_key: string;
}

export interface TaskSubmissionResponse {
  task_id: string;
  state: string;
  created: boolean;
}

export interface TaskDetail {
  task_id: string;
  project_id: string;
  workstream_id: string | null;
  state: string;
  updated_at: string;
  description: string | null;
  priority: string | null;
  model_preference: string | null;
  expected_result: string | null;
  submitted_by: string | null;
  submitted_at: string | null;
}

export interface OrchestratorHealth {
  status: string;
  database: string;
}

export interface Phase3BEvidenceItem {
  kind: string;
  detail: string;
  passed: boolean;
}

export interface Phase3BDetail {
  evidence: null | {
    run_id: string;
    digest: string;
    passed: boolean;
    created_at: string;
    items: Phase3BEvidenceItem[];
  };
  manifest: null | {
    run_id: string;
    digest: string;
    branch_ref: string;
    base_sha: string;
    created_at: string;
    files: Array<{ path: string; content_digest: string }>;
  };
  approval: null | {
    approval_id: string;
    state: string;
    target_ref: string | null;
    expires_at: number;
    requires_confirmation: boolean;
  };
  promotion: null | {
    outcome: string;
    reason: string;
    target_ref: string | null;
    commit: string | null;
    created_at: string;
  };
}

function authorityHeaders(): Record<string, string> {
  return {
    "Content-Type": "application/json",
  };
}

async function throwOnError(response: Response, action: string): Promise<void> {
  if (response.ok) return;
  let message = `HTTP ${response.status}`;
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "error" in body && typeof body.error === "string") {
      message = body.error;
    }
  } catch {
    // response body wasn't JSON -- fall back to the status-only message above.
  }
  throw new Error(`${action} failed: ${message}`);
}

export async function submitTask(
  request: TaskSubmissionRequest,
): Promise<TaskSubmissionResponse> {
  const response = await fetch("/api/orchestrator/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  await throwOnError(response, "task submission");
  return (await response.json()) as TaskSubmissionResponse;
}

export async function getTaskDetail(taskId: string): Promise<TaskDetail> {
  const response = await fetch(`/api/orchestrator/tasks/${encodeURIComponent(taskId)}`);
  await throwOnError(response, "task detail fetch");
  return (await response.json()) as TaskDetail;
}

export async function cancelTask(taskId: string, reason?: string): Promise<TaskDetail> {
  const response = await fetch(`/api/orchestrator/tasks/${encodeURIComponent(taskId)}/cancel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(reason ? { reason } : {}),
  });
  await throwOnError(response, "task cancellation");
  return (await response.json()) as TaskDetail;
}

export async function getOrchestratorHealth(): Promise<OrchestratorHealth> {
  // Deliberately does not throw on a non-OK status: a 503 body ({"status":"degraded",...}) is
  // exactly what the health badge needs to display, not an error to propagate.
  const response = await fetch("/api/orchestrator/health");
  return (await response.json()) as OrchestratorHealth;
}

export async function getPhase3BDetail(taskId: string): Promise<Phase3BDetail> {
  const response = await fetch(
    `/api/orchestrator/tasks/${encodeURIComponent(taskId)}/phase3b`,
  );
  await throwOnError(response, "Phase 3B detail fetch");
  return (await response.json()) as Phase3BDetail;
}

export async function requestPromotionApproval(taskId: string, targetRef: string) {
  const response = await fetch(
    `/api/orchestrator/tasks/${encodeURIComponent(taskId)}/approval-requests`,
    {
      method: "POST",
      headers: authorityHeaders(),
      body: JSON.stringify({ target_ref: targetRef }),
    },
  );
  await throwOnError(response, "promotion approval request");
  return (await response.json()) as { approval_id: string };
}

export async function approvePromotion(taskId: string, approvalId: string) {
  const response = await fetch(`/api/orchestrator/tasks/${encodeURIComponent(taskId)}/approve`, {
    method: "POST",
    headers: authorityHeaders(),
    body: JSON.stringify({
      approval_id: approvalId,
      confirmed_destructive: true,
    }),
  });
  await throwOnError(response, "promotion approval");
  return (await response.json()) as { outcome: string; state: string };
}

export async function rejectPromotion(taskId: string, approvalId: string, reason: string) {
  const response = await fetch(`/api/orchestrator/tasks/${encodeURIComponent(taskId)}/reject`, {
    method: "POST",
    headers: authorityHeaders(),
    body: JSON.stringify({ approval_id: approvalId, reason }),
  });
  await throwOnError(response, "promotion rejection");
  return (await response.json()) as { outcome: string; state: string };
}

export interface IntegrationStatus {
  name: "agent-zero" | "worldmonitor";
  state: string;
  detail: string;
  occurred_at: number;
  configured_enabled: boolean;
  capability_coverage?: {
    status: "INCOMPLETE" | "COMPLETE";
    implemented: string[];
    required: string[];
  };
  operation: IntegrationResult | null;
}

export type IntegrationStatuses = Record<"agent-zero" | "worldmonitor", IntegrationStatus>;

export interface IntegrationResult {
  operation_id: string;
  status: string;
  occurred_at: number;
  context_id: string | null;
  reason: string | null;
  payload: Record<string, unknown>;
}

export async function getIntegrationStatuses(): Promise<IntegrationStatuses> {
  const response = await fetch("/api/orchestrator/integrations");
  await throwOnError(response, "integration status fetch");
  return (await response.json()) as IntegrationStatuses;
}

export async function integrationAction(
  name: IntegrationStatus["name"], action: "install" | "start" | "stop" | "disable" | "remove",
): Promise<IntegrationStatus> {
  const response = await fetch(`/api/orchestrator/integrations/${name}/${action}`, {
    method: "POST", headers: authorityHeaders(),
    body: JSON.stringify({ operation_id: crypto.randomUUID() }),
  });
  await throwOnError(response, `${name} ${action}`);
  return (await response.json()) as IntegrationStatus;
}

export async function getIntegrationLogs(name: IntegrationStatus["name"]): Promise<string[]> {
  const response = await fetch(`/api/orchestrator/integrations/${name}/logs?tail=200`, { headers: authorityHeaders() });
  await throwOnError(response, `${name} logs`);
  return ((await response.json()) as { lines: string[] }).lines;
}

export async function cancelAgentZero(operationId: string): Promise<IntegrationResult> {
  const response = await fetch("/api/orchestrator/integrations/agent-zero/cancel", {
    method: "POST", headers: authorityHeaders(), body: JSON.stringify({ operation_id: operationId }),
  });
  await throwOnError(response, "Agent Zero cancellation");
  return (await response.json()) as IntegrationResult;
}

export async function getAgentZeroOperation(operationId: string): Promise<IntegrationResult> {
  const response = await fetch(
    `/api/orchestrator/integrations/agent-zero/tasks/${encodeURIComponent(operationId)}`,
    { headers: authorityHeaders() },
  );
  await throwOnError(response, "Agent Zero operation fetch");
  return (await response.json()) as IntegrationResult;
}

export async function runAgentZero(instructions: string): Promise<IntegrationResult> {
  const response = await fetch("/api/orchestrator/integrations/agent-zero/tasks", {
    method: "POST", headers: authorityHeaders(),
    body: JSON.stringify({ operation_id: crypto.randomUUID(), instructions }),
  });
  await throwOnError(response, "Agent Zero task");
  return (await response.json()) as IntegrationResult;
}

export async function refreshWorldMonitor(): Promise<IntegrationResult> {
  const end = Date.now();
  const response = await fetch("/api/orchestrator/integrations/worldmonitor/refresh", {
    method: "POST", headers: authorityHeaders(),
    body: JSON.stringify({ operation_id: crypto.randomUUID(), start_ms: end - 86400000, end_ms: end, limit: 50 }),
  });
  await throwOnError(response, "WorldMonitor refresh");
  return (await response.json()) as IntegrationResult;
}
