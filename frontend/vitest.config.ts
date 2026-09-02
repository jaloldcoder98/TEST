import path from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    globals: true,
    // Playwright specs live under e2e/ and have their own runner — keep them out of vitest's
    // collection so `npm test` stays fast and doesn't try to boot a browser.
    exclude: ["node_modules/**", "e2e/**"],
  },
});
