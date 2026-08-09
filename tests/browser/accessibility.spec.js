"use strict";

const { expect, test } = require("@playwright/test");

const routes = [
  ["statistics", "/index.html?format=modern&product=mtgo-statistics&lang=en"],
  ["matchups", "/index.html?format=modern&product=mtgo-matchups&lang=en"],
  ["top8", "/index.html?format=modern&product=mtgo-top8&lang=en"],
  ["pickup", "/index.html?format=standard&product=weekly-pickup&lang=en"],
  ["tabletop", "/melee/index.html?format=modern&product=tabletop-major-events&lang=en"],
];

async function expectLoaded(page) {
  await expect(page.locator("#view .loading-state")).toHaveCount(0);
  await expect(page.locator("#view .error-state")).toHaveCount(0);
  await expect(page.locator(".freshness-strip")).toBeVisible();
}

function channel(value) {
  const normalized = value / 255;
  return normalized <= 0.04045
    ? normalized / 12.92
    : ((normalized + 0.055) / 1.055) ** 2.4;
}

function luminance(color) {
  const values = color.match(/[\d.]+/g).slice(0, 3).map(Number);
  return (0.2126 * channel(values[0]))
    + (0.7152 * channel(values[1]))
    + (0.0722 * channel(values[2]));
}

function contrast(foreground, background) {
  const light = Math.max(luminance(foreground), luminance(background));
  const dark = Math.min(luminance(foreground), luminance(background));
  return (light + 0.05) / (dark + 0.05);
}

test("product routes expose named regions and a useful heading outline", async ({ page }) => {
  for (const [name, route] of routes) {
    await page.goto(route);
    await expectLoaded(page);
    await expect(page.locator("header")).toHaveCount(1);
    await expect(page.locator("main")).toHaveCount(1);
    await expect(page.locator("footer")).toHaveCount(1);
    await expect(page.locator("h1")).toHaveCount(1);
    expect(await page.locator("h2").count(), `${name} needs a view heading`).toBeGreaterThan(0);
    await expect(page.locator("#view")).toHaveJSProperty("tagName", "DIV");

    const unnamedSections = await page.locator("section").evaluateAll(sections => (
      sections.filter(section => (
        !section.hasAttribute("aria-label")
        && !section.hasAttribute("aria-labelledby")
        && !section.querySelector("h1,h2,h3,h4,h5,h6")
      )).map(section => section.className || "section")
    ));
    expect(unnamedSections, `${name} has unnamed sections`).toEqual([]);
  }
});

test("unavailable navigation explains itself without changing state", async ({ page }) => {
  for (const language of ["zh", "en"]) {
    await page.goto(`/index.html?format=modern&product=mtgo-statistics&lang=${language}`);
    await expectLoaded(page);
    const unavailable = page.locator('.format-tabs [aria-disabled="true"]').first();
    const descriptionId = await unavailable.getAttribute("aria-describedby");
    expect(descriptionId).toBeTruthy();
    await expect(page.locator(`#${descriptionId}`)).not.toHaveText("");

    await unavailable.focus();
    const url = page.url();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(url);
    await expect(page.locator("#availability-message")).not.toHaveText("");
    await expect(unavailable).toBeFocused();
  }
});

test("key text and non-chart controls meet the compact accessibility floor", async ({ page }) => {
  const viewports = [
    { width: 390, height: 844 },
    { width: 412, height: 915 },
  ];
  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    for (const [name, route] of routes) {
      await page.goto(route);
      await expectLoaded(page);
      const failures = await page.evaluate(() => {
        const visible = element => {
          const style = getComputedStyle(element);
          const box = element.getBoundingClientRect();
          return style.display !== "none" && style.visibility !== "hidden" && box.width > 0 && box.height > 0;
        };
        return [...document.querySelectorAll("button,a[href],select,[tabindex]")]
          .filter(element => (
            visible(element)
            && (!element.hasAttribute("tabindex") || element.getAttribute("tabindex") === "0")
            && !element.matches(".composition-segment,.matrix-cell")
            && !element.matches('input[type="checkbox"]')
          ))
          .map(element => {
            const box = element.getBoundingClientRect();
            return {
              label: (element.getAttribute("aria-label") || element.textContent || element.tagName).trim().replace(/\s+/g, " ").slice(0, 60),
              width: box.width,
              height: box.height,
            };
          })
          .filter(item => item.width < 24 || item.height < 24);
      });
      expect(failures, `${name} has undersized controls at ${viewport.width}px`).toEqual([]);

      const sizes = await page.evaluate(() => ({
        body: parseFloat(getComputedStyle(document.body).fontSize),
        format: parseFloat(getComputedStyle(document.querySelector(".format-tabs button")).fontSize),
        product: parseFloat(getComputedStyle(document.querySelector(".product-tabs button")).fontSize),
        language: parseFloat(getComputedStyle(document.querySelector(".lang-switch button")).fontSize),
        freshness: parseFloat(getComputedStyle(document.querySelector(".freshness-strip")).fontSize),
        source: document.querySelector(".source-note")
          ? parseFloat(getComputedStyle(document.querySelector(".source-note")).fontSize)
          : 13,
      }));
      expect(sizes.body).toBeGreaterThanOrEqual(16);
      expect(sizes.format).toBeGreaterThanOrEqual(13);
      expect(sizes.product).toBeGreaterThanOrEqual(13);
      expect(sizes.language).toBeGreaterThanOrEqual(12);
      expect(sizes.freshness).toBeGreaterThanOrEqual(13);
      expect(sizes.source).toBeGreaterThanOrEqual(13);
    }
  }
});

