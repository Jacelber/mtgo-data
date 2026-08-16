"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const matchup = require("../../assets/js/phase8/matchup-model.js");
require("../../assets/js/phase8/i18n.js");

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
