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
  `docs/history/ROADMAP-PHASE-12-COMPLETED.md`;
- the complete Phase 13 design, task sequence, acceptance criteria, and closeout
  record: `docs/history/ROADMAP-PHASE-13-COMPLETED.md`.

## Phase index

| Phase | Objective | Status |
| --- | --- | --- |
| 12 | Productize loading, state, accessibility, sharing, and the MTGO Landing under one visual system. | Complete on 2026-08-25 |
| 13 | Aggregate compatible multi-event matchups from raw counts. | Complete on 2026-08-27 |
| Pre-14 | Establish provenance-safe Chinese card names and complete card images. | Documentation authorized; implementation not authorized |
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

## Problem

Chinese pages still show English card names and use the English card-image path.
The superseded localization program added a separate identity manifest, Bulk
snapshot handling, source digests, capacity proxies, and three implementation
stages without delivering product behavior. The repository already normalizes
maintained aliases and card-face names before generated product documents reach
the browser; localization must reuse those names rather than implement another
normalizer.

## Current decision

DEC-146 supersedes the DEC-136 sidecar and DEC-145 mixed-delivery implementation
route. The rights record and completed MTGCH source/direct-image observations
remain evidence, so no new availability, latency, cache, image-size, or name-
conversion trial is required.

| Task | Problem | Operation | Expected effect | Recommended model |
| --- | --- | --- | --- | --- |
| `L10N-RESET` | The repository still describes and carries an unused B1/B2/C localization route. | Remove the unused localization builder, Schema, tests, dedicated CI trigger, and active B1/B2/C roadmap; record DEC-146 without changing Pages or the browser. | One clean baseline remains: existing English behavior and Landing cache are unchanged, while the abandoned route cannot be mistaken for authorization. | `gpt-5.6-terra`, medium reasoning |
| `L10N-SIMPLE` | Chinese card names and images are not yet displayed. | After separate authorization, implement one flat English-name-to-MTGCH display map, store only current default-Landing Chinese images in Pages, use MTGCH image URLs elsewhere on Chinese pages, retain the existing Landing cache and Scryfall image URLs on English pages, and use one shared browser selector. | Chinese names and images work through the smallest production path without a separate sidecar Schema or staged B1/B2/C admission. | `gpt-5.6-sol`, high reasoning |

`L10N-SIMPLE` is one future implementation and acceptance subject, not three
phases. Its only feature-specific checks are that the flat map parses, every
declared current-Landing local image exists, and the shared selector chooses
Chinese local, Chinese MTGCH, English local, and English Scryfall sources
correctly. Mandatory changed-scope repository validation still applies. No
real-source availability experiment is repeated.

The accepted MTGCH permission record remains authoritative. Historical audits
and DEC-137 through DEC-144 remain evidence of rights, source coverage, and the
completed direct-image observation; they do not prescribe a current
implementation route. Phase 14 remains separately unauthorized.

---

# Phase 14 — Pauper MTGO and Paupergeddon

## Objective

Add Pauper to both product tracks after the Modern reference path, reusable
event strategies, and the separately accepted card-localization foundation are
stable.

## Required work

Use the shared classifier and stable Pauper archetype identities for both
sources while keeping MTGO and Tabletop inputs, outputs, statistics, catalogs,
and product behavior separate. Depend on the engineering and front-end
baselines established by Phases 10 through 13.

Pauper must publish an admitted Landing under the Phase 12 contract in the same
public launch as its other required MTGO products. Until that complete set is
ready, the format remains unavailable in the public catalog. The Owner supplies
the Paupergeddon event link only when `P14-05` is authorized. Its trial data
remains disposable and non-public until a later explicit event-admission task.

## Task sequence

### P14-00 — Freeze the Phase 14 contract

- **Problem:** the former ten-line sequence did not identify input evidence,
  exact artifacts, stop conditions, or the boundary between MTGO and Tabletop.
- **Operation:** inventory existing Pauper archives, rule files, catalogs,
  Schemas, consumers, Landing requirements, and event-strategy contracts using
  read-only evidence. Define exact task paths and risk-triggered checks. Do not
  fetch a real event or change a whitelist.
- **Effect:** one Owner-reviewable implementation contract exists without data,
  code, or public behavior changes.
- **Recommended model:** `gpt-5.6-sol`, high reasoning.

### P14-01 — Establish and accept Pauper classification

- **Problem:** shared Pauper parent/subtype identities and representative rules
  are not yet an accepted cross-source taxonomy.
- **Operation:** inspect existing behavior, propose rules before coding, then
  add stable IDs, explicit priorities, fixtures, conflicts, Unknown reporting,
  and the smallest Standard/Modern regression evidence that answers the named
  compatibility risk.
