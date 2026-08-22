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

function landingFunctions(language = "zh") {
  const context = {
    ArchetypeVisuals: { manaIdentities: {} },
    I18n: { language: () => language },
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
      pickupOpen: new Set(),
      product: "mtgo-landing",
    },
    t: key => key,
    window: { location: { href: "http://localhost/index.html" } },
  };
  context.globalThis = context;
  vm.runInNewContext(`${source}
    globalThis.__landing = {
      landingDirection,
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
    text: { zh: "前文 deck:abc123 后文", en: "Before deck:abc123 after" },
    deck_links: [{
      token: "deck:abc123",
      label: { zh: "套牌 · 牌手 · 第1名", en: "Deck · Player · Rank 1" },
      deck: { event_id: "42", final_rank: 1 },
    }],
  }, "2026-W33");

  assert.match(html, /^前文 <a /);
  assert.match(html, />套牌 · 牌手 · 第1名<\/a> 后文$/);
  assert.match(html, /product=mtgo-top8/);
  assert.match(html, /detail=42%3A1/);
  assert.doesNotMatch(html, />前文/);
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

test("feature history does not invent cards or copy from legacy Pickup rows", () => {
  const { landingFeatureItems } = landingFunctions();
  const current = {
    landing: { week: { id: "2026-W33" }, features: { items: [{ order: 1 }] } },
    featureFile: "2026-W33.json",
    pickupDocument: null,
  };
  const legacy = {
    landing: current.landing,
    featureFile: "2026-W27.json",
    pickupDocument: { existing_changes: [{ comment_zh: "draft only" }] },
  };

  assert.equal(landingFeatureItems(current).length, 1);
  assert.equal(landingFeatureItems(legacy).length, 0);
});

test("a reviewed feature keeps one disclosure action and four separate card links", () => {
  const { landingFeatureHtml } = landingFunctions();
  const html = landingFeatureHtml({
    category: "new_deck",
    order: 1,
    archetype_id: "new-deck",
    subtype_id: null,
    display_name: "New Deck",
    headline: { zh: "新套牌标题", en: "New deck headline" },
    positioning: { zh: "定位文案", en: "Positioning" },
    featured_cards: ["A", "B", "C", "D"].map(name => ({ name })),
    deck: {},
  });

  assert.equal((html.match(/data-pickup-toggle=/g) || []).length, 1);
  assert.equal((html.match(/data-progressive-image=/g) || []).length, 4);
  assert.match(html, /<\/button><span class="landing-feature-cards"/);
});
