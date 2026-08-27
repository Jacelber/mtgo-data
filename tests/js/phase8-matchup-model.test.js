"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const matchup = require("../../assets/js/phase8/matchup-model.js");
require("../../assets/js/phase8/i18n.js");

const multiEventParityFixture = JSON.parse(fs.readFileSync(
  path.join(__dirname, "../fixtures/melee/multi_event_matchup_parity.json"),
  "utf8"
));

function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

function applyFixtureOperation(target, operation) {
  const parent = operation.path.slice(0, -1).reduce((current, segment) => (
    current[segment]
  ), target);
  const key = operation.path.at(-1);
  if (operation.op === "set") {
    parent[key] = deepClone(operation.value);
    return;
  }
  if (operation.op === "delete") {
    delete parent[key];
    return;
  }
  if (operation.op === "truncate") {
    parent[key].length = operation.length;
    return;
  }
  throw new Error(`unsupported fixture operation: ${operation.op}`);
}

function record(seed, rowIndex, columnIndex) {
  return {
    wins: (seed + rowIndex * 3 + columnIndex) % 7,
    losses: (seed + rowIndex + columnIndex * 2) % 5,
    draws: (seed + rowIndex + columnIndex) % 3,
  };
}

function sumRecords(records) {
  return records.reduce(
    (total, current) => ({
      wins: total.wins + current.wins,
      losses: total.losses + current.losses,
      draws: total.draws + current.draws,
    }),
    { wins: 0, losses: 0, draws: 0 }
  );
}

function documentFor(seed) {
  const leaves = ["alpha/one", "alpha/two", "bravo/one", "bravo/two"];
  const leafMatrix = {};
  leaves.forEach((rowId, rowIndex) => {
    leafMatrix[rowId] = {};
    leaves.forEach((columnId, columnIndex) => {
      leafMatrix[rowId][columnId] = record(seed, rowIndex, columnIndex);
    });
  });
  return {
    hierarchical: true,
    min_sample_hint: 20,
    hierarchy: {
      parents: [
        { id: "alpha", name: "Alpha", subtype_ids: leaves.slice(0, 2), expandable: true },
        { id: "bravo", name: "Bravo", subtype_ids: leaves.slice(2), expandable: true },
      ],
      leaves: leaves.map(id => ({
        id,
        parent_id: id.split("/")[0],
        display_name: id,
      })),
    },
    parent_order: ["alpha", "bravo"],
    leaf_matrix: leafMatrix,
  };
}

function leafIdsFor(node) {
  return node.kind === "subtype" ? [node.id] : node.id === "alpha"
    ? ["alpha/one", "alpha/two"]
    : ["bravo/one", "bravo/two"];
}

function assertRecord(actual, expected) {
  assert.equal(actual.wins, expected.wins);
  assert.equal(actual.losses, expected.losses);
  assert.equal(actual.draws, expected.draws);
  assert.equal(actual.matches, expected.wins + expected.losses + expected.draws);
  if (actual.matches) {
    assert.equal(actual.win_rate, actual.wins / actual.matches);
  } else {
    assert.equal(actual.win_rate, null);
  }
}

test("matchup views preserve literal record aggregation properties", () => {
  for (let seed = 0; seed < 20; seed += 1) {
    const document = documentFor(seed);
    const collapsed = matchup.buildView(document, [], []);
    const expanded = matchup.buildView(document, ["alpha"], ["bravo"]);

    for (const view of [collapsed, expanded]) {
      for (const row of view.rows) {
        const expectedOverall = sumRecords(
          leafIdsFor(row).flatMap(rowId => Object.values(document.leaf_matrix[rowId]))
        );
        assertRecord(view.overall[row.id], expectedOverall);
        for (const column of view.columns) {
          const expectedCell = sumRecords(
            leafIdsFor(row).flatMap(rowId => leafIdsFor(column).map(
              columnId => document.leaf_matrix[rowId][columnId]
            ))
          );
          assertRecord(view.matrix[row.id][column.id], expectedCell);
        }
      }
    }
  }
});

