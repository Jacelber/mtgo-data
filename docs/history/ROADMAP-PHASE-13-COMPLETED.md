# Phase 13 completed roadmap detail

This file preserves the complete Phase 13 design, task sequence, acceptance
criteria, and closeout evidence. It is historical and non-authoritative. Phase
13 closed on 2026-08-27; current authorization remains solely in
`docs/STATUS.yaml`.

## Design gate

The Owner authorized `PHASE-13-DESIGN` on 2026-08-27. The design split
implementation into separately authorized tasks and finished with a real-event
test using exact Melee event `437444` supplied by the Owner. That event remained
a disposable non-public input and was never admitted to the production
whitelist, catalogs, Pages artifact, or front end.

The accepted design is preserved in `docs/audits/PHASE-13-DESIGN.md`. P13-01
through P13-06 were separately authorized, followed by the bounded P13-06R
correction and P13-07 active-taxonomy admission. Neither correction changed
classification meaning, production event inclusion, or public availability.

## Objective

Allow matchup matrices to combine selected events without merging unrelated
overview statistics.

## Required work

### Aggregation eligibility

Only combine events that:

- use the same Constructed format;
- use compatible archetype IDs;
- pass Schema validation and required quality checks;
- are explicitly selected; and
- expose the requested matchup scope.

### Aggregation method

Aggregate eligible wins, losses, played draws, and valid matches as raw counts,
then recalculate rates and intervals. Never average already calculated
percentages.

### Default exclusions

Exclude mirror matches from overall non-mirror win rate, plus byes, no-shows,
intentional draws, official awarded wins, Draft rounds, unknown rounds, unknown
results, and playoffs unless a separate playoff view is explicitly selected.

### Scope behavior

The matrix identifies all Constructed Swiss, Day 1 Constructed, or Day 2
Constructed scope. Selecting two or more compatible events forces
`all_constructed`, the only scope shared by the approved event structures. Day
1 and Day 2 remain available only for a single event that declares them.

## Completed task sequence

1. Freeze compatibility rules for source, Constructed format, Schema version,
   archetype identity, quality status, and supported scope.
2. Aggregate underlying eligible W-L-D counts and recalculate rates and
   intervals from those counts.
3. Keep event overview documents independent and do not average event rates.
4. Limit initial multi-event selection to `all_constructed` as required by
   DEC-061.
5. Restore a single event's prior scope only when its catalog still declares
   that scope.
6. Persist selected event identities through the canonical multi-event URL
   representation while keeping transient expanded rows outside the URL.
7. Keep production multi-event selection disabled until at least two compatible
   real events are separately approved.
8. Validate event `437444` only in a disposable non-public test; do not retain
   its registration, source, normalized data, derived outputs, or front-end
   availability.
9. Bind every future multi-event-eligible catalog to the active format taxonomy
   and require every selected event to match that exact version and digest.

## Acceptance criteria

Phase 13 required single-event and multi-event matrices to reconcile from raw
counts; cross-format selection to remain impossible; incompatible Schemas to
fail closed; sample size, low-sample warnings, confidence intervals, and scope
to remain visible; overview metrics to remain per-event; and every admitted
event to equal the catalog-declared active taxonomy even when all selected stale
events otherwise agree with one another.

## Closeout evidence

The accepted implementation sequence is backed by these cloud merge records:

| Task | Merge evidence |
| --- | --- |
| P13-01 | PR #285, `43310f9345c670f40d7bb900275e9d9a0968fa91` |
| P13-02 | PR #286, `82bf76770a2993e360e49a941ac92c5a37b7733c` |
| P13-03 | PR #287, `01baad87620de95b29c954d7d6801a94667785f0` |
| P13-04 | PR #288, `6f4dfaeb2288b235eddcd5dcc3282a5acedcaa74` |
| P13-05 | PR #289, `3a571a0780c7861d3f0cd4422368513ca45d8c22` |
| P13-06 / P13-06R | PR #290, `f9aa032edce29e49c68d08282b7bdc3309d07fdb` |
| P13-07 | PR #291, `a0c4c9391e3cee096f675441b1a5deb144ec7fdb` |

P13-07 received Owner acceptance and merged unchanged. Pull-request validation
run `33087197220`, master validation run `33087428322`, and merge-triggered
Pages run `33087428346` succeeded. The later scheduled production run
`33108441657` published from the P13-07 merge and Pages run `33110315667`
deployed exact master commit `960a78d3767229383b2d4fac3ddd8c3a7b1806e1`.

The MTGO entry, Tabletop entry, and public catalog returned HTTP 200. Event
`437444` was absent from the public catalog and remained outside the whitelist,
Pages data, and front end. Phase 14 was not started. These results satisfy the
Phase 13 acceptance criteria; the previously stale live wording was a status
maintenance omission, not missing implementation or publication work.
