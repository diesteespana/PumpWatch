import { test, expect } from "@playwright/test";

// Requires a running stack with a seeded test user.
// See .env.local.example for connection details.

const TEST_EMAIL = process.env.TEST_USER_EMAIL ?? "testuser@example.com";
const TEST_PASS = process.env.TEST_USER_PASS ?? "testpassword1";

async function loginAs(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(TEST_EMAIL);
  await page.getByLabel("Password").fill(TEST_PASS);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/dashboard/, { timeout: 10_000 });
}

test.describe("Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page);
  });

  test("shows overview page after login", async ({ page }) => {
    await expect(page.getByText("Live Event Feed")).toBeVisible();
    await expect(page.getByText("Tracked wallets")).toBeVisible();
  });

  test("navigates to Wallets page", async ({ page }) => {
    await page.getByRole("link", { name: "Wallets" }).click();
    await expect(page).toHaveURL(/\/dashboard\/wallets/);
    await expect(page.getByRole("heading", { name: /Tracked Wallets/i })).toBeVisible();
  });

  test("navigates to Alerts page", async ({ page }) => {
    await page.getByRole("link", { name: "Alerts" }).click();
    await expect(page).toHaveURL(/\/dashboard\/alerts/);
    await expect(page.getByRole("heading", { name: /Alerts/i })).toBeVisible();
  });

  test("navigates to Tokens page", async ({ page }) => {
    await page.getByRole("link", { name: "Tokens" }).click();
    await expect(page).toHaveURL(/\/dashboard\/tokens/);
    await expect(page.getByRole("heading", { name: /Tracked Tokens/i })).toBeVisible();
  });

  test("navigates to Settings page", async ({ page }) => {
    await page.getByRole("link", { name: "Settings" }).click();
    await expect(page).toHaveURL(/\/dashboard\/settings/);
    await expect(page.getByText("Telegram")).toBeVisible();
    await expect(page.getByText("Discord")).toBeVisible();
    await expect(page.getByText("Email")).toBeVisible();
  });
});
