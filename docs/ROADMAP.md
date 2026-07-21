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
8. `P5-08` — run reduced-fixture end-to-end validation and, only with separate authorization, validate a live fetch of the reference event.

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

P5-03 local implementation adds a bounded Melee raw-response client and immutable snapshot archive. Whitelist Schema 2.0.0 requires explicit typed `raw_requests`; the client rejects redirects and out-of-bound URLs, defaults its CLI to dry run, uses bounded retry and pagination, streams responses within per-response and per-snapshot limits, preserves safe response metadata, validates archive manifests against a dedicated Schema, and publishes only complete snapshots. The reference event `434455` remains disabled, so this implementation made no live Melee request and produced no real raw archive. Parsing, normalization, classification, statistics, and front-end work remain outside this task. Publication and P5-04 remain separately controlled.

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

## Acceptance criteria

Phase 6 is complete when:

- Modern rules pass validation;
- known Modern fixtures classify correctly;
- rule conflicts are reviewable;
- Unknown decks are reviewable;
- Modern output is separate from Standard output;
- MTGO Modern can be regenerated;
- Standard output remains compatible;
- the MTGO front end can select Modern without hardcoded Standard-only behavior.

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

# Phase 8 — Tabletop Major Events front end

## Objective

Create the separate event-based front end for approved tabletop events.

## Target page

Create:

- `melee/index.html`

The directory name may remain `melee` as an internal implementation path, but the visible product name should be:

- Tabletop Major Events

## Top-level navigation

Use:

- MTGO Environment Trends
- Tabletop Major Events

Do not present the entire second product only as “Melee.”

## Event behavior

The front end must support:

- format selection;
- event selection;
- latest enabled event as the default for each format;
- event-specific overview;
- event-specific matchup matrix;
- visible data-quality warnings;
- links or references to the source event;
- separate MTGO and tabletop navigation.

## Page A: event overview

Page A is calculated per event only.

It may show, depending on event type:

- archetype;
- deck count;
- initial metagame share;
- average points per theoretical round;
- high-score count;
- high-score-region share;
- high-score conversion;
- Day 2 count;
- Day 2 share;
- Day 2 conversion;
- Day 1 win rate;
- Day 2 win rate;
- all-Constructed Swiss win rate;
- sample size;
- quality warnings.

## Page B: matchup matrix

Page B must support:

- a single-event matrix;
- optional aggregation of approved same-format events;
- visible matchup scope;
- W-L-D counts;
- valid match count;
- win rate;
- confidence interval where specified;
- low-sample warnings.

## Acceptance criteria

Phase 8 is complete when:

- the approved Modern Pro Tour is viewable independently from MTGO Modern;
- the event overview loads per-event JSON;
- the matchup matrix loads event-specific JSON;
- data-quality warnings are visible;
- the latest event behavior is configuration-driven;
- the MTGO page remains operational;
- no MTGO and Melee statistics are merged.

---

# Phase 9 — Pure Constructed event strategies

## Objective

Complete statistical support for both pure Constructed event structures.

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

## Acceptance criteria

Phase 9 is complete when:

- event structure is selected explicitly from configuration;
- the two structures use separate strategies;
- theoretical-round denominators follow the statistics specification;
- drop handling follows the statistics specification;
- high-score thresholds are deterministic;
- tests cover both structures;
- front-end labels clearly indicate which structure is being displayed.

---

# Phase 10 — Mixed Draft and Constructed events

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

# Phase 11 — Multi-event matchup aggregation

## Objective

Allow matchup matrices to combine selected events without merging unrelated overview statistics.

## Aggregation eligibility

Only combine events that:

- use the same Constructed format;
- use compatible archetype IDs;
- pass schema validation;
- pass required quality checks;
- are explicitly selected;
- expose the requested matchup scope.

## Aggregation method

Aggregate raw counts:

- wins;
- losses;
- played draws;
- valid matches.

Do not average already calculated percentages.

## Default exclusions

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

## Scope behavior

The matrix must identify whether it uses:

- all Constructed Swiss;
- Day 1 Constructed only;
- Day 2 Constructed only.

For mixed events, the default may be all Constructed Swiss, but Day 1 and Day 2 scopes must remain available where data permits.

## Acceptance criteria

Phase 11 is complete when:

