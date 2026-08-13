# Development Roadmap

## Document purpose

This document defines the approved development order for the `mtgo-data` repository.

It is an authoritative planning document for AI assistants, coding agents, and human developers.

Development must proceed phase by phase. A later phase must not begin until the current phase meets its acceptance criteria, unless the project owner explicitly approves a change of order.

This document defines development order and phase-level acceptance criteria.

Detailed product boundaries belong in `docs/PROJECT_SCOPE.md`.

Detailed statistical definitions belong in `docs/STATISTICS_SPEC.md`.

Detailed code, data, schema, and front-end paths belong in `docs/DATA_ARCHITECTURE.md`.

Confirmed scope and statistical decisions belong in `docs/DECISIONS.md`.

Current implementation progress belongs in `docs/STATUS.yaml`.

---

## Roadmap status

The current implementation phase and the next approved action are tracked in `docs/STATUS.yaml`.

Before starting work, read `docs/STATUS.yaml` and confirm:

- the current phase;
- the current working branch;
- the next approved task;
- known blockers;
- prohibited next actions.

This roadmap defines the approved phase order, objectives, dependencies, and acceptance criteria. It does not hard-code the live project phase.

If a historical phase-status statement elsewhere in the repository conflicts with `docs/STATUS.yaml`, use `docs/STATUS.yaml` for current progress while continuing to use this roadmap for development order and phase acceptance criteria.

---

## Phase index

This index records roadmap position, not standing authority to begin work.
`docs/STATUS.yaml` remains authoritative for current task authorization, known
blockers, and stop conditions.

| Phase | One-line objective | Roadmap status |
| --- | --- | --- |
| Phase 0 | Establish authoritative project documentation. | Completed |
| Phase 1 | Protect and document the Standard regression baseline. | Completed |
| Phase 2 | Establish shared classification foundations. | Completed |
| Phase 3 | Generalize the Standard-only MTGO pipeline. | Completed |
| Phase 4 | Split the MTGO front end without changing behavior. | Completed |
| Phase 5 | Establish the controlled Melee ingestion baseline. | Completed |
| Phase 6 | Deliver the Modern MTGO product. | Completed |
| Phase 7 | Deliver the Tabletop mixed-event backend. | Completed |
| Phase 8 | Deliver the format-first MTGO and Tabletop front ends. | Completed |
| Phase 9 | Support pure Constructed Tabletop event structures. | Completed |
| Historical Phase 10 | Specify mixed Draft and Constructed event behavior. | `superseded_by_phases_7_and_8` |
| Phase 10 | Establish data governance, compliance, and production operations. | Completed on 2026-08-02 |
| Phase 11 | Establish the engineering baseline and reduce structural debt. | Completed on 2026-08-04; P11-04 and P11-09 remain skipped by owner decision, and P11-01 through P11-15 are published |
| Phase 12 | Productize loading, state, accessibility, sharing, and an editorial MTGO landing experience under one durable visual system. | Planned; not authorized |
| Phase 13 | Aggregate compatible multi-event matchups from raw counts. | Planned; not authorized |
| Phase 14 | Add Pauper MTGO and approved Paupergeddon support. | Planned; not authorized |
| Phase 15 | Add Pioneer through the established dual-product process. | Planned; not authorized |
| Phase 16 | Add Legacy and approved Eternal Weekend Legacy support. | Planned; not authorized |
| Phase 17 | Add qualifying Standard Tabletop events. | Planned; not authorized |
| Phase 18 | Decide whether Vintage should be implemented. | Decision gate; not authorized |
| Phase 19 | Complete release and long-term maintenance readiness. | Planned; not authorized |

Post-Phase-9 governance task `R-01` completed the roadmap renumbering through
pull request #138 and merge commit
`e8bf64f377bd31595b0f3fbbaf05276718e0c2d2`. The separate repository-fact
reconciliation task `R-02` completed through pull request #139 and merge
commit `fc13babbcd5469b77f3c879de753be5fbdbeafdc`. Neither governance task
authorized Phase 10; the owner separately authorized P10-01 on 2026-08-01.

---

## Development principles

All phases must follow these principles:

1. Preserve the currently working Standard MTGO implementation until regression protection exists.
2. Keep MTGO and Melee source data separate.
3. Keep MTGO and Melee normalized data separate.
4. Keep MTGO and Melee generated statistics separate.
5. Do not merge MTGO and Melee results into one statistic.
6. Share classification logic and reusable statistical utilities where appropriate.
7. Do not silently ignore malformed, incomplete, or ambiguous data.
8. Generate explicit reports for Unknown decks, classification conflicts, missing data, and data-quality problems.
9. Add tests before replacing working legacy behavior.
10. Do not develop directly on `master`.
11. Use small, reviewable branches and commits.
12. Do not manually edit generated JSON as a substitute for fixing the generating code.
13. Update specifications, schemas, and tests whenever statistical behavior changes.
14. Keep GitHub Pages compatible without requiring a front-end build framework unless separately approved.
15. Keep existing public data paths compatible until a migration plan exists.
16. Stop after each guided task and wait for user confirmation.
17. Do not delete legacy scripts until their replacements have been verified.
18. Record important scope or statistical changes in `docs/DECISIONS.md`.
19. Update `docs/STATUS.yaml` at the end of every completed phase.
20. Treat `PROJECT_NOTES.md` as historical context rather than the current specification.

---

## Approved product direction

The repository will support two separate product areas:

1. **MTGO Environment Trends**
2. **Tabletop Major Events**

The Tabletop Major Events product may use Melee as a data source, but the user-facing product should not be named only “Melee.”

The intended constructed formats are:

- Standard
- Pauper
- Modern
- Pioneer
- Legacy
- Vintage, only if approved at a later decision gate

The approved format-development order is:

1. Preserve Standard as the regression baseline.
2. Generalize the Standard-only MTGO pipeline.
3. Implement Modern for MTGO as the first post-Standard format.
4. Implement the approved mixed-format Modern Pro Tour reference event.
5. Complete reusable mixed-event and pure Constructed strategies.
6. Implement Pauper for MTGO and the approved Paupergeddon event.
7. Implement Pioneer.
8. Implement Legacy.
9. Add qualifying Standard tabletop events when the Melee pipeline is stable.
10. Decide whether Vintage should be implemented.

---

## Approved event policy

Melee must not be crawled without an event whitelist.

Approved events must be registered manually in:

`configs/melee_events.yaml`

Target event categories are:

- World Championships;
- Pro Tours;
- Regional Championships;
- Magic Spotlight Series;
- Paupergeddon main events;
- Eternal Weekend Legacy main events;
- Eternal Weekend Vintage main events, if Vintage is approved later.

The following are excluded unless the project owner explicitly changes the policy:

- team events;
- pure Limited events;
- side events;
- unrelated local events;
- qualifiers that are not specifically approved;
- events that are not present in the whitelist.

Mixed Draft and Constructed events are allowed only when the Constructed rounds can be identified reliably.

---

# Phase 0 — Authoritative documentation

## Objective

Create a stable documentation system that allows any AI assistant, coding agent, or human developer to understand the project without reconstructing requirements from conversation history.

## Required files

Create and review:

- `AGENTS.md`
- `CLAUDE.md`
- `.github/copilot-instructions.md`
- `docs/PROJECT_SCOPE.md`
- `docs/STATISTICS_SPEC.md`
- `docs/DATA_ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/DECISIONS.md`
- `docs/STATUS.yaml`

Add a historical-document warning to:

- `PROJECT_NOTES.md`

## Required decisions to document

The documentation set must establish:

- MTGO and Melee separation;
- shared classification boundaries;
- supported formats;
- format-development order;
- event whitelist policy;
- pure Constructed event modes;
- mixed-format event handling;
- Day 1 and Day 2 handling;
- average-point formulas;
- high-score-region formulas;
- matchup scopes;
- intentional-draw handling;
- bye handling;
- drop handling;
- no-show handling;
- official awarded-win handling;
- playoff handling;
- raw, normalized, and generated data paths;
- front-end structure;
- engineering-quality requirements;
- phase acceptance criteria.

## Acceptance criteria

Phase 0 is complete when:

- all authoritative documents exist;
- document precedence is explicit;
- the documents do not contradict one another;
- MTGO and Melee product boundaries are clear;
- event inclusion and exclusion policy is clear;
- statistical result handling is documented;
- mixed-format behavior is documented;
- the development order is documented;
- `PROJECT_NOTES.md` is clearly marked as historical;
- the documentation changes are committed on a documentation branch;
- a Pull Request is opened and reviewed;
- no production behavior has changed.

---

# Phase 1 — Engineering foundation and Standard baseline

## Objective

Protect the current working Standard implementation before refactoring it.

## Required repository files

Add or improve:

- `README.md`
- `LICENSE`
- `NOTICE.md`
- `requirements.txt`
- `requirements-dev.txt`
- pytest configuration
- `tests/`
- `schemas/`
- rule-validation command
- JSON validation command
- CI workflow
- `.gitignore`

## Standard baseline work

Record a recoverable Standard baseline that includes:

- a baseline Git tag;
- representative Standard input fixtures;
- representative classification fixtures;
- representative generated output fixtures;
- current Unknown output;
- current conflict behavior;
- current public JSON paths;
- a front-end smoke-test checklist;
- a list of current production commands.

The baseline must make unintended behavior changes visible.

## Existing workflow review

Review:

- `.github/workflows/scrape.yml`
- `.github/workflows/update.yml`

Determine:

- which workflow currently updates production data;
- whether both workflows run the same scraper;
- whether duplicate runs can create conflicts;
- which files each workflow commits;
- what schedule is currently active;
- what permissions each workflow uses.

Do not delete or disable a workflow until its production role is confirmed.

## GitHub Actions requirements

CI must use least-privilege permissions.

CI permission target:

    permissions:
      contents: read

Data-update workflows may use:

    permissions:
      contents: write

Workflows must include:

- explicit concurrency groups;
- dependency installation from requirement files;
- pytest execution;
- rule validation;
- JSON or schema validation where applicable;
- useful `$GITHUB_STEP_SUMMARY` output;
- clear failure behavior.

Initial failure handling should use:

- GitHub workflow status;
- GitHub notifications;
- workflow step summaries.

Do not automatically create GitHub Issues for every failed run during the initial implementation.

## Acceptance criteria

Phase 1 is complete when:

- current Standard data can be regenerated;
- baseline tests detect unintended Standard changes;
- production commands are documented;
- duplicate automation is resolved safely;
- dependencies are reproducible;
- CI runs on Pull Requests;
- CI uses read-only permissions unless write access is required;
- data-update concurrency is explicit;
- existing `index.html` still works;
- no multi-format behavior has been introduced accidentally.

Phase 1 completion is recorded in `docs/STATUS.yaml`. The recoverable Standard baseline is tagged as `phase-1-standard-baseline`. Phase 2 remains subject to separate project-owner authorization.

---

# Phase 2 — Shared rule system and classifier

## Objective

Extract format-independent classification behavior while preserving approved Standard classification results.

## Required shared capabilities

Implement reusable support for:

- YAML rule loading;
- archetype IDs;
- rule IDs;
- explicit priority values;
- card-name normalization;
- deck normalization;
- full-match evaluation;
- deterministic result selection;
- Unknown reporting;
- multiple-match reporting;
- conflict detection;
- rule validation.

The shared result model must also support an optional subtype identity beneath the selected archetype.

## Archetype and subtype compatibility

The Phase 2 compatibility classifier must preserve the parent archetype selected by the approved Standard baseline. Different existing rule entries that already resolve to the same legacy archetype may be represented as different subtypes beneath that archetype.

Initial subtype scope is deliberately narrow:

- create subtypes only for existing duplicate Standard archetype rule paths;
- leave subtype unset for every other existing Standard archetype;
- do not add new archetypes;
- do not invent additional subtype taxonomy;
- complete and validate the compatibility classifier before any later rule expansion.

Subtype identity is supplementary. Archetype-level statistics and public compatibility output remain grouped by the parent archetype unless a later approved task changes the relevant schemas, generators, statistics specification, and front end.

## Rule requirements

Every archetype must have:

- a stable machine-readable `id`;
- a display name;
- an explicit `priority`;
- one or more identifiable classification rules.

Every classification rule must have:

- a stable rule ID;
- explicit match conditions;
- validation coverage.

YAML file order must not silently determine the classification result.

Equal-priority conflicts must be reported rather than silently resolved.

Lower-priority matches that are overridden should remain available in diagnostic output.

## Proposed shared code area

The intended shared package is:

    src/
    └── mtgmeta/
        ├── __init__.py
        ├── card_names.py
        ├── classifier.py
        ├── config.py
        ├── deck.py
        ├── metrics.py
        └── rules.py

The exact modules may be adjusted during implementation, but their responsibilities must remain clear.

## Required reports

Generate machine-readable reports for:

- Unknown decks;
- multiple matched archetypes;
- equal-priority conflicts;
- overridden lower-priority matches;
- malformed rules;
- missing IDs;
- duplicate IDs;
- invalid priorities.

## Legacy compatibility

Keep existing Standard entry points available temporarily, including where still used:

- `classify_standard.py`
- `stats_standard.py`
- `stats_matchup.py`

Compatibility wrappers may call the new shared implementation.

## Required implementation sequence

1. P2-01: define the Standard archetype, rule, priority, and subtype migration contract without changing production rules.
2. P2-02: extract shared card-name and deck normalization utilities with legacy parity tests.
3. P2-03: implement the shared rule model, loader, validation, and rule schema.
4. P2-04: migrate Standard rules to stable archetype IDs, rule IDs, explicit priorities, and only the approved compatibility subtypes.
5. P2-05: implement full-match evaluation, deterministic parent-archetype selection, optional subtype selection, and conflict diagnostics.
6. P2-06: route legacy Standard entry points through the shared classifier while preserving every baseline archetype result.
7. P2-07: generate sanitized Unknown, multiple-match, conflict, overridden-match, and subtype diagnostic reports.
8. P2-08: complete Phase 2 regression, generated-output, and front-end behavior verification before considering new archetypes or subtypes.

P2-01 must map all 76 legacy Standard rule entries, all 74 legacy archetype display identities, and the two existing duplicate-name groups (`4-Color Control` and `Izzet Aggro`). It must prove that proposed explicit priorities reproduce the legacy parent archetype for all 3,936 frozen records, including 71 Unknown results and 947 multiple-match records. Production rules and classifiers remain unchanged during P2-01.

## Acceptance criteria

Phase 2 is complete when:

- Standard classification matches the approved baseline;
- every Standard deck's parent archetype matches the approved baseline even when an optional subtype is present;
- archetype IDs are stable and unique;
- subtype IDs are stable and unique within their parent archetype;
- only approved legacy duplicate rule paths produce an initial subtype;
- rule IDs are stable and unique;
- priorities are explicit;
- YAML order does not determine classification accidentally;
- conflicts are visible and reviewable;
- Unknown decks are visible and reviewable;
- tests cover positive, negative, Unknown, and conflict cases;
- malformed rule files fail validation clearly.

P2-08 completed these criteria on 2026-07-20. The full 3,936-deck Standard parent-archetype baseline remains unchanged, only the four approved duplicate-rule subtype paths are selected, diagnostic reports remain reviewable, and generated output is now byte-stable across Python hash seeds. Existing MTGO statistics, Weekly Pickup, and Videre matchup page behavior passed browser regression. The project owner accepted the closeout, and P2-08 was published through pull request #39 and merge commit `a5361fc4ec5a05b07811f47b40daa94ecbc9d0e5`. The recoverable Phase 2 baseline is tagged as `phase-2-shared-classifier-baseline`. Phase 3 remains subject to separate task authorization.

---

# Phase 3 — Generalize the MTGO pipeline

## Objective

Replace Standard-only assumptions with explicit format configuration.

Official MTGO event archival is independently configurable and does not make a format executable. During Phase 3, the six-format legacy raw-event archive remains active while Standard remains the only format authorized for Videre, classification, statistics, Pickup, catalogs, public output, and front-end behavior.

## Required work

Make these functions format-aware:

- event fetching;
- raw event storage;
- normalization;
- classification;
- event statistics;
- range statistics;
- matchup statistics;
- Weekly Pickup where applicable;
- metadata generation;
- catalog generation.

The generalized pipeline should accept an explicit format argument, such as:

- `standard`
- `pauper`
- `modern`
- `pioneer`
- `legacy`

Vintage must not be enabled before the Vintage decision gate.

## Design rules

Do not add formats by copying the complete Standard pipeline into new format-specific scripts.

Format selection should control:

- input paths;
- output paths;
- rule paths;
- format-specific configuration;
- front-end catalog entries.

Selecting one format must not read from or overwrite another format’s data.

## Legacy compatibility

Temporary compatibility wrappers may remain for current commands.

The wrappers must be removed only after:

- the generalized command is verified;
- workflows use the generalized command;
- documentation is updated;
- regression tests pass.

## Required implementation sequence

1. P3-01: define the executable format-aware MTGO pipeline migration contract and inventory every current Standard-only coupling boundary without changing production behavior.
2. P3-02: add the validated format registry and safe repository-relative path resolution, with only Standard executable.
3. P3-03: generalize MTGO event fetching, raw storage, normalization, and classification dispatch while preserving legacy Standard entry points.
4. P3-04: route Standard event and rolling-range statistics through format-aware MTGO internals.
5. P3-05: generalize Videre matchup processing and classification-report routing.
6. P3-06: generalize Weekly Pickup, metadata, and catalog generation where supported by format configuration.
7. P3-07: add the generalized MTGO command entry point and migrate the production workflow after every legacy command has a verified replacement.
8. P3-08: complete fixed-reference Standard regeneration, public-contract, cross-format isolation, and front-end behavior verification.

P3-01 must distinguish known, executable, planned, and decision-gated formats. Only Standard is executable during the migration. Under DEC-033, event archival permission is separate from product execution: a collection-enabled planned format may archive only its own official event data, while every unauthorized product operation must fail clearly and must never silently use Standard paths. P3-01 changes no generator, workflow, public JSON, rule file, or front-end code.

P3-01 completed on 2026-07-20 through pull request #41 and merge commit `c95f156737d10014f6f593ee27378e73b8e06fb3`. Its executable contract is pinned to the Phase 2 recovery baseline. P3-02 remains subject to separate project-owner authorization.

P3-02 local implementation completed in an isolated workspace on 2026-07-20 after explicit project-owner authorization. It adds only the validated format registry and safe repository-relative path-resolution boundary; it does not enable another MTGO format or change production behavior. The local acceptance suite passed. The project owner accepted the result and authorized its separate remote publication on 2026-07-20.

P3-02 was published through pull request #43 and merge commit `485887b89d57407916d7d668c507de739e7b726c`. P3-03 remains subject to separate project-owner authorization.

P3-03 local implementation completed in an isolated workspace on 2026-07-20 after explicit project-owner authorization. It extracts format-aware MTGO event download, parsing, normalization, safe storage, and classification dispatch while retaining the legacy Standard entry points and leaving production data, statistics, workflows, public JSON, and front-end behavior unchanged. The project owner accepted the result and authorized its separate remote publication on 2026-07-20.

P3-03 was published through pull request #45 and merge commit `3bf23ffaf54b8f83146e45c0e8d71974962a6e4d`. P3-04 is the next planned task, but because it migrates production statistics behavior it requires a detailed pre-development review and separate project-owner authorization.

P3-04 local implementation completed in an isolated workspace on 2026-07-20 after detailed review and explicit project-owner authorization. It routes Standard event and 1/4/12/36-week rolling statistics through `src/mtgmeta/mtgo/stats.py`, retains `stats_standard.py` as the production and import-compatibility wrapper, and rejects disabled formats before output side effects. Fixed-reference regeneration produced nine byte-identical Standard statistics documents. Statistical formulas, public JSON, schemas, workflows, rules, Videre processing, Weekly Pickup, metadata, catalogs, and front-end source remain unchanged. The project owner accepted the result and authorized its remote publication on 2026-07-20.

P3-04 was published through pull request #47 and merge commit `e401f64d78081b5ac8ed6cc7ff499e5545485d1d`. P3-05 is the next planned task, but requires a detailed pre-development review and separate project-owner authorization before implementation begins.

P3-05 local implementation was authorized and started in an isolated workspace on 2026-07-20. Its approved scope is format-aware Videre match fetching, matchup generation, and classification-report routing while retaining the existing Standard commands and outputs. It does not authorize another executable format, live Videre fetching, statistical changes, workflow changes, public-contract changes, or remote publication.

P3-05 local implementation completed on 2026-07-20. Standard fixed-reference regeneration produced five byte-identical matchup documents and six byte-identical de-identified classification reports; 1/4/12/36-week counted-match totals remain 619/2,564/6,732/8,247. The legacy production commands and browser behavior remain compatible, disabled formats fail before network or output side effects, and no live Videre fetch, production data change, workflow change, schema change, rule change, or front-end source change occurred. The project owner accepted the result and authorized its remote publication on 2026-07-20.

P3-05 was published through pull request #49 and merge commit `3596fcd5b5ba275e8228aee2931f5814e7ca3ed2`. P3-06 is the next planned task, but requires a detailed pre-development review and separate project-owner authorization before implementation begins.

