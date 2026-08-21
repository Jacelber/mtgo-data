"use strict";

const { expect, test } = require("@playwright/test");

async function expectPublishedNumber(page, metric) {
  await expect(page.locator("#view .loading-state")).toHaveCount(0);
  await expect(page.locator("#view .error-state")).toHaveCount(0);
  await expect(page.locator("#view .panel").first()).toBeVisible();
  await expect(page.locator(`[data-freshness-key="${metric}"]`)).toContainText(/\d/);
}

async function expectInViewport(locator) {
  await expect.poll(async () => locator.evaluate(element => {
    const rect = element.getBoundingClientRect();
    return rect.top < window.innerHeight && rect.bottom > 0;
  })).toBe(true);
}

async function expectedMainstreamParents(request, path, records, idKey, shareKey) {
  const response = await request.get(path);
  expect(response.ok()).toBe(true);
  const document = await response.json();
  return new Set(records(document)
    .filter(record => Number(record[shareKey]) >= 0.02)
    .map(record => record[idKey])
    .filter(id => id && id !== "unknown"));
}

async function expectKeyboardMatrixScrolling(page, path, viewport) {
  await page.setViewportSize(viewport);
  await page.goto(path);
  const scroller = page.locator(".matrix-scroll");
  const cell = page.locator(".matchup-table .matrix-cell[tabindex='0']").first();
  await expect(cell).toBeVisible();
  const before = await page.evaluate(() => {
    const matrix = document.querySelector(".matrix-scroll");
    const target = document.querySelector(".matchup-table .matrix-cell[tabindex='0']");
    matrix.scrollLeft = 0;
    target.focus({ preventScroll: true });
    return {
      columnWidth: target.getBoundingClientRect().width,
      rows: [...document.querySelectorAll("[data-matchup-row-identity]")]
        .map(row => row.dataset.matchupRowIdentity),
      columns: [...document.querySelectorAll("[data-matchup-column]")]
        .map(column => column.dataset.matchupColumn),
      expandedRows: document.querySelectorAll('[data-matchup-row-identity*="/"]').length,
      mainstream: document.querySelector("[data-matchup-mainstream]")?.checked ?? false,
      url: location.href,
    };
  });

  await cell.press("ArrowRight");
  await expect.poll(() => scroller.evaluate(element => element.scrollLeft))
    .toBeCloseTo(before.columnWidth, 0);
  await expect.poll(() => page.locator(".matrix-sticky-viewport").evaluate(
    element => element.scrollLeft
  )).toBeCloseTo(before.columnWidth, 0);
  expect(await cell.evaluate(element => document.activeElement === element)).toBe(true);

  await cell.press("ArrowLeft");
  await expect.poll(() => scroller.evaluate(element => element.scrollLeft)).toBe(0);
  expect(await cell.evaluate(element => document.activeElement === element)).toBe(true);

  const ignoredKeys = await cell.evaluate(element => {
    const dispatch = (key, modifiers = {}) => element.dispatchEvent(new KeyboardEvent(
      "keydown",
      { key, ...modifiers, bubbles: true, cancelable: true }
    ));
    return {
      up: dispatch("ArrowUp"),
      down: dispatch("ArrowDown"),
      altRight: dispatch("ArrowRight", { altKey: true }),
      ctrlRight: dispatch("ArrowRight", { ctrlKey: true }),
      metaRight: dispatch("ArrowRight", { metaKey: true }),
      shiftedRight: dispatch("ArrowRight", { shiftKey: true }),
    };
  });
  expect(ignoredKeys).toEqual({
    up: true,
    down: true,
    altRight: true,
    ctrlRight: true,
    metaRight: true,
    shiftedRight: true,
  });
  expect(await scroller.evaluate(element => element.scrollLeft)).toBe(0);

  expect(await page.evaluate(() => ({
    rows: [...document.querySelectorAll("[data-matchup-row-identity]")]
      .map(row => row.dataset.matchupRowIdentity),
    columns: [...document.querySelectorAll("[data-matchup-column]")]
      .map(column => column.dataset.matchupColumn),
    expandedRows: document.querySelectorAll('[data-matchup-row-identity*="/"]').length,
    mainstream: document.querySelector("[data-matchup-mainstream]")?.checked ?? false,
    url: location.href,
  }))).toEqual({
    rows: before.rows,
    columns: before.columns,
    expandedRows: before.expandedRows,
    mainstream: before.mainstream,
    url: before.url,
  });
}

