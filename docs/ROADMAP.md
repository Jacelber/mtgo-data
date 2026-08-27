# Development Roadmap

## Live-document contract

This document contains only the active phase, useful future phases, and their
acceptance criteria. It never authorizes work: read `docs/STATUS.yaml` for the
current task, blockers, and stop conditions. Product, statistical, and data
contracts remain in their dedicated specifications.

Completed and superseded roadmap detail is non-authoritative history:

- Phases 0–11 and superseded specifications:
  `docs/history/ROADMAP-PHASES-0-11.md`;
- the complete Phase 12 task sequence, acceptance criteria, and closeout record:
  `docs/history/ROADMAP-PHASE-12-COMPLETED.md`.

## Phase index

| Phase | Objective | Status |
| --- | --- | --- |
| 12 | Productize loading, state, accessibility, sharing, and the MTGO Landing under one visual system. | Complete on 2026-08-25 |
| 13 | Aggregate compatible multi-event matchups from raw counts. | Implementation in progress; P13-03 Owner accepted |
| 14 | Add Pauper MTGO and approved Paupergeddon support. | Planned; not authorized |
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

Phase 13 implementation began on 2026-08-27. P13-01 and P13-02 are complete;
P13-03 is Owner accepted for unchanged same-task completion. Every later task
remains a separate authorization gate.

---

# Phase 13 — Multi-event raw-count matchup aggregation

## Design gate

The Owner authorized `PHASE-13-DESIGN` on 2026-08-27. The design must split
implementation into separately authorized tasks and finish with a real-event
test using an exact Melee link supplied by the Owner at that later gate. That
event remains a non-public test input: it is not admitted to the production
whitelist, catalogs, Pages artifact, or front end.

The accepted design and bounded task sequence are in
`docs/audits/PHASE-13-DESIGN.md`. The Owner separately authorized P13-01,
P13-02, and P13-03. Those authorizations do not carry to controller or renderer
work, live collection, public enablement, or production.

## Objective

Allow matchup matrices to combine selected events without merging unrelated overview statistics.

## Required work

### Aggregation eligibility

Only combine events that:

- use the same Constructed format;
- use compatible archetype IDs;
- pass schema validation;
- pass required quality checks;
- are explicitly selected;
- expose the requested matchup scope.

### Aggregation method

Aggregate raw counts:

- wins;
- losses;
- played draws;
- valid matches.

Do not average already calculated percentages.

### Default exclusions

Exclude from primary matchup aggregation:

- mirror matches from overall non-mirror win rate;
- byes;
- no-shows;
- intentional draws;
- official awarded wins;
- Draft rounds;
- unknown rounds;
- unknown results;
- playoffs, unless a separate playoff view is explicitly selected.

### Scope behavior

The matrix must identify whether it uses:

- all Constructed Swiss;
- Day 1 Constructed only;
- Day 2 Constructed only.

For mixed events, the default may be all Constructed Swiss, but Day 1 and Day 2 scopes must remain available where data permits.

For the initial multi-event product, selecting two or more compatible events
forces `all_constructed`, the only scope common to all three approved event
structures. Day 1 and Day 2 remain selectable only for one event that declares
those scopes. A later expansion of multi-event stage-specific aggregation
requires a separate compatibility decision.

## Task sequence

1. Freeze compatibility rules for source, Constructed format, schema version,
   archetype identity, quality status, and supported scope.
2. Aggregate underlying eligible W-L-D counts and recalculate all rates and
   intervals from those counts.
3. Keep event overview documents independent and do not average event rates.
4. Limit initial multi-event selection to `all_constructed` as required by
   DEC-061.
5. When a second event is selected, switch to `all_constructed`; when selection
   returns to one event, restore its prior scope only if the catalog still
   declares that scope.
6. Persist selected event identities through the canonical multi-event URL
   representation reserved by P12-02; selected events are durable user state,
   while transient expanded table rows remain outside the URL.
7. Keep the production multi-event entry disabled until at least two compatible
   real events are approved. Synthetic contracts may prove the engineering
   capability but do not constitute real production acceptance.
