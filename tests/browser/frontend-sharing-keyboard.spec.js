"use strict";
const { expect, test } = require("@playwright/test");

const statistics = "/index.html?format=pauper&product=mtgo-statistics&range=4&lang=en";
const matrix = "/index.html?format=pauper&product=mtgo-matchups&range=4&lang=en";
const tabletop = "/melee/index.html?format=modern&product=tabletop-major-events&event=405588&view=matchup&lang=en";
async function ready(page, selector = "[data-share-view]") {
  await expect(page.locator(selector).first()).toBeVisible();
  await expect(page.locator("#view")).not.toHaveAttribute("aria-busy", "true");
  await expect(page.locator("[data-share-view]")).toBeEnabled();
  await expect(page.locator("#view .error-state")).toHaveCount(0);
}
async function copy(page) {
  await page.locator("[data-share-view]").click();
  await expect(page.locator("#share-status")).toHaveText(/Link copied|链接已复制/);
  return page.evaluate(() => copiedViewLink);
}
test.beforeEach(async ({ page }) => {
  page.errors = [];
  page.on("pageerror", error => page.errors.push(error.message));
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: {
      writeText: async value => { globalThis.copiedViewLink = value; },
    } });
  });
});
test.afterEach(async ({ page }) => expect(page.errors).toEqual([]));

test("matrix sharing restores mainstream and independent row/column expansion; history restores defaults", async ({ page }) => {
  await page.goto(matrix);
  await ready(page, "[data-record]");
  await page.locator("[data-matchup-mainstream]").check();
  await ready(page);
  const row = page.locator("[data-matchup-row]").first();
  const rowId = await row.getAttribute("data-matchup-row");
  await row.click();
  await expect(page).toHaveURL(/rows=/);
  const column = page.locator("[data-matchup-column]").first();
  const columnId = await column.getAttribute("data-matchup-column");
  await column.click();
  const link = await copy(page);
  const query = new URL(link).searchParams;
  expect(query.get("mainstream")).toBe("1");
  expect(query.get("rows")).toBe(rowId);
  expect(query.get("cols")).toBe(columnId);
  await page.goto(link);
  await ready(page, "[data-record]");
  expect(await page.evaluate(() => ({ rows: [...state.matchupRows], columns: [...state.matchupColumns], main: state.matchupMainstreamOnly })))
    .toEqual({ rows: [rowId], columns: [columnId], main: true });
  await page.locator("[data-matchup-mainstream]").uncheck();
  await ready(page);
  await page.goBack();
  await ready(page);
  await expect(page.locator("[data-matchup-mainstream]")).toBeChecked();
  await page.goForward();
  await ready(page);
  await expect(page.locator("[data-matchup-mainstream]")).not.toBeChecked();
});

test("filter selection survives a shared link; Escape discards a draft and restores focus", async ({ page }) => {
  await page.goto(matrix);
  await ready(page, "[data-record]");
  await page.locator("[data-matchup-filter-toggle]").click();
  await page.locator("[data-matchup-filter-select-all]").uncheck();
  const option = page.locator("[data-matchup-filter-option]:visible").first();
  const id = await option.getAttribute("data-matchup-filter-option");
  await option.check();
  await page.locator("[data-matchup-filter-apply]").click();
  await ready(page);
  const link = await copy(page);
  expect(new URL(link).searchParams.get("filter")).toBe(id);
  await page.goto(link);
  await ready(page);
  expect(await page.evaluate(() => [...state.matchupFilterIdentities])).toEqual([id]);
  await page.locator("[data-matchup-filter-toggle]").click();
  await page.locator("[data-matchup-filter-select-all]").check();
  await page.keyboard.press("Escape");
  await expect(page.locator("[data-matchup-filter-menu]")).toBeHidden();
  await expect(page.locator("[data-matchup-filter-toggle]")).toBeFocused();
  expect(await page.evaluate(() => [...state.matchupFilterIdentities])).toEqual([id]);
});

test("statistics shares detail identity and representative mode, then Escape returns to its trigger", async ({ page }) => {
  await page.goto(statistics);
  await ready(page, ".composition-panel");
  const trigger = page.locator("button[data-detail-identity]:visible").first();
  const id = await trigger.getAttribute("data-detail-identity");
  await trigger.press("Enter");
  await ready(page, ".deck-detail-row");
  await page.locator('[data-deck-mode="typical"]:visible').first().click();
  await ready(page);
  const link = await copy(page);
  expect(new URL(link).searchParams.get("detail")).toBe(id);
  expect(new URL(link).searchParams.get("mode")).toBe("typical");
  await page.goto(link);
  await ready(page, ".deck-detail-row");
  await expect(page.locator('[data-deck-mode="typical"]:visible').first()).toHaveClass("active");
  await page.locator('[data-deck-mode="typical"]:visible').first().focus();
  await page.keyboard.press("Escape");
  await ready(page);
  await expect(page.locator(".deck-detail-row")).toHaveCount(0);
  await expect(page.locator(`button[data-detail-identity="${id}"]:visible`).first()).toBeFocused();
  expect(new URL(page.url()).searchParams.has("detail")).toBe(false);
});