P3-06 local implementation was authorized and completed in an isolated workspace on 2026-07-20. Weekly Pickup candidate generation, manual publication, MTGO metadata, and public-catalog authorization now use explicit format configuration through `src/mtgmeta/mtgo/pickup.py`; the legacy Standard commands remain available. Fixed-reference regeneration produced byte-identical W28 candidate YAML, W28 base-reference YAML, and `meta.json`. Catalog generation is now capability-gated before Standard statistics, matchup, or Pickup catalog writes. The full 210-test suite and repository, rule, classification-report, and Schema validation pass. Browser regression confirmed the Standard statistics, matchup, and W27 Pickup views with zero console errors. No format was enabled, no production data or public JSON changed, and no workflow, schema, rule, statistical formula, or front-end source was modified. The project owner accepted P3-06 and authorized its commit, push, pull request, and merge on 2026-07-20.

P3-06 was published through pull request #51 and merge commit `82824622a1fc6080b037d368437b91b0dd1c5c5e`. Its first CI run exposed and then corrected a shallow-checkout-only metadata test assumption; the replacement deterministic test and the full remote validation passed. P3-07 is the next planned task, but requires a detailed pre-development review and separate project-owner authorization before any command or production-workflow migration begins.

P3-07 local implementation was authorized and completed in an isolated workspace on 2026-07-20. The new `python -m mtgmeta.mtgo --format ...` entry point covers official event fetching, Videre match fetching, rolling statistics, matchup statistics, Weekly Pickup candidate generation and manual publication, metadata, and de-identified classification reports. DEC-033 separates official-event archival from product execution: Standard, Pauper, Modern, Pioneer, Legacy, and Vintage retain their legacy daily raw-event collection, while only Standard may run Videre, classification, statistics, Pickup, metadata, catalogs, or public generation. The production workflow preserves its single schedule, permissions, concurrency, validation, and publication controls and no longer regenerates the superseded identity-bearing text diagnostics. Legacy root commands remain available as compatibility entry points. No additional product format was enabled, and no live fetch or workflow dispatch occurred. The project owner accepted P3-07 and authorized its commit, push, pull request, and merge on 2026-07-20.

P3-07 was published through pull request #53 and merge commit `3cdf07701a89f88568cf38f9af05265b70a59f66`; the remote repository validation passed before merge. P3-08 is the next planned task, but remains unstarted until its detailed closeout scope is reviewed and the project owner separately authorizes implementation.

P3-08 local implementation was authorized and completed in an isolated workspace on 2026-07-20. A new end-to-end closeout test regenerated 23 fixed-reference Standard statistics, matchup, Pickup, metadata, and classification-report documents into temporary directories; every document was byte-identical to the committed product. All 35 non-Standard product command combinations fail before dispatch or output, while the six-format official-event archive remains available under DEC-033. The 225-test suite and repository, rule, Standard-quality, strict classification-report, and Schema validation passed. Browser regression confirmed the visible 1/4/12-week statistics, deck details, matchup matrices, W27 Pickup, optional-data fallback, and language switching with zero console errors or warnings. The front-end smoke checklist now reflects the long-standing intentional omission of 36-week buttons while automated contracts continue to validate the generated 36-week documents. No production output, generator, workflow, rule, Schema, statistical formula, public contract, or front-end source changed. P3-08 awaits project-owner acceptance and separate remote-publication authorization; Phase 4 is not authorized.

The project owner accepted P3-08 and authorized its publication and the Phase 3 tag on 2026-07-20. P3-08 was published through pull request #55 and merge commit `dd8741fc8b63ded9206cdbf88ac8b87682e3bf14`; the remote repository validation passed before merge. The recoverable Phase 3 product baseline is tagged `phase-3-generalized-mtgo-pipeline` at that merge commit. Phase 3 is complete. P4-01 is the next planned task, but requires a detailed behavior-preservation review and separate project-owner authorization before the monolithic MTGO front end is split.

## Acceptance criteria

Phase 3 is complete when:

- Standard runs through generalized internal code;
- existing Standard public output remains compatible;
- format names are configuration-driven;
- data paths are format-aware;
- unsupported command-and-format combinations fail clearly;
- event collection is limited to the explicit archive allowlist and does not enable product execution;
- selecting one format cannot overwrite another format;
- Standard regression tests pass.

---

# Phase 4 — Split the existing MTGO front end

## Objective

Make the current monolithic `index.html` maintainable before adding major multi-format and Melee front-end behavior.

## Initial target structure

    index.html
    assets/
    ├── css/
    │   └── site.css
    └── js/
        ├── common.js
        └── mtgo.js

Additional JavaScript modules may later be introduced for:

- MTGO statistics;
- decklist display;
- matchup matrices;
- Weekly Pickup;
- localization;
- format navigation.

Later front-end planning must consider how optional subtype information can be displayed or filtered without replacing the parent archetype, changing archetype-level totals, or double-counting decks. The initial Phase 4 split does not have to expose subtypes and must not introduce subtype-level statistical behavior implicitly.

## Preservation requirements

The first split must preserve:

- current appearance;
- current labels;
- current language behavior;
- existing JSON paths;
- existing buttons and filters;
- charts;
- decklist display;
- Weekly Pickup;
- matchup matrix behavior;
- GitHub Pages deployment.

## Restrictions

Do not introduce during the initial split:

- a mandatory Node.js build step;
- a bundler;
- a front-end framework;
- changed statistical behavior;
- Melee-specific statistics inside the MTGO page.

These changes require separate approval if later desired.

P4-01 local implementation was authorized and completed in an isolated workspace on 2026-07-20. The monolithic `index.html` now loads the preserved stylesheet from `assets/css/site.css`, shared browser helpers from `assets/js/common.js`, and MTGO-specific state, data loading, and rendering from `assets/js/mtgo.js`. The scripts remain classic ordered scripts so the existing inline language controls and initialization contract remain compatible. The Standard public-path contract now searches the external JavaScript assets, and a focused structural test protects asset presence, load order, the absence of inline style/script blocks, classic global hooks, and the materially smaller HTML shell. Browser regression preserved statistics, deck details, matchup matrices, Weekly Pickup, localization, and narrow-screen behavior with zero console errors or warnings. No public JSON, statistical formula, generated output, workflow, classifier, rule, Schema, format authorization, subtype presentation, or Melee behavior changed. The project owner accepted P4-01 and authorized its commit, push, pull request, merge, Phase 4 closeout, and Phase 4 tag on 2026-07-20. Publication is pending; Phase 5 is not authorized.

P4-01 was published through pull request #57 and merge commit `ab4a7fe731eee7696215fcfb53588ba85129904c`; the remote repository validation passed before merge. The recoverable Phase 4 product baseline is tagged `phase-4-split-mtgo-frontend` at that merge commit. Phase 4 is complete. P5-01 is the next planned task, but requires a detailed whitelist, source-boundary, normalized-model, and data-quality review plus separate project-owner authorization before any Melee ingestion work begins.

## Acceptance criteria

Phase 4 is complete when:

- `index.html` is materially smaller;
- CSS is loaded from `assets/css/`;
- JavaScript is loaded from `assets/js/`;
- existing Standard behavior passes the smoke-test checklist;
- existing public JSON paths still work;
- GitHub Pages works without a build step;
- the split does not alter statistics;
- MTGO and Melee front-end responsibilities remain separate.

---

# Phase 5 — Melee ingestion and normalized event model

## Objective

Implement safe, reproducible fetching and normalization for explicitly whitelisted Melee events.

The first reference contract is Melee event `434455`, Pro Tour Magic: The Gathering® | Marvel Super Heroes. It is a `mixed` event whose Constructed format is Modern. The event has Draft and Modern Swiss rounds on both days and a Draft Top 8, so stage, round phase, and game format must remain independently represented.

## Planned task sequence

1. `P5-01` — align the approved reference-event and format order, then define the whitelist and normalized-event contracts without network access.
2. `P5-02` — implement whitelist loading, validation, and rejection of unlisted or disabled events.
3. `P5-03` — implement the rate-limited Melee client and raw-response archive with safe re-fetch behavior.
4. `P5-04` — parse stored tournament, standings, decklist, round, and match fixtures.
5. `P5-05` — assemble source records into one normalized event with stable participant and record identities.
6. `P5-06` — normalize stages, formats, result types, and reviewed event-specific overrides.
7. `P5-07` — add quality gates, idempotency checks, Schema validation, and publication blocking.
8. `P5-08` — run reduced-fixture end-to-end validation and, only with separate authorization, prove complete live collection, parsing, normalization, and quality assessment for the reference event.

No Phase 5 task generates Modern classification, statistics, or front-end output.

## Required configuration

Create:

- `configs/melee_events.yaml`

Only enabled whitelist entries may be fetched.

## Proposed Melee package

    src/
    └── mtgmeta/
        └── melee/
            ├── __init__.py
            ├── assembler.py
            ├── client.py
            ├── parser.py
            └── quality.py

## Raw data location

Store raw event material under:

    data_raw/melee/<event_id>/

Possible raw files include:

- tournament page;
- standings pages;
- round information;
- match information;
- decklist information;
- request metadata;
- fetch timestamp;
- source URLs.

## Normalized data location

Store normalized events under:

    data/<format>/melee/events/<event_id>.json

## Client requirements

The Melee client must support:

- request delays;
- pagination;
- limited retries;
- descriptive errors;
- fetch timestamps;
- source URLs;
- raw response preservation where appropriate;
- dry-run or validation-only behavior;
- safe re-fetching.

## Required normalized result types

The normalized model must distinguish:

- played win;
- played loss;
- played draw;
- intentional draw;
- bye;
- no-show;
- unplayed round after drop;
- official awarded win;
- Draft round;
- Constructed round;
- playoff round;
- unknown result;
- unknown round type.

## Data-quality rules

Unknown rounds or results must not be silently included in Constructed statistics.

Fetching must not automatically publish unvalidated statistics.

Raw data and normalized data must remain separate.

## Acceptance criteria

Phase 5 is complete when:

- only whitelisted events can be fetched;
- disabled whitelist entries are rejected;
- raw and normalized data are separate;
- re-fetching does not silently corrupt prior data;
- normalized events include source and timestamp metadata;
- unknown phases are reported;
- malformed results are reported;
- normalized event JSON passes its schema;
- unvalidated data cannot be published as final statistics.

P5-01 local implementation was authorized and completed in an isolated workspace on 2026-07-20. It records DEC-034, registers Melee event `434455` as a verified but disabled mixed-format Modern reference, defines versioned whitelist and normalized-event Schemas, and adds synthetic contract fixtures. Stage, round phase, and actual game format are independent so the reference event's Draft Top 8 cannot be mistaken for a Modern playoff. Repository validation, existing public-output Schema validation, and all 236 pytest tests passed. No network fetch, raw event archive, generated statistic, workflow, public JSON, or front-end behavior changed. P5-01 was published through pull request #59 and merge commit `c742c9d7a78ff7fc6648b2476340ad3e811d64a4`. P5-02 remains separately controlled and is not authorized.

P5-02 was implemented and published from an isolated workspace on 2026-07-21 through pull request #61 and merge commit `a9a6485cfa773d0a68fd095af3bd1f63da7f23f5`. It adds an immutable Melee whitelist registry that rejects malformed, duplicate, unlisted, and disabled entries before any future collection client can obtain a source URL. The reference event `434455` remains disabled and therefore is inspectable but not fetchable. Repository validation, public-output Schema validation, 19 focused Melee tests, and all 247 pytest tests passed. P5-02 made no network request and does not authorize P5-03 or a live Melee fetch.

P5-03 was implemented and published on 2026-07-21 through pull request #67 and merge commit `0caa03b6b1bcf4ad4bfef6adcf467da0a45796e8`. It adds a bounded Melee raw-response client and immutable snapshot archive. Whitelist Schema 2.0.0 requires explicit typed `raw_requests`; the client rejects redirects and out-of-bound URLs, defaults its CLI to dry run, uses bounded retry and pagination, streams responses within per-response and per-snapshot limits, preserves safe response metadata, validates archive manifests against a dedicated Schema, and publishes only complete snapshots. The reference event `434455` remains disabled, so implementation and validation made no live Melee request and produced no real raw archive. Repository, rule, and Schema validation plus all 275 pytest tests passed after the committed-baseline stability hotfix in pull request #66. Parsing, normalization, classification, statistics, front-end work, and P5-04 remain separately controlled.

P5-04 was implemented and published on 2026-07-21 through pull request #69 and merge commit `ac08bef5159e4dc43650d80ccfecac9f81ed299e`. It adds deterministic parsing of stored P5-03 snapshots into immutable source-level tournament, standing, decklist-reference, round, match, decklist, and card records. It verifies manifest paths, byte counts, and SHA-256 values; accepts UTF-8 JSON or exactly one supported JSON payload embedded in stored HTML; rejects duplicate JSON keys, unsupported or missing fields, duplicate source IDs, identity mismatches, unsafe paths, malformed primitives, and oversized responses. The checked-in snapshot fixture is synthetic, deidentified, and validated against the P5-03 raw-archive Schema. The parser retains raw source labels and IDs but does not join participants across resources or assign stages, formats, normalized result types, statistical eligibility, or archetypes. The reference event remains disabled; no live request, real raw archive, normalized event, statistic, workflow, public JSON, or front-end output was created. All 51 combined Melee tests and all 295 repository tests passed. P5-05 remains separately controlled.

P5-05 was implemented and published on 2026-07-21 through pull request #71 and merge commit `6da679d042662d7aa7ccd9f849ad8799473d0fac`. It assembles P5-04 source records into one deterministic, Schema-shaped event; creates event-scoped participant, round, and match identities from source IDs; joins standings, decklists, and match competitors; rejects dangling or conflicting cross-resource references; and preserves source evidence and raw-artifact provenance. Display names do not determine identity, and source-page order does not change the assembled output. Round, format, participant-status, and result semantics remain unresolved for P5-06, so every P5-05 document is explicitly blocked and non-publishable with unknown-phase and unknown-result issues. The stored fixture remains unchanged, and no live request, real raw archive, classification, statistic, workflow, public JSON, or front-end output was created. All 68 combined Melee tests and all 312 repository tests passed. P5-06 remains separately controlled.

P5-06 was implemented and published on 2026-07-21 through pull request #73, implementation commit `d4a3a7c0f69fbff2c1e11b6b69511af2c7dfa0b7`, and merge commit `1eece4d2585a8a420bb1bc907d3b303bb7aa5195`. It resolves reviewed round phases, stages, actual formats, participant states, per-competitor result types and points, and primary Constructed/matchup eligibility. Winner and loser are never inferred from competitor order. Whitelist Schema 3.0.0 adds explicitly verified, evidence-backed event-specific match overrides, including protection for Top 8 lock awards. Unknown or inconsistent records remain blocking; fully resolved output is still non-publishable because P5-07 owns the publication gate. The synthetic stored fixture exercises Draft, Modern, bye, and explicit per-competitor outcomes. All 95 focused Melee tests, all 324 repository tests, the four local validators, and the remote repository-validation check passed. No live Melee request, real raw archive, Modern classification/statistic, workflow, public JSON, or front-end output was created. P5-07 remains separately controlled and is not authorized.

P5-07 local implementation was authorized and completed in an isolated workspace on 2026-07-21. Normalized Melee event Schema 2.0.0 now constrains played and eligibility flags and makes blocking issues incompatible with publication. The deterministic quality gate validates Schema both before and after assessment, checks whitelist authorization, reviewed metadata, raw-artifact digests, stable identities, cross-record references, round and result semantics, and Constructed Swiss eligibility. Missing or unavailable decklists remain visible non-blocking warnings without inventing the deferred OPEN-002 coverage threshold. Only an enabled, verified, otherwise valid event can produce canonical UTF-8 publication bytes; blocked input raises before any write. Repeated input produces identical objects, bytes, and hashes without mutating its source. Windows validation exposed pre-existing platform-default CRLF output in the MTGO statistics, matchup, Pickup, and classification-report writers; those writers and the Melee manifest writer now explicitly use LF, matching committed bytes without changing data or formulas. The 105 focused Melee and Schema tests, all 334 repository tests, and all four local validators pass. The reference event remains disabled and therefore remains blocked. No live request, real normalized event, Modern classification/statistic, workflow, public JSON, or front-end output was created. The project owner accepted P5-07 and authorized its publication on 2026-07-21. P5-07 was published through pull request #75, implementation commit `0e4636ffcc4afcb95c977fe1b714753ce7b97c6a`, and merge commit `1c15c719367edbec1cf8ad0a0348e4d35999d923`; the remote repository-validation check passed before merge. P5-08 remains separately controlled and is not authorized.

P5-08 local implementation and raised live end-to-end acceptance were authorized on 2026-07-21. The reduced-fixture closeout test crosses the stored-raw, parser, assembler, semantic-normalization, quality, Schema, and canonical-publication boundary; proves deterministic objects, bytes, and hashes; confirms the real disabled whitelist entry fails before network or archive side effects; and leaves fixtures and production/public paths unchanged. After the project-branded User-Agent received HTTP 403, owner-approved comparison with the public `j6e/mtg-meta-analyzer` implementation established an anonymous browser-compatible, sequential, bounded DataTables adapter without cookies, credentials, browser-session reuse, or access-control bypass. Raw manifest 2.0.0 records request method, request-body digest, and source context while remaining parser-compatible with 1.0.0 fixtures. Complete temporary validations of event `434455` repeatedly collected 483 responses and resolved 362 participants, 362 decklists, 19 rounds, and 2,296 matches. The real source exposed six participant status labels; normal cut/elimination and explicit drop mappings removed the initial quality blocker, while `Disqualified` remains a distinct retained status. Focused source-semantic audits distinguished seven ordinary byes from seven `Qualified` Top 8 lock awards and four `0-0-3` intentional-draw matches. The one disqualified participant and all 12 affected matches remain retained, but the complete match units are excluded from win-rate and matchup eligibility, removing 6 otherwise eligible Modern Swiss matches. Normalized event Schema 2.1.0 records the distinct state. The final run produced 1,394 eligible Modern Swiss matches, zero unresolved normalization issues, and a publishable non-blocking quality `warning` identifying the disqualification exclusion. All 118 focused Melee and Schema tests, all 347 repository tests, and all local validators pass. All real participant data and private raw snapshots were deleted after anonymous verification; the committed event remains disabled and no statistic, workflow, public JSON, or front-end output was created. The project owner accepted the corrected result and authorized commit, push, pull request, merge, and the Phase 5 tag on 2026-07-21. Publication completed on the same date; detailed evidence is recorded in `docs/audits/P5-08.md`.

P5-08 was published through pull request #77, implementation commit `1cdb06834d2c40b91b660b87a026a8f0fb08ecb4`, and merge commit `f30eb79e651d4ee2d6351872c0a70912c146ec4d`; the remote repository-validation check passed before merge. The recoverable Phase 5 baseline is tagged `phase-5-melee-ingestion-baseline` at that merge commit. Phase 5 is complete. P6-01 is the next planned task but requires a detailed Modern-rule baseline review and separate project-owner authorization.

---

# Phase 6 — Modern classification and MTGO Modern

## Objective

Add Modern as the first new format using the generalized MTGO pipeline and shared classifier.

## Required rule file

Create and validate:

- `my_archetypes/modern.yaml`

## Required work

Implement:

- stable Modern archetype IDs;
- Modern rule IDs;
- explicit Modern rule priorities;
- known-deck test fixtures;
- Unknown reporting;
- conflict reporting;
- MTGO Modern classification;
- MTGO Modern event statistics;
- MTGO Modern range statistics;
- MTGO Modern matchup output where source data permits;
- Modern entry in the MTGO format catalog.

## Separation requirements

MTGO Modern data must remain separate from:

- Standard MTGO data;
- Melee Modern raw data;
- Melee Modern normalized data;
- Melee Modern statistics.

The shared classifier should use the same Modern archetype IDs for both MTGO and Melee.

## P6-01 Modern compatibility baseline

P6-01 uses the public `j6e/mtg-meta-analyzer` Modern classification definitions as the compatibility source rather than inventing a new taxonomy. The reference is pinned to commit `0ecd26bd734cedc6c40e7c753115f796613a32ba`, file `data/archetypes/modern.yaml`, dated 2026-07-08 and licensed as CC BY 4.0 content.

The migrated rule baseline preserves the deterministic signature-card behavior exactly:

- only mainboard cards satisfy signature conditions;
- every signature condition must match;
- the matching rule with the greatest number of signature conditions wins;
- source-list order breaks equal-condition-count ties;
- stable archetype IDs, rule IDs, and unique explicit priorities encode that result independently of YAML collection order;
- unmatched decks remain explicit `Unknown` results.

The upstream corpus-dependent centroid fallback is not part of the compatibility rule baseline because it would turn the result into a function of the surrounding dataset and hide reviewable Unknown decks. The initial migration adds no new archetype or subtype taxonomy.

