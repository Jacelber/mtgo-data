"use strict";

const { expect, test } = require("@playwright/test");

test.beforeEach(async ({ page }) => {
  page.runtimeErrors = [];
  page.on("pageerror", error => page.runtimeErrors.push(error.message));
});

test.afterEach(async ({ page }) => {
  expect(page.runtimeErrors).toEqual([]);
});

// Exercise the real page/controllers and retained public data. Only the
// response ordering or failure under test is intercepted.
async function holdResponse(page, pattern, respond = route => route.continue()) {
  let release;
  let arrived;
  const gate = new Promise(resolve => { release = resolve; });
  const seen = new Promise(resolve => { arrived = resolve; });
  await page.route(pattern, async route => {
    arrived();
    await gate;
    await respond(route);
  });
  return { seen, release };
}

async function statisticsReady(page, format) {
  await expect(page.locator(`[data-format="${format}"]`)).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#view .composition-panel")).toBeVisible();
  await expect(page.locator("#view")).not.toHaveAttribute("aria-busy", "true");
}

test("late names only fill their own format cache", async ({ page }) => {
  await page.goto("/index.html?format=modern&product=mtgo-statistics&range=1&lang=en");
  await statisticsReady(page, "modern");
  const held = await holdResponse(page, "**/stats/pioneer/archetype_names.json");
  try {
    await page.locator('[data-format="pioneer"]').click();
    await held.seen;
    await page.locator('[data-format="standard"]').click();
    await statisticsReady(page, "standard");
    const content = await page.locator("#view").innerText();
    held.release();
    await expect.poll(() => page.evaluate(() => state.classifierNameContracts.has("pioneer"))).toBe(true);
    expect(await page.evaluate(() => state.classifierNameContract.format)).toBe("standard");
    expect(await page.locator("#view").innerText()).toBe(content);
    await expect(page).toHaveURL(/format=standard/);
  } finally { held.release(); }
});

test("interval failure shows the requested URL during loading and supports history and retry", async ({ page }) => {
  await page.goto("/index.html?format=pauper&product=mtgo-statistics&range=1&lang=en");
  await statisticsReady(page, "pauper");
  const path = "**/stats/pauper/mtgo/range_4w.json";
  const held = await holdResponse(page, path, route => route.fulfill({ status: 503, body: "failure" }));
  try {
    await page.locator('[data-stats-range="4"]').click();
    await held.seen;
    await expect(page).toHaveURL(/range=4/);
    await expect(page.locator("#payload-status")).toHaveText("Loading data…");
    await expect(page.locator("#view .composition-panel")).toHaveCount(0);
    held.release();
    await expect(page.locator("#view .error-state")).toBeVisible();
    await page.unroute(path);
    await page.locator("[data-retry-view]").click();
    await statisticsReady(page, "pauper");
    expect(await page.evaluate(() => currentContext.range.period.weeks)).toBe(4);
    await page.goBack();
    await statisticsReady(page, "pauper");
    await expect(page.locator('[data-stats-range="1"]')).toHaveClass("active");
    await page.goForward();
    await expect(page.locator('[data-stats-range="4"]')).toHaveClass("active");
  } finally { held.release(); }
});

test("first detail failure retains the same list and retries the missing deck resource", async ({ page }) => {
  await page.goto("/index.html?format=pauper&product=mtgo-statistics&range=1&lang=en");
  await statisticsReady(page, "pauper");
  const path = "**/stats/pauper/mtgo/decks_1w.json";
  await page.route(path, route => route.fulfill({ status: 503, body: "failure" }));
  await page.locator('button[data-detail-identity]:visible').first().click();
  await expect(page.locator("#view .inline-error-state")).toBeVisible();
  await expect(page.locator("#view .composition-panel")).toBeVisible();
  await expect(page.locator("#view .error-state")).toHaveCount(0);
  await page.unroute(path);
  await page.locator("[data-retry-view]").click();
  await expect(page.locator(".deck-detail-row:not(.load-error-row)")).toBeVisible();
  await expect(page.locator("#view .inline-error-state")).toHaveCount(0);
});

