"use strict";
const { expect, test } = require("@playwright/test");

async function ready(page, selector = ".composition-panel") {
  await expect(page.locator(selector).first()).toBeVisible();
  await expect(page.locator("#view")).not.toHaveAttribute("aria-busy", "true");
}
async function changeJson(page, pattern, mutate) {
  await page.route(pattern, async route => {
    const response = await route.fetch();
    const json = await response.json();
    mutate(json);
    await route.fulfill({ json });
  });
}
const statsUrl = "/index.html?format=pauper&product=mtgo-statistics&range=1&lang=en";
const eventUrl = "/melee/index.html?format=modern&product=tabletop-major-events&event=405588&view=matchup&lang=en";
const eventPath = "**/stats/modern/melee/events/405588/matchup.json";
const namePath = "**/stats/pauper/archetype_names.json";

test("mainstream refresh applies the same-period range with the new matrix", async ({ page }) => {
  await page.goto("/index.html?format=pauper&product=mtgo-matchups&range=4&lang=en");
  await ready(page, "[data-record]");
  await page.locator("[data-matchup-mainstream]").check();
  await ready(page, "[data-record]");
  const before = await page.evaluate(() => [...currentContext.matchupMainstreamParentIds]);
  const chosen = await page.evaluate(async () => (await MtgoController.loadRangeStatistics("pauper", 4))
    .archetypes.find(row => !currentContext.matchupMainstreamParentIds.has(row.id)).id);
  await changeJson(page, "**/stats/pauper/mtgo/range_4w.json", json => {
    json.archetypes.forEach(row => { row.high_score_share = row.id === chosen ? 1 : 0; });
  });
  await changeJson(page, "**/stats/pauper/mtgo/matchup_4w.json", json => { json.generated_at = "2099-01-01"; });
  await page.evaluate(() => checkForUpdates());
  expect(await page.evaluate(() => [...currentContext.matchupMainstreamParentIds])).toEqual(before);
  await page.locator("[data-apply-refresh]").click();
  await ready(page, "[data-record]");
  expect(await page.evaluate(() => [...currentContext.matchupMainstreamParentIds])).toEqual([chosen]);
  expect(await page.evaluate(() => currentContext.matchupDocument.generated_at)).toBe("2099-01-01");
});

test("name-only refresh updates the active contract, normalized cache and raw cache together", async ({ page }) => {
  await page.goto(statsUrl);
  await ready(page);
  const old = await page.evaluate(() => classifierName("grixis-affinity"));
  await changeJson(page, namePath, json => {
    json.names.find(item => item.identity_id === "grixis-affinity").display.en = "Updated Affinity";
  });
  await page.evaluate(() => checkForUpdates());
  expect(await page.evaluate(() => classifierName("grixis-affinity"))).toBe(old);
  await page.locator("[data-apply-refresh]").click();
  await ready(page);
  expect(await page.evaluate(() => classifierName("grixis-affinity"))).toBe("Updated Affinity");
  expect(await page.evaluate(async () => ({
    normalized: state.classifierNameContracts.get("pauper").names.get("grixis-affinity").en,
    raw: (await classifierNameClient.fetchJson("stats/pauper/archetype_names.json"))
      .names.find(item => item.identity_id === "grixis-affinity").display.en,
  }))).toEqual({ normalized: "Updated Affinity", raw: "Updated Affinity" });
});

test("incomplete names reject data refresh atomically and allow a valid retry", async ({ page }) => {
  await page.goto(statsUrl);
  await ready(page);
  const before = await page.evaluate(() => currentContext.range.generated_at);
  await changeJson(page, namePath, json => {
    json.names = json.names.filter(item => item.parent_id !== "grixis-affinity");
  });
  await changeJson(page, "**/stats/pauper/mtgo/range_1w.json", json => { json.generated_at = "2099-02-01"; });
  await page.evaluate(() => checkForUpdates());
  await expect(page.locator("#refresh-status")).toHaveAttribute("data-kind", "error");
  expect(await page.evaluate(async () => (await MtgoController.loadRangeStatistics("pauper", 1)).generated_at)).toBe(before);
  await page.unroute(namePath);
  await page.locator("[data-retry-refresh]").click();
  await page.locator("[data-apply-refresh]").click();
  await ready(page);
  expect(await page.evaluate(() => currentContext.range.generated_at)).toBe("2099-02-01");
});

