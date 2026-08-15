# Pickup review classifier corrections

Task ID: `CLASSIFIER-PICKUP-REVIEW-CORRECTIONS-20260815`

## Objective

Correct the two classification errors found during the bounded 2026-W32 Pickup
review without changing the accepted Landing thresholds or creating new parent
or subtype identities:

- classify the two reviewed Standard shells as `leyline-aggro/izzet` instead
  of `izzet-fling`; and
- classify the reviewed Modern Broodscale shell with main-deck red-producing
  lands as `broodscale-combo/gruul` instead of
  `broodscale-combo/mono-green`.

## Authorized local scope

The Owner authorized local implementation on 2026-08-15. Commit, remote
publication, merge, workflow dispatch, production fetch, and production
publication remain unauthorized.

The repair must preserve all existing parent, subtype, and rule IDs. It may add
one explicit Standard rule for the reviewed Leyline-style Izzet shell, adjust
only the priorities needed to resolve the accepted overlap, and extend the
reviewed semantic-feature manifest only for the exact red-producing lands used
by the affected Modern deck. The Modern Gruul and Mono-Green Broodscale rules
must then use the shared main-deck red-source marker instead of one named land.

## Required validation

- Add exact-deck regression coverage for both reviewed Standard decks and the
  reviewed Modern deck.
- Prove deterministic rule-order behavior and preserve conflict, invalid-deck,
  Unknown, and residual-subtype reporting.
- Compare every current Standard and Modern MTGO deck, both frozen classifier
  corpora, and retained Modern Tabletop event `434455` before and after the
  repair. Record every identity transition; unexplained transitions fail the
  task.
- Regenerate only existing classification-derived artifacts whose facts or
  classifier provenance change. Do not fetch or retain source responses and do
  not alter protected event `434455` source bytes.
- For the later Pickup review return path, reclassify only the affected
  format's current-week candidates and prior four complete reference weeks.
  Do not repeat unaffected human review.

Existing passed evidence remains valid unless this task changes its code,
fixture, dependency, bootstrap, or input. A passed test must not be rerun.
Unknown failures permit only the failed node and smallest affected set; known
controlled errors are recorded without a complete rerun.

## Stop point

Stop after local implementation, bounded validation, impact reporting, and
Owner review. Do not commit or publish without a separate Owner authorization.

## Local result

The exact reviewed W32 decks now select:

- `itstime`, Standard event `12850815`: `leyline-aggro/izzet` through
  `leyline-aggro-izzet-talent-shell`;
- `MacIsaac`, Standard event `12850613`: `leyline-aggro/izzet` through
  `leyline-aggro-izzet`; and
- `manohito`, Modern event `12851108`: `broodscale-combo/gruul` through
  `broodscale-combo-gruul`.

Complete de-identified impact comparison found:

| Corpus | Accepted transitions | Count |
| --- | --- | ---: |
| Current Standard, 4,925 decks | Izzet Fling -> Leyline Aggro / Izzet | 84 |
| Current Standard, 4,925 decks | Izzet Prowess -> Leyline Aggro / Izzet | 1 |
| Frozen Standard, 3,936 decks | Izzet Fling -> Leyline Aggro / Izzet | 56 |
| Frozen Standard, 3,936 decks | Izzet Prowess -> Leyline Aggro / Izzet | 1 |
| Current Modern, 7,104 decks | Mono-Green -> Gruul Broodscale | 157 |
| Frozen Modern, 5,792 decks | Mono-Green -> Gruul Broodscale | 117 |
| Tabletop event 434455, 362 decks | Mono-Green -> Gruul Broodscale | 12 |

There are no other identity transitions and no conflict, invalid-deck, or
residual-subtype result. Strict current reports retain 15 Standard Unknown and
three Modern Unknown results; all accepted transitions remain classified.

Eight new focused regression cases passed. The complete-impact node then
stopped on a test allowlist that omitted the one actual-Leyline Prowess
transition. The allowlist was corrected after a read-only diagnosis. Under the
Owner's no-rerun rule, that known controlled test-definition failure was not
rerun and is not represented as a pass. The previously unexecuted Modern and
event `434455` comparisons were completed directly once. Five affected
rule-rebuild, manifest, Schema, and prior Spellementals tests passed once;
nine event-compatibility and public-Schema tests passed once. Ruff passed for
all changed Python files. No Playwright or complete local pytest suite ran.

Existing Standard and Modern MTGO statistics, matchups, completeness,
hierarchy, metadata, strict reports, catalog, and indexed W30-W32 Top 8 files
were rebuilt once. Event `434455` classification and derived closure were
rebuilt once, while its normalized event stayed byte-identical at SHA-256
`0b4296a9573a4facf4cfde1ce98569156f78fde6f5d2a1d3d662b54e2889e710`.