- single-event and multi-event matrices reconcile from raw counts;
- cross-format selection is impossible;
- incompatible schema versions are rejected or migrated;
- sample size is displayed;
- low-sample warnings are displayed;
- confidence intervals are generated where specified;
- scope selection is visible;
- overview metrics remain per-event rather than merged.

---

# Phase 12 — Whitelist operations and Melee automation

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

# Phase 13 — Pauper and Paupergeddon

## Objective

Add Pauper to both product tracks after the Modern reference path and reusable event strategies are stable.

## Required sequence

1. Add Pauper archetype rules.
2. Add Pauper rule fixtures.
3. Validate Pauper rule IDs and priorities.
4. Run Pauper MTGO classification.
5. Generate Pauper MTGO statistics.
6. Validate Pauper MTGO output.
7. Register the approved Paupergeddon main event.
8. Normalize and validate that event as `constructed_day2`.
9. Generate event-specific Pauper statistics.
10. Enable Pauper in both front ends.

## Acceptance criteria

Phase 13 is complete when:

- shared Pauper archetype IDs are used by both sources;
- MTGO and Melee data remain separate;
- MTGO and Melee statistics remain separate;
- Pauper rules pass validation;
- Standard and Modern regression tests pass;
- front-end format selection is catalog-driven;
- quality reports are available.

---

# Phase 14 — Pioneer

## Objective

Add Pioneer using the established shared-classifier and dual-product process.

## Required sequence

1. Add Pioneer archetype rules.
2. Add Pioneer fixtures.
3. Validate rule IDs and priorities.
4. Add Pioneer MTGO processing.
5. Validate Pioneer MTGO statistics.
6. Register an approved Pioneer Melee event.
7. Normalize and validate the event.
8. Generate event-specific Pioneer statistics.
9. Enable Pioneer in both front ends.

## Acceptance criteria

Phase 14 is complete when:

- Pioneer uses the generalized MTGO pipeline;
- Pioneer uses the shared classifier;
- MTGO and Melee remain separate;
- no copied Standard-only pipeline is introduced;
- rules, tests, schemas, and catalogs are updated;
- prior-format regression tests pass.

---

# Phase 15 — Legacy

## Objective

Add Legacy using the established process, including approved Eternal Weekend Legacy main events.

## Required sequence

1. Add Legacy archetype rules.
2. Add Legacy fixtures.
3. Validate rule IDs and priorities.
4. Add Legacy MTGO processing.
5. Validate Legacy MTGO statistics.
6. Register an Eternal Weekend Legacy main event.
7. Normalize and validate the event.
8. Generate event-specific Legacy statistics.
9. Enable Legacy in both front ends.

## Event restrictions

Only approved Eternal Weekend main events may be included under this policy.

Do not include:

- side events;
- trials;
- qualifiers;
- team events;
- unrelated Legacy events not present in the whitelist.

## Acceptance criteria

Phase 15 is complete when:

- only the approved main event is included;
- side events remain excluded;
- shared Legacy archetype IDs are stable;
- MTGO and Melee remain separate;
- prior-format regressions pass;
- front-end catalogs are updated.

---

# Phase 16 — Standard tabletop events

## Objective

Enable qualifying Standard tabletop events after the Melee pipeline is stable.

## Requirements

Only Standard events matching the approved event policy may be added.

Standard MTGO and Standard Melee must remain separate in:

- raw data;
- normalized data;
- generated statistics;
- catalogs;
- front-end presentation.

Qualifying mixed-format Standard events must use the mixed-event strategy.

## Acceptance criteria

Phase 16 is complete when:

- Standard tabletop events use the shared Standard classifier;
- no MTGO and Melee statistics are merged;
- mixed-format rules are applied where required;
- current Standard MTGO behavior remains compatible;
- data quality and source metadata are visible.

---

# Phase 17 — Vintage decision gate

## Objective

Decide whether Vintage support should be implemented.

## Required decision inputs

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

## Possible outcomes

The project owner may:

1. approve Vintage and implement it using the established process;
2. defer Vintage with a documented reason;
3. reject Vintage from the current scope.

## Acceptance criteria

Phase 17 is complete when:

- the decision is recorded in `docs/DECISIONS.md`;
- `docs/PROJECT_SCOPE.md` is updated;
- `docs/STATUS.yaml` is updated;
- the roadmap is updated if implementation phases change;
- Vintage is not enabled before the decision is recorded.

---

# Phase 18 — Cleanup, operations, and release

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
