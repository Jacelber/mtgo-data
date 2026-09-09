# Completed Phase 14 roadmap detail

Historical evidence only; this document never authorizes work.

P14-00 was accepted on 2026-08-30. P14-01 completed through PR #313,
merged as `41d2abd4be5f924c67d8b78762f31dfda3c103af`. The following
roadmap text is retained from the P14-02A cloud baseline
`48ab5e3d14f0a2e90a8aa71049966b06525d1079`; its prospective stop and
permission wording describes that historical stage, not current authority.

### P14-00 — Freeze the Phase 14 contract

- **Problem:** the former ten-line sequence did not identify input evidence,
  exact artifacts, stop conditions, or the boundary between MTGO and Tabletop.
- **Operation:** inventory existing Pauper archives, rule files, catalogs,
  Schemas, consumers, Landing requirements, and event-strategy contracts using
  read-only evidence. Classify explicit Standard/Modern assumptions as active,
  intentional compatibility, synthetic/test-only, or historical. Define exact
  task path envelopes, private/public state transitions, separate shared-repair
  gates, and risk-triggered checks. Do not fetch a real event or change a
  whitelist.
- **Effect:** one Owner-reviewable implementation contract exists without data,
  code, or public behavior changes.
- **Paths:** `docs/audits/P14-00.md`, this Phase 14 section, and the live
  `docs/STATUS.yaml` task contract only.
- **Validation:** focused live-status and roadmap-pointer checks, one final
  changed-scope repository validation, and complete diff review. Do not run
  classifier, data, Schema, browser, candidate, Pages, or production tests.
- **Stop:** Owner acceptance. P14-01 remains separately unauthorized.
- **Recommended model:** `gpt-5.6-sol`, high reasoning.

### P14-01 — Establish and accept Pauper classification

- **Problem:** shared Pauper parent/subtype identities and representative rules
  are not yet an accepted cross-source taxonomy, and the earlier single-step
  wording did not identify where retained-corpus review and final rule
  refinement occur.
- **Operation A — P14-01A taxonomy proposal:** inspect existing behavior and the
  current retained recent Pauper corpus, propose parent/subtype boundaries and
  bilingual identities before coding, and obtain Owner acceptance of the
  classification logic. This proposal is design evidence, not an executable
  classifier.
- **Operation B — P14-01B rule implementation:** encode the accepted taxonomy
  with stable IDs, explicit priorities, bounded representative fixtures,
  conflicts, Unknown reporting, and proposed bilingual identity coverage.
  Classify by stable primary-engine signals rather than incidental cards. A
  subtype-defining parent has no implicit Other or parent-only fallback.
- **Operation C — P14-01C retained-corpus refinement:** replay the implemented
  rules once against the current retained recent corpus; cluster every Unknown
  and every classified-but-reference-inconsistent record by stable primary
  engine and deck similarity; present every affected record, representative
  lists, and an evidence-backed recommendation for Owner confirmation; apply
  only the confirmed reference corrections, intentional Unknown dispositions,
  and rule refinements; then rerun the affected focused evidence and freeze the
  final taxonomy for Owner acceptance. Multiple matches, conflicts, and the
  accepted boundary cohorts remain visible in the same review. Machine replay
  metrics or a generated review queue do not complete P14-01C without the
  clustered Owner review and post-decision rerun. P14-01B and P14-01C are one
  continuous focused implementation task and do not add an intermediate
  authorization gate.
- **Validation:** validate the Pauper rule document and focused fixtures, record
  the retained-corpus impact report, and use only the smallest Standard/Modern
  regression evidence that answers a named shared-validator risk.
- **Effect:** one accepted classifier can later classify both MTGO and the
  approved Tabletop event without copying source-specific archetypes; final
  refinement is complete before private product generation begins.
- **Expected paths:** `my_archetypes/pauper.yaml`, focused Pauper rule fixtures
  and tests, an Owner-review artifact for the proposed bilingual identities,
  and only directly required rule contract paths. The maintained two-format
  name catalog is not extended until P14-03A generalizes its shared contract.
- **Stop:** final taxonomy, retained-corpus report, and proposed bilingual
  identity acceptance after P14-01C. If P14-02 later exposes a material
  classifier defect, stop product generation and return to a separately scoped
  classifier repair; do not mix rule changes into data generation or Landing
  review. Do not activate Pauper execution, generate product output, or import
  the names into the maintained catalog during P14-01.
