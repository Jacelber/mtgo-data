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

## Governance migration and publication state

PR 211 already exists. Its historical head `46809db` ran all 79 Playwright
tests, with 78 passing and one missing-card-art failure; historical head
`485bd7d` then added the Owner-approved Leyline art and metadata. Those results
remain evidence for the unchanged classifier/UI inputs, not instructions to
rerun the retired suites.

On 2026-08-16 the accepted task tree was merged forward onto current master
`9b80490651d605aad99d1fec41e8b6b5541eaeca` in a fresh isolated workspace.
Current master changed no relevant classifier, generated-data, Schema, or UI
input after the original branch point. The migration therefore retains the
already generated artifacts and impact counts without recalculation, removes
the branch's obsolete classifier regression module, and does not restore any
test retired by GOV-07 or GOV-08.

Under the current trigger matrix, local migration adds only one new check: the
value-independent output-invariant validator on the final tree. After new
Owner acceptance, targeted PR CI owns the repository-reference, live-document,
rule, and Schema checks selected by the final changed paths. Full pytest,
committed-baseline, R4/R5, Node, and Playwright reruns are not required.

The first command-line attempt did not enter the validator because `python`
was absent from the PowerShell path. A startup preflight then selected the
configured Python 3.12.7 interpreter; the validator ran once and reported
`Generated MTGO output invariants are valid.` No failed or partial test was
rerun.

No commit, push, PR update, workflow run, merge, production dispatch, Pickup
reflow, or P12-10 work is authorized before that acceptance. Production,
Pickup reflow, and P12-10 remain separately gated after publication.