test("active matchup documents omit leaves with no played matches", () => {
  const document = documentFor(1);
  document.leaf_matrix["bravo/two"] = {};
  Object.values(document.leaf_matrix).forEach(columns => {
    delete columns["bravo/two"];
  });

  const active = matchup.activeMatchupDocument(document, 20);

  assert.deepEqual(active.hierarchy.leaves.map(leaf => leaf.id), [
    "alpha/one",
    "alpha/two",
    "bravo/one",
  ]);
  assert.deepEqual(
    active.hierarchy.parents.find(parent => parent.id === "bravo").subtype_ids,
    ["bravo/one"]
  );
  assert.equal(
    active.hierarchy.parents.find(parent => parent.id === "bravo").expandable,
    false
  );
  assert.equal(matchup.resolveFilterIdentity(active, "bravo/two"), null);
  assert.equal(matchup.resolveFilterIdentity(active, "bravo").id, "bravo");
});

test("exact matchup row filters preserve stable order and column expansion", () => {
  const document = documentFor(3);
  const expandedRows = new Set();
  const expandedColumns = new Set(["alpha"]);

  const filtered = matchup.buildVisibleView(
    document,
    expandedRows,
    expandedColumns,
    new Set(["bravo", "alpha/two"])
  );

  assert.deepEqual(filtered.rows.map(node => node.id), ["alpha/two", "bravo"]);
  assert.deepEqual(filtered.columns.map(node => node.id), [
    "alpha",
    "alpha/one",
    "alpha/two",
    "bravo",
  ]);
  assert.deepEqual([...expandedRows], []);
  assert.deepEqual([...expandedColumns], ["alpha"]);
  assertRecord(
    filtered.matrix["alpha/two"]["bravo"],
    sumRecords([
      document.leaf_matrix["alpha/two"]["bravo/one"],
      document.leaf_matrix["alpha/two"]["bravo/two"],
    ])
  );

  expandedRows.add("bravo");
  const disclosedFiltered = matchup.buildVisibleView(
    document,
    expandedRows,
    expandedColumns,
    new Set(["bravo", "alpha/two"])
  );
  assert.deepEqual(disclosedFiltered.rows.map(node => node.id), [
    "alpha/two", "bravo", "bravo/one", "bravo/two",
  ]);

  const unfiltered = matchup.buildVisibleView(document, expandedRows, expandedColumns, null);
  assert.deepEqual(unfiltered.rows.map(node => node.id), [
    "alpha", "bravo", "bravo/one", "bravo/two",
  ]);
});

test("mainstream eligibility uses the stored parent share and excludes Unknown", () => {
  const mtgo = matchup.mainstreamParentIds([
    { id: "alpha", high_score_share: 0.02 },
    { id: "bravo", high_score_share: 0.0199 },
    { id: "unknown", high_score_share: 0.75 },
    { id: "missing", high_score_share: null },
  ], "id", "high_score_share");
  const tabletop = matchup.mainstreamParentIds([
    { archetype_id: "alpha", metagame_share: 0.2 },
    { archetype_id: "bravo", metagame_share: 0.01 },
  ], "archetype_id", "metagame_share");

  assert.deepEqual([...mtgo], ["alpha"]);
  assert.deepEqual([...tabletop], ["alpha"]);
  assert.equal(
    matchup.mainstreamParentIds(
      [{ id: "alpha", high_score_share: null }],
      "id",
      "high_score_share"
    ),
    null
  );
});

test("mainstream projection constrains both parent axes without changing saved state", () => {
  const document = documentFor(9);
  const before = JSON.stringify(document);
  const expandedRows = new Set(["alpha", "bravo"]);
  const expandedColumns = new Set(["alpha", "bravo"]);
  const selectedRows = new Set(["alpha/two", "bravo"]);
  const mainstreamParents = new Set(["alpha"]);

  const mainstream = matchup.buildVisibleView(
    document,
    expandedRows,
    expandedColumns,
    selectedRows,
    mainstreamParents
  );

  assert.deepEqual(mainstream.rows.map(node => node.id), ["alpha/two"]);
  assert.deepEqual(mainstream.columns.map(node => node.id), [
    "alpha", "alpha/one", "alpha/two",
  ]);
  assert.deepEqual([...selectedRows], ["alpha/two", "bravo"]);
  assert.deepEqual([...expandedRows], ["alpha", "bravo"]);
  assert.deepEqual([...expandedColumns], ["alpha", "bravo"]);
  assert.equal(JSON.stringify(document), before);

  const restored = matchup.buildVisibleView(
    document,
    expandedRows,
    expandedColumns,
    selectedRows
  );
  assert.deepEqual(restored.rows.map(node => node.id), [
    "alpha/two", "bravo", "bravo/one", "bravo/two",
  ]);
  assert.deepEqual(restored.columns.map(node => node.id), [
    "alpha", "alpha/one", "alpha/two", "bravo", "bravo/one", "bravo/two",
  ]);
});

