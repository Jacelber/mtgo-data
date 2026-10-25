"use strict";
const { expect, test } = require("@playwright/test");

async function ready(page) {
  await expect(page.locator('#view')).not.toHaveAttribute('aria-busy', 'true');
  await expect(page.locator('#view .error-state')).toHaveCount(0);
}

async function trackResourceLeases(page) {
  await page.addInitScript(() => {
    globalThis.resourceClients = [];
    Object.defineProperty(globalThis, 'P8Runtime', {
      configurable: true,
      set(runtime) {
        const wrapped = { ...runtime, createJsonClient(...args) {
          const client = runtime.createJsonClient(...args);
          resourceClients.push(client);
          return client;
        } };
        Object.defineProperty(globalThis, 'P8Runtime', { value: wrapped, configurable: true });
      },
    });
  });
}

test('overview loads decks only on first detail and English does not load Chinese lookup', async ({ page }) => {
  const reads = [];
  page.on('request', request => reads.push(new URL(request.url()).pathname));
  await page.goto('/melee/index.html?format=modern&product=tabletop-major-events&event=405588&view=overview&lang=en');
  await expect(page.locator('#tabletop-event')).toBeVisible();
  await ready(page);
  expect(reads.filter(path => path.endsWith('/decks.json'))).toHaveLength(0);
  expect(reads.filter(path => path.includes('/card-localization/'))).toHaveLength(0);
  const before = await page.evaluate(() => JSON.stringify(currentContext.overview.scopes.all_constructed.literal_record));
  await page.locator('button[data-tabletop-detail]:visible').first().click();
  await expect(page.locator('.deck-detail-row:not(.load-error-row)')).toBeVisible();
  await ready(page);
  expect(reads.filter(path => path.endsWith('/events/405588/decks.json'))).toHaveLength(1);
  expect(await page.evaluate(() => JSON.stringify(currentContext.overview.scopes.all_constructed.literal_record))).toBe(before);
});

test('scope and filters reuse the active matrix and leases leave with the view', async ({ page }) => {
  await trackResourceLeases(page);
  const reads = [];
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    const path = new URL(request.url()).pathname;
    if (path.endsWith('.json')) reads.push(path);
  });
  await page.goto('/melee/index.html?format=modern&product=tabletop-major-events&event=405588&view=matchup&lang=en');
  await expect(page.locator('[data-record]').first()).toBeVisible();
  await ready(page);
  const resources = reads.length;
  await page.locator('[data-tabletop-scope="day1"]').click();
  await ready(page);
  await page.locator('[data-matchup-mainstream]').check();
  await ready(page);
  await page.locator('[data-matchup-mainstream]').uncheck();
  await ready(page);
  expect(reads.length).toBe(resources);
  const retained = () => page.evaluate(() => resourceClients.flatMap(client => [...client.snapshot().retainedPaths]));
  expect(await retained()).toContain('stats/modern/melee/events/405588/matchup.json');
  await page.locator('[data-tabletop-view="overview"]').click();
  await expect(page.locator('button[data-tabletop-detail]:visible').first()).toBeVisible();
  await ready(page);
  expect(await retained()).not.toContain('stats/modern/melee/events/405588/matchup.json');
  expect(errors).toEqual([]);
});

test('failed replacement releases resource leases and retry acquires only its target', async ({ page }) => {
  await trackResourceLeases(page);
  await page.goto('/melee/index.html?format=modern&product=tabletop-major-events&event=405588&view=overview&lang=en');
  await expect(page.locator('#tabletop-event')).toBeVisible();
  await ready(page);
  const path = '**/stats/modern/melee/events/405590/overview.json';
  await page.route(path, route => route.fulfill({ status: 503, body: 'temporary failure' }));
  await page.locator('#tabletop-event').selectOption('405590');
  await expect(page.locator('#view .error-state')).toBeVisible();
  const retained = () => page.evaluate(() => resourceClients.flatMap(client => [...client.snapshot().retainedPaths]));
  expect(await retained()).toEqual([]);
  await page.unroute(path);
  await page.locator('[data-retry-view]').click();
  await expect(page.locator('#tabletop-event')).toHaveValue('405590');
  await ready(page);
  expect(await retained()).toContain('stats/modern/melee/events/405590/overview.json');
  expect((await retained()).some(path => path.includes('/405588/'))).toBe(false);
});

test('single-event filters reuse successful contract validation', async ({ page }) => {
  await page.addInitScript(() => {
    globalThis.matrixValidationCalls = 0;
    Object.defineProperty(globalThis, 'P8ReviewData', {
      configurable: true,
      set(api) {
        Object.defineProperty(globalThis, 'P8ReviewData', { configurable: true, value: {
          ...api,
          validateEventMatchup(...args) {
            matrixValidationCalls += 1;
            return api.validateEventMatchup(...args);
          },
        } });
      },
    });
  });
  await page.goto('/melee/index.html?format=modern&product=tabletop-major-events&event=405588&view=matchup&lang=en');
  await expect(page.locator('[data-record]').first()).toBeVisible();
  await ready(page);
  expect(await page.evaluate(() => matrixValidationCalls)).toBe(1);
  await page.locator('[data-tabletop-scope="day1"]').click();
  await ready(page);
  await page.locator('[data-matchup-mainstream]').check();
  await ready(page);
  expect(await page.evaluate(() => matrixValidationCalls)).toBe(1);
});
