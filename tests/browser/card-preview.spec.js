"use strict";

const { expect, test } = require("@playwright/test");

const pixel = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
  "base64"
);

async function openDecklist(page) {
  await page.goto("/index.html?format=modern&product=mtgo-statistics&lang=zh");
  await expect(page.locator("#view .panel").first()).toBeVisible();
  const mobileDetail = page.locator("button[data-mobile-stats-detail]").first();
  if (await mobileDetail.isVisible()) {
    await mobileDetail.click();
    await expect(page.locator(".mobile-card-detail")).toBeVisible();
  } else {
    await page.locator("button[data-detail-identity]").first().click();
    await expect(page.locator(".deck-detail-row")).toBeVisible();
  }
}

async function touchPage(browser) {
  const context = await browser.newContext({
    hasTouch: true,
    isMobile: true,
    viewport: { width: 390, height: 844 },
  });
  await context.route("https://api.scryfall.com/**", route => route.fulfill({
    body: pixel,
    contentType: "image/png",
  }));
  await context.route("https://scryfall.com/**", route => route.fulfill({
    body: "<!doctype html><title>Scryfall</title>",
    contentType: "text/html",
  }));
  return { context, page: await context.newPage() };
}

test("desktop keeps hover preview and direct Scryfall click", async ({ context, page }) => {
  await context.route("https://api.scryfall.com/**", route => route.fulfill({
    body: pixel,
    contentType: "image/png",
  }));
  await context.route("https://scryfall.com/**", route => route.fulfill({
    body: "<!doctype html><title>Scryfall</title>",
    contentType: "text/html",
  }));
  await openDecklist(page);
  const card = page.locator("a[data-card-image]:visible").first();

  await card.hover();
  await expect(page.locator("#card-preview")).toBeVisible();
  await expect(page.locator("#card-preview .card-image-frame")).toHaveClass(/is-loaded/);
  await expect(page.locator("#card-preview-modal")).toBeHidden();

  const popupPromise = page.waitForEvent("popup");
  await card.click();
  const popup = await popupPromise;
  await popup.waitForLoadState("domcontentloaded");
  expect(new URL(popup.url()).hostname).toBe("scryfall.com");
  await popup.close();
});

test("touch first tap opens a modal and every dismissal restores position and focus", async ({ browser }) => {
  const { context, page } = await touchPage(browser);
  await openDecklist(page);
  const card = page.locator("a[data-card-image]:visible").first();
  const url = page.url();
  await card.scrollIntoViewIfNeeded();
  const before = await page.evaluate(() => window.scrollY);

  await card.click();
  const modal = page.locator("#card-preview-modal");
  await expect(modal).toBeVisible();
  await expect(page.locator("#card-preview-scryfall")).toHaveText("在 Scryfall 中查看");
  await expect(page.locator("[data-card-preview-close]")).toBeFocused();
  expect(page.url()).toBe(url);

  await modal.click({ position: { x: 4, y: 4 } });
  await expect(modal).toBeHidden();
  await expect(card).toBeFocused();
  expect(await page.evaluate(() => window.scrollY)).toBe(before);

  await card.click();
  await expect(modal).toBeVisible();
  await page.goBack();
  await expect(modal).toBeHidden();
  expect(page.url()).toBe(url);

  await card.click();
  const popupPromise = page.waitForEvent("popup");
  await page.locator("#card-preview-scryfall").click();
  const popup = await popupPromise;
  await popup.waitForLoadState("domcontentloaded");
  await expect(modal).toBeHidden();
  expect(new URL(popup.url()).hostname).toBe("scryfall.com");
  await popup.close();
  await context.close();
});

test("touch image failure offers one explicit retry and remains non-blocking", async ({ browser }) => {
  const context = await browser.newContext({
    hasTouch: true,
    isMobile: true,
    viewport: { width: 412, height: 915 },
  });
  let attempts = 0;
  await context.route("https://api.scryfall.com/**", route => {
    attempts += 1;
    route.abort();
  });
  const page = await context.newPage();
  await openDecklist(page);
  await page.locator("a[data-card-image]:visible").first().click();

  await expect(page.locator("[data-card-image-retry]")).toBeVisible();
  await page.locator("[data-card-image-retry]").click();
  await expect(page.locator("#card-preview-modal .card-image-frame")).toHaveClass(/is-error/);
  await expect(page.locator("[data-card-image-retry]")).toBeHidden();
  expect(attempts).toBe(2);
  await expect(page.locator("#card-preview-scryfall")).toBeVisible();
  await context.close();
});

test("third-party image queue never exceeds four concurrent requests", async ({ context, page }) => {
  let active = 0;
  let maximum = 0;
  await context.route("https://api.scryfall.com/queue/**", async route => {
    active += 1;
    maximum = Math.max(maximum, active);
    await new Promise(resolve => setTimeout(resolve, 80));
    active -= 1;
    await route.fulfill({ body: pixel, contentType: "image/png" });
  });
  await page.goto("/index.html?format=modern&product=mtgo-statistics&lang=en");
  await expect(page.locator("#view .panel").first()).toBeVisible();

  await page.evaluate(async () => {
    await Promise.all(Array.from({ length: 7 }, (_, index) => (
      P8CardImages.load(`https://api.scryfall.com/queue/${index}`)
    )));
  });

  expect(maximum).toBe(4);
  expect(await page.evaluate(() => P8CardImages.snapshot().queued)).toBe(0);
});
