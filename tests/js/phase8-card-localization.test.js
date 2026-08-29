"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "../../assets/js/phase8/card-localization.js"),
  "utf8"
);

function localization() {
  const context = { URL };
  context.globalThis = context;
  vm.runInNewContext(source, context);
  return context.P8CardLocalization;
}

const localImage = `assets/card-localization/images/${"a".repeat(64)}.webp`;
const mtgchImage = "https://images.mtgch.com/zhs/normal/front/a/a/card.webp?ts=1";

test("parses the flat English-name lookup", () => {
  const api = localization();
  const lookup = api.parseLookup({
    "Lightning Bolt": { zh_name: "闪电击", image_url: mtgchImage },
  });
  assert.equal(lookup["Lightning Bolt"].zh_name, "闪电击");
  assert.throws(() => api.parseLookup({
    Unsafe: { zh_name: "不安全", image_url: "https://example.com/card.webp" },
  }));
});

test("selects Chinese local, Chinese MTGCH, English local, and English Scryfall", () => {
  const api = localization();
  const lookup = api.parseLookup({
    "Local Card": {
      zh_name: "本地牌",
      image_url: mtgchImage,
      local_image: localImage,
    },
    "Remote Card": { zh_name: "远程牌", image_url: mtgchImage },
  });

  assert.deepEqual(
    JSON.parse(JSON.stringify(api.resolve("Local Card", "zh", lookup, "assets/card-cache/v1/images/en.jpg"))),
    { displayName: "本地牌", image: localImage, source: "chinese-local" }
  );
  assert.deepEqual(
    JSON.parse(JSON.stringify(api.resolve("Remote Card", "zh", lookup))),
    { displayName: "远程牌", image: mtgchImage, source: "chinese-mtgch" }
  );
  assert.deepEqual(
    JSON.parse(JSON.stringify(api.resolve("Local Card", "en", lookup, "assets/card-cache/v1/images/en.jpg"))),
    { displayName: "Local Card", image: "assets/card-cache/v1/images/en.jpg", source: "english-local" }
  );
  assert.deepEqual(
    JSON.parse(JSON.stringify(api.resolve("Remote Card", "en", lookup))),
    {
      displayName: "Remote Card",
      image: "https://api.scryfall.com/cards/named?exact=Remote%20Card&format=image&version=normal",
      source: "english-scryfall",
    }
  );
});

test("a missing Chinese value preserves the existing English fallback", () => {
  const api = localization();
  assert.deepEqual(
    JSON.parse(JSON.stringify(api.resolve("Missing Card", "zh", Object.create(null)))),
    {
      displayName: "Missing Card",
      image: "https://api.scryfall.com/cards/named?exact=Missing%20Card&format=image&version=normal",
      source: "english-scryfall",
    }
  );
});

test("a Chinese name without a Chinese image keeps the name and uses the English image", () => {
  const api = localization();
  const lookup = api.parseLookup({
    "Name Only Card": { zh_name: "只有中文名" },
  });
  assert.deepEqual(
    JSON.parse(JSON.stringify(api.resolve("Name Only Card", "zh", lookup))),
    {
      displayName: "只有中文名",
      image: "https://api.scryfall.com/cards/named?exact=Name%20Only%20Card&format=image&version=normal",
      source: "english-scryfall",
    }
  );
});
