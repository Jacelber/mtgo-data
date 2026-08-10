"use strict";

const { expect, test } = require("@playwright/test");

const languages = ["zh", "en"];
const viewports = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile-390", width: 390, height: 844 },
  { name: "mobile-412", width: 412, height: 915 },
];

async function expectLoaded(page, { language, format, product, surface }) {
  await expect(page.locator("html")).toHaveAttribute("data-surface", surface);
  await expect(page.locator("html")).toHaveAttribute(
    "lang",
    language === "zh" ? "zh-CN" : "en"
  );
  await expect(page.locator(`#lang-${language}`)).toHaveClass(/active/);
  await expect(page.locator(`#lang-${language}`)).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(`[data-format="${format}"]`)).toHaveClass(/active/);
  await expect(page.locator(`[data-product="${product}"]`)).toHaveClass(/active/);
  await expect(page.locator("#view .loading-state")).toHaveCount(0);
  await expect(page.locator("#view .error-state")).toHaveCount(0);
  await expect(page.locator("#view .panel").first()).toBeVisible();
  await expect(page.locator(".cat-brand-watermark")).toHaveAttribute("aria-hidden", "true");
  await expect(page.locator(".cat-brand-watermark img")).toBeVisible();
  expect(await page.evaluate(() => (
    document.documentElement.scrollWidth <= document.documentElement.clientWidth
  ))).toBe(true);

  const shellStyles = await page.evaluate(() => {
    const languageButton = document.querySelector(".lang-switch button");
    const formatButton = document.querySelector(".format-tabs button");
    const productButton = document.querySelector(".product-tabs button.active");
    return {
      languageBorder: getComputedStyle(languageButton).borderTopWidth,
      formatRadius: Number.parseFloat(getComputedStyle(formatButton).borderTopLeftRadius),
      productBorder: Number.parseFloat(getComputedStyle(productButton).borderBottomWidth),
    };
  });
  expect(shellStyles.languageBorder).toBe("0px");
  expect(shellStyles.formatRadius).toBeGreaterThan(15);
  expect(shellStyles.productBorder).toBeGreaterThanOrEqual(3);
}

for (const language of languages) {
  for (const viewport of viewports) {
    for (const format of ["standard", "modern"]) {
      test(`MTGO ${format} ${language} ${viewport.name}`, async ({ page }) => {
        const errors = [];
        page.on("pageerror", error => errors.push(error.message));
        await page.setViewportSize(viewport);
        await page.goto(`/index.html?format=${format}&product=mtgo-statistics&lang=${language}`);
        await expectLoaded(page, {
          language,
          format,
          product: "mtgo-statistics",
          surface: "mtgo",
        });
        await expect(page.locator(".composition-panel")).toBeVisible();
        await expect(page.locator(".composition-heading h2")).toHaveText(
          language === "zh" ? "高分牌表环境构成" : "High-score deck environment composition"
        );
        expect(await page.locator(".composition-segment").count()).toBeGreaterThan(1);
        await expect(page.locator(".composition-legend")).toHaveCount(0);
        await expect(page.locator(".pie-panel, .pie-card, .pie-slice")).toHaveCount(0);
        const visibleStats = viewport.width <= 780 ? ".mobile-metric-layout" : ".desktop-metric-table";
        await expect(page.locator(`${visibleStats} .mana-identity`).first()).toBeVisible();
        await expect(page.locator(`${visibleStats} .mana-identity img`).first()).toHaveAttribute(
          "src",
          /assets\/images\/mana\/[wubrgc]\.svg$/
        );
        expect(errors).toEqual([]);
      });
    }

    test(`Tabletop Modern ${language} ${viewport.name}`, async ({ page }) => {
      const errors = [];
      page.on("pageerror", error => errors.push(error.message));
      await page.setViewportSize(viewport);
      await page.goto(`/melee/index.html?format=modern&product=tabletop-major-events&lang=${language}`);
      await expectLoaded(page, {
        language,
        format: "modern",
        product: "tabletop-major-events",
        surface: "tabletop",
      });
      expect(errors).toEqual([]);
    });

    test(`unavailable Tabletop Standard redirects ${language} ${viewport.name}`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await page.goto(`/melee/index.html?format=standard&product=tabletop-major-events&lang=${language}`);
      await expect(page).toHaveURL(/\/index\.html\?format=standard&product=mtgo-statistics&lang=(zh|en)$/);
      await expectLoaded(page, {
        language,
        format: "standard",
        product: "mtgo-statistics",
        surface: "mtgo",
      });
    });
  }
}