test("critical text and focus indicators meet contrast targets", async ({ page }) => {
  await page.goto("/index.html?format=modern&product=mtgo-statistics&lang=en");
  await expectLoaded(page);
  const language = page.locator(".lang-switch button:not(.active)").first();
  const languageStyle = await language.evaluate(element => {
    const style = getComputedStyle(element);
    return { color: style.color, opacity: Number(style.opacity) };
  });
  expect(languageStyle.opacity).toBe(1);
  expect(contrast(languageStyle.color, "rgb(143, 72, 39)")).toBeGreaterThanOrEqual(4.5);

  const dataButton = page.locator(".name-button").first();
  await dataButton.focus();
  const dataFocus = await dataButton.evaluate(element => getComputedStyle(element).outlineColor);
  expect(contrast(dataFocus, "rgb(255, 255, 255)")).toBeGreaterThanOrEqual(3);

  await language.focus();
  const headerFocus = await language.evaluate(element => getComputedStyle(element).outlineColor);
  expect(contrast(headerFocus, "rgb(143, 72, 39)")).toBeGreaterThanOrEqual(3);

  const tip = page.locator(".tip").first();
  const tipColors = await tip.evaluate(element => {
    const style = getComputedStyle(element, "::before");
    return { color: style.color, background: style.backgroundColor };
  });
  expect(contrast(tipColors.color, tipColors.background)).toBeGreaterThanOrEqual(4.5);

  await page.goto("/index.html?format=modern&product=mtgo-matchups&lang=en");
  await expectLoaded(page);
  const naColors = await page.locator(".matrix-cell.na").first().evaluate(element => {
    const style = getComputedStyle(element);
    return { color: style.color, background: style.backgroundColor };
  });
  expect(contrast(naColors.color, naColors.background)).toBeGreaterThanOrEqual(4.5);

  await page.goto("/index.html?format=modern&product=mtgo-top8&lang=en");
  await expectLoaded(page);
  const eventMeta = await page.locator(".top8-week-table th small").first().evaluate(element => {
    const style = getComputedStyle(element);
    return { color: style.color, background: getComputedStyle(element.closest("th")).backgroundColor };
  });
  expect(contrast(eventMeta.color, eventMeta.background)).toBeGreaterThanOrEqual(4.5);
});

test("accessible icon targets keep compact visual glyphs", async ({ page }) => {
  await page.goto("/index.html?format=modern&product=mtgo-statistics&lang=zh");
  await expectLoaded(page);
  await page.locator("#stats-expand-all").click();

  const visual = await page.evaluate(() => {
    const tip = document.querySelector(".tip");
    const tipTarget = tip.getBoundingClientRect();
    const tipGlyph = getComputedStyle(tip, "::before");
    const toggle = document.querySelector(".identity-cell .round-toggle");
    const mana = toggle.closest("button").querySelector(".mana-identity");
    const toggleRect = toggle.getBoundingClientRect();
    const manaRect = mana.getBoundingClientRect();
    return {
      tipTarget: [tipTarget.width, tipTarget.height],
      tipGlyph: [parseFloat(tipGlyph.width), parseFloat(tipGlyph.height)],
      toggle: [toggleRect.width, toggleRect.height],
      gap: manaRect.left - toggleRect.right,
    };
  });

  expect(visual.tipTarget[0]).toBeGreaterThanOrEqual(24);
  expect(visual.tipTarget[1]).toBeGreaterThanOrEqual(24);
  expect(visual.tipGlyph).toEqual([16, 16]);
  expect(visual.toggle).toEqual([18, 18]);
  expect(visual.gap).toBeGreaterThanOrEqual(2);
});

