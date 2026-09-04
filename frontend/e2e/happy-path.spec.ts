import { createHmac } from "node:crypto";

import { test, expect } from "@playwright/test";

// One continuous user journey: open the Mini App -> dashboard -> exercises -> favorite -> create
// a workout -> start a session -> log a set -> finish -> log a meal -> log today's weight. Run
// against the "en" locale so button/label text is stable to assert on (see messages/en.json).
//
// There is no web sign-up any more (docs/DECISIONS.md D-10), so the journey starts the way a real
// one does: by injecting a Telegram Mini App SDK whose `initData` is signed with the bot token,
// exactly as the Telegram client would hand it over. The app then authenticates itself through
// its normal path — nothing about auth is stubbed, only the SDK that carries the identity.
//
// Requires the backend and this frontend to already be running, and TELEGRAM_BOT_TOKEN to match
// the backend's, since the signature is verified server-side.

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;

test.describe.configure({ mode: "serial" });

test.skip(!BOT_TOKEN, "TELEGRAM_BOT_TOKEN must match the backend's to sign initData");

function signedInitData(telegramId: number): string {
  const fields: Record<string, string> = {
    auth_date: String(Math.floor(Date.now() / 1000)),
    query_id: "AAHdF6IQAAAAAN0XohDhrOrc",
    user: JSON.stringify({ id: telegramId, first_name: "E2E", username: `e2e_${telegramId}` }),
  };
  const check = Object.keys(fields)
    .sort()
    .map((k) => `${k}=${fields[k]}`)
    .join("\n");
  const secret = createHmac("sha256", "WebAppData").update(BOT_TOKEN!).digest();
  const hash = createHmac("sha256", secret).update(check).digest("hex");
  return new URLSearchParams({ ...fields, hash }).toString();
}

test("open the Mini App, log a workout session, a meal, and today's weight", async ({ page }) => {
  // --- Arrive as Telegram would deliver us ---------------------------------------------------
  const initData = signedInitData(Date.now() % 1_000_000_000);
  await page.addInitScript((data) => {
    (window as unknown as { Telegram: unknown }).Telegram = {
      WebApp: { initData: data, ready: () => {}, expand: () => {}, colorScheme: "dark" },
    };
  }, initData);

  await page.goto("/en");
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
