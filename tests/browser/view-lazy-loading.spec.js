"use strict";

const { expect, test } = require("@playwright/test");

function observeNetwork(page) {
  const requests = [];
  page.on("request", request => requests.push(new URL(request.url()).pathname));
  return requests;
}

async function loadReadable(page, path, errors = []) {
  page.on("pageerror", error => errors.push(error.message));
  await page.goto(path);
  await expect(page.locator("#view .panel").first()).toBeVisible();
}

function requestCount(requests, path) {
  return requests.filter(item => item === path).length;
}

function requestCountMatching(requests, predicate) {
  return requests.filter(predicate).length;
}

test("MTGO statistics loads detail once and isolates format caches", async ({ page }) => {
  const requests = observeNetwork(page);
  const errors = [];
  await loadReadable(
    page,
    "/index.html?format=modern&product=mtgo-statistics&lang=zh",
    errors
  );
  const modernDecks = "/stats/modern/mtgo/decks_1w.json";
  const standardDecks = "/stats/standard/mtgo/decks_1w.json";
  expect(requests).not.toContain(modernDecks);

  const detail = page.locator("button[data-detail-identity]").first();
  await detail.click();
  await expect(page.locator(".deck-detail-row")).toBeVisible();
  expect(requestCount(requests, modernDecks)).toBe(1);

  await page.locator("button[data-close-detail]").click();
  await expect(page.locator(".deck-detail-row")).toHaveCount(0);
  await detail.click();
  await expect(page.locator(".deck-detail-row")).toBeVisible();
  expect(requestCount(requests, modernDecks)).toBe(1);

  const modernMatchup = "/stats/modern/mtgo/matchup_4w.json";
  await page.locator('button[data-product="mtgo-matchups"]').click();
  await expect(page.locator(".matchup-table")).toBeVisible();
  expect(requestCount(requests, modernMatchup)).toBe(1);
  await page.locator('button[data-product="mtgo-statistics"]').click();
  await expect(page.locator(".data-table")).toBeVisible();
  expect(requestCount(requests, modernDecks)).toBe(1);
  expect(requestCount(requests, "/stats/modern/mtgo/range_1w.json")).toBe(1);

  await page.locator('button[data-format="standard"]').click();
  await expect(page.locator('button[data-format="standard"]')).toHaveClass(/active/);
  expect(requests).not.toContain(standardDecks);
  await page.locator("button[data-detail-identity]").first().click();
  await expect(page.locator(".deck-detail-row")).toBeVisible();
  expect(requestCount(requests, modernDecks)).toBe(1);
  expect(requestCount(requests, standardDecks)).toBe(1);
  expect(errors).toEqual([]);
});

test("MTGO Top 8 defers and reuses comparison bases", async ({ page }) => {
  const requests = observeNetwork(page);
  const errors = [];
  await loadReadable(
    page,
    "/index.html?format=modern&product=mtgo-top8&lang=zh",
    errors
  );
  const isBases = path => path.startsWith("/stats/modern/mtgo/top8/")
    && path.endsWith("-bases.json");
  expect(requestCountMatching(requests, isBases)).toBe(0);

  const detail = page.locator("button[data-top8-detail]").first();
  await detail.click();
  await expect(page.locator(".deck-detail")).toBeVisible();
  expect(requestCountMatching(requests, isBases)).toBe(1);

  await page.locator("button[data-close-top8]").click();
  await detail.click();
  await expect(page.locator(".deck-detail")).toBeVisible();
  expect(requestCountMatching(requests, isBases)).toBe(1);
  expect(errors).toEqual([]);
});

test("Tabletop views and details load on first activation only", async ({ page }) => {
  const requests = observeNetwork(page);
  const errors = [];
  await loadReadable(
    page,
    "/melee/index.html?format=modern&product=tabletop-major-events&lang=zh",
    errors
  );
  const matchup = "/stats/modern/melee/events/434455/matchup.json";
  const eventDecks = "/stats/modern/melee/events/434455/decks.json";
  const mtgoDecks = "/stats/modern/mtgo/decks_4w.json";
  expect(requests).not.toContain(matchup);
  expect(requests).not.toContain(eventDecks);
  expect(requests).not.toContain(mtgoDecks);

  await page.locator('button[data-tabletop-view="matchup"]').click();
  await expect(page.locator(".matchup-table")).toBeVisible();
  expect(requestCount(requests, matchup)).toBe(1);
  expect(requests).not.toContain(eventDecks);
  expect(requests).not.toContain(mtgoDecks);

  await page.locator('button[data-tabletop-view="overview"]').click();
  await expect(page.locator("button[data-tabletop-detail]").first()).toBeVisible();
  await page.locator('button[data-tabletop-view="matchup"]').click();
  await expect(page.locator(".matchup-table")).toBeVisible();
  expect(requestCount(requests, matchup)).toBe(1);

  await page.locator('button[data-tabletop-view="overview"]').click();
  const detail = page.locator("button[data-tabletop-detail]").first();
  await detail.click();
  await expect(page.locator(".deck-detail-row")).toBeVisible();
  expect(requestCount(requests, eventDecks)).toBe(1);
  expect(requestCount(requests, mtgoDecks)).toBe(1);

  await page.locator("button[data-close-tabletop-detail]").click();
  await detail.click();
  await expect(page.locator(".deck-detail-row")).toBeVisible();
  expect(requestCount(requests, eventDecks)).toBe(1);
  expect(requestCount(requests, mtgoDecks)).toBe(1);
  expect(errors).toEqual([]);
});

test("deferred request failure stays local and retries with a new request", async ({ page }) => {
  const errors = [];
  let attempts = 0;
  await page.route("**/stats/modern/mtgo/decks_1w.json", route => {
    attempts += 1;
    if (attempts === 1) route.abort();
    else route.continue();
  });
  await loadReadable(
    page,
    "/index.html?format=modern&product=mtgo-statistics&lang=zh",
    errors
  );
  await page.locator("button[data-detail-identity]").first().click();
  await expect(page.locator("#view .inline-error-state")).toBeVisible();
  await expect(page.locator("#view .data-table")).toBeVisible();
  await page.locator("button[data-retry-view]").click();
  await expect(page.locator(".deck-detail-row")).toBeVisible();
  expect(attempts).toBe(2);
  expect(errors).toEqual([]);
});