test("numeric headers align with values while tips and sort arrows float", async ({ page }) => {
  await page.goto("/index.html?format=standard&product=mtgo-statistics&range=1&sort=high_score_share&dir=asc&lang=zh");
  await expectLoaded(page);

  const alignment = await page.evaluate(() => {
    const textRight = element => {
      const range = document.createRange();
      range.selectNodeContents(element);
      return range.getBoundingClientRect().right;
    };
    const headers = [...document.querySelectorAll(".metric-columns th.number")];
    const values = [...document.querySelectorAll(".metric-columns tbody tr:not(.deck-detail-row):first-child td.number")];
    return headers.map((header, index) => {
      const label = header.querySelector(".sort-label");
      const accessories = [...header.querySelectorAll(".sort-indicator, .tip")];
      const labelRight = textRight(label);
      return {
        delta: Math.abs(labelRight - textRight(values[index])),
        accessoryGaps: accessories.map(item => item.getBoundingClientRect().left - labelRight),
      };
    });
  });

  for (const column of alignment) {
    expect(column.delta).toBeLessThanOrEqual(1);
    for (const gap of column.accessoryGaps) expect(gap).toBeGreaterThanOrEqual(2);
    if (column.accessoryGaps.length) expect(column.accessoryGaps[0]).toBeLessThanOrEqual(6);
  }
});

test("rerendered controls retain focus and detail buttons expose expansion", async ({ page }) => {
  await page.goto("/index.html?format=modern&product=mtgo-statistics&lang=en");
  await expectLoaded(page);
  const detailButton = page.locator("button[data-detail-identity]").first();
  const identity = await detailButton.getAttribute("data-detail-identity");
  await expect(detailButton).toHaveAttribute("aria-expanded", "false");
  await detailButton.click();
  await expect(page.locator(".deck-detail")).toBeVisible();
  await expect(page.locator(`button[data-detail-identity="${identity}"]`)).toHaveAttribute("aria-expanded", "true");
  await expect(page.locator(`button[data-detail-identity="${identity}"]`)).toBeFocused();

  await page.locator("[data-close-detail]").click();
  await expect(page.locator(".deck-detail")).toHaveCount(0);
  await expect(page.locator(`button[data-detail-identity="${identity}"]`)).toBeFocused();

  const sort = page.locator("button[data-stats-sort]").first();
  const sortKey = await sort.getAttribute("data-stats-sort");
  await sort.click();
  await expect(page.locator(`button[data-stats-sort="${sortKey}"]`)).toBeFocused();
});

test("composition segments are independent controls and reduced motion is honored", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/index.html?format=standard&product=mtgo-statistics&range=1&lang=en");
  await expectLoaded(page);
  await expect(page.locator(".composition-bar")).not.toHaveAttribute("role", "img");
  const segments = page.locator("button.composition-segment");
  expect(await segments.count()).toBeGreaterThan(1);
  for (const segment of await segments.all()) {
    await expect(segment).toHaveAttribute("type", "button");
    await expect(segment).toHaveAttribute("aria-label", /\d+\.\d+%/);
  }
  const residuals = page.locator("span.composition-segment");
  for (const residual of await residuals.all()) {
    await expect(residual.locator("button,a,[tabindex]")).toHaveCount(0);
  }
  const duration = await segments.first().evaluate(element => (
    parseFloat(getComputedStyle(element).transitionDuration)
  ));
  expect(duration).toBeLessThanOrEqual(0.001);

  const first = segments.first();
  await expect(first).toHaveAttribute("aria-expanded", "false");
  await first.click();
  await expect(page.locator(".deck-detail")).toBeVisible();
  await expect(page.locator("button.composition-segment[aria-expanded=true]")).toBeFocused();
});

test("mobile composition uses non-animated navigation when reduced motion is requested", async ({ page }) => {
  await page.addInitScript(() => {
    const original = Element.prototype.scrollIntoView;
    window.__scrollIntoViewCalls = [];
    Element.prototype.scrollIntoView = function scrollIntoView(options) {
      window.__scrollIntoViewCalls.push(options);
      return original.call(this, options);
    };
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/index.html?format=standard&product=mtgo-statistics&range=1&lang=en");
  const segment = page.locator("button.composition-segment").first();
  await segment.click();
  await segment.click();
  await expect(page.locator(".mobile-deck-detail")).toBeVisible();
  await expect.poll(() => page.evaluate(() => window.__scrollIntoViewCalls.at(-1)?.behavior))
    .toBe("auto");
});
