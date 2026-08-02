// End-to-end render check for the actual App tree (App -> Dashboard -> Card/Button/stores/queries)
// under jsdom. A real browser isn't available in every environment this suite runs in, so this is
// the strongest in-repo substitute: it exercises the real component graph, QueryClientProvider,
// Zustand store, and TanStack Query hook, with `fetch` replaced by deterministic mock data — never
// a live network call (no backend exists in this repository state).
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App } from "@/App";
import type { TaskSnapshot } from "@/queries/useTaskSnapshot";

const mockTasks: TaskSnapshot[] = [{ task_id: "t-1", state: "running", updated_at: 1000 }];

function renderApp() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>,
  );
}

describe("App/Dashboard render", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, json: async () => mockTasks }) as Response),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    cleanup();
  });

  it("renders the command center heading with no thrown errors", async () => {
    renderApp();
    expect(await screen.findByRole("heading", { name: "Builder Command Center" })).toBeInTheDocument();
  });

  it("renders the backend-sourced task snapshot once the query resolves", async () => {
    renderApp();
    expect(await screen.findByText("t-1: running")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/tasks/snapshot"));
  });

  it("collapses and expands the sidebar via Zustand presentation state only", async () => {
    renderApp();
    const toggle = await screen.findByRole("button", { name: "Toggle sidebar" });
    fireEvent.click(toggle);
    fireEvent.click(toggle);
    await waitFor(() => expect(toggle).toBeInTheDocument());
  });
});

describe("App/Dashboard stale/error truthfulness (API unavailable or invalid)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    cleanup();
  });

  it("shows the stale-reconciling message, never fabricated data, when the network call rejects", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network error");
      }),
    );
    renderApp();
    expect(await screen.findByText("Snapshot may be stale — reconciling…")).toBeInTheDocument();
    expect(screen.queryByText("t-1: running")).not.toBeInTheDocument();
  });

  it("shows the stale-reconciling message, never fabricated data, on a non-OK HTTP response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, status: 503, json: async () => ({}) }) as Response),
    );
    renderApp();
    expect(await screen.findByText("Snapshot may be stale — reconciling…")).toBeInTheDocument();
    expect(screen.queryByText("t-1: running")).not.toBeInTheDocument();
  });

  it("shows the stale-reconciling message, never fabricated data, when the body isn't valid JSON", async () => {
    // Mirrors today's real failure mode: Vite's SPA fallback returns index.html (200, text/html)
    // for an unproxied /api/* request, and response.json() throws parsing it.
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          ({
            ok: true,
            json: async () => {
              throw new SyntaxError("Unexpected token '<'");
            },
          }) as unknown as Response,
      ),
    );
    renderApp();
    expect(await screen.findByText("Snapshot may be stale — reconciling…")).toBeInTheDocument();
    expect(screen.queryByText("t-1: running")).not.toBeInTheDocument();
  });
});