test("MTGO page renders a published number", async ({ page }) => {
  await page.goto("/index.html?format=standard&product=mtgo-statistics&range=1&lang=en");
  await expectPublishedNumber(page, "decks");
});

test("Weekly Pickup renders an unavailable construction deviation as a dash", async ({ page }) => {
  await page.goto("/index.html?format=standard&product=weekly-pickup&lang=zh");
  await expect(page.locator(".pickup-card")).toHaveCount(11);
  const borosDragons = page.locator(".pickup-card", { hasText: "Boros Dragons" });
  await expect(borosDragons).toHaveCount(1);
  await expect(borosDragons.locator(".pickup-head")).toContainText("偏离度： —");
  await expect(page.locator(".pickup-content")).not.toContainText("null 分");
});

test("Tabletop page renders a published number", async ({ page }) => {
  await page.goto(
    "/melee/index.html?format=modern&product=tabletop-major-events&scope=all_constructed&lang=en"
  );
  await expectPublishedNumber(page, "scope-decks");
});

test("matchup matrices use Left and Right for one-column viewport movement", async ({ page }) => {
  await expectKeyboardMatrixScrolling(
    page,
    "/index.html?format=modern&product=mtgo-matchups&range=4&lang=en",
    { width: 800, height: 720 }
  );
  await expectKeyboardMatrixScrolling(
    page,
    "/melee/index.html?format=modern&product=tabletop-major-events&event=434455&view=matchup&scope=all_constructed&lang=en",
    { width: 375, height: 844 }
  );
});

test("MTGO matchup filter searches its tree and applies an exact multi-row subset", async ({ page }) => {
  let matchupRequests = 0;
  page.on("request", request => {
    if (request.url().includes("/stats/modern/mtgo/matchup_4w.json")) matchupRequests += 1;
  });
  await page.goto("/index.html?format=modern&product=mtgo-matchups&range=4&lang=en");
  await expect(page.locator("[data-matchup-filter-toggle]")).toBeVisible();
  await expect(page.locator(".matchup-table .row-head").first()).toBeVisible();
  await page.locator('[data-matchup-column="prowess"]').click();
  const initialColumnCount = await page.locator(".matchup-table .column-head:not(.overall)").count();
  const initialRowCount = await page.locator(".matchup-table .row-head").count();
  const initialRequests = matchupRequests;

  await page.locator("[data-matchup-filter-toggle]").click();
  await expect(page.locator("[data-matchup-filter-menu]")).toBeVisible();
  await expect(page.locator('[data-matchup-filter-parent="prowess"]')).toHaveAttribute("aria-expanded", "false");
  await page.locator('[data-matchup-filter-parent="prowess"]').click();
  await expect(page.locator('[data-matchup-filter-option="prowess/mono-red"]')).toBeVisible();
  await page.locator('[data-matchup-filter-parent="prowess"]').click();
  await expect(page.locator('[data-matchup-filter-option="prowess/mono-red"]')).toBeHidden();

  await page.locator("[data-matchup-filter-select-all]").uncheck();
  await page.locator("#matchup-filter-search").fill("  MONO-RED   prowess  ");
  await expect(page.locator('[data-matchup-filter-option="prowess/mono-red"]')).toBeVisible();
  await page.locator('[data-matchup-filter-option="prowess/mono-red"]').check();
  await page.locator("#matchup-filter-search").fill("boros energy");
  await page.locator('[data-matchup-filter-option="boros-energy"]').check();

  const scroller = page.locator(".matrix-scroll");
  await scroller.evaluate(element => element.scrollLeft = 180);
  await page.evaluate(() => window.scrollTo({ top: 200, behavior: "auto" }));
  const beforeApply = await page.evaluate(() => ({
    y: window.scrollY,
    left: document.querySelector(".matrix-scroll").scrollLeft,
  }));
  await page.locator("[data-matchup-filter-apply]").click();

  await expect(page.locator(".matchup-table .row-head")).toHaveCount(2);
  await expect(page.locator(".matchup-table .row-head").first()).toContainText("Boros Energy");
  await expect(page.locator(".matchup-table .row-head").nth(1)).toContainText("Mono-Red Prowess");
  await expect(page.locator("[data-matchup-focus]")).toHaveCount(0);
  await expect(page.locator(".matchup-table .column-head:not(.overall)"))
    .toHaveCount(initialColumnCount);
  expect(matchupRequests).toBe(initialRequests);
  await expect.poll(async () => page.evaluate(() => ({
    y: window.scrollY,
    left: document.querySelector(".matrix-scroll").scrollLeft,
  }))).toEqual(beforeApply);

  await page.locator("[data-matchup-filter-reset]").click();
  await expect(page.locator(".matchup-table .row-head")).toHaveCount(initialRowCount);
});

