"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "../../assets/js/phase8/app-metadata.js"),
  "utf8"
);
const rootEntry = fs.readFileSync(path.join(__dirname, "../../index.html"), "utf8");
const tabletopEntry = fs.readFileSync(
  path.join(__dirname, "../../melee/index.html"),
  "utf8"
);

function scriptSources(html) {
  return [...html.matchAll(/<script src="([^"]+)"><\/script>/g)]
    .map(match => match[1]);
}

function metadataFunctions() {
  const context = { URLSearchParams };
  context.globalThis = context;
  vm.runInNewContext(source, context);
  return context.P8Metadata;
}

test("metadata copy is stable and contains no current-week claim", () => {
  const metadata = metadataFunctions();
  assert.deepEqual(JSON.parse(JSON.stringify(metadata.metadataFor("zh"))), {
    title: "猫猫万智周报｜MTGO 环境与精选套牌",
    description: "每周整理 MTGO 标准与摩登的环境变化、套牌数据与精选套牌。",
    locale: "zh_CN",
    footer: {
      source: "卡图与卡牌数据：",
      policyLead: "猫猫万智周报为依据",
      policyLabel: "《爱好者内容政策》",
      policyTail: "制作的非官方爱好者内容，未获 Wizards 批准或认可。部分材料归 Wizards of the Coast LLC 所有。© Wizards of the Coast LLC。",
    },
  });
  assert.equal(
    metadata.metadataFor("en").title,
    "MTG Meta Analytics | MTGO Metagame & Featured Decks"
  );
  assert.equal(
    metadata.metadataFor("en").description,
    "Weekly MTGO Standard and Modern metagame trends, deck data, and featured decks."
  );
});

test("an explicit URL language overrides saved browser preference", () => {
  const metadata = metadataFunctions();
  const storage = { getItem: () => "en" };
  assert.equal(metadata.resolveLanguage("zh", storage), "zh");
  assert.equal(metadata.resolveLanguage(null, storage), "en");
  assert.equal(metadata.resolveLanguage("invalid", { getItem: () => "invalid" }), "zh");
});

test("legacy Pickup state maps to Landing features without losing its review week", () => {
  const metadata = metadataFunctions();
  const route = metadata.normalizedRoute(new URLSearchParams(
    "format=standard&product=weekly-pickup&week=2026-W33&lang=en"
  ));
  assert.equal(route.toString(), "format=standard&product=mtgo-landing&week=2026-W33&lang=en&section=features");
});

test("Landing feature canonical URL keeps its week and exact feature destination", () => {
  const metadata = metadataFunctions();
  const canonical = metadata.canonicalParameters(new URLSearchParams(
    "format=standard&product=mtgo-landing&section=features&week=2026-W33&feature=deck:aaaaaaaaaaaaaaaaaaaa&detail=ignore&lang=zh"
  ));
  assert.equal(canonical.toString(), "format=standard&product=mtgo-landing&section=features&week=2026-W33&feature=deck%3Aaaaaaaaaaaaaaaaaaaaa&lang=zh");
});

test("both production entries load metadata before the shared application", () => {
  for (const [entry, metadataPath, appPath] of [
    [rootEntry, "assets/js/phase8/app-metadata.js", "assets/js/phase8/app.js"],
    [tabletopEntry, "../assets/js/phase8/app-metadata.js", "../assets/js/phase8/app.js"],
  ]) {
    const scripts = scriptSources(entry);
    assert.notEqual(scripts.indexOf(metadataPath), -1);
    assert.ok(scripts.indexOf(metadataPath) < scripts.indexOf(appPath));
  }
});

test("both production titles provide a script-independent default Landing link", () => {
  assert.match(
    rootEntry,
    /<h1><a id="site-title" class="brand-home" href="\.\/index\.html\?format=standard&amp;product=mtgo-landing">/
  );
  assert.match(
    tabletopEntry,
    /<h1><a id="site-title" class="brand-home" href="\.\.\/index\.html\?format=standard&amp;product=mtgo-landing">/
  );
});

test("both production entries declare the approved tab and touch icons", () => {
  for (const [entry, prefix] of [
    [rootEntry, "assets/images/"],
    [tabletopEntry, "../assets/images/"],
  ]) {
    assert.match(entry, new RegExp(`<link rel="icon" href="${prefix}favicon-32\\.png" sizes="32x32"`));
    assert.match(entry, new RegExp(`<link rel="icon" href="${prefix}favicon-16\\.png" sizes="16x16"`));
    assert.match(entry, new RegExp(`<link rel="apple-touch-icon" href="${prefix}apple-touch-icon\\.png" sizes="180x180"`));
  }
});
