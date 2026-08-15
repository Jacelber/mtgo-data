"use strict";

const { expect, test } = require("@playwright/test");

async function expectPublishedNumber(page, metric) {
  await expect(page.locator("#view .loading-state")).toHaveCount(0);
  await expect(page.locator("#view .error-state")).toHaveCount(0);
  await expect(page.locator("#view .panel").first()).toBeVisible();
  await expect(page.locator(`[data-freshness-key="${metric}"]`)).toContainText(/\d/);
}

test("MTGO page renders a published number", async ({ page }) => {
  await page.goto("/index.html?format=standard&product=mtgo-statistics&range=1&lang=en");
  await expectPublishedNumber(page, "decks");
});

test("Tabletop page renders a published number", async ({ page }) => {
  await page.goto(
    "/melee/index.html?format=modern&product=tabletop-major-events&scope=all_constructed&lang=en"
  );
  await expectPublishedNumber(page, "scope-decks");
});