test("Tabletop shared link restores multiple events, scope, language and filter", async ({ page }) => {
  await page.goto(tabletop);
  await ready(page, "[data-record]");
  await page.locator('[data-tabletop-event-check="405590"]').check();
  await ready(page);
  await page.locator("[data-matchup-filter-toggle]").click();
  await page.locator("[data-matchup-filter-select-all]").uncheck();
  const option = page.locator("[data-matchup-filter-option]:visible").first();
  const id = await option.getAttribute("data-matchup-filter-option");
  await option.check();
  await page.locator("[data-matchup-filter-apply]").click();
  await ready(page);
  const link = await copy(page);
  expect(new URL(link).searchParams.get("events")).toBe("405588,405590");
  await page.goto(link);
  await ready(page);
  expect(await page.evaluate(() => ({ events: [...state.tabletopSelectedEvents], scope: state.tabletopScope, filter: [...state.matchupFilterIdentities] })))
    .toEqual({ events: ["405588", "405590"], scope: "all_constructed", filter: [id] });
});

test("matrix keyboard moves cells in both directions with one tab stop and dismisses the tooltip", async ({ page }) => {
  await page.goto(matrix);
  await ready(page, "[data-record]");
  const cells = page.locator(".matrix-cell[data-record]");
  await expect(page.locator('.matrix-cell[tabindex="0"]')).toHaveCount(1);
  await cells.first().focus();
  const origin = await cells.first().getAttribute("data-matrix-cell");
  await page.keyboard.press("ArrowRight");
  const right = await page.evaluate(() => document.activeElement.dataset.matrixCell);
  expect(right).not.toBe(origin);
  expect(right.split("|")[0]).toBe(origin.split("|")[0]);
  await page.keyboard.press("ArrowDown");
  const down = await page.evaluate(() => document.activeElement.dataset.matrixCell);
  expect(down.split("|")[1]).toBe(right.split("|")[1]);
  expect(down.split("|")[0]).not.toBe(right.split("|")[0]);
  await expect(page.locator('.matrix-cell[tabindex="0"]')).toHaveCount(1);
  await expect(page.locator("#matrix-hover-pop")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator("#matrix-hover-pop")).toBeHidden();
  await page.keyboard.press("Home");
  expect(await page.evaluate(() => document.activeElement.dataset.matrixCell.split("|")[1])).toBe("overall");
});

test("clipboard denial offers a selected readable link without false success", async ({ page }) => {
  await page.goto(statistics);
  await ready(page);
  await page.evaluate(() => { navigator.clipboard.writeText = async () => { throw new Error("denied"); }; });
  await page.locator("[data-share-view]").click();
  await expect(page.locator("#share-status")).toHaveText("Copy the link below");
  await expect(page.locator("#share-link")).toBeFocused();
  await expect(page.locator("#share-fallback")).toBeInViewport();
  expect(await page.locator("#share-link").inputValue()).toBe(page.url());
  await page.keyboard.press("Escape");
  await expect(page.locator("#share-link")).toBeHidden();
  await expect(page.locator("#share-fallback")).toBeHidden();
  await expect(page.locator("[data-share-view]")).toBeFocused();
});

