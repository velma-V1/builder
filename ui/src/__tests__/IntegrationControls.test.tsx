import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { IntegrationControls } from "@/components/IntegrationControls";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function renderControls() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <IntegrationControls />
    </QueryClientProvider>,
  );
}

it("shows authoritative independent state and actionable errors", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: true,
    json: async () => ({
      "agent-zero": { name: "agent-zero", state: "FAILED", detail: "Docker unavailable", occurred_at: 1 },
      worldmonitor: { name: "worldmonitor", state: "READY", detail: "ready", occurred_at: 2 },
    }),
  } as Response)));

  renderControls();

  expect(await screen.findByText("Agent Zero: FAILED")).toBeInTheDocument();
  expect(screen.getByText("Docker unavailable")).toBeInTheDocument();
  expect(screen.getByText("WorldMonitor: READY")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Start Agent Zero" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Stop WorldMonitor" })).toBeInTheDocument();
});

it("reports WorldMonitor's approved scope as incomplete instead of earthquake-complete", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: true,
    json: async () => ({
      "agent-zero": { name: "agent-zero", state: "READY", configured_enabled: true, detail: "ready", occurred_at: 1 },
      worldmonitor: {
        name: "worldmonitor",
        state: "READY",
        configured_enabled: true,
        detail: "ready",
        occurred_at: 1,
        capability_coverage: {
          status: "INCOMPLETE",
          implemented: ["disasters.earthquakes"],
          required: ["disasters", "climate", "markets"],
        },
      },
    }),
  } as Response)));

  renderControls();

  expect(await screen.findByText(/WorldMonitor capability scope: INCOMPLETE/)).toBeInTheDocument();
  expect(screen.getByText(/Implemented: disasters.earthquakes/)).toBeInTheDocument();
});

it("performs real authenticated lifecycle actions", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    if (String(input).endsWith("/start")) {
      return { ok: true, json: async () => ({ state: "READY" }) } as Response;
    }
    return { ok: true, json: async () => ({
      "agent-zero": { name: "agent-zero", state: "STOPPED", detail: "stopped", occurred_at: 1 },
      worldmonitor: { name: "worldmonitor", state: "STOPPED", detail: "stopped", occurred_at: 1 },
    }) } as Response;
  });
  vi.stubGlobal("fetch", fetchMock);
  renderControls();

  fireEvent.click(await screen.findByRole("button", { name: "Start Agent Zero" }));

  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
    "/api/orchestrator/integrations/agent-zero/start",
    expect.objectContaining({ method: "POST", headers: { "Content-Type": "application/json" } }),
  ));
});

it("submits an Agent Zero task and reconciles the durable Builder result", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    if (String(input).endsWith("/tasks")) {
      return { ok: true, json: async () => ({ operation_id: "dispatch-1", status: "RUNNING", context_id: "task-1", payload: {} }) } as Response;
    }
    if (String(input).includes("/tasks/dispatch-1")) {
      return { ok: true, json: async () => ({ operation_id: "dispatch-1", status: "SUCCEEDED", context_id: "task-1", payload: { task_id: "task-1" } }) } as Response;
    }
    return { ok: true, json: async () => ({
      "agent-zero": { name: "agent-zero", state: "READY", detail: "ready", occurred_at: 1 },
      worldmonitor: { name: "worldmonitor", state: "READY", detail: "ready", occurred_at: 1 },
    }) } as Response;
  });
  vi.stubGlobal("fetch", fetchMock);
  renderControls();

  fireEvent.change(await screen.findByLabelText("Agent Zero instructions"), { target: { value: "fix tests" } });
  fireEvent.click(screen.getByRole("button", { name: "Run Agent Zero task" }));

  expect(await screen.findByText("Builder task task-1 completed verification and promotion.")).toBeInTheDocument();
});

it("does not expose operational controls for disabled integrations", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: true,
    json: async () => ({
      "agent-zero": { name: "agent-zero", state: "DISABLED", detail: "disabled by configuration", occurred_at: 1 },
      worldmonitor: { name: "worldmonitor", state: "DISABLED", detail: "disabled by configuration", occurred_at: 1 },
    }),
  } as Response)));

  renderControls();

  expect(await screen.findByText("Agent Zero: DISABLED")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Agent Zero/ })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /WorldMonitor/ })).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Agent Zero instructions")).not.toBeInTheDocument();
});

