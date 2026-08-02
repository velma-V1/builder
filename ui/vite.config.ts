// Phase 1 activation: dependencies pinned in package.json and installed. This config wires the
// React plugin, the Tailwind v4 Vite plugin, and the `@/*` path alias used throughout src/.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Tauri expects a fixed, predictable dev server port and strict port binding.
  server: {
    port: 1420,
    strictPort: true,
    // Phase 2B: proxy /api/* to the local read-only snapshot API (scripts/run_api.py) so
    // the frontend's unchanged fetch("/api/tasks/snapshot?...") reaches a real backend
    // instead of Vite's own SPA fallback. Loopback default only; override for local setups
    // where the API runs on a different port via VITE_API_PROXY_TARGET.
    //
    // Phase 3A: /api/orchestrator/* is a distinct, write-authorized process (scripts/
    // run_orchestrator.py) on its own port. This key is listed before the broader "/api"
    // key so its more specific prefix match wins; the two prefixes never overlap in what
    // they route to a real backend.
    proxy: {
      "/api/orchestrator": {
        target: process.env.VITE_ORCHESTRATOR_PROXY_TARGET ?? "http://127.0.0.1:8100",
        changeOrigin: true,
      },
      "/api": {
        target: process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  resolve: {
    alias: {
      "@": "/src",
    },
  },
  build: {
    // Tauri supports es2021+ across its target platforms.
    target: process.env.TAURI_PLATFORM === "windows" ? "chrome105" : "safari13",
    sourcemap: !!process.env.TAURI_DEBUG,
  },
});
