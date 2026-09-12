# Development Roadmap

## Live-document contract

This document contains only the active phase, useful future phases, and their
acceptance criteria. Current instructions and the confirmed plan authorize work
under GOVERNANCE; STATUS records durable facts and actual blockers. Product, statistical, and data
contracts remain in their dedicated specifications.

Completed and superseded roadmap detail is non-authoritative history:

- Phases 0–11 and superseded specifications:
  `docs/history/ROADMAP-PHASES-0-11.md`;
- the complete Phase 12 task sequence, acceptance criteria, and closeout record:
  `docs/history/ROADMAP-PHASE-12-COMPLETED.md`;
- the complete Phase 13 design, task sequence, acceptance criteria, and closeout
  record: `docs/history/ROADMAP-PHASE-13-COMPLETED.md`;
- the completed Pre-Phase-14 localization reset and minimal implementation:
  `docs/history/ROADMAP-PRE-14-COMPLETED.md`;
- the complete Phase 14 task sequence, acceptance criteria, and closeout record:
  `docs/history/ROADMAP-PHASE-14-COMPLETED.md`.

## Phase index

| Phase | Objective | Status |
| --- | --- | --- |
| 12 | Productize loading, state, accessibility, sharing, and the MTGO Landing under one visual system. | Complete on 2026-08-25 |
| 13 | Aggregate compatible multi-event matchups from raw counts. | Complete on 2026-08-27 |
| Pre-14 | Establish provenance-safe Chinese card names and complete card images. | Owner accepted on 2026-08-29; completion authorized |
| 14 | Add Pauper MTGO and approved Paupergeddon support. | Complete on 2026-09-10 |
| 15 | Add Pioneer through the established dual-product process. | Planned; not authorized |
| 16 | Add Legacy and approved Eternal Weekend Legacy support. | Planned; not authorized |
| 17 | Add qualifying Standard Tabletop events. | Planned; not authorized |
| 18 | Decide whether Vintage should be implemented. | Decision gate; not authorized |
| 19 | Complete release and long-term maintenance readiness. | Planned; not authorized |

---

# Phase 12 — Front-end productization, editorial landing, and visual system

Phase 12 completed on 2026-08-25 after the Owner accepted P12-16 and its
Landing-default cutover merged through PR #276. The phase delivered the shared
visual system, resilient retained views, the reviewed bilingual Landing and
feature archive, Pickup compatibility and retirement, cross-device behavior,
and the reversible bare-entry default without changing statistical meaning or
merging MTGO and Tabletop products.

The complete task sequence, embedded implementation history, final acceptance
criteria, and closeout evidence are preserved in
`docs/history/ROADMAP-PHASE-12-COMPLETED.md`.

Phase 13 completed on 2026-08-27 after the Owner accepted P13-07 and its
active-taxonomy admission merged through PR #291. The phase delivered raw-count
multi-event matchup aggregation, compatible selection and URL state, retained
per-event overview metrics, current-taxonomy admission, and a disposable
real-event validation without enabling a second public event.

The complete design, task sequence, acceptance criteria, and cloud closeout
evidence are preserved in
`docs/history/ROADMAP-PHASE-13-COMPLETED.md`.

---

# Pre-Phase-14 — Simple card localization

The Owner accepted the minimal localization implementation on 2026-08-29. It
replaces the abandoned staged route with one shared card-name candidate entry,
one flat MTGCH lookup, local current-Landing images, and language-aware browser
selection while preserving the English path.

The complete problem statement, implementation sequence, acceptance boundary,
and retained evidence are preserved in
`docs/history/ROADMAP-PRE-14-COMPLETED.md`. Phase 14 resumed on 2026-09-05
with its shared-repair lane; later tasks remain separate.

---

# Phase 14 — Pauper MTGO and Paupergeddon

Phase 14 completed on 2026-09-10 after the Owner accepted one coordinated
public admission of the complete Pauper MTGO product and Paupergeddon event
`438329`. Pauper now reuses the shared classifier, generators, catalogs, and
front ends while MTGO and Tabletop source data and statistics remain separate.
The admission includes 109 explicitly reviewed MTGO events through 2026-W36;
event `12853710` remains excluded.

The complete contract, task sequence, acceptance criteria, and closeout
evidence are preserved in
`docs/history/ROADMAP-PHASE-14-COMPLETED.md` and `docs/audits/P14-07B.md`.
The public catalogs checked on 2026-09-12 list Standard, Modern and Pauper MTGO;
Tabletop lists Modern `405590`, `441441`, `434455` (default `405590`) and Pauper
`438329`. Public admission does not mean known image or color defects are fixed.
Phase 15 is not part of the current governance-rebuild delivery.

---

# Phase 15 — Pioneer

## Objective

Add Pioneer using the established shared-classifier and dual-product process.

## Required work

Use the established shared-classifier and dual-product process without copying
or forking the Standard-only pipeline. Depend on the engineering and front-end
baselines established by Phases 10 through 12.

