"use strict";

const { expect, test } = require("@playwright/test");

async function expectNoPageOverflow(page) {
  expect(await page.evaluate(() => (
    document.documentElement.scrollWidth <= document.documentElement.clientWidth
  ))).toBe(true);
}

async function openMobile(page, path, width = 390) {
  await page.setViewportSize({ width, height: 844 });
  await page.goto(path);
  await expect(page.locator("#view .loading-state, #view .error-state")).toHaveCount(0);
}

for (const language of ["zh", "en"]) {
  for (const width of [390, 412]) {
    test(`MTGO cards expose every metric at ${width}px in ${language}`, async ({ page }) => {
      await openMobile(
        page,
        `/index.html?format=modern&product=mtgo-statistics&lang=${language}`,
        width
      );
      await expect(page.locator(".desktop-metric-table")).toBeHidden();
      await expect(page.locator(".mobile-metric-layout")).toBeVisible();
      const card = page.locator(".mobile-metric-card").first();
      await expect(card.locator("h3")).not.toBeEmpty();
      await expect(card.locator(".mobile-metric dt")).toHaveCount(6);
      await expect(card.locator(".mobile-metric dd")).toHaveCount(6);
      const action = page.locator(".mobile-card-action").first();
      expect((await action.boundingBox()).height).toBeGreaterThanOrEqual(44);
      await expectNoPageOverflow(page);
    });

    test(`Tabletop cards expose every metric at ${width}px in ${language}`, async ({ page }) => {
      await openMobile(
        page,
        `/melee/index.html?format=modern&product=tabletop-major-events&lang=${language}`,
        width
      );
      await expect(page.locator(".desktop-metric-table")).toBeHidden();
      await expect(page.locator(".mobile-metric-layout")).toBeVisible();
      const card = page.locator(".mobile-metric-card").first();
      await expect(card.locator("h3")).not.toBeEmpty();
      await expect(card.locator(".mobile-metric dt")).toHaveCount(6);
      await expect(card.locator(".mobile-metric dd")).toHaveCount(6);
      await expect(card.locator(".mobile-primary-metrics small")).toHaveCount(2);
      await expectNoPageOverflow(page);
    });
  }
}

test("mobile stats sorting, expansion, detail visibility, and focus share existing state", async ({ page }) => {
  await openMobile(page, "/index.html?format=modern&product=mtgo-statistics&lang=en");
  const sort = page.locator("[data-mobile-stats-sort]");
  await sort.selectOption("name");
  await expect(page).toHaveURL(/sort=name&dir=asc/);
  await expect(sort).toBeFocused();
  await page.locator("[data-mobile-stats-direction]").click();
  await expect(page).toHaveURL(/sort=name&dir=desc/);
  await expect(page.locator("[data-mobile-stats-direction]")).toBeFocused();
  await expect(page.locator("#payload-status")).toContainText("Sorted by");

  const toggle = page.locator("[data-mobile-stats-toggle]").first();
  const parentId = await toggle.getAttribute("data-mobile-stats-toggle");
  await toggle.click();
  await expect(page.locator(`[data-mobile-stats-toggle="${parentId}"]`)).toBeFocused();
  await expect(page.locator(`#stats-mobile-subtypes-${parentId}`)).toBeVisible();

  const detailAction = page.locator("[data-mobile-stats-detail]").last();
  const identity = await detailAction.getAttribute("data-mobile-stats-detail");
  await detailAction.scrollIntoViewIfNeeded();
  await detailAction.click();
  await expect(page.locator(`[data-mobile-stats-detail="${identity}"]`)).toBeFocused();
  const detail = page.locator(`[data-mobile-expanded-content="stats:${identity}"]`);
  await expect(detail).toBeVisible();
  expect((await detail.boundingBox()).y).toBeLessThan(844);
  expect(new URL(page.url()).searchParams.get("detail")).toBe(identity);
  await detail.locator("[data-close-mobile-stats-detail]").click();
  await expect(page.locator(`[data-mobile-stats-detail="${identity}"]`)).toBeFocused();
  await expect(page.locator(".mobile-card-detail")).toHaveCount(0);
});

test("mobile Tabletop sorting and deck detail preserve focus and URL", async ({ page }) => {
  await openMobile(page, "/melee/index.html?format=modern&product=tabletop-major-events&lang=en", 412);
  const sort = page.locator("[data-mobile-tabletop-sort]");
  await sort.selectOption("metagame_share");
  await expect(page).toHaveURL(/sort=metagame_share&dir=desc/);
  await expect(sort).toBeFocused();
  await page.locator("[data-mobile-tabletop-direction]").click();
  await expect(page).toHaveURL(/sort=metagame_share&dir=asc/);
  await expect(page.locator("[data-mobile-tabletop-direction]")).toBeFocused();

  const detailAction = page.locator("[data-mobile-tabletop-detail]").first();
  const identity = await detailAction.getAttribute("data-mobile-tabletop-detail");
  await detailAction.click();
  await expect(page.locator(`[data-mobile-tabletop-detail="${identity}"]`)).toBeFocused();
  await expect(page.locator(`[data-mobile-expanded-content="tabletop:${identity}"]`)).toBeVisible();
  expect(new URL(page.url()).searchParams.get("detail")).toBe(identity);
  await page.locator("[data-close-mobile-tabletop-detail]").click();
  await expect(page.locator(`[data-mobile-tabletop-detail="${identity}"]`)).toBeFocused();
});

