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

test("Landing feature canonical URL keeps only the compatible feature week", () => {
  const metadata = metadataFunctions();
  const canonical = metadata.canonicalParameters(new URLSearchParams(
    "format=standard&product=mtgo-landing&section=features&week=2026-W33&detail=ignore&lang=zh"
  ));
  assert.equal(canonical.toString(), "format=standard&product=mtgo-landing&section=features&week=2026-W33&lang=zh");
});
