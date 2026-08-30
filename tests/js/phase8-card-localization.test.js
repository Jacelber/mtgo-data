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
const mtgchCard = "https://mtgch.com/card/TST/1/";

test("parses the flat English-name lookup", () => {
  const api = localization();
  const lookup = api.parseLookup({
    "Lightning Bolt": { zh_name: "闪电击", image_url: mtgchImage, mtgch_url: mtgchCard },
  });
  assert.equal(lookup["Lightning Bolt"].zh_name, "闪电击");
  assert.throws(() => api.parseLookup({
    Unsafe: { zh_name: "不安全", image_url: "https://example.com/card.webp" },
  }));
  assert.throws(() => api.parseLookup({
    Unsafe: { zh_name: "不安全", mtgch_url: "https://example.com/card/TST/1/" },
  }));
});

test("selects Chinese local, Chinese MTGCH, English local, and English Scryfall", () => {
  const api = localization();
  const lookup = api.parseLookup({
    "Local Card": {
      zh_name: "本地牌",
      image_url: mtgchImage,
      local_image: localImage,
      mtgch_url: mtgchCard,
    },
    "Remote Card": { zh_name: "远程牌", image_url: mtgchImage, mtgch_url: mtgchCard },
  });

  assert.deepEqual(
    JSON.parse(JSON.stringify(api.resolve("Local Card", "zh", lookup, "assets/card-cache/v1/images/en.jpg"))),
    {
      displayName: "本地牌",
      image: localImage,
      source: "chinese-local",
      linkUrl: mtgchCard,
      linkProvider: "mtgch",
    }
  );
  assert.deepEqual(
    JSON.parse(JSON.stringify(api.resolve("Remote Card", "zh", lookup))),
    {
      displayName: "远程牌",
      image: mtgchImage,
      source: "chinese-mtgch",
      linkUrl: mtgchCard,
      linkProvider: "mtgch",
    }
  );
  assert.deepEqual(
    JSON.parse(JSON.stringify(api.resolve("Local Card", "en", lookup, "assets/card-cache/v1/images/en.jpg"))),
    {
      displayName: "Local Card",
      image: "assets/card-cache/v1/images/en.jpg",
      source: "english-local",
      linkUrl: "https://scryfall.com/search?q=!%22Local%20Card%22",
      linkProvider: "scryfall",
    }
  );
  assert.deepEqual(
    JSON.parse(JSON.stringify(api.resolve("Remote Card", "en", lookup))),
    {
      displayName: "Remote Card",
      image: "https://api.scryfall.com/cards/named?exact=Remote%20Card&format=image&version=normal",
      source: "english-scryfall",
      linkUrl: "https://scryfall.com/search?q=!%22Remote%20Card%22",
      linkProvider: "scryfall",
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
      linkUrl: "https://scryfall.com/search?q=!%22Missing%20Card%22",
      linkProvider: "scryfall",
    }
  );
});

test("a Chinese name without a Chinese image keeps the name and uses the English image", () => {
  const api = localization();
  const lookup = api.parseLookup({
    "Name Only Card": { zh_name: "只有中文名", mtgch_url: "https://mtgch.com/card/ACR/276/" },
  });
  assert.deepEqual(
    JSON.parse(JSON.stringify(api.resolve("Name Only Card", "zh", lookup))),
    {
      displayName: "只有中文名",
      image: "https://api.scryfall.com/cards/named?exact=Name%20Only%20Card&format=image&version=normal",
      source: "english-scryfall",
      linkUrl: "https://mtgch.com/card/ACR/276/",
      linkProvider: "mtgch",
    }
  );
});