test("MTGO subtype rows use explicit mana symbols", async ({ page }) => {
  await page.goto("/index.html?format=modern&product=mtgo-statistics&lang=zh");
  const esper = page.locator('button[data-detail-identity="goryos-reanimator/esper"]');
  await expect(esper).toBeVisible();
  await expect(esper.locator(".mana-identity")).toHaveAttribute(
    "aria-label",
    "法术力颜色：白、蓝、黑"
  );
  await expect(esper.locator(".mana-identity img")).toHaveCount(3);
});

test("Standard composition uses card art and opens detail from one desktop click", async ({ page }) => {
  await page.goto("/index.html?format=standard&product=mtgo-statistics&range=1&lang=en");
  const segment = page.locator('[data-composition-identity="izzet-prowess"]');
  await expect(segment).toHaveAttribute("data-tooltip", /Izzet Prowess .* 16\.2%/);
  await expect(segment).not.toHaveAttribute("data-tooltip", /Boomerang Basics/);
  const backgroundImage = await segment.evaluate(node => getComputedStyle(node).backgroundImage);
  expect(backgroundImage).toContain("boomerang-basics.jpg");
  const imageUrl = backgroundImage.match(/url\("([^"]*boomerang-basics\.jpg)"\)/)[1];
  expect((await page.request.get(imageUrl)).ok()).toBe(true);
  await segment.click();
  await expect(page).toHaveURL(/detail=izzet-prowess/);
  await expect(page.locator('[data-stats-parent="izzet-prowess"]').locator("xpath=ancestor::tr/following-sibling::tr[1]"))
    .toHaveClass(/deck-detail-row/);
});

test("desktop composition reveals an off-screen detail after rendering settles", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto("/index.html?format=modern&product=mtgo-statistics&range=1&lang=en");
  const segment = page.locator('[data-composition-identity="ruby-storm"]');
  await segment.click();
  await expect(page).toHaveURL(/detail=ruby-storm/);
  const detailClose = page.locator('[data-responsive-key="stats-detail:ruby-storm:close"]')
    .filter({ visible: true });
  await expect(detailClose).toBeVisible();
  await expect.poll(() => detailClose.evaluate(node => {
    const rect = node.getBoundingClientRect();
    return rect.top < window.innerHeight && rect.bottom > 0;
  })).toBe(true);
});

for (const width of [390, 412]) {
  test(`mobile ${width} composition keeps disclosure until the same item is tapped again`, async ({ page }) => {
    const requests = [];
    page.on("request", request => requests.push(new URL(request.url()).pathname));
    await page.addInitScript(() => {
      const original = Element.prototype.scrollIntoView;
      window.__scrollIntoViewCalls = [];
      Element.prototype.scrollIntoView = function scrollIntoView(options) {
        window.__scrollIntoViewCalls.push(options);
        return original.call(this, options);
      };
    });
    await page.setViewportSize({ width, height: width === 412 ? 915 : 844 });
    await page.goto("/index.html?format=standard&product=mtgo-statistics&range=1&lang=en");
    const segments = page.locator("button.composition-segment");
    const first = segments.nth(0);
    const second = segments.nth(1);
    const identity = await second.getAttribute("data-composition-identity");
    const decksPath = "/stats/standard/mtgo/decks_1w.json";

    await first.click();
    await expect(first).toHaveClass(/touch-active/);
    await expect(page).not.toHaveURL(/detail=/);
    expect(requests).not.toContain(decksPath);

    await second.click();
    await expect(first).not.toHaveClass(/touch-active/);
    await expect(second).toHaveClass(/touch-active/);
    await expect(page).not.toHaveURL(/detail=/);
    expect(requests).not.toContain(decksPath);

    await page.waitForTimeout(1900);
    await second.click();
    await expect(page).toHaveURL(new RegExp(`detail=${identity}`));
    await expect(page.locator(`[data-stats-parent="${identity}"]`).locator("xpath=ancestor::tr/following-sibling::tr[1]"))
      .toHaveClass(/deck-detail-row/);
    const mobileDetail = page.locator(`[data-mobile-expanded-content="stats:${identity}"]`);
    await expect(mobileDetail).toBeVisible();
    await expect.poll(() => mobileDetail.evaluate(node => {
      const rect = node.getBoundingClientRect();
      return rect.top < window.innerHeight && rect.bottom > 0;
    })).toBe(true);
    expect(requests.filter(path => path === decksPath)).toHaveLength(1);
    await expect.poll(() => page.evaluate(() => window.__scrollIntoViewCalls.at(-1)?.behavior))
      .toBe("smooth");
  });
}

