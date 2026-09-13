"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

const context = vm.createContext({
  t: key => key,
  ReviewData: { literalRecord: counts => counts },
});
vm.runInContext(fs.readFileSync(path.join(__dirname, "../../assets/js/phase8/app-tabletop.js"), "utf8"), context);

test("overall uses eligible participant records, including unavailable decks and excluding DQ results", () => {
  const scope = {
    participant_count: 3,
    theoretical_rounds: 6,
    result_counts: { played_win: 3, played_loss: 3, played_draw: 0, drop_unplayed: 0 },
  };
  const result = context.tabletopOverall(scope, [
    { wins: 1, losses: 0, draws: 1 },
    { wins: 0, losses: 1, draws: 1 }, // No usable decklist; the played result still counts.
    { wins: 0, losses: 0, draws: 0 }, // DQ results were excluded by the generator.
  ]);
  assert.deepEqual(JSON.parse(JSON.stringify(result.literal_record)), { wins: 1, losses: 1, draws: 2 });
  assert.equal(result.deck_count, 3);
  assert.equal(result.completion_rate, 1);
  assert.deepEqual(JSON.parse(JSON.stringify(context.tabletopOverall(scope, []).literal_record)),
    { wins: 0, losses: 0, draws: 0 });
});