The frozen P6-01 corpus contains all 5,792 committed `CMODERN` deck records from 181 event files dated 2026-04-01 through 2026-07-20. It uses synthetic record IDs and card counts only. Two misplaced `CPREMODERN` event files and their 64 records are excluded by source format. The shared classifier reproduces all 5,792 reference parent results with zero differences: 5,157 classified records, 635 Unknown records, 324 multi-rule matches, and at most three matches for one deck.

P6-01 creates and validates `my_archetypes/modern.yaml`, the frozen compatibility contract, de-identified corpus, regression tests, decision record, and audit only. It does not enable Modern in the format registry, run production classification, generate Modern statistics or reports, change the workflow, modify public JSON, or change either front end.

P6-02 completes the remaining framework migration and integration work around this rule file. It connects the fixed 38-parent Modern baseline to the generalized shared classification and diagnostic paths, removes any remaining Standard-only assumptions encountered on that path, and adds the necessary integration and report-contract tests. P6-02 must not add or rename a parent archetype, change a signature condition for taxonomy reasons, or define a subtype. Its output must remain compatible with the P6-01 frozen parent results.

P6-03 performs the first taxonomy review. It analyzes the P6-01 Unknown population, multi-rule matches, conflicts, and current representative decklists; then it may propose and test new or revised rules, new parent archetypes, and optional subtypes. Every P6-03 change must report its difference from the P6-01 compatibility baseline. Modern product enablement, statistics, workflow, and front-end work remain later separately controlled tasks.

P6-01 was published through pull request #79, implementation commit `a3ee05a748b0855c91c4b772178d0189c4f29d82`, and merge commit `a09740028b39607021a3a02f1ee1679986f39b85` on 2026-07-21; the remote repository-validation check passed before merge.

P6-02 local implementation was authorized and completed in an isolated workspace on 2026-07-21. It adds a read-only, in-memory classification audit for collection-enabled planned MTGO formats without granting executable product capabilities. The Modern audit loads the fixed P6-01 rules, requires matching rule metadata, admits 181 embedded `CMODERN` event documents, and reports the two misplaced `CPREMODERN` documents as explicit exclusions. It produces the P6-01 totals of 5,792 decks, 5,157 classified, 635 Unknown, 324 multiple matches, zero conflicts, zero invalid decks, and zero selected subtypes without creating a report directory. Shared report construction now requires report format and rule format to agree, and the authorized production report writer rejects cross-format event input before creating output. The production Modern CLI remains disabled. The P6-01 rule bytes, 38 parent archetypes, registry, report Schema, production reports, statistics, workflow, public JSON, and front ends are unchanged. The project owner accepted P6-02 and authorized its commit, push, pull request, and merge on 2026-07-21; P6-03 remains separately controlled and is not yet authorized.

P6-03 local implementation was authorized and completed in an isolated workspace on 2026-07-22. The review used the complete de-identified 5,792-deck Modern corpus together with a read-only comparison against 4,771 high-score classifications from 179 uniquely matched events in the owner-supplied workbook. The workbook itself and all player or event identities remain outside the repository. The production rule file now defines 55 parent archetypes, 100 deterministic mainboard rules, and 54 subtype definitions. Broodscale Combo, Prowess, and Eldrazi Tron use approved shared parents with color or construction subtypes; Energy variants remain separate parent archetypes because their strategic differences are intentionally not reduced to subtypes. The frozen audit classifies 5,664 decks, leaves 128 explicit Unknown, selects 2,329 subtypes, reports 1,519 reviewable multiple matches and 132 same-parent multiple-subtype matches, and produces zero conflicts or invalid decks. A frozen copy of the exact P6-01 rules continues to prove the original 5,792-result compatibility baseline, while a new transition contract records every P6-01-to-P6-03 parent result, selected subtype count, and representative selected identity. All 363 repository tests pass. Modern remains disabled: no production report, statistic, workflow, public JSON, or front-end behavior changed. The project owner accepted P6-03 and authorized its commit, push, pull request, and merge on 2026-07-22. It was published through pull request #81, implementation commit `b313ea5ccbb0b3dee59fdaaaf00193889de228bb`, and merge commit `ccdd2495ed1bbf8029c0d588337220574a3a9b63`; the remote repository-validation check passed.

P6-04 local implementation was authorized and completed in an isolated workspace on 2026-07-22. Modern is now executable but remains non-public and exposes only the classification capability. The production generator writes six de-identified documents under `reports/modern/mtgo/` for 181 embedded `CMODERN` events and 5,792 decks. It classifies 5,664 decks, leaves 128 Unknown, reports 1,519 multiple and overridden matches, 2,329 selected subtypes, 132 same-parent multiple-subtype matches, and zero conflicts or invalid decks. The two misplaced `CPREMODERN` documents identified during P6-01/P6-02 were deleted after the owner clarified that Premodern is a separate unsupported format; no Premodern product or exception path was added. Any future cross-format document blocks generation before writes. The Schema manifest validates all 29 generated Standard and Modern output documents. Standard report bytes remain unchanged, and every Modern capability other than classification still fails before output side effects. No Modern statistics, match data, Pickup, metadata, catalog, workflow, public-format entry, or front-end behavior was enabled. P6-04 was published through pull request #82, implementation commit `1b5eb7fe79153405445107a363821f3157211ad3`, and merge commit `9589f6a1f00da5c4880d6a7c832e76bb2717aa63`; the remote repository-validation check passed before merge.

P6-04A is an owner-requested read-only follow-up audit of the Modern/Premodern collection boundary. The current parser takes the complete first URL segment after `/decklist/` and accepts a candidate only when that segment exactly equals the explicitly requested format. Consequently `premodern-*` is `other` when Modern is requested, while Modern leagues are independently excluded. The existing regression test covers this exact distinction. An anonymous live evaluation of the current discovery function against the June and July 2026 MTGO archive pages found 50 and 42 Modern candidates respectively, alongside 48 and 34 Premodern links, with zero Premodern links selected in either month. Repository history shows that the two removed files entered with the initial database import even though the tracked crawler already had the exact-token safeguard; their precise pre-repository provenance is not recorded. No fetch-code, configuration, workflow, or test correction is required. The audit is recorded in `docs/audits/P6-04A.md`; the owner accepted the result and authorized its remote documentation publication on 2026-07-22.

P6-05 enables only the next Modern product layer: MTGO event statistics and 1-, 4-, 12-, and 36-complete-week rolling statistics under `stats/modern/mtgo/`. The primary aggregation uses the stable selected parent archetype ID, which is emitted beside its display name in new Modern range and representative-deck documents; a selected subtype therefore neither creates a separate metagame row nor double-counts a deck. Statistics input must contain the exact embedded `CMODERN` marker; any cross-format document blocks generation before output. The range index belongs to this statistics product and therefore no longer requires the broader `catalog_generation` capability. Modern remains non-public, and matchup data, Weekly Pickup, metadata, the public format catalog, production workflow, and front-end selection remain outside P6-05. Existing MTGO statistics Schemas are extended to accept Modern while the committed Standard documents remain byte-compatible. The local implementation generated nine deterministic documents from all 181 Modern inputs while correctly limiting complete-week statistics to 179 events and 5,728 decks through 2026-07-19; all 374 repository tests pass. P6-05 was published through pull request #84, implementation commit `57b642b0e2e31e539d88812dd69f42d1a8dd1d1c`, and merge commit `f0be04a557c4b2cb02a52372618fd066d14761a2`; remote repository validation passed before merge. No follow-up task is currently authorized.

## Remaining Phase 6 sequence

### P6-06 — Hierarchical Modern matchup calculation

Define and implement the shared hierarchical matchup contract before designing
the final interface. Fetch and preserve approved Modern Videre match records,
generate 1-, 4-, 12-, and 36-complete-week Modern matchup outputs, and retain
canonical directed W-L-D counts that support parent-parent, subtype-parent,
parent-subtype, and subtype-subtype views. The default statistical view remains
the fully collapsed parent matrix. Parent and subtype rollups must use stable
IDs and must never average percentages.

P6-06 must keep Modern non-public, keep Standard public bytes compatible, and
exclude Premodern exactly. It must not add a synthetic residual subtype. A null
subtype under a parent that defines subtypes is blocking under the approved
no-residual policy recorded by OPEN-005.

P6-06 local implementation was authorized and completed in an isolated
workspace on 2026-07-23. An exact Modern-only Videre fetch requested 187 event
IDs, wrote 165 public raw-response files, received 22 explicit no-result
responses, and had zero failures. Four Modern Last Chance raw files are
preserved but excluded from statistics because no corresponding official
decklist event was admitted. The generated 1-, 4-, 12-, and 36-week outputs
contain 793, 3,266, 8,475, and 10,817 counted physical matches respectively.
They publish canonical directed counts for 92 taxonomy leaves beneath 55
parents, mark the 17 multi-subtype parents as expandable, and reproduce every
parent cell exactly by count rollup. Independent row and column aggregation
supports all four parent/subtype view combinations without averaging
percentages. The no-residual condition blocks visibly, Premodern remains
excluded, Standard matchup bytes remain unchanged, all 43 Schema-managed
outputs pass, and all 381 repository tests pass. Modern remains non-public; the
workflow, Pickup, metadata, catalog, and front end are unchanged. Detailed
evidence is recorded in `docs/audits/P6-06.md`. Owner acceptance and separate
remote-publication authorization were granted on 2026-07-23. P6-06 was
published through pull request #86, implementation commit
`f0e76aeb32a37093e6cbf439107fec18ea874555`, and merge commit
`8b600a70d6e01c6e630fff5e27b28f083cc54730`; remote checks passed. P6-07
remains separately controlled.

### P6-07 — Modern Pickup, metadata, and hierarchy catalog

Generate Modern Weekly Pickup and format metadata after P6-06 is accepted.
Expose stable parent/subtype hierarchy metadata, including the taxonomy-based
expandability rule, without yet changing the public format catalog or front
end.

P6-07 local implementation was authorized and completed in an isolated
workspace on 2026-07-23. Modern now has the three scoped capabilities
`weekly_pickup`, `metadata_generation`, and `catalog_generation` while remaining
non-public. The generated hierarchy catalog contains all 55 maintained parents
and 92 most-specific leaves and marks exactly the 17 parents with at least two
defined subtypes as expandable; it is byte-for-byte aligned with the hierarchy
embedded by P6-06. Modern metadata references the statistics, matchup, and
hierarchy catalogs and reports measured Videre coverage of 183 admitted
official events, 161 with stored archives, 22 without archives, 165 stored
archives total, and four archives outside the admitted statistics set.

The one-time Pickup bootstrap records 54 parent archetype IDs observed in the
latest 12 complete weeks. The real 2026-W29 review artifact contains 92
deduplicated Top 8 candidate decklists, all existing parents, including stable
parent IDs and 35 selected-subtype identities. Every candidate remains
unapproved; no weekly Pickup document or index was published. Candidate
generation still cannot update known state. Standard generated bytes, workflows,
the public format catalog, and the front end are unchanged. Detailed evidence
is recorded in `docs/audits/P6-07.md`. Owner acceptance and remote publication
were authorized on 2026-07-23. P6-07 was published through pull request #87,
implementation commit `939914efc8079d302dd4defbfbf1bb5355e4dfad`, and merge
commit `2a94d7eb4d235612e6d4217da37922f73d53d1d6`; remote checks
passed. P6-08 remains separately controlled.

### P6-08 — Modern production workflow

Add authorized recurring Modern Videre collection and deterministic Modern
statistics, matchup, Pickup, metadata, Schema, and production-candidate
validation to the production workflow. Keep MTGO formats and tabletop products
separate.

P6-08 local implementation was authorized on 2026-07-24. The single scheduled
workflow retains official-event archival for Standard, Legacy, Pioneer, Pauper,
Vintage, and Modern, while the complete product loop runs only Standard and
Modern Videre collection, statistics, matchups, Pickup candidate preparation,
metadata, and strict classification diagnostics. Modern additionally
regenerates its maintained hierarchy catalog; Standard hierarchy migration
remains P6-09 work. Weekly Pickup remains candidate-only, manual approval and
publication remain unchanged, and Modern remains absent from the public format
catalog and front end.

The production-candidate baseline advances to version `2.0.0` and derives both
collection formats and complete products from the format registry. It validates
event and match counts per format, rejects embedded cross-format event data,
limits statistics and reports to complete products, and preserves the
restrictive allowlist for newly created generated paths. An offline production
simulation from the current committed archive regenerated both products,
passed strict Standard and Modern classification, and passed the dynamic
candidate gate with changes confined to existing Standard and Modern generated
outputs. No network fetch, workflow dispatch, generated-data commit, public
catalog change, or front-end change is part of local P6-08 acceptance.
The owner accepted the local implementation and separately authorized commit,
push, pull request, and merge on 2026-07-24. A manual production workflow
dispatch remains separately controlled.

P6-08 was published through pull request #88, implementation commit
`1d9ab80257d2ecf77c4fc17457959676a6cf14e1`, and merge commit
`3fab907bb778d86c3bb3b441718fff929baab870`; pull-request validation,
post-merge validation, and Pages deployment passed. The owner then authorized
real Standard and Modern production verification. Runs `30056505630` and
`30056952539` both passed the clean-checkout baseline and six-format official
event collection, then failed closed during Modern Videre collection when event
`12838888` returned HTTP 408. Standard had zero Videre failures, and neither run
created a production commit or changed master.

P6-08A is the focused reliability follow-up. It adds request-level bounded
retries for HTTP 408, 425, 429, 5xx, connection failures, and timeouts without
weakening the data-quality gate. Explicit `400 No results found` remains a
non-failing missing archive; other non-transient HTTP failures are immediate;
and exhausted retries remain publication-blocking. P6-08A changes no
statistical formula, generated document contract, workflow, public catalog, or
front-end behavior. P6-09 must not begin until the hotfix is published and one
complete real Standard/Modern production run succeeds.

P6-08A was published through pull request #89 and merge commit
`1259b672b0eb62e078becb836b911b6ca44fa5d2`. Production run
`30059165608` then completed successfully. Event `12838888` returned HTTP 408
on its first request, the bounded retry path ran, and the source subsequently
resolved to an explicit non-failing no-results response. Standard and Modern
generation, strict classification, candidate validation, publication
confirmation, and the following Pages deployment passed. The resulting
production commit is
`ee83e92d19f2b5ba779f250ef5e225bc80334747`.

### P6-09 — Shared hierarchical matchup front end

Apply the shared hierarchical calculation to Standard before changing the
front end. Prove that the fully collapsed Standard result reproduces the
existing parent-level matrix, then migrate Standard and Modern to one shared
renderer. The matrix defaults to parent archetypes; row and column parents can
expand independently; a global control expands or collapses all eligible
parents; and parents with zero or one defined subtype never expose an expansion
control.

This task owns the Standard migration to the new hierarchical calculation. It
must not leave Standard on the legacy calculation while Modern alone uses the
new interactive matrix.

P6-09 local implementation was authorized on 2026-07-24. Standard now uses the
same stable-ID canonical leaf calculation as Modern. Its original name-keyed
fields remain compatibility aliases derived from the new parent rollup. A
frozen migration contract proves exact equality for every 1-, 4-, 12-, and
36-week parent cell, overall record, visible ordering, and counted-match total
against production commit `ee83e92`; the four windows retain 469, 2,475, 6,597,
and 8,716 counted matches.

The shared static renderer defaults to parent archetypes, expands row and
column axes independently, provides one global expand/collapse control, and
uses maintained taxonomy rather than observed window volume to decide
expandability. Parents with zero or one subtype expose no control. Interactive
records, rates, confidence intervals, and low-sample flags are recalculated
from canonical leaf W-L-D counts, never from averaged percentages. Standard and
Modern are both public format selections, both generate hierarchy catalogs and
complete metadata, and Standard retains its existing public paths.

Local browser acceptance confirmed Standard 4-week transitions of 36x36,
37x36, and 37x37 for independent Izzet Aggro expansion, followed by exact
global collapse. Modern defaults to 50x50 and expands the 16 currently observed
eligible parents to 85x85 with 51 subtype rows and columns; Broodscale exposes
Golgari, Gruul, and Mono-Green. Narrow-screen horizontal scrolling and a
zero-error browser console were also confirmed. Remote publication and real
post-merge production verification remain separately controlled. The owner
accepted the implementation and authorized commit, push, pull request, and
merge on 2026-07-24; real post-merge production verification remains outside
that authorization.

P6-09 was published through pull request #90, implementation commit
`033fb0c6656115031e88fa37042ed394276418dc`, and merge commit
`4b9ac8fbbc5ba7452bf732b910e935ac0bc90f06`. Pull-request validation,
post-merge validation, and Pages deployment all passed. No production workflow
was manually dispatched, and P6-10 remains subject to separate owner
authorization.

### P6-10 — Phase 6 closeout

Run the complete Standard and Modern regression, Schema, production, front-end,
and rollup-conservation checks. Confirm that Modern is public only after every
required data layer is available, update phase status, and publish the Phase 6
recovery tag after separate owner authorization.

P6-10 local development and validation were authorized on 2026-07-24 from
production master `f70b6a7`. The closeout adds one cross-layer acceptance
contract without changing product behavior or freezing mutable live counts.
It verifies registry/workflow/public-layer alignment, all four Standard and
Modern hierarchical matchup rollups, Standard compatibility aliases, and the
shared public renderer. A real production workflow dispatch, remote
publication, and the proposed `phase-6-modern-mtgo-product` recovery tag remain
separately controlled.

Local closeout validation found and repaired one front-end-only P6-09 gap:
after independently expanding a parent row or column, replacement subtype
nodes had removed that axis's individual collapse button. The first rendered
subtype now retains one parent-labeled collapse control; other subtype nodes do
not duplicate it, and zero- or one-subtype parents remain non-expandable.
Standard browser behavior now proves `36x36 -> 37x36 -> 36x36`; Modern
Broodscale proves `50x50 -> 52x50 -> 50x50`, and the global control proves
`50x50 -> 85x85 -> 50x50`. Statistics, Pickup states, language switching,
narrow-screen scrolling, and a zero-error console also passed.

All three new cross-layer closeout tests, 103 impacted subsystem tests, and the
final 411-test repository suite pass. All 46 governed JSON outputs, both rule
files, and repository validation also pass. No generated data, rule, taxonomy,
formula, public path, workflow, or source archive changed through the local
closeout implementation.

The project owner separately authorized the real production dispatch and
remote Phase 6 publication on 2026-07-24. Production run `30065570450`
completed successfully from `f70b6a7`, passed the clean-checkout, candidate,
repository, rule, Schema, classification, and publication-confirmation layers,
and published generated-data commit `25df27c`. The commit added one Modern
match archive and one Pioneer official-event archive and regenerated the
affected Standard and Modern public indexes and metadata. Standard classified
4,064 decks with 78 Unknown and Modern classified 5,920 decks with 130
Unknown; both reported zero conflicts and zero invalid decks. Pages deployment
run `30066074838` also passed. P6-10 publication and the
`phase-6-modern-mtgo-product` recovery tag are authorized; the tag must target
the final P6-10 merge commit. After rebasing the closeout onto production
commit `25df27c`, all 411 tests, 46 governed-output Schema checks, both rule
validations, and repository validation passed again; the updated repository
inventory contains 1,015 JSON and 1,191 hygiene-checked files. The owner
accepted the result and authorized pull request #92, merge, and recovery-tag
publication. Once this closeout record is present on `master`, Phase 6 is
complete; exact merge and tag identities remain authoritative in Git and
GitHub history, and no subsequent phase or task is authorized automatically.

## Acceptance criteria

Phase 6 is complete when:

- Modern rules pass validation;
- known Modern fixtures classify correctly;
- rule conflicts are reviewable;
- Unknown decks are reviewable;
- Modern output is separate from Standard output;
- MTGO Modern can be regenerated;
- Standard output remains compatible;
- every collapsed parent matchup is reproducible from canonical subtype-aware
  W-L-D counts;
- Standard is reapplied to the shared hierarchical matchup calculation before
  the expandable front end is accepted;
- the MTGO front end can select Modern without hardcoded Standard-only behavior;
- matchup rows and columns can expand independently by subtype while parents
  with zero or one defined subtype remain non-expandable.

---

# Bridge — MTGO hierarchical subtype range statistics

Before Phase 7 changes the Melee product, complete the independently approved
`BRIDGE-MTGO-SUBTYPE-STATS-01` task for the existing MTGO Standard and Modern
products.

This bridge extends the existing MTGO rolling-range and deck-construction JSON
additively:

- keep the parent archetype as the default and compatibility aggregation;
- nest the complete maintained subtype taxonomy beneath every observed
  subtype-defining parent;
- calculate subtype counts, high-score metrics, Top 8 metrics, conversion,
  points per round, construction deviation, best deck, average deck, Core/Flex,
  and recent construction change from the subtype's own records;
- retain zero-observation maintained subtypes with explicit empty states;
- prove parent totals, rates, construction payloads, and ordering remain
  compatible with the Phase 6 committed baseline;
- update Schemas, specifications, generated Standard and Modern snapshots,
  and regression contracts;
- leave the current front end visually unchanged until its separately planned
  hierarchical statistics controls are implemented.

The existing MTGO production workflow already invokes the shared statistics
generator for enabled formats, so this task must not add another workflow.
Phase 7 remains source-separated and must not merge Pro Tour/Melee data into
these MTGO outputs.