test("closing the matchup filter without Apply preserves the current rows", async ({ page }) => {
  await page.goto("/index.html?format=modern&product=mtgo-matchups&range=4&lang=en");
  await expect(page.locator(".matchup-table .row-head").first()).toBeVisible();
  const initialRows = await page.locator(".matchup-table .row-head").allTextContents();

  await page.locator("[data-matchup-filter-toggle]").click();
  await page.locator("[data-matchup-filter-select-all]").uncheck();
  await page.locator("#matchup-filter-search").fill("mono-red prowess");
  await page.locator('[data-matchup-filter-option="prowess/mono-red"]').check();
  await page.locator("[data-matchup-filter-cancel]").click();

  await expect(page.locator("[data-matchup-filter-menu]")).toBeHidden();
  expect(await page.locator(".matchup-table .row-head").allTextContents()).toEqual(initialRows);
});

test("MTGO mainstream matchups load share lazily and preserve hidden row selection", async ({ page, request }) => {
  const expectedParents = await expectedMainstreamParents(
    request,
    "/stats/modern/mtgo/range_4w.json",
    document => document.archetypes,
    "id",
    "high_score_share"
  );
  let rangeRequests = 0;
  let failRange = true;
  await page.route("**/stats/modern/mtgo/range_4w.json", async route => {
    rangeRequests += 1;
    if (failRange) await route.fulfill({ status: 503, body: "unavailable" });
    else await route.continue();
  });

  await page.goto("/index.html?format=modern&product=mtgo-matchups&range=4&lang=en");
  await expect(page.locator("[data-matchup-row-identity]").first()).toBeVisible();
  const initialRowIds = await page.locator("[data-matchup-row-identity]").evaluateAll(rows => (
    rows.map(row => row.dataset.matchupRowIdentity)
  ));
  const initialColumnCount = await page.locator(".matchup-table .column-head:not(.overall)").count();
  expect(rangeRequests).toBe(0);

  await page.locator("[data-matchup-mainstream]").check();
  await expect(page.locator(".matchup-mainstream-status")).toBeVisible();
  await expect(page.locator("[data-matchup-row-identity]")).toHaveCount(initialRowIds.length);
  await expect(page.locator(".matchup-table .column-head:not(.overall)"))
    .toHaveCount(initialColumnCount);
  expect(rangeRequests).toBe(1);

  failRange = false;
  await page.locator("[data-matchup-mainstream-retry]").click();
  await expect(page.locator(".matchup-mainstream-status")).toHaveCount(0);
  const expectedVisibleIds = initialRowIds.filter(id => expectedParents.has(id));
  const expectedHiddenIds = initialRowIds.filter(id => !expectedParents.has(id));
  expect(expectedVisibleIds.length).toBeGreaterThan(0);
  expect(expectedHiddenIds.length).toBeGreaterThan(0);
  const visibleRow = page.locator(
    `[data-matchup-row-identity=${JSON.stringify(expectedVisibleIds[0])}]`
  );
  const hiddenId = expectedHiddenIds[0];
  const hiddenRow = page.locator(
    `[data-matchup-row-identity=${JSON.stringify(hiddenId)}]`
  );
  await expect(page.locator("[data-matchup-row-identity]"))
    .toHaveCount(expectedVisibleIds.length);
  expect(await page.locator("[data-matchup-row-identity]").evaluateAll(rows => (
    rows.map(row => row.dataset.matchupRowIdentity)
  ))).toEqual(expectedVisibleIds);
  await expect(page.locator(".matchup-table .column-head:not(.overall)"))
    .toHaveCount(expectedVisibleIds.length);
  await expect(visibleRow).toBeVisible();
  await expect(hiddenRow).toHaveCount(0);
  expect(rangeRequests).toBe(2);

  await page.locator("[data-matchup-mainstream]").uncheck();
  await expect(page.locator("[data-matchup-row-identity]")).toHaveCount(initialRowIds.length);
  await page.locator("[data-matchup-filter-toggle]").click();
  await page.locator("[data-matchup-filter-select-all]").uncheck();
  const hiddenOption = page.locator(
    `[data-matchup-filter-option=${JSON.stringify(hiddenId)}]`
  );
  await expect(hiddenOption).toHaveCount(1);
  const hiddenName = await hiddenOption.evaluate(option => option.parentElement.textContent.trim());
  await page.locator("#matchup-filter-search").fill(hiddenName);
  await expect(hiddenOption).toBeVisible();
  await hiddenOption.check();
  await page.locator("[data-matchup-filter-apply]").click();
  await expect(hiddenRow).toBeVisible();

  await page.locator("[data-matchup-mainstream]").check();
  await expect(page.locator(".matchup-filter-empty")).toContainText(
    "contains no mainstream archetype"
  );
  expect(rangeRequests).toBe(2);
  await page.locator("[data-matchup-mainstream]").uncheck();
  await expect(hiddenRow).toBeVisible();
  expect(rangeRequests).toBe(2);
});

