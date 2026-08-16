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

test("MTGO matchup search filters the loaded projection without another data request", async ({ page }) => {
  let matchupRequests = 0;
  page.on("request", request => {
    if (request.url().includes("/stats/modern/mtgo/matchup_4w.json")) matchupRequests += 1;
  });
  await page.goto("/index.html?format=modern&product=mtgo-matchups&range=4&lang=en");
  await expect(page.locator("#matchup-search")).toBeVisible();
  await expect(page.locator(".matchup-table .row-head").first()).toBeVisible();
  await page.locator('[data-matchup-row="prowess"]').click();
  await page.locator('[data-matchup-column="prowess"]').click();
  await expect(page.locator(".matchup-table .row-head", { hasText: "Izzet Prowess" })).toBeVisible();
  const initialColumnCount = await page.locator(".matchup-table .column-head:not(.overall)").count();
  const initialRequests = matchupRequests;

  await page.locator("#matchup-search").fill("  MONO-RED   prowess  ");

  await expect(page.locator(".matchup-table .row-head")).toHaveCount(2);
  await expect(page.locator(".matchup-table .row-head").first()).toContainText("Prowess");
  await expect(page.locator(".matchup-table .row-head").nth(1)).toContainText("Mono-Red Prowess");
  await expect(page.locator(".matchup-table .column-head:not(.overall)"))
    .toHaveCount(initialColumnCount);
  await expect(page.locator(".matchup-table .column-head", { hasText: "Boros Energy" }))
    .toBeVisible();
  expect(matchupRequests).toBe(initialRequests);

  await page.locator("#matchup-search").fill("not a published deck");
  await expect(page.locator(".matchup-search-empty")).toContainText(
    "No decks match “not a published deck”."
  );
  expect(matchupRequests).toBe(initialRequests);

  await page.locator(".matchup-search-input [data-matchup-search-clear]").click();
  await expect(page.locator("#matchup-search")).toHaveValue("");
  await expect(page.locator(".matchup-table .row-head", { hasText: "Izzet Prowess" })).toBeVisible();
  expect(matchupRequests).toBe(initialRequests);

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator("#matchup-search")).toBeVisible();
  const mobileLayout = await page.locator("html").evaluate(element => ({
    clientWidth: element.clientWidth,
    scrollWidth: element.scrollWidth,
    searchDirection: getComputedStyle(
      element.querySelector(".matchup-search-input")
    ).flexDirection,
  }));
  expect(mobileLayout.scrollWidth).toBe(mobileLayout.clientWidth);
  expect(mobileLayout.searchDirection).toBe("column");
});

test("Tabletop matchup search uses the same visible projection", async ({ page }) => {
  await page.goto(
    "/melee/index.html?format=modern&product=tabletop-major-events&event=434455&view=matchup&scope=all_constructed&lang=zh"
  );
  await expect(page.locator("#matchup-search")).toBeVisible();

  await page.locator("#matchup-search").fill("mono-green broodscale");

  await expect(page.locator(".matchup-table .row-head")).toHaveCount(2);
  await expect(page.locator(".matchup-table .row-head").first()).toContainText("Broodscale Combo");
  await expect(page.locator(".matchup-table .row-head").nth(1)).toContainText(
    "Mono-Green Broodscale Combo"
  );
});
