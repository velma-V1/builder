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