for (const failure of [false, true]) {
  test(`stale background refresh ${failure ? "failure" : "update"} does not affect the new view`, async ({ page }) => {
    await page.goto("/index.html?format=modern&product=mtgo-statistics&range=1&lang=en");
    await statisticsReady(page, "modern");
    const held = await holdResponse(page, "**/stats/modern/mtgo/range_1w.json", async route => {
      if (failure) return route.fulfill({ status: 503, body: "failure" });
      const response = await route.fetch();
      const document = await response.json();
      document.generated_at = "2026-10-24T23:59:00Z";
      await route.fulfill({ json: document });
    });
    try {
      await page.evaluate(() => { window.refreshDone = checkForUpdates(); });
      await held.seen;
      await page.locator('[data-format="standard"]').click();
      await statisticsReady(page, "standard");
      held.release();
      await page.evaluate(() => window.refreshDone);
      expect(await page.evaluate(() => state.pendingRefresh)).toBe(null);
      await expect(page.locator("#refresh-status")).toBeHidden();
      expect(await page.evaluate(() => currentContext.range.format)).toBe("standard");
    } finally { held.release(); }
  });
}

test("late matchup data cannot replace a statistics context", async ({ page }) => {
  await page.goto("/index.html?format=pauper&product=mtgo-statistics&range=1&lang=en");
  await statisticsReady(page, "pauper");
  const held = await holdResponse(page, "**/stats/pauper/mtgo/matchup_4w.json");
  try {
    await page.locator('[data-product="mtgo-matchups"]').click();
    await held.seen;
    await page.locator('[data-product="mtgo-statistics"]').click();
    await statisticsReady(page, "pauper");
    held.release();
    await page.evaluate(async () => { await MtgoController.loadMatchup("pauper", 4); });
    expect(await page.evaluate(() => Boolean(currentContext.range) && !currentContext.matchupDocument)).toBe(true);
    await expect(page).toHaveURL(/product=mtgo-statistics/);
  } finally { held.release(); }
});

test("same-view background update remains reviewable and can be applied", async ({ page }) => {
  await page.goto("/index.html?format=pauper&product=mtgo-statistics&range=1&lang=en");
  await statisticsReady(page, "pauper");
  const before = await page.evaluate(() => currentContext.range.generated_at);
  const stamp = "2026-10-24T23:59:00Z";
  await page.route("**/stats/pauper/mtgo/range_1w.json", async route => {
    const response = await route.fetch();
    await route.fulfill({ json: { ...await response.json(), generated_at: stamp } });
  });
  await page.evaluate(() => checkForUpdates());
  await expect(page.locator("[data-apply-refresh]")).toBeVisible();
  expect(await page.evaluate(() => currentContext.range.generated_at)).toBe(before);
  await page.locator("[data-apply-refresh]").click();
  await statisticsReady(page, "pauper");
  expect(await page.evaluate(() => currentContext.range.generated_at)).toBe(stamp);
  await expect(page.locator("#refresh-status")).toBeHidden();
});

test("late Landing load cannot change the statistics context or feature selection", async ({ page }) => {
  await page.goto("/index.html?format=pauper&product=mtgo-statistics&range=1&lang=en");
  await statisticsReady(page, "pauper");
  const held = await holdResponse(page, "**/stats/pauper/mtgo/landing/current.json");
  try {
    await page.locator('[data-product="mtgo-landing"]').click();
    await held.seen;
    await page.locator('[data-product="mtgo-statistics"]').click();
    await statisticsReady(page, "pauper");
    held.release();
    await page.evaluate(async () => { await MtgoController.loadLanding("pauper", "stats/pauper/mtgo/landing/current.json", null); });
    expect(await page.evaluate(() => Boolean(currentContext.range) && !currentContext.landing)).toBe(true);
    expect(await page.evaluate(() => state.landingFeatureWeekFile)).toBe(null);
    await expect(page).toHaveURL(/product=mtgo-statistics/);
  } finally { held.release(); }
});

