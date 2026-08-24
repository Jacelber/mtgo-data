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

test("Landing history excludes empty archive weeks and never loads Pickup", async () => {
  const requested = [];
  const documents = {
    "stats/standard/mtgo/landing/current.json": {
      format: "standard",
      week: { id: "2026-W33", start: "2026-08-10", end: "2026-08-16" },
    },
    "stats/standard/mtgo/landing/features/index.json": {
      format: "standard",
      weeks: [
        { week: "2026-W33", file: "2026-W33.json", feature_count: 14 },
        { week: "2026-W27", file: "2026-W27.json", feature_count: 0 },
      ],
    },
    "stats/standard/mtgo/landing/features/2026-W33.json": {
      format: "standard",
      week: { id: "2026-W33" },
      features: { items: [{ destination_id: "deck:aaaaaaaaaaaaaaaaaaaa" }] },
    },
    "stats/standard/mtgo/landing/features/2026-W27.json": {
      format: "standard",
      week: { id: "2026-W27" },
      features: { items: [] },
    },
    "stats/standard/mtgo/meta.json": { format: "standard" },
    "stats/standard/mtgo/range_1w.json": {
      format: "standard",
      period: { start: "2026-08-10", end: "2026-08-16" },
    },
    "stats/standard/mtgo/completeness/1w.json": {
      format: "standard",
      period: { start: "2026-08-10", end: "2026-08-16" },
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
    "2026-W27.json"
  );

  assert.equal(result.featureFile, "2026-W33.json");
  assert.equal(result.featureDocument.week.id, "2026-W33");
  assert.deepEqual(
    Array.from(result.featureIndex.weeks, item => item.file),
    ["2026-W33.json"]
  );
  assert.equal(requested.some(item => item.includes("/pickup/")), false);
  assert.equal(
    requested.includes("stats/standard/mtgo/landing/features/2026-W27.json"),
    false
  );
  assert.equal(
    requested.includes("stats/standard/mtgo/landing/features/2026-W33.json"),
    true
  );
});
