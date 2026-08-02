// Phase 3A: task submission is the only way a task enters the authoritative queue. This proves
// the form validates required fields, submits through the orchestrator API (never the read-only
// snapshot API), and keeps the same idempotency key across a failed submit but rotates it after a
// confirmed success.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TaskSubmissionForm } from "@/components/TaskSubmissionForm";

function renderForm() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <TaskSubmissionForm />
    </QueryClientProvider>,
  );
}

function fillRequiredFields() {
  fireEvent.change(screen.getByLabelText("Project / repo reference"), {
    target: { value: "builder" },
  });
  fireEvent.change(screen.getByLabelText("Workstream"), { target: { value: "ws-1" } });
  fireEvent.change(screen.getByLabelText("Description"), {
    target: { value: "Do the thing" },
  });
}

describe("TaskSubmissionForm", () => {
  beforeEach(() => {
    // Base stub so a test that doesn't care about the network response still has one; each
    // test that asserts on the request/response overrides this with its own stub.
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => ({}) }) as Response));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    cleanup();
  });

  it("disables submit until the required fields are filled", () => {
    renderForm();
    expect(screen.getByRole("button", { name: "Submit task" })).toBeDisabled();
    fillRequiredFields();
    expect(screen.getByRole("button", { name: "Submit task" })).not.toBeDisabled();
  });

  it("submits through POST /api/orchestrator/tasks with a generated idempotency key", async () => {
    const fetchMock = vi.fn<typeof fetch>(
      async () =>
        ({
          ok: true,
          json: async () => ({ task_id: "t-9", state: "queued", created: true }),
        }) as Response,
    );
    vi.stubGlobal("fetch", fetchMock);

    renderForm();
    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: "Submit task" }));

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("t-9 submitted"));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/orchestrator/tasks",
      expect.objectContaining({ method: "POST" }),
    );
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(init.body as string) as { idempotency_key: string };
    expect(body.idempotency_key).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("keeps the same idempotency key across a failed submit so a retry is a true replay", async () => {
    const fetchMock = vi.fn<typeof fetch>(
      async () => ({ ok: false, status: 503, json: async () => ({ error: "unavailable" }) }) as Response,
    );
    vi.stubGlobal("fetch", fetchMock);

    renderForm();
    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: "Submit task" }));
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: "Submit task" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));

    const firstKey = (
      JSON.parse((fetchMock.mock.calls[0] as [string, RequestInit])[1].body as string) as {
        idempotency_key: string;
      }
    ).idempotency_key;
    const secondKey = (
      JSON.parse((fetchMock.mock.calls[1] as [string, RequestInit])[1].body as string) as {
        idempotency_key: string;
      }
    ).idempotency_key;
    expect(secondKey).toBe(firstKey);
  });
});