test("matrix names disclose parents and row leaves open a visible MTGO detail", async ({ page }) => {
  await page.goto("/index.html?format=modern&product=mtgo-matchups&range=4&lang=en");
  const expandable = page.locator('tr[data-matchup-row-identity="prowess"] [data-matchup-row="prowess"]');
  const expandableName = expandable.locator(".row-axis-name");
  const plainName = page.locator('tr[data-matchup-row-identity="boros-energy"] .row-axis-name');
  const alignment = await Promise.all([
    expandableName.evaluate(element => element.getBoundingClientRect().left),
    plainName.evaluate(element => element.getBoundingClientRect().left),
    expandable.evaluate(element => element.getBoundingClientRect().height),
  ]);
  expect(Math.abs(alignment[0] - alignment[1])).toBeLessThanOrEqual(1);
  expect(alignment[2]).toBeGreaterThanOrEqual(44);
  const desktopDetailLayout = await page.locator(
    'tr[data-matchup-row-identity="boros-energy"] .row-axis-detail-link'
  ).evaluate(link => {
    const name = link.querySelector(".row-axis-name").getBoundingClientRect();
    const icon = link.querySelector(".axis-detail-external").getBoundingClientRect();
    return { gap: icon.left - name.right };
  });
  expect(desktopDetailLayout.gap).toBeGreaterThanOrEqual(3);
  expect(desktopDetailLayout.gap).toBeLessThanOrEqual(5);

  await page.evaluate(() => {
    const row = document.querySelector('[data-matchup-row-identity="prowess"]');
    window.scrollTo({ top: window.scrollY + row.getBoundingClientRect().top - 320, behavior: "auto" });
  });
  const beforeDisclosure = await page.evaluate(() => ({
    y: window.scrollY,
    top: document.querySelector('[data-matchup-row="prowess"]').getBoundingClientRect().top,
  }));
  await expect(page.locator("[data-matrix-sticky]")).toHaveClass(/active/);
  await page.evaluate(() => {
    const view = document.querySelector("#view");
    const previousSticky = document.querySelector("[data-matrix-sticky]");
    window.__matrixStickyReplacement = null;
    const observer = new MutationObserver(() => {
      const replacement = document.querySelector("[data-matrix-sticky]");
      if (!replacement || replacement === previousSticky) return;
      window.__matrixStickyReplacement = {
        active: replacement.classList.contains("active"),
        visibility: getComputedStyle(replacement).visibility,
      };
      observer.disconnect();
    });
    observer.observe(view, { childList: true, subtree: true });
  });
  const disclosureBox = await expandable.boundingBox();
  await page.mouse.click(
    disclosureBox.x + (disclosureBox.width / 2),
    disclosureBox.y + (disclosureBox.height / 2)
  );
  await expect(page.locator('tr[data-matchup-row-identity="prowess/mono-red"]')).toBeVisible();
  await expect.poll(() => page.evaluate(() => window.__matrixStickyReplacement)).toEqual({
    active: true,
    visibility: "visible",
  });
  await expect.poll(async () => page.evaluate(() => ({
    y: window.scrollY,
    top: document.querySelector('[data-matchup-row="prowess"]').getBoundingClientRect().top,
  }))).toEqual(beforeDisclosure);

  const detailLink = page.locator('tr[data-matchup-row-identity="steel-cutter"] .row-axis-detail-link');
  const target = new URL(await detailLink.getAttribute("href"));
  expect(target.searchParams.get("product")).toBe("mtgo-statistics");
  expect(target.searchParams.get("range")).toBe("4");
  expect(target.searchParams.get("detail")).toBe("steel-cutter/izzet");
  await expect(detailLink).toHaveAttribute("target", "_blank");

  const popupPromise = page.waitForEvent("popup");
  await detailLink.click();
  const detailPage = await popupPromise;
  await expect(detailPage.locator(".deck-detail-row")).toBeVisible();
  await expectInViewport(detailPage.locator(".deck-detail-row"));
});

