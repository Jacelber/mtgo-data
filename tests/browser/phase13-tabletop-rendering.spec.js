"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { expect, test } = require("@playwright/test");

const fixture = JSON.parse(fs.readFileSync(
  path.join(__dirname, "../fixtures/melee/multi_event_matchup_parity.json"),
  "utf8"
));

function overview(eventId) {
  return {
    format: "modern",
    event_id: eventId,
    event_structure: "constructed_single_stage",
    event: {
      name: `Synthetic ${eventId}`,
      date: { start: "2026-08-01", end: "2026-08-02" },
      source_url: `https://melee.gg/Tournament/View/${eventId}`,
    },
    scopes: {
      all_constructed: {
        archetypes: [{
          group_id: "unknown",
          classification_status: "unknown",
          archetype_id: null,
          archetype_name: "Unknown",
          expandable: false,
          deck_count: 1,
          metagame_share: 1,
          average_points_per_effective_round: 0,
          completion_rate: 0,
          match_record: {
            all_matches: {
              literal_record: { wins: 0, losses: 0, draws: 0, matches: 0, win_rate: null },
            },
          },
          subtypes: [],
        }],
        average_points_per_effective_round: null,
        day2_conversion: null,
        high_score_deck_count: 0,
        participant_count: 1,
        result_counts: {},
        theoretical_rounds: 1,
      },
    },
  };
}

function quality() {
  return {
    format: "modern",
    issues: [],
    counts: {
      submitted_decklists: 0,
      missing_or_unavailable_decklists: 0,
    },
  };
}

async function routeSyntheticEvents(page, {
  catalog = fixture.catalog,
  overviewFor = overview,
  qualityFor = quality,
} = {}) {
  const documents = new Map([
    ["/stats/modern/melee/index.json", catalog],
    ["/stats/modern/archetype_names.json", {
      schema_version: "1.0.0",
      format: "modern",
      names: [
        { identity_id: "alpha", parent_id: "alpha", subtype_id: null, display: { en: "Alpha", zh: "阿尔法" } },
        { identity_id: "beta", parent_id: "beta", subtype_id: null, display: { en: "Beta", zh: "贝塔" } },
        { identity_id: "beta/one", parent_id: "beta", subtype_id: "one", display: { en: "One Beta", zh: "贝塔一" } },
        { identity_id: "beta/two", parent_id: "beta", subtype_id: "two", display: { en: "Two Beta", zh: "贝塔二" } },
      ],
    }],
  ]);
  fixture.event_inputs.forEach(input => {
    const eventId = input.meta.event_id;
    const base = `/stats/modern/melee/events/${eventId}`;
    documents.set(`${base}/meta.json`, input.meta);
    documents.set(`${base}/matchup.json`, input.matchup);
    documents.set(`${base}/overview.json`, overviewFor(eventId));
    documents.set(`${base}/quality.json`, qualityFor(eventId));
  });
  await page.route("**/stats/modern/{archetype_names.json,melee/**}", async route => {
    const value = documents.get(new URL(route.request().url()).pathname);
    if (!value) {
      await route.fulfill({ status: 404, body: "not found" });
      return;
    }
    await route.fulfill({ json: value });
  });
}

