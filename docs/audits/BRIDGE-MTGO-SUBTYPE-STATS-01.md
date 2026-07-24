# BRIDGE-MTGO-SUBTYPE-STATS-01 audit

## Purpose

Prepare the existing MTGO Standard and Modern environment-statistics backend
for a later expandable archetype/subtype front end without mixing the work into
the Phase 7 Melee pipeline.

## Authorized scope

- retain selected subtype identity during MTGO event-statistics processing;
- add nested subtype range statistics and deck-construction outputs;
- preserve all parent-level Phase 6 results;
- extend the existing MTGO range and decks Schemas additively;
- regenerate committed Standard and Modern MTGO statistics deterministically;
- add focused, committed-baseline, Schema, and regression tests;
- update the authoritative statistical, architecture, roadmap, decision, and
  status documents;
- leave front-end rendering and production workflows unchanged.

Remote publication and production workflow dispatch are separate authorization
gates.

## Statistical contract

- Parent archetypes remain the default and primary aggregation.
- Subtype counts are direct record counts and conserve each parent.
- High-score and Top 8 shares retain the existing range-wide denominators.
- Parent share uses subtype deck count divided by parent deck count.
- Conversion uses subtype Top 8 count divided by subtype high-score count.
- Average points per round uses only the subtype's scores and theoretical
  rounds.
- Average deviation uses the subtype's own eligible four-week construction
  base.
- Best and average decks are built independently for each subtype.
- A maintained zero-observation subtype remains explicit.
- A null subtype under a subtype-defining parent is blocking; no residual
  subtype is synthesized.

## Compatibility contract

The frozen fixture
`tests/fixtures/mtgo/subtype_stats_parent_contract.json` records SHA-256 hashes
of parent-only projections from Phase 6 source commit
`e68e4e7ac989239213b82bd8e4b3cae4497cbe18`.

For all Standard and Modern 1-, 4-, 12-, and 36-week files:

- totals are unchanged;
- parent counts, rates, ordering, and deviations are unchanged;
- parent best and average deck payloads are unchanged;
- existing public paths and index documents are unchanged.

## Output contract

`stats/<format>/mtgo/range_<n>w.json` nests `subtypes` beneath an observed
subtype-defining parent. `stats/<format>/mtgo/decks_<n>w.json` nests the matching
subtype construction entries beneath that parent deck entry. Parents without
maintained subtype definitions omit the collection.

The output is an additive extension of the current `1.0.0` compatibility
profile. No existing required field or public path is removed or renamed.

## Validation record

Local validation results are recorded in `docs/STATUS.yaml` when the focused
implementation is complete. Owner acceptance, commit, PR, merge, production
dispatch, and any later front-end task remain separate stop points.
