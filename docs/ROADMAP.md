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
  record: `docs/history/ROADMAP-PHASE-13-COMPLETED.md`;
- the completed Pre-Phase-14 localization reset and minimal implementation:
  `docs/history/ROADMAP-PRE-14-COMPLETED.md`.

## Phase index

| Phase | Objective | Status |
| --- | --- | --- |
| 12 | Productize loading, state, accessibility, sharing, and the MTGO Landing under one visual system. | Complete on 2026-08-25 |
| 13 | Aggregate compatible multi-event matchups from raw counts. | Complete on 2026-08-27 |
| Pre-14 | Establish provenance-safe Chinese card names and complete card images. | Owner accepted on 2026-08-29; completion authorized |
| 14 | Add Pauper MTGO and approved Paupergeddon support. | Active; shared repair precedes private generation |
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

## Objective

Add Pauper to both product tracks after the Modern reference path, reusable
event strategies, and the separately accepted card-localization foundation are
stable.

## Required work

Use the shared classifier and stable Pauper archetype identities for both
sources while keeping MTGO and Tabletop inputs, outputs, statistics, catalogs,
and product behavior separate. Depend on the engineering and front-end
baselines established by Phases 10 through 13.

Phase 14 is a third-format reuse proof, not a Pauper-specific product copy.
Every task must inspect the existing shared producer, contract, validator, and
consumer before adding a path. Pauper-specific rules, data, and reviewed
content are permitted; a parallel statistics engine, Landing renderer, page,
catalog, workflow, or source-specific taxonomy is not. A small closed-enum or
parameter extension may stay in the directly affected task. A material shared
framework gap must be repaired and separately accepted before Pauper input
enters that layer.

Pauper must publish an admitted Landing under the Phase 12 contract in the same
public launch as its other required MTGO products. Until that complete set is
ready, the format remains unavailable in the public catalog. The Owner supplies
the Paupergeddon event link only when `P14-05` is authorized. Its trial data
remains disposable and non-public until a later explicit event-admission task.

The complete read-only base inventory, invalidation map, task path envelopes,
risk-triggered validation, and state transitions are frozen in
`docs/audits/P14-00.md`. Its observed archive counts describe only the P14-00
base and are not fixed acceptance facts.

## Reuse and admission sequence

1. freeze the Phase 14 contract without changing product behavior;
2. accept one Pauper taxonomy shared by MTGO and Tabletop;
3. repair any material third-format MTGO contract gap with synthetic input
   before generating Pauper output;
4. generate and accept a complete private Pauper MTGO product while
   `public: false` keeps every catalog capability unavailable;
5. generalize the Landing/maintenance carrier with synthetic third-format
   subjects before importing Pauper human review;
6. trial the Owner-supplied real event once in a disposable non-public location;
7. after separate event admission, build a private Tabletop Pauper product; and
8. generalize the production/admission boundary before one coordinated complete
   Pauper launch.

The existing format registry permits an executable but non-public format. The
generated catalog exposes products only for a public format and rejects a
public format missing any required MTGO product. Phase 14 reuses that state
model; it does not add an intermediate public capability.

## Task sequence

Completed P14-00 and P14-01 detail is preserved in
`docs/history/ROADMAP-PHASE-14-COMPLETED.md`. The accepted Pauper classifier
merged through PR #313; no real Pauper product has been enabled.

### P14-02 — Produce Pauper MTGO data and statistics privately

- **Problem:** archived Pauper collection does not constitute a complete MTGO
  product, and active product Schemas, manifests, validation, and orchestration
  still contain confirmed Standard/Modern boundaries.
- **Operation A — shared repair:** inspect the invalidation map and repair active
  third-format gaps with synthetic input before using Pauper product data.
  Preserve intentional Standard compatibility aliases and do not edit frozen
  migration tools merely because they contain two-format history. A material
  shared repair is its own Owner-authorized and Owner-accepted subtask.
- **P14-02A boundary:** the refreshed exact contract and invalidation map are
  in `docs/audits/P14-02A.md`. Synthetic third-format execution, reviewed input
  selection, statistical Schemas, dynamic manifests, complete public catalog
  admission, production format selection, and direct-path Pages exclusion are
  repaired together. P14-03 human Landing/name carriers remain separate.
- **Operation B — private generation:** after shared repair acceptance, activate
  Pauper capabilities with `public: false`, then run the generalized
  classification and generators. Collect matches only under separate authority.
  Produce versioned statistics, ranges, matchups, Top 8, completeness,
  hierarchy, metadata, and quality reports with visible Unknown, conflicts,
  invalid decks, and source completeness.
- **Effect:** a versioned, Schema-valid private Pauper MTGO candidate exists
  with visible Unknown and source-completeness evidence.