test("mobile matchup filter fits the viewport and does not move the page when applied", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 844 });
  await page.goto("/index.html?format=modern&product=mtgo-matchups&range=4&lang=zh");
  await expect(page.locator('[data-matchup-row-identity="prowess"]')).toBeVisible();
  await expect(page.locator('[data-matchup-row-identity="boros-energy"]')).toBeVisible();
  await expect(page.locator('[data-matchup-row-identity="mono-blue-belcher"] .row-axis-name'))
    .not.toHaveClass(/is-clipped/);
  await expect(page.locator('[data-matchup-row-identity="golgari-yawgmoth"] .row-axis-name'))
    .not.toHaveClass(/is-clipped/);
  await expect(page.locator("[data-matchup-mainstream]")).toBeVisible();
  const compactLayout = await page.evaluate(() => {
    const parentRow = document.querySelector('[data-matchup-row-identity="prowess"]');
    const plainRow = document.querySelector('[data-matchup-row-identity="boros-energy"]');
    const parentName = parentRow.querySelector(".row-axis-name").getBoundingClientRect();
    const plainName = plainRow.querySelector(".row-axis-name").getBoundingClientRect();
    const rowHead = parentRow.querySelector(".row-head").getBoundingClientRect();
    const scroller = document.querySelector(".matrix-scroll").getBoundingClientRect();
    const matrixCell = parentRow.querySelector(".matrix-cell").getBoundingClientRect();
    return {
      parentPlainDelta: Math.abs(parentName.left - plainName.left),
      parentInset: parentName.left - rowHead.left,
      rowHeadWidth: rowHead.width,
      visibleResultColumns: (scroller.right - rowHead.right) / matrixCell.width,
    };
  });
  expect(compactLayout.parentPlainDelta).toBeLessThanOrEqual(1);
  expect(compactLayout.parentInset).toBeLessThanOrEqual(25);
  expect(compactLayout.rowHeadWidth).toBeGreaterThanOrEqual(140);
  expect(compactLayout.visibleResultColumns).toBeGreaterThanOrEqual(3.25);
  expect(compactLayout.visibleResultColumns).toBeLessThanOrEqual(3.75);

  await page.locator('[data-matchup-row="prowess"]').click();
  await expect(page.locator('tr[data-matchup-row-identity="prowess/mono-red"]')).toBeVisible();
  const subtypeIndent = await page.evaluate(() => {
    const parent = document.querySelector('[data-matchup-row-identity="prowess"] .row-axis-name')
      .getBoundingClientRect();
    const subtype = document.querySelector('[data-matchup-row-identity="prowess/mono-red"] .row-axis-name')
      .getBoundingClientRect();
    return subtype.left - parent.left;
  });
  expect(subtypeIndent).toBeGreaterThanOrEqual(0);
  expect(subtypeIndent).toBeLessThanOrEqual(10);

  const compactDetailLayout = await page.locator(
    '[data-matchup-row-identity="golgari-yawgmoth"] .row-axis-detail-link'
  ).evaluate(link => {
    const name = link.querySelector(".row-axis-name").getBoundingClientRect();
    const icon = link.querySelector(".axis-detail-external").getBoundingClientRect();
    return { gap: icon.left - name.right };
  });
  expect(compactDetailLayout.gap).toBeGreaterThanOrEqual(3);
  expect(compactDetailLayout.gap).toBeLessThanOrEqual(5);

  await page.locator("[data-matchup-filter-toggle]").click();
  await expect(page.locator("[data-matchup-filter-menu]")).toBeVisible();
  const menuLayout = await page.locator("[data-matchup-filter-menu]").evaluate(menu => ({
    left: menu.getBoundingClientRect().left,
    right: menu.getBoundingClientRect().right,
    viewport: window.innerWidth,
    pageOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  }));
  expect(menuLayout.left).toBeGreaterThanOrEqual(0);
  expect(menuLayout.right).toBeLessThanOrEqual(menuLayout.viewport);
  expect(menuLayout.pageOverflow).toBe(0);

  await page.locator("[data-matchup-filter-select-all]").uncheck();
  await page.locator("#matchup-filter-search").fill("mono-red prowess");
  await page.locator('[data-matchup-filter-option="prowess/mono-red"]').check();
  await page.evaluate(() => window.scrollTo({ top: 200, behavior: "auto" }));
  const beforeY = await page.evaluate(() => window.scrollY);
  await page.locator("[data-matchup-filter-apply]").click();
  await expect(page.locator(".matchup-table .row-head")).toHaveCount(1);
  await expect(page.locator(".matchup-table .row-head").first()).toContainText("Mono-Red Prowess");
  await expect.poll(async () => page.evaluate(() => window.scrollY)).toBe(beforeY);
  expect(await page.locator("html").evaluate(element => element.scrollWidth - element.clientWidth)).toBe(0);

  const detailLink = page.locator(".matchup-table .row-axis-detail-link");
  const popupPromise = page.waitForEvent("popup");
  await detailLink.click();
  const detailPage = await popupPromise;
  await detailPage.setViewportSize({ width: 375, height: 844 });
  await detailPage.reload();
  const mobileDetail = detailPage.locator('[data-mobile-expanded-content="stats:prowess/mono-red"]');
  await expect(mobileDetail).toBeVisible();
  await expectInViewport(mobileDetail);
});