- **Recommended model:** `gpt-5.6-sol`, high reasoning.
- **Current evidence:** P14-01A, all 13 Owner-review batches, and the completed
  consolidated P14-01B/P14-01C subject are Owner-accepted. Same-task completion
  through one Ready PR, required CI, and merge is authorized. P14-02 remains
  unauthorized.

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
- **Completion evidence:** the shared third-format repair and private Pauper
  candidate merged through PR #361 and PR #362. The candidate remained
  `public: false`, with no consumer-catalog or Pages admission.

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
- **Completion evidence:** the Owner accepted the Pauper 2026-W35 bilingual
  Landing subject on 2026-09-06. The imported private review binds workbook
  SHA-256 `b2d565484d3d112eb056fe6b536196f23b6eb00ccb14374858321f221c97c2e2`,
  six source events, two retained copy paragraphs, and two exact feature decks.
  Pauper remains `public: false`; P14-04 is a separate task.

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
- **Completion evidence:** the Owner accepted the complete private product on
  2026-09-07 after separate Landing/statistics and matchup review. The retained
  official-event match set contains 99 usable archives; eight Videre event IDs
  remain visibly missing, while the reviewed 2026-W35 four-week preview covers
  all 19 expected events. Card names, images, and outbound links follow the
  accepted Chinese/MTGCH and English/Scryfall locale contracts. Pauper remains
  excluded from public catalogs and Pages assets.

### P14-05 — Trial the Owner-supplied Paupergeddon event

- **Problem:** the event's real round labels, decklists, and result completeness
  could not be established from assumptions.
- **Operation:** after the Owner supplied Melee event `438329`, collect it once
  into a disposable private location, classify it with the accepted Pauper
  taxonomy, and validate the proposed `constructed_day2` strategy without
  changing the formal registry or public catalog.
- **Effect:** the source, round strategy, and classifier compatibility were
  reviewed before any retained event admission.
- **Validation:** the retained checkpoint was reused through the bounded source
  compatibility repair and full classification review; no repeated real-data
  request was used as a substitute for diagnosis.
- **Stop:** Owner acceptance of the admit conclusion; P14-06 remained separately
  authorized.
- **Recommended model:** `gpt-5.6-sol`, high reasoning.
- **Completion evidence:** the Owner accepted the repaired source-compatibility
  result and every classified or intentional-Unknown event record. The private
  checkpoint then became the exact retained input authorized for P14-06.

### P14-06 — Implement the separately approved Paupergeddon product

- **Problem:** a successful disposable trial was evidence, not authority to
  retain or publish the event.
- **Operation:** register only event `438329`, normalize its retained checkpoint,
  generate event-specific overview and matchup statistics, and prove the
  active-taxonomy and private-public boundaries before Owner review.
- **Effect:** a private Tabletop Pauper candidate reused the shared classifier
  while its source data and statistics remained separate from MTGO.
- **Expected paths:** the exact event registry entry, approved source and
  normalized event data, `stats/pauper/melee/`, applicable manifest entries,
  and focused producer and consumer tests.
- **Stop:** Owner acceptance of the exact private Tabletop subject; catalog and
  Pages admission remained unopened.
- **Recommended model:** `gpt-5.6-sol`, high reasoning.
- **Completion evidence:** the Owner accepted the private event `438329`
  overview and matchup product. The normalized event digest retained for final
  publication is recorded in `docs/audits/P14-07B.md`.

### P14-07 — Coordinate admission, publication, and closeout

- **Problem:** enabling only one source or MTGO view would create a partial
  public format and inconsistent navigation.
- **Operation A — shared production acceptance:** generalize the complete-public
  production and admission boundary with synthetic third-format subjects while
  preserving least privilege, concurrency, validation before publication,
  failure reporting, and exact-evidence Pages admission.
- **Operation B — coordinated admission:** after separate acceptance of the
  unchanged MTGO and Tabletop subjects, admit every required Pauper product
  together through generated catalogs, verify retained product behavior, and
  use the normal commit, Ready PR, merge, exact-SHA Pages, and documentation
  closeout gates.
- **Effect:** Pauper appears once as a complete catalog-driven format with
  separate MTGO and Tabletop products and the accepted bilingual card behavior.
- **Validation:** the final immutable candidate received one complete repository,
  rule, Schema, invariant, and production-consumer validation path.
- **Stop:** Phase 14 complete. Phase 15 remains separately unauthorized.
- **Recommended model:** `gpt-5.6-sol`, high reasoning.
- **Completion evidence:** P14-07A's shared boundary, the Elves compatibility
  repair, and the W36 Grixis Control/Jund Ramp classifier repair were separately
  accepted before final restaging. Classifier repair PR #392 merged as
  `6dfbbe26002730b795219b1822179c831959bdc9`. On 2026-09-10 the Owner authorized
  the exact 109-event Pauper initial public scope through `12853701`, explicitly
  excluding `12853710`, and authorized the coordinated PR, merge, and Pages
  publication chain. Exact candidate evidence is in `docs/audits/P14-07B.md`.

## Final acceptance criteria

Phase 14 completed with the card-localization rights gates still enforced, one
shared Pauper taxonomy across both sources, and no parallel Pauper statistics
engine, renderer, page, catalog, workflow, or source-specific taxonomy. MTGO
and Melee source data and statistics remain separate. The complete five-product
catalog admission is atomic, classifier and generated-contract checks pass,
and event `12853710` remains outside the accepted public scope. Phase 15 is not
authorized by this closeout.
