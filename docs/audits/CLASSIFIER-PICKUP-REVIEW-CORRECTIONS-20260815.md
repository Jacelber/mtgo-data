# Pickup review classifier corrections

Task ID: `CLASSIFIER-PICKUP-REVIEW-CORRECTIONS-20260815`

## Objective

Correct the two classification errors found during the bounded 2026-W32 Pickup
review without changing the accepted Landing thresholds or creating new parent
or subtype identities:

- classify the reviewed four-Leyline Standard build as
  `leyline-aggro/izzet`, while keeping zero- and single-Leyline Callous
  Sell-Sword builds in `izzet-fling`; and
- classify the reviewed Modern Broodscale shell with main-deck red-producing
  lands as `broodscale-combo/gruul` instead of
  `broodscale-combo/mono-green`.

## Corrected Standard boundary

The first proposed implementation incorrectly generalized one zero-Leyline
Talent/Slickshot/Otter/Wild Ride list into a new
`leyline-aggro-izzet-talent-shell` rule and raised Leyline Aggro above Izzet
Fling. The reviewed Pickup Leyline list did not justify that rule: the actual
`MacIsaac` list in Standard event `12850613` has four main-deck Leyline of
Resonance and already matches the maintained `leyline-aggro-izzet` rule. The
`itstime` list in event `12850815` has zero main-deck Leyline and three Callous
Sell-Sword, so it belongs to Izzet Fling.

The corrected implementation therefore:

- deletes `leyline-aggro-izzet-talent-shell` completely;
- restores the Leyline Aggro priorities to Izzet 27040, Gruul 27030, Boros
  27020, Rakdos 27010, and Mono-Red 27000;
- leaves Izzet Fling at priority 53000; and
- adds `Leyline of Resonance`, main deck, maximum count one to the existing
  `izzet-fling-primary` rule.

The Owner-approved Leyline of Resonance and Wild Ride representative-card pair
and the Leyline Aggro/Izzet U/R display metadata remain retained. After the
corrected statistics rebuild, the parent Leyline Aggro identity is below the
3% composition threshold, while its Izzet subtype remains present in rendered
statistics.

## Impact audit

One corrected Standard-only comparison against the accepted R4 plus
Spellementals boundary produced these transitions:

| Corpus | Transition | Count |
| --- | --- | ---: |
| Current Standard, 4,925 decks | Izzet Fling -> Leyline Aggro / Izzet | 3 |
| Current Standard, 4,925 decks | Izzet Fling -> Izzet Prowess | 2 |
| Frozen Standard, 3,936 decks | Izzet Fling -> Izzet Prowess | 2 |

Every transition is caused by the new at-most-one main-deck Leyline condition.
There are no Standard conflicts, invalid decks, or residual subtypes. Strict
current reports contain 15 Standard Unknown records.

The previously accepted Modern correction is unchanged: current and frozen
Modern move 157 and 117 Mono-Green Broodscale records to Gruul, and retained
Tabletop event `434455` moves twelve. Those inputs and tests were not rerun for
the Standard correction.

## Local validation and generated closure

After the initial six corrected Standard cases passed once, four new
at-most-one-specific nodes passed once in 0.38 seconds: one-Leyline acceptance,
two-Leyline rejection, and the two reviewed `Arcbound_Papi` lists. The already
passed zero-Leyline, Modern, and browser nodes were not rerun.

The first read-only Standard audit command failed before repository logic ran
because a PowerShell string preserved literal newline escape characters. Its
corrected one-line form then completed once; this was not a test rerun.

Standard statistics, matchups, completeness, hierarchy, metadata, strict
classification reports, and indexed W30-W32 Top 8 documents were regenerated
once without fetching source data. Modern and event `434455` artifacts were
not regenerated again.

## Publication state

PR 211 already exists. Its head `46809db` previously ran all 79 Playwright
tests, with 78 passing and one missing-card-art failure. Head `485bd7d` added
the Owner-approved Leyline art and metadata, but its remote validation is
superseded by this uncommitted rule correction. No commit, push, PR update,
workflow rerun, merge, production dispatch, or Pickup reflow was performed
after the Owner paused publication.

The Owner accepted the corrected local result and authorized commit, PR 211
update, one complete CI run on the new exact head, and merge after every
required check succeeds. Production dispatch, Pickup reflow, and P12-10 remain
outside this authorization.
