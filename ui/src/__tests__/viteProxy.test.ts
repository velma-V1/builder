// Phase 2B: the dev server must proxy /api/* to the read-only snapshot API (scripts/run_api.py)
// instead of falling back to index.html, and must not hardcode a production hostname.
//
// Phase 3A: /api/orchestrator/* must proxy to a distinct, write-authorized process on its own
// port, and must be checked before the broader "/api" rule so its more specific prefix wins.
import { describe, expect, it } from "vitest";
import type { UserConfig } from "vite";
import viteConfig from "../../vite.config";

describe("vite dev server /api proxy", () => {
  it("proxies /api to a loopback target by default", () => {
    const config = viteConfig as UserConfig;
    const proxy = config.server?.proxy as Record<string, { target?: string }> | undefined;
    expect(proxy).toBeDefined();
    expect(proxy?.["/api"]).toBeDefined();
    const target = proxy?.["/api"]?.target ?? "";
    expect(target).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/);
  });

  it("proxies /api/orchestrator to a distinct loopback target, listed before /api", () => {
    const config = viteConfig as UserConfig;
    const proxy = config.server?.proxy as Record<string, { target?: string }> | undefined;
    expect(proxy).toBeDefined();
    expect(proxy?.["/api/orchestrator"]).toBeDefined();
    const orchestratorTarget = proxy?.["/api/orchestrator"]?.target ?? "";
    expect(orchestratorTarget).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/);
    expect(orchestratorTarget).not.toBe(proxy?.["/api"]?.target);

    const keys = Object.keys(proxy ?? {});
    expect(keys.indexOf("/api/orchestrator")).toBeLessThan(keys.indexOf("/api"));
  });
});