test("late staged names cannot replace the contract after navigation", async ({ page }) => {
  await page.goto(statsUrl);
  await ready(page);
  let release, arrived;
  const gate = new Promise(resolve => { release = resolve; });
  const seen = new Promise(resolve => { arrived = resolve; });
  await page.route(namePath, async route => {
    const response = await route.fetch();
    const json = await response.json();
    json.names.find(item => item.identity_id === "grixis-affinity").display.en = "Stale Name";
    arrived();
    await gate;
    await route.fulfill({ json });
  });
  const refresh = page.evaluate(() => checkForUpdates());
  await seen;
  await page.locator('[data-format="standard"]').click();
  await ready(page);
  release();
  await refresh;
  expect(await page.evaluate(() => state.classifierNameContract.format)).toBe("standard");
  expect(await page.evaluate(() => state.classifierNameContracts.get("pauper").names.get("grixis-affinity").en)).not.toBe("Stale Name");
  await expect(page.locator("[data-apply-refresh]")).toHaveCount(0);
});

for (const view of ["mtgo", "tabletop"]) {
  test(`Chinese ${view} matrix does not request card localization`, async ({ page }) => {
    const reads = [];
    page.on("request", request => {
      if (request.url().includes("/card-localization/")) reads.push(request.url());
    });
    await page.route("**/assets/card-localization/cards.json", route => route.fulfill({ status: 503, body: "unavailable" }));
    await page.goto(view === "mtgo"
      ? "/index.html?format=pauper&product=mtgo-matchups&range=4&lang=zh"
      : eventUrl.replace("lang=en", "lang=zh"));
    await ready(page, "[data-record]");
    expect(reads).toEqual([]);
  });
}

for (const defect of ["encoding", "row"]) {
  test(`single-event ${defect} corruption is rejected on load and can be retried`, async ({ page }) => {
    await changeJson(page, eventPath, json => {
      if (defect === "encoding") delete json.matrix_encoding;
      else delete json.scopes.all_constructed.leaf_matrix[json.scopes.all_constructed.leaf_order[0]];
    });
    await page.goto(eventUrl);
    await expect(page.locator("#view .error-state")).toBeVisible();
    await expect(page.locator("[data-record]")).toHaveCount(0);
    await page.unroute(eventPath);
    await page.locator("[data-retry-view]").click();
    await ready(page, "[data-record]");
  });
}

test("invalid single-event refresh retains the valid cache and a later refresh applies", async ({ page }) => {
  await page.goto(eventUrl);
  await ready(page, "[data-record]");
  const before = await page.locator("#view").innerText();
  await changeJson(page, eventPath, json => { delete json.matrix_encoding; });
  await page.evaluate(() => checkForUpdates());
  await expect(page.locator("#refresh-status")).toHaveAttribute("data-kind", "error");
  expect(await page.locator("#view").innerText()).toBe(before);
  await page.locator('[data-tabletop-scope="day1"]').click();
  await ready(page, "[data-record]");
  await page.unroute(eventPath);
  await changeJson(page, eventPath, json => { json.generated_at = "2099-03-01"; });
  await page.evaluate(() => checkForUpdates());
  await page.locator("[data-apply-refresh]").click();
  await ready(page, "[data-record]");
  expect(await page.evaluate(() => currentContext.matchup.generated_at)).toBe("2099-03-01");
});

test("Chinese statistics loads card names when its first deck detail needs them", async ({ page }) => {
  const reads = [];
  page.on("request", request => {
    if (request.url().endsWith("/assets/card-localization/cards.json")) reads.push(request.url());
  });
  await page.route("**/assets/card-localization/cards.json", route => route.fulfill({ status: 503, body: "unavailable" }));
  await page.goto(statsUrl.replace("lang=en", "lang=zh"));
  await ready(page);
  expect(reads).toEqual([]);
  await page.locator("button[data-detail-identity]:visible").first().click();
  await ready(page, ".deck-detail-row:not(.load-error-row)");
  expect(reads).toHaveLength(1);
});

test("new classifier identity and its approved name apply in one refresh", async ({ page }) => {
  await page.goto(statsUrl);
  await ready(page);
  const oldId = "grixis-affinity", newId = "renamed-affinity";
  await changeJson(page, namePath, json => {
    const old = json.names.find(item => item.identity_id === oldId);
    json.names.push({ ...old, identity_id: newId, parent_id: newId,
      display: { en: "New Affinity Identity", zh: "新共鸣身份" } });
  });
  await changeJson(page, "**/stats/pauper/mtgo/range_1w.json", json => {
    json.archetypes.find(item => item.id === oldId).id = newId;
  });
  await page.evaluate(() => checkForUpdates());
  await page.locator("[data-apply-refresh]").click();
  await ready(page);
  expect(await page.evaluate(() => currentContext.range.archetypes.some(item => item.id === "renamed-affinity"))).toBe(true);
  await expect(page.locator("#view")).toContainText("New Affinity Identity");
});