The bridge is complete when local validation passes, the owner accepts the
result, and the focused change is published under separate remote
authorization. Phase 7 does not begin implicitly when the bridge closes.

---

# Phase 7 — Mixed-format Modern Pro Tour reference pipeline

## Objective

Implement the first approved Melee event from fetching through per-event statistics.

## Initial event

The initial approved event is:

- Name: Pro Tour Magic: The Gathering® | Marvel Super Heroes
- Melee tournament ID: `434455`
- Constructed format: Modern
- Event type: mixed Draft and Constructed with Day 2 and a Draft Top 8

The event must be explicitly registered in:

- `configs/melee_events.yaml`

## Approved task sequence

Phase 7 proceeds through the following focused tasks. Each task requires its
own local authorization and acceptance; production workflow dispatch, remote
publication, and the next task remain separately controlled unless the owner
explicitly authorizes them.

1. `P7-01` — activate the verified reference-event contract and freeze the
   source-retention, output, authorization, and no-side-effect boundaries.
2. `P7-02` — collect one complete immutable raw snapshot, support safe
   restart/reuse of complete archived responses, normalize the event, and pass
   the existing Schema and semantic quality gate before retaining the
   production input.
3. `P7-03` — classify submitted Modern decklists with the shared Modern
   taxonomy, retaining parent archetype, subtype, rule evidence, Unknowns, and
   conflicts without changing the MTGO Modern product.
4. `P7-04` — build the mixed-event participation and Constructed-opportunity
   ledger for Day 1, Day 2, all Constructed Swiss, drops, byes, intentional
   draws, disqualification exclusions, and verified Top 8 lock exemptions.
5. `P7-05` — generate per-event overview and deck statistics directly from the
   classified normalized event and the opportunity ledger.
6. `P7-06` — generate parent/subtype-aware matchup statistics for Day 1,
   Day 2, and all Constructed Swiss, with inverse-cell, scope, exclusion, and
   count-conservation checks.
7. `P7-07` — finalize versioned public Schemas, the Modern tabletop event
   catalog, deterministic output packaging, and a separately authorized
   source-specific production workflow.
8. `P7-08` — run the complete real-source production path, validate the
   retained inputs and generated candidates, confirm MTGO/Melee separation,
   close the phase documentation, and create the Phase 7 recovery tag after
   owner acceptance.

The sequence intentionally completes normalized source retention before
classification, classification before statistics, and statistics before
workflow publication. Phase 8 owns the format-first public redesign and
Tabletop Major Events front end; Phase 7 produces the complete event backend
contract that those views will consume.

## P7-01 — Reference-event activation and production boundary

P7-01 changes the verified event `434455` from a disabled Phase 5 reference
contract to the only enabled Melee whitelist entry. It freezes these
boundaries:

- activation authorizes only an explicit manual collection command for this
  exact event and does not enable event discovery;
- complete collection still requires the explicit `--execute --complete`
  command flags;
- P7-01 itself performs no network request and creates no raw, normalized,
  statistical, catalog, workflow, or front-end output;
- immutable raw retention and canonical normalized-event production begin in
  P7-02, not P7-01;
- Modern classification, overview statistics, matchup statistics, workflow
  integration, and the front end remain assigned to their later tasks;
- MTGO Modern data and Melee Modern data remain source-separated.

P7-01 is complete when the registry and Schema accept the enabled verified
event, disabled-event fail-closed behavior remains covered independently,
implicit complete collection remains impossible, no production data path is
created, and the detailed Phase 7 sequence is recorded in the authoritative
documents.

## P7-02 — Complete source retention and normalized production input

P7-02 collects one complete immutable snapshot for event `434455` and promotes
it to canonical normalized input only after the existing raw, Schema, semantic,
and publication-quality boundaries pass. It adds a separate no-network
retention command so a completed snapshot can be verified and reused without
contacting the source.

Safe reuse applies only to a completed, digest-verified snapshot. Interrupted
collections remain all-or-nothing temporary directories and are deleted on
failure; responses from different source moments are never combined. Repeating
normalization for the retained snapshot must be byte-identical, while a
different candidate cannot silently overwrite the canonical event.

The retained P7-02 input includes the source-published participant identifiers,
names, standings, matches, and submitted decklists required to reproduce later
classification and statistics. It remains third-party tournament data under
`NOTICE.md`, separate from project code and from all MTGO data. P7-02 does not
classify decks, calculate event statistics, add a catalog or workflow, or
change either front end; those responsibilities remain P7-03 through P7-08.

P7-02 local implementation completed in an isolated workspace on 2026-07-24.
The bounded client retained snapshot `20260724T092458Z-01` with 483 public
responses (7,729,288 bytes including its manifest). Canonical normalized event
Schema 2.2.0 records 362 participants, 362 standings and decklists, 19 rounds,
and 2,296 matches. The existing semantic gate accepts 1,394 eligible Modern
Swiss matches and emits only the reviewed non-blocking
`disqualified_participant_matches_excluded` warning. Rebuilding from the
retained snapshot is byte-identical. All 429 tests and repository, Standard,
Modern, and Schema validators pass. Remote publication was separately
controlled. The project owner accepted the result and authorized commit, push,
pull request, and merge on 2026-07-24.

P7-02 was published through pull request 95 and merged as
`ff9ccc1c0ad952f5069f22900826fd08732811ee` on 2026-07-24. Repository
validation run 30085905795 completed successfully.

## P7-03 — Classify the retained Modern decklists

P7-03 applies the unchanged shared Modern taxonomy to all 362 submitted
decklists in normalized event `434455`. The canonical normalized event remains
immutable. Classification is stored as a separate deterministic overlay at
`data/modern/melee/classifications/434455.json`, keyed by `participant_id` for
later joins.

The overlay records exact event and rule hashes; parent archetype, subtype,
selected rule and priority; all matched and overridden rule evidence;
Unknown-deck card evidence; conflict and invalid-input evidence; and summary
conservation totals. Strict validation permits Unknowns but blocks conflicts,
invalid decks, and any missing subtype under a parent that maintains subtypes.
The disqualified participant's deck remains classified because deck identity
is archival; P7-04 retains responsibility for match-statistics exclusion.

The retained taxonomy classifies 290 decklists and leaves 72 explicit Unknown.
Of the classified decks, 153 select maintained subtypes and 137 select parents
that define no subtype. There are 75 multiple-match and 75 overridden-match
records, two same-parent multiple-subtype diagnostic records, zero conflicts,
zero invalid decks, and zero residual-subtype violations. The result uses 28
selected parents and 17 selected subtype identities.

P7-03 does not change `my_archetypes/modern.yaml`, raw or normalized event
data, MTGO Modern output, statistical formulas, workflows, public catalogs, or
either front end. Taxonomy improvement for the 72 Unknowns requires a separate
reviewed task; P7-04 may build the participation and Constructed-opportunity
ledger without reclassifying them.

## P7-04 — Mixed-event Constructed-opportunity ledger

P7-04 creates the deterministic internal ledger at
`data/modern/melee/opportunities/434455.json`. It binds the byte-identical
P7-02 normalized event and P7-03 classification overlay by their exact
SHA-256 values and does not mutate either input.

The ledger establishes the 362-player Day 1 field and 220-player Day 2 field,
then emits one record for every scheduled Constructed Swiss opportunity:
1,810 for Day 1 and 1,100 for Day 2. The combined 2,910 theoretical
opportunities reconcile to 2,903 effective opportunities after seven verified
Top 8 lock exemptions. It retains 88 ordinary drop/unplayed opportunities,
four administrative unplayed opportunities after the one disqualification,
seven byes, and the two Constructed intentional-draw matches.

Every row keeps point, theoretical-round, effective-round, win-rate, and
matchup inclusion independent. The 1,394 eligible real matches reconcile
exactly with the normalized event. All six Constructed matches involving the
disqualified participant remain present on both sides but excluded from match
statistics. Draft, playoffs, non-qualifier Day 2 opportunities, unexplained
absences, and inferred Top 8 locks cannot enter silently.

P7-04 adds a versioned Schema, deterministic dry-run/atomic-write command,
synthetic special-result tests, real-event byte-rebuild coverage, and scope
conservation tests. It does not aggregate archetypes, calculate win rates or
matchup cells, create public output, change MTGO, modify taxonomy, add a
workflow, or alter either front end. Those boundaries remain assigned to
P7-05 through P7-08.

The project owner accepted the local P7-04 result and authorized commit, push,
pull request, and merge on 2026-07-25.

P7-04 was published through pull request #99, implementation commit
`f1cef2a72559efdc2a77196a2e400ac04a7e254e`, and merge commit
`687d539b3e7fefa8e4a74b8327f62d4bfe3ebe19`. Pull-request CI, post-merge CI,
and Pages deployment all completed successfully.

## P7-05 — Per-event overview and deck statistics

P7-05 consumes the exact retained event, classification overlay, opportunity
ledger, and Modern taxonomy bytes without changing them. It generates
`overview.json`, `decks.json`, and `quality.json` under
`stats/modern/melee/events/434455/`.

The overview exposes separate Day 1, Day 2, and all-Constructed-Swiss scopes.
It keeps the parent archetype as the default unit, includes Unknown in every
applicable denominator, and nests complete maintained subtype lists beneath
observed subtype-defining parents. Direct subtype totals must conserve their
parent. Stage-specific high-score results are available for Day 1 and Day 2;
the combined scope intentionally has no high-score result. Played-match
records retain raw W-L-D counts and 95% Wilson intervals. No low-sample display
threshold is invented before OPEN-002 is resolved.

The participant deck output preserves submitted decklists, classification,
official standing context, and scope-level opportunity accounting. The
disqualified participant remains archived with the point treatment frozen by
P7-04, while the six affected matches remain excluded from played win rate.
The quality output reports all reviewed exclusions and reconciliation totals.

This task does not create `matchup.json`, `meta.json`, a public event catalog,
workflow integration, or front-end behavior. P7-06 through P7-08 remain
separately controlled.

The project owner accepted P7-05 and authorized commit, push, pull request, and
merge on 2026-07-25. Implementation commit
`777bd5fca5badcee56bf5a82d691219d1f1a3d76` is published through pull request
#100 and merge commit `6f2e483c5baf3245545ce8a68f2a5fa3e76b34da`.
Pull-request CI run `30144216455`, post-merge CI run `30144509446`, and Pages
run `30144509231` completed successfully. P7-06 remains separately
controlled.

## P7-06 — Scoped hierarchical matchup statistics

P7-06 consumes the unchanged retained event, classification overlay,
opportunity ledger, and Modern taxonomy. It rebuilds the P7-05 overview as an
input-validation boundary, then generates only
`stats/modern/melee/events/434455/matchup.json`.

The output keeps `day1`, `day2`, and `all_constructed` scopes and defaults to
the combined Constructed-Swiss view. It emits a complete canonical 55-leaf
matrix and derives the complete 29-parent matrix by independently rolling up
both axes. All maintained subtype nodes, non-subtype parents, Unknown, and
zero cells remain present. Sibling subtype matches remain visible as
non-mirrors when expanded but become parent mirrors when collapsed.

Only complete reciprocal matches whose two opportunity rows have
`matchup_included: true` enter the matrix. Each physical match contributes
exactly two directed observations. The output reconciles Day 1's 861 and Day
2's 533 eligible matches, and retains the 22 combined physical-match
exclusions by reviewed reason. Raw W-L-D counts and 95% Wilson intervals are
available for every cell and overall record; no low-sample threshold is
invented before OPEN-002 is resolved.

The generator is deterministic, read-only by default, and writes atomically
only with `--execute`. Its Schema and output are validated directly but remain
outside the public-output manifest. This task does not add `meta.json`, public
catalog discovery, workflow integration, front-end behavior, taxonomy
changes, or MTGO changes. Those boundaries remain P7-07 and Phase 8 work.

The project owner explicitly authorized local P7-06 development on
2026-07-25. Local implementation and validation are complete in the isolated
`codex/p7-06-event-matchups` workspace. The owner accepted and published P7-06
through implementation commit
`864284328437f400a0e0a906d9d3d5ab9a8a75d6`, pull request #101, and merge
commit `d429b978cb7f2386d9f80c8095b59247d6add97f`. Pull-request CI run
`30146146051`, post-merge CI run `30146467926`, and Pages run `30146467706`
completed successfully.

## P7-07 — Public packaging and manual production candidate workflow

P7-07 generates deterministic event metadata and a Modern Tabletop Major
Events catalog. The metadata binds the exact overview, decks, matchup, and
quality bytes by relative path, Schema version, size, and SHA-256. The catalog
exposes only enabled, verified event `434455`. All six public event and catalog
documents enter the versioned public-output manifest.

A source-specific candidate validator permits only the selected event's new
raw snapshot, normalized Melee inputs, event statistics, and format catalog.
It rejects deletion, mutation of retained raw evidence, another event or
format, and every MTGO path.

The new workflow is manual-only, event-scoped, explicitly concurrent, and
separate from MTGO `update.yml`. It runs the approved full event sequence but
may publish only to `data/melee-<event_id>` for review. It cannot push
`master`, create a pull request, merge, or run on a schedule.

The owner authorized local P7-07 development on 2026-07-25. The task performs
no live source request and no workflow dispatch. P7-08 remains separately
controlled. Local implementation completed in the isolated
`codex/p7-07-publication` workspace with 44 focused, 252 affected, and 488
complete tests passing. Standard and Modern rule validation, 52-document
public Schema validation, and repository validation also pass. The owner
accepted the result and authorized commit, push, pull request, and merge on
2026-07-25. Workflow dispatch and P7-08 remain separately controlled.

P7-07 was published through implementation commit
`9791e7398f9eca1187f146e38aa0dfddb7ee5534`, pull request #102, and merge
commit `30fb4fbdd7a72f093847fc74f33f7a6a654df1c4`. Pull-request CI run
`30148125167`, post-merge CI run `30148439065`, and Pages run `30148438934`
completed successfully.

## P7-08 — Production validation and Phase 7 closeout

The owner authorized P7-08 local preparation on 2026-07-25. The local task
adds one minimal cross-layer acceptance contract, backfills P7-07 publication
evidence, and prepares the Phase 7 closeout audit. It does not change retained
data, generated output, classification, statistics, schemas, workflows, or
either front end.

The first real execution of `.github/workflows/fetch_melee.yml` remains a
separate authorization gate. For retained event `434455`, the expected run
reuses the exact P7-02 immutable snapshot, rebuilds every downstream layer, and
reports no candidate change. Any generated difference or review-branch push
blocks closeout pending investigation. Remote publication, merge, and the
proposed `phase-7-tabletop-major-events-backend` recovery tag also remain
separately controlled.

Local preparation completed in the isolated `codex/p7-08-closeout` workspace.
The three-test cross-layer contract, 255 impacted tests, and the complete
491-test suite pass. Standard and Modern rule validation, all 52 governed
public Schema documents, and repository validation also pass. No retained or
generated data, rule, schema, workflow, front-end source, or statistical
behavior changed. Local preparation stopped before workflow dispatch until
the owner separately authorized the production run recorded below.

The owner separately authorized the first real Melee production candidate
run. Workflow run `30149718594` executed from `master` commit
`30fb4fbdd7a72f093847fc74f33f7a6a654df1c4` and completed successfully on
2026-07-25. It reused retained snapshot `20260724T092458Z-01`; reproduced the
362-participant event, 290 classified and 72 Unknown decks, 2,910
opportunities, 1,394 eligible matches, the 55-leaf/29-parent matchup, and all
six public documents; and passed its 488-test clean-checkout baseline,
candidate boundary, repository, Modern-rule, and 52-document Schema checks.
Every generated layer reported reuse, candidate validation reported zero
changed paths, no review branch was created, and `master` remained unchanged.

The owner accepted P7-08 and authorized its commit, push, pull request, merge,
and the `phase-7-tabletop-major-events-backend` recovery tag on 2026-07-25.
The validated closeout contract satisfies the Phase 7 acceptance criteria.
Phase 8 remains separately controlled and is not authorized.

## Required input work

Fetch and normalize:

- event metadata;
- standings;
- decklists;
- rounds;
- matches;
- Day 1 participation;
- Day 2 participation;
- drop information where available;
- bye information;
- intentional draws;
- playoff information;
- independent stage, round-phase, and game-format labels;
- official Top 8 lock evidence where available;
- source metadata;
- quality metadata.

## Required output location

Generate:

    stats/modern/melee/events/434455/
    ├── meta.json
    ├── overview.json
    ├── decks.json
    ├── matchup.json
    └── quality.json

## Required quality report

Report at least:

- listed player count;
- standings count;
- valid decklist count;
- missing decklist count;
- Unknown archetype count;
- classification conflict count;
- valid played-match count;
- excluded bye count;
- excluded intentional-draw count;
- no-show count;
- drop count;
- Day 2 player count;
- playoff participant count;
- unidentified round count;
- unidentified result count.

## Acceptance criteria

Phase 7 is complete when:

- the event can be fetched only through its whitelist entry;
- raw data is preserved;
- normalized data passes schema validation;
- all exclusions appear in the quality report;
- Modern classification uses the shared rules;
- per-event statistics can be regenerated from normalized data;
- MTGO Modern and Melee Modern remain separate;
- Draft Swiss and Draft playoff records do not enter Modern statistics;
- unexplained quality failures prevent publication.

---

# Phase 8 — Format-first front end and supporting data contracts

## Objective

Redesign the public information architecture around format-first navigation,
add the separate Tabletop Major Events front end, expose parent/subtype data
consistently, and implement only the backend additions required by the approved
interface.

The authoritative execution plan is:

- `docs/audits/P8-FRONTEND-PLANNING.md`

The phase order is fixed:

1. audit the current UI and public data;
2. design and approve the final UI locally;
3. freeze the initial UI behavior and backend consumer contract;
4. implement and validate required backend additions;
5. load representative real generated data into the accepted UI and obtain a
   final owner review;
6. implement the final MTGO and tabletop front ends;
7. run cross-product regression and browser acceptance.

Do not implement backend payloads before the P8-03 UI freeze. Do not implement
the final production front end before P8-07 backend consumer-readiness
acceptance.

## Navigation and source boundary

Format is the primary analysis selector. After a format is selected, expose the
available products:

- MTGO official event statistics;
- MTGO matchup win rates;
- MTGO weekly Top 8 decklists;
- Tabletop Major Events;
- Weekly Pickup.

The available products and paths are catalog-driven. MTGO remains at
`/index.html`, Tabletop Major Events remains at `/melee/index.html`, and the
shared shell may retain the selected format while routing between them. It must
not merge their records, caches, generated statistics, or quality claims.

## Hierarchical interaction

Parent archetypes are shown by default. Eligible parents expand into maintained
subtypes individually, matchup axes expand independently, and one global
control expands or collapses all eligible parents. Parents with zero or one
maintained subtype expose no redundant control.

Subtype labels must be self-contained when displayed, such as
`Grixis Prowess`. Selecting an expandable parent only reveals its subtypes.
Representative deck, average deck, deviation, and recent construction change
use the most specific maintained identity and are never averaged across
different subtypes for display.

## New data products

Phase 8 adds, after contract approval:

- a complete-week MTGO Top 8 view covering every admitted event and its first
  eight finishing decklists when available;
- exact-deck detail that compares the selected event deck with its subtype
  average and deviation base;
- range-specific Videre expected/available/missing event completeness;
- reviewed theoretical-versus-observed MTGO high-score decklist completeness;
- stable self-contained subtype display labels;
- literal all-match win rates with normal draws retained only in the denominator,
  explicit supporting non-mirror rates, and visible mirror matrix cells;
- a direct Tabletop per-event and per-scope overall summary with aggregate
  completion and match records;
- catalog-declared Tabletop event structure and supported scopes, with mixed
  all-Constructed high-score values explicitly unavailable.

The completeness formulas, denominators, event eligibility, exclusions,
rounding, and unavailable states are specified and tested before generators or
front-end presentation change. The browser does not infer them.

## Design method

Use local UI analysis, disposable HTML/CSS/JavaScript prototypes, and browser
review by default. Superdesign is not part of the default phase toolchain.
Before any Superdesign generation or upload, explain the unresolved design
problem, expected value, current price or quota limits, transmitted context,
privacy controls, and local alternative, then obtain separate owner
authorization. Installation or authentication alone is not authorization.

## Tasks

1. `P8-01` — audit current UI, public data consumers, and backend gaps.
2. `P8-02` — build local information-architecture and interaction prototypes.
3. `P8-03` — record the accepted Chinese-first UI behavior, proposed English
   dictionary, target-versus-legacy statistical boundary, and consumer matrix;
   then obtain owner approval to freeze the UI and consumer contract.
4. `P8-04` — specify win-rate migration, completeness, Top 8, subtype-label,
   detail, Schema, and compatibility contracts.
5. `P8-05` — implement the weekly MTGO Top 8 backend product.
6. `P8-06` — implement MTGO matchup and high-score completeness products.
7. `P8-07` — validate Standard/Modern backend consumer readiness against real
   retained production data, exercise the accepted UI with those payloads, and
   obtain the final pre-implementation owner review.
