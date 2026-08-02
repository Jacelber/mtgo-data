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
});

test("Chinese and English translation keys match exactly", () => {
  const zh = globalThis.P8I18n.translationKeys("zh").sort();
  const en = globalThis.P8I18n.translationKeys("en").sort();

  assert.deepEqual(zh, en);
  assert.ok(zh.length > 0);
});
