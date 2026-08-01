import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  retries: 0,
  reporter: "html",
  use: {
    baseURL: "http://localhost:1420",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  // The dev server is started by an operator during activation — never by this config in CI here.
  webServer: {
    command: "echo 'preview server start is NOT wired in this repository state' && exit 1",
    port: 1420,
    reuseExistingServer: true,
  },
});
