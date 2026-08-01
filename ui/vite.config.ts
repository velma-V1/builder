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
