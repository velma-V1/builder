import { afterEach, expect, it, vi } from "vitest";
import {
  approvePromotion,
  configureOperatorSession,
  clearOperatorSession,
} from "@/api/orchestrator";

afterEach(() => {
  clearOperatorSession();
  vi.unstubAllGlobals();
});

it("keeps the runtime credential in memory and sends no caller operator identity", async () => {
  const fetchMock = vi.fn(async (...args: [RequestInfo | URL, RequestInit?]) => {
    void args;
    return {
      ok: true,
      json: async () => ({ outcome: "PROMOTED", state: "COMPLETE" }),
    } as Response;
  });
  vi.stubGlobal("fetch", fetchMock);
  configureOperatorSession("ephemeral-session-token");

  await approvePromotion("task-1", "apr-1");

  const init = fetchMock.mock.calls[0]?.[1];
  if (!init) throw new Error("fetch init missing");
  expect(init.headers).toEqual({
    "Content-Type": "application/json",
    Authorization: "Bearer ephemeral-session-token",
  });
  expect(JSON.parse(String(init.body))).toEqual({
    approval_id: "apr-1",
    confirmed_destructive: true,
  });
  expect(sessionStorage.length).toBe(0);
  expect(localStorage.length).toBe(0);
});

it("fails closed when no runtime operator session was injected", async () => {
  await expect(approvePromotion("task-1", "apr-1")).rejects.toThrow(
    /operator session is unavailable/,
  );
});