Pioneer must admit a reviewed Landing and every required MTGO product in one
public launch. It remains unavailable in the public catalog until that set is
complete.

## Task sequence

1. Add Pioneer archetype rules.
2. Add Pioneer fixtures.
3. Validate rule IDs and priorities.
4. Add Pioneer MTGO processing.
5. Validate Pioneer MTGO statistics.
6. Register an approved Pioneer Melee event.
7. Normalize and validate the event.
8. Generate event-specific Pioneer statistics.
9. Enable Pioneer in both front ends only when Landing and every required
   product are generated and admitted together.

## Acceptance criteria

Phase 15 is complete when:

- Pioneer uses the generalized MTGO pipeline;
- Pioneer uses the shared classifier;
- MTGO and Melee remain separate;
- no copied Standard-only pipeline is introduced;
- applicable rules, schemas and catalogs describe the new product, with proof
  for affected results and any changed core mechanism;
- Pioneer is not public without an admitted Landing and complete required
  product set;
- existing products retain their required behavior, with affected-result proof
  selected under QUALITY rather than an automatic prior-format regression suite.

---

# Phase 16 — Legacy and Eternal Weekend

## Objective

Add Legacy using the established process, including approved Eternal Weekend Legacy main events.

## Required work

Use the established shared-classifier and dual-product process for Legacy, and
retain the approved Eternal Weekend main-event boundary. Depend on the
engineering and front-end baselines established by Phases 10 through 12.

Legacy must admit a reviewed Landing and every required MTGO product in one
public launch. It remains unavailable in the public catalog until that set is
complete.

## Task sequence

1. Add Legacy archetype rules.
2. Add Legacy fixtures.
3. Validate rule IDs and priorities.
4. Add Legacy MTGO processing.
5. Validate Legacy MTGO statistics.
6. Register an Eternal Weekend Legacy main event.
7. Normalize and validate the event.
8. Generate event-specific Legacy statistics.
9. Enable Legacy in both front ends only when Landing and every required
   product are generated and admitted together.

### Event restrictions

Only approved Eternal Weekend main events may be included under this policy.

Do not include:

- side events;
- trials;
- qualifiers;
- team events;
- unrelated Legacy events not present in the whitelist.

## Acceptance criteria

Phase 16 is complete when:

- only the approved main event is included;
- side events remain excluded;
- shared Legacy archetype IDs are stable;
- MTGO and Melee remain separate;
- Legacy is not public without an admitted Landing and complete required
  product set;
- existing formats retain supported behavior; validate only affected results
  and changed mechanisms, reusing applicable evidence;
- front-end catalogs are updated.

---

# Phase 17 — Standard Tabletop events

## Objective

Enable qualifying Standard tabletop events after the Melee pipeline is stable.

## Required work

Only Standard events matching the approved event policy may be added.

Standard MTGO and Standard Melee must remain separate in:

- raw data;
- normalized data;
- generated statistics;
- catalogs;
- front-end presentation.

Qualifying mixed-format Standard events must use the mixed-event strategy.

## Task sequence

1. Select only owner-approved Standard events that satisfy the whitelist and
   event-category policy.
2. Validate each event's source completeness and declared structure.
3. Reuse the shared Standard classifier without merging MTGO and Tabletop data.
4. Generate event-specific Tabletop statistics and quality evidence.
5. Validate mixed, Constructed Day 2, or single-stage behavior as applicable.
6. Enable the complete event product through the catalog within its authorized
   plan and agreed business acceptance, without a second publication approval.
7. Check affected Tabletop results and any changed shared behavior. Source
   separation and Standard compatibility remain required; adding an event does
   not automatically trigger Standard MTGO regression or all-product browsing.

## Acceptance criteria

Phase 17 is complete when:

- Standard tabletop events use the shared Standard classifier;
- no MTGO and Melee statistics are merged;
- mixed-format rules are applied where required;
- current Standard MTGO behavior remains compatible;
- data quality and source metadata are visible.

---

# Phase 18 — Vintage decision gate

## Objective

Decide whether Vintage support should be implemented.

## Required work

Review:

- available MTGO Vintage data;
- Eternal Weekend Vintage data quality;
- decklist completeness;
- matchup completeness;
- classification maintenance cost;
- expected user value;
- front-end impact;
- automation impact;
- long-term operational cost.

## Task sequence

1. Audit the available MTGO and Eternal Weekend Vintage evidence.
2. Estimate classification, data-quality, front-end, automation, and ongoing
   maintenance cost.
3. Present approve, defer, and reject options to the owner.
4. Stop for an explicit owner decision.
5. If approved, add separately authorized implementation tasks using the
   established process; do not enable Vintage through this decision task.

### Possible outcomes

The project owner may:

1. approve Vintage and implement it using the established process;
2. defer Vintage with a documented reason;
3. reject Vintage from the current scope.

## Acceptance criteria

Phase 18 is complete when:

- the resulting scope decision is recorded in the applicable business specification;
- `docs/PROJECT_SCOPE.md` is updated;
- `docs/STATUS.yaml` is updated;
- the roadmap is updated if implementation phases change;
- Vintage is not enabled before the decision is recorded.

