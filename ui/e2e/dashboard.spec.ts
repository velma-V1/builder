import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("dashboard renders the command center heading", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Builder Command Center" })).toBeVisible();
});

test("dashboard sidebar toggle collapses and expands", async ({ page }) => {
  await page.goto("/");
  const toggle = page.getByRole("button", { name: "Toggle sidebar" });
  await toggle.click();
  await toggle.click();
});

test("dashboard has no detectable accessibility violations", async ({ page }) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