8. `P8-08` — productionize the owner-accepted P8-07 real-data prototype as a
   modular parallel candidate with a shared shell and separate MTGO/Tabletop
   controllers, without replacing a production entry point.
9. `P8-09` — connect the accepted MTGO candidate to `/index.html`, verify it
   one-to-one against the legacy regression and rollback baseline, and retire
   compatibility assets only after acceptance.
10. `P8-10` — connect the accepted Tabletop controller to
    `/melee/index.html`, preserving independent catalogs, loaders, caches, and
    product behavior.
11. `P8-11` — complete cross-product regression, deployed-browser acceptance,
    documentation, and Phase 8 closeout.

Every task requires separate focused authorization. P8-03 and P8-07 are
mandatory owner stop points. P8-03 freezes the initial consumer contract needed
to implement the backend safely. P8-07 is a second, data-backed UI review: the
owner may request final display, density, wording, empty-state, and interaction
changes after seeing representative real payloads. P8-08 must not begin until
that review is accepted. If the P8-07 review discovers a missing or incorrect
statistical payload, return to a separately authorized contract/backend task
instead of reconstructing the value in browser code.

The original P8-08 decomposition route was superseded on 2026-07-29 after
P8-07 became a high-fidelity, owner-accepted real-data prototype and review
showed that Phase 4 had already split the legacy production page. The revised
route uses P8-07 as the implementation source and the deployed page only as a
regression oracle and rollback baseline. P8-08 creates a parallel candidate;
P8-09 and P8-10 retain separate production-entry authorization.

P8-03 was owner-accepted on 2026-07-27. Its contract is recorded in
`docs/audits/P8-03.md`, including the accepted English dictionary and the
target-versus-legacy statistical boundary. It changes no production page,
generator, Schema, fixture, output, workflow, or public path.

P8-04 local implementation defines the parallel versioned target Schema,
representative fixture, formula and compatibility specification, and executable
contract tests. It does not map a new production document, migrate a generator,
rewrite existing statistics, change a workflow, or alter the deployed page.
Owner acceptance remains the stop point before publication or P8-05.

P8-05 local implementation adds a capability-gated Standard/Modern weekly Top
8 producer, product Schemas, manifest mappings, metadata discovery, and
fail-closed scheduled workflow integration. The first release publishes the
latest complete week only: Standard contains 8 events and 64 available
placements for 2026-07-20 through 2026-07-26; Modern contains 13 events and 104
available placements, including 42 subtype identities. Every event has exactly
ranks 1 through 8, and every comparison identity resolves in the same-period
four-week deck output. Historical week retention is deferred until immutable
historical construction-base provenance is specified; P8-07 must review that
boundary with real data. No source fetcher, classification rule, statistical
formula, current production page, or Tabletop output changes in P8-05.

P8-06 implements the accepted MTGO completeness and win-rate migration
contracts without changing the deployed page. Standard and Modern now publish
1-, 4-, 12-, and 36-week completeness documents plus a catalog. Each interval
keeps Videre available, deferred, missing, and excluded event identities and
keeps modeled-versus-observed high-score decklist counts with unsupported
events explicit. Because no durable Videre defer ledger exists, production
does not guess that a missing archive is deferred.

MTGO matchup cells retain their deployed draw-adjusted compatibility fields and
add an explicit literal record. Parent and leaf identities additionally expose
all-match and non-mirror records with physical mirror counts, so P8-07 and the
future front end need no statistical derivation in browser code. The
`completeness_reporting` capability, two product Schemas, metadata discovery,
manifest mappings, candidate boundary, and scheduled producer step make the
product fail closed. P8-06 changes no classifier, fetch policy, Melee output,
or front-end source.

The P8-07 real-data readiness audit found four consumer blockers: subtype labels
were not self-contained outside Top 8, Tabletop still exposed only legacy
draw-adjusted rates, Top 8 comparison references were rolling rather than
historical, and no global format/product catalog existed. The owner authorized
a focused backend bridge before resuming the UI review.

The bridge adds only additive consumer fields and generated discovery. MTGO and
Tabletop subtype nodes now expose complete labels. Tabletop overview and
matchup records keep legacy percentages and add literal win records. The global
catalog declares all six known formats and five approved product slots from
actual published catalogs. Top 8 now retains 2026-W30 as its first immutable
week, stores a same-week comparison-base companion, emits exact-deck deviation
when a valid four-week base exists, and fails if a frozen week or base would be
rewritten. Earlier weeks remain unbackfilled. The bridge changes no front-end
source, classifier, source fetcher, event inclusion policy, or legacy rate
field.

After P8-04 owner acceptance, perform a separately authorized focused
investigation of retained MTGO event `12847150`. The owner verified that the
current official event page contains complete data, while the retained archive
lacks Swiss-score fields. The investigation must trace the original collection
and completeness decision, reproduce the failure where possible, and propose
fetch-time validation, retry/defer behavior, and regression coverage. It must
not be folded into the P8-04 contract change or started automatically.

The separately authorized investigation found that the original and current
fetch completeness gates accept non-empty decklists without standings, after
which `fetched.txt` prevents self-healing. Production-candidate validation also
does not require player-level Swiss evidence, and statistics currently coerce
missing scores to zero. A full retained-archive scan found the same defect in
Modern event `12847150` and Pioneer event `12844304`.

Before P8-05, obtain separate authorization for two ordered focused tasks:

1. `P8-HOTFIX-MTGO-EVENT-COMPLETENESS` — strengthen fetch-time semantics,
   retry/defer diagnostics, normalized candidate validation, and regression
   coverage so no new incomplete event can be retained.
2. `P8-REPAIR-MTGO-EVENTS-12847150-12844304` — perform validated atomic
   source refreshes, prove the retained exception count is zero, activate
   fail-closed statistical consumption, and regenerate affected Modern outputs
   without hand-editing generated data or manipulating the fetched ledger as a
   substitute.

This boundary avoids an invalid intermediate master: enabling strict
statistical consumption before repairing `12847150` intentionally breaks the
committed Modern and Pickup rebuilds. The admission barrier must merge first;
the source repair and consumer strictness must then land together.

The first hotfix has completed local implementation. New playoff payloads now
require complete unique deck, standing, and final-rank identity coverage before
storage or ledger admission, and production-candidate validation rejects
missing normalized Swiss or placement evidence. Existing non-playoff exclusion
behavior and all generated statistics remain unchanged. All 511 tests and
repository, rule, and Schema validation pass; no retained event or workflow was
changed. The owner accepted the hotfix and authorized publication on
2026-07-28. It was published through pull request #112, implementation commit
`35407874a6f23524806f10d967ad437e80322e66`, and merge commit
`444a9da3a66e1f7ba6c256b47d3a4948e120a0c3`; the remote checks passed before
merge.

The separately isolated event repair is locally complete. An explicit
`refresh-event` command validated and atomically replaced Modern event
`12847150` and Pioneer event `12844304` without changing either fetched ledger.
Both archives retain the same event identity, format, player identities, final
ranks, and deck contents; only the five previously absent Swiss-derived fields
were restored. All 671 retained event archives now pass the semantic audit.
Fail-closed statistics reject missing Swiss scores and invalid final ranks, and
the affected Modern statistics and the existing 2026-W29 Pickup candidate were
regenerated from source rather than edited by hand. The fixed 2026-07-13 through
2026-07-19 Modern window keeps 416 decks and 104 Top 8 decks while restoring 27
high-score decks, from 330 to 357. All 517 tests and repository, rule, and
Schema validation pass. The repair was published through pull request #113,
implementation commit `0a952d794db21ed5be53780cb6cea338bdd9b53a`,
and merge commit `c2a5cf24303172a83cc561fd8bfe9ca446c9aad4`.

The full evidence, uncertainty boundary, expected repair invariants, and
acceptance tests are recorded in
`docs/audits/P8-FOLLOWUP-12847150.md`.

The 2026-07-27 daily production commit exposed two migration tests that froze
rolling Standard counts and hashes instead of the compatibility behavior they
were intended to protect. The focused
`P8-HOTFIX-ROLLING-CONTRACT-TESTS` replaces those data-dependent assertions
with immutable synthetic contracts for Standard legacy matchup aliases, parent
rollups, additive subtype statistics, and additive subtype construction
details. It changes no producer, generated data, statistical formula, or public
contract. All 40 focused tests and all 516 repository tests pass.

P8-11 completed the local cross-product regression on 2026-07-30 and was
published through pull request #127, implementation commit
`321792414cc6697d1c3afbbf1679c6267f46c284`, and merge commit
`96f0e234b7ca6db21c35ad00e541cc33fc2081b6`. The deployed MTGO and Tabletop
entries passed catalog routing, bilingual rendering, parent/subtype
interaction, Top 8 detail, mixed-event scope, literal matchup, mirror-cell,
source-separation, and narrow-screen checks. The complete 593-test suite and
all repository, Standard/Modern rule, Schema, and JavaScript checks passed.

That acceptance found a real-data classification defect: ordinary Melee
double-faced card names used `front face // back face`, while the existing
Modern rules used the front-face name. Impact testing rejected a global shared
normalizer change because it altered one frozen Standard classification. The
focused `P8-HOTFIX-MELEE-DFC-NORMALIZATION` instead normalizes only the
temporary Melee classifier input, leaving retained card names, the shared
normalizer, taxonomy, and MTGO behavior unchanged.

The hotfix was published through pull request #128, implementation commit
`a8e7fe098feafbb7faefd39d584422c20a9c4ffd`, and merge commit
`10e6780c2c48585cb05d02492ce81702cbb869c1`. Deterministic regeneration
recovered exactly 62 decklists: 45 Boros Energy, 16 Ruby Storm, and one Mardu
Energy. Event `434455` moved from 290 to 352 classified decks and from 72 to ten
explicit Unknowns, with zero conflicts or invalid decks. The opportunity and
match boundaries remained 2,910 theoretical opportunities, 2,903 effective
opportunities, and 1,394 included matches. All 594 repository tests passed.

The repeated deployed acceptance then confirmed 352 classified and ten Unknown
decklists, 211 classified and nine Unknown Day 2 decklists, 32 observed parent
rows, 58 observed leaf rows, and zero browser console warnings or errors.
The former P8-11 blocker is resolved. The remaining ten Unknown decklists stay
explicit pending later taxonomy review and do not block Phase 8.

The Phase 8 closeout also reconciles the already accepted shared presentation
warning of fewer than 20 valid matches. It is a visual caution marker used by
both MTGO and Tabletop matchup consumers, not a reliability guarantee,
publication gate, match-eligibility rule, or change to the literal win-rate
formula. DEC-060 records that existing production behavior.

Local Phase 8 closure evidence is recorded in
`docs/audits/P8-CLOSEOUT.md`. The owner accepted the closeout and authorized
its remote publication and the `phase-8-format-first-frontends` recovery tag
on 2026-07-30. Phase 9 remains separately controlled and is not authorized.

## Tabletop behavior

The Tabletop Major Events front end supports:

- format and event selection;
- latest enabled event as the catalog-driven default;
- event-specific overview and hierarchical matchup matrix;
- Day 1, Day 2, and all-Constructed scope where applicable;
- W-L-D counts, sample sizes, confidence intervals, and low-sample states;
- visible selection-bias, exclusion, completeness, and quality warnings;
- source-event references;
- optional aggregation only for approved compatible same-format events.

The visible product name is Tabletop Major Events. `Melee` remains an internal
path and source name.

## Acceptance criteria

Phase 8 is complete when:

- format is the primary analysis selector;
- the five product views are catalog-driven by selected format;
- MTGO and tabletop entry points and statistics remain separate;
- parent/subtype controls work on statistics and both matchup axes;
- zero- or one-subtype parents expose no redundant control;
- every visible subtype label is self-contained;
- deck-construction details use the most specific maintained identity;
- weekly MTGO Top 8 exact-deck and subtype-comparison details work;
- Videre and high-score decklist completeness display approved generated
  numerators, denominators, exclusions, and unavailable states;
- the approved Modern Pro Tour is viewable independently from MTGO Modern;
- event overview and matchup data load from event-specific public JSON;
- Standard and Modern baselines, public paths, GitHub Pages behavior, and
  source separation pass regression;
- owner browser acceptance is complete.

---

# Phase 9 — Pure Constructed event strategies

## Objective

Complete statistical support for both pure Constructed event structures.

Phase 9 starts from the accepted mixed Modern event `434455` implementation.
It generalizes the statistical and public-output boundary without redoing
mixed-event ingestion, classification, or Phase 8 front-end work. The retained
mixed outputs are byte-stability regression evidence for every task that
touches a shared generator or Schema.

## Mode A: constructed with Day 2

Configuration value:

- `constructed_day2`

Primary metrics include:

- initial field count;
- initial metagame share;
- average points per theoretical Constructed round;
- Day 2 player count;
- Day 2 metagame share;
- Day 2 conversion;
- Day 2 average performance;
- Day 1 played-match win rate;
- Day 2 played-match win rate;
- all-Constructed Swiss win rate;
- completion and quality indicators.

## Mode B: constructed without Day 2

Configuration value:

- `constructed_single_stage`

Primary metrics include:

- field count;
- initial metagame share;
- average points per theoretical round;
- high-score count;
- high-score-region share;
- conversion from initial field to the high-score region;
- played-match win rate;
- completion and quality indicators.

## Statistical restrictions

Do not invent Day 2 metrics for single-stage events.

Use high-score substitution only where the event has no Day 2 and the statistics specification requires it.

Do not use playoff single-match samples as the primary archetype performance measure.

## Task sequence

1. `P9-01` — Pure Constructed readiness audit and contract plan
   - inspect configuration, normalized data, opportunity accounting, statistics,
     matchup, publication, Schemas, fixtures, and the Tabletop consumer;
   - record each mixed-only guard and fixed-scope contract;
   - freeze the smallest structure-dispatch implementation order;
   - reconcile the Phase 8 closeout publication record as ordinary governance
     maintenance; no production code, data, event admission, or live request.
2. `P9-02` — Pure Constructed fixture and public-contract freeze
   - create deterministic synthetic fixtures for `constructed_day2` and
     `constructed_single_stage`;
   - freeze each structure's scope set, unavailable states, denominator
     evidence, and Schema migration boundary before changing generators;
   - retain byte-identical mixed `434455` reproduction as a mandatory fixture.
   - freeze the single-event scope matrix and the cross-structure multi-event
     rule: multiple selections use only `all_constructed`, while unsupported
     scopes are omitted and temporarily unavailable multi-event scopes are
     disabled with an explanation.
3. `P9-03` — Structure-dispatched opportunity ledger
   - introduce explicit per-structure opportunity construction while sharing
     result eligibility and diagnostics;
   - prohibit inferred Day 2 membership, fictional cuts, and cross-structure
     scopes.
4. `P9-04` — Structure-specific overview and deck statistics
   - add pure Day 2 participation/conversion metrics and single-stage
     high-score metrics from raw opportunity counts;
   - preserve subtype/parent conservation, drop handling, literal W-L-D, and
     mixed output stability.
5. `P9-05` — Matchup, quality, publication, catalog, and Schema generalization
   - make generated documents advertise only their supported scopes;
   - preserve source separation and reject incompatible aggregation or identity
     mismatches;
   - version any public-breaking Schema change deliberately.
6. `P9-06` — Structure-aware Tabletop consumer
   - render the scopes that the selected event declares;
   - show Day 2 conversion only for pure Constructed Day 2 events, high-score
     output only for single-stage events, and the selection-bias warning only
     for mixed events.
   - switch a stage-specific single-event selection to `all_constructed` when
     a second event is selected, disable Day 1 and Day 2 controls during
     multi-selection, and restore only a scope supported by the remaining
     single event.
7. `P9-07` — Bounded real-source pilots (separately authorized)
   - use the owner-approved Standard events `415628`, `425324`, and `419742`
     as one bounded source probe for each supported event structure;
   - read only tournament metadata, final-Swiss standings pagination, and
     per-round match totals needed to verify source shape and estimate a
     complete request plan;
   - do not activate the whitelist, retain raw responses, generate production
     data, or publish an event.
8. `P9-07S` — Resumable large-event collection (separately authorized)
   - replace the fixed 500-decklist and 500-response assumptions with a
     bounded request plan suitable for reviewed 2,000-plus-player events;
   - add checkpointed batches, retry and pacing controls, resumability,
     progress reporting, and atomic finalization;
   - prove that an interrupted run resumes without redownloading verified
     responses and produces the same final snapshot as an uninterrupted run;
   - keep incomplete snapshots ineligible for normalization, statistics, or
     publication.
9. `P9-08` — Cross-structure and cross-format regression and closeout
   - replace hard-coded Modern scope labels with labels derived from the
     selected event's format metadata and the language dictionary;
   - verify Standard labels such as `第一日标准`, `第二日标准`, and
     `全部标准瑞士轮` while preserving the corresponding Modern behavior;
   - verify both pure fixtures, mixed `434455`, public Schemas, Tabletop
     behavior, source separation, and full validation before Phase 9 closeout.

The historical Phase 10 description remains a specification reference for
mixed events. Its substantive `434455` implementation was accepted through
Phase 7 and Phase 8; Phase 9 must preserve it rather than reimplement it.

The former Phase 11, renumbered as current Phase 13 by DEC-063, remains
responsible for implementing the actual compatible multi-event raw-count
aggregation. Phase 9 freezes and exposes the event-level scope information and
consumer selection behavior that current Phase 13 will consume.

P9-04 was published through pull request #132, implementation commit
`2736c700fd42dfa4d8113d4c5223df140ea24627`, and merge commit
`f0fe8937ecacaab67abb9008bc79c473bf884e73`. P9-05 local implementation was
authorized and completed on 2026-07-30. The remaining quality, matchup, meta,
catalog, and public Schema boundary now supports both pure structures while
retaining byte-identical mixed event `434455` outputs. No real event,
whitelist, generated production file, workflow, or front-end behavior changed.
The owner accepted P9-05 and separately authorized remote publication on
2026-07-30. P9-06 was published through pull request #134, implementation
commit `828a6b3ae8f823d6c839737b09c9260d7f6fca48`, and merge commit
`a1db24946a1921c14800218cf674a5d7b16e8a36`.

The owner authorized P9-07 and approved the revised
`P9-07 -> P9-07S -> P9-08` route on 2026-07-30. The bounded P9-07 probe
confirmed all three owner-selected Standard candidates without retaining raw
source responses. Event `419742` exposes 893 decklists and an estimated 1,085
complete-archive responses, so the current fixed limits cannot collect it.
P9-07S is therefore a Phase 9 prerequisite rather than a former Phase 11
(current Phase 13) aggregation task. P9-08 owns the separate format-dynamic
Tabletop label correction and the final cross-format consumer regression.

P9-07 was published through pull request #135, implementation commit
`0a787ed916f843f3b89882e70c0048c7eb978d66`, and merge commit
`85876cbee74bad5ab173ba151ef63e8167f69baa`. P9-07S local implementation
subsequently completed against that merged baseline. Its resumable collector
successfully collected and parsed all 1,085 responses for temporary event
`419742`, then removed the temporary source archive. It does not activate the
event whitelist, retain generated or source data, or change a workflow.
P9-07S was published through pull request #136, implementation commit
`5f05ef325514d93cb76c12aa24d49c0cfac840ea`, and merge commit
`b6ef3a59bd3cfbe29a8a1e3e8a3cf7b45cc84c19`.

P9-08 local implementation completed on 2026-07-31 against master commit
`7249d2451668df2190eca4fc31529fa4a895713c`. The Tabletop consumer now
requires consistent format metadata across its loaded documents and derives
scope labels and format-sensitive notices from that validated format and the
language dictionary. Executable contracts cover exact Standard and Modern
labels in both languages; browser regression preserves mixed event `434455`.
No event was activated and no generated data, workflow, public Schema, or
statistical formula changed. The owner accepted P9-08 and authorized its
publication plus the
`phase-9-pure-constructed-events` recovery tag on 2026-07-31. Phase 9 is
complete when this closeout reaches `master` and the tag targets that merge.
No work under the then-numbered Phase 10 specification, or under the current
post-Phase-9 roadmap, is implied by the closeout authorization.

## Acceptance criteria

Phase 9 is complete when:

- event structure is selected explicitly from configuration;
- the two structures use separate strategies;
- theoretical-round denominators follow the statistics specification;
- drop handling follows the statistics specification;
- high-score thresholds are deterministic;
- tests cover both structures;
- front-end scope labels clearly indicate the selected event format and
  structure-supported scope.

---

# Historical Phase 10 — Mixed Draft and Constructed events

Status: `superseded_by_phases_7_and_8`

This historical specification is retained in full. Its substantive mixed-event
implementation and public consumer work were completed through Phases 7 and 8,
and Phase 9 preserved event `434455` as the mixed-event regression baseline.
The historical `Phase 10` and `Page A` / `Page B` names below retain their
original meaning and are not current task identifiers.

## Objective

Support Pro Tours and World Championships without allowing Draft performance to contaminate Constructed deck statistics.

## Required phase configuration

Mixed events must identify:

