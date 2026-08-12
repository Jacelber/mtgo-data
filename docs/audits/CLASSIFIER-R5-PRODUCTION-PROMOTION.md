# Classifier R5 production promotion

## Status and authorization boundary

The Owner authorized `CLASSIFIER-R5-PRODUCTION-PROMOTION` for local
implementation on 2026-08-12. The artifact-impact declaration is
`statistical_json_structure`. The isolated workspace is
`D:/dl/crawlerpj/.codex-workspaces/classifier-r5-20260812-01`, the branch is
`codex/classifier-r5-production-promotion`, and the R4 base is
`b3f379a95284ecbe5da21124a4be651bb346e602`. Push is disabled.

For publication, the complete R1-R5 chain was replayed in the fresh independent
workspace
`D:/dl/crawlerpj/.codex-workspaces/classifier-r5-publication-20260812-01`
from verified remote `master` commit
`f8a4714c07861b104193721524ac5669cef69084`. That base includes the two later
production-data refreshes and the PR 200 dynamic-consumer validation hotfix.
No source fetch or production workflow dispatch occurred during reconciliation.

The Owner accepted the complete local implementation on 2026-08-12 and
separately authorized its local commit, reconciliation with the current remote
`master`, Ready pull request, complete CI, and merge. Manual production
dispatch, the Landing shadow, threshold decisions, representative-card work,
P12-10, and every later task remain unauthorized.

## Exact accepted inputs

| Artifact | SHA-256 |
| --- | --- |
| R4 Modern shadow | `5bff0207af7e43d3b59807c102ab323a0e51109e7543e27e59f293bade632b31` |
| R4 Standard shadow | `b72aa3fcb0202eb9bc5d9c1f6f88abbe76d8d8ca29923662e3a75f8e54d3da74` |
| R3 semantic manifest | `0cd94ee3a4d6974f88446a660e661943d1cc2c4d8a25891dd6d214931a6aa999` |
| Frozen R3 Modern rules | `df9c55e78e8fd8ed9e6cb18b0117a4d2947f207a302fe7148b3da00deee74045` |
| Frozen R3 Standard rules | `d88c3342826343f07442c37d4652b4caac5be7f690d21122fc31884b63eb37f5` |

The production rule files are byte-identical to their accepted R4 shadows.
Modern has 127 parents, 70 subtypes, and 205 rules. Standard has 102 parents,
11 subtypes, and 126 rules. No semantic-feature manifest change was needed.

## Pickup known-state migration

The R3 known states are frozen beneath `docs/audits/classifier-r4/`. Modern
moves from 69 to 126 known parent IDs by adding the 57 accepted R4 parents.
Standard moves from 60 to 91 known parent names by adding 31 parents, migrating
`Temur Elementals` to `Ramp Elementals`, and excluding retired
`Grixis Elementals`. This prevents every newly accepted or renamed identity
from appearing as a false new deck.

No Pickup candidate, reviewer comment, approval, published week, base, or
index is rewritten.

## Regenerated existing consumers

All generated JSON changes come from maintained production commands or bounded
R5 tools; no generated report or statistic was hand-edited.

- Publication-baseline MTGO Modern: 6,944 classified, zero Unknown, conflicts, or invalid
  decks.
- Publication-baseline MTGO Standard: 4,821 classified, eight non-blocking
  fail-closed Unknown, zero conflicts, and zero invalid decks. One is the
  accepted R4 intentional Unknown and seven come from post-review production
  events; R5 adds no unreviewed classifier judgment for them.
- Frozen Modern: all 5,792 classified. Frozen Standard: 3,928 classified and
  eight historical Unknown.
- Existing 1/4/12/36-week statistics, matchup, completeness, hierarchy,
  metadata, reports, catalog, and only indexed W30/W31/W32 Top 8 contents are
  refreshed.
- Event 434455 has 362 classified decklists, zero Unknown, conflicts, invalid
  decks, or residual subtypes. Its 2,910 theoretical rounds, 2,903 effective
  theoretical rounds, and 1,394 eligible Constructed matches are unchanged.
- Event 434455 exact derived-artifact compatibility advances from 1.2 to 1.3.

## Protected boundaries

`data/modern/melee/events/434455.json` remains exactly 2,944,810 bytes with
SHA-256 `0b4296a9573a4facf4cfde1ce98569156f78fde6f5d2a1d3d662b54e2889e710`.
The raw snapshot closure, retained responses, MTGO source events, formulas,
windows, match treatment, rounding, workflows, front-end files, product
separation, request paths, and public paths remain unchanged. No new Top 8
week exists.

## Validation result

- complete ordinary pytest shard: 938 passed, 8 committed-baseline tests
  deselected;
- independent committed-baseline shard: 8 passed, 938 ordinary tests
  deselected;
- Ruff: passed for all changed Python files;
- strict mypy baseline: passed, 4 source files checked;
- repository validation: 159 Python, 17 JavaScript, 1,747 JSON, 51 YAML, 56
  references, and 2,174 hygiene entries passed;
- Standard and Modern production-rule validation: passed;
- public generated-JSON Schema validation: 77 documents passed;
- Standard frozen quality baseline: passed with 3,936 records, 71 Unknown, and
  947 multiple matches;
- current strict classification reports: Modern 6,944 decks with zero Unknown,
  conflicts, or invalid decks; Standard 4,829 decks with eight non-blocking
  Unknown and zero conflicts or invalid decks; and
- Playwright real-browser regression: 77 tests passed.

Final path review finds no source-event, raw snapshot, retained response,
front-end, workflow, Pickup candidate/week/index, Top 8 index, newly created
calendar week, event-whitelist, or public-path change. The existing W32 files
introduced by the remote production refresh are reclassified in place.
`git diff --check` passes. The local implementation was accepted by the Owner
on 2026-08-12.

## Stop point

Complete only the authorized R5 commit, current-`master` reconciliation, Ready
pull request, complete CI, merge, and automatic Pages verification. Do not
dispatch production, rerun the Landing shadow, select thresholds or
representative cards, or start P12-10.