test("late Top 8 week cannot change the selected week after history navigation", async ({ page }) => {
  await page.goto("/index.html?format=pauper&product=mtgo-top8&lang=en");
  await expect(page.locator("#top8-week")).toBeVisible();
  const original = await page.locator("#top8-week").inputValue();
  const other = await page.locator(`#top8-week option:not([value="${original}"])`).first().getAttribute("value");
  const held = await holdResponse(page, `**/stats/pauper/mtgo/top8/${other}`);
  try {
    await page.locator("#top8-week").selectOption(other);
    await held.seen;
    await page.goBack();
    await expect(page.locator("#top8-week")).toHaveValue(original);
    held.release();
    await page.evaluate(async file => { await MtgoController.loadTop8("stats/pauper/mtgo/top8/index.json", file); }, other);
    expect(await page.evaluate(() => state.top8WeekFile)).toBe(original);
    await expect(page.locator("#top8-week")).toHaveValue(original);
    await expect(page).toHaveURL(new RegExp(`week=${original.slice(0, -5)}`));
  } finally { held.release(); }
});

test("late Tabletop event cannot change the new format, event or URL", async ({ page }) => {
  await page.goto("/melee/index.html?format=modern&product=tabletop-major-events&view=overview&lang=en");
  await expect(page.locator("#tabletop-event")).toBeVisible();
  const original = await page.locator("#tabletop-event").inputValue();
  const other = await page.locator(`#tabletop-event option:not([value="${original}"])`).first().getAttribute("value");
  const held = await holdResponse(page, `**/stats/modern/melee/events/${other}/overview.json`);
  try {
    await page.locator("#tabletop-event").selectOption(other);
    await held.seen;
    await page.locator('[data-format="pauper"]').click();
    await expect(page.locator("#tabletop-event")).toBeVisible();
    await expect(page.locator("#view")).not.toHaveAttribute("aria-busy", "true");
    const expectedEvent = await page.locator("#tabletop-event").inputValue();
    held.release();
    await page.evaluate(async id => {
      await TabletopController.loadEvent("stats/modern/melee/index.json", id, "modern", MtgoController, { includeDecks: true });
    }, other);
    expect(await page.evaluate(() => [state.tabletopEventId, currentContext.eventEntry.event_id, state.classifierNameContract.format]))
      .toEqual([expectedEvent, expectedEvent, "pauper"]);
    await expect(page).toHaveURL(/format=pauper/);
    await expect(page).toHaveURL(new RegExp(`event=${expectedEvent}`));
  } finally { held.release(); }
});

