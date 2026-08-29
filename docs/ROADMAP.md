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

# Pre-Phase-14 — Card localization foundation

## Problem

Chinese interface and archetype labels are available, but card names and
complete card images still use the English Scryfall path. Official Simplified
Chinese status must be proved independently through Scryfall; MTGCH supplies
additional Chinese names and rendered images but does not expose one unified
official/community source field. Phase 14 would multiply the unresolved surface
by adding Pauper cards and another source product.

## Required sequence

| Task | Problem | Operation | Implemented effect | Recommended model |
| --- | --- | --- | --- | --- |
| `L10N-00` | Product, identity, provenance, fallback, rights, and rollout boundaries are not authoritative. | Update only scope, architecture, decision, roadmap, status, and validation-trigger documents. | One reviewable contract exists; no code or public behavior changes. | `gpt-5.6-terra`, medium reasoning |
| `L10N-A` | Card localization has no versioned join, resolver, or manifest contract. | Define the `oracle_id` + `scryfall_id` + `face_index` sidecar, provenance vocabulary, official/community/English priority, source adapter, Schema, and deterministic synthetic fixtures. Do not use real community image bytes. | A bounded build can prove identity, provenance, fallback, and atomic failure without changing the existing English cache. | `gpt-5.6-sol`, high reasoning |
| `L10N-RIGHTS` | Public API access alone does not prove image redistribution permission, while the Owner has project-specific permission from the MTGCH founder. | Record public evidence and the Owner attestation. Prove official Simplified Chinese through Scryfall; otherwise classify exact-identity MTGCH Chinese names/images as project-permitted community material; fail closed on identity ambiguity, non-MTGCH third-party material, or unpermitted modification. | The official-first, community-second, English-fallback order is derived without inventing an MTGCH source field or misrepresenting the Owner attestation as a public license. | `gpt-5.6-sol`, high reasoning for evidence review; Owner or qualified rights review remains authoritative |
| `L10N-DIRECT-TRIAL-CONTRACT` | Six planned formats make a complete bilingual Pages image mirror unlikely to remain sustainable, but the repository has no bounded evidence that direct MTGCH image delivery is suitable from the real Pages origin. | Define only the separately authorized trial subject, request ceiling, pacing, transient-browser boundary, measurements, stop conditions, controlled conclusions, and unchanged production prohibition. Do not contact a real card endpoint or image host. | One reviewable diagnostic contract exists without changing code, public paths, source traffic, or product behavior. | `gpt-5.6-terra`, medium reasoning |
| `L10N-DIRECT-TRIAL` | Direct-origin and local-cache architectures cannot be compared from storage estimates alone. | After separate authorization, attempt the bounded DEC-138 diagnostic. The run stopped during candidate metadata resolution before its first image request. | The result characterizes the tested per-card metadata setup only. DEC-140 supersedes DEC-138's automatic hybrid-selection consequence for this incomplete setup; no image architecture was measured or selected. | `gpt-5.6-terra`, medium reasoning |
| `L10N-ARCHITECTURE-EVIDENCE-CONTRACT` | The earlier trial stopped during metadata setup before its first image request, so it cannot support a cache size, an image-delivery decision, or a runtime prohibition. | Withdraw the unmeasured DEC-139 proposal; define the exact missing subject, coverage, byte, Pages-headroom, direct-image, cache, interaction, fallback, and grouped-metadata evidence; freeze deterministic sampling, budgets, retention, stop conditions, and result-to-decision rules. Do not contact another card or image endpoint. | One reviewable contract separates setup failure from image evidence and selects no architecture before measurement. | `gpt-5.6-sol`, high reasoning |
| `L10N-ARCHITECTURE-EVIDENCE-TRIAL` | No real data established Chinese-image coverage/size or exact-image behavior from the Pages origin. | Close the offline current-product inventory and begin the accepted grouped-source setup. The first MTGCH request returns HTTP 200, but the local validator incorrectly demands undocumented full-card/provenance fields and stops before image selection. | One corrected aggregate report preserves the valid subject, Pages, Cache-B, and Scryfall identity measurements, invalidates the false source-failure conclusion, and records image delivery as unmeasured. | `gpt-5.6-sol`, high reasoning |
| `L10N-ARCHITECTURE-EVIDENCE-CONTRACT-CORRECTION` | The accepted contract confuses project-derived `official`/`community`/`english_fallback` classes with nonexistent mandatory MTGCH source fields. | Correct DEC-137/140, the rights and architecture contracts, the evidence report, roadmap, and live status. Define Scryfall as official-printing proof and MTGCH exact-identity Chinese material as community when official proof is absent. Do not resume source access. | One internally consistent documentation subject identifies the validator design error and provides a reviewable basis for a later bounded rerun. | `gpt-5.6-sol`, high reasoning |
| `L10N-ARCHITECTURE-EVIDENCE-TRIAL-RERUN` | Corrected source classification still leaves image delivery unmeasured. | Reproduce the immutable offline subject, resolve official material from one Scryfall `all_cards` snapshot, complete no more than 32 grouped MTGCH requests, prepare the deterministic image sample, and start Stage C only through the approved Pages-origin browser capability. | Stage A and B close: 28 of 28 MTGCH requests return HTTP 200 and 100 images cover every eligible stratum. Stage C stops before its first sampled image because the approved browser cannot inject the external exact URLs or expose the declared network metrics; no source failure or architecture is inferred. | `gpt-5.6-sol`, high reasoning |
| `L10N-STAGE-C-EXECUTION-CONTRACT` | The evidence contract assumes a Pages-origin browser executor capability that the approved in-app browser does not expose. | Select an Owner-controlled, repository-owned Playwright/Chromium runner; bind it to served Pages/controller bytes; define deterministic regeneration, real interaction shapes, observable network/cache metrics, aggregate redaction, external temporary state, logical/physical budgets, and fail-closed cleanup. Make no source or image request while writing the contract. | One reviewable contract resolves the executor design without bypassing in-app-browser security: implementation and real traffic remain separate later gates. | `gpt-5.6-sol`, high reasoning |
| `L10N-STAGE-C-RUNNER` | The accepted contract lacked an executable, independently verified diagnostic. | Implement the repository-owned runner and prove binding, interaction, budget, redaction, retention, and cleanup only with local synthetic fixtures. | The accepted runner passed 9/9 focused cases and can exercise the Pages/controller path without retaining exact sample data. | `gpt-5.6-sol`, high reasoning |
| `L10N-STAGE-C-TRIAL` | Stage C lacked real exact-image status, decode, redirect, latency, cache, and fallback evidence. | Reproduce the accepted subject, regenerate the deterministic sample, and complete one Pages-origin observation session; retain only its aggregate and make no cross-time claim. | 200/200 MTGCH and 200/200 controls decoded with zero failure or timeout; direct delivery met DEC-140's optional-path thresholds for the observed window. | `gpt-5.6-sol`, high reasoning |
| `L10N-ARCHITECTURE-DECISION` | Direct delivery qualifies, but the Owner wants initially visible Landing images to be independent of MTGCH. | Select the current default-Landing representative-plus-Feature hot set for local Pages packaging, use corresponding English complete-card bytes as its capacity proxy without another Chinese sizing trial, and use controlled exact URLs plus English fallback for every other image. | One bounded mixed architecture makes the current default Landing local without mirroring decklists or complete formats. | `gpt-5.6-sol`, high reasoning |
| `L10N-B1` | The synthetic contract lacks a real hot-set definition, English proxy accounting, and mixed local/direct delivery classes. | After architecture acceptance, implement the deterministic current-Landing extractor; evolve Schema, builder, and synthetic fixtures; then build a real repository-external candidate with names, provenance, attribution, exact non-hot-set URLs, original hot-set bytes, English proxy totals, actual totals, and atomic capacity checks. Change no Pages or browser path. | One external candidate proves the complete localization contract and an at-most-64-MiB current Landing hot set without a separate sizing experiment. | `gpt-5.6-sol`, high reasoning |
| `L10N-B2` | A validated mixed-delivery candidate is not yet an admitted optional Pages resource. | After B1 acceptance, add subject-addressed artifact reuse and a separate generated overlay for the manifest, attribution, and hot-set files; enforce the 64-MiB overlay and 1-GiB Pages ceilings; omit a failed, rejected, missing, or oversized overlay. Add no browser consumer. | Pages carries only current default-Landing Chinese images, while every failure preserves a valid English artifact. | `gpt-5.6-sol`, high reasoning |
| `L10N-C` | Chinese views do not consume the admitted local/direct resource, and Landing still has separate representative-art and Feature image paths. | After B2 acceptance, add one shared identity-based consumer: local Chinese files for default Landing, controlled exact URLs elsewhere, and English fallback throughout. Validate desktop, 390px, 412px, current/archived/legacy routes and interactions, then remove only caller-proven obsolete representative assets and duplicate selection branches. | Initially visible Landing images are local in Chinese, other images remain bounded on demand, and redundant image code is removed safely. | `gpt-5.6-sol`, high reasoning |

