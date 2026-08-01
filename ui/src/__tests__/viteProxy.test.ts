// Phase 2B: the dev server must proxy /api/* to the read-only snapshot API (scripts/run_api.py)
// instead of falling back to index.html, and must not hardcode a production hostname.
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
});