- Day 1 Draft rounds;
- Day 1 Constructed rounds;
- Day 2 Draft rounds;
- Day 2 Constructed rounds;
- playoff rounds;
- advancement rules;
- official Top 8 lock behavior where applicable.

Every event round must be labeled as:

- `draft`;
- `constructed`;
- `playoff`;
- `unknown`.

Unknown rounds must be reported and excluded until reviewed.

## Required Constructed scopes

Generate separate scopes for:

- Day 1 Constructed;
- Day 2 Constructed;
- all Constructed Swiss;
- playoffs as contextual data only.

## Day 1 purpose

Day 1 Constructed statistics describe the broad initial tournament field.

Day 1 metrics should include:

- initial archetype count;
- initial metagame share;
- Day 1 Constructed average points;
- Day 1 Constructed high-score metrics;
- Day 1 Constructed played-match win rate;
- completion and drop indicators.

## Day 2 purpose

Day 2 Constructed statistics describe the qualified field.

They are affected by qualification selection, including Draft performance, and must show a selection-bias warning.

Day 2 performance must not be represented by average score alone.

Where data permits, show by archetype:

- Day 2 player count;
- Day 2 field share;
- Day 2 Constructed average points;
- Day 2 played-match win rate;
- Day 2 high-score count or score distribution where meaningful;
- effective theoretical rounds;
- valid real-match count;
- intentional-draw count;
- bye count;
- official awarded-win count;
- Top 8 lock count;
- sample-size warning;
- selection-bias warning.

## Combined purpose

All-Constructed Swiss metrics may combine Day 1 and Day 2 played Constructed Swiss matches.

The combined scope must be labeled clearly.

It must not be described as an unbiased estimate of the initial field because Day 2 participants are selected.

## Official awarded wins

Official awarded wins after a player has locked Top 8:

- do not count as real match wins;
- do not count in played-match win rate;
- do not count in matchup matrices;
- do not count as earned Constructed points;
- must be recorded separately;
- may exempt the affected round from the player’s effective theoretical-round denominator when the official event structure confirms that no match was required.

## Acceptance criteria

Phase 10 is complete when:

- Draft rounds contribute nothing to Constructed deck statistics;
- Day 1, Day 2, and combined Constructed scopes reconcile;
- official awarded wins are distinguishable from played wins;
- intentional draws are distinguishable from played draws;
- unknown rounds are excluded and reported;
- mixed-event output includes selection-bias warnings;
- representative mixed-event tests pass;
- Page A and Page B expose the correct scopes.

---

# Phase 10 — Data governance, compliance, and production operations

## Objective

Establish an explicit privacy, compatibility, storage, and production-operations
boundary before adding more Tabletop events or Constructed formats.

## Required work

- classify retained and public identity fields by source resource and purpose;
- define the compatibility boundary for mixed event `434455` without silently
  changing its current public bytes;
- minimize future raw snapshots before persistence while retaining reviewed
  provenance and resumability requirements;
- separate public-site publication from raw and long-term archive storage only
  after the owner selects an approved design;
- align supported Python runtimes and split fetch, build, publication, and
  failure-notification responsibilities without weakening validation;
- finish format-dynamic whitelist operations and non-programmer documentation;
- retain explicit owner gates for history rewriting, storage migration,
  credentials, remote writes, and production dispatch.

## Task sequence

1. `P10-01` — Data classification and privacy audit
   - inventory retained identity, account, preference, provenance, and public
     event-name fields;
   - classify fields separately for tournament, standings, matches, and
     decklist responses;
   - produce documentation only.
2. `P10-02` — Freeze the explicit `434455` compatibility manifest
   - distinguish event-specific public bytes and reproducibility inputs from
     global catalogs that may expand legally;
   - require separate owner approval for any version migration.
3. `P10-03` — Future-event privacy snapshot v3
   - apply per-resource allowlists before persistence;
   - replace enumerable unsalted participant pseudonyms under a reviewed
     secret or mapping-management contract;
   - do not regenerate the v2 `434455` baseline.
4. `P10-04` — Privacy validation and notice update
   - use Schemas and resource allowlists as the primary production-data gate;
   - use prohibited-field scans only as a scoped supplemental check;
   - document contact and removal procedures.
5. `P10-05` — Owner gate for history rewriting
   - prepare a private independent mirror or Git bundle and prove restoration;
   - document force-push, tag, branch, fork, pull-request, Pages, and
     collaborator effects;
   - stop unless the owner gives separate written approval.
6. `P10-06` — Data and deployment separation proposal
   - compare same-origin Pages artifacts for public assets with independent
     raw-archive storage options;
   - preserve current public URLs;
   - stop for an owner selection before implementation.
7. `P10-07` — Implement the selected separation
   - retain the current public Git data archive and daily commit behavior;
   - replace managed branch-root Pages publication with a fresh allowlisted
     artifact;
   - preserve `434455` compatibility and all approved current paths;
   - report repository, data-tree, and Pages-artifact size without automatic
     deletion or migration.
8. `P10-08` — Unify the Python runtime
   - prefer Python 3.12 for CI and production;
   - document an explicit support matrix if Python 3.11 remains required.
9. `P10-09` — Split production into fetch, build, and publish jobs
   - transfer immutable artifacts between jobs;
   - preserve clean-checkout, candidate, and publication-confirmation layers.
10. `P10-10` — Add MTGO resumability
    - implement checkpoint and restart behavior as a separate focused task;
    - do not combine it with the workflow split pull request.
11. `P10-11` — Add deduplicated failure issues
    - grant `issues: write` only to a dedicated notification job;
    - prevent duplicate open issues without expanding other job permissions.
12. `P10-12` — Complete whitelist operations
    - remove the Melee workflow's hard-coded Modern format and derive the
      event format from the validated whitelist;
    - document approved event addition and refresh for non-programmers;
    - preserve manual review and publication gates.

P10-01 completed its documentation-only audit against master commit
`fc13babbcd5469b77f3c879de753be5fbdbeafdc`. The audit is recorded in
`docs/audits/P10-01.md`. It found that the canonical snapshot declares 483
responses rather than the handoff's incomplete 120-file count, classified the
raw and downstream identity fields without recording participant values, and
confirmed that the committed raw paths are also currently served by GitHub
Pages. No code, Schema, configuration, workflow, raw or generated data,
statistical behavior, public path, or front-end behavior changed. The owner
accepted P10-01, and it was published through pull request #140 and merge commit
`837599002a43f7ce6f200bf03b357eba7e9dc2d3` on 2026-08-01.

P10-02 adds the version `1.0.0` executable compatibility manifest for event
`434455`. It freezes the raw snapshot closure, normalized event,
classification overlay, opportunity ledger, and five event-specific public
documents by exact bytes. It verifies only the selected event and product
projections in the expandable format and global catalogs. No production data,
public catalog, statistic, public path, workflow, source configuration, or
front-end behavior changes. The owner accepted P10-02 and authorized its
publication on 2026-08-01. It was published through pull request #141 and
merge commit `23ed3467e0501ae1796d3326433c05035abb98e5`.

P10-03 implements complete manifest `3.0.0` for future approved events. It
parses source responses in bounded memory, persists only explicit per-resource
allowlists as canonical JSON, and uses event-scoped HMAC-SHA256 participant
references under a required non-secret key ID. Source-published `DisplayName`
is preserved by owner decision; unused account, profile, preference, duplicate
identity, and deck metadata fields are dropped before persistence. Parsers and
retention remain compatible with immutable v2 snapshots, and the P10-02
contract continues to freeze event `434455` exactly. P10-03 provisions no real
secret, changes no workflow or production data, and performs no live fetch.
The owner accepted P10-03 and authorized commit, push, pull request, and merge
on 2026-08-01. It was published through pull request #142 and merge commit
`c2886d20658dab2e490b39e637eccb6b7e4cb436`.

P10-04 adds strict resource Schema `1.0.0` as the primary gate before future
v3 resource persistence and again on read. A resource-scoped JSON-key scan is
supplemental defense and deliberately does not scan source bodies, values,
documentation, the whole repository, or immutable v1/v2 snapshots. The public
notice identifies `djacerror@gmail.com` and separates current-content review,
upstream-source requests, and the separately owner-gated history-rewrite
process. P10-04 changes no production data, statistic, workflow, whitelist,
public path, or front end. P10-05 remains separately owner-gated.

The owner authorized only the P10-05 preparation stage on 2026-08-01. Its
read-only inventory found one introducing commit, 484 current raw files, 21
affected ordinary remote branches, three affected phase tags, and 49 affected
GitHub-managed pull-request heads. The current raw manifest and tournament
paths remain HTTP 200 on Pages. Preparation must create an owner-designated
private independent bundle, prove restoration, document the platform and
collaborator effects, and stop again. It does not authorize a history filter,
path deletion, force-push, ref mutation, GitHub Support request, compatibility
migration, storage migration, or P10-06.

The private bundle and restoration proof succeeded for base
`48a4863a28d6ec6d9b854c7a9d72058c68a0f4aa`: all 216 named refs matched, both
restored repositories passed `git fsck --full`, the master tree matched, and
the restored worktree passed the seven `434455` compatibility tests plus all
repository validators. Backup-directory ACL hardening also passed: inherited
general-user access was removed and only the owner account, Administrators,
and SYSTEM retain access. The owner accepted the completed preparation on
2026-08-01. This acceptance does not select a rewrite outcome or grant rewrite
authority. P10-05 was published through pull request #144, local commit
`78aa1921f78fc4bb1868ab07652b32f812482d67`, and merge commit
`c7dbcb01f92bc70c54928efe4b300ddf9c743fc2`; pull-request validation, master
validation, and Pages runs all succeeded. The owner then selected deferral of
history rewriting until P10-06/P10-07 establish an approved current archive
destination and compatibility successor.

The owner authorized local P10-06 proposal preparation on 2026-08-01. Its
inventory confirms that the current scheduled MTGO workflow commits generated
`data/`, `stats/`, `reports/`, and `fetched.txt` changes directly to master,
while the branch-root Pages deployment serves representative paths from all
four current data layers, including `data_raw/`. The active front end consumes
the `stats/` contract, but that fact alone does not authorize removing any
other current URL.

P10-06 initially recommended a private versioned object archive, but the owner
requested a concrete review of necessity before accepting the added provider,
account, fee, credential, and recovery work. P10-01/P10-03/P10-04 already give
future Melee data a fail-closed field boundary, the owner does not require
approved tournament data to be private, the current Git pack is 17.30 MiB, and
the comparable public `j6e/mtg-meta-analyzer` repository keeps a larger current
data tree in public Git while deploying a separate Pages artifact. Videre's
PostgreSQL and R2 architecture serves a broader database/API product and does
not create a current requirement for this static site.

The owner therefore selected A+ on 2026-08-01. The current public Git
repository and daily commit behavior remain the durable data path. A
separately authorized P10-07 may replace managed branch-root publication with
a fresh allowlisted Pages artifact, preserve every approved URL and event
`434455` compatibility byte, add non-destructive size reporting, and prove
rollback. P10-09 remains the separate fetch/build/publish job split. Cloud
storage, data migration, raw-path removal, compatibility revision, and history
rewriting are deferred unless later measured evidence and separate owner
authorization justify them. P10-06 itself changes no workflow, data,
credential, public path, statistic, or front end and stops again for acceptance
of the revised documents before commit or P10-07 implementation. The local
proposal passed the seven event `434455` compatibility tests, repository,
Schema, rule, and diff validation.

The owner accepted the revised A+ proposal on 2026-08-01 and authorized its
commit, push, pull request, and merge. This publication authorization closes
only P10-06 documentation; P10-07 remains a separate owner gate.

P10-06 was published through pull request #145, implementation commit
`f4cd4100071976c18df9d026224f5d5177c0bc0f`, and merge commit
`82a28d954546cb6112ad0655223fd609035b0b40`. Pull-request validation run
`30699399303`, master confirmation run `30699811157`, and Pages run
`30699810612` all succeeded. The owner then authorized P10-07 local
implementation on 2026-08-01 and directed that the only owner-facing pre-commit
acceptance be verification that both final front ends operate normally; the
agent remains responsible for file, code, permission, compatibility, and
rollback review.

P10-07 builds a fresh artifact from the explicit product roots and preserves
the current public Git data archive and daily commit behavior. The downloaded
legacy Pages baseline contains 1,996 files and 226,062,320 unpacked bytes. The
first local candidate contains 1,584 files and 213,481,951 bytes; its 1,583
source files all match the legacy artifact byte for byte, it adds only an empty
`.nojekyll`, and all 494 protected `434455` paths pass. Code, tests, and internal
development documents remain public through Git but are not copied into the
site. Local implementation does not authorize commit, remote publication,
Pages-source changes, deployment, merge, production dispatch, P10-08, or
P10-09. It stops for owner front-end acceptance before any commit.

The completed local implementation passed 28 focused tests, all 654 repository
tests in 402.73 seconds, repository validation for 135 Python, 1,613 JSON, 22
YAML, 30 reference, and 1,907 hygiene checks, all 69 public Schema documents,
rule validation, and diff validation. A local HTTP server returned all 1,584
candidate files and 213,481,951 bytes exactly. Codex browser automation could
not initialize because its local kernel-asset path was unavailable after one
reset and retry; this infrastructure failure did not reach the candidate site.
Owner browser verification of the two candidate front ends remains the final
pre-commit gate.

The owner completed that browser verification on 2026-08-01 and accepted both
candidate front ends. Commit and publication were authorized. The publication
scope includes branch push, pull request, the recorded legacy-to-Actions Pages
source transition immediately before the exact validated merge, custom Pages
deployment, and restoration of legacy `master` `/` if the new path fails. It
does not authorize a production-data dispatch, P10-08, P10-09, storage
migration, compatibility change, or history rewrite.

P10-07 was published through pull request #146. Its implementation commit
`c97b6d2f6c6269df722dba062a08dfeafebbe9de` merged as
`a2d92c384d386d0a98ab9fd4bb7632ce066b3bfd` after pull-request validation run
`30701806996` passed. The repository Pages source changed from legacy
`master` `/` to GitHub Actions immediately before merge. Master admission run
`30702234519` and custom Pages deployment run `30702234546` passed; the MTGO
and Tabletop entry points plus selected runtime documents matched the merged
source bytes. No production-data workflow was dispatched, and P10-08 began
only after separate owner authorization.

P10-08 changes only the scheduled MTGO update runtime from Python 3.11 to the
already exercised Python 3.12 environment and adds a workflow-wide 3.12
regression assertion. All 655 Python 3.12 tests, repository validation, rule
validation, public Schema validation, and diff validation passed locally. No
source was fetched, no generated data changed, and no production workflow was
dispatched. The owner accepted the local result and authorized its publication
on 2026-08-01; P10-09 remains separately controlled.

P10-08 was published through pull request #147. Its implementation commit
`16138470273477b304f72c03ce1924444e6adc0b` merged as
`3cded88f689b42377370240921e2975d53f97ab3` after pull-request validation run
`30703719148` passed. Master confirmation run `30704150549` and allowlisted
Pages deployment run `30704150587` also passed. No production-data workflow
was dispatched, and both public product entry points returned HTTP 200.

The owner authorized P10-09 local implementation on 2026-08-01. It replaces
the single write-capable update job with read-only fetch and build jobs that
pass one-day immutable artifacts to a final write-capable publish job. The
clean-checkout regression, dynamic candidate validation, publication
confirmation, schedule, master guard, concurrency, format boundaries, and
generated-path boundary remain required. The task introduces no live fetch,
generated-data change, statistics change, public-path change, front-end change,
storage provider, restart behavior, failure issue, commit, remote publication,
or merge. It stops for owner acceptance after local validation.

P10-09 local implementation is complete. The former `update` job is now the
read-only `fetch`, read-only `build`, and write-scoped `publish` sequence; both
job handoffs verify SHA-256 checksums, and the publish archive rejects paths
outside the existing generated-data boundary before extraction. The focused
cross-layer suite passed 84 tests and the complete Python 3.12.7 suite passed
all 654 tests in 407.17 seconds. Repository, Standard rule, public Schema, YAML,
and diff validation also passed. No production workflow was dispatched and no
data, statistic, public path, front-end, Pages setting, storage, or history
changed. The owner accepted the local result on 2026-08-02 and separately
authorized commit, remote publication, pull-request creation, and merge. A real
production-data dispatch and P10-10 remain separately controlled.

The owner authorized P10-10 local implementation on 2026-08-02. It adds only
bounded MTGO fetch-stage restart behavior: a failed collection may retain a
seven-day, same-commit checkpoint of inputs and completed operations; a later
matching fetch run verifies it and repeats only pending work. An incomplete
checkpoint must not reach build or publication. No live fetch, generated data,
statistic, public path, front-end, storage-provider, commit, remote publication,
merge, or failure issue is authorized during local implementation.

P10-10 local implementation is complete. The read-only fetch job now records
only completed format operations, retains a failed collection for seven days,
and accepts a prior checkpoint only after the Action metadata, exact master SHA,
collection plan, baseline, checksums, and archive path boundary all verify. It
continues attempting independent pending operations before failing, but build
and publish receive only a fully successful one-day fetch candidate. The
focused suite passed 18 tests and the complete Python 3.12.13 suite passed all
659 tests in 412.17 seconds; repository, rule, and public Schema validation
also passed. No production workflow was dispatched and no data, statistic,
front-end, public path, Pages setting, storage provider, failure issue, commit,
remote publication, or merge changed. It stops for owner acceptance before any
commit or remote action.

The owner authorized P10-11 local implementation on 2026-08-02. It adds one
deduplicated failure-notification job after MTGO fetch, build, and publication.
Only that job may receive `issues: write`; it must create or update one open
issue per failed stage without copying raw source content or error text. Local
work does not dispatch production, create a real issue, change data or
statistics, alter public paths or front ends, or authorize commit, publication,
or merge.

P10-11 was accepted and published on 2026-08-02 through pull request #150 and
merge commit `bf9749bd5871a65273f62fd379a4be987bd33df2`. Its 19 focused tests,
661-test local suite, pull-request validation, master admission, and Pages
deployment passed. No production workflow was dispatched and no real failure
issue was created during acceptance.

The owner authorized P10-12 local implementation on 2026-08-02. It removes
the manual Melee workflow's hard-coded Modern format and resolves the one
enabled verified event format from the strict whitelist before any candidate
baseline, retained snapshot lookup, or source request. It documents the
unchanged manual event-addition, review-branch, and owner pull-request gates.
P10-12 does not edit the whitelist, activate an event, dispatch a workflow,
contact Melee, generate data, alter statistics or front ends, or authorize
commit, publication, or merge.

Phase 10 closed on 2026-08-02 after owner acceptance of P10-01 through P10-12.
P10-12 was published through pull request #151 and merge commit
`6806a71b2cf3975d6993a3c2465529e028df4665`; its pull-request validation,
master admission, and Pages deployment passed. P11-02 was published through
pull request #154 and merge commit `9ebb99133f7e410681cd2b2a2b8237f07a744586`.
P11-03 was published through pull request #155 and merge commit
`eba8e3a3c6b3b86c0dc756ecd75143b4e2cffab8`. The owner skipped P11-04 after
the measured whole-package coverage path was too slow for required CI. P11-05
was published through pull request #156 and merge commit
`c2e8939967072cc688673b60799323804bc7cb61`. P11-06 was published through
pull request #165 and merge commit
`419c382148dd96ec266a8a9b2abe4975f99235f9`. P11-07 was published through
pull request #166 and merge commit
`feadb7ebe6f06969f5b1bb0ab9b4c09827956315`. P11-08 was published through
pull request #167 and merge commit
`26341162d4d303d179a0bd4f6de156e4ea3fc04b`; pull-request validation,
master admission, and Pages deployment passed. On 2026-08-02 the owner
skipped P11-09 because extracting shared APIs for draw-adjusted compatibility
metrics would invest in logic selected for eventual removal. P11-10 was
published through pull request #169 and merge commit
`c448332b1444b3734bd3fcf5eb37d8f4d1777e9e`; its pull-request validation,
master admission, and Pages deployment passed.

## Acceptance criteria

Phase 10 is complete when:

- future raw snapshots retain no unapproved fields;
- the approved `434455` compatibility manifest remains satisfied;
- generated data no longer enters the code branch through the daily update
  mechanism selected for replacement;
- fetch, build, and publication are independently observable and recoverable;
- CI covers every supported production runtime;
- a controlled failure creates one deduplicated issue with least privilege;
- whitelist operations are format-dynamic and documented;
- no statistical formula changes;
- every owner-gated migration has an explicit recorded decision.

---

# Phase 11 — Engineering baseline, test structure, and documentation reduction

## Objective

Create a maintainable engineering baseline and reduce structural debt without
changing production data, public paths, statistical behavior, or the frozen
`434455` compatibility boundary.

## Required work

- establish standard Python packaging, linting, typing, and coverage controls;
- establish JavaScript, workflow, and real-browser test baselines;
- do not extract the deprecated draw-adjusted compatibility calculation into a
  shared API; retain its current bytes until the Phase 19 contract migration;
- extend repository validation to the current production front end;
- audit and remove legacy entry points only after owner approval and verified
  replacement;
