"use strict";

const { expect, test } = require("@playwright/test");

test("catalog failure keeps the shell and retries with a new request", async ({ page }) => {
  let attempts = 0;
  await page.route("**/stats/catalog.json", route => {
    attempts += 1;
    if (attempts === 1) route.abort();
    else route.continue();
  });

  await page.goto("/index.html?format=modern&product=mtgo-statistics&lang=zh");
  await expect(page.locator(".app-header")).toBeVisible();
  await expect(page.locator("#view .error-state")).toBeVisible();
  await expect(page.locator("button[data-retry-catalog]")).toHaveText("重试产品目录");

  await page.locator("button[data-retry-catalog]").click();
  await expect(page.locator("#view .panel").first()).toBeVisible();
  expect(attempts).toBe(2);
});

test("background refresh stages a complete view until the user applies it", async ({ page }) => {
  let rangeRequests = 0;
  await page.route("**/stats/modern/mtgo/range_1w.json", async route => {
    rangeRequests += 1;
    const response = await route.fetch();
    const document = await response.json();
    if (rangeRequests > 1) document.archetypes[0].name = "Updated Test Identity";
    await route.fulfill({ response, json: document });
  });

  await page.goto("/index.html?format=modern&product=mtgo-statistics&lang=en");
  await expect(page.locator("#view .panel").first()).toBeVisible();
  await expect(page.getByText("Updated Test Identity")).toHaveCount(0);

  await page.evaluate(() => checkForUpdates());
  await expect(page.locator("#refresh-status")).toContainText("New data is available");
  await expect(page.getByText("Updated Test Identity")).toHaveCount(0);

  await page.locator("button[data-apply-refresh]").click();
  await expect(page.locator(".identity-label", { hasText: "Updated Test Identity" }).first()).toBeVisible();
  expect(rangeRequests).toBe(2);
});

test("leaving a view discards an update that the user did not apply", async ({ page }) => {
  let rangeRequests = 0;
  await page.route("**/stats/modern/mtgo/range_1w.json", async route => {
    rangeRequests += 1;
    const response = await route.fetch();
    const document = await response.json();
    if (rangeRequests > 1) document.archetypes[0].name = "Unapplied Test Identity";
    await route.fulfill({ response, json: document });
  });

  await page.goto("/index.html?format=modern&product=mtgo-statistics&lang=en");
  await expect(page.locator("#view .panel").first()).toBeVisible();
  await page.evaluate(() => checkForUpdates());
  await expect(page.locator("#refresh-status")).toContainText("New data is available");

  await page.locator("button[data-stats-range='4']").click();
  await expect(page.locator("#refresh-status")).toBeHidden();
  await page.locator("button[data-stats-range='1']").click();
  await expect(page.getByText("Unapplied Test Identity")).toHaveCount(0);
  expect(rangeRequests).toBe(2);
});

test("grouped refresh includes the detail document currently on screen", async ({ page }) => {
  let deckRequests = 0;
  await page.route("**/stats/modern/mtgo/decks_1w.json", route => {
    deckRequests += 1;
    if (deckRequests === 2) route.abort();
    else route.continue();
  });

  await page.goto("/index.html?format=modern&product=mtgo-statistics&lang=en");
  await page.locator(".desktop-metric-table button[data-detail-identity]").first().click();
  await expect(page.locator(".desktop-metric-table .deck-detail")).toBeVisible();
  await page.evaluate(() => checkForUpdates());

  await expect(page.locator("#refresh-status")).toContainText(
    "Showing the last successfully loaded data"
  );
  await expect(page.locator(".desktop-metric-table .deck-detail")).toBeVisible();
  expect(deckRequests).toBe(2);
});

test("a failed grouped refresh preserves the complete old view and can retry", async ({ page }) => {
  let completenessRequests = 0;
  await page.route("**/stats/modern/mtgo/completeness/1w.json", route => {
    completenessRequests += 1;
    if (completenessRequests === 2) route.abort();
    else route.continue();
  });
  await page.goto("/index.html?format=modern&product=mtgo-statistics&lang=zh");
  await expect(page.locator("#view .panel").first()).toBeVisible();
  const firstIdentity = await page.locator("button[data-detail-identity]").first().innerText();

  await page.evaluate(() => checkForUpdates());
  await expect(page.locator("#refresh-status")).toContainText("上次成功加载的数据");
  await expect(page.locator("button[data-detail-identity]").first()).toHaveText(firstIdentity);

  await page.locator("button[data-retry-refresh]").click();
  await expect(page.locator("#refresh-status")).toBeHidden();
  expect(completenessRequests).toBe(3);
});
