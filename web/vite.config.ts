/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // The back end (uvicorn app.main:app --port 8000) serves the frontend-shaped API under /web.
    proxy: { "/web": "http://localhost:8000" },
  },
  css: {
    // GOV.UK Frontend still contains an old Internet Explorer media query hack
    // that the minifier rejects. Recovering strips it; modern browsers ignore it anyway.
    lightningcss: { errorRecovery: true },
    preprocessorOptions: {
      scss: {
        loadPaths: ["node_modules"],
        quietDeps: true,
        silenceDeprecations: ["import"],
      },
    },
  },
  test: {
    env: { VITE_SAMPLE_DATA: "1" },
    environment: "jsdom",
    css: false,
  },
});
