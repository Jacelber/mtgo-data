"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "../../assets/js/phase8/app-mtgo.js"),
  "utf8"
);
const freshnessSource = fs.readFileSync(
  path.join(__dirname, "../../assets/js/phase8/app-freshness.js"),
  "utf8"
);

function landingFunctions(language = "zh") {
  const context = {
    ArchetypeVisuals: { manaIdentities: {} },
    I18n: { language: () => language },
    classifierName: (parentId, subtypeId = null) => subtypeId || parentId,
    REPRESENTATIVE_CARDS: {},
    URL,
    currentContext: {},
    escapeHtml: value => String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;"),
    localizedValue: value => language === "en"
      ? (value.en || value.zh || "")
      : (value.zh || value.en || ""),
    manaIdentityHtml: () => "",
    pct: value => `${(Number(value) * 100).toFixed(1)}%`,
    state: {
      compositionIdentity: null,
      detailIdentity: null,
      format: "standard",
      landingFeatureOpen: new Set(),
      product: "mtgo-landing",
    },
    t: key => key,
    window: {
      addEventListener: () => {},
      location: { href: "http://localhost/index.html" },
    },
  };
  context.globalThis = context;
  vm.runInNewContext(`${freshnessSource}\n${source}
    globalThis.__landing = {
      landingFreshness,
      landingDirection,
      landingEnvironmentDetailTitle,
      landingEnvironmentRows,
      landingFeatureHtml,
      landingFeatureItems,
      landingSummaryText,
    };`, context);
  return context.__landing;
}

test("weekly summary replaces only the exact deck token with its localized link", () => {
  const { landingSummaryText } = landingFunctions("zh");
  const html = landingSummaryText({
    text: { zh: "前文 deck:aaaaaaaaaaaaaaaaaaaa 后文", en: "Before deck:aaaaaaaaaaaaaaaaaaaa after" },
    deck_links: [{
      token: "deck:aaaaaaaaaaaaaaaaaaaa",
      label: { zh: "套牌 · 牌手 · 第1名", en: "Deck · Player · Rank 1" },
      deck: { event_id: "42", final_rank: 1 },
    }],
  }, "2026-W33");

  assert.match(html, /^前文 <a /);
  assert.match(html, />套牌 · 牌手 · 第1名<\/a> 后文$/);
  assert.match(html, /product=mtgo-landing/);
  assert.match(html, /section=features/);
  assert.match(html, /feature=deck%3Aaaaaaaaaaaaaaaaaaaaa/);
  assert.match(html, /data-landing-feature-destination="deck:aaaaaaaaaaaaaaaaaaaa"/);
  assert.match(html, /data-landing-feature-week="2026-W33\.json"/);
  assert.doesNotMatch(html, />前文/);
});

test("a legacy noncanonical token retains the exact Top 8 fallback", () => {
  const { landingSummaryText } = landingFunctions("en");
  const html = landingSummaryText({
    text: { zh: "", en: "Legacy deck:old" },
    deck_links: [{
      token: "deck:old",
      label: { zh: "", en: "Legacy Deck" },
      deck: { event_id: "42", final_rank: 3 },
    }],
  }, "2026-W27");

  assert.match(html, /product=mtgo-top8/);
  assert.match(html, /detail=42%3A3/);
  assert.doesNotMatch(html, /data-landing-feature-destination/);
});

test("environment direction uses the accepted five-point movement boundary", () => {
  const { landingDirection } = landingFunctions();

  assert.equal(landingDirection({
    current: { share: 0.12 }, previous_four_weeks: { share: 0.06 },
  }, true).className, "up");
  assert.equal(landingDirection({
    current: { share: 0.12 }, previous_four_weeks: { share: 0.09 },
  }, true).className, "steady");
  assert.equal(landingDirection({
    current: { share: 0.03 }, previous_four_weeks: { share: 0.09 },
  }, true).className, "down");
});

test("environment rows render three shares and never expose raw counts", () => {
  const { landingEnvironmentRows } = landingFunctions();
  const html = landingEnvironmentRows({
    comparison: { available: true },
    environment: {
      rows: [{
        archetype_id: "deck-one",
        display_name: "Deck One",
        key_cards: [],
        current: { count: 17, denominator: 129, share: 0.1318 },
        previous_week: { count: 1, denominator: 122, share: 0.0082 },
        previous_four_weeks: { count: 2, denominator: 469, share: 0.0043 },
      }],
    },
  });

  assert.match(html, /13\.2%/);
  assert.match(html, /0\.8%/);
  assert.match(html, /0\.4%/);
  assert.doesNotMatch(html, />17</);
  assert.doesNotMatch(html, />129</);
  assert.doesNotMatch(html, />469</);
});

test("Landing detail titles use the subtype that owns the displayed best deck", () => {
  const { landingEnvironmentDetailTitle } = landingFunctions();
  const row = { archetype_id: "combo" };

  assert.equal(landingEnvironmentDetailTitle(row, {
    parent_id: "combo",
    id: "direct-child",
  }), "direct-child");

  assert.equal(landingEnvironmentDetailTitle(row, {
    best_deck: { player: "Player", event_id: "42", final_rank: 5 },
    subtypes: [
      { id: "first", best_deck: { player: "Other", event_id: "41", final_rank: 1 } },
      { id: "matching-child", best_deck: { player: "Player", event_id: "42", final_rank: 5 } },
    ],
  }), "matching-child");
});

test("feature history reads only the Landing-owned week document", () => {
  const { landingFeatureItems } = landingFunctions();
  const current = {
    featureDocument: { features: { items: [{ order: 1 }] } },
  };
  const empty = {
    featureDocument: { features: { items: [] } },
  };

  assert.equal(landingFeatureItems(current).length, 1);
  assert.equal(landingFeatureItems(empty).length, 0);
});

test("a reviewed feature keeps one disclosure action and four separate card links", () => {
  const { landingFeatureHtml } = landingFunctions();
  const html = landingFeatureHtml({
    category: "new_deck",
    order: 1,
    destination_id: "deck:aaaaaaaaaaaaaaaaaaaa",
    archetype_id: "new-deck",
    subtype_id: null,
    display_name: "New Deck",
    headline: { zh: "新套牌标题", en: "New deck headline" },
    positioning: { zh: "定位文案", en: "Positioning" },
    featured_cards: ["A", "B", "C", "D"].map(name => ({ name })),
    deck: {},
  });

  assert.equal((html.match(/data-landing-feature-toggle=/g) || []).length, 1);
  assert.equal((html.match(/data-progressive-image=/g) || []).length, 4);
  assert.match(html, /<\/button><span class="landing-feature-cards"/);
});

test("retained Landing freshness does not mix newer companion facts", () => {
  const { landingFreshness } = landingFunctions();
  const html = landingFreshness({
    week: { start: "2026-08-10", end: "2026-08-16" },
    populations: { current: { event_count: 8, high_score_count: 129, top8_count: 64 } },
  }, null, null);

  assert.match(html, /2026-08-10 – 2026-08-16/);
  assert.match(html, /data-freshness-key="events"[\s\S]*?<b>8<\/b>/);
  assert.match(html, /data-freshness-key="decks"[\s\S]*?<b>freshness\.unknown<\/b>/);
  assert.match(html, /data-freshness-key="high-score"[\s\S]*?<b>129<\/b>/);
  assert.match(html, /data-freshness-key="top8"[\s\S]*?<b>64<\/b>/);
  assert.match(html, /data-freshness-key="high-score-completeness"[\s\S]*?freshness\.unknown/);
});