The `L10N-RIGHTS` evidence matrix and operational conditions are recorded in
`docs/audits/CARD_LOCALIZATION_RIGHTS_REVIEW_20260829.md` and DEC-137. The
diagnostic exception is defined by DEC-138. The diagnostic required separate
authorization, and neither decision authorizes `L10N-B1`; each real-source
operation requires its own exact authorization after its contract is accepted
and merged.

The authorized direct trial then stopped when candidate-resolution request 31
returned HTTP 429, before any image request. DEC-139's unmeasured hybrid-cache
proposal was withdrawn before acceptance. DEC-140 and
`docs/audits/CARD_LOCALIZATION_HYBRID_CACHE_ARCHITECTURE_20260829.md` define the
replacement evidence contract.

The first authorized replacement trial closed 47 registered documents and
measured 108,651 card-name occurrences, 1,892 distinct English input strings,
a 270,195,353-byte/1,936-file base Pages artifact, and the existing 71-image
Cache-B subject. It then stopped on `validator_contract_design_error`, not an
MTGCH failure. After DEC-141 was accepted and merged, the separately authorized
corrected rerun reproduced that subject, used one Scryfall `all_cards` snapshot,
and completed all 28 grouped MTGCH requests with HTTP 200. Provider precedence
assigned Chinese names and images for all 1,866 resolved canonical identities,
and a deterministic 100-image sample covered the two eligible face-form strata.