- separate live status from historical evidence without deleting history;
- split oversized modules incrementally under regression protection.

## Task sequence

1. `P11-01` — Add `pyproject.toml`, an installable package, and console scripts
   while retaining compatible root entry points.
2. `P11-02` — Introduce Ruff in a separate mechanical pull request.
3. `P11-03` — Introduce mypy incrementally, beginning with stable shared
   modules and without a global silent baseline.
4. `P11-04` — Record the first coverage baseline and then enforce that coverage
   does not decrease.
5. `P11-05` — Add monthly Dependabot updates for pip and GitHub Actions.
6. `P11-06` — Add `node:test`, matchup-model property tests, and exact Chinese
   and English translation-key parity.
7. `P11-07` — Add actionlint while retaining explicit workflow permission,
   trigger, branch, and publication behavior assertions.
8. `P11-08` — Add a Playwright real-browser baseline for both production
   entries, both languages, Standard, Modern, desktop, and 390px width.
9. `P11-09` — Skipped by owner decision on 2026-08-02. Do not establish a
   shared API around the draw-adjusted compatibility calculation selected for
   removal in Phase 19; retain current production bytes until that migration.
10. `P11-10` — Extend `validate_repository.py` to protect Phase 8 production
    resources, both HTML entries, controllers, and JavaScript syntax.
11. `P11-11` — Audit legacy entry points and produce an owner deletion list.
12. `P11-12` — Delete approved entry points or move approved tools under
    `tools/` only after replacements are verified.
13. `P11-13` — Reduce STATUS, README, and agent-guide duplication while moving
    retained history to `docs/history/`.
14. `P11-14` — Add README, STATUS, and product-catalog fact-consistency checks.
15. `P11-15` — Split `assets/js/phase8/app.js` under E2E protection without a
    framework or deployment build step.

DEC-078 records the retirement route. Phase 11 does not reinterpret, remove,
or regenerate any compatibility field. P11-10 through P11-12 establish and
audit the production and legacy-entry boundaries first. The first Phase 19
compatibility-migration task then removes the draw-adjusted calculation and its
obsolete public contract under an explicit Schema version, generated-data,
`434455`, rollback, and owner-authorization gate. It must not silently assign
the literal method to an old field whose published meaning was draw-adjusted.

P11-11 completed its local audit on 2026-08-03 against `master` commit
`43476a3076127bbae7b6950f8c7da9099ef044d0`. It classified all 26 root Python
files, identified nine active workflow or publication tools to retain, nine
compatibility wrappers with verified package replacements, seven obsolete or
one-off scripts, and one maintained quality validator suitable for relocation
under `tools/`. It also identified the two retained text outputs belonging to
the retired identity-bearing diagnostics. `docs/audits/P11-11.md` contains the
individual evidence, migration conditions, rollback requirement, and owner
decision list. P11-11 deletes or moves nothing. The owner accepted the
recommended list and authorized P11-11 commit and publication on 2026-08-03.
P11-12 was separately authorized on 2026-08-03 and completed the accepted
cleanup list against `master` commit
`fa0409b3ab77177632e656a249ae485755b531ce`. It deletes the nine compatibility
wrappers, seven obsolete one-off scripts, and two retired identity-bearing text
diagnostics approved in P11-11. It moves the frozen Standard aggregate quality
validator to `tools/`, migrates live tests and README commands to installed
commands or package APIs, and preserves the Phase 3 inventory as an explicitly
historical fixture. The nine active root workflow and publication tools remain;
after the first clean-checkout PR run, `validate_repository.py` gained a fast
AST rule requiring `mtgmeta` test subprocesses to declare `PYTHONPATH`. P11-12
changes no workflow, data, statistics, Schema, public path, front-end source,
or protected event `434455` byte. The owner accepted P11-12 and authorized
commit, push, pull-request creation, CI monitoring, and merge on 2026-08-04.
PR #173 merged P11-12 as commit
`83a54fe0907e1c8775b643295fd9e15327e0daf5`; pull-request validation, master
validation, and Pages publication all passed. P11-13 was separately authorized
for local development on 2026-08-04. It reduces live STATUS, README, and agent
guide duplication and preserves the complete pre-split STATUS under
`docs/history/`. It does not implement the P11-14 cross-document fact checker.
The owner accepted the local P11-13 result and authorized commit, push,
pull-request creation, CI monitoring, and merge on 2026-08-04.
PR #174 merged P11-13 as commit
`0a6f7d23021960476026d382605ba76214b5c323`; its pull-request validation,
master validation, and Pages publication passed. P11-14 was separately
authorized for local development on 2026-08-04. It adds deliberate
README/STATUS/catalog contradiction checks to the existing repository validator
without adding a workflow or a separate CI job.
The owner accepted the local P11-14 result and authorized commit, push,
pull-request creation, CI monitoring, and merge on 2026-08-04. PR #176 merged
P11-14 as task commit `7e035d57834368634cdaa126db248603ef0c0699` and
merge commit `ac48566acc8ab76c9ec33533bb3fdbbd37aaa4f4`; pull-request
validation, master validation, and Pages publication all passed. P11-15 was
separately authorized for local development on 2026-08-04 from that published
base. It splits the Phase 8 application renderer into focused classic scripts,
retains direct static loading without a framework or deployment build step,
and changes no public path, data, statistical behavior, or protected event
`434455` byte. The owner accepted the local P11-15 front end and authorized
commit, push, pull-request creation, CI monitoring, and merge on 2026-08-04.
PR #177 merged P11-15 as task commit
`28a7336c5ff888f584ae4229b39bfc710577e0f1` and merge commit
`f90a26721c406e59f5071c79a360a133fbf6920d`; pull-request validation,
master validation, and Pages publication all passed. Phase 11 is therefore
complete. Its accepted skips remain P11-04, where the owner declined the
coverage baseline because measured CI time was unacceptable, and P11-09, where
the owner declined a premature shared API for the draw-adjusted compatibility
calculation scheduled for an explicit Phase 19 migration.

After Phase 11, the owner separately authorized an operational reliability
repair from master commit `922de5dc6ce57c8fe90400f191fdb17d0270fc97`.
The repair gives newly complete MTGO weeks a seven-day provisional window for
safe additive late-event discovery, then seals their Top 8 week and comparison
base. Weekly Pickup deliberately remains timely: it generates immediately and
refreshes unreviewed candidates when the source event list grows. Reviewed
candidates are preserved for explicit re-review. This maintenance task does
not authorize Phase 12.

## Acceptance criteria

Phase 11 is complete when:

- the package and supported commands work without setting `PYTHONPATH`;
- CI includes Python linting, typing, coverage, JavaScript tests, actionlint,
  and a real-browser smoke test;
- live STATUS is approximately 10 KB and all historical evidence remains
  traceable;
- deliberate README, STATUS, and catalog contradictions fail validation;
- no legacy entry point was removed before replacement verification and owner
  approval;
- production data, public paths, statistical behavior, and approved `434455`
  bytes remain unchanged.

---

# Pre-Phase 12 readiness — Planned; not authorized

## Objective

Remove avoidable acceptance and CI friction before Phase 12 changes visible
front-end behavior, while preserving the existing strict committed baseline,
production-data admission boundary, public paths, statistical meaning, and
owner authorization gates.

These are three independent focused tasks. Each task requires separate owner
authorization and one pull request. Completing this planning section does not
authorize any readiness task or Phase 12 implementation.

## Required work

- make expected artifact impact explicit before implementation and present
  human-readable evidence at owner acceptance;
- measure a bounded ordinary-pytest parallelization prototype before retaining
  any CI dependency or workflow change;
- machine-enforce the compact live-status contract and close the deferred
  history-rewrite question with measurable re-evaluation triggers;
- do not weaken byte-level committed-baseline tests, production candidate
  validation, public-product fact checks, or remote publication controls;
- keep Phase 12 front-end work free of generated statistics, production data,
  and public-path changes unless a later task explicitly changes that contract.

## Task sequence

1. `P12-00-A` — Artifact-impact and owner-acceptance protocol
   - add a Gate 1 artifact-impact declaration covering no artifact change,
     internal diagnostics, user-visible UI, statistical JSON structure, and
     public paths;
   - document a lightweight Gate 3 comparison using focused generation or
     rendering plus human-readable `git diff` summaries before the full suite;
   - retain the current strict Gate 4 committed-baseline behavior instead of
     adding a non-failing pytest review mode or an automatic baseline-acceptance
     tool;
   - require Gate 5 acceptance evidence to show the declared impact, relevant
     source or rendered diff, and browser or data verification appropriate to
     that impact;
   - reconcile the Pages workflow description with the accepted production
     publication dispatch behavior recorded by DEC-084.
2. `P12-00-B` — CI feedback-time optimization and governance closeout
   - route strictly allowlisted documentation and user-visible UI changes to
     focused validation regardless of Draft or Ready maturity, while every
     backend, workflow, authoritative-document, statistical, Schema,
     public-path, deletion, rename, unknown, ambiguous, or unreadable change
     retains the complete ordinary pytest, committed-baseline, Schema/rules,
     Ruff, mypy, Node, Playwright, and repository validation path;
   - publish locally completed work Ready by default, keep Draft optional for
     explicitly requested incomplete-work review, and do not trigger an
     identical suite for a state-only Draft/Ready transition;
   - keep one stable aggregate check, preserve exact-merge confirmation on
     `master` only after current declaration, complete file evidence, exact job
     class, base, head, PR, workflow, and pre-merge timing are reproved, and fail
     safe to complete validation for missing, changed, ambiguous, or
     higher-impact evidence;
   - replace mandatory full-document rereading with task-scoped authoritative
     reading, permit bounded authorization batches, and keep ordinary task
     evidence in pull requests and Git while STATUS remains live state only;
   - measure validation-class timing after the split. Do not introduce xdist in
     this task. Re-evaluate ordinary-pytest parallelism only if it remains the
     principal bottleneck; abandon it if measured improvement is below about
     30 percent, test semantics change, ordering dependencies appear, or flaky
     behavior increases.
   - 2026-08-13 follow-up: real runs showed that the accepted split did not
     prevent individual ordinary tests from repeating full production-corpus
     generation, and the exact-merge reader did not support a 165-file PR.
     GOV-04 hardens browser launch failure, changed-file pagination, and the
     ordinary per-call timing boundary without changing product validation.
     The Owner accepted the validated local result on 2026-08-13 and separately
     authorized commit, one Ready pull request, complete CI, and merge after all
     required checks succeed. Production dispatch and P12-10 remain unauthorized.
3. `P12-00-C` — Folded into P12-00-B; no independent prerequisite
   - retain the existing STATUS size and `live_state_only` checks and add the
     missing non-empty `history_policy` assertion in P12-00-B;
   - defer the P10-05 history-rewrite decision until an existing pack-size,
     controlled-clone, valid privacy or legal, or approved public-path
     retirement trigger actually occurs;
   - do not create P12-00-D, P12-00-E, or P12-00-F.

## Acceptance criteria

Pre-Phase 12 readiness is complete when:

- the artifact-impact protocol contains a complete Phase 12 UI example and
  leaves non-review committed-baseline tests byte-strict;
- pull-request maturity and validation class are separated, the conservative
  focused allowlists and complete fail-safe path are enforced for both Draft
  and Ready pull requests, and runtime timing evidence is reserved for P12-01;
- deliberate STATUS growth beyond 16 KiB and missing live-state policy fields
  fail the fast repository check in under five seconds;
- the deferred history-rewrite triggers remain explicit and no Git history,
  tag, branch, or public path is changed; and
- P12-00-A and P12-00-B are accepted and published before P12-01 begins.

---

# Phase 12 — Front-end productization, editorial landing, and visual system

## Objective

Make the existing static MTGO and Tabletop products faster, shareable,
accessible, resilient, and usable across desktop and mobile. Add a curated
MTGO weekly landing view that answers what changed, what the environment looks
like now, and what new decks or technology deserve attention. Establish one
durable visual system and apply it incrementally without changing existing
statistical meaning, mixing MTGO with Tabletop data, or moving established
public entry points.

## Required work

- load large documents only when the selected view needs them;
- make supported product state shareable and recoverable through the URL;
- freeze the Landing product, data, editorial, weekly-lifecycle, and
  compatibility contract before implementing its producer or front end;
- establish an owner-approved visual system before the first broad redesign and
  implement reusable tokens and components before composing the Landing page;
- integrate the existing Weekly Pickup review, publication, known-state, and
  history boundary into the Landing feature section instead of preserving a
  duplicate standalone product or creating a parallel approval system;
- publish structured Landing facts separately from fixed interface translations
  and human editorial copy;
- correct chart semantics and identity presentation without assigning changing
  rank colors as stable archetype identity;
- expose only freshness and completeness facts that each product actually
  provides, without a provisional-week warning;
- improve accessibility, loading, retry, matrix, mobile, image, and metadata
  behavior under semantic and real-browser tests;
- retain the no-framework, classic-script, no-required-build-step GitHub Pages
  deployment.

## Task sequence

1. `P12-01` — View-level lazy loading
   - record the current clean-browser request count, transferred bytes, and
     readable-content timing for representative MTGO and Tabletop overview
     views before changing their loading behavior;
   - do not load matchup, deck-detail, comparison, Pickup, or future Landing
     documents until the selected view needs them;
   - preserve every existing public path, generated byte, and visible behavior.
2. `P12-02` — Shareable URL state
   - cover format, product, range, sort, event, scope, view, language, and a
     stable archetype or deck-detail identity where supported;
   - support reload, history, and `popstate` restoration;
   - reserve a canonical representation for future multi-event selection so
     Phase 13 can persist selected event IDs without putting transient expanded
     table rows into the URL;
   - retain existing URLs and keep transient expanded identity sets out of the
     URL.
3. `P12-03` — Landing product, data, and editorial contract
   - define the Landing as the eventual default MTGO weekly overview inside
     `/index.html`, switching independently between Standard and Modern while
     Tabletop Major Events remains a separate product and data source;
   - preserve the existing default view during P12-11 and P12-12, expose the
     in-progress Landing only through an explicit shareable URL, and reserve
     the bare-entry cutover for P12-16 after complete owner acceptance;
   - freeze one format-scoped, versioned latest-only public document at
     `stats/<format>/mtgo/landing/current.json`, discovered through the product
     catalog, without a public weekly archive or historical-browsing index;
   - define machine-generated structured facts, fixed i18n templates, and
     manually reviewed editorial copy as three separate responsibilities;
   - store Chinese and English editorial fields as localized alternatives, use
     the existing site-wide language control, URL state, and fallback policy to
     select one active language, and never render Chinese and English editorial
     versions together;
   - retain the latest complete natural week and DEC-083 additive provisional
     refresh behavior without presenting provisional or sealed warnings;
   - require current-week, previous-week, and four-week reference populations
     to be classified in one reproducible run with the same rule set; record the
     rule version or digest, and emit no change claim when comparable inputs
     cannot be established;
   - complete P12-03A as an eight-to-twelve-week read-only Standard and Modern
     shadow, then complete P12-03B by recording the owner-selected contract in
     `PROJECT_SCOPE.md`, `STATISTICS_SPEC.md`, `DATA_ARCHITECTURE.md`,
     `DECISIONS.md`, and the P12-03 audit without writing production outputs;
   - include every current parent at or above 3% high-score share in the
     environment list and show current-week, previous-week, and aggregated
     previous-four-week counts and shares; retain `other_classified` and
     `Unknown` as separate residuals;
   - emit `share_move` only for an absolute current-versus-previous-four-week
     movement of at least five percentage points, use a return state for a
     known archetype that rises from no four-week observation to at least 5%,
     retain `exit` for at least 5% to no current observation, and remove the
     redundant public `notable` and statistical `new_entry` concepts;
   - publish a new deck only from an owner-approved one-Top-8 Weekly Pickup
     `new_archetype` item; a returning known archetype is not a new deck;
   - define `build_shift` from one concrete current-week Top 8 deck whose
     maintained subtype has at least eight previous-four-week reference decks
     and whose existing construction-deviation score is at least 20; never
     fall back to the parent identity;
   - reuse the existing Weekly Pickup review workflow for new-technology
     features, generate difference-card suggestions from cards newly present
     or increased against the subtype base, and leave the final four-card
     display to the reviewer;
   - do not reuse the 20-match matchup warning as a 20-deck Landing filter;
   - require future formats to admit Landing and all required MTGO products in
     one public launch; Standard and Modern are explicit Phase 12 migration
     exceptions and must satisfy the same rule at P12-16;
   - define invalid generated Landing data as publication-blocking, while no
     admitted events and no manually approved feature are separate valid empty
     states; external card-image failure remains non-blocking;
   - keep representative key cards manually selected outside classifier rules,
     prefer subtype pairs, use parent fallback only when explicitly allowed,
     and remain text-only instead of guessing when no mapping exists;
   - freeze editorial refresh, empty-state, `mtgo-landing` direct-link, and
     mobile content-floor rules before code begins;
   - block P12-10 until a separately authorized classifier remediation is
     accepted, known-archetype state is validated or migrated, the shadow is
     rerun, the three numeric thresholds are rechecked with the owner, and the
     manual representative-card map is then approved.

   The Owner accepted the R1 stable-identity contract and R2 full-corpus shadow
   audit, then authorized `CLASSIFIER-R3-PRODUCTION-MIGRATION` for local
   implementation only on 2026-08-11. R3 promotes the exact accepted Standard
   and Modern rules through a narrow, fail-closed semantic-feature manifest;
   migrates only the parent-keyed Pickup known state; refreshes the existing
   MTGO and Tabletop classification-derived closure; and freezes R1/R2 baselines
   so the pre-migration evidence remains reproducible. It changes no source
   event, formula, public path, workflow, front end, or product boundary. R3
   acceptance, commit, publication, R4 residual-Unknown review, the Landing
   shadow rerun and threshold confirmation, representative-card approval, and
   P12-10 remain separate gates.

   The Owner accepted the validated local R3 implementation and authorized its
   local commit on 2026-08-11. Publication, R4, and P12-10 remain separately
   unauthorized.

   The Owner separately authorized the non-production
   `CLASSIFIER-R4-RESIDUAL-UNKNOWN-REVIEW` on 2026-08-11. R4 freezes the R3
   Unknown inputs, groups all residual Standard and Modern records into
   transparent de-identified candidate families, and records one explicit
   Owner disposition for each family. Candidate similarity and nearest-rule
   evidence do not assign an archetype. Production-rule promotion, statistics,
   Pickup state, the Landing shadow, commit, publication, and P12-10 remain
   separate gates.

   Modern owner preclassification batches 1 through 4 are implemented and
   Owner-accepted in the non-production R4 shadow. Batch 4 records nine accepted singleton
   dispositions as eight parents, moves the nine remaining current MTGO Modern
   Unknown records to reviewed identities, and moves seven structurally matching
   Dimir Tempo records to Dimir Unearth. All 6,784 current and all 5,792 frozen
   Modern records are classified in this shadow, while all 362 registered
   Tabletop decklists retain their pre-batch identity. On 2026-08-12 the Owner
   accepted the final Modern batch and authorized a one-time local Modern
   closeout commit. The machine-readable closeout freezes all 88 accepted
   Modern dispositions and the exact shadow, generator, queue, workbook,
   production-rule, and protected-event hashes before Standard begins. This is
   review evidence, not production promotion; Standard review and any later
   commit, publication, the Landing shadow, and P12-10 remain separate gates.

   The Owner then completed and accepted all 59 Standard R4 families, including
   all 43 singleton dispositions, and authorized the final local R4 closeout
   commit `b3f379a95284ecbe5da21124a4be651bb346e602` on 2026-08-12. The accepted
   shadows classify all 6,784 current and 5,792 frozen Modern records; classify
   4,732 of 4,733 current Standard records while preserving one explicit
   intentional Unknown; and classify 3,928 of 3,936 frozen Standard records.
   R4 changes no production rule or generated statistic.

   The Owner separately authorized `CLASSIFIER-R5-PRODUCTION-PROMOTION` for
   local implementation on 2026-08-12. R5 promotes only the hash-locked R4
   Modern and Standard shadows, migrates parent-keyed Pickup known state, and
   refreshes the existing MTGO and event 434455 classification-derived closure.
   It freezes the R3 production inputs beneath the R4 audit and changes no
   formula, source event, retained response, public path, workflow, front end,
   or product boundary. R5 acceptance and commit, publication, the Landing
   shadow, threshold reconfirmation, representative-card approval, and P12-10
   remain separate gates.

   On 2026-08-12 the Owner accepted the complete R5 local implementation and
   separately authorized its local commit, reconciliation with the current
   remote `master`, Ready pull request, complete CI, and merge. Manual
   production dispatch, the Landing shadow, threshold reconfirmation,
   representative-card approval, P12-10, and every later task remain separate
   and unauthorized.

   Publication reconciliation then replayed the complete R1-R5 chain onto
   remote `master` commit `f8a4714c07861b104193721524ac5669cef69084`
   without fetching new source data. The refreshed publication baseline has
   6,944 classified Modern decks and zero Unknown; Standard has 4,821
   classified decks and eight non-blocking fail-closed Unknown from 4,829
   records. The accepted frozen-corpus identities remain unchanged, and the
   already indexed W32 Top 8 files are reclassified without changing either
   Top 8 index or any Pickup candidate.

   R5 was published through pull request #201 and merge commit
   `a2b254298508d10431e76531b6a4e029802c9165`; complete pull-request and
   post-merge validation, automatic Pages deployment, byte-level public JSON
   verification, and Owner live acceptance succeeded. The 2026-08-13 subtype
   display-name compatibility fix for nine subtype
   `display_name` values that repeat a parent color prefix. The fix must derive
   the replaceable prefix from the parent's own subtype definitions, preserve
   all stable identities and statistics, leave the other 72 subtype labels
   unchanged, merged as PR #202 before this classifier repair was rebased.

   On 2026-08-13 the Owner authorized
   `STANDARD-SPELLEMENTALS-TALENT-BOUNDARY` fix. The Standard Spellementals rule
   requires an exact mainboard Stormchaser's Talent count of zero while keeping
   Sunderflock zone-neutral, so mainboard Talent/Slickshot builds select Izzet
   Prowess and sideboard-only Talent Spellementals remain unchanged. The exact
   impact is 102 current and 56 frozen transitions from Izzet Spellementals to
   Izzet Prowess with no status-count or other identity change. The accepted
   R4/R5 evidence remains frozen. The Owner then accepted commit, publication,
   and merge; the Landing shadow, P12-10, and production dispatch remain
   separate gates.
