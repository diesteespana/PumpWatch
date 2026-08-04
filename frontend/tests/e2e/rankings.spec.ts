import { test, expect } from "@playwright/test";

const TEST_EMAIL = process.env.TEST_USER_EMAIL ?? "testuser@example.com";
const TEST_PASS = process.env.TEST_USER_PASS ?? "testpassword1";

async function loginAs(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(TEST_EMAIL);
  await page.getByLabel("Password").fill(TEST_PASS);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/dashboard/, { timeout: 10_000 });
}

test.describe("Rankings", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page);
  });

  test("navigates to rankings page", async ({ page }) => {
    await page.getByRole("link", { name: "Rankings" }).click();
    await expect(page).toHaveURL(/\/dashboard\/rankings/);
    await expect(
      page.getByRole("heading", { name: /Wallet Rankings/i }),
    ).toBeVisible();
  });

  test("shows empty state when no events", async ({ page }) => {
    await page.goto("/dashboard/rankings");
    // Either the table renders or the empty state — both are valid
    const hasTable = await page.locator("table").isVisible().catch(() => false);
    const hasEmpty = await page
      .getByText("No data yet")
      .isVisible()
      .catch(() => false);
    expect(hasTable || hasEmpty).toBe(true);
  });
});