---

# Phase 19 — Release and long-term maintenance closeout

## Objective

Prove that the completed product, data, and operational system can be released,
recovered, rolled back, and maintained without relying on undocumented project
history or unverified compatibility entry points.

## Required work

- complete only the compatibility cleanup that remains after Phase 11 owner
  review, beginning with the draw-adjusted compatibility metric retirement;
- publish current operator documentation for MTGO, Tabletop, Landing and Weekly
  Pickup editorial review, late-event re-review, storage, Pages, workflows,
  schemas, rules, quality review, rollback, and recovery;
- retain applicable evidence that the selected public-data and archive-storage
  path works; fill only gaps introduced by the release changes;
- establish that affected release results and retained compatibility behavior
  meet their contracts, using valid prior evidence and focused new checks;
- define long-term ownership, maintenance cadence, incident handling, and
  release evidence;
- retain applicable complete deployment versions under DELIVERY's recovery policy.

## Task sequence

1. Retire the draw-adjusted win-rate calculation and compatibility fields under
   a dedicated versioned contract migration. Update the statistical
   specification, Schemas, generators, fixtures, tests, public MTGO and
   Tabletop documents, the protected `434455` manifest, legacy JavaScript, and
   rollback evidence without silently changing an existing field's meaning.
2. Reconcile the final list of other compatibility entry points and remove only
   those whose replacements and rollback paths are verified.
3. Complete the operator runbooks and non-programmer maintenance instructions,
   including weekly Landing and Pickup candidate review, publication, valid
   empty states, additive late-event re-review, stale-content diagnosis, and
   Landing fallback recovery.
4. Reuse applicable archive, workflow and Pages recovery evidence. Verify only
   changed recovery mechanisms or a necessary capability not yet demonstrated;
   release closeout alone does not trigger repeated drills or a production rollback.
5. Confirm the affected collection-to-publication path using applicable results
   and agreed business review. Do not collect data or publish a product solely
   to repeat already-valid release evidence.
6. Resolve gaps in proof for the actual changes and their combinations. Check
   affected numbers, contracts and usable pages; no full-suite closeout prerequisite.
7. Resolve or explicitly defer every release-blocking Unknown, conflict,
   quality, privacy, compatibility, and operational issue.
8. Obtain owner acceptance, publish the approved release tag, and record the
   maintenance responsibility and cadence.

## Acceptance criteria

Phase 19 is complete when:

- compatibility cleanup is approved, verified, documented, and reversible;
- no production generator or retained front-end asset calculates a draw as
  half a win, and the sole published win-rate meaning is declared as
  `wins_over_valid_matches` under the migrated Schema contract;
- written operations cover routine refresh, event addition, Landing and Pickup
  editorial review, late-event re-review, quality review, schema migration,
  deployment, rollback, and recovery;
- Pages, selected storage and production workflows have applicable evidence
  that the required recovery path works; unchanged evidence remains reusable;
- affected results in the approved formats and both product areas satisfy
  their applicable business and compatibility contracts;
- production pages and public paths remain compatible;
- the agreed release tag is published within the accepted release plan;
- long-term ownership and maintenance cadence are recorded in
  `docs/STATUS.yaml`.

---

# Unnumbered candidate — Environment Trends

## Objective

Evaluate a possible historical Environment Trends capability without treating
it as part of Phase 12 or as approved product scope.

Phase 12 publishes only a latest-state `landing/current.json`. That current
document, its Git history, and the existing Weekly Pickup archive do not by
themselves authorize historical Landing browsing or establish an authoritative
cross-week trend series.

## Required work

- identify an authoritative historical weekly snapshot source;
- define missing-week behavior;
- define comparability across classification-rule changes;
- determine required `docs/PROJECT_SCOPE.md` and
  `docs/STATISTICS_SPEC.md` changes;
- decide whether immutable Landing-week retention is appropriate and how it
  remains comparable across classification-rule and Schema versions;
- decide whether the capability is an extension of the current Environment
  Trends product.

## Task sequence

1. Prepare a documentation-only feasibility proposal.
2. Present the scope, statistical, data, and maintenance choices to the owner.
3. Stop unless the owner explicitly approves adding this candidate to the
   numbered roadmap.

## Acceptance criteria

This candidate may enter the numbered roadmap only when the owner has approved
its product scope, historical data source, missing-data rules, classification
comparability policy, statistical specification changes, retention and
migration policy, and maintenance cost. It must not treat Phase 12's
latest-only document or Git history as an approved historical product source.

---

# Completion and change control

Keep this roadmap focused on useful product direction and remaining work.
Ordinary delivery facts remain in Git/GitHub. GOVERNANCE defines task completion;
only changes to actual roadmap or durable project facts require updating them.

# Current approved action

The active Owner instruction and confirmed plan define the current task.
Governance rebuild is authorized through U6 acceptance, then U7 cutover;
implementation facts are in `plans/governance-rebuild/RESULTS.md`.