The first approved browser surface could not introduce the external exact
sample into the deployed controller, so DEC-142 correctly classified that stop
as an executor gap rather than an image failure. DEC-143 then selected the
Owner-controlled repository Playwright/Chromium runner. Its separately accepted
Stage-C session loaded and decoded 200/200 MTGCH cases and 200/200 matched
Scryfall controls with zero timeout or failure, a 693-ms p95 disadvantage, and
98.5% useful warm reuse. DEC-144 limits that result to one observed window.

DEC-145 and
`docs/audits/CARD_LOCALIZATION_ARCHITECTURE_DECISION_20260829.md` therefore
propose a bounded mixed design. The local subject is only the default Landing's
representative and current Feature cards: 29 Standard names, 34 Modern names,
and 61 after cross-format deduplication in the current documents. The Owner
accepts corresponding English complete-card bytes as the planning proxy, so no
second Chinese sizing trial is inserted. Both proxy and actual overlay must fit
64 MiB; non-hot-set images use controlled exact delivery and English fallback.
Architecture acceptance does not authorize `L10N-B1`, `L10N-B2`, or `L10N-C`.

These tasks are separate authorization and acceptance subjects. `L10N-00`
does not authorize `L10N-A`; the rights decision does not authorize a build;
and no accepted local task authorizes commit, publication, merge, Pages, or the
next task until the applicable workflow gate is satisfied. Phase 14 cannot
start until the Owner accepts the complete localization foundation or records
an explicit narrower Phase 14 boundary.

The model recommendations follow the current OpenAI model roles: Sol for
complex reasoning and coding, Terra for balanced intelligence and cost, and
Luna only for later high-volume mechanical work after a stronger model has
frozen the contract. They are operating recommendations, not authorization,
and should be rechecked against the
[official OpenAI model catalog](https://developers.openai.com/api/docs/models)
when a task is opened.

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
