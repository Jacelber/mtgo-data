"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const pickupSource = fs.readFileSync(
  path.join(__dirname, "../../assets/js/phase8/app-mtgo.js"),
  "utf8"
);

function pickupRenderer() {
  const context = {
    ArchetypeVisuals: { manaIdentities: {} },
    I18n: { language: () => "zh" },
    cardList: () => "",
    dateText: value => value,
    escapeHtml: value => String(value),
    state: { pickupOpen: new Set() },
    t: (key, values = {}) => key === "deck.points" ? `${values.count} 分` : `${key}:`,
  };
  context.globalThis = context;
  vm.runInNewContext(`${pickupSource}\nglobalThis.__pickupDeck = pickupDeck;`, context);
  return context.__pickupDeck;
}

function item(deviation) {
  return {
    archetype: "Boros Dragons",
    player: "Player",
    final_rank: 3,
    swiss_score: 15,
    starttime: "2026-08-14",
    deviation,
    comment_zh: "中文稿",
    main_deck: [],
    side_deck: [],
  };
}

test("Pickup renders an unavailable deviation as a dash", () => {
  const html = pickupRenderer()(item(null), "existing_changes");

  assert.match(html, /deck\.deviation: —/);
  assert.doesNotMatch(html, /null 分/);
});

test("Pickup preserves a numeric deviation and its points suffix", () => {
  const html = pickupRenderer()(item(20), "existing_changes");

  assert.match(html, /deck\.deviation: 20 分/);
});