test("mobile statistics expands rows without rebuilding the view and preserves anchors", async ({ page }) => {
  const requests = [];
  page.on("request", request => requests.push(new URL(request.url()).pathname));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/index.html?format=modern&product=mtgo-statistics&range=1&lang=en");
  await expect(page.locator("#view .panel").first()).toBeVisible();
  await page.evaluate(() => {
    window.__loadingInsertions = 0;
    new MutationObserver(records => {
      records.flatMap(record => [...record.addedNodes]).forEach(node => {
        if (!(node instanceof Element)) return;
        if (node.matches(".loading-state") || node.querySelector(".loading-state")) {
          window.__loadingInsertions += 1;
        }
      });
    }).observe(document.querySelector("#view"), { childList: true, subtree: true });
    document.querySelector(".composition-panel").dataset.renderMarker = "preserved";
  });

  const toggle = page.locator("button[data-mobile-stats-toggle]").first();
  await toggle.scrollIntoViewIfNeeded();
  const beforeToggleTop = await toggle.evaluate(node => node.getBoundingClientRect().top);
  const jsonRequestCount = requests.filter(path => path.endsWith(".json")).length;
  await toggle.click();
  await expect(page.locator(".mobile-subtype-list").first()).toBeVisible();
  const afterToggleTop = await page.locator("button[data-mobile-stats-toggle]").first()
    .evaluate(node => node.getBoundingClientRect().top);
  expect(Math.abs(afterToggleTop - beforeToggleTop)).toBeLessThan(2);
  expect(requests.filter(path => path.endsWith(".json"))).toHaveLength(jsonRequestCount);
  expect(await page.evaluate(() => window.__loadingInsertions)).toBe(0);
  await expect(page.locator('.composition-panel[data-render-marker="preserved"]')).toBeVisible();

  const expandAll = page.locator("#stats-expand-all");
  await expandAll.scrollIntoViewIfNeeded();
  const beforeExpandAllTop = await expandAll.evaluate(node => node.getBoundingClientRect().top);
  await expandAll.click();
  const afterExpandAllTop = await expandAll.evaluate(node => node.getBoundingClientRect().top);
  expect(Math.abs(afterExpandAllTop - beforeExpandAllTop)).toBeLessThan(2);
  expect(await page.evaluate(() => window.__loadingInsertions)).toBe(0);

  const sort = page.locator("[data-mobile-stats-sort]");
  await sort.scrollIntoViewIfNeeded();
  const beforeSortTop = await sort.evaluate(node => node.getBoundingClientRect().top);
  await sort.selectOption("name");
  await expect(sort).toBeFocused();
  const afterSortTop = await sort.evaluate(node => node.getBoundingClientRect().top);
  expect(Math.abs(afterSortTop - beforeSortTop)).toBeLessThan(2);
  expect(await page.evaluate(() => window.__loadingInsertions)).toBe(0);

  const detail = page.locator("button[data-mobile-stats-detail]").first();
  await detail.click();
  await expect(page.locator(".mobile-card-detail")).toBeVisible();
  const close = page.locator("button[data-close-mobile-stats-detail]");
  await close.scrollIntoViewIfNeeded();
  const detailIdentity = await detail.getAttribute("data-mobile-stats-detail");
  const restoredDetail = page.locator(`button[data-mobile-stats-detail="${detailIdentity}"]`);
  const beforeCloseTop = await restoredDetail.evaluate(node => node.getBoundingClientRect().top);
  await close.click();
  await expect(page.locator(".mobile-card-detail")).toHaveCount(0);
  await expect(restoredDetail).toBeFocused();
  const afterCloseTop = await restoredDetail.evaluate(node => node.getBoundingClientRect().top);
  expect(Math.abs(afterCloseTop - beforeCloseTop)).toBeLessThan(2);
  expect(await page.evaluate(() => window.__loadingInsertions)).toBe(0);
});