- **Effect:** one accepted classifier can later classify both MTGO and the
  approved Tabletop event without copying source-specific archetypes.
- **Recommended model:** `gpt-5.6-sol`, high reasoning.

### P14-02 — Produce Pauper MTGO data and statistics privately

- **Problem:** archived Pauper collection does not constitute a complete MTGO
  product or prove the generalized pipeline.
- **Operation:** run the generalized Pauper classification and generators,
  update required contracts and quality reports, and validate only the Pauper
  output plus named cross-format risks. Keep catalogs and Pages unchanged.
- **Effect:** a versioned, Schema-valid private Pauper MTGO candidate exists
  with visible Unknown and source-completeness evidence.
- **Recommended model:** `gpt-5.6-sol`, high reasoning.

### P14-03 — Complete the Pauper Landing review path

- **Problem:** a future MTGO format cannot launch without a reviewed Landing
  and complete weekly-maintenance inputs.
- **Operation:** run the established Unknown, representative-card, deck-color,
  screening, machine-fact, and human bilingual-copy sequence for Pauper. The
  Owner remains authoritative for final content and card choices.
- **Effect:** the private Pauper candidate has an admitted-quality Landing and
  feature subject instead of a statistics-only partial product.
- **Recommended model:** `gpt-5.6-terra`, medium reasoning for bounded carrier
  preparation; use `gpt-5.6-sol`, high reasoning for stale-binding or contract
  failures.

### P14-04 — Accept the complete private Pauper MTGO product

- **Problem:** individually valid outputs can still disagree at the catalog,
  freshness, localization, or product-completeness boundary.
- **Operation:** assemble a local non-public complete-product candidate, verify
  Landing, official statistics, matchup coverage, Top 8 decklists, card
  localization, routes, and mobile behavior, then stop for Owner acceptance.
- **Effect:** the exact MTGO Pauper subject is ready for later coordinated
  admission but remains absent from the public catalog.
- **Recommended model:** `gpt-5.6-sol`, high reasoning.

### P14-05 — Trial the Owner-supplied Paupergeddon event

- **Problem:** the event's real round labels, decklists, and result completeness
  cannot be established from assumptions.
- **Operation:** only after the Owner supplies and authorizes the exact event
  link, collect it into a disposable test location, classify it with the
  accepted Pauper taxonomy, and validate the proposed `constructed_day2`
  strategy. Do not add it to `configs/melee_events.yaml`, the public catalog,
  Pages, production retention, or a front end.
- **Effect:** the Owner receives a quality and compatibility report based on the
  real event while the test event remains non-public and disposable.
- **Recommended model:** `gpt-5.6-sol`, high reasoning.

### P14-06 — Implement the separately approved Paupergeddon product

- **Problem:** a successful disposable trial is evidence, not authorization to
  retain or publish the event.
- **Operation:** after separate Owner approval, register only the exact approved
  main event, normalize and validate it under the accepted event strategy,
  generate event-specific overview and matchup statistics, and prove the
  active-taxonomy and privacy/publication boundaries.
- **Effect:** a private Tabletop Pauper candidate reuses the same classifier but
  keeps its source data and statistics separate from MTGO.
- **Recommended model:** `gpt-5.6-sol`, high reasoning.

### P14-07 — Coordinate admission, publication, and closeout

- **Problem:** enabling one source or one MTGO view early would create a partial
  public format and inconsistent navigation.
- **Operation:** after separate acceptance of the unchanged MTGO and Tabletop
  subjects, admit Pauper through generated catalogs, verify both front ends and
  retained Standard/Modern behavior, then use the normal commit, Ready PR,
  merge, exact-SHA Pages, and documentation closeout gates. Stop on any changed
  subject, failed check, conflict, permission blocker, or new decision.
- **Effect:** Pauper appears once as a complete catalog-driven format with
  separate MTGO and Tabletop products, verified Chinese card fallback, and
  recoverable publication evidence.
- **Recommended model:** `gpt-5.6-sol`, high reasoning.

## Acceptance criteria

Phase 14 is complete when:

- the card-localization foundation is accepted and its unresolved rights gates
  remain enforced;
- shared Pauper archetype IDs are used by both sources;
- MTGO and Melee data remain separate;
- MTGO and Melee statistics remain separate;
- Pauper rules pass their focused validation;
- Standard and Modern named regressions pass without repeating unrelated tests;
- the Owner-supplied real-event trial remained non-public until separate event
  admission;
- front-end format selection is catalog-driven;
- Pauper is not public until Landing and every required MTGO product are
  admitted together;
- quality, localization-fallback, and publication evidence are available; and
- Phase 15 remains unauthorized until separately opened.

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
