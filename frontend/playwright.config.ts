import fs from "node:fs";

import { defineConfig, devices } from "@playwright/test";

// E2E happy path (docs/IMPLEMENTATION_PLAN.md Phase 8): register -> dashboard -> exercises ->
// favorite -> workout create -> session -> log set -> finish -> nutrition log -> progress log
// weight. Assumes the backend (FastAPI) and this frontend are already running — see
// docs/DEVELOPMENT.md — mirroring how CI brings the stack up via docker-compose before running
// this suite, rather than trying to boot Postgres/Redis/FastAPI from inside Playwright itself.

// This sandbox environment ships a pre-installed Chromium at a fixed path instead of the browser
// `npx playwright install` would normally download (see AGENTS.md / env notes) — use it only
// when present and the caller hasn't already pointed at a specific binary, so this config still
// works unmodified on a machine with a normally-installed Playwright browser (e.g. real CI).
const SANDBOX_CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const executablePath =
  process.env.PLAYWRIGHT_CHROMIUM_PATH || (fs.existsSync(SANDBOX_CHROMIUM) ? SANDBOX_CHROMIUM : undefined);

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false, // the spec runs one continuous user journey against shared backend state
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        launchOptions: {
          executablePath,
          args: executablePath ? ["--no-sandbox"] : [],
        },
      },
    },
  ],
});
