import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Phase3BControls } from "@/components/Phase3BControls";
import { clearOperatorSession, configureOperatorSession } from "@/api/orchestrator";

afterEach(() => {
  cleanup();
  clearOperatorSession();
  vi.unstubAllGlobals();
});

function renderControls(state = "AWAITING_APPROVAL") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <Phase3BControls taskId="task-1" state={state} />
    </QueryClientProvider>,
  );
}

it("renders durable evidence, manifest, failure reasons, and rollback evidence", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: true,
    json: async () => ({
      evidence: { run_id: "run-1", digest: "e1", passed: false, created_at: "now", items: [{ kind: "tests", detail: "failed test_x", passed: false }] },
      manifest: { run_id: "run-1", digest: "m1", branch_ref: "worker", base_sha: "base", created_at: "now", files: [{ path: "a.py", content_digest: "abc" }] },
      approval: null,
      promotion: { outcome: "ROLLED_BACK", reason: "promotion failed; rolled back", target_ref: "integration", commit: null, created_at: "now" },
    }),
  } as Response)));
  renderControls("FAILED");
  expect(await screen.findByText("Result: FAIL")).toBeInTheDocument();
  expect(screen.getByText(/failed test_x/)).toBeInTheDocument();
  expect(screen.getByText(/a.py — abc/)).toBeInTheDocument();
  expect(screen.getByText(/ROLLED_BACK: promotion failed/)).toBeInTheDocument();
});

it("reconciles a pending approval after reconnect and exposes approve and reject", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: true,
    json: async () => ({
      evidence: { run_id: "run-1", digest: "e1", passed: true, created_at: "now", items: [] },
      manifest: { run_id: "run-1", digest: "m1", branch_ref: "worker", base_sha: "base", created_at: "now", files: [] },
      approval: { approval_id: "apr-1", state: "PENDING", target_ref: "integration", expires_at: 1, requires_confirmation: true },
      promotion: null,
    }),
  } as Response)));
  renderControls();
  expect(await screen.findByText("Approval pending for integration")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Approve promotion" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Reject promotion" })).toBeDisabled();
});

it("requires an approval request before promotion", async () => {
  configureOperatorSession("test-session");
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/approval-requests")) {
      return { ok: true, json: async () => ({ approval_id: "apr-1" }) } as Response;
    }
    return { ok: true, json: async () => ({
      evidence: { run_id: "run-1", digest: "e1", passed: true, created_at: "now", items: [] },
      manifest: { run_id: "run-1", digest: "m1", branch_ref: "worker", base_sha: "base", created_at: "now", files: [] },
      approval: null,
      promotion: null,
    }) } as Response;
  });
  vi.stubGlobal("fetch", fetchMock);
  renderControls();
  fireEvent.click(await screen.findByRole("button", { name: "Request promotion approval" }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
    "/api/orchestrator/tasks/task-1/approval-requests",
    expect.objectContaining({ method: "POST" }),
  ));
});