test("Tabletop defaults to the latest event and presents only meaningful metrics", async ({ page }) => {
  const catalog = structuredClone(fixture.catalog);
  catalog.default_event_id = "20";
  catalog.events[0].event_structure = "constructed_day2";
  catalog.events[0].scope_order = ["day1", "day2", "all_constructed"];
  const overviewFor = eventId => {
    const document = overview(eventId);
    if (eventId === "20") {
      document.event_structure = "constructed_day2";
      const all = document.scopes.all_constructed;
      const day2 = structuredClone(all);
      all.day2_conversion = null;
      day2.day2_conversion = 0.25;
      day2.archetypes[0].day2_conversion = 0.25;
      document.scopes = { day1: structuredClone(all), day2, all_constructed: all };
    } else {
      document.event_structure = "mixed";
    }
    return document;
  };
  const qualityFor = eventId => eventId === "20"
    ? {
      format: "modern",
      issues: [
        { code: "unknown_classifications", count: 7 },
        { code: "missing_or_unavailable_decklists", count: 3 },
      ],
      counts: { submitted_decklists: 7, missing_or_unavailable_decklists: 3 },
    }
    : quality();
  await routeSyntheticEvents(page, { catalog, overviewFor, qualityFor });

  await page.goto(
    "/melee/index.html?format=modern&product=tabletop-major-events&view=overview&scope=all_constructed&lang=en"
  );
  await expect(page.locator("#tabletop-event")).toHaveValue("20");
  await expect(page.locator(".event-summary")).toContainText("Synthetic 20");
  const advancementHeader = page.locator(".desktop-metric-table thead th").last();
  await expect(advancementHeader).toContainText("Day 2 CVR");
  await expect(page.locator(".desktop-metric-table .overall-row td").last()).toHaveText("25.0%");
  await expect(page.locator(".desktop-metric-table tbody tr").nth(1).locator("td").last()).toHaveText("25.0%");
  await expect(page.locator(".mobile-metric-card.overall-card")).toContainText("Day 2 CVR");
  await expect(page.locator(".mobile-metric-card.overall-card")).toContainText("25.0%");
  await expect(page.locator(".quality-notice")).toContainText(
    "7 valid submitted decklists resemble random card piles or placeholder lists."
  );
  await expect(page.locator(".quality-notice")).toContainText(
    "3 participants have no available decklist."
  );
  const labelBox = await advancementHeader.locator(".sort-label").boundingBox();
  const accessoriesBox = await advancementHeader.locator(".sort-accessories").boundingBox();
  expect(labelBox.x + labelBox.width).toBeLessThanOrEqual(accessoriesBox.x + 1);

  await page.goto(
    "/melee/index.html?format=modern&product=tabletop-major-events&view=overview&event=20&scope=all_constructed&lang=zh"
  );
  await expect(page.locator(".quality-notice")).toContainText(
    "7 份有效提交牌表近似于随机卡堆或凑数牌"
  );
  await expect(page.locator(".quality-notice")).toContainText(
    "3 名参赛者没有可用牌表"
  );

  await page.goto(
    "/melee/index.html?format=modern&product=tabletop-major-events&view=overview&event=10&scope=all_constructed&sort=high_score&lang=en"
  );
  await expect(page.locator(".desktop-metric-table thead th")).toHaveCount(8);
  await expect(page.locator(".desktop-metric-table")).not.toContainText("High-score decks");
  await expect(page.locator(".mobile-metric-layout")).not.toContainText("High-score decks");
  await expect(page.locator(".quality-notice")).toHaveCount(0);
  await expect.poll(() => new URL(page.url()).searchParams.get("sort")).toBe("deck_count");
});

test("Tabletop renders the combined result without merging Event Overview", async ({ page }) => {
  await routeSyntheticEvents(page);
  await page.goto(
    "/melee/index.html?format=modern&product=tabletop-major-events&view=matchup&event=10&events=10,20&scope=all_constructed&lang=en"
  );

  const summary = page.locator(".multi-event-summary");
  await expect(summary).toContainText("Included events");
  await expect(summary).toContainText("Synthetic 10 · Melee event ID 10");
  await expect(summary).toContainText("Synthetic 20 · Melee event ID 20");
  await expect(summary).toContainText("matchup data only");
  await expect(page.locator(".matrix-toolbar-note")).toContainText("2 events · 28 valid matches");
  await expect(page.locator(".scope-lock-note")).toContainText("only All Constructed Swiss");
  await expect(page.locator("[data-matchup-mainstream]")).toHaveCount(0);
  await expect(page.locator(".matchup-table")).toBeVisible();

  const alphaCells = page.locator('[data-matchup-row-identity="alpha"] .matrix-cell');
  await expect(alphaCells.nth(1)).toHaveClass(/low-sample/);
  await expect(alphaCells.nth(1)).toHaveAttribute("data-record", "1-1-0（2）");
  await expect(alphaCells.nth(2)).toHaveAttribute("data-record", "9-11-2（22）");
  await expect(alphaCells.nth(2).locator("strong")).toHaveText("40.9");
  await expect(alphaCells.nth(2).locator("small")).toHaveText("±19.0");
  await expect(page.locator(".matchup-legend")).toContainText("fewer than 20 matches");

  await page.locator('[data-tabletop-view="overview"]').click();
  await expect(page.locator(".multi-event-summary")).toHaveCount(0);
  await expect(page.locator(".event-summary")).toContainText("Synthetic 10");
  await expect(page.locator(".identity-label").filter({ hasText: "Unknown" })).toBeVisible();
  await page.locator('[data-tabletop-sort="name"]').click();
  await expect(page.locator("#view .error-state")).toHaveCount(0);

  await page.goto(
    "/melee/index.html?format=modern&product=tabletop-major-events&view=matchup&event=10&events=10,20&scope=all_constructed&lang=zh"
  );
  await expect(page.locator(".multi-event-summary")).toContainText("纳入赛事");
  await expect(page.locator(".matrix-toolbar-note")).toContainText("2 场赛事 · 28 场有效对局");
  await page.locator('[data-tabletop-view="overview"]').click();
  await expect(page.locator(".identity-label").filter({ hasText: "Unknown" })).toBeVisible();
});
