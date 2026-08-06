"use strict";

const { expect, test } = require("@playwright/test");

async function expectReadable(page) {
  await expect(page.locator("#view .loading-state")).toHaveCount(0);
  await expect(page.locator("#view .error-state")).toHaveCount(0);
  await expect(page.locator("#view .panel").first()).toBeVisible();
}

function parameters(page) {
  return new URL(page.url()).searchParams;
}

test("existing entry URLs remain unchanged until durable state changes", async ({ page }) => {
  await page.goto("/index.html?format=modern&product=mtgo-statistics&lang=zh");
  await expectReadable(page);
  await expect(page).toHaveURL(
    /\/index\.html\?format=modern&product=mtgo-statistics&lang=zh$/
  );

  await page.locator('button[data-stats-range="12"]').click();
  await expect(page.locator('button[data-stats-range="12"]')).toHaveClass(/active/);
  expect(parameters(page).get("range")).toBe("12");
  expect(parameters(page).get("sort")).toBe("high_score_share");
  expect(parameters(page).get("dir")).toBe("desc");
});

test("MTGO statistics state survives sharing, reload, back, and forward", async ({ page }) => {
  await page.goto("/index.html?format=modern&product=mtgo-statistics&lang=zh");
  await expectReadable(page);

  await page.locator('button[data-stats-range="12"]').click();
  await page.locator('button[data-stats-sort="name"]').click();
  const detail = page.locator("button[data-detail-identity]").first();
  const detailId = await detail.getAttribute("data-detail-identity");
  await detail.click();
  await expect(page.locator(".deck-detail-row")).toBeVisible();

  expect(parameters(page).get("range")).toBe("12");
  expect(parameters(page).get("sort")).toBe("name");
  expect(parameters(page).get("dir")).toBe("asc");
  expect(parameters(page).get("detail")).toBe(detailId);

  await page.reload();
  await expectReadable(page);
  await expect(page.locator('button[data-stats-range="12"]')).toHaveClass(/active/);
  await expect(page.locator(".deck-detail-row")).toBeVisible();

  await page.locator('button[data-product="mtgo-matchups"]').click();
  await expect(page.locator(".matchup-table")).toBeVisible();
  expect(parameters(page).get("product")).toBe("mtgo-matchups");
  await page.goBack();
  await expect(page.locator(".deck-detail-row")).toBeVisible();
  await expect(page.locator('button[data-stats-range="12"]')).toHaveClass(/active/);
  await page.goForward();
  await expect(page.locator(".matchup-table")).toBeVisible();
});

test("subtype details derive expansion without serializing transient rows", async ({ page }) => {
  await page.goto("/index.html?format=modern&product=mtgo-statistics&lang=zh");
  await expectReadable(page);

  const toggle = page.locator("button[data-stats-toggle]").first();
  await toggle.click();
  const subtype = page.locator('button[data-detail-identity*="/"]').first();
  const subtypeId = await subtype.getAttribute("data-detail-identity");
  expect(subtypeId).toContain("/");
  await subtype.click();
  await expect(page.locator(".deck-detail-row")).toBeVisible();

  const url = new URL(page.url());
  expect(url.searchParams.get("detail")).toBe(subtypeId);
  expect(url.searchParams.has("expanded")).toBe(false);
  expect(url.searchParams.has("events")).toBe(false);

  await page.reload();
  await expect(page.locator(".deck-detail-row")).toBeVisible();
  await expect(page.locator(`button[data-detail-identity="${subtypeId}"]`)).toBeVisible();
});

test("Top 8 week and deck detail survive reload", async ({ page }) => {
  await page.goto("/index.html?format=modern&product=mtgo-top8&lang=en");
  await expectReadable(page);

  const weeks = page.locator("#top8-week option");
  expect(await weeks.count()).toBeGreaterThan(1);
  const olderFile = await weeks.nth(1).getAttribute("value");
  await page.locator("#top8-week").selectOption(olderFile);
  const detail = page.locator("button[data-top8-detail]").first();
  const detailId = await detail.getAttribute("data-top8-detail");
  await detail.click();
  await expect(page.locator(".deck-detail")).toBeVisible();

  expect(parameters(page).get("week")).toBe(olderFile.replace(/\.json$/, ""));
  expect(parameters(page).get("detail")).toBe(detailId);
  await page.reload();
  await expect(page.locator("#top8-week")).toHaveValue(olderFile);
  await expect(page.locator(".deck-detail")).toBeVisible();
});

test("Tabletop event, view, scope, sort, detail, and language are recoverable", async ({ page }) => {
  await page.goto(
    "/melee/index.html?format=modern&product=tabletop-major-events&lang=zh"
  );
  await expectReadable(page);

  await page.locator('button[data-tabletop-sort="name"]').click();
  const detail = page.locator("button[data-tabletop-detail]").first();
  const detailId = await detail.getAttribute("data-tabletop-detail");
  await detail.click();
  await expect(page.locator(".deck-detail-row")).toBeVisible();
  await page.locator("#lang-en").click();

  expect(parameters(page).get("event")).toBe("434455");
  expect(parameters(page).get("view")).toBe("overview");
  expect(parameters(page).get("scope")).toBe("all_constructed");
  expect(parameters(page).get("sort")).toBe("name");
  expect(parameters(page).get("dir")).toBe("asc");
  expect(parameters(page).get("detail")).toBe(detailId);
  expect(parameters(page).get("lang")).toBe("en");

  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.locator(".deck-detail-row")).toBeVisible();

  await page.locator('button[data-tabletop-view="matchup"]').click();
  await expect(page.locator(".matchup-table")).toBeVisible();
  expect(parameters(page).get("view")).toBe("matchup");
  expect(parameters(page).get("detail")).toBeNull();
  await page.goBack();
  await expect(page.locator(".deck-detail-row")).toBeVisible();
});

test("invalid extended state falls back and canonicalizes without an error", async ({ page }) => {
  await page.goto(
    "/index.html?format=modern&product=mtgo-statistics&range=99&sort=bogus&dir=sideways&detail=missing&events=2,1&lang=zh"
  );
  await expectReadable(page);

  const current = parameters(page);
  expect(current.get("range")).toBe("1");
  expect(current.get("sort")).toBe("high_score_share");
  expect(current.get("dir")).toBe("desc");
  expect(current.get("detail")).toBeNull();
  expect(current.has("events")).toBe(false);
});
