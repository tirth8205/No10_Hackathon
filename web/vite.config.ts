/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
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
    environment: "jsdom",
    css: false,
  },
});
