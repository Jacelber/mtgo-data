# P8-HOTFIX-MELEE-DFC-NORMALIZATION

Status: `owner accepted; remote publication authorized`

Date: 2026-07-30

Branch: `codex/p8-hotfix-melee-dfc-normalization`

Base: `96f0e234b7ca6db21c35ad00e541cc33fc2081b6`

## Purpose

Correct the real-data classification defect found by P8-11 without changing
the Modern taxonomy or the established MTGO Standard and Modern behavior.
Melee decklists commonly retain ordinary double-faced card names as
`front face // back face`, while the shared Modern rules use the front-face
name.

## Impact discovery

The first proposed implementation folded every ordinary double-faced name in
the global shared card-name normalizer. A frozen 3,936-deck Standard regression
test rejected that approach: one existing Standard deck changed from Unknown
to Mono-Black Demons because the current Standard rules intentionally contain
both full and front-face spellings of `Unholy Annex`.

The implementation was therefore narrowed to the Melee classification adapter.
This preserves:

- all 158 explicit OM1/SPM aliases;
- the shared deck normalizer and classifier;
- every existing Standard frozen-corpus parent result;
- committed MTGO Standard and Modern statistics;
- the retained normalized Melee event and its source card names.

Only the temporary deck representation passed from the Melee overlay builder
to the shared classifier uses the text before the first canonical ` // `
separator.

## Test-first implementation

The new adapter test supplied `Alpha Card // Alpha Back` to a rule requiring
`Alpha Card`. It failed as Unknown before the change and passed after the
single adapter normalization function was added.

No rule, priority, subtype, format configuration, Schema, workflow, source
archive, normalized event, or statistical formula changed.

## Regenerated products

The deterministic generator chain was run from the retained event and existing
Modern rules:

1. classification overlay;
2. Constructed opportunity ledger;
3. event overview, decks, and quality;
4. hierarchical matchup statistics;
5. event metadata and catalog packaging.

The candidate boundary accepted exactly seven changed generated paths:

- `data/modern/melee/classifications/434455.json`;
- `data/modern/melee/opportunities/434455.json`;
- `stats/modern/melee/events/434455/decks.json`;
- `stats/modern/melee/events/434455/matchup.json`;
- `stats/modern/melee/events/434455/meta.json`;
- `stats/modern/melee/events/434455/overview.json`;
- `stats/modern/melee/events/434455/quality.json`.

The global consumer catalog was rebuilt only as a check. Its sole difference
was the generated timestamp, so that unrelated change was excluded.

## Real-event result

Event `434455` retains all 362 submitted decklists:

- classified: 290 to 352;
- Unknown: 72 to 10;
- conflicts: 0;
- invalid decks: 0;
- newly classified Boros Energy: 45;
- newly classified Ruby Storm: 16;
- newly classified Mardu Energy: 1.

The 62 recovered classifications exactly match the P8-11 diagnostic. The ten
remaining decks stay explicit Unknown; this task does not guess new taxonomy
rules for them.

Statistical opportunity and match boundaries are unchanged:

- theoretical Constructed opportunities: 2,910;
- effective opportunities: 2,903;
- included matches: 1,394;
- Day 1 included matches: 861;
- Day 2 included matches: 533;
- disqualified-player match exclusions: 6.

The observed event hierarchy grows from 29 to 32 parent rows and from 55 to 58
leaf rows because Boros Energy, Mardu Energy, and Ruby Storm are now observed
rather than absorbed by Unknown.

## Validation

- Red test before implementation: 3 expected failures.
- Focused shared/adapter tests after the final narrowed design: 19 passed.
- Affected Melee generator and committed-artifact tests: 49 passed.
- Phase 8 consumer and production-entry tests: 23 passed.
- MTGO Standard/Modern regression tests: 62 passed.
- Complete pytest suite: 594 passed across all 66 test files.
- Melee production-candidate validation: passed with seven generated paths.
- Repository validation: 124 Python, 1,590 JSON, 21 YAML, 30 references, and
  1,855 hygiene checks passed.
- Standard and Modern rule validation: passed.
- Public generated-JSON Schema validation: 69 documents passed.
- JavaScript syntax: 9 files passed `node --check`.
- `git diff --check`: passed.

## Stop point

The owner accepted the local implementation and authorized commit, push,
pull-request creation, and merge on 2026-07-30.

After publication, P8-11 must repeat the affected real-browser checks before
Phase 8 completion or its recovery tag can be authorized.