4. `P12-04` — Visual direction and durable design-system contract
   - publish the durable repository authority at
     `docs/FRONTEND_DESIGN_SYSTEM.md`, covering product personality,
     typography, color, spacing, density, hierarchy, controls, panels, tables,
     card images, responsive behavior, motion, and accessibility principles;
   - compare the current rendered product with two coherent design directions
     and obtain owner selection before production implementation;
   - treat the selected Landing composition as the reference expression of the
     system while keeping shared tokens suitable for all existing views;
   - do not transmit repository content to an external design service without
     separate owner authorization, and do not change production front-end
     source in this design-contract task.
5. `P12-05` — Shared visual foundation
   - implement the accepted colors, type scale, spacing, focus, elevation,
     panel, control, table, link, and responsive tokens in shared static assets;
   - migrate the shared shell, navigation, format tabs, product tabs, notices,
     and common loading containers first; distinguish top-level products from
     in-page Landing sections and keep the language control visually distinct
     from the format selector;
   - preserve content order, data meaning, URLs, and product availability while
     the remaining views migrate incrementally. Weekly Pickup remains reachable
     through its existing product state until the tested P12-16 cutover.
6. `P12-06` — Correct chart semantics
   - use accurate Chinese product and metric names;
   - replace rank-colored pie charts with aligned comparison graphics that do
     not assign identity color by sorted position;
   - let Landing composition colors express hierarchy or selection, not a
     changing archetype identity, and keep labels and values authoritative.
   - local implementation on 2026-08-08 selected the Landing composition
     contract: current-week archetypes at or above the fixed 3% high-score-share
     threshold remain interactive segments, lower classified share is grouped
     as Other, Unknown and genuine unassigned share stay separate, and Top 8
     metrics remain in the authoritative table;
   - the owner-selected B revision changes only mapped segment fills to the
     first manually maintained representative-card image; tooltips keep only
     deck name and share, with no legend, while desktop click and mobile
     first-tap/second-tap navigation open detail beneath the corresponding row;
   - explicit maintained mana-identity mappings add local W/U/B/R/G/C symbols
     to MTGO parent and subtype names without runtime name inference or changes
     to classifier, statistics, generated data, product name, or public paths;
   - owner acceptance, commit, publication, merge, deployment, and P12-07
     remain separate authorization gates.
7. `P12-07` — Product-specific freshness strip
   - display only dates, coverage, event counts, deck counts, and completeness
     supplied by the active product;
   - display unknown rather than inventing a common metric;
   - keep DEC-083 provisional and sealed lifecycle state internal.
   - local implementation on 2026-08-08 adds one shared, responsive strip
     renderer while keeping the fact selection product-specific: MTGO statistics
     shows its rolling period, updates, deck counts, and publication
     completeness; matchups shows its own coverage and exclusions; Top 8 and
     Weekly Pickup show only their week and available counts; Tabletop shows the
     selected event date, event count, scoped deck count, and submission
     availability;
   - missing source values render as an explicit localized Unknown value rather
     than zero, an empty dash, or a cross-product substitute;
   - responsive verification covers Chinese and English product routes plus
     390- and 412-pixel viewports without taking on the broader list conversion
     reserved for P12-08A;
   - the strip measures its rendered content: it keeps the title and all facts
     on one row when they fit, but moves the complete fact group to a new row
     aligned with the title's left edge as soon as they do not;
   - owner acceptance, commit, publication, merge, deployment, and P12-08 remain
     separate authorization gates.
8. `P12-08` — Readability and accessibility baseline
   - cover contrast, type size, target size, focus, headings, landmarks,
     reduced motion, and unavailable-navigation semantics;
   - establish reusable accessible link or button behavior for future Landing
     stacked-bar segments rather than hiding interactive children in one image
     role;
   - use a 16-pixel body, 14-pixel table/key-label, and 13-pixel secondary-copy
     baseline, with a 24-by-24-pixel interactive-target floor and explicit
     light/dark focus colors;
   - keep proportional composition-segment widths as an essential visualization
     exception only where the accompanying table or card list provides an
     equivalent named control;
   - restore keyboard focus after dynamic rerenders and inline-detail closure,
     label content regions, and expose unavailable-navigation reasons through
     programmatic descriptions;
   - verify all retained product routes in Chinese and English at desktop,
     390-pixel, and 412-pixel widths without taking on the semantic-card list
     conversion reserved for P12-08A;
   - owner acceptance, commit, publication, merge, deployment, and P12-08A
     remain separate authorization gates.

   P12-08 was merged in PR 194 at `f26ae788`. P12-08A received separate local
   implementation authorization on 2026-08-09; commit and publication remain
   separate owner gates.
8A. `P12-08A` — Existing-product small-screen list remediation
   - translate the one-dimensional statistics and Tabletop overview lists into
     semantic cards at 780 CSS pixels and below rather than exposing only the
     first columns of a desktop table;
   - preserve deck identity, core metrics, secondary metrics, and the existing
     expand or deck-detail action without hiding data merely to make the layout
     fit;
   - open detail directly beneath the originating card;
   - provide a mobile sort selector and direction control that reuse the
     existing sort state, URL contract, and history behavior;
   - keep matchup matrices and the Top 8 cross-event comparison in bounded
     horizontal scrollers with a sticky identity column and first-use cue;
   - retain Weekly Pickup's existing card semantics and wrap its secondary
     metric without clipping at narrow widths;
   - verify Chinese and English behavior at 390- and 412-pixel widths plus the
     780/781-pixel boundary, focus restoration, and page-overflow contract;
   - do not begin until P12-08 is accepted and the owner separately authorizes
     P12-08A implementation.

   P12-08A local implementation was owner-accepted on 2026-08-09, with commit,
   remote publication, and merge authorized. P12-09 and any manual production
   dispatch remain separate authorization gates.
9. `P12-09` — Loading, failure, and retry model
   - separate successful caching from background refresh;
   - evict or retry failed promises and add useful text-first skeletons;
   - reserve card-image dimensions so progressive image loading does not move
     already readable content;
   - keep the MTGO shell usable when the Landing document cannot be loaded by
     offering retry and a deterministic route to the first available existing
     product rather than rendering a blank default page;
   - treat Scryfall image or preview unavailability as a bounded placeholder,
     not as a blocker for readable product content;
   - defer below-the-fold card images until they approach the viewport and use
     bounded concurrent image loading so the Landing does not issue an
     uncontrolled burst of third-party requests;
   - lazy-load the Pickup index and a selected historical feature document only
     when the Landing feature section needs them, and isolate their loading,
     empty, failure, and retry states from the current Landing facts.

   Local P12-09 implementation was owner-authorized on 2026-08-09. The current
   review candidate separates bounded successful caches from foreground and
   refresh requests, stages grouped refreshes before an explicit Apply action,
   preserves readable content on scoped failure, and adds bounded progressive
   card images plus a touch-only accessible preview. It also exposes separate
   Pickup index and historical-document loaders for the later Landing consumer
   without adding Landing data or UI. The owner accepted the local result and
   authorized commit, Ready publication, and normal merge on 2026-08-09.
   Production dispatch and P12-10 remain separate gates.
10. `P12-10` — Landing weekly-facts producer and Pickup integration
    - do not start until the P12-03 classifier-remediation gate, refreshed
      shadow, owner threshold confirmation, known-state migration check, and
      representative-card approval are complete;
    - add the Schema-validated latest-only
      `stats/<format>/mtgo/landing/current.json` document under the reviewed
      manifest, catalog, workflow, production-candidate, and Pages-allowlist
      boundaries;
    - generate byte-deterministic structured changes, trends, raw counts,
      selected key-card identities, source event IDs, and the common classifier
      rule version or digest without generated Chinese or English prose;
    - extend the existing format-scoped Weekly Pickup candidates and manual
      publication fields for Landing headlines, positioning copy, and approved
      featured items; do not add parallel root-level candidate configuration;
    - refresh unreviewed provisional-week facts after additive late events,
      preserve reviewed content for explicit re-review, and never auto-publish
      an unreviewed candidate;
    - produce a Schema-valid no-event document and a Schema-valid empty-feature
      list when those are the truthful states; fail publication for malformed,
      internally inconsistent, or missing required Landing output;
    - exclude candidate, review-note, design, and other non-public working files
      from the Pages artifact, and prove that only the admitted current document
      is deployable;
    - preserve every pre-existing statistic, Pickup public document and history
      index, rule, comparison base, and protected `434455` byte. The P12-04B
      product-contract migration authorizes using Pickup as Landing's internal
      feature source, not deleting or rewriting those documents.
11. `P12-11` — Landing weekly summary and environment structure
    - render up to five truthful structured weekly observations without forcing
      a minimum, plus the environment composition strip and high-score-share
      structure list from the same P12-10 document;
    - show every archetype above the owner-approved high-score-share threshold,
      show current, previous-week, and aggregated previous-four-week raw counts
      and high-score shares, display current Top 8 share only as supporting
      information, and do not apply a 20-deck exclusion;
    - make the composition segments and list rows use the same archetype set and
      the P12-02 shareable detail URL;
    - render text before progressively loaded key-card images and provide a
      useful no-event state;
    - keep this view non-default and reachable through its explicit P12-02 URL
      until the complete Landing is accepted in P12-16.
12. `P12-12` — Landing curated new-deck and new-technology panel
    - show every approved item for the selected feature week, with all
      `new_deck` items before all `new_technology` items, category, archetype,
      editorial positioning, four reviewer-selected cards, supporting facts,
      and a shareable full-deck link;
    - place one week selector inside the Landing feature panel, default it to
      the current week, and reuse the existing Pickup index and week documents;
      selecting history changes only this panel and never the current Landing
      brief, environment, composition, or construction-change facts;
    - render only the currently selected language, rerender the same item when
      the existing Chinese or English control changes, and do not introduce a
      side-by-side bilingual Landing mode;
    - reuse the common card-image preview, placeholder, and failure behavior;
    - use one disclosure action per item and the shared deck-detail view; show a
      stable-environment empty state when no item was approved, never expose a
      pending-review state or internal approval vocabulary, and introduce no
      standalone Weekly Pickup front-end state.
13. `P12-13` — Large-matrix interaction
    - add search, focused archetype, Top-N, and minimum-match filters;
    - retain the established 20-match warning and use roving tabindex plus
      directional-key navigation.
14. `P12-14` — Mobile matrix and card-image interaction
    - provide a single-archetype vertical opponent view;
    - add a touch-friendly card image layer and failure placeholder;
    - verify the selected Landing list-image treatment, feature week selector,
      multiple approved items, and shared inline deck detail at 390px without
      hiding required names, values, trends, or navigation.
15. `P12-15` — Metadata and sharing
    - add description, Open Graph, favicon, canonical URL, language memory, and
      required Scryfall and Wizards attribution;
    - provide appropriate Landing metadata without presenting machine facts as
      human editorial claims;
    - define a canonical Landing feature URL and map legacy
      `product=weekly-pickup&week=<week>` state to
      `product=mtgo-landing&section=features&week=<week>`, with the week scoped
      only to the feature panel.
16. `P12-16` — Cross-device and visual-system closeout
    - verify the Landing plus the four retained top-level product views in
      Chinese and English independently, both public MTGO formats, the protected
      Tabletop product, desktop, 390px width, language switching, URL
      restoration, and zero application console errors;
    - after the complete Landing, empty states, failure fallback, direct links,
      and Pages artifact are accepted, make it the bare `/index.html` MTGO
      default while retaining every explicit existing product URL through a
      compatible destination;
    - remove `weekly-pickup` from the product navigation, product order, and
      standalone product identity only after its old URLs have been verified to
      open the Landing feature section at the requested week. Preserve its
      generated history, internal candidate/review capability, known state, and
      rollback path;
    - verify that no future format can be catalog-public without an admitted
      Landing and all required MTGO products, while the Standard and Modern
      migration exceptions both satisfy this invariant at closeout;
    - compare request count, transferred bytes, readable-content timing, image
      request behavior, and layout stability with the P12-01 baseline; stop for
      review on an unexplained material regression rather than inventing an
      arbitrary pre-measurement limit;
    - keep the default-product selection independently reversible and exercise
      a local rollback that restores the prior statistics default without
      deleting the Landing document or changing any explicit public URL;
    - audit every migrated view against the accepted visual-system contract and
      record any intentionally deferred component rather than silently leaving
      a second visual language.

This phase does not authorize changing the existing 20-match warning,
migrating the Tabletop null threshold into generated data, merging MTGO and
Tabletop statistics, claiming statistical significance from interval overlap,
automatically publishing editorial candidates, presenting the DEC-083 internal
week lifecycle as a user warning, or changing an established generated path.
The only new public-data boundary is the format-scoped Landing product after
separate P12-03 contract acceptance and P12-10 implementation authorization.
Phase 12 publishes only the latest Landing document; it does not authorize
historical Landing browsing or cross-classification-version trend analysis.
Selecting an approved historical Pickup week inside the feature section is a
bounded archive view and does not change that rule.

## Acceptance criteria

Phase 12 is complete when:

- overview views avoid unnecessary large-document requests;
- supported state survives sharing, reload, back, and forward navigation;
- the selected visual system governs the Landing, shared shell, and every
  migrated existing view without a required framework or build step;
- the Landing answers what changed, what the current environment looks like,
  and what new decks or technology were manually selected, using one
  format-scoped structured source;
- the bare MTGO entry changes to the Landing only in P12-16 after complete
  acceptance, while existing explicit product links remain compatible and old
  Weekly Pickup links resolve to the corresponding Landing feature week;
- machine facts, fixed translations, and human editorial copy remain separate,
  and no unreviewed candidate reaches the public product;
- no 20-deck filter or unsupported statistical-significance claim is introduced;
- chart names, order, and colors do not imply false equivalence or changing
  identity;
- keyboard and mobile users can operate Landing links and inspect large
  matrices without traversing thousands of tab stops;
- failure states can retry safely and progressive images do not block readable
  content or shift established layout;
- weekly comparisons use one recorded classifier rule version, and unavailable
  comparability produces no false environment-change claim;
- real-browser acceptance passes across the required products, formats,
  languages, and viewport sizes, with exactly one selected language rendered at
  a time;
- the Pages artifact contains the admitted latest Landing document but no
  candidate, review, design, or other working file;
- measured loading behavior has no unexplained material regression, and the
  bare-entry Landing cutover has a verified reversible default-state rollback;
- all pre-existing public JSON paths, statistical formulas, and protected
  `434455` bytes remain unchanged, while the new Landing documents pass their
  versioned Schema and production-publication boundaries.

---

# Phase 13 — Multi-event raw-count matchup aggregation

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

# Historical Phase 12 — Whitelist operations and Melee automation

Status: `partially_implemented_remaining_work_moved_to_phase_10`

This historical specification is retained so that completed and remaining
operational requirements are not lost. Phases 5, 7, 8, and 9 implemented the
whitelist, controlled ingestion, quality, publication, and resumable collection
foundations. The remaining format-dynamic workflow and non-programmer operation
work is assigned to current Phase 10.

## Objective

Create a controlled workflow for adding and refreshing approved events.

## Required operational commands

Document and implement commands for:

- whitelist validation;
- event fetch;
- event normalization;
- data-quality reporting;
- deck classification;
- statistics generation;
- schema validation;
- event catalog generation.

## Proposed workflow

Create:

- `.github/workflows/fetch_melee.yml`

During initial operation, use manual dispatch rather than unrestricted automatic discovery.

## Required workflow sequence

The workflow should:

1. validate the event ID against the whitelist;
2. confirm that the event is enabled;
3. fetch raw data;
4. normalize event data;
5. generate quality reports;
6. classify decklists;
7. generate per-event statistics;
8. validate generated JSON;
9. run tests;
10. write a workflow summary;
11. publish only through a reviewable change.

## Workflow safety

The workflow must have:

- explicit permissions;
- explicit concurrency;
- event-specific logs;
- failure before publication when quality checks fail;
- protection against overwriting valid data with incomplete fetches.

## Acceptance criteria

Phase 12 is complete when:

- unlisted events are rejected;
- disabled events are rejected;
- excluded event types cannot be enabled accidentally;
- fetch failures do not overwrite valid existing data;
- quality failures prevent publication;
- permissions are least-privilege;
- concurrency is explicit;
- event addition is documented for non-programmers.

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

# Historical Phase 18 — Cleanup, operations, and release

Status: `split_across_phases_10_11_and_19`

This historical specification is retained so that no cleanup, operations, or
release requirement is dropped. Data and workflow operations move to current
Phase 10, engineering and documentation cleanup moves to current Phase 11, and
final release readiness moves to current Phase 19.

## Objective

Remove obsolete compatibility code only after replacements are verified, then document long-term maintenance and release procedures.

## Required cleanup

Review:

- obsolete root-level scripts;
- temporary compatibility wrappers;
- duplicate workflows;
- unused generated files;
- Python cache files;
- `.gitignore`;
- old documentation;
- obsolete public paths;
- repository data volume.

Do not delete a legacy entry point until:

- its replacement is verified;
- workflows use the replacement;
- tests cover the replacement;
- documentation uses the replacement;
- rollback is possible.

## Required operations documentation

Document:

- MTGO data refresh;
- Melee event addition;
- Melee event refresh;
- whitelist maintenance;
- classification-rule maintenance;
- Unknown-deck review;
- conflict resolution;
- quality-report review;
- schema migration;
- GitHub Actions operation;
- GitHub Pages deployment;
- rollback;
- release verification.

## Acceptance criteria

Phase 18 is complete when:

- obsolete code is removed safely;
- compatibility decisions are documented;
- README reflects actual commands and paths;
- operations can be performed from written instructions;
- all tests pass;
- all required schemas validate;
- production pages work;
- workflows use explicit permissions and concurrency;
- a release tag is created;
- `docs/STATUS.yaml` records the released state.

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

# Phase completion procedure

At the end of every phase:

1. Run all tests required by the phase.
2. Run rule validation where applicable.
3. Run schema validation where applicable.
4. Verify that current production behavior is not unintentionally broken.
5. Review Unknown and conflict reports.
6. Review data-quality reports.
7. Update `docs/STATUS.yaml`.
8. Update `docs/ROADMAP.md` if phase status or order changed.
9. Add a record to `docs/DECISIONS.md` when a scope or statistical decision changed.
10. Update schemas when data structures changed.
11. Update tests when statistical behavior changed.
12. Update README when commands or operations changed.
13. Review the Git diff.
14. Commit with a focused commit message.
15. Push the branch.
16. Open or update a Pull Request.
17. Wait for review and user confirmation before beginning the next phase.

---

# Change-control rules

Changes to the following require explicit project-owner confirmation:

- merging MTGO and Melee statistics;
- adding an event category outside the whitelist policy;
- enabling automatic Melee-wide event discovery;
- including team events;
- including pure Limited events;
- changing intentional-draw handling;
- changing bye handling;
- treating awarded wins as played wins;
- including Draft results in Constructed statistics;
- using playoffs as the primary performance sample;
- changing the approved format-development order;
- introducing a mandatory front-end framework or build system;
- breaking existing public JSON paths;
- removing legacy entry points before replacement verification;
- enabling Vintage before the Vintage decision gate.

When such a decision is approved:

- update `docs/DECISIONS.md`;
- update the relevant specification;
- update tests;
- update schemas if needed;
- update `docs/STATUS.yaml`.

---

# Current approved next action

The current approved task is defined in `docs/STATUS.yaml`.

Before beginning work:

1. confirm `current_phase`;
2. confirm `next_approved_task`;
3. confirm the current working branch;
4. review `prohibited_next_actions`;
5. stop and request project-owner confirmation if the requested work does not match the recorded next task.

Do not infer the current task from examples, historical notes, completed pull requests, or the static phase descriptions in this roadmap.
