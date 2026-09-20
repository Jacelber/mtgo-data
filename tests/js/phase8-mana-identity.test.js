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

function functionsFor(manaIdentities) {
  const context = {
    ArchetypeVisuals: { manaIdentities },
    Runtime: { publicPath: value => value },
    escapeHtml: value => String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;"),
    state: { format: "fixture" },
    t: (key, values) => values?.colors || key,
  };
  context.globalThis = context;
  vm.runInNewContext(`${source}\n    globalThis.__mana = { manaIdentityHtml, matchupAxisNameHtml };`, context);
  return context.__mana;
}

test("colorless renders the shared c indicator", () => {
  const { manaIdentityHtml } = functionsFor({ fixture: { artifacts: ["c"] } });
  const html = manaIdentityHtml("artifacts");

  assert.match(html, /assets\/images\/mana\/c\.svg/);
  assert.match(html, /aria-label="mana\.c"/);
});

test("matchup axis labels share mana rendering for rows and columns", () => {
  const { matchupAxisNameHtml } = functionsFor({ fixture: { tempo: ["u", "r"] } });
  const row = matchupAxisNameHtml("Tempo", "tempo", "row-axis-name");
  const column = matchupAxisNameHtml("Tempo", "tempo");

  for (const html of [row, column]) {
    assert.match(html, />Tempo<span class="mana-identity"/);
    assert.match(html, /assets\/images\/mana\/u\.svg/);
    assert.match(html, /assets\/images\/mana\/r\.svg/);
  }
});