test("each product shows only its own freshness facts", async ({ page }) => {
  await page.goto("/index.html?format=standard&product=mtgo-statistics&range=1&lang=en");
  await expect(page.locator('.freshness-strip')).toHaveAttribute("aria-label", "Data status");
  await expect(page.locator('[data-freshness-key="high-score-completeness"]')).toContainText("136 / 139 · 97.9%");
  await expect(page.locator('[data-freshness-key="decks"]')).toContainText("285");
  await expect(page.locator('[data-freshness-key="matchup-coverage"]')).toHaveCount(0);

  await page.goto("/index.html?format=standard&product=mtgo-matchups&range=1&lang=en");
  await expect(page.locator('[data-freshness-key="matchup-coverage"]')).toContainText("9 / 9 · 100.0%");
  await expect(page.locator('[data-freshness-key="missing-events"]')).toContainText("0");
  await expect(page.locator('[data-freshness-key="high-score-completeness"]')).toHaveCount(0);

  await page.goto("/index.html?format=standard&product=mtgo-top8&lang=en");
  await expect(page.locator('[data-freshness-key="events"]')).toContainText("9");
  await expect(page.locator('[data-freshness-key="placements"]')).toContainText("72");
  await expect(page.locator('[data-freshness-key="available-decks"]')).toContainText("72");
  await expect(page.locator("#view")).not.toContainText(/provisional|sealed/i);

  await page.goto("/index.html?format=standard&product=weekly-pickup&lang=en");
  await expect(page.locator('[data-freshness-key="week"]')).toContainText("2026-06-29 – 2026-07-05");
  await expect(page.locator('[data-freshness-key="featured-decks"]')).toContainText("1");
  await expect(page.locator('[data-freshness-key="events"]')).toHaveCount(0);

  await page.goto("/melee/index.html?format=modern&product=tabletop-major-events&scope=all_constructed&lang=en");
  await expect(page.locator('[data-freshness-key="event-date"]')).toContainText("2026-07-17 – 2026-07-19");
  await expect(page.locator('[data-freshness-key="selected-events"]')).toContainText("1");
  await expect(page.locator('[data-freshness-key="scope-decks"]')).toContainText("362");
  await expect(page.locator('[data-freshness-key="submitted-decks"]')).toContainText("362");
  await expect(page.locator('[data-freshness-key="unavailable-decks"]')).toContainText("0");
  await expect(page.locator('[data-freshness-key="high-score-completeness"]')).toHaveCount(0);
});

test("unavailable freshness values render as Unknown rather than zero", async ({ page }) => {
  await page.route("**/stats/standard/mtgo/completeness/1w.json", async route => {
    const response = await route.fetch();
    const body = await response.json();
    body.high_score_decklist_completeness.status = "unavailable";
    body.high_score_decklist_completeness.expected_decklist_count = null;
    body.high_score_decklist_completeness.expected_decklist_count_display = null;
    body.high_score_decklist_completeness.completeness_rate = null;
    await route.fulfill({ response, json: body });
  });
  await page.goto("/index.html?format=standard&product=mtgo-statistics&range=1&lang=en");
  const fact = page.locator('[data-freshness-key="high-score-completeness"]');
  await expect(fact).toContainText("136 / Unknown · Unknown");
  await expect(fact).not.toContainText("0 / 0");
});

test("freshness facts move together below the title only when needed", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/index.html?format=standard&product=mtgo-statistics&range=1&lang=zh");
  const strip = page.locator(".freshness-strip");
  await strip.locator(".freshness-fact").evaluateAll(facts => {
    facts.slice(1).forEach(fact => { fact.style.display = "none"; });
  });
  await page.evaluate(() => window.dispatchEvent(new Event("resize")));
  await expect(strip).not.toHaveClass(/freshness-stacked/);

  await strip.locator(".freshness-fact").evaluateAll(facts => {
    facts.forEach(fact => { fact.style.removeProperty("display"); });
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(strip).toHaveClass(/freshness-stacked/);
  const positions = await strip.evaluate(element => {
    const titleBox = element.querySelector(".freshness-title").getBoundingClientRect();
    const factsBox = element.querySelector(".freshness-facts").getBoundingClientRect();
    return {
      titleLeft: titleBox.left,
      titleBottom: titleBox.bottom,
      factsLeft: factsBox.left,
      factsTop: factsBox.top,
    };
  });
  expect(Math.abs(positions.factsLeft - positions.titleLeft)).toBeLessThan(1);
  expect(positions.factsTop).toBeGreaterThanOrEqual(positions.titleBottom);
});
