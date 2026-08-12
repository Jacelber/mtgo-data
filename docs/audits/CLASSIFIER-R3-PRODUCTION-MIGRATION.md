# Classifier R3 production migration

## Status and authorization boundary

The Owner authorized `CLASSIFIER-R3-PRODUCTION-MIGRATION` for local development
on 2026-08-11 under the previously agreed contract. The isolated workspace is
`D:/dl/crawlerpj/.codex-workspaces/classifier-r3-20260810-01`, the branch is
`codex/classifier-r3-production-migration`, and the local R2 base is
`f586bff875c46c9f4cedcb3b84dc74427700f30c`. Push is disabled by the remote URL.

The Owner accepted the validated local implementation and authorized its local
commit on 2026-08-11. This authorization does not include a push, pull request,
merge, production dispatch, R4, or P12-10.

## Implemented production contract

- Production rules use Schema 1.1 and bind the reviewed semantic manifest by
  safe repository-relative path and exact SHA-256.
- The manifest is deliberately narrow and fail-closed. Unlisted cards add no
  semantic feature; missing or altered manifests and caller-supplied reserved
  markers are rejected.
- Modern contains exactly 70 parents, 54 subtypes, and 119 globally unique
  rules. Standard contains 72 parents, 11 subtypes, and 82 globally unique
  rules.
- The production rule files are deterministic transformations of the accepted
  R2 shadow files, including the existing Modern CC BY attribution.
- Reversing parent and rule order changes no frozen-corpus selection. Both
  formats have zero conflicts, invalid decks, and residual subtype results.

Exact production inputs:

| Artifact | SHA-256 |
| --- | --- |
| Modern rules | `df9c55e78e8fd8ed9e6cb18b0117a4d2947f207a302fe7148b3da00deee74045` |
| Standard rules | `d88c3342826343f07442c37d4652b4caac5be7f690d21122fc31884b63eb37f5` |
| Semantic feature manifest | `0cd94ee3a4d6974f88446a660e661943d1cc2c4d8a25891dd6d214931a6aa999` |

## Frozen-corpus equivalence

Every one of the 9,728 accepted R2 shadow records produces the same R3
production identity:

| Format | Records | Classified | Unknown | Conflicts | Invalid | Residual subtype |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Modern | 5,792 | 5,650 | 142 | 0 | 0 | 0 |
| Standard | 3,936 | 3,868 | 68 | 0 | 0 | 0 |

R1/R2 production-rule and Pickup inputs are copied under
`docs/audits/classifier-r2/baseline_rules/` and
`docs/audits/classifier-r2/baseline_pickup/`. Historical R1 and R2 tests and
builders now resolve those copies instead of the migrated production paths.

## Weekly Pickup migration

The deterministic migration validates the exact accepted R2 source hashes
before writing. Modern moves from 54 to 69 known parent keys by removing 6 and
adding 21. Standard moves from 62 to 60 known parent names by removing 7 and
adding 5. The resulting SHA-256 values are:

| Format | Migrated known-state SHA-256 |
| --- | --- |
| Modern | `9bdec0902255774386f7222d52a38d09e84ac194c97bb65db4640fecf87ff5fd` |
| Standard | `a77116cdec4173b86b7eb37b50beccd9a440e77d3eecb3e31297a56d20a1244c` |

The current Modern initializer discovers 67 observed parents; all are included
in the 69-key known state, whose other two accepted targets currently have zero
observations. A W29 candidate dry run reports zero new archetypes. No candidate,
comment, approval, published Pickup week, base, or Pickup index byte changes.

## Regenerated existing consumers

All generated changes come from the production commands or the bounded R3
migration tools; generated JSON was not hand-edited.

- Current committed MTGO data: Modern 6,784 decks, 6,607 classified and 177
  Unknown; Standard 4,733 decks, 4,616 classified and 117 Unknown. Both strict
  reports have zero conflicts and invalid decks.
- Existing 1/4/12/36-week statistics, matchup, completeness, hierarchy,
  metadata, reports, catalog, and already indexed W30/W31 Top 8 contents were
  regenerated. No new calendar week or public path was added.
- Event 434455 remains 362 submitted Modern decks: 351 classified, 11 Unknown,
  64 multiple matches, zero conflicts, zero invalid decks, and zero residual
  subtypes. Its derived closure is byte-reproducible under compatibility
  contract 1.2.
- Tabletop opportunity and statistics totals remain 2,910 theoretical rounds,
  2,903 effective theoretical rounds, and 1,394 eligible constructed matches.

## Protected-boundary proof

`data/modern/melee/events/434455.json` remains exactly 2,944,810 bytes with
SHA-256 `0b4296a9573a4facf4cfde1ce98569156f78fde6f5d2a1d3d662b54e2889e710`.
The raw snapshot closure, all retained responses, MTGO source events, formulas,
windows, match treatment, rounding, workflow files, front-end files, product
separation, request paths, and public paths are unchanged.

An initial generation attempt observed the current calendar week and proposed
four untracked W32 Top 8 files. R3 removed those untracked files and rebuilt
only the W30/W31 weeks already named by each committed index. The indexes retain
their original dates, entries, and exact no-final-newline byte convention.

## Validation result

Focused R3 production and frozen-history coverage passes. The first broad
cross-consumer run found only stale pre-R3 inventory assertions, temporary-test
roots missing the new manifest, and the intentionally versioned event 434455
derived-artifact compatibility closure. Those migrations were corrected; all
15 identified cases pass.

Final local validation:

- complete ordinary pytest shard: 851 passed, 8 deselected;
- independent committed-baseline shard: 8 passed, 851 deselected;
- Ruff: passed for changed production, migration, and test Python;
- strict mypy baseline: passed, 4 source files checked;
- repository validation: 147 Python, 17 JavaScript, 1,712 JSON, 37 YAML, 56
  references, and 2,110 hygiene entries passed;
- Standard and Modern rule validators: passed;
- public generated-JSON Schema validation: 73 documents passed; and
- Standard and Modern strict classification reports: passed with zero
  conflicts and invalid decks.

Final path review finds no source-event, raw snapshot, retained response,
front-end, workflow, Pickup candidate/week/index, Top8 index, W32, or public-path
change. `git diff --check` passes. The Owner accepted the validated local R3
implementation and authorized its local commit on 2026-08-11; it is not
published.

## Stop point

The Owner accepted R3 and authorized its local commit on 2026-08-11. After the
commit, stop without publishing, starting R4, rerunning or approving the
Landing shadow, choosing Landing thresholds or representative cards, or
starting P12-10.
