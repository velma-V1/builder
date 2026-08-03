import { afterEach, expect, it, vi } from "vitest";
import { approvePromotion } from "@/api/orchestrator";

afterEach(() => {
  vi.unstubAllGlobals();
});

it("leaves runtime authentication to the local proxy and sends no caller identity", async () => {
  const fetchMock = vi.fn(async (...args: [RequestInfo | URL, RequestInit?]) => {
    void args;
    return {
      ok: true,
      json: async () => ({ outcome: "PROMOTED", state: "COMPLETE" }),
    } as Response;
  });
  vi.stubGlobal("fetch", fetchMock);
  await approvePromotion("task-1", "apr-1");

  const init = fetchMock.mock.calls[0]?.[1];
  if (!init) throw new Error("fetch init missing");
  expect(init.headers).toEqual({
    "Content-Type": "application/json",
  });
  expect(JSON.parse(String(init.body))).toEqual({
    approval_id: "apr-1",
    confirmed_destructive: true,
  });
  expect(sessionStorage.length).toBe(0);
  expect(localStorage.length).toBe(0);
});
