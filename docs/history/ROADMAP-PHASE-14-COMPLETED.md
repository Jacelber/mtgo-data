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
