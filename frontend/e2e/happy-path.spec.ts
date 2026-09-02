import { test, expect } from "@playwright/test";

// One continuous user journey (docs/IMPLEMENTATION_PLAN.md Phase 8): register -> dashboard ->
// exercises -> favorite -> create a workout -> start a session -> log a set -> finish -> log a
// meal -> log today's weight. Run against the "en" locale so button/label text is stable to
// assert on (see messages/en.json) — the same flow is exercised in every language by the unit
// tests around next-intl message completeness, so this file's job is the end-to-end wiring, not
// translation coverage.
//
// Requires the backend and this frontend to already be running (npm run build && npm run start,
// backend via uvicorn against a reachable Postgres) — see docs/DEVELOPMENT.md.

test.describe.configure({ mode: "serial" });

const username = `e2e_${Date.now()}`;
const password = "password123";

test("register, log a workout session, a meal, and today's weight", async ({ page }) => {
  // --- Register -----------------------------------------------------------------------------
  await page.goto("/en/register");
  await page.locator("#username").fill(username);
  await page.locator("#password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/en\/dashboard/, { timeout: 15_000 });

  // --- Exercises: favorite the first result --------------------------------------------------
  await page.goto("/en/exercises");
  const firstFavoriteButton = page.getByRole("button", { name: "Add to favorites" }).first();
  await expect(firstFavoriteButton).toBeVisible({ timeout: 15_000 });
  await firstFavoriteButton.click();
  await expect(page.getByRole("button", { name: "Remove from favorites" }).first()).toBeVisible();

  // --- Workouts: create one with a single exercise -------------------------------------------
  await page.goto("/en/workouts");
  await page.getByRole("button", { name: "New workout" }).click();
  await page.locator("#w-name").fill("E2E Push Day");

  const exerciseSelect = page.locator("select").filter({ hasText: "Select an exercise" });
  await exerciseSelect.selectOption({ index: 1 });
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByText(/^1\. /)).toBeVisible();

  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page).toHaveURL(/\/en\/workouts\/[0-9a-f-]{36}$/, { timeout: 15_000 });

  // --- Start the workout and log one set ------------------------------------------------------
  await page.getByRole("link", { name: "Start workout" }).click();
  await expect(page).toHaveURL(/\/en\/workouts\/[0-9a-f-]{36}\/session$/, { timeout: 15_000 });

  const repsInput = page.locator("input[type=number]").first();
  const weightInput = page.locator("input[type=number]").nth(1);
  await expect(repsInput).toBeVisible({ timeout: 15_000 });
  await repsInput.fill("10");
  await weightInput.fill("40");
  await page.getByRole("button", { name: "Log set" }).click();
  await expect(page.getByText("Set 1")).toBeVisible();

  await page.getByRole("button", { name: "Finish session" }).click();
  await expect(page.getByRole("heading", { name: "Workout complete" })).toBeVisible({ timeout: 15_000 });

  // --- Nutrition: log a meal --------------------------------------------------------------
  await page.goto("/en/nutrition");
  await page.getByPlaceholder("Food name").fill("Chicken breast");
  const macroInputs = page.locator("input[type=number]");
  await macroInputs.nth(0).fill("150"); // grams
  await macroInputs.nth(1).fill("250"); // calories
  await page.getByRole("button", { name: "Log meal" }).click();
  await expect(page.getByText("250", { exact: false }).first()).toBeVisible({ timeout: 15_000 });

  // --- Progress: log today's weight -----------------------------------------------------------
  await page.goto("/en/progress");
  await page.locator("#weight-kg").fill("82.5");
  await page.getByRole("button", { name: "Save", exact: true }).first().click();
  await expect(page.locator("#weight-kg")).toHaveValue("", { timeout: 15_000 });
});
