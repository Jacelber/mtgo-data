# P8-CLOSEOUT — Phase 8 completion reconciliation

Status: `owner accepted; remote publication and recovery tag authorized`

Date: 2026-07-30

Branch: `codex/p8-closeout-v2`

Base: `10e6780c2c48585cb05d02492ce81702cbb869c1`

## Purpose

Reconcile the completed Phase 8 implementation, the P8-11 regression result,
the Melee double-faced-card normalization hotfix, and the repeated deployed
browser acceptance into one durable phase-completion record.

This task changes no production code, generated data, Schema, workflow,
classifier, taxonomy, public path, statistical formula, or source policy.

## Publication reconciliation

P8-11:

- pull request: #127;
- implementation commit:
  `321792414cc6697d1c3afbbf1679c6267f46c284`;
- merge commit: `96f0e234b7ca6db21c35ad00e541cc33fc2081b6`;
- PR validation: `30502479440`;
- master admission: `30503074938`;
- Pages deployment: `30503074350`.

P8-HOTFIX-MELEE-DFC-NORMALIZATION:

- pull request: #128;
- implementation commit:
  `a8e7fe098feafbb7faefd39d584422c20a9c4ffd`;
- merge commit: `10e6780c2c48585cb05d02492ce81702cbb869c1`;
- PR validation: `30504274023`;
- master admission: `30504857129`;
- Pages deployment: `30504856795`.

## Cleared blocker

The focused Melee adapter fix recovered exactly 62 event `434455` decklists
without changing MTGO classification:

- classified decklists: 290 to 352;
- Unknown decklists: 72 to 10;
- recovered Boros Energy: 45;
- recovered Ruby Storm: 16;
- recovered Mardu Energy: 1;
- classification conflicts: 0;
- invalid decks: 0.

Repeated deployed acceptance confirmed 352 classified and ten Unknown
decklists, 211 classified and nine Unknown Day 2 decklists, 32 observed parent
rows, 58 observed leaf rows, and zero browser console warnings or errors.
`BLOCK-P8-11-MELEE-DFC-NORMALIZATION` is resolved.

The ten remaining Unknown decks are retained explicitly. Assigning new
taxonomy rules for them is not part of Phase 8 closeout.

## Low-sample decision reconciliation

P8-07 introduced and the owner accepted one shared presentation warning at
fewer than 20 valid matches. P8-08 through P8-11 retained that value in the
production consumer, but OPEN-002 and the statistical specification still
described it as pending.

DEC-060 closes that documentation gap. The value is a visual caution marker,
not a reliability guarantee, match-eligibility rule, publication gate, or
change to `wins / (wins + losses + draws)`. The actual sample count and 95%
Wilson interval remain available.

## Phase 8 acceptance criteria

- format is the primary selector;
- five product slots are discovered from the generated catalog;
- MTGO and Tabletop entry points, data, caches, and statistics remain separate;
- parent/subtype expansion works in statistics and on both matchup axes;
- parents with fewer than two active subtypes expose no redundant control;
- visible subtype labels are self-contained;
- construction detail uses the most specific maintained identity;
- weekly MTGO Top 8 exact-deck and immutable comparison-base detail works;
- Videre and modeled high-score completeness use generated source evidence;
- event `434455` is independently available through Tabletop Major Events;
- event overview and matchup load from event-specific public JSON;
- Standard and Modern baselines, public paths, Pages behavior, and source
  separation pass regression;
- repeated owner-facing browser acceptance after the classification hotfix
  passed.

## Validation

- Phase 8 closeout, contract, consumer, review, and production-entry tests:
  41 passed.
- Complete pytest suite: 594 passed across 66 test files.
- Repository validation: 124 Python, 1,590 JSON, 21 YAML, 30 references, and
  1,856 hygiene checks passed.
- Standard and Modern rule validation: passed.
- Public generated-JSON Schema validation: 69 documents passed.
- JavaScript syntax: 9 files passed `node --check`.
- Final YAML parsing, documentation consistency, changed-path review, and
  `git diff --check`: passed.

## Stop point

The owner accepted this closeout on 2026-07-30 and authorized its commit, push,
pull request, merge, and the `phase-8-format-first-frontends` recovery tag.
Phase 9 planning and implementation remain separately controlled.
