"use strict";

const { expect, test } = require("@playwright/test");

const languages = ["zh", "en"];
const viewports = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile", width: 390, height: 844 },
];

async function expectLoaded(page, { language, format, product, surface }) {
  await expect(page.locator("html")).toHaveAttribute("data-surface", surface);
  await expect(page.locator("html")).toHaveAttribute(
    "lang",
    language === "zh" ? "zh-CN" : "en"
  );
  await expect(page.locator(`#lang-${language}`)).toHaveClass(/active/);
  await expect(page.locator(`[data-format="${format}"]`)).toHaveClass(/active/);
  await expect(page.locator(`[data-product="${product}"]`)).toHaveClass(/active/);
  await expect(page.locator("#view .loading-state")).toHaveCount(0);
  await expect(page.locator("#view .error-state")).toHaveCount(0);
  await expect(page.locator("#view .panel").first()).toBeVisible();
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
