"use strict";

const { expect, test } = require("@playwright/test");

async function expectPublishedNumber(page, metric) {
  await expect(page.locator("#view .loading-state")).toHaveCount(0);
  await expect(page.locator("#view .error-state")).toHaveCount(0);
  await expect(page.locator("#view .panel").first()).toBeVisible();
  await expect(page.locator(`[data-freshness-key="${metric}"]`)).toContainText(/\d/);
}

test("MTGO entry renders candidate-derived data", async ({ page }) => {
  await page.goto("/index.html?format=standard&product=mtgo-statistics&range=1&lang=en");
  await expectPublishedNumber(page, "decks");
});

test("legacy Weekly Pickup path renders the admitted Landing feature", async ({ page, request }) => {
  const response = await request.get("/stats/standard/mtgo/landing/current.json");
  expect(response.ok()).toBe(true);
  const landing = await response.json();
  expect(Array.isArray(landing.features?.items)).toBe(true);
  const expectedFeatureCount = landing.features.items.length;

  await page.goto("/index.html?format=standard&product=weekly-pickup&lang=zh");
  await expect(page).toHaveURL(/product=mtgo-landing/);
  const normalizedUrl = new URL(page.url());
  expect(normalizedUrl.searchParams.get("format")).toBe("standard");
  expect(normalizedUrl.searchParams.get("product")).toBe("mtgo-landing");
  expect(normalizedUrl.searchParams.get("section")).toBe("features");
  expect(normalizedUrl.searchParams.get("lang")).toBe("zh");
  await expect(page.locator("#view .error-state")).toHaveCount(0);
  await expect(page.locator(".landing-features")).toBeVisible();
  await expect(page.locator(".landing-feature-item")).toHaveCount(expectedFeatureCount);
  const emptyState = page.locator(".landing-feature-content .landing-empty");
  if (expectedFeatureCount === 0) await expect(emptyState).toBeVisible();
  else await expect(emptyState).toHaveCount(0);
});

test("Tabletop entry renders candidate-derived data", async ({ page }) => {
  await page.goto(
    "/melee/index.html?format=modern&product=tabletop-major-events&scope=all_constructed&lang=en"
  );
  await expectPublishedNumber(page, "scope-decks");
});
