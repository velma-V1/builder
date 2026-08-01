// Structure-only placeholder — not installed, not run in this repository state.
// Once dependencies are pinned (see package.manifest.json) and installed by an operator, this
// config wires the React plugin and the `@/*` path alias used throughout src/.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Tauri expects a fixed, predictable dev server port and strict port binding.
  server: {
    port: 1420,
    strictPort: true,
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
