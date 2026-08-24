"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const names = require("../../assets/js/phase8/archetype-names.js");

function contract() {
  return {
    schema_version: "1.0.0",
    format: "modern",
    names: [
      {
        identity_id: "prowess",
        parent_id: "prowess",
        subtype_id: null,
        display: { en: "Prowess", zh: "灵技" },
      },
      {
        identity_id: "prowess/mono-red",
        parent_id: "prowess",
        subtype_id: "mono-red",
        display: { en: "Mono-Red Prowess", zh: "纯红灵技" },
      },
    ],
  };
}

test("resolves approved names only by stable identity and language", () => {
  const normalized = names.normalize(contract(), "modern");

  assert.equal(names.resolve(normalized, "prowess", null, "en", "Unknown"), "Prowess");
  assert.equal(
    names.resolve(normalized, "prowess", "mono-red", "zh", "未知套牌"),
    "纯红灵技"
  );
  assert.equal(names.resolveIdentity(normalized, "unknown", "zh", "未知套牌"), "未知套牌");
  assert.throws(
    () => names.resolve(normalized, "missing", null, "zh", "未知套牌"),
    /Missing approved classifier name/
  );
});

test("rejects malformed, duplicated, or incomplete name contracts", () => {
  const missingChinese = contract();
  missingChinese.names[0].display.zh = "";
  assert.throws(() => names.normalize(missingChinese, "modern"), /Invalid classifier name entry/);

  const duplicated = contract();
  duplicated.names.push({ ...duplicated.names[0] });
  assert.throws(() => names.normalize(duplicated, "modern"), /Invalid classifier name entry/);

  const orphanedSubtype = contract();
  orphanedSubtype.names.shift();
  assert.throws(() => names.normalize(orphanedSubtype, "modern"), /has no parent name/);
});

test("localizes matchup hierarchy labels without changing stable IDs", () => {
  const normalized = names.normalize(contract(), "modern");
  const localized = names.localizeHierarchy(normalized, {
    parents: [{ id: "prowess", name: "Prowess", subtype_ids: ["prowess/mono-red"] }],
    leaves: [{
      id: "prowess/mono-red",
      parent_id: "prowess",
      subtype_id: "mono-red",
      name: "Mono-Red",
      display_name: "Mono-Red Prowess",
    }],
  }, "zh", "未知套牌");

  assert.equal(localized.parents[0].id, "prowess");
  assert.equal(localized.parents[0].name, "灵技");
  assert.equal(localized.leaves[0].id, "prowess/mono-red");
  assert.equal(localized.leaves[0].display_name, "纯红灵技");
});
