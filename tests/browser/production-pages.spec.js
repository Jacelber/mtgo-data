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