test.describe("touch layout", () => {
test.use({ hasTouch: true });
test("mobile landing, statistics intervals and full confidence bounds keep their own meaning", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/index.html?format=pauper&product=mtgo-landing&lang=zh");
  await expect(page.locator(".landing-brief")).toBeVisible();
  await expect(page.locator(".landing-environment")).toContainText("本周");
  await page.locator('[data-product="mtgo-statistics"]').click();
  await statisticsReady(page, "pauper");
  await page.locator('[data-stats-range="12"]').click();
  await statisticsReady(page, "pauper");
  await expect(page.locator(".composition-heading")).toContainText("所选区间");
  await expect(page.locator(".composition-note")).not.toContainText("本周");
  await page.locator("#lang-en").click();
  await expect(page.locator(".composition-heading")).toContainText("selected-period");
  // A one-win Wilson interval is asymmetric about 100%. Display the supplied
  // endpoints, never infer them by adding/subtracting half-width from win rate.
  const label = await page.evaluate(() => {
    const table = document.createElement("table");
    table.innerHTML = `<tbody><tr>${matrixCell({ wins: 1, losses: 0, draws: 0, matches: 1,
      win_rate: 1, confidence_interval_95: { lower: 0.206543, upper: 1 } })}</tr></tbody>`;
    return table.querySelector("td").getAttribute("aria-label");
  });
  expect(label).toContain("95% confidence interval: 20.7%–100.0%");
  await page.locator('[data-product="mtgo-matchups"]').click();
  const cell = page.locator("[data-record]:visible").first();
  await cell.tap();
  await expect(page.locator("#matrix-record")).toHaveCount(0);
  await expect(page.locator("#matrix-hover-pop")).toBeInViewport();
  await expect(page.locator("#matrix-hover-pop")).toContainText("W-L-D:");
  await expect(page.locator("#matrix-hover-pop")).not.toContainText("confidence interval");
  const mobileBox = await page.locator("#matrix-hover-pop").boundingBox();
  expect(mobileBox.x + mobileBox.width).toBeLessThanOrEqual(390);
  await page.screenshot({ path: testInfo.outputPath("mobile-matchup.png") });
  await page.setViewportSize({ width: 1280, height: 900 });
  await cell.hover();
  await expect(page.locator("#matrix-hover-pop")).toContainText("W-L-D:");
  await expect(page.locator("#matrix-hover-pop")).not.toContainText("confidence interval");
  const box = await page.locator("#matrix-hover-pop").boundingBox();
  expect(box.x).toBeGreaterThanOrEqual(0);
  expect(box.x + box.width).toBeLessThanOrEqual(1280);
  await page.screenshot({ path: testInfo.outputPath("desktop-matchup.png") });
  await cell.blur();
  await cell.focus();
  await expect(page.locator("#matrix-hover-pop")).toBeInViewport();
  await page.locator('[data-product="mtgo-statistics"]').click();
  await statisticsReady(page, "pauper");
  await expect(page.locator("#matrix-hover-pop")).toBeHidden();
});
});

test("failed format switch removes the previous format and retry loads the requested one", async ({ page }) => {
  await page.goto("/index.html?format=modern&product=mtgo-statistics&range=1&lang=en");
  await statisticsReady(page, "modern");
  const path = "**/stats/standard/mtgo/range_1w.json";
  await page.route(path, route => route.fulfill({ status: 503, body: "temporary failure" }));
  await page.locator('[data-format="standard"]').click();
  await expect(page.locator("[data-retry-view]")).toBeVisible();
  await expect(page.locator("#view .composition-panel")).toHaveCount(0);
  await expect(page.locator("#view .error-state")).toBeVisible();
  await expect(page).toHaveURL(/format=standard/);
  await page.unroute(path);
  await page.locator("[data-retry-view]").click();
  await statisticsReady(page, "standard");
  expect(await page.evaluate(() => currentContext.range.format)).toBe("standard");
});

test("late statistics cannot replace the active context after history navigation", async ({ page }) => {
  await page.goto("/index.html?format=modern&product=mtgo-statistics&range=1&lang=en");
  await statisticsReady(page, "modern");
  const held = await holdResponse(page, "**/stats/modern/mtgo/range_4w.json");
  try {
    await page.locator('[data-stats-range="4"]').click();
    await held.seen;
    // A history event can occur while the content panel is inert. Returning
    // to the original interval also keeps both documents' names valid.
    await page.evaluate(() => {
      history.pushState(null, "", "?format=modern&product=mtgo-statistics&range=1&lang=en");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    await statisticsReady(page, "modern");
    const expectedRange = await page.evaluate(() => currentContext.range.period);
    held.release();
    await page.evaluate(async () => { await MtgoController.loadStatistics("modern", 4); });
    expect(await page.evaluate(() => currentContext.range.period)).toEqual(expectedRange);
    await expect(page).toHaveURL(/range=1/);
  } finally { held.release(); }
});