test("780px boundary transfers focus and expansion state without changing layout semantics", async ({ page }) => {
  await openMobile(page, "/index.html?format=modern&product=mtgo-statistics&lang=en", 780);
  const mobileToggle = page.locator("[data-mobile-stats-toggle]").first();
  const parentId = await mobileToggle.getAttribute("data-mobile-stats-toggle");
  await mobileToggle.click();
  await page.locator(`[data-mobile-stats-toggle="${parentId}"]`).focus();
  await page.setViewportSize({ width: 781, height: 844 });
  const desktopToggle = page.locator(`[data-stats-toggle="${parentId}"]`);
  await expect(page.locator(".mobile-metric-layout")).toBeHidden();
  await expect(page.locator(".desktop-metric-table")).toBeVisible();
  await expect(desktopToggle).toHaveAttribute("aria-expanded", "true");
  await expect(desktopToggle).toBeFocused();
});

for (const product of ["mtgo-matchups", "mtgo-top8"]) {
  test(`${product} retains a sticky first column and dismissible horizontal hint`, async ({ page }) => {
    const width = product === "mtgo-matchups" ? 375 : 390;
    await openMobile(page, `/index.html?format=modern&product=${product}&lang=en`, width);
    const frame = page.locator(".horizontal-scroll-frame").first();
    const scroller = frame.locator("[data-scroll-hint-key]");
    await expect(frame.locator(".horizontal-scroll-hint")).toBeVisible();
    expect(await scroller.evaluate(node => node.scrollWidth > node.clientWidth)).toBe(true);
    const firstCell = product === "mtgo-top8"
      ? scroller.locator(".top8-week-table th:first-child")
      : scroller.locator(".matchup-table .row-head").first();
    await expect(firstCell).toHaveCSS("position", "sticky");
    if (product === "mtgo-matchups") {
      const compactLayout = await scroller.evaluate(node => {
        const rowHead = node.querySelector(".matchup-table .row-head");
        const dataCell = node.querySelector(".matchup-table .matrix-cell");
        const expandableName = node.querySelector(".row-axis-label .row-axis-name");
        const staticName = node.querySelector(".row-head > .row-axis-name");
        const plus = node.querySelector(".row-axis-label .axis-toggle");
        const textLeft = element => {
          const range = document.createRange();
          range.selectNodeContents(element);
          return range.getClientRects()[0]?.left;
        };
        return {
          rowShare: rowHead.getBoundingClientRect().width / node.clientWidth,
          visibleDataColumns: (
            node.clientWidth - rowHead.getBoundingClientRect().width
          ) / dataCell.getBoundingClientRect().width,
          whiteSpace: getComputedStyle(rowHead.querySelector("span")).whiteSpace,
          nameStartDelta: Math.abs(textLeft(expandableName) - textLeft(staticName)),
          plusBorder: getComputedStyle(plus).borderTopWidth,
          plusRadius: getComputedStyle(plus).borderRadius,
        };
      });
      expect(compactLayout.rowShare).toBeLessThanOrEqual(0.4);
      expect(compactLayout.visibleDataColumns).toBeGreaterThanOrEqual(3.5);
      expect(compactLayout.whiteSpace).toBe("normal");
      expect(compactLayout.nameStartDelta).toBeLessThan(1);
      expect(compactLayout.plusBorder).toBe("0px");
      expect(compactLayout.plusRadius).toBe("0px");
      const clippedName = scroller.locator(".row-axis-name.is-clipped").first();
      await expect(clippedName).toBeVisible();
      expect(await clippedName.evaluate(node => getComputedStyle(node, "::after").content)).toContain("…");
      expect(await clippedName.getAttribute("title")).toBe(await clippedName.textContent());
    }
    await scroller.evaluate(node => { node.scrollLeft = 120; });
    await expect(frame).toHaveClass(/hint-dismissed/);
  });
}

for (const width of [375, 1200]) {
  test(`matchup opponent header remains visible while scrolling at ${width}px`, async ({ page }) => {
    await openMobile(page, "/index.html?format=modern&product=mtgo-matchups&lang=zh", width);
    const frame = page.locator(".horizontal-scroll-frame").first();
    const scroller = frame.locator(".matrix-scroll");
    const sticky = frame.locator("[data-matrix-sticky]");
    await expect(sticky).not.toHaveClass(/active/);

    const scrollTarget = await scroller.evaluate(node => (
      node.getBoundingClientRect().top + window.scrollY + 180
    ));
    await page.evaluate(y => window.scrollTo(0, y), scrollTarget);
    await expect(sticky).toHaveClass(/active/);
    const stickyViewport = sticky.locator(".matrix-sticky-viewport");
    await expect(stickyViewport).toBeVisible();
    expect(Math.abs(await stickyViewport.evaluate(node => (
      node.getBoundingClientRect().top
    )))).toBeLessThan(1);
    await expect(sticky.locator(".column-head")).toHaveCount(
      await scroller.locator("thead .column-head").count()
    );

    await scroller.evaluate(node => { node.scrollLeft = 120; });
    await expect.poll(() => stickyViewport.evaluate(node => (
      node.scrollLeft
    ))).toBe(120);
  });
}

test("Weekly Pickup keeps the secondary metric on its own narrow line", async ({ page }) => {
  await openMobile(page, "/index.html?format=standard&product=weekly-pickup&lang=en", 390);
  const heading = page.locator(".pickup-head").first();
  const metric = heading.locator("b");
  const boxes = await Promise.all([heading.boundingBox(), metric.boundingBox()]);
  expect(Math.abs(boxes[1].x - boxes[0].x)).toBeLessThan(20);
  await expectNoPageOverflow(page);
});