it("keeps removal and restart controls available after a runtime disable", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: true,
    json: async () => ({
      "agent-zero": { name: "agent-zero", state: "DISABLED", configured_enabled: true, detail: "disabled by operator", occurred_at: 1 },
      worldmonitor: { name: "worldmonitor", state: "READY", configured_enabled: true, detail: "ready", occurred_at: 1 },
    }),
  } as Response)));

  renderControls();

  expect(await screen.findByRole("button", { name: "Start Agent Zero" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Remove Agent Zero/ })).toBeInTheDocument();
});

it("reconciles a durable Agent Zero operation after dashboard reconnect", async () => {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    if (String(input).includes("/tasks/dispatch-restart")) {
      return { ok: true, json: async () => ({ operation_id: "dispatch-restart", status: "SUCCEEDED", context_id: "task-restart", reason: null, payload: { task_id: "task-restart" } }) } as Response;
    }
    return { ok: true, json: async () => ({
      "agent-zero": {
        name: "agent-zero", state: "READY", detail: "ready", occurred_at: 1,
        operation: { operation_id: "dispatch-restart", status: "RUNNING", context_id: "task-restart", reason: null, payload: {} },
      },
      worldmonitor: { name: "worldmonitor", state: "READY", detail: "ready", occurred_at: 1, operation: null },
    }) } as Response;
  }));

  renderControls();

  expect(await screen.findByText("Builder task task-restart completed verification and promotion.")).toBeInTheDocument();
});

it("restores durable WorldMonitor degraded evidence after dashboard reconnect", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: true,
    json: async () => ({
      "agent-zero": { name: "agent-zero", state: "READY", detail: "ready", occurred_at: 1, operation: null },
      worldmonitor: {
        name: "worldmonitor", state: "DEGRADED", detail: "source unavailable", occurred_at: 2,
        operation: { operation_id: "refresh-restart", status: "FAILED", context_id: null, reason: "USGS unavailable after restart", payload: {} },
      },
    }),
  } as Response)));

  renderControls();

  expect(await screen.findByRole("alert")).toHaveTextContent("USGS unavailable after restart");
});

it("refreshes and displays WorldMonitor source-attributed records", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    if (String(input).endsWith("/refresh")) {
      return { ok: true, json: async () => ({ operation_id: "refresh-1", status: "SUCCEEDED", payload: { records: [{ id: "q1", summary: "M5 — Anchorage", geography: "1,2", freshness: "FRESH", source: { name: "USGS via WorldMonitor", url: "https://earthquake.usgs.gov/q1", record_id: "q1" } }] } }) } as Response;
    }
    return { ok: true, json: async () => ({
      "agent-zero": { name: "agent-zero", state: "READY", detail: "ready", occurred_at: 1 },
      worldmonitor: { name: "worldmonitor", state: "READY", detail: "ready", occurred_at: 1 },
    }) } as Response;
  });
  vi.stubGlobal("fetch", fetchMock);
  renderControls();

  fireEvent.click(await screen.findByRole("button", { name: "Refresh WorldMonitor" }));

  expect(await screen.findByText("M5 — Anchorage")).toBeInTheDocument();
  expect(screen.getByText(/USGS via WorldMonitor/)).toBeInTheDocument();
});

it("shows durable WorldMonitor degraded-source evidence without records", async () => {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    if (String(input).endsWith("/refresh")) {
      return { ok: true, json: async () => ({ operation_id: "refresh-2", status: "FAILED", context_id: null, reason: "USGS upstream unavailable", payload: {} }) } as Response;
    }
    return { ok: true, json: async () => ({
      "agent-zero": { name: "agent-zero", state: "READY", detail: "ready", occurred_at: 1 },
      worldmonitor: { name: "worldmonitor", state: "DEGRADED", detail: "USGS upstream unavailable", occurred_at: 1 },
    }) } as Response;
  }));
  renderControls();

  fireEvent.click(await screen.findByRole("button", { name: "Refresh WorldMonitor" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("USGS upstream unavailable");
  expect(screen.queryByRole("listitem")).not.toBeInTheDocument();
});