8. After synthetic backend and browser acceptance, stop for the Owner to supply
   one exact Melee event link. Validate that event only in a disposable,
   non-public test: do not commit its registration or data, add it to a public
   catalog, render it in the production front end, dispatch a workflow, or
   publish it. An incompatible event proves rejection behavior but does not
   provide positive real aggregation acceptance.

## Acceptance criteria

Phase 13 is complete when:

- single-event and multi-event matrices reconcile from raw counts;
- cross-format selection is impossible;
- incompatible schema versions are rejected or migrated;
- sample size is displayed;
- low-sample warnings are displayed;
- confidence intervals are generated where specified;
- scope selection is visible;
- overview metrics remain per-event rather than merged.

---

# Phase 14 — Pauper MTGO and Paupergeddon

## Objective

Add Pauper to both product tracks after the Modern reference path and reusable event strategies are stable.

## Required work

Use the shared classifier and stable Pauper archetype identities for both
sources while keeping MTGO and Tabletop inputs, outputs, statistics, catalogs,
and product behavior separate. Depend on the engineering and front-end
baselines established by Phases 10 through 12.

Pauper must publish an admitted Landing under the Phase 12 contract in the same
public launch as its other required MTGO products. Until that complete set is
ready, the format remains unavailable in the public catalog.

## Task sequence

1. Add Pauper archetype rules.
2. Add Pauper rule fixtures.
3. Validate Pauper rule IDs and priorities.
4. Run Pauper MTGO classification.
5. Generate Pauper MTGO statistics.
6. Validate Pauper MTGO output.
7. Register the approved Paupergeddon main event.
8. Normalize and validate that event as `constructed_day2`.
9. Generate event-specific Pauper statistics.
10. Enable Pauper in both front ends only when its reviewed Landing and every
    required product are produced and admitted together.

## Acceptance criteria

Phase 14 is complete when:

- shared Pauper archetype IDs are used by both sources;
- MTGO and Melee data remain separate;
- MTGO and Melee statistics remain separate;
- Pauper rules pass validation;
- Standard and Modern regression tests pass;
- front-end format selection is catalog-driven;
- Pauper is not public until Landing and every required MTGO product are
  admitted together;
- quality reports are available.

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
- rules, tests, schemas, and catalogs are updated;
- Pioneer is not public without an admitted Landing and complete required
  product set;
- prior-format regression tests pass.

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
- prior-format regressions pass;
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
6. Enable each event through the catalog only after separate owner approval.
7. Run Standard MTGO regression and cross-product browser acceptance.

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

- the decision is recorded in `docs/DECISIONS.md`;
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
  review, beginning with the DEC-078 draw-adjusted metric retirement;
- publish current operator documentation for MTGO, Tabletop, Landing and Weekly
  Pickup editorial review, late-event re-review, storage, Pages, workflows,
  schemas, rules, quality review, rollback, and recovery;
- exercise the selected public-data and archive-storage design end to end;
- run regression across every approved format and both product areas;
- define long-term ownership, maintenance cadence, incident handling, and
  release evidence;
- retain rollback paths until the release is accepted.

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
4. Perform backup restoration, workflow recovery, publication rollback, and
   Pages recovery drills.
5. Exercise the production pipeline from approved source collection through
   data publication without bypassing validation or review gates.
6. Run full cross-format, cross-product, Schema, rule, repository, and
   real-browser regression.
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
- Pages, selected data storage, and production workflows pass an end-to-end
  recovery exercise;
- all approved formats and both product areas pass their regression contracts;
- production pages and public paths remain compatible;
- a release tag is published only after separate owner authorization;
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

At task completion, keep docs/STATUS.yaml live-only. When completed task detail
exists in this roadmap, move it in the same accepted task to the corresponding
phase file under docs/history/, update the history index, and leave only the
remaining plan plus a compact history pointer here. Git and the pull request
retain ordinary validation and publication evidence.

Use `docs/DEVELOPMENT_WORKFLOW.md` for task gates, artifact impact, validation,
Owner acceptance, publication, and stop conditions. Record scope or statistical
decisions in `docs/DECISIONS.md`. Historical files never authorize work.

# Current approved action

The current approved task is defined only in `docs/STATUS.yaml`.
