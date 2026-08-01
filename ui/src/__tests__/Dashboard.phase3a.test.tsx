// Phase 3A additions to the Dashboard: cancel button visibility per task state, the click-through
// details panel, and the orchestrator health badge. Fetch is routed by URL so each backend surface
// (read-only snapshot vs. write-authorized orchestrator) gets its own deterministic mock response —
// never a live network call.
import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App } from "@/App";
import type { TaskSnapshot } from "@/queries/useTaskSnapshot";

function renderApp() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>,
  );
}

function stubFetchByUrl(handlers: { snapshot?: TaskSnapshot[]; health?: object; detail?: object }) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/orchestrator/health")) {
        return { ok: true, json: async () => handlers.health ?? { status: "ok", database: "reachable" } } as Response;
      }
      if (url.includes("/api/orchestrator/tasks/")) {
        return { ok: true, json: async () => handlers.detail ?? {} } as Response;
      }
      if (url.includes("/api/tasks/snapshot")) {
        return { ok: true, json: async () => handlers.snapshot ?? [] } as Response;
      }
      return { ok: true, json: async () => ({}) } as Response;
    }),
  );
}

describe("Dashboard Phase 3A: cancel visibility", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    cleanup();
  });

  it("shows a Cancel button for a non-terminal task", async () => {
    stubFetchByUrl({ snapshot: [{ task_id: "t-1", state: "running", updated_at: 1000 }] });
    renderApp();
    expect(await screen.findByText("t-1: running")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
  });

  it("shows a Cancel button for a queued task (cancelled via the QUEUED->PLANNING pre-step)", async () => {
    stubFetchByUrl({ snapshot: [{ task_id: "t-5", state: "queued", updated_at: 1000 }] });
    renderApp();
    expect(await screen.findByText("t-5: queued")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
  });

  it("hides the Cancel button for a terminal task", async () => {
    stubFetchByUrl({ snapshot: [{ task_id: "t-2", state: "complete", updated_at: 1000 }] });
    renderApp();
    expect(await screen.findByText("t-2: complete")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
  });

  it("hides the Cancel button for an already-cancelled task", async () => {
    stubFetchByUrl({ snapshot: [{ task_id: "t-3", state: "cancelled", updated_at: 1000 }] });
    renderApp();
    expect(await screen.findByText("t-3: cancelled")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
  });

  it("hides the Cancel button for a failed task (no legal edge to STOPPING, even though FAILED isn't backend-terminal)", async () => {
    stubFetchByUrl({ snapshot: [{ task_id: "t-6", state: "failed", updated_at: 1000 }] });
    renderApp();
    expect(await screen.findByText("t-6: failed")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
  });

  it("hides the Cancel button for a task already mid-cancellation (STOPPING)", async () => {
    stubFetchByUrl({ snapshot: [{ task_id: "t-7", state: "stopping", updated_at: 1000 }] });
    renderApp();
    expect(await screen.findByText("t-7: stopping")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
  });
});

describe("Dashboard Phase 3A: orchestrator health badge", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    cleanup();
  });

  it("reports healthy when the orchestrator health route returns ok", async () => {
    stubFetchByUrl({ snapshot: [], health: { status: "ok", database: "reachable" } });
    renderApp();
    expect(await screen.findByText(/Orchestrator: healthy/)).toBeInTheDocument();
  });

  it("reports unreachable when the orchestrator health route returns degraded", async () => {
    stubFetchByUrl({ snapshot: [], health: { status: "degraded", database: "unreachable" } });
    renderApp();
    expect(await screen.findByText(/Orchestrator: unreachable/)).toBeInTheDocument();
  });
});

describe("Dashboard Phase 3A: task details panel", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    cleanup();
  });

  it("shows task details after clicking a task row", async () => {
    stubFetchByUrl({
      snapshot: [{ task_id: "t-4", state: "running", updated_at: 1000 }],
      detail: {
        task_id: "t-4",
        project_id: "builder",
        workstream_id: "ws-1",
        state: "running",
        updated_at: 1000,
        description: "Do the thing",
        priority: "normal",
        model_preference: null,
        expected_result: null,
        submitted_by: "operator",
        submitted_at: "2026-08-01T00:00:00Z",
      },
    });
    renderApp();
    const row = await screen.findByRole("button", { name: "t-4: running" });
    fireEvent.click(row);
    await waitFor(() => expect(screen.getByText("Do the thing")).toBeInTheDocument());
  });
});