test("header link stays beside language on desktop and below on narrow screens", async ({ page }) => {
  for (const path of [statistics, "/melee/index.html?format=modern&product=tabletop-major-events&event=405588&view=overview&lang=en"]) {
    await page.goto(path);
    await ready(page);
    for (const width of [1280, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      const language = await page.locator(".lang-switch").boundingBox();
      const button = await page.locator("[data-share-view]").boundingBox();
      if (width > 780) {
        expect(button.x).toBeGreaterThanOrEqual(language.x + language.width);
        expect(button.y).toBeLessThan(language.y + language.height);
      } else {
        expect(button.y).toBeGreaterThanOrEqual(language.y + language.height);
        expect(button.width).toBe(44);
        expect(button.height).toBe(44);
      }
      expect(button.x + button.width).toBeLessThanOrEqual(width);
      await expect(page.locator(".view-share")).toHaveCount(0);
      await page.evaluate(() => { navigator.clipboard.writeText = async () => { throw new Error("denied"); }; });
      await page.locator("[data-share-view]").click();
      await expect(page.locator("#share-fallback")).toBeInViewport();
      const panel = await page.locator("#share-fallback").boundingBox();
      expect(panel.x).toBeGreaterThanOrEqual(0);
      expect(panel.x + panel.width).toBeLessThanOrEqual(width);
      await page.keyboard.press("Escape");
    }
  }
});

test("copy uses a temporary checkmark and language changes retain the icon", async ({ page }) => {
  await page.goto(statistics);
  await ready(page);
  const button = page.locator("[data-share-view]");
  await button.click();
  await expect(button.locator(".share-check")).toBeVisible();
  await expect(button).toHaveAttribute("aria-label", "Link copied");
  await expect(page.locator("#share-fallback")).toBeHidden();
  await expect(button.locator(".share-chain")).toBeVisible({ timeout: 4000 });
  await page.locator("#lang-zh").click();
  await ready(page);
  await expect(button).toHaveAttribute("aria-label", "复制当前视图链接");
  await expect(button.locator(".share-chain")).toBeVisible();
  await button.click();
  await expect(button.locator(".share-check")).toBeVisible();
  await expect(page.locator("#share-status")).toHaveText("链接已复制");
});

test("unavailable route identities and malformed filter state are discarded", async ({ page }) => {
  await page.goto(matrix + "&filter=%3Cscript%3E&rows=no-such-parent&cols=no-such-parent&mainstream=no");
  await ready(page, "[data-record]");
  const query = new URL(await copy(page)).searchParams;
  for (const key of ["filter", "rows", "cols", "mainstream"]) expect(query.has(key)).toBe(false);
});

test("mobile statistics keeps expanded identity in the copied route", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/index.html?format=modern&product=mtgo-statistics&range=4&lang=zh");
  await ready(page);
  const toggle = page.locator("[data-mobile-stats-toggle]:visible").first();
  const id = await toggle.getAttribute("data-mobile-stats-toggle");
  await toggle.click();
  const link = await copy(page);
  expect(new URL(link).searchParams.get("expanded")).toContain(id);
  await page.goto(link);
  await ready(page);
  expect(await page.evaluate(id => state.statsExpanded.has(id), id)).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test("Top 8 shares the selected week and exact placement", async ({ page }) => {
  await page.goto("/index.html?format=pauper&product=mtgo-top8&lang=en");
  await ready(page, "[data-top8-detail]");
  const button = page.locator("[data-top8-detail]:visible").first();
  const id = await button.getAttribute("data-top8-detail");
  await button.press("Enter");
  await ready(page, "[data-close-top8]");
  const link = await copy(page);
  expect(new URL(link).searchParams.get("detail")).toBe(id);
  expect(new URL(link).searchParams.get("week")).toMatch(/^\d{4}-W\d{2}$/);
  await page.goto(link);
  await ready(page, "[data-close-top8]");
  expect(await page.evaluate(() => state.top8Detail)).toBe(id);
});

test("Landing shares a featured deck destination and returns to its open content", async ({ page }) => {
  await page.goto("/index.html?format=pauper&product=mtgo-landing&lang=en");
  await ready(page, "[data-landing-feature-toggle]");
  const button = page.locator("[data-landing-feature-toggle]").first();
  const id = await button.getAttribute("data-landing-feature-toggle");
  await button.press("Enter");
  await ready(page);
  const link = await copy(page);
  const query = new URL(link).searchParams;
  expect(query.get("feature")).toBe(id);
  expect(query.get("section")).toBe("features");
  await page.goto(link);
  await ready(page);
  await expect(page.locator(`.landing-feature-toggle[data-landing-feature-toggle="${id}"]`)).toHaveAttribute("aria-expanded", "true");
  await page.locator(`.deck-close[data-landing-feature-toggle="${id}"]`).focus();
  await page.keyboard.press("Escape");
  await ready(page);
  await expect(page.locator(`.landing-feature-toggle[data-landing-feature-toggle="${id}"]`)).toHaveAttribute("aria-expanded", "false");
  await expect(page.locator(`.landing-feature-toggle[data-landing-feature-toggle="${id}"]`)).toBeFocused();
});

test("Tabletop overview shares detail mode and closes to the same identity", async ({ page }) => {
  await page.goto(tabletop.replace("view=matchup", "view=overview"));
  await ready(page, "[data-tabletop-detail]");
  const button = page.locator("[data-tabletop-detail]:visible").first();
  const id = await button.getAttribute("data-tabletop-detail");
  await button.press("Enter");
  await ready(page, "[data-close-tabletop-detail]");
  await page.locator('[data-deck-mode="typical"]:visible').first().click();
  await ready(page);
  const link = await copy(page);
  expect(new URL(link).searchParams.get("detail")).toBe(id);
  expect(new URL(link).searchParams.get("mode")).toBe("typical");
  await page.goto(link);
  await ready(page, "[data-close-tabletop-detail]");
  await expect(page.locator('[data-deck-mode="typical"]:visible').first()).toHaveClass("active");
  await page.locator('[data-close-tabletop-detail]:visible').focus();
  await page.keyboard.press("Escape");
  await ready(page);
  await expect(page.locator(`[data-tabletop-detail="${id}"]:visible`)).toBeFocused();
});