test("Tabletop matchup uses the same hierarchical exact-row filter", async ({ page }) => {
  await page.goto(
    "/melee/index.html?format=modern&product=tabletop-major-events&event=434455&view=matchup&scope=all_constructed&lang=zh"
  );
  await page.locator("[data-matchup-filter-toggle]").click();
  await page.locator("[data-matchup-filter-select-all]").uncheck();
  await page.locator("#matchup-filter-search").fill("mono-green broodscale");
  await page.locator('[data-matchup-filter-option="broodscale-combo/mono-green"]').check();
  await page.locator("[data-matchup-filter-apply]").click();

  await expect(page.locator(".matchup-table .row-head")).toHaveCount(1);
  await expect(page.locator(".matchup-table .row-head").first()).toContainText(
    "Mono-Green Broodscale Combo"
  );
  const detailLink = page.locator(".matchup-table .row-axis-detail-link");
  const target = new URL(await detailLink.getAttribute("href"));
  expect(target.searchParams.get("view")).toBe("overview");
  expect(target.searchParams.get("event")).toBe("434455");
  expect(target.searchParams.get("scope")).toBe("all_constructed");
  expect(target.searchParams.get("detail")).toBe("broodscale-combo/mono-green");

  const popupPromise = page.waitForEvent("popup");
  await detailLink.click();
  const detailPage = await popupPromise;
  await expect(detailPage.locator(".deck-detail-row")).toBeVisible();
  await expectInViewport(detailPage.locator(".deck-detail-row"));
});

test("Tabletop mainstream matchups reuse the active-scope Overview", async ({ page, request }) => {
  const expectedParents = await expectedMainstreamParents(
    request,
    "/stats/modern/melee/events/434455/overview.json",
    document => document.scopes.all_constructed.archetypes,
    "archetype_id",
    "metagame_share"
  );
  let overviewRequests = 0;
  page.on("request", requestEvent => {
    if (requestEvent.url().includes("/stats/modern/melee/events/434455/overview.json")) {
      overviewRequests += 1;
    }
  });
  await page.goto(
    "/melee/index.html?format=modern&product=tabletop-major-events&event=434455&view=matchup&scope=all_constructed&lang=en"
  );
  await expect(page.locator("[data-matchup-row-identity]").first()).toBeVisible();
  const initialRowIds = await page.locator("[data-matchup-row-identity]").evaluateAll(rows => (
    rows.map(row => row.dataset.matchupRowIdentity)
  ));
  const requestsAfterLoad = overviewRequests;
  const expectedVisibleIds = initialRowIds.filter(id => expectedParents.has(id));

  await page.locator("[data-matchup-mainstream]").check();
  await expect(page.locator("[data-matchup-row-identity]"))
    .toHaveCount(expectedVisibleIds.length);
  expect(await page.locator("[data-matchup-row-identity]").evaluateAll(rows => (
    rows.map(row => row.dataset.matchupRowIdentity)
  ))).toEqual(expectedVisibleIds);
  await expect(page.locator(".matchup-table .column-head:not(.overall)"))
    .toHaveCount(expectedVisibleIds.length);
  expect(overviewRequests).toBe(requestsAfterLoad);

  await page.locator("[data-matchup-mainstream]").uncheck();
  await expect(page.locator("[data-matchup-row-identity]")).toHaveCount(initialRowIds.length);
  expect(overviewRequests).toBe(requestsAfterLoad);
});
