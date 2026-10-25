"use strict";

const { expect, test } = require("@playwright/test");

for (const [product, path] of [
  ["MTGO", "/index.html?format=modern&product=mtgo-matchups&range=36"],
  ["Tabletop", "/melee/index.html?format=modern&product=tabletop-major-events&event=405588&view=matchup"],
]) {
  for (const lang of ["zh", "en"]) {
    test(`${product} ${lang} multicolor column labels stay inside their column`, async ({ page }) => {
      await page.goto(`${path}&lang=${lang}`);
      await expect(page.locator(".matchup-table [data-record]").first()).toBeVisible();
      for (const width of [1280, 390]) {
        await page.setViewportSize({ width, height: 900 });
        // Check both the original heading and the floating copy after scrolling.
        for (const floating of [false, true]) {
          await page.evaluate(floating => {
            const table = document.querySelector(".matchup-table");
            window.scrollTo(0, floating ? table.getBoundingClientRect().top + window.scrollY + 180 : 0);
          }, floating);
          const table = floating ? ".matrix-sticky-table" : ".matchup-table";
          await expect(page.locator(`${table} .column-head`).first()).toBeVisible();
          const labels = await page.locator(`${table} .column-head`).evaluateAll(heads => heads
            .filter(head => head.querySelectorAll(".mana-identity img").length >= 4)
            .map(head => {
              const rect = node => {
                const { left, right, top, bottom } = node.getBoundingClientRect();
                return { left, right, top, bottom };
              };
              return { head: rect(head), name: rect(head.querySelector(".axis-name-text")),
                colors: [...head.querySelectorAll(".mana-identity img")].map(rect) };
            }));
          expect(labels.length).toBeGreaterThan(0);
          for (const { head, name, colors } of labels) {
            for (const [i, color] of colors.entries()) {
              expect(color.left).toBeGreaterThanOrEqual(head.left);
              expect(color.right).toBeLessThanOrEqual(head.right);
              expect(color.top).toBeGreaterThanOrEqual(head.top);
              expect(color.bottom).toBeLessThanOrEqual(head.bottom);
              expect(color.left).toBeGreaterThanOrEqual(name.right);
              if (i) expect(color.top).toBeGreaterThanOrEqual(colors[i - 1].bottom);
            }
          }
        }
      }
    });
  }
}