- **Expected paths:** active shared owners and tests for Operation A; then the
  Pauper registry entry, `data/pauper/mtgo/matches/` when authorized,
  `stats/pauper/mtgo/`, `reports/pauper/mtgo/`, and directly required manifest
  patterns for Operation B. The consumer catalog remains unavailable.
- **Validation:** one synthetic private-executable/public-false format for each
  changed shared contract, then Pauper-only generated contracts and named
  shared regressions. Schema/manifest changes retain complete Schema validation.
- **Stop:** private candidate acceptance. Do not start Landing review.
- **Recommended model:** `gpt-5.6-sol`, high reasoning.

### P14-03 — Complete the Pauper Landing review path

- **Problem:** a future MTGO format cannot launch without a reviewed Landing
  and complete weekly-maintenance inputs.
- **Operation A — shared repair:** generalize active bilingual-name, Landing
  review, weekly readiness, and card-cache selection contracts with synthetic
  third-format subjects. Pauper must not be forced to share a review week with
  Standard/Modern. Frozen Pickup history remains unchanged. A material repair
  is separately authorized and accepted.
- **Operation B — Pauper review:** run the established Unknown,
  representative-card, deck-color, screening, machine-fact, Chinese authoring,
  English final review, and feature-card sequence. The Owner remains
  authoritative for final content and card choices.
- **Effect:** the private Pauper candidate has an admitted-quality Landing and
  feature subject instead of a statistics-only partial product.
- **Expected paths:** active Landing/editorial/readiness/name/cache owners,
  Schemas, synthetic fixtures, and tests for Operation A; then Pauper private
  review sources, visuals, names, reviewed candidate, and bounded review
  artifacts for Operation B. Public catalog availability remains false.
- **Stop:** Owner acceptance of the exact private Landing subject.
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
- **Validation:** complete-product consistency and only named shared regressions,
  followed by one final local visible-subject review at desktop, 390px, and
  412px. Do not publish or repeat passed immutable checks.
- **Stop:** Owner accepts the unchanged complete private MTGO subject.
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
- **Validation:** collect once, reuse the snapshot during diagnosis, and delete
  all temporary registration, source, derived output, and HMAC material after
  the exact quality harness completes.
- **Stop:** present admit, repair, defer, or reject options. Trial success does
  not authorize P14-06.
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
- **Expected paths:** the exact approved `configs/melee_events.yaml` entry,
  approved source/normalized event paths, `stats/pauper/melee/`, quality/privacy
  evidence, applicable manifest entries, and focused producer/consumer tests.
- **Stop:** Owner acceptance of the exact private Tabletop subject. No catalog
  or Pages admission follows automatically.
- **Recommended model:** `gpt-5.6-sol`, high reasoning.

### P14-07 — Coordinate admission, publication, and closeout

- **Problem:** enabling one source or one MTGO view early would create a partial
  public format and inconsistent navigation.
- **Operation A — shared production acceptance:** before publication, reuse
  the P14-02A registry-derived product/hierarchy selection and private Pages
  exclusion. Review only remaining candidate, admission, and metadata gaps
  against the eventual complete accepted product; preserve least
  privilege, concurrency, immutable candidate transfer, validation before
  publication, failure reporting, and exact-evidence Pages admission. This is a
  separate Owner-authorized and Owner-accepted task and changes no generated
  Pauper product bytes.
- **Operation B — coordinated admission:** after separate acceptance of the
  unchanged MTGO and Tabletop subjects, admit every required Pauper product
  together through generated catalogs, verify both front ends and retained
  Standard/Modern behavior, then use the normal commit, Ready PR, merge,
  exact-SHA Pages, and documentation closeout gates. Stop on any changed subject,
  failed check, conflict, permission blocker, or new decision.
- **Effect:** Pauper appears once as a complete catalog-driven format with
  separate MTGO and Tabletop products, verified Chinese card fallback, and
  recoverable publication evidence.
- **Validation:** synthetic registry routing proves collection-only, private,
  incomplete-public, and complete-public states before the final immutable
  candidate receives its one applicable publication path.
- **Stop:** Phase 14 complete. Phase 15 remains separately unauthorized.
- **Recommended model:** `gpt-5.6-sol`, high reasoning.

## Acceptance criteria

Phase 14 is complete when:

- the card-localization foundation is accepted and its unresolved rights gates
  remain enforced;
- shared Pauper archetype IDs are used by both sources;
- every Pauper layer reuses the maintained shared owner or records and
  separately accepts a material shared-framework repair before Pauper input;
- no parallel Pauper statistics engine, Landing renderer, page, catalog,
  workflow, or source-specific taxonomy was introduced;
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