test("matchup filter candidates expose parent-subtype hierarchy without duplicate rows", () => {
  const document = documentFor(5);
  const candidates = matchup.filterCandidates(document);
  assert.deepEqual(candidates.map(parent => parent.id), ["alpha", "bravo"]);
  assert.deepEqual(candidates[0].children.map(child => child.id), ["alpha/one", "alpha/two"]);
  assert.deepEqual(candidates[1].children.map(child => child.id), ["bravo/one", "bravo/two"]);

  const active = matchup.activeMatchupDocument(document, 20);
  const singleLeafBravo = active.hierarchy.parents.find(parent => parent.id === "bravo");
  singleLeafBravo.subtype_ids = ["bravo/one"];
  singleLeafBravo.expandable = false;
  active.hierarchy.leaves = active.hierarchy.leaves.filter(leaf => leaf.id !== "bravo/two");
  delete active.leaf_matrix["bravo/two"];
  Object.values(active.leaf_matrix).forEach(columns => delete columns["bravo/two"]);
  const noDuplicate = matchup.buildVisibleView(active, [], [], new Set(["bravo"]));
  assert.equal(noDuplicate.rows.filter(node => node.id === "bravo").length, 1);
});

test("matchup filter identity resolution rejects unavailable identities", () => {
  const document = documentFor(7);

  assert.deepEqual(matchup.resolveFilterIdentity(document, "alpha"), {
    id: "alpha",
    kind: "archetype",
    name: "Alpha",
    parentId: "alpha",
    parentName: "Alpha",
    expandable: true,
    showAxisToggle: true,
  });
  assert.equal(matchup.resolveFilterIdentity(document, "alpha/two").parentId, "alpha");
  assert.equal(matchup.resolveFilterIdentity(document, "missing"), null);

  document.parent_order = ["bravo"];
  assert.equal(matchup.resolveFilterIdentity(document, "alpha"), null);
  assert.equal(matchup.resolveFilterIdentity(document, "alpha/two"), null);
});

test("Chinese and English translation keys match exactly", () => {
  const zh = globalThis.P8I18n.translationKeys("zh").sort();
  const en = globalThis.P8I18n.translationKeys("en").sort();

  assert.deepEqual(zh, en);
  assert.ok(zh.length > 0);
});

test("multi-event aggregation matches the Python contract fixture exactly", () => {
  const result = matchup.buildMultiEventMatchupContract(
    deepClone(multiEventParityFixture.event_inputs),
    deepClone(multiEventParityFixture.canonical_hierarchy),
    deepClone(multiEventParityFixture.catalog)
  );

  assert.deepEqual(result, multiEventParityFixture.expected);
  assert.deepEqual(matchup.MULTI_EVENT_ERROR_CODES, [
    "active_taxonomy_mismatch",
    "blocking_quality",
    "catalog_compatibility_mismatch",
    "catalog_event_missing",
    "catalog_identity_mismatch",
    "duplicate_catalog_event",
    "duplicate_event_conflict",
    "event_identity_mismatch",
    "format_mismatch",
    "identity_metadata_mismatch",
    "invalid_contract_input",
    "invalid_event_input",
    "matrix_invariant_failed",
    "missing_active_taxonomy",
    "missing_all_constructed_scope",
    "missing_catalog_compatibility",
    "product_mismatch",
    "provenance_mismatch",
    "source_mismatch",
    "taxonomy_digest_mismatch",
    "taxonomy_version_mismatch",
    "too_few_events",
    "unsupported_catalog_schema",
    "unsupported_matchup_schema",
  ]);
});

test("multi-event admission rejects the same incompatible fixture mutations as Python", () => {
  multiEventParityFixture.rejections.forEach(rejection => {
    const candidate = deepClone({
      event_inputs: multiEventParityFixture.event_inputs,
      catalog: multiEventParityFixture.catalog,
    });
    rejection.operations.forEach(operation => applyFixtureOperation(candidate, operation));

    assert.throws(
      () => matchup.buildMultiEventMatchupContract(
        candidate.event_inputs,
        deepClone(multiEventParityFixture.canonical_hierarchy),
        candidate.catalog
      ),
      error => (
        error instanceof matchup.MultiEventMatchupError
        && error.code === rejection.error_code
      ),
      rejection.name
    );
  });
});
