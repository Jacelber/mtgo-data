"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "../../assets/js/phase8/mtgo-controller.js"),
  "utf8"
);

test("Pinned Landing keeps its own week when rolling statistics advance", async () => {
  const week = { id: "2026-W35", start: "2026-08-24", end: "2026-08-30" };
  const prefix = "stats/pauper/mtgo/landing";
  const requested = [];
  const files = Object.fromEntries(["range", "completeness", "environment_decks", "feature_decks"]
    .map(key => [key, `weeks/${week.id}/${key}.json`]));
  const documents = {
    [`${prefix}/current.json`]: { format: "pauper", week, classifier: { digest: "abc" }, data_files: files },
    [`${prefix}/features/index.json`]: { format: "pauper", weeks: [] },
    "stats/pauper/mtgo/meta.json": { format: "pauper" },
    [`${prefix}/${files.range}`]: { format: "pauper", period: week, classifier_digest: "abc", total_decks: 192 },
    [`${prefix}/${files.completeness}`]: { format: "pauper", period: week },
    [`${prefix}/${files.environment_decks}`]: { format: "pauper", period: week, classifier_digest: "abc", decks: {} },
  };
  const context = { P8Runtime: {
    ResourceError: class ResourceError extends Error {},
    createJsonClient: () => ({ fetchJson: async key => {
      requested.push(key);
      assert.ok(key in documents, `Unexpected rolling or missing dependency: ${key}`);
      return documents[key];
    }, stage: async paths => ({ changed: true, get: key => documents[key], commit() {} }) }),
  } };
  context.globalThis = context;
  vm.runInNewContext(source, context);
  const result = await context.P8MtgoController.loadLanding("pauper", `${prefix}/current.json`, null,
    { includeEnvironmentDecks: true });
  assert.equal(result.range.total_decks, 192);
  assert.equal(result.environmentDecks.period.start, week.start);
  assert.equal(requested.some(key => /range_1w|completeness\/1w|decks_1w/.test(key)), false);
  const refresh = await context.P8MtgoController.stageLanding("pauper", `${prefix}/current.json`, null);
  assert.equal(refresh.changed, true);
  refresh.commit();
  documents[`${prefix}/${files.range}`].period = { start: "2026-08-31", end: "2026-09-06" };
  await assert.rejects(() => context.P8MtgoController.loadLanding("pauper", `${prefix}/current.json`));
  await assert.rejects(() => context.P8MtgoController.stageLanding("pauper", `${prefix}/current.json`, null));
  documents[`${prefix}/current.json`].data_files.range = "../../modern/mtgo/range_1w.json";
  await assert.rejects(() => context.P8MtgoController.loadLanding("pauper", `${prefix}/current.json`));
});

test("Landing history excludes empty archive weeks and never loads Pickup", async () => {
  const requested = [];
  const documents = {
    "stats/standard/mtgo/landing/current.json": {
      format: "standard",
      week: { id: "2099-W02", start: "2099-01-05", end: "2099-01-11" },
    },
    "stats/standard/mtgo/landing/features/index.json": {
      format: "standard",
      weeks: [
        { week: "2099-W02", file: "2099-W02.json", feature_count: 1 },
        { week: "2099-W01", file: "2099-W01.json", feature_count: 0 },
      ],
    },
    "stats/standard/mtgo/landing/features/2099-W02.json": {
      format: "standard",
      week: { id: "2099-W02" },
      features: { items: [{ destination_id: "deck:aaaaaaaaaaaaaaaaaaaa" }] },
    },
    "stats/standard/mtgo/landing/features/2099-W01.json": {
      format: "standard",
      week: { id: "2099-W01" },
      features: { items: [] },
    },
    "stats/standard/mtgo/meta.json": { format: "standard" },
    "stats/standard/mtgo/range_1w.json": {
      format: "standard",
      period: { start: "2099-01-05", end: "2099-01-11" },
    },
    "stats/standard/mtgo/completeness/1w.json": {
      format: "standard",
      period: { start: "2099-01-05", end: "2099-01-11" },
    },
  };
  const context = {
    P8Runtime: {
      ResourceError: class ResourceError extends Error {},
      createJsonClient: () => ({
        fetchJson: async requestPath => {
          requested.push(requestPath);
          return documents[requestPath];
        },
      }),
      dirname: value => path.posix.dirname(value),
      joinPath: (...values) => path.posix.join(...values),
    },
  };
  context.globalThis = context;
  vm.runInNewContext(source, context);

  const result = await context.P8MtgoController.loadLanding(
    "standard",
    "stats/standard/mtgo/landing/current.json",
    "2099-W01.json"
  );

  assert.equal(result.featureFile, "2099-W02.json");
  assert.equal(result.featureDocument.week.id, "2099-W02");
  assert.deepEqual(
    Array.from(result.featureIndex.weeks, item => item.file),
    ["2099-W02.json"]
  );
  assert.equal(requested.some(item => item.includes("/pickup/")), false);
  assert.equal(
    requested.includes("stats/standard/mtgo/landing/features/2099-W01.json"),
    false
  );
  assert.equal(
    requested.includes("stats/standard/mtgo/landing/features/2099-W02.json"),
    true
  );
});
