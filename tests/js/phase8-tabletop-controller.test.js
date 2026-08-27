"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const runtimeSource = fs.readFileSync(
  path.join(__dirname, "../../assets/js/phase8/runtime.js"),
  "utf8"
);
const matchupSource = fs.readFileSync(
  path.join(__dirname, "../../assets/js/phase8/matchup-model.js"),
  "utf8"
);
const controllerSource = fs.readFileSync(
  path.join(__dirname, "../../assets/js/phase8/tabletop-controller.js"),
  "utf8"
);
const parityFixture = JSON.parse(fs.readFileSync(
  path.join(__dirname, "../fixtures/melee/multi_event_matchup_parity.json"),
  "utf8"
));

function response(value, { status = 200 } = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async text() {
      return JSON.stringify(value);
    },
  };
}

function controllerWith(documents) {
  const context = {
    AbortController,
    DOMException,
    TextEncoder,
    clearTimeout,
    document: { documentElement: { dataset: { statsBase: "./" } } },
    fetch: async url => (
      documents.has(url)
        ? response(documents.get(url))
        : response({ missing: url }, { status: 404 })
    ),
    setTimeout,
  };
  context.globalThis = context;
  vm.runInNewContext(runtimeSource, context);
  vm.runInNewContext(matchupSource, context);
  vm.runInNewContext(controllerSource, context);
  return context.P8TabletopController;
}

function eventOverview(eventId) {
  return {
    format: "modern",
    event_id: eventId,
    event_structure: "constructed_single_stage",
    event: {
      name: `Synthetic ${eventId}`,
      date: { start: "2026-08-01", end: "2026-08-02" },
      source_url: `https://melee.gg/Tournament/View/${eventId}`,
    },
    scopes: {
      all_constructed: {
        archetypes: [],
        participant_count: 0,
      },
    },
  };
}

function eventQuality() {
  return {
    format: "modern",
    issues: [],
    counts: {
      submitted_decklists: 0,
      missing_or_unavailable_decklists: 0,
    },
  };
}

function eventDocuments() {
  const inputs = new Map();
  parityFixture.event_inputs.forEach(input => {
    inputs.set(input.meta.event_id, input);
  });
  const documents = new Map([
    ["./stats/modern/melee/index.json", parityFixture.catalog],
  ]);
  inputs.forEach((input, eventId) => {
    const base = `./stats/modern/melee/events/${eventId}`;
    documents.set(`${base}/meta.json`, input.meta);
    documents.set(`${base}/matchup.json`, input.matchup);
    documents.set(`${base}/overview.json`, eventOverview(eventId));
    documents.set(`${base}/quality.json`, eventQuality());
  });
  return documents;
}

const canonicalIdentityOrder = ["alpha", "beta", "beta/one", "beta/two", "unknown"];

test("selected matchup events load as one catalog-admitted canonical set", async () => {
  const controller = controllerWith(eventDocuments());

  assert.deepEqual(
    Array.from(controller.parseSelectedEventIds("20,10,20")),
    ["10", "20"]
  );
  assert.equal(controller.parseSelectedEventIds("20,stale"), null);
  assert.deepEqual(
    Array.from(controller.resolveEventSelection(
      parityFixture.catalog.events,
      ["20", "999"],
      "20"
    ).eventIds),
    ["20"]
  );

  const active = await controller.loadEvent(
    "stats/modern/melee/index.json",
    "20",
    "modern",
    {},
    {
      includeMatchup: true,
      selectedEventIds: ["20", "10", "20"],
    }
  );
  assert.deepEqual(
    Array.from(active.selectedEventEntries, item => item.event_id),
    ["10", "20"]
  );
  assert.equal(active.eventEntry.event_id, "20");

  const selection = await controller.loadMultiEventMatchups(
    "stats/modern/melee/index.json",
    active.index,
    active.selectedEventEntries,
    "modern",
    canonicalIdentityOrder
  );
  assert.deepEqual(Array.from(selection.multiEventMatchup.event_ids), ["10", "20"]);
  assert.deepEqual(
    Array.from(selection.multiEventMatchup.hierarchy.parents, item => item.id),
    ["alpha", "beta", "unknown"]
  );
});

test("a rejected staged member cannot replace the last complete selection", async () => {
  const documents = eventDocuments();
  const controller = controllerWith(documents);
  const active = await controller.loadEvent(
    "stats/modern/melee/index.json",
    "20",
    "modern",
    {},
    { includeMatchup: true, selectedEventIds: ["10", "20"] }
  );
  const initial = await controller.loadMultiEventMatchups(
    "stats/modern/melee/index.json",
    active.index,
    active.selectedEventEntries,
    "modern",
    canonicalIdentityOrder
  );

  const changed = structuredClone(
    documents.get("./stats/modern/melee/events/10/meta.json")
  );
  changed.input.taxonomy_sha256 = "f".repeat(64);
  documents.set("./stats/modern/melee/events/10/meta.json", changed);

  await assert.rejects(controller.stageEvent(
    "stats/modern/melee/index.json",
    active.eventEntry,
    "modern",
    {},
    {
      includeMatchup: true,
      selectedEventEntries: active.selectedEventEntries,
      canonicalIdentityOrder,
    }
  ));

  const retained = await controller.loadMultiEventMatchups(
    "stats/modern/melee/index.json",
    active.index,
    active.selectedEventEntries,
    "modern",
    canonicalIdentityOrder
  );
  assert.deepEqual(
    retained.multiEventMatchup.leaf_matrix,
    initial.multiEventMatchup.leaf_matrix
  );
});

test("single-event scope restoration remains independent of multi-event scope", () => {
  const controller = controllerWith(eventDocuments());
  const events = [
    {
      event_id: "10",
      default_scope: "all_constructed",
      scope_order: ["day1", "day2", "all_constructed"],
    },
    {
      event_id: "20",
      default_scope: "all_constructed",
      scope_order: ["all_constructed"],
    },
  ];
  const multi = controller.resolveScopeState({
    events,
    selectedEventIds: ["10", "20"],
    activeEventId: "10",
    requestedScope: "day1",
    preferredSingleScope: "day1",
  });
  assert.equal(multi.scope, "all_constructed");

  const restored = controller.resolveScopeState({
    events,
    selectedEventIds: ["10"],
    activeEventId: "10",
    requestedScope: multi.scope,
    preferredSingleScope: "day1",
    restoreSingleScope: true,
  });
  assert.equal(restored.scope, "day1");
});
