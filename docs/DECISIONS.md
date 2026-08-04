# Project Decisions

## Document purpose

This document records confirmed product, statistical, architectural, and operational decisions for the `mtgo-data` repository.

It exists to prevent AI assistants, coding agents, and human developers from silently changing established scope or statistical meaning.

This document records decisions, not implementation progress.

Current implementation progress belongs in `docs/STATUS.yaml`.

Development order belongs in `docs/ROADMAP.md`.

Detailed formulas belong in `docs/STATISTICS_SPEC.md`.

Detailed file paths and data structures belong in `docs/DATA_ARCHITECTURE.md`.

---

## Decision status values

Each decision uses one of these status values:

- `Accepted`: approved and currently authoritative.
- `Proposed`: documented but not yet approved.
- `Deferred`: intentionally postponed.
- `Superseded`: replaced by a later decision.
- `Rejected`: considered and not adopted.

An `Accepted` decision must not be changed silently.

To change an accepted decision:

1. add a new decision entry;
2. identify the decision it supersedes;
3. explain the reason;
4. obtain project-owner approval;
5. update affected specifications;
6. update tests and schemas where applicable;
7. update `docs/STATUS.yaml`.

---

# DEC-001 — Separate MTGO and tabletop products

Status: `Accepted`

## Context

The project began as a Standard-only MTGO statistics page.

The expanded project will also process selected tabletop tournament data obtained from Melee.

MTGO events and tabletop events have different population structures, event formats, data sources, and statistical limitations.

## Decision

The project will have two separate product areas:

1. MTGO Environment Trends
2. Tabletop Major Events

MTGO and Melee may share reusable code, but they must keep separate:

- source data;
- normalized event data;
- generated statistics;
- catalogs;
- front-end product behavior.

MTGO and Melee results must not be merged into one metagame statistic.

## Consequences

Users may compare the products visually, but the project must not imply that their populations are statistically interchangeable.

Internal paths may use the name `melee`, but the user-facing product name should be “Tabletop Major Events.”

---

# DEC-002 — Share classification logic across data sources

Status: `Accepted`

## Context

MTGO and Melee decklists may represent the same Constructed archetypes even though their event and match data structures differ.

Maintaining separate archetype definitions for each source would create inconsistent naming and duplicated work.

## Decision

MTGO and Melee will share format-specific archetype definitions and reusable classification logic.

Shared capabilities may include:

- card-name normalization;
- deck normalization;
- archetype IDs;
- rule IDs;
- explicit priorities;
- rule loading;
- full-match evaluation;
- conflict detection;
- Unknown reporting;
- common statistical utilities.

Source ingestion and source-specific statistics will remain separate.

## Consequences

A Pauper archetype should use the same stable archetype ID in MTGO and Melee output.

A source-specific parser must not be placed inside the shared classifier.

---

# DEC-003 — Use stable IDs and explicit priorities in classification rules

Status: `Accepted`

## Context

Rule order alone is not a safe or maintainable way to resolve multiple matching archetypes.

AI-generated changes may reorder YAML content and accidentally change classification results.

## Decision

Every archetype must have:

- a stable machine-readable ID;
- a display name;
- an explicit priority.

Every classification rule must have a stable rule ID.

The classifier must evaluate all relevant matches before selecting a result.

Equal-priority conflicts must be reported rather than silently resolved.

Overridden lower-priority matches should remain available in diagnostic output.

## Consequences

Rule validation and conflict tests are required.

Changing a stable ID requires an explicit migration plan because generated statistics and front-end references may depend on it.

---

# DEC-004 — Use a manual Melee event whitelist

Status: `Accepted`

## Context

The project is intended to analyze selected large-scale Constructed tournaments, not every event hosted by Melee.

Automatic site-wide event discovery would create scope, data-quality, and maintenance problems.

## Decision

Only events explicitly registered in `configs/melee_events.yaml` may be fetched and published.

The whitelist may be updated manually.

Initial Melee automation should use an event ID supplied through a controlled workflow.

Unlisted or disabled events must be rejected.

## Consequences

The project does not need an unrestricted Melee crawler.

Automatic discovery may be reconsidered only through a new approved decision.

---

# DEC-005 — Limit tabletop events to approved categories

Status: `Accepted`

## Context

Many events on Melee are local, Limited, team-based, side events, or otherwise outside the product’s purpose.

## Decision

Target event categories are:

- World Championships;
- Pro Tours;
- Regional Championships;
- Magic Spotlight Series;
- Paupergeddon main events;
- Eternal Weekend Legacy main events;
- Eternal Weekend Vintage main events if Vintage is approved later.

Exclude:

- team events;
- pure Limited events;
- side events;
- unrelated local events;
- unapproved qualifiers;
- events not present in the whitelist.

Mixed Draft and Constructed events are allowed only when their Constructed rounds can be identified reliably.

## Consequences

An event name alone is not sufficient for inclusion.

Whitelist entries must contain enough metadata to verify event type, format, and included phases.

---

# DEC-006 — Use three Melee event structures

Status: `Accepted`

## Context

A single statistical strategy cannot correctly represent every tabletop event.

Pure Constructed events with Day 2, pure Constructed single-stage events, and mixed Draft plus Constructed events require different handling.

## Decision

Every enabled Melee event must use one of these structures:

- `constructed_day2`
- `constructed_single_stage`
- `mixed`

The selected structure must be explicit in event configuration.

## Consequences

Statistics must dispatch through an event-structure strategy.

The code must not infer and silently change structure only from final standings.

Any automatic structure detection must be treated as validation assistance rather than the final authority.

---

# DEC-007 — Use Day 2 data for pure Constructed events when available

Status: `Accepted`

## Context

In a pure Constructed event, Day 2 qualification is based on Constructed tournament performance and provides useful conversion information.

When no Day 2 exists, the product still needs a way to describe stronger-performing decks.

## Decision

For pure Constructed events with Day 2, provide:

- initial field count and share;
- Day 2 count and share;
- Day 2 conversion;
- average performance;
- played-match win rate.

For pure Constructed events without Day 2, use the approved high-score-region logic and provide:

- high-score count;
- high-score-region share;
- conversion from the initial field to the high-score region;
- average performance;
- played-match win rate.

## Consequences

High-score-region conversion is not a substitute for Day 2 conversion when a meaningful pure Constructed Day 2 exists.

The front end must label the two metrics differently.

---

# DEC-008 — Exclude Draft performance from Constructed deck statistics

Status: `Accepted`

## Context

In a mixed event such as a Pro Tour, a player’s total standing and Day 2 qualification may be influenced by both Draft and Constructed performance.

Using total standings points would attribute Draft performance to the player’s Constructed deck.

## Decision

Draft rounds must not contribute to Constructed deck-performance statistics.

Every round in a mixed event must be labeled as:

- Draft;
- Constructed;
- playoff;
- unknown.

Unknown rounds must be reported and excluded until reviewed.

Overall standings points must not be used as Constructed deck points.

## Consequences

Mixed events require round-level data.

A standings-only data source is insufficient for the intended Constructed performance analysis.

---

# DEC-009 — Treat Day 1, Day 2, and combined Constructed scopes separately

Status: `Accepted`

## Context

Day 1 represents a broader initial field but may contain early drops.

Day 2 adds real Constructed matches and increases sample size, but participants are selected partly by prior tournament performance.

In mixed events, that selection may include Draft performance.

## Decision

Where data permits, generate separate scopes for:

- Day 1 Constructed;
- Day 2 Constructed;
- all Constructed Swiss rounds.

Day 1 Constructed describes the broad initial field.

Day 2 Constructed describes the qualified field and must include a selection-bias warning.

All Constructed Swiss may combine real Day 1 and Day 2 Constructed Swiss matches, but it must be labeled clearly and must not be described as an unbiased estimate of the initial population.

## Consequences

The project must retain phase information for every match.

A combined result must be reconstructable from Day 1 and Day 2 raw counts.

---

# DEC-010 — Default matchup behavior for mixed events

Status: `Accepted`

## Context

Day 1 matchup data is closer to the initial field but may have smaller samples because of drops.

Adding Day 2 uses more real Constructed matches but gives extra weight to qualified players and decks.

Neither scope is free from bias.

## Decision

For mixed events:

- the primary matchup interface may default to all Constructed Swiss rounds;
- users must be able to select Day 1 Constructed only;
- users should be able to select Day 2 Constructed only when the sample exists;
- the selected scope must always be visible.

The event overview should show Day 1 and all-Constructed win rates together where practical.

Significant phase differences should produce a warning when sample-size requirements are met.

## Consequences

The product must preserve raw W-L-D counts by phase.

The interface must not show one unlabeled matchup matrix for a mixed event.

---

# DEC-011 — Use theoretical rounds for average-point metrics

Status: `Accepted`

## Context

Using only rounds actually played can make early drops appear less harmful.

For example, a player who starts 0-2 and drops should not receive the same denominator treatment as a player who completes the scheduled Constructed phase.

The metric is intended to describe deck-level point acquisition across the scheduled opportunity.

## Decision

Average-point metrics use total applicable points divided by total applicable theoretical Constructed rounds.

Unplayed scheduled rounds after an ordinary drop contribute zero points and remain in the denominator.

The exact theoretical-round scope depends on:

- event structure;
- day or phase;
- Constructed round schedule;
- confirmed official exemptions.

Played-match win rate remains a separate metric and uses actual valid played matches.

## Consequences

Average points and played-match win rate must not be treated as interchangeable.

The normalized event model must preserve enough information to distinguish drops, exemptions, and played matches.

---

# DEC-012 — Exclude intentional draws from win rate and matchup matrices

Status: `Accepted`

## Context

An intentional draw reported as `0-0-3` is an agreed tournament result and does not represent a played matchup.

It still contributes standings points.

## Decision

For an intentional draw reported as `0-0-3`:

- award the applicable standings point for point-based metrics;
- include the scheduled round in the theoretical-round denominator;
- exclude the result from played-match win rate;
- exclude the result from matchup matrices;
- record the intentional-draw count separately.

A normal played draw is different and may count as half a win in played-match win-rate calculations.

## Consequences

The parser must distinguish intentional draws from played draws.

If the distinction cannot be determined, the result must be reported rather than silently assumed.

---

# DEC-013 — Exclude byes from played-match statistics

Status: `Accepted`

## Context

A bye may award tournament points but no opponent was played.

## Decision

A normal bye:

- may contribute its awarded points to point-based metrics;
- remains part of the applicable scheduled-round opportunity unless another rule applies;
- does not count in played-match win rate;
- does not count in matchup matrices;
- must be recorded separately.

## Consequences

Points and match records cannot be reconstructed correctly from one undifferentiated win count.

The normalized model must distinguish byes from played wins.

---

# DEC-014 — Handle drops as zero-point scheduled opportunities

Status: `Accepted`

## Context

Early drops are not random and can bias statistics.

Ignoring unplayed rounds may overstate the average-point performance of archetypes with unsuccessful early records.

## Decision

For average points per theoretical Constructed round:

- ordinary unplayed rounds after a drop contribute zero points;
- ordinary unplayed rounds remain in the theoretical-round denominator.

For played-match win rate:

- only valid real matches count;
- unplayed rounds do not count as losses;
- completion and drop rates must be reported separately.

## Consequences

The project must show both point-acquisition metrics and played-match metrics.

Quality output should include drop and completion information by event and, where useful, by archetype.

---

# DEC-015 — Treat official Top 8 lock wins separately

Status: `Accepted`

## Context

Some premier events stop requiring real Swiss matches after a player has officially locked Top 8.

The event system may display an awarded win even though no match was played.

Treating that result as a real win would inflate points, win rate, and matchup statistics.

## Decision

An official awarded win after a confirmed Top 8 lock:

- does not count as a played win;
- does not count in played-match win rate;
- does not count in matchup matrices;
- does not count as earned Constructed match points;
- must be recorded separately.

The affected round may be removed from the player’s effective theoretical-round denominator when the official event structure confirms that the player was no longer required to play.

## Consequences

Awarded wins must not be stored as ordinary wins.

Event configuration or verified event metadata must identify official Top 8 lock behavior.

---

# DEC-016 — Do not use Day 2 average alone

Status: `Accepted`

## Context

Day 2 average performance is useful, but it can be misleading when shown without sample size, played-match information, selection context, and awarded-win handling.

## Decision

Day 2 performance must not be represented by a single average value.

Where data permits, Day 2 archetype output should include:

- player count;
- field share;
- average Constructed points;
- effective theoretical rounds;
- valid played-match count;
- played-match win rate;
- high-score count or score distribution where meaningful;
- intentional-draw count;
- bye count;
- awarded-win count;
- Top 8 lock count;
- sample-size warning;
- selection-bias warning.

## Consequences

The front end may summarize these fields, but it must retain access to the supporting counts.

Low-sample Day 2 results must be labeled clearly.

---

# DEC-017 — Exclude playoffs from primary performance statistics

Status: `Accepted`

## Context

Quarterfinals and later playoff rounds have very small, highly selected samples.

A single elimination match is not a reliable primary measure of broad archetype performance.

## Decision

Playoffs are excluded from:

- primary Swiss average-point metrics;
- primary played-match win rate;
- primary matchup matrices;
- high-score-region calculations.

Playoff results may be shown separately as contextual event results.

Final placements may also be displayed as context.

## Consequences

The normalized event model must label playoff rounds explicitly.

The interface must not combine playoff and Swiss results without clear, separately approved behavior.

---

# DEC-018 — Aggregate multi-event matchups from raw counts

Status: `Accepted`

## Context

Combining already calculated percentages can weight small and large events incorrectly.

Overview metrics such as Day 2 conversion also depend on event structure and should not be merged casually.

## Decision

Multi-event aggregation is initially limited to matchup data for compatible events of the same format.

Aggregate raw:

- wins;
- losses;
- played draws;
- valid match counts.

Do not average precomputed win-rate percentages.

Per-event overview statistics remain per-event.

## Consequences

Combined matrices require compatible archetype IDs, scopes, and schema versions.

Cross-format aggregation is prohibited.

---

# DEC-019 — Preserve the current Standard implementation as the baseline

Status: `Accepted`

## Context

The current repository has a working Standard MTGO page and generated outputs.

Large refactoring without regression protection could silently change classification or public output.

## Decision

Standard remains the regression baseline.

Before replacing Standard-only internals:

- record representative fixtures;
- record public output paths;
- add tests;
- create a recoverable baseline;
- preserve temporary compatibility entry points.

## Consequences

Refactoring must be incremental.

Legacy scripts may remain temporarily even if the final architecture uses `src/mtgmeta/`.

---

# DEC-020 — Split the current front end before major expansion

Status: `Accepted`

## Context

The current `index.html` contains a large amount of HTML, CSS, and JavaScript in one file.

Adding formats and a second product without first separating responsibilities would make maintenance harder.

## Decision

Before major multi-format front-end expansion, split the existing MTGO front end into:

- a smaller `index.html`;
- shared CSS under `assets/css/`;
- JavaScript under `assets/js/`.

The first split must preserve current behavior and GitHub Pages compatibility.

Do not introduce a mandatory framework, bundler, or build step unless separately approved.

## Consequences

Front-end splitting is an engineering-preservation phase, not a visual redesign phase.

Melee-specific product logic belongs in the separate tabletop front end.

---

# DEC-021 — Use a separate tabletop front end

Status: `Accepted`

## Context

MTGO is organized around time ranges and environment trends.

Melee is organized around individual major events.

Trying to place both products into one page would blur their different statistical meanings.

## Decision

Use:

- `/index.html` for MTGO Environment Trends;
- `/melee/index.html` for Tabletop Major Events.

Each tabletop event has an event-specific page state.

Each format defaults to its latest enabled event.

## Consequences

Navigation should connect the two products while preserving separate data loading and statistical behavior.

---

# DEC-022 — Use shared format development order

Status: `Superseded by DEC-034`

## Context

The existing implementation supports only Standard MTGO.

The project also needs additional MTGO formats and corresponding tabletop formats using shared classification rules.

## Decision

Use this development order:

1. protect Standard;
2. generalize the MTGO pipeline;
3. implement Pauper MTGO;
4. implement Paupergeddon;
5. implement Modern;
6. implement Pioneer;
7. implement Legacy;
8. enable qualifying Standard tabletop events;
9. decide Vintage later.

## Consequences

A later format should reuse the established pipeline rather than create a separate copied implementation.

The roadmap may be changed only with explicit project-owner confirmation.

---

# DEC-023 — Defer Vintage until a decision gate

Status: `Accepted`

## Context

Vintage has lower event volume and may require additional classification and maintenance work.

The quality and value of available MTGO and Eternal Weekend data must be reviewed first.

## Decision

Vintage is not currently enabled.

A later decision gate will review:

- data availability;
- decklist completeness;
- matchup completeness;
- maintenance cost;
- expected user value;
- front-end impact;
- automation impact.

## Consequences

Vintage rule placeholders may be discussed, but production Vintage support must not be implemented before the decision is recorded.

---

# DEC-024 — Complete engineering-quality work before feature expansion

Status: `Accepted`

## Context

The repository currently lacks some engineering safeguards needed for safe multi-format and multi-source development.

## Decision

Before major feature expansion, add or improve:

- README;
- license and data notice;
- dependency lists;
- pytest;
- rule validation;
- classification conflict reports;
- Unknown reports;
- JSON Schemas;
- schema versions;
- CI;
- least-privilege Actions permissions;
- concurrency controls;
- workflow summaries;
- Standard regression protection.

## Consequences

Engineering-quality work is an early roadmap phase rather than final cleanup.

Feature implementation must not bypass missing validation by manually correcting generated files.

---

# DEC-025 — Use explicit schema versions

Status: `Accepted`

## Context

Normalized events and generated statistics will evolve as formats and event structures are added.

Without schema versions, consumers cannot safely distinguish old and new structures.

## Decision

Normalized event data and important generated output must include an explicit schema version.

JSON Schemas must validate supported structures.

Incompatible changes require:

- a schema-version change;
- updated validation;
- updated tests;
- updated consumers;
- migration or compatibility handling where necessary.

## Consequences

Schema changes are part of the public internal contract and must not be made silently.

---

# DEC-026 — Use raw counts and visible sample sizes

Status: `Accepted`

## Context

Percentages without counts can be misleading, especially for Day 2 archetypes and matchup matrices.

## Decision

Statistical output should retain the raw counts needed to reproduce displayed percentages.

Where applicable, the front end should show:

- player or deck count;
- match count;
- W-L-D;
- denominator;
- low-sample warning;
- confidence interval.

## Consequences

Generated JSON must not store only rounded display percentages.

Rounding belongs at the presentation layer where practical.

---

# DEC-027 — Report uncertainty and data-quality problems

Status: `Accepted`

## Context

Tournament data may contain missing decklists, Unknown archetypes, malformed results, incomplete rounds, or ambiguous phase labels.

Silently ignoring these problems would make statistics appear more reliable than they are.

## Decision

Generate and preserve data-quality information for each event.

Statistics must expose relevant warnings when:

- decklists are missing;
- archetypes are Unknown;
- classification conflicts exist;
- rounds are unidentified;
- results are unidentified;
- match coverage is incomplete;
- sample sizes are low;
- Day 2 selection affects interpretation.

## Consequences

Quality reporting is part of the product, not only a debugging tool.

Severe unresolved quality failures may block publication.

---

# DEC-030 — License code, documentation, rules, and source data separately

Status: `Accepted`

## Context

The repository contains project-authored software, documentation, and archetype classification rules alongside third-party tournament records and intellectual property. One license cannot accurately grant rights over all of these materials.

## Decision

License repository software code under the MIT License.

License project-authored documentation and archetype classification rules under the Creative Commons Attribution 4.0 International license.

Do not claim ownership of or relicense underlying tournament records, decklists, card names, artwork, trademarks, or other third-party materials. Record source, attribution, trademark, and data-use boundaries in `NOTICE.md`.

## Consequences

The repository must include `LICENSE` and `NOTICE.md`, and `README.md` must summarize the licensing boundary. Reusers must evaluate their own right to use third-party data. Source provenance should be preserved where supported.

---

# DEC-031 — Use one scheduled MTGO production update workflow

Status: `Accepted`

## Context

The legacy `scrape.yml` and `update.yml` workflows both ran `batch_mtgo.py`, modified `data/` and `fetched.txt`, and pushed repository changes on separate schedules without shared concurrency. The complete update workflow already included the scraper's fetch responsibility plus Videre match fetching and statistics generation.

## Decision

Use `.github/workflows/update.yml` as the only scheduled MTGO production update pipeline. It must fetch official MTGO events, fetch Videre matches, generate Standard and matchup statistics, run validation, and publish the complete reviewed output set in one serialized workflow.

Remove `.github/workflows/scrape.yml` after static regression tests verify that its unique committed paths and `batch_mtgo.py` invocation remain covered by `update.yml`. Keep `batch_mtgo.py` as the production fetch entry point.

Use explicit `contents: write`, one non-cancelling production concurrency group, pinned dependencies, a master-only job guard, a bounded timeout, and an Actions summary. This decision does not authorize automatic event discovery or change any statistical formula.

## Consequences

The repository no longer publishes raw MTGO fetch results separately from the statistics derived from them. A failure before publication leaves the previously committed data and statistics together rather than publishing a partially refreshed state. Videre fetching and matchup generation remain required production steps. If `master` advances during a run, publication fails safely instead of rebasing output generated by older code onto the newer revision.

---

# Open decisions

The following items track decisions that remain open, have been resolved, or are deferred. Unresolved items must not be guessed during implementation.

## License details

Status: `Resolved by DEC-030`

The approved licensing structure includes:

- a code license;
- a notice covering third-party and source data;
- clear treatment of project documentation and classification rules.

The approved license combination is recorded in DEC-030.

## Low-sample matchup presentation warning

Status: `Resolved by DEC-060`

The Phase 8 MTGO and Tabletop consumers warn when a matchup has fewer than 20
valid matches. This is a presentation caution only, not a reliability,
eligibility, confidence-interval, or publication threshold. Confidence
intervals remain available for every nonzero valid-match sample.

## Remaining statistical warning and quality thresholds

Status: `Accepted`

The project still needs exact policies where applicable for:

- Day 1 versus all-Constructed difference warnings;
- configurable decklist-coverage blocking thresholds;
- event publication quality failures beyond the existing deterministic gates.

These values must be finalized in `docs/STATISTICS_SPEC.md` or an applicable
quality specification and covered by tests before implementation.

## Vintage implementation

Status: `Deferred`

Vintage remains behind the decision gate recorded in DEC-023.

## Automatic Melee discovery

Status: `Deferred`

The approved initial design uses a manual whitelist.

Automatic discovery is not part of the current implementation scope.

---

# Decision maintenance procedure

When adding a decision:

1. assign the next sequential decision ID;
2. provide a short title;
3. set its status;
4. explain the context;
5. state the decision precisely;
6. record the consequences;
7. identify any superseded decision;
8. update related specification files;
9. update tests and schemas where applicable;
10. update `docs/STATUS.yaml`.

Do not delete old decisions merely because they are no longer active.

Mark them `Superseded` and link them to the replacement decision.

---

# DEC-028 — Use disposable isolated workspaces for agent development

Status: `Accepted`

Operational restrictions in this decision are partially superseded by DEC-029. Its isolation, credential, protected-source, direct-`master`, and no-automatic-publication requirements remain accepted.

## Context

Broad permissions, credential exposure, protected-repository writes, and per-command human technical approval each create avoidable security, integrity, and operational risks.

## Decision

Use independent, disposable clones for agent development. Permit sandboxed ordinary-file writes and use Auto-review only for narrow local Git metadata operations in the isolated task workspace. Deny network access by default.

Require owner confirmation for external or irreversible operations. Full access, automatic push, automatic PR creation, automatic merge, direct development on `master`, and credential access are prohibited. Task authorization ends at the task stop point and does not authorize later tasks.

The operational requirements are defined in `docs/DEVELOPMENT_WORKFLOW.md`.

## Consequences

This decision does not alter product scope, statistics, architecture, public paths, schemas, or production behavior.

---

# DEC-029 — Delegate local execution within approved focused tasks

Status: `Accepted`

## Context

Requiring repeated Owner approval for harmless local-only operations can prevent an already approved focused task from being completed efficiently, while remote publication and product decisions still require direct Owner control.

## Decision

Adopt a two-gate authorization model. An approved focused task grants delegated local execution authority inside its disposable isolated workspace for reasonably necessary implementation, investigation, testing, test repair, fixture generation, temporary experimentation, and local Git operations. This authority does not carry over to another task or phase.

Remote publication and every remote mutation require separate Owner authorization. Product and statistical decisions remain Owner-controlled. Disposable-workspace isolation, credential restrictions, no direct development on `master`, and no automatic publication remain mandatory. `docs/DEVELOPMENT_WORKFLOW.md` is the detailed operational authority.

This decision partially supersedes only the restrictive operational portions of DEC-028.

## Consequences

Task contracts must distinguish delegated local execution from remote-publication authority and preserve explicit protected-path and stop conditions. Harmless local task operations do not require repeated Owner authorization. This decision does not alter product scope, statistics, architecture, public paths, schemas, or production behavior.

---

# DEC-032 — Add optional subtypes beneath compatibility archetypes

Status: `Accepted`

## Context

The legacy Standard classifier contains 76 ordered rule entries but only 74 distinct archetype display names. `4-Color Control` and `Izzet Aggro` each have two distinct legacy rule paths that currently return the same archetype name.

The shared classifier needs stable rule identities and full-match diagnostics, but treating every legacy rule path as a separate archetype would break the approved Standard compatibility baseline. Conversely, discarding the rule-level distinction would prevent the product from exposing meaningful variants later.

## Decision

Use a two-level classification identity:

- `archetype` is the required parent identity and compatibility result;
- `subtype` is an optional rule-level variant beneath one archetype.

During the initial Phase 2 compatibility migration, different existing rule entries that already return the same legacy archetype may produce different subtypes. The parent archetype must remain identical to the legacy classifier for every frozen Standard record.

Initial subtype creation is limited to the existing duplicate Standard rule groups. Archetypes without an existing duplicate rule path return no subtype. No new archetype or additional subtype taxonomy is added until the compatibility classifier is complete and a later rule-development task is separately approved.

Primary statistics continue to aggregate by parent archetype. Subtype-level statistics or presentation are not introduced implicitly. Later front-end work must explicitly consider how to display subtype information without splitting or double-counting the parent archetype.

## Consequences

Archetype IDs, subtype IDs, and rule IDs require stable validation. Classification results and diagnostics may carry nullable subtype fields. Compatibility tests must compare parent archetype results against the Phase 1 baseline and separately verify subtype assignment.

Rule migration, classifier implementation, schemas, reports, and later front-end planning must follow this hierarchy. Adding future archetypes or subtypes remains a separately reviewed rule and product change.

---

# DEC-033 — Separate MTGO event archival from product-format execution

Status: `Accepted`

## Context

Before Phase 3, the scheduled `batch_mtgo.py` command archived official MTGO event data for Standard, Pauper, Modern, Pioneer, Legacy, and Vintage. Only Standard had Videre match collection, classification rules, generated statistics, Pickup, and front-end output. Treating every non-executable format as ineligible for all network collection would silently stop the existing non-Standard event archive during the generalized-command migration.

## Decision

Represent official MTGO event archival separately from complete product-format execution. `event_collection_enabled` authorizes event-page discovery, download, normalized raw storage under `data/<format>/`, and fetched-ledger maintenance. It does not enable Videre collection, classification, statistics, Pickup, metadata, catalogs, public JSON, or front-end presentation.

Preserve official event archival for Standard, Pauper, Modern, Pioneer, Legacy, and Vintage. Keep Standard as the only executable MTGO product format during Phase 3. Keep Videre collection Standard-only until another format's implementation is separately approved.

## Consequences

The format registry and its Schema must distinguish collection permission from execution permission. The production workflow must keep its event-collection allowlist aligned with the registry. Tests must prove that a collection-enabled planned format writes only to its own event path and remains unable to run product commands. Collecting raw events is not approval to publish or statistically process a format.

---

# DEC-034 — Use the 2026 Marvel Super Heroes Pro Tour and Modern as the first post-Standard reference path

Status: `Accepted`

Supersedes the ordering portion of DEC-022 and the Paupergeddon-first reference-event decision. Pauper and Paupergeddon remain approved later targets.

## Context

The original roadmap selected Pauper and Paupergeddon Summer 2026 (`438329`) as the first post-Standard format and tabletop reference event. After Pro Tour Magic: The Gathering® | Marvel Super Heroes concluded, the project owner selected its Melee event (`434455`) as the more useful current reference and explicitly changed the first post-Standard trial format to Modern.

The event ran three Draft Swiss rounds followed by five Modern Swiss rounds on each of Day 1 and Day 2, with a Draft Top 8 playoff. It therefore exercises mixed-event boundaries, Day 1 and Day 2 separation, Draft exclusion, overall-standing ambiguity, and official Top 8 lock handling earlier than the pure Constructed reference would.

## Decision

Use Melee event `434455`, `https://melee.gg/Tournament/View/434455`, as the initial Tabletop Major Events reference contract. Treat it as a `mixed` event with Modern as its Constructed format. Keep the whitelist entry disabled until live Melee fetching receives separate authorization.

Represent these dimensions independently in normalized data:

- event stage, such as Day 1, Day 2, or playoff;
- round phase, such as Draft, Constructed, playoff, or unknown;
- actual game format, such as Limited or Modern.

Implement Modern before Pauper after the protected Standard baseline. Retain Pauper, Paupergeddon, Pioneer, Legacy, qualifying Standard tabletop events, and the Vintage decision gate in later roadmap positions.

## Consequences

Phase 5 uses `434455` only to define and validate ingestion contracts; it does not authorize live fetching, Modern classification, statistics, or publication. Later Modern statistics may include only verified Modern Swiss records. Draft Swiss and the Draft Top 8 remain available as source context but are excluded from Modern performance and matchup calculations.

Overall standings cannot be presented as Modern-only performance because they combine Draft and Modern results. Day 2 metrics require the existing selection-bias warning. The roadmap, scope, architecture examples, status, whitelist, schemas, and tests must reflect the new reference path.

---

# DEC-035 — Separate clean baselines from production candidate acceptance

Status: `Accepted`

## Context

The production update run `29795445118` successfully fetched and generated new MTGO data, then failed five fixed-reference tests because those tests read the now-mutated production directories and compared them with the previously committed Standard snapshot. The failures correctly detected that the checkout no longer matched the historical baseline, but that baseline responsibility was being applied at the wrong lifecycle stage. Treating historical deck counts as daily data-acceptance thresholds would make every legitimate data increment look like a regression.

## Decision

Use three explicit validation layers:

- read-only pull-request and `master` CI runs the complete test suite against a clean checkout, including tests marked `committed_baseline`;
- the production workflow runs the same clean-checkout suite before any fetch as defense in depth, then captures a dynamic production baseline;
- after fetching and generation, a dedicated candidate validator checks permitted publication paths, rejects deletions and source-boundary violations, parses changed documents, verifies event and match shape, checks ledger uniqueness, and prevents event, match, or ledger count regression;
- strict classification diagnostics and repository, rule, and Schema validators continue to run on the generated candidate;
- after publication, the workflow confirms a clean workspace and equality between the local published commit and remote `master`.

Fixed-reference tests do not run against a checkout after production mutation. Dynamic candidate acceptance does not use historical hard-coded event, deck, or matchup counts.

## Consequences

Standard remains the committed regression baseline without blocking legitimate daily growth. Production publication receives a separate fail-closed boundary that can detect unexpected code, configuration, Melee, or unsupported-format product writes. A newly generated file is parsed even when it is still untracked and therefore invisible to tracked-file-only repository checks. Extending the production publication scope or permitting automatic deletion requires an explicit validator and workflow review.

This decision changes validation orchestration only. It does not change statistical formulas, classification rules, public JSON contracts, source inclusion policy, or format authorization.

---

# DEC-036 — Reproduce the currently committed production snapshot from its metadata

Status: `Accepted`

## Context

The first successful production run after DEC-035 published commit `c50d599730d1c0bbce26bb609e9cddae1e6fcc66`. The candidate validator correctly accepted the new data, but the next clean checkout failed five `committed_baseline` tests. Those tests still supplied the previous run's hard-coded generation date, timestamps, event count, matchup counts, report counts, and Pickup week while comparing against the newly committed production files. The failure was caused by stale test inputs rather than a generator, statistical, or data-quality regression.

## Decision

Committed-snapshot tests must derive volatile reproduction inputs and expected aggregate counts from the versioned metadata already stored with the committed snapshot. They continue to regenerate outputs and require byte-identical equality with the committed files.

Stable behavioral expectations remain explicit and independent of daily volume: Standard legacy and shared entry points must agree; classification reports must have no conflicts or invalid decks; report totals must be internally consistent; only the approved compatibility subtype identities may appear; generated outputs must match committed reports; and the frozen classification corpus, formulas, schemas, rules, path boundaries, and production candidate validation remain unchanged.

## Consequences

A legitimate automated production update does not require an accompanying manual test edit merely because dates, event totals, matchup totals, subtype observations, or Pickup weeks advanced. A clean checkout still detects non-deterministic generators, stale or internally inconsistent committed outputs, wrapper divergence, unexpected subtype identities, conflicts, invalid decks, and byte-level output differences.

This decision changes test reference selection only. It does not change production code, statistical formulas, classification rules, generated data, public JSON, or source inclusion policy.

---

# DEC-037 — Require explicit evidence for Melee result normalization

Status: `Accepted`

## Context

P5-05 deliberately assembled source matches with unknown result semantics. A
source result string such as `2-1-0` does not identify the winner by itself, and
competitor array order is not a reliable outcome contract. Exceptional records
such as awarded wins after a Top 8 lock also require event-specific evidence.

## Decision

Retain explicit per-competitor source outcome text and match points when the
stored response supplies them. Never infer a winner from competitor order.
Accept the earlier identity-only stored fixture shape for parser compatibility,
but leave its result unknown unless a complete evidence-backed interpretation is
available.

Whitelist Schema 3.0.0 adds event-scoped `reviewed_overrides`. An override must
be explicitly `verified`, identify one source match, list complete source participant results and points,
declare whether play occurred, provide a reason, and cite HTTPS evidence. A Top
8 lock awarded win additionally requires the event's advancement configuration
to support that procedure. Overrides cannot invent participant or match
identities.

Only consistent played win/loss or draw/draw results in the configured
Constructed Swiss format are eligible for primary Constructed and matchup
statistics. All other normalized types remain contextual and ineligible.
Unknown phases, statuses, or results block quality. P5-06 always leaves
`publishable` false; P5-07 separately decides publication readiness.

## Consequences

The normalized output becomes deterministic and auditable without using source
ordering as hidden semantics. Existing Standard behavior, MTGO collection,
classification rules, statistics, public JSON, workflows, and front-end output
do not change. The reference Melee event remains disabled and no live fetch is
authorized.

---

# DEC-038 — Require complete bounded public-source validation for Melee ingestion

Status: `Accepted`

## Context

The initial P5-08 live check requested only the whitelisted tournament page with
a project-branded User-Agent and received HTTP 403. Browser reachability alone
could not prove that Phase 5 could collect standings, matches, and decklists or
normalize the real reference event. The project owner raised P5-08 acceptance
from a page-reachability probe to complete real-source collection, parsing,
normalization, and quality assessment, and approved comparison with the public
`j6e/mtg-meta-analyzer` implementation.

## Decision

Use ordinary anonymous browser-compatible request headers for public Melee HTML
and JSON endpoints without credentials, cookies, browser-session reuse, or
access-control bypass. Begin only from an enabled whitelisted tournament page;
discover completed rounds from that page; fetch the final completed Swiss
standings, every completed round's DataTables match pages, and only the decklist
GUIDs referenced by those standings.

Keep collection sequential and rate-limited. Reject redirects, unexpected
hosts or paths, unsafe IDs, changing pagination totals, and configured round,
decklist, response, or byte limits. Raw manifest `2.0.0` records method,
request-body digest, and applicable source round, participant, and decklist
context. Stored `1.0.0` fixture manifests remain readable.

Map Melee participant states `Cut` and `Eliminated` to completed active
participation and `Dropped (Self)` or `Dropped (Staff)` to dropped
participation. Preserve `Disqualified` as the distinct normalized participant
status `disqualified`. Retain that participant, standings, decklist, points, and
all source matches, but exclude every match involving them as a complete unit
from Constructed win-rate and matchup eligibility. Do not delete only one side
of a match. Emit a non-blocking quality warning so the exclusion is visible.

This mapping does not alter source match outcomes or points. Normalized event
Schema `2.1.0` adds the explicit participant status and the quality gate verifies
the resulting match eligibility.

## Consequences

P5-08 must pass an ephemeral complete run through parsing, normalization,
Schema, and semantic quality assessment before Phase 5 can close. Real raw,
participant, match, and decklist data remain temporary during this closeout and
must not enter Git or production paths. Anonymous aggregate counts and issue
codes may be retained as audit evidence.

This decision does not enable the committed reference event, authorize Modern
classification or statistics, change the front end or workflows, or authorize
publication. Production retention, resumability, and operational progress
reporting remain later tasks.

---

# DEC-039 — Adopt a pinned j6e Modern signature-rule compatibility baseline

Status: `Accepted`

## Context

The project owner identified the public `j6e/mtg-meta-analyzer` Modern classifier as the appropriate starting point, consistent with the historical origin of the Standard classification logic. The current project has since replaced the legacy framework with stable archetype and rule IDs, explicit priorities, optional subtypes, conflict evidence, and explicit Unknown reporting.

The upstream Modern definitions at commit `0ecd26bd734cedc6c40e7c753115f796613a32ba`, file `data/archetypes/modern.yaml`, contain 38 unique parent archetypes. The deterministic upstream signature classifier checks mainboard cards only and chooses the matching definition with the greatest number of signature conditions; the earlier source-list position wins a tie. Its later centroid fallback depends on the surrounding deck corpus rather than only on a reviewable rule.

## Decision

Use that pinned file as the P6-01 parent-archetype compatibility source and provide CC BY 4.0 attribution to Joan G.E. and `j6e/mtg-meta-analyzer`. Convert each source definition into one shared-schema rule with:

- a stable archetype ID and rule ID;
- `subtype_id: null`;
- an explicit `main` zone on every condition;
- a unique priority equal to `condition_count * 1000 + (rule_count - source_index) * 10`.

This priority encodes the complete deterministic upstream winner order: condition count first and source order second. It must produce the same parent archetype on the frozen committed Modern corpus even if YAML collections are reordered.

Do not migrate the corpus-dependent centroid fallback. A deck without a deterministic signature match remains `Unknown` so it can be measured and reviewed. Do not add new archetypes or subtypes during P6-01 or P6-02. P6-02 completes framework migration and shared-path integration while preserving the fixed 38-parent rule contract. Modern rule extensions, new parent archetypes, and optional subtype distinctions belong to P6-03 and must retain an explicit compatibility comparison with this baseline.

Only committed `CMODERN` event records may enter the baseline. At the P6-01 snapshot, two misplaced `CPREMODERN` files were excluded from the frozen compatibility corpus; P6-04 later removes those unsupported-format files from `data/modern/`. The frozen fixture must be de-identified and contain no participant, account, standing, event, or source identifiers.

## Consequences

MTGO and Melee can later share the same 38 Modern parent IDs without coupling their source data or statistics. The migration is deterministic, attribution-compliant, reorder-independent, and reviewable. Unknown and overlapping-rule counts become explicit baseline quality measurements rather than being silently filled by a model.

P6-01 does not enable Modern in the format registry, change Standard behavior, run production classification, generate statistics or reports, modify workflows, change public JSON, or change front-end behavior. P6-02 may complete shared classification and diagnostic integration only; P6-03 owns the first taxonomy additions. Product enablement and publication behavior remain later separately authorized Phase 6 tasks.

---

# DEC-040 — Use strategic-family parents and evidence-backed Modern subtypes

Status: `Accepted`

## Context

P6-01 intentionally froze the 38-parent j6e compatibility result before any taxonomy changes. For P6-03, the project owner supplied an independent Chinese classification workbook covering recent Modern challenge high-score decks and clarified the intended parent/subtype boundary. A read-only comparison uniquely aligned 179 committed `CMODERN` events and 4,771 high-score deck records; it found 166 non-empty owner labels and one blank label. The workbook, event identities, player identities, and source rows are not repository artifacts.

The owner-defined labels frequently describe color or construction variants within one strategic family. In particular, Broodscale Combo variants and Prowess variants should share a parent, and Colorless and Mono-Green Eldrazi Tron should share a parent. Energy variants should remain separate parents because Boros, Mardu, Jeskai, and non-red builds differ enough that one Energy parent would hide material strategic differences.

## Decision

Use a shared parent archetype when variants retain the same defining engine and game plan, and use a subtype for a reviewable color or construction branch within that family. Apply this boundary to Broodscale Combo, Prowess, Eldrazi Tron, and other strongly evidenced families. Keep Boros Energy, Mardu Energy, Jeskai Energy, Azorius Energy, Selesnya Energy, and Esper Energy as separate parent archetypes with no Energy umbrella subtype.

Every production rule remains a deterministic mainboard signature rule with a stable archetype ID, stable rule ID, explicit subtype or `null`, and globally unique priority. Unsupported centroid or corpus-nearest-neighbor fallback remains prohibited. Sparse workbook labels do not justify a new production identity by themselves; proposed Hardened Scales, Kethis, and Valakut labels therefore remain absent until representative evidence supports reliable rules.

Preserve the P6-01 artifact as a separate frozen rule fixture and continue running its original full-corpus compatibility tests unchanged. Add a P6-03 taxonomy contract over the same de-identified 5,792 records. The contract must freeze the active rule-text hash, exact parent counts, exact selected subtype counts, every P6-01-to-P6-03 parent transition, representative selected identities, rule-order independence, and the approved parent/subtype boundaries.

## Consequences

The active Modern taxonomy contains 55 parents, 100 rules, and 54 subtype definitions. On the frozen corpus it classifies 5,664 records and leaves 128 explicit Unknown; 2,329 records receive a subtype. The diagnostic path reports 1,519 multiple matches and 132 same-parent multiple-subtype matches, with zero conflicts and zero invalid decks. These overlaps remain visible and deterministic rather than being hidden.

This decision changes Modern taxonomy and its regression contracts only. It does not enable Modern in `configs/formats.yaml`, generate Modern reports or statistics, change Standard or Melee behavior, modify workflows or schemas, publish public JSON, or alter either front end. Product enablement and any later taxonomy extension remain separately controlled tasks.

---

# DEC-041 — Enable Modern classification and remove unsupported Premodern archives

Status: `Accepted`

## Context

P6-03 established a reviewed Modern taxonomy, but Modern remained globally disabled. The generalized MTGO command layer already supports per-operation capabilities, so enabling all Modern product behavior merely to create classification diagnostics would unnecessarily expose statistics, match collection, Pickup, metadata, catalogs, workflows, and front-end behavior. The committed Modern raw-event directory also contained two Premodern documents whose embedded format was `CPREMODERN`. The project owner clarified that Premodern is a separate unsupported format and must not be stored as Modern data.

## Decision

Make Modern executable and non-public with the `classification` capability only. Generate deterministic, de-identified classification diagnostics under `reports/modern/mtgo/`. Keep every other Modern product capability disabled and require its command to fail before network or output side effects.

Delete the two misplaced Premodern documents from `data/modern/`. Do not create a Premodern registry entry, storage path, exception allowlist, report, statistic, or product surface. Preserve the existing fail-closed classifier behavior: any future embedded format other than `CMODERN` under `data/modern/` blocks report generation before writes.

Generalize only the classification-report Schema fields needed to validate multiple format IDs and their format-scoped source paths. Retain classification-report Schema version `1.0.0` and format-registry Schema version `1.1.0`; existing Standard documents remain byte-identical.

## Consequences

Modern classification is now a reproducible repository product without implying Modern statistics or public availability. The six Modern report documents are Schema-validated and contain no participant identity fields. `data/modern/` contains only embedded `CMODERN` events, and cross-format input remains blocking rather than silently omitted. Standard retains its existing paths, generated bytes, statistics, workflow, and front-end behavior. Later Modern statistics, matchup data, catalogs, workflows, and front-end selection require separate authorized tasks.

---

# DEC-042 — Calculate hierarchical matchups before the expandable front end

Status: `Accepted`

## Context

The approved front-end direction defaults to parent-archetype matchup rows and
columns while allowing either axis to expand independently into subtypes. A
global control should expand or collapse all eligible parents. A parent with
zero or one defined subtype should not expose subtype controls.

The existing matchup calculation aggregates only parent archetypes. Deferring
subtype-aware calculation until front-end implementation would require a later
statistics and Schema redesign and would risk placing undocumented statistical
logic only in JavaScript. Standard must also adopt the shared calculation when
the front end migrates; leaving Standard on the legacy calculation would create
two incompatible product paths.

A read-only scan at production commit `168e929` found:

- Standard has 74 parent archetypes, two parents with subtype definitions, and
  no parent with exactly one subtype. Of 3,955 classified decks, 46 select a
  subtype. The other 3,909 belong only to parents with no subtype definitions.
- Modern has 55 parent archetypes, 17 parents with subtype definitions, and no
  parent with exactly one subtype. Of 5,726 classified decks in the then-current
  event snapshot, 2,360 select a subtype. The other 3,366 belong only to parents
  with no subtype definitions.
- Neither format has a classified deck with a null subtype under a parent that
  defines subtypes.

## Decision

P6-06 must implement and validate canonical directed W-L-D counts that support
parent-parent, subtype-parent, parent-subtype, and subtype-subtype matchup views.
The fully collapsed parent matrix remains the default and must reconcile
exactly from the subtype-aware representation. Rates are calculated from summed
counts, never by averaging percentages.

The final front-end interaction belongs to P6-09, after Modern data production
and metadata are available. P6-09 must first run Standard through the same
shared hierarchical calculation and prove that its collapsed parent matrix
matches the existing Standard result. It then implements independent row and
column expansion, the global expansion control, and taxonomy-based suppression
for parents with zero or one defined subtype.

A null subtype is valid when a parent defines no subtypes. No residual subtype
is currently necessary for either Standard or Modern. If a future classified
deck has a null subtype under a parent that defines subtypes, generation must
fail visibly under OPEN-005's approved no-residual resolution; it must not
silently omit the deck or invent an unapproved residual subtype.

## Consequences

The statistical contract is fixed before front-end design, while detailed
visual presentation remains deferred. Standard public matchup output remains
compatible until P6-09 performs its explicit migration. P6-06 owns Modern
hierarchical calculation and real matchup data; P6-07 owns hierarchy metadata;
P6-08 owns recurring production; P6-09 owns the shared front end and Standard
migration; P6-10 owns final regression and the phase tag.

The owner authorized local P6-06 implementation and confirmed the no-residual
scope on 2026-07-23. Remote publication, workflow changes, and front-end changes
remain separately controlled.

---

# DEC-043 — Generate hierarchical MTGO range statistics before Phase 7

Status: `Accepted`

## Context

The Phase 6 front end can expand matchup rows and columns by subtype, but the
official MTGO environment statistics remain parent-only. The intended MTGO
statistics interaction is the same hierarchy principle: parent archetypes are
shown by default, eligible parents can expose their subtypes, and one global
control can expand or collapse all eligible parents. Implementing only the
front-end control later would leave subtype metagame, performance, conversion,
and deck-construction values unavailable or tempt the browser to reconstruct
statistical logic from parent aggregates.

Phase 7 begins a separate Melee source pipeline. Mixing this MTGO backend change
into the Pro Tour work would blur the required MTGO/Melee boundary and make
regression attribution harder.

## Decision

Implement `BRIDGE-MTGO-SUBTYPE-STATS-01` as an independent task between Phase 6
and Phase 7. Extend existing MTGO `range_<n>w.json` and `decks_<n>w.json`
documents additively with nested subtype entries. Do not create a separate
subtype endpoint or workflow.

Parent archetypes remain the primary and default aggregation. A subtype row is
computed directly from records assigned to that subtype and uses the same
thresholds and formulas as its parent-level counterpart. For a
subtype-defining parent, subtype counts must conserve the parent deck,
high-score, and Top 8 counts exactly. The complete maintained subtype list is
emitted for every observed subtype-defining parent, including explicit
zero-observation entries.

Deck-construction outputs are also recalculated independently per subtype.
Their four-week base, sample threshold, representative deck, average deck,
Core/Flex lists, deviation, and recent-change result use only that subtype's
records. They must not reuse or proportionally split the parent base.

Preserve the no-residual rule: a classified deck under a subtype-defining
parent without a selected subtype blocks generation. Preserve Phase 6
parent-only values and ordering through a frozen projection contract. Leave the
current front-end rendering unchanged; the later UI task will consume the
already-defined hierarchy rather than redefine its statistics.

## Consequences

Standard and Modern gain schema-validated subtype-ready MTGO range and
deck-construction data while existing parent presentation remains stable.
Generated documents grow because they retain maintained subtype empty states
and construction payloads. The scheduled MTGO workflow needs no structural
change because it already runs the shared generator for both enabled formats.

This decision does not alter Weekly Pickup grouping, matchup formulas,
classification taxonomy, Melee outputs, public paths, or the Phase 7 reference
event. It does not authorize remote publication or a production workflow run.

---

# DEC-044 — Activate the verified Pro Tour reference event in a staged Phase 7 pipeline

Status: `Accepted`

## Context

Phase 5 proved that the complete public source for Melee event `434455` can be
collected, parsed, normalized, and assessed without unresolved issues. Its real
records remained temporary and the committed whitelist entry stayed disabled.
Phase 6 then completed the shared Modern taxonomy and MTGO Modern product.
Phase 7 must now turn the verified ingestion capability into a retained,
source-separated Tabletop Major Events backend without combining activation,
live data retention, classification, statistics, workflow automation, and
front-end work in one change.

## Decision

P7-01 makes event `434455` the only enabled Melee whitelist entry. The event
remains `verified`, `mixed`, and Modern, with Draft and Constructed phases kept
independent. Activation permits only the existing bounded client to resolve
this exact event when a caller explicitly invokes collection. Complete live
collection continues to require both `--execute` and `--complete`.

P7-01 performs no live request and creates no real raw archive, normalized
event, statistic, catalog, workflow, or front-end output. P7-02 owns retained
raw and normalized production input. P7-03 through P7-08 then own shared Modern
classification, mixed-event opportunity accounting, overview statistics,
hierarchical matchup statistics, public packaging and workflow integration,
and real production closeout respectively. Phase 8 owns the tabletop front
end.

Historical Phase 5 disabled-event protections remain testable with an explicit
disabled copy of the same immutable event definition. Current-configuration
tests instead require the verified event to be fetchable and continue to prove
that disabled events fail before network or filesystem side effects.

## Consequences

The repository gains a deliberate Phase 7 lifecycle transition without a
network or generated-data change. Running the manual collection command can now
create a raw snapshot for event `434455`, but only with explicit execution
flags; no scheduled workflow invokes it. Unlisted, disabled, unverified, unsafe,
redirected, or over-bound source access remains rejected.

MTGO Modern behavior, MTGO generated data, Modern taxonomy, statistical
formulas, public JSON, GitHub workflows, and both front ends remain unchanged
in P7-01. Starting P7-02 or dispatching a live or production workflow requires
separate owner authorization.

# DEC-045 — Retain one complete reference snapshot as deterministic normalized input

Status: `Accepted`

## Context

Phase 5 validated the complete event `434455` source path with temporary real
data, and P7-01 activated that exact verified whitelist entry. Later Phase 7
classification and statistics need reproducible production input, but
request-level resume could combine pages observed at different source moments.
The normalized event also previously named artifacts only at the event
directory level rather than identifying the immutable snapshot that supplied
them.

## Decision

P7-02 retains one complete raw manifest `2.0.0` snapshot and one canonical
normalized event in Git. Retention requires the snapshot to be a direct
timestamped child of the approved event archive, requires exact manifest/file
coverage, verifies every response's size and SHA-256, parses the complete
source, applies reviewed normalization, and passes the existing fail-closed
Schema and semantic quality gate before writing.

Safe restart reuses only a completed and digest-verified snapshot. Partial
temporary collections are discarded as a unit and are never combined with a
later request. The immutable snapshot timestamp supplies `normalized_at`, so
the same source rebuilds byte-identically. An existing normalized event with
different bytes is a review failure, not an overwrite opportunity. Production
raw-artifact provenance includes the snapshot directory. Git treats
`data_raw/**` as byte-preserved source evidence with both text and end-of-line
conversion disabled, so a clean checkout retains the manifest's exact response
bytes.

The retained source contains only the public tournament records needed for the
approved product, including source-published participant names and IDs,
standings, matches, and decklists. It contains no cookies, credentials, private
request headers, or browser-session state. Third-party records remain covered
by `NOTICE.md` and are not relicensed as project code.

## Consequences

Event `434455` becomes reproducible production input without yet becoming
classified or statistical output. P7-03 can classify its submitted Modern
decklists without another network request. Any later source refresh creates a
new immutable candidate and needs explicit review before repository retention
or canonical-input replacement.

P7-02 changes normalized event Schema from `2.1.0` to `2.2.0` for
snapshot-qualified production provenance while retaining read compatibility
with the committed `2.1.0` synthetic fixture. It does not change match
eligibility, classification rules, statistical formulas, workflows, public
catalogs, MTGO data, or either front end.

# DEC-046 — Store Melee deck classification as a deterministic overlay

Status: `Accepted`

## Context

P7-02 made event `434455` reproducible normalized input. Appending
classification to that event would break its byte-identical rebuild contract
and couple source normalization to a taxonomy that may evolve independently.
Later event statistics still need a stable participant-keyed parent and
subtype result with enough evidence to review Unknowns and overlapping rules.

## Decision

P7-03 stores derived classification at
`data/<format>/melee/classifications/<event_id>.json` instead of rewriting the
canonical normalized event. The output joins by normalized `participant_id`
and records exact event and rule bytes through SHA-256 provenance. It applies
the unchanged shared format taxonomy and retains selected parent, subtype,
rule, priority, all matched rule evidence, overridden evidence, conflicts,
invalid-input errors, and normalized deck evidence for Unknowns.

Strict validation treats conflicts, invalid decks, and a null subtype under a
parent with maintained subtypes as blocking. Unknowns are reviewable but
non-blocking. A null subtype remains valid only for a parent with no maintained
subtypes. Classification is independent of statistical eligibility, so a
disqualified participant's retained decklist is classified while their
matches remain excluded from later statistics.

The overlay is deterministic: it contains no wall-clock, checkout-depth, Git
history, or current-branch value. Identical normalized-event and rule bytes
must rebuild the exact committed JSON bytes. The adapter maps Melee card
sections to the shared classifier input only and must not contain a second
source-specific taxonomy.

## Consequences

The retained reference event yields 362 overlay records: 290 classified and 72
Unknown, with zero conflicts, invalid decks, or residual-subtype violations.
There are 153 selected subtype records and 137 parent-only records. The source
event and shared Modern taxonomy stay byte-identical, and all MTGO Modern
products remain unchanged.

P7-04 and later tasks can join classifications without mutating production
input. P7-03 does not calculate participation, opportunities, points, win
rates, conversion, or matchups. Improving the 72 Unknown classifications would
change the shared Modern taxonomy and requires a separate reviewed task with
MTGO regression evidence.

# DEC-047 — Store mixed-event Constructed opportunities as a deterministic ledger

Status: `Accepted`

## Context

The retained Pro Tour event mixes Draft and Modern on both days. Later
archetype statistics need scheduled Constructed opportunities even when a
player drops, while win-rate and matchup calculations need only eligible real
matches. Deriving those populations and exclusions separately in P7-05 and
P7-06 would risk inconsistent Day 2 membership, double counting, and different
treatment of byes, intentional draws, disqualification, or Top 8 locks.

## Decision

P7-04 stores a deterministic participant-round ledger at
`data/<format>/melee/opportunities/<event_id>.json`. It hashes the immutable
normalized event and the P7-03 classification overlay, joins them by stable
participant ID, and records the selected classification summary without
rewriting either input.

The Day 1 population is the complete starting field. The Day 2 population is
established by actual Day 2 Swiss participation, including Draft evidence;
Draft results themselves remain excluded. Every member receives each scheduled
Constructed Swiss opportunity in that stage. Missing rounds are synthesized
only for a normalized `dropped` or `disqualified` status; any unexplained
absence fails closed.

Point inclusion, theoretical and effective rounds, win-rate inclusion, matchup
inclusion, and exclusion reasons are independent fields. Ordinary drops retain
zero-point theoretical rounds. Verified Top 8 lock awards retain their source
value but contribute zero Constructed points and no effective theoretical
round. A disqualified participant remains distinct from a drop; both sides of
each affected match remain retained and symmetrically excluded from win-rate
and matchup use under DEC-038.

The ledger contains no wall-clock, checkout, branch, or Git-history value.
Identical input bytes must rebuild identical UTF-8 JSON. It is an internal
derived input, not a public statistic. P7-05 owns archetype overview and deck
aggregation; P7-06 owns matchup aggregation.

## Consequences

Event `434455` yields 362 Day 1 participants, 220 evidenced Day 2
participants, 2,910 theoretical Constructed opportunities, and 2,903 effective
opportunities after seven verified Top 8 lock exemptions. It retains 88
ordinary unplayed drop opportunities, four later administrative
disqualification opportunities, seven byes, and two Constructed intentional
draw matches. The 1,394 win-rate and matchup-eligible source matches reconcile
exactly with the normalized event; six disqualification-affected Constructed
matches remain excluded as complete units.

Draft and playoff records, MTGO products, taxonomy rules, public statistics,
workflows, and both front ends remain unchanged. Any future event with an
unexplained missing participant-round record must be reviewed rather than
silently assigned a result.

# DEC-048 — Generate direct hierarchical per-event deck statistics

Status: `Accepted`

## Context

P7-04 established one authoritative Constructed-opportunity ledger for the
mixed Modern reference event. P7-05 needs to turn that ledger into event and
deck statistics without changing the shared Modern taxonomy, pre-aggregating
future matchup cells, hiding Unknown decks, or applying a front-end sample
policy that has not yet been approved.

## Decision

Generate three deterministic event candidates at
`stats/<format>/melee/events/<event_id>/`: `overview.json`, `decks.json`, and
`quality.json`. Bind each document to the exact normalized-event,
classification-overlay, opportunity-ledger, and taxonomy bytes and fail closed
on any provenance or identity mismatch.

Use separate `day1`, `day2`, and `all_constructed` scopes. Calculate parent
rows directly and retain Unknown as an explicit parent bucket in applicable
denominators. For each observed parent with maintained subtypes, emit the
complete subtype list in taxonomy order, calculate every subtype directly,
and require additive counts and all-match W-L-D records to reproduce the
parent. The parent remains the default view and is expandable only when at
least two maintained subtypes exist.

Report stage-specific high-score metrics for Day 1 and Day 2. Do not invent a
combined high-score result across unequal populations. Retain raw W-L-D sample
counts, all-match and non-mirror records, and 95% Wilson intervals. Do not
hard-code the unresolved OPEN-002 low-sample display thresholds.

Keep the disqualified participant's deck and official Constructed points as
frozen by the P7-04 ledger, but exclude all affected matches from played win
rate. P7-06 remains responsible for matchup aggregation. P7-07 remains
responsible for `meta.json`, catalog discovery, public-manifest integration,
and workflow packaging; Phase 8 owns front-end behavior.

## Consequences

Event `434455` produces 362 Day 1 and 220 Day 2 participant records. The
all-Constructed-Swiss scope contains 2,910 theoretical and 2,903 effective
opportunities, 4,196 Constructed points, and 1,394 eligible matches. The
classification population remains 290 known and 72 Unknown. Observed parent
and maintained subtype statistics are reproducible without changing MTGO
Modern or the taxonomy.

The generated candidates are directly Schema-validated but are not yet
catalog-discoverable or part of the public-output manifest. No source fetch,
matchup matrix, workflow, catalog, or front-end change is implied.

# DEC-049 — Store canonical leaf matchups and derive both parent axes

Status: `Accepted`

## Context

P7-05 exposes direct parent and maintained-subtype deck statistics, while the
approved future front end must independently expand either matchup axis.
Generating only a parent matrix cannot recover subtype matchups. Generating
separate display matrices risks double counting, incompatible samples, and
parent totals that no longer reproduce the established overview. The
low-sample display policy also remains unresolved under OPEN-002.

## Decision

For each mixed-event scope, store one complete canonical matrix at the most
specific maintained leaf identity. A leaf is a subtype, a parent with no
defined subtype, or Unknown. Retain all event hierarchy nodes and explicit
zero cells. Derive the complete parent matrix by summing the leaf matrix over
both axes; never roll up rates.

Use `day1`, `day2`, and `all_constructed` scopes, defaulting to
`all_constructed`. Admit only physical matches represented by exactly two
reciprocal opportunity rows whose `matchup_included` values are both true and
whose played results are inverse. Preserve reviewed physical-match exclusion
counts by reason.

Sibling subtype matches are leaf non-mirrors and parent mirrors. Leaf overall
records therefore exclude only their own leaf diagonal; parent overall records
exclude the complete parent diagonal and must reproduce P7-05 parent
non-mirror records. Retain raw W-L-D counts and Wilson 95% intervals. Record a
null low-sample threshold until OPEN-002 is resolved.

## Consequences

Event `434455` yields 29 parent nodes and 55 canonical leaves across every
scope. It includes 861 Day 1 and 533 Day 2 physical matches, for 1,394 combined
matches and 2,788 directed combined observations. The combined 22 exclusions
are seven byes, two intentional-draw matches, seven verified Top 8 lock
awards, and six disqualification-affected matches.

The deterministic `matchup.json` is directly Schema-validated and can support
future independent row and column expansion without reprocessing source
matches. P7-07 still owns catalog discovery, manifest governance, `meta.json`,
and workflow integration. Phase 8 owns the front-end interaction. No MTGO
output, taxonomy rule, source data, or existing P7-05 statistic changes.

# DEC-050 — Publish Melee events through deterministic metadata and a review branch

Status: `Accepted`

## Context

P7-05 and P7-06 produced complete event statistics, but those files had no
format catalog, no per-event integrity metadata, and no public-manifest
governance. A future front end needs one stable discovery entry point.
Production refreshes also need a source-specific boundary that cannot modify
MTGO data or push unreviewed source changes directly to `master`.

## Decision

Generate deterministic `meta.json` and `index.json` documents. The event
metadata records exact path, Schema version, byte size, and SHA-256 for the
overview, decks, matchup, and quality documents after each one reproduces its
deterministic generator bytes. The format catalog exposes only the enabled,
verified reference event and its five public paths. Add all six event/catalog
documents to `schemas/manifest.json`.

Add a separate Melee candidate validator. Permit only the selected event's new
raw snapshot, normalized event, classification overlay, opportunity ledger,
five event statistics, and format catalog. Reject deletions, mutation of
retained raw evidence, cross-event writes, cross-format writes, MTGO writes,
and inconsistent embedded identities.

Provide a manual-only, event-scoped workflow with `contents: write`, explicit
concurrency, and no schedule. Reuse the exact immutable snapshot recorded by
an existing canonical event; fetch only when the selected approved event has
no canonical input. It may push a successful candidate only to
`data/melee-<event_id>`. It must not push `master`, create or merge a pull
request, or share the MTGO workflow. Owner-controlled PR publication remains
outside the workflow.

## Consequences

Modern event `434455` becomes discoverable through
`stats/modern/melee/index.json`, while its `meta.json` provides a stable
integrity boundary for all four statistical payloads. Public Schema validation
expands from 46 to 52 documents without changing any statistic.

P7-07 performs no live source request and does not dispatch the workflow.
P7-08 separately owns the first real run, candidate review, Phase 7 closeout,
and recovery tag. Phase 8 owns all front-end behavior.

---

# DEC-051 — Freeze a local format-first UI before Phase 8 backend additions

Status: `Accepted`

## Context

Phase 8 was originally described only as the separate Tabletop Major Events
front end. The project now has two public MTGO formats, hierarchical parent and
subtype matchup data, subtype-specific MTGO range and construction data, and a
complete Modern Pro Tour backend. Designing each statistic first and adding a
format selector inside it would obscure the selected format and duplicate
navigation.

The owner also requires a weekly MTGO Top 8 decklist view, subtype-specific
construction details, and visible completeness for Videre match archives and
MTGO high-score decklists. These requirements create new backend consumers, but
their payloads should not be implemented before the interaction and
unavailable-state behavior are approved.

Superdesign is installed as an optional external design service. It is useful
for parallel high-fidelity visual exploration, but it is not required to define
information architecture or to validate the repository's data-heavy
interactions. Defaulting to it would introduce an external-service dependency,
possible plan or quota limits, and unnecessary context transmission before a
specific visual problem exists.

## Decision

Phase 8 uses format as the primary analysis selector. After selecting a format,
the interface exposes the available MTGO official statistics, MTGO matchup,
MTGO weekly Top 8, Tabletop Major Events, and Weekly Pickup products. Generated
catalogs determine availability.

Keep `/index.html` and `/melee/index.html` as separate source-product entry
points. A shared shell may preserve the selected format while navigating
between them, but MTGO and tabletop data loading, caches, statistics, quality
claims, and generated outputs remain separate.

Parent archetypes are the default display. Eligible parents may expand into
maintained subtypes, matchup axes expand independently, and one global control
expands or collapses all eligible parents. A parent with zero or one maintained
subtype is non-expandable. Public subtype labels are self-contained without
changing stable subtype identities.

Deck-construction detail uses the most specific maintained identity. Selecting
an expandable parent only reveals subtypes and does not display a cross-subtype
average. Selecting a subtype displays its independently generated construction
data. A weekly Top 8 selection reuses the detail component while showing the
exact event deck against the subtype average and deviation base.

Before backend changes, P8-01 audits current consumers, P8-02 creates local
prototypes, and P8-03 freezes the owner-approved UI and backend consumer
contract. P8-04 then specifies formulas and public payloads; P8-05 through
P8-07 implement and validate only the confirmed backend gaps; P8-08 through
P8-10 implement the shared shell and final front ends; P8-11 closes the phase.

Local HTML/CSS/JavaScript prototyping is the default design method. Superdesign
may be used only after a separate owner authorization based on a documented
unresolved design problem, expected deliverables, verified current pricing or
quota limits, transmitted context, privacy minimization, and local alternative.
Installation or authentication does not authorize generation or upload.

## Consequences

Phase 8 expands from a Tabletop-only page task into a controlled redesign and
supporting-data phase, but it does not merge the two source products or approve
another front-end framework. Existing hierarchical calculations are reused and
must not be rebuilt in browser code.

The exact Videre and high-score completeness formulas remain a P8-04
statistical-contract decision. No generator or front-end implementation may
estimate those denominators before the specification, fixtures, Schemas, and
owner-required unavailable states are approved.

The owner approved this planning direction on 2026-07-25. The approval
authorizes the documentation baseline only. P8-01 implementation, external
design-service use, production changes, publication, workflow dispatch, and
deployment remain separately controlled.

---

# DEC-052 — Revalidate the Phase 8 UI with real generated data before implementation

Status: `Accepted`

## Context

P8-03 can approve information hierarchy, statistical meaning, navigation, and
representative component states before the missing backend products exist.
However, some final UI decisions depend on real payload characteristics such as
row counts, label lengths, missing values, warning frequency, table density,
deck-detail size, and narrow-screen behavior. Treating the first prototype
approval as the last visual review would force those issues to be discovered
after production implementation.

## Decision

Keep P8-03 as the initial UI and backend-consumer-contract freeze required
before backend development. Extend P8-07 into a second mandatory owner gate.
After the required backend products have been generated and validated against
retained real Standard and Modern data, load representative real payloads into
the accepted review UI and obtain final owner acceptance before P8-08 begins.

The P8-07 review may revise presentation, wording, density, responsive layout,
empty and unavailable states, and interactions. If it reveals a missing field,
formula, denominator, provenance value, or Schema rule, stop and return to a
separately authorized contract/backend task. Do not reconstruct the missing
statistic in browser code.

## Consequences

P8-03 remains meaningful: it prevents speculative backend products and freezes
the intended consumer contract. P8-07 prevents the final front end from being
built against representative placeholders only. P8-08 through P8-10 cannot
begin until the data-backed review is accepted.

The owner approved this route clarification and the recommended interaction
decisions on 2026-07-27. This decision does not authorize backend production
changes, production front-end implementation, publication, or deployment.

---

# DEC-053 — Use literal all-match win rate and preserve visible mirror cells

Status: `Accepted`

## Context

The existing statistical specification uses
`(wins + 0.5 × normal draws) / valid matches` and prefers non-mirror archetype
rates for comparison. During P8-02 review, the owner clarified that the visible
label `胜率` should instead mean the literal percentage of valid matches won.
The owner also confirmed that mirror results are meaningful: their draw
frequency is information, and the deployed MTGO matrix already displays its
diagonal rather than replacing it with an unavailable state.

The first P8-02 prototype incorrectly returned an unavailable dash for every
diagonal matrix cell. This was an unauthorized loss of existing behavior.

## Decision

The Phase 8 target consumer contract is:

- `win_rate = wins / (wins + losses + normal_draws)`;
- a normal played draw remains in the denominator and contributes zero wins;
- the established exclusions for intentional draws, byes, no-shows, awarded
  wins, administrative results, Draft, and primary-Swiss playoffs remain;
- primary overview and `整体` values include mirror matches;
- non-mirror rates remain explicit supporting output;
- both MTGO and Tabletop matchup matrices display real diagonal mirror W-L-D,
  win rate, confidence interval, and sample state.

P8-02 may demonstrate this contract with clearly identified prototype data.
P8-04 owns the versioned migration of statistical specifications, generators,
Schemas, compatibility fields, fixtures, and regression tests. Production
statistics are not reinterpreted or rewritten during P8-02.

## Consequences

MTGO mirror cells with no draws remain 50%. Tabletop mirror cells may be below
50% because normal draws count as valid non-wins under the literal definition.
That value is intentional and exposes the mirror draw frequency rather than
hiding it.

The production front end must not derive the new rate from incomplete browser
data. P8-04 must define explicit all-match and non-mirror fields and a
compatibility plan before any generator or production consumer changes.

---

# DEC-054 — Freeze the initial Phase 8 UI and backend consumer contract

Status: `Accepted`

## Context

P8-02 received owner acceptance as a Chinese-first local prototype, but its
decisions were distributed across the prototype audit, planning document, and
DEC-051 through DEC-053. The current public output also still reflects the
pre-P8 draw-adjusted compatibility behavior. Starting backend work from either
the prototype alone or the legacy output would risk speculative fields,
browser-side statistics, feature deletion, or a false claim that the new
win-rate formula is already deployed.

## Proposal

Use `docs/audits/P8-03.md` as the initial Phase 8 UI and backend consumer
contract. It freezes the accepted Chinese interaction baseline, preserves the
current production feature surface unless a deletion is separately accepted,
assigns missing data products to P8-04 through P8-06, and separates target
literal all-match win rate from legacy published compatibility output.

The audit records the accepted English dictionary alongside the accepted
Chinese prototype language. Any later wording change remains subject to owner
review.

P8-04 must make the versioned Schema, field-name, compatibility, rounding,
fixture, and migration decisions. No P8-03 documentation change authorizes a
generator, public page, workflow, data rewrite, or browser calculation.

## Consequences

P8-03 becomes the mandatory acceptance gate before Phase 8 backend changes.
P8-07 remains the separate real-data visual review before production UI work.
If owner review changes an interaction without changing data meaning, amend the
P8-03 contract before P8-04 begins. If it changes a statistic or source
boundary, obtain a separately authorized P8-04 decision.

The owner accepted this freeze and its recorded English dictionary on
2026-07-27. This acceptance does not authorize P8-04 implementation.

---

# DEC-055 — Version the Phase 8 public statistical target

Status: `Accepted`

## Context

The accepted UI requires literal all-match win rate, range-specific Videre
coverage, modeled MTGO high-score decklist completeness, complete-week Top 8
decks, self-contained subtype identities, and direct Tabletop scope summaries.
Existing public outputs use legacy draw-adjusted rates and do not expose all of
those inputs. Changing their meaning in place would make old and new consumers
indistinguishable.

## Decision

Define `schemas/phase8-public-contract.schema.json` version `1.0.0` as a
parallel migration target with an executable fixture and semantic tests. Do not
map it to current public files during P8-04.

Target match records declare `win_rate_method:
"wins_over_valid_matches"`, calculate `W / (W + L + D)`, retain all-match and
non-mirror records, and calculate Wilson intervals with literal wins as
successes and all valid played matches as trials.

Videre interval coverage uses
`available / (available + deferred + missing)` and keeps excluded events outside
the denominator. High-score decklist completeness uses the reviewed
`mtgo-high-score-binomial-v1` model: infer rounds from the existing player-count
table, calculate each event's fair decisive-match binomial tail without
rounding, sum raw expectations, round the displayed expected count half-up, cap
the displayed rate at one, and retain `exceeds_model`. Events without the
required player, round, threshold, or Swiss-score evidence are unsupported and
never treated as zero.

Top 8 weeks retain exactly ranks 1 through 8 per admitted event and fail closed
with explicit missing-deck entries. Public subtype labels are self-contained.
Tabletop documents expose event structure, supported scopes, direct per-scope
overall records, and compatible matchup scopes.

## Consequences

P8-04 changes no producer, current public JSON, manifest mapping, workflow, or
front end. P8-05 and P8-06 own product-specific producer Schemas and migration;
P8-07 owns validation against real retained Standard and Modern data.

The high-score expectation is a completeness model under explicit simplifying
assumptions, not an exact reconstruction of Swiss pairings. Unsupported events
remain visible and can trigger focused source-quality work instead of lowering
the denominator silently.

---

# DEC-056 — Publish the latest complete-week MTGO Top 8 product

Status: `Accepted`

## Context

P8-03 requires a weekly MTGO Top 8 table whose event columns preserve exact
finishing decks and whose detail view compares the selected deck with the most
specific maintained parent or subtype construction base. P8-04 freezes the
event, placement, exact-deck, identity, missing-state, and comparison-reference
contract. The current four-week deck output is rolling and has no immutable
historical address.

## Decision

Add the capability-gated `build-top8` producer for Standard and Modern. Publish
`top8/index.json` and one latest complete-week `top8/YYYY-Www.json`, validate
them with product-specific version 1.0.0 Schemas, map the four concrete public
documents in the manifest, and expose the catalog through MTGO metadata.

Every admitted event has exactly eight ordered rank slots. Missing decks remain
explicit null states. Available decks retain exact main deck and sideboard,
self-contained stable identity, and a same-period `decks_4w.json` comparison
reference. Generation fails on duplicate event identities, duplicate Top 8
ranks, or invalid event metadata.

Do not retain historical weeks while their references would resolve to a newer
rolling comparison base. Historical browsing requires a separately reviewed
immutable or version-addressable construction-base contract. P8-07 reviews
whether that extension is required before production UI implementation.

## Consequences

The format registry advances to version 1.2.0 and complete MTGO products now
require `weekly_top8`. The scheduled workflow builds the product before
metadata, and production-candidate validation admits only the defined Top 8
catalog and week paths for Standard and Modern. The production manifest grows
from 52 to 56 mapped documents. P8-05 changes no fetch behavior, classifier,
win-rate formula, Tabletop output, or deployed front end.

---

# DEC-057 — Publish range-specific MTGO completeness and literal match records

Status: `Accepted`

## Context

P8-04 froze Videre range coverage, modeled high-score decklist completeness,
and literal all-match win rates. The deployed MTGO output exposes only
format-global archive counts and draw-adjusted percentages. The browser cannot
derive the approved denominators or safely reinterpret those legacy values.
The current Videre fetcher also has no durable deferred-event status ledger.

## Decision

Add the Standard/Modern `completeness_reporting` capability and publish
`completeness/index.json` plus 1-, 4-, 12-, and 36-week range documents. Each
document carries the two separate P8-04 completeness blocks. A usable non-empty
Videre archive is available. An admitted event without one is missing unless
explicit durable source evidence marks it deferred; absence alone is never
treated as temporary incompleteness.

Keep existing MTGO matchup `win_rate` and Wilson-half-width fields as deployed
compatibility data. Add `literal_record` to each matrix cell and add
`parent_match_records` and `leaf_match_records` containing primary all-match,
supporting non-mirror, and physical mirror counts. Only records declaring
`wins_over_valid_matches` have the new target meaning.

Expose the completeness catalog through metadata, validate the product with
dedicated version 1.0.0 Schemas, map all ten Standard/Modern documents, admit
only their reviewed paths in production-candidate validation, and regenerate
them before Top 8 and metadata in the scheduled workflow.

## Consequences

The format registry advances to version 1.3.0 and the production manifest grows
from 56 to 66 documents. The current front end remains unchanged and continues
reading legacy matchup fields until P8-09. P8-07 can now validate real
Standard/Modern completeness, labels, density, and empty states without
inventing statistics in JavaScript. A future deferred-event ledger requires a
separate reviewed source-status contract rather than a silent denominator
change.

---

# DEC-058 — Bridge frozen Phase 8 consumers with immutable weekly Top 8 bases

Status: `Accepted`

## Context

P8-07 exercised the frozen consumer contract against real Standard, Modern,
and Tabletop output. Most statistical products were present, but consumers
would still have had to reconstruct subtype labels, reinterpret Tabletop legacy
win rates, hard-code product paths, and compare an older Top 8 deck against a
mutable rolling construction base.

## Decision

Publish a generated `stats/catalog.json` containing all known formats, all five
approved product slots, actual availability, and public entry paths. Add a
self-contained `display_name` to subtype consumers across MTGO and Tabletop.
Preserve every existing Tabletop draw-adjusted record and add a nested literal
record using wins over all valid played matches, including normal draws only in
the denominator.

Retain weekly Top 8 history only with a same-week immutable
`YYYY-Www-bases.json` companion. The catalog starts at the first safely
reproducible week, 2026-W30, and accumulates forward. Existing immutable week
and base bytes must reproduce exactly. Exact-deck deviation uses the existing
four-week subtype or parent formula; insufficient samples produce an explicit
unavailable base and null deviation.

## Consequences

The production front end can consume labels, rates, product availability,
historical averages, and deviation without deriving them in JavaScript. The
current deployed page remains unchanged. No older week is guessed or
backfilled, no legacy rate field is removed, and MTGO and Tabletop data remain
separate.

---

# DEC-059 — Productionize the P8-07 prototype instead of re-splitting the legacy page

Status: `Accepted`

## Context

The original P8-08 plan was written before P8-07 grew into a high-fidelity,
owner-accepted prototype backed by real Standard, Modern, and Tabletop data.
Phase 4 had already split the deployed legacy page into static assets.
Decomposing that page again would create an intermediate implementation that
the accepted P8-07 design would immediately replace.

## Decision

Use P8-07 as the target implementation and behavior reference. Keep the
deployed legacy MTGO page only as the regression oracle and rollback baseline.

P8-08 creates a parallel modular production candidate with a shared shell,
catalog-driven availability, and separate MTGO and Tabletop controllers,
loaders, state, and caches. It does not replace `/index.html`, create the final
`/melee/index.html`, change formulas, or change public data contracts.

P8-09 separately connects the accepted MTGO candidate to `/index.html` after
one-to-one regression. P8-10 separately connects the accepted Tabletop
controller to `/melee/index.html`. No mandatory framework or build step is
introduced.

## Consequences

P8-08 avoids a second legacy decomposition and concentrates verification on the
accepted real-data behavior. Production entry-point changes remain isolated,
reviewable, and independently reversible. The owner approved this revised
P8-08 through P8-10 route on 2026-07-29.

---

# DEC-060 — Use one 20-match low-sample presentation warning

Status: `Accepted`

## Context

OPEN-002 deferred the exact low-sample display threshold until the Tabletop
consumer could be reviewed with real data. During P8-07, the owner reviewed a
shared MTGO and Tabletop warning at fewer than 20 valid matches. The accepted
production front end uses that same value for both products, but the durable
specification and project status still described the decision as pending.

A 20-match sample near a 50% observed win rate still has a wide 95% Wilson
interval. Reaching 20 matches therefore cannot be presented as proof that an
estimate is reliable.

## Decision

Use one Phase 8 presentation warning for both MTGO and Tabletop matchup
consumers:

- fewer than 20 valid matches: show the low-sample warning;
- 20 or more valid matches: do not show that warning solely because of sample
  count.

The threshold is a visual caution marker only. It does not change match
eligibility, W-L-D counts, literal win-rate calculation, confidence intervals,
generated-data admission, or publication. Zero-match cells remain unavailable.
Consumers must continue to expose the actual match count and 95% Wilson
interval; the warning must state that crossing the line does not guarantee
reliability.

The shared Phase 8 consumer value is authoritative for the current static
front end. A later configuration or generated-contract migration may relocate
the value without changing its meaning, but must not silently choose a
different threshold for one source product.

## Consequences

OPEN-002 is resolved. The existing production UI behavior is documented rather
than changed. MTGO and Tabletop use the same warning logic while their source
data, matrices, and statistics remain separate.

This decision does not establish a decklist-coverage blocking threshold and
does not remove the need to interpret confidence intervals and raw sample
counts.

---

# DEC-061 — Limit initial multi-event matchup selection to all Constructed Swiss

Status: `Accepted`

## Context

Tabletop events may use `mixed`, `constructed_day2`, or
`constructed_single_stage`. Mixed and pure Day 2 events can expose Day 1, Day
2, and all Constructed Swiss scopes, while a single-stage event has no Day 1
or Day 2 cut scope. The existing multi-event decision requires compatible
scopes but did not define what the consumer should do when selected events
have different structures.

Stage-specific raw-count aggregation can be meaningful for a carefully
compatible event set, but enabling it initially would require additional rules
for cut structures, absent stages, and selection effects.

## Decision

When exactly one event is selected, expose every scope declared by that event.
A `constructed_single_stage` event therefore exposes only
`all_constructed`; it does not display fictional or zero-valued Day 1 and Day
2 scopes.

When two or more compatible same-format Tabletop events are selected, force
the matchup scope to `all_constructed`. Aggregate underlying valid Constructed
Swiss W-L-D counts and recalculate the rate and interval. Do not average event
percentages and do not merge event-overview metrics.

If a second event is selected while Day 1 or Day 2 is active, switch to
`all_constructed`. During multi-selection, keep stage controls disabled with
an explanation when they are useful for orientation; omit them when the
selected single event does not define those scopes. Returning to one event may
restore its last supported single-event scope.

## Consequences

`all_constructed` is the initial common cross-structure aggregation scope.
Phase 9 must expose reliable event-level supported-scope metadata and enforce
the consumer state transition. Phase 11 remains responsible for implementing
the multi-event raw-count aggregator and compatibility checks.

This decision does not declare stage-specific multi-event aggregation invalid.
Enabling it later requires a separate reviewed contract for compatible event
structures, cut rules, missing stages, and selection effects.

---

# DEC-062 — Complete large-event ingestion and dynamic format labels before Phase 9 closeout

Status: `Accepted`

## Context

The initial Phase 9 plan placed bounded real-source pilots immediately before
cross-structure closeout. The owner-selected Standard pilot event `419742`
contains 893 final-Swiss decklists. A complete archive is estimated to require
1,085 successful responses, which exceeds both the current 500-decklist and
500-response limits.

Future approved tabletop events may exceed 2,000 players. This is a
single-event ingestion constraint, not Phase 11 multi-event aggregation.

The P9-06 Tabletop consumer is structure-aware but its scope labels still
contain hard-coded Modern text. Standard source pilots expose that consumer
genericity gap before Standard tabletop publication is enabled.

## Decision

Use the Phase 9 route:

```text
P9-07 -> P9-07S -> P9-08
```

P9-07 uses three owner-selected Standard events, one for each supported
structure, and retains only aggregate audit evidence.

P9-07S implements a bounded, checkpointed, resumable complete-event collector.
It must finalize atomically and must not allow incomplete work to enter
normalization, statistics, or publication.

P9-08 replaces hard-coded Modern scope labels with labels derived from the
selected event's format metadata and the language dictionary. It then performs
the final cross-structure and cross-format consumer regression.

## Consequences

Phase 9 cannot close while an approved 893-player event is structurally valid
but impossible to archive safely. Raising one constant is not an accepted
solution because it provides neither resumability nor atomic completeness.

Phase 11 remains responsible for compatible multi-event raw-count aggregation.
Phase 16 may enable Standard tabletop events only after the format-neutral
consumer behavior has already been proven in P9-08.

No event is added to the whitelist and no production data is generated or
published by this decision.

---

# DEC-063 — Renumber the post-Phase-9 roadmap

Status: `Accepted`

## Context

The roadmap written before the Phase 7 through Phase 9 implementation still
lists mixed Draft and Constructed event support as Phase 10. That work is now a
historical specification: Phases 7 and 8 delivered the mixed-event backend and
consumer for event `434455`, and Phase 9 preserved it while adding pure
Constructed strategies.

The former roadmap also places multi-event aggregation immediately after that
historical phase and defers data governance, engineering-baseline, front-end
productization, and long-term operational work. A first renumbering proposal
omitted former Phase 12, Whitelist operations and Melee automation, and former
Phase 18, Cleanup, operations, and release. Both contain requirements that must
remain traceable even when their remaining work moves elsewhere.

## Decision

Adopt the following post-Phase-9 mapping:

| Former roadmap position | Current roadmap position |
| --- | --- |
| Former Phase 10 — Mixed Draft and Constructed events | Retain in full as Historical Phase 10 with status `superseded_by_phases_7_and_8` |
| Former Phase 11 — Multi-event matchup aggregation | Phase 13 — Multi-event raw-count matchup aggregation |
| Former Phase 12 — Whitelist operations and Melee automation | Retain as a historical migration record; move remaining work to Phase 10 |
| Former Phase 13 — Pauper and Paupergeddon | Phase 14 — Pauper MTGO and Paupergeddon |
| Former Phase 14 — Pioneer | Phase 15 — Pioneer |
| Former Phase 15 — Legacy | Phase 16 — Legacy and Eternal Weekend |
| Former Phase 16 — Standard tabletop events | Phase 17 — Standard Tabletop events |
| Former Phase 17 — Vintage decision gate | Phase 18 — Vintage decision gate |
| Former Phase 18 — Cleanup, operations, and release | Retain as a historical migration record; split remaining work across Phases 10, 11, and 19 |

Insert these current phases before multi-event and format expansion:

- Phase 10 — Data governance, compliance, and production operations;
- Phase 11 — Engineering baseline, test structure, and documentation
  reduction;
- Phase 12 — Front-end productization and sharing readiness.

Use Phase 19 for final release and long-term maintenance closeout. Keep the
possible Environment Trends time-series capability unnumbered unless the owner
separately approves its product scope, data source, comparability policy, and
statistical specification.

Every current Phase 10 through Phase 19 section must use `Objective`,
`Required work`, `Task sequence`, and `Acceptance criteria`. Listing a phase or
task does not authorize its implementation. `docs/STATUS.yaml` remains the
source of truth for task authorization and stop conditions.

References written before DEC-063 retain their historical numbering unless
they explicitly cite this mapping. Historical audit files and task identifiers
must not be mass-renumbered. New planning references use the current numbering.

## Consequences

The roadmap preserves the complete former Phase 10 specification and explicit
migration records for former Phases 12 and 18. Multi-event aggregation moves to
Phase 13, format expansion moves to Phases 14 through 18, and final release
readiness moves to Phase 19.

This decision changes roadmap order and identifiers only. It does not change a
statistical formula, match-eligibility rule, public Schema, public data path,
production output, front-end behavior, event whitelist, or the existing
`434455` compatibility bytes. It does not authorize R-02, any current Phase 10
task, event activation, production dispatch, remote publication, history
rewriting, or storage migration.

---

# DEC-064 — Freeze event 434455 bytes without freezing expandable catalogs

Status: `Accepted`

## Context

Event `434455` is the retained mixed-event regression baseline. Existing tests
rebuild its normalized and public artifacts, but exact digests are distributed
across tests and historical status records. The Phase 9 handoff also listed
whole-file hashes for `stats/modern/melee/index.json` and `stats/catalog.json`.
P10-01 proved that the latter changed during a legal production update even
though no event-specific `434455` byte changed.

Freezing only the five event statistics would omit their retained source and
derived-input chain. Freezing either complete catalog would block unrelated
events or products from being added legally.

## Decision

Adopt `tests/fixtures/melee/434455_compatibility_manifest.json` version `1.0.0`
as the executable compatibility boundary.

Freeze the exact bytes of the retained raw snapshot manifest, normalized event,
classification overlay, opportunity ledger, and five event-specific public
documents. Treat the raw manifest as a closure root and verify every declared
response's unique path, byte count, and SHA-256 together with the snapshot's
exact declared file set.

Do not freeze the complete bytes of `stats/modern/melee/index.json` or
`stats/catalog.json`. Freeze only the selected `434455` event entry and the
Modern `tabletop-major-events` product route. Permit unrelated catalog growth
and volatile root-field changes when those projections remain unchanged.

Do not freeze the complete whitelist or Modern taxonomy as event-specific
bytes. Their shared evolution remains separately controlled. Any protected
byte change requires a new compatibility version, replacement evidence, this
decision's successor, and separate owner approval. Do not regenerate the v2
snapshot under a future privacy contract.

## Consequences

The compatibility boundary is explicit, Schema-validated, and enforced without
copying 483 response hashes into a second maintained list. Later event and
product work can expand both catalogs without weakening `434455` protection.

P10-02 changes tests, a contract fixture, a non-public contract Schema, and
documentation only. It changes no retained or generated data, public Schema
mapping, public path, statistic, source configuration, workflow, or front end.
P10-03 remains separately owner-gated.

---

# DEC-065 — Minimize future Melee snapshots before persistence

Status: `Accepted`

## Context

The retained event `434455` snapshot is a source-preserving v2 archive and is
now protected by the P10-02 exact-byte compatibility manifest. P10-01 found
that its standings and match responses repeatedly retain unused account,
profile, preference, and duplicate identity fields. The complete collector
also wrote each source response before parsing it, so downstream filtering
could not enforce a persistence boundary.

The existing public participant IDs were deterministic unsalted hashes of
small numeric source IDs. Anyone who knew the event ID and algorithm could
enumerate those values. Participant names are a separate product choice: the
owner selected continued use of source-published `DisplayName` for future
events while rejecting unused account and profile fields.

## Decision

Use complete manifest `3.0.0` and minimized resource document `1.0.0` for
future approved Melee events. Parse every bounded source response in memory,
construct persistence from explicit tournament, standings, match, and decklist
allowlists, and write only canonical JSON. Store transient source byte count
and SHA-256 for provenance, but never store the unfiltered source body in the
v3 collection path.

Replace raw participant IDs with references of the form `melee-v3-<digest>`,
where the digest is HMAC-SHA256 over:

```text
melee\0v3\0<event_id>\0participant\0<source_participant_id>
```

Require at least 32 bytes of key material and a reviewed non-secret key ID.
Only the key ID is persisted. Missing or invalid key settings fail before
network or filesystem side effects, and a checkpoint cannot resume under a
different key ID. One key ID must never identify different key material.

Preserve source-published `DisplayName`, statistical record/result/status
fields, card name/quantity/section, reviewed source identifiers, request
integrity metadata, and required source URLs. Exclude the unused fields listed
in `docs/audits/P10-03.md` before persistence.

Continue reading immutable v1/v2 fixtures and snapshots. Permit retention from
complete v2 or v3 manifests. Do not regenerate, migrate, or otherwise change
the retained event `434455` v2 snapshot or any byte protected by P10-02.

## Consequences

Future participant records remain joinable within one event but raw numeric
participant IDs are no longer persisted or enumerable without the secret, and
the same source ID produces a different reference in another event. Because
`DisplayName` remains public by owner decision, this is not an anonymity
guarantee.

Production key creation, storage, rotation, workflow provisioning, and live
collection remain separately owner-gated. P10-04 owns resource Schemas as the
primary production-data gate, supplemental prohibited-field scans, and the
notice/contact/removal update. P10-03 changes no statistic, production data,
public path, whitelist, workflow, or front end.

---

# DEC-066 — Validate minimized Melee resources and publish the privacy contact

Status: `Accepted`

## Context

P10-03 constructs future v3 persistence from explicit Python allowlists, but
the minimized resource document had no standalone JSON Schema. Strict parser
field checks provided a second implementation boundary, while a repository-
wide text scan would create false positives in legacy v2 evidence, tests,
documentation, and legitimate string values. The public notice also lacked a
specific privacy contact and correction or removal procedure.

## Decision

Use `schemas/melee-minimized-resource.schema.json` version `1.0.0` as the
authoritative persistence contract for tournament, standings, matches, and
decklist documents. Reject additional properties at every persisted object
level and validate the document before canonical serialization and again when
reading a v3 resource.

Retain a separate exact-key prohibited-field scan as supplemental defense.
Run it only on a decoded minimized v3 resource and never on source bodies,
string values, documentation, the repository as a whole, or immutable v1/v2
snapshots. The Schema is the primary allowlist and the scan protects against a
future Schema edit accidentally admitting a previously rejected source key.

Publish `djacerror@gmail.com` in `NOTICE.md`. Ask requesters for the event ID
or URL, displayed name or record, affected project location, and requested
action, while discouraging passwords, tokens, and unrelated identity
documents. Distinguish project-controlled current content, upstream source
records, and repository history. Do not promise or perform a history rewrite
under this procedure.

## Consequences

Future v3 persistence and all v3 consumers share one machine-readable,
fail-closed field contract. Legacy v1/v2 parsing and the exact event `434455`
compatibility bytes remain unchanged. P10-04 changes no production data,
statistic, workflow, configuration, public path, or front end. Production key
provisioning, live collection, remote publication, and P10-05 history rewriting
remain separately owner-gated.

---

# DEC-067 — Require a restoration proof before any history-rewrite decision

Status: `Accepted`

## Context

P10-01 found unused account, profile, preference, and duplicate identity data
in the retained v2 event `434455` source snapshot. P10-03 and P10-04 prevent
the same unapproved fields from entering future v3 persistence, but they do
not remove the legacy snapshot from current master, Pages, Git history, or
other reachable refs.

P10-05 inventory finds one introducing commit, 21 affected ordinary remote
branches, three affected phase tags, and 49 affected GitHub pull-request head
refs. GitHub's pull-request refs are read-only, while external clones, forks,
and caches are outside a force-push's control. The current master files also
remain protected by the P10-02 exact-byte compatibility contract.

## Proposed decision

Before deciding whether to rewrite history, create an owner-designated private
independent Git bundle outside the repository and all disposable workspaces.
Record its byte count and SHA-256 without publishing its private absolute path,
verify the bundle, clone it into a second disposable repository, compare refs,
run `git fsck --full`, and pass the event `434455` compatibility and repository
validators in the restored clone.

Treat the bundle as controlled legacy source data. Do not commit, upload, or
publicly synchronize it. A tag or another clone sharing the same repository
storage is not an independent backup.

Do not execute a history rewrite during the preparation stage. After the
restoration proof, stop for a written owner choice to reject, defer, or
separately authorize execution. Prefer deferral until P10-06/P10-07 establish
an approved current raw-archive destination and compatibility successor,
because a history-only rewrite leaves the same files public at master and
Pages.

## Consequences

Preparation creates a recoverable pre-rewrite checkpoint without changing any
Git history, ref, production data, public path, workflow, or statistic. The
bundle itself carries the legacy exposure and needs deliberate retention and
eventual disposal.

Any later execution must separately authorize the exact filter, removal from
the current tree, compatibility migration, force-push, affected branch and tag
handling, collaborator instructions, Pages verification, and any GitHub
Support request. GitHub Support eligibility and removal of third-party copies
cannot be guaranteed by this project.

The preparation proof produced an 18,003,023-byte bundle at base
`48a4863a28d6ec6d9b854c7a9d72058c68a0f4aa`, verified SHA-256
`53ea51b53cd03f7cd55bdbfff61e7e0235e2c74f5556e3966f44f40e2c83a35d`,
restored all 216 named refs exactly, and passed object, compatibility, Schema,
rule, and repository validation. After explicit owner authorization, inherited
general-user ACL entries were removed; only the owner account, Administrators,
and SYSTEM retain access. Any later execution must refresh the bundle after
refs stop moving rather than treating this preparation artifact as current
forever.

---

# DEC-068 — Keep public Git data storage and separate Pages publication

Status: `Accepted`

## Context

The current scheduled MTGO workflow performs fetch, build, validation, commit,
push, and publication in one job. It commits changes under `data/`, `stats/`,
`reports/`, and `fetched.txt` directly to master. The manual Melee workflow
puts raw, normalized, and public candidate data into a Git review branch.

GitHub's managed branch-root Pages build currently serves representative
paths under `data/`, `stats/`, `reports/`, and `data_raw/`. The active product
front end consumes `stats/catalog.json` and `stats/<format>/mtgo/**`; publishing
the other layers follows from using the repository root, not from a proven
runtime dependency. P10-05 also established that rewriting history while the
same raw files remain current and public has no useful privacy effect.

P10-01 found unused Melee account, profile, preference, and duplicate identity
fields in the retained legacy v2 response bodies. P10-03 and P10-04 already
prevent those fields from entering future v3 persistence through exact
resource allowlists, strict Schemas, and a supplemental prohibited-key scan.
The owner does not require otherwise approved tournament data to be private.

The current repository contains a 17.30 MiB Git pack. An anonymous comparison
with `j6e/mtg-meta-analyzer` found 336,898,617 current data bytes, daily MTGO
and Videre commits to public master, and a separate custom Pages artifact. This
supports public Git storage at the present scale, while Videre's PostgreSQL and
R2 architecture serves a materially broader database and API product.

## Decision

Adopt option A+. Keep approved source evidence, normalized inputs, generated
data, code, tests, Schemas, reviewed configuration, and governance documents
in the current public Git repository and history. Continue applying the
accepted future Melee v3 minimization and validation boundary before
persistence. Do not add a storage provider, cloud account, storage fee,
object-store credential, or storage migration without new measured evidence
and a separate owner decision.

Replace implicit repository-root Pages publication with a custom static
artifact assembled in a fresh directory from an explicit allowlist. The first
artifact must preserve all approved user-facing and compatibility URLs,
including the exact event `434455` closure. An omitted current path is treated
as a deletion and fails unless a separate compatibility change was approved.

P10-07 may implement only that Pages-artifact boundary, compatible size
reporting, comparison, and rollback. It preserves the current public Git data
location and daily commit behavior. P10-09 remains the separately reviewable
task for splitting fetch, build, and publish jobs and narrowing each job's
permissions.

## Consequences

The selected design adds no paid service and no cloud-storage operational
burden. Public Git remains the durable archive, the independent P10-05 bundle
remains a controlled backup, and bounded Actions artifacts remain transfer or
Pages-delivery objects rather than the data source of record.

Approved repository data remains public and Git history continues to grow.
Those are accepted A+ properties, not confidentiality promises. P10-07 must
record repository, data-tree, and Pages-artifact sizes without automatically
deleting or migrating anything. A later storage proposal requires measured
capacity, performance, policy, or recovery evidence rather than hypothetical
growth alone.

The Pages artifact gives publication an exact path boundary even though the
same files remain available through the public Git repository. P10-07 narrows
what Pages serves; it does not claim to make Git-retained data private.

P10-06 changes no data, workflow, credential, public path, statistic, or front
end. The owner selected A+ on 2026-08-01. P10-07 implementation, commit, remote
publication, production dispatch, compatibility changes, data migration, and
history rewriting remain separately gated.

---

# DEC-069 — Build Pages from explicit product paths

Status: `Accepted`

## Context

The accepted A+ design keeps approved data in public Git but requires Pages to
deploy a fresh allowlisted artifact. The successful legacy Pages artifact from
run `30699810612` contains 1,996 files and 226,062,320 unpacked bytes. Besides
the two products and their data, it includes Python source, tests, internal
governance documents, reviewed configuration, rule files, Schemas, and
Jekyll-rendered Markdown output. The front ends consume only their static entry
points, assets, and `stats/` documents, while the approved compatibility
boundary also retains current `data/`, `data_raw/`, `reports/`, and fetched
ledger paths.

## Decision

Build the Pages artifact from `index.html`, `fetched.txt`, and the complete
`assets/`, `data/`, `data_raw/`, `melee/`, `reports/`, and `stats/` trees. Build
only into a new external directory, generate `.nojekyll`, prohibit symbolic
links and unsafe paths, preserve bytes, validate all 494 protected event
`434455` files, and fail above 1 GiB. Record tracked-repository, Git-object,
data-tree, artifact, protected-file, and excluded-file measurements on every
build.

Use a repository-owned custom Pages workflow. Pull requests build but do not
deploy. Every `master` push builds the current Git data state; only that event
may upload the Pages artifact and invoke a separate deployment job. The build
job has `contents: read`; the deploy job has only `pages: write` and
`id-token: write` and uses the protected `github-pages` environment.

Keep the repository Pages source in legacy `master` `/` mode through local and
pull-request validation. A separate remote authorization is required to switch
to GitHub Actions immediately before the accepted merge. If deployment or
front-end verification fails, restore the captured legacy source and require a
successful managed build.

## Consequences

The first candidate has 1,584 files and 213,481,951 bytes. Its 1,583 source
files are byte-identical to the same paths in the legacy artifact, and the only
new site file is empty `.nojekyll`. Repository code, tests, internal documents,
configuration, rules, Schemas, and Jekyll-only rendering output remain public in
Git but stop being Pages payloads. No data is deleted or migrated, no statistic
or front-end source changes, no external storage or credential is added, and
the P10-09 fetch/build/publish job split remains separate.

The owner confirmed both candidate front ends on 2026-08-01 and authorized
commit and publication. Pull request #146 merged implementation commit
`c97b6d2f6c6269df722dba062a08dfeafebbe9de` as
`a2d92c384d386d0a98ab9fd4bb7632ce066b3bfd`. The Pages setting switched to
GitHub Actions immediately before that exact merge. Pull-request validation
run `30701806996`, master admission run `30702234519`, and custom Pages run
`30702234546` passed. The custom deployment required no rollback, and public
entry points plus selected runtime documents matched the merged source bytes.

Production dispatch and later Phase 10 tasks remain separately controlled.

---

# DEC-070 — Split MTGO production into least-privilege artifact handoffs

Status: `Accepted`

## Context

Before P10-09, the one scheduled MTGO job fetched live inputs, generated
statistics, ran all validation, committed, pushed, and confirmed publication
with workflow-wide `contents: write`. Its validations were ordered correctly,
but fetch and build did not need repository-write authority and a failed stage
did not expose a durable job boundary within the workflow run.

The owner selected A+ public Git storage in DEC-068 and directed P10-09 to
split fetch, build, and publication without changing the daily public-Git
commit behavior. P10-10 and P10-11 remain separate tasks for resumability and
deduplicated failure issues.

## Decision

Keep one scheduled and manually dispatchable MTGO workflow, its master-only
guard, non-cancelling concurrency group, Python 3.12 runtime, registry-derived
format loops, and three validation layers. Split its responsibilities into:

1. a read-only `fetch` job that runs clean-checkout regression before live
   collection, snapshots the candidate baseline, and transfers the fetched
   inputs plus baseline through `mtgo-fetch-candidate`;
2. a read-only `build` job that verifies that immutable transfer, generates all
   existing products, runs candidate, repository, rule, and Schema validation,
   then transfers the validated allowed output through `mtgo-build-candidate`;
3. a `contents: write` `publish` job that verifies the validated-output digest,
   rejects paths outside `data/`, `stats/`, `reports/`, and `fetched.txt`, then
   performs the existing no-op, commit, push, and remote-master confirmation.

Both artifacts retain for one day. They are intra-run transfer objects, not a
new data store, durable archive, restart checkpoint, or permission grant. Each
job checks out the same immutable trigger SHA. No job receives issue, Pages,
OIDC, secret, storage-provider, or other unrelated permission.

## Consequences

The workflow exposes fetch, build, and publication as separately observable
steps and confines repository write access to the only step that can publish a
fully validated candidate. A transfer or validation failure prevents the
publish job from starting. DEC-072 subsequently adds the separately authorized
P10-11 issue-only notification boundary; normal Actions status and per-job
summaries remain the primary diagnostic record.

---

# DEC-071 — Resume only verified incomplete MTGO input collection

Status: `Accepted`

## Context

P10-09 made the MTGO fetch, build, and publication boundary explicit, but an
input-collection failure still discarded its runner-local progress at the end
of the run. Repeating a failed scheduled run could therefore repeat already
completed format collections even when the source code, configuration, and
master commit had not changed. The owner authorized P10-10 as the separate
resumability task, without authorizing a live production dispatch, a new data
store, a repository write, or P10-11 failure issues.

## Decision

The read-only fetch job records a versioned progress manifest after its clean
baseline is available. It defines every event-format and match-format operation
as `pending` or `complete`. An operation becomes complete only after its
existing collection command succeeds. If any planned operation fails, the job
finishes every remaining pending operation it can, fails overall, and uploads a
separate immutable `mtgo-fetch-checkpoint` artifact for seven days. That
artifact contains only the collected inputs, the clean baseline, the progress
manifest, and SHA-256 sums.

At the start of a later fetch run, `actions: read` may locate the newest
unexpired checkpoint only for the same `master` head SHA. The job then verifies
the artifact digest, accepted archive paths, repository identity, full commit,
and exact event/match plan before restoring it. It skips only manifest-complete
operations. Any mismatch, corruption, expiration, or absence fails closed to a
new clean collection; it never resumes a different code or configuration
version.

The normal one-day `mtgo-fetch-candidate` handoff remains the sole fetch input
to build. The checkpoint is not downloaded by build or publish, does not
contain generated statistics, and cannot lead to staging or publication. No
job gains `contents: write`, and P10-11 remains the sole owner of failure issue
creation.

## Consequences

An interrupted MTGO input collection can reuse successful work for up to seven
days while keeping the daily repository commit and public data architecture
unchanged. The checkpoint is intentionally temporary, bounded, and rejected
across code/configuration changes. Successful later work leaves an older
checkpoint to expire rather than granting additional deletion permission.

No statistical formula, source-selection rule, generated-data path, public
URL, front-end behavior, Pages configuration, storage provider, production-data
dispatch, or repository write is part of P10-10 local implementation.

No statistical formula, source-selection rule, event whitelist, generated-data
path, public URL, front-end behavior, Pages configuration, raw retention
policy, storage provider, or production-data commit changes during local
implementation. A real production dispatch remains separately owner-gated.

---

# DEC-072 — Deduplicate MTGO production failure issues by pipeline stage

Status: `Accepted`

## Context

The split production workflow already exposes failed fetch, build, and publish
jobs in GitHub Actions, and P10-10 retains incomplete input collection safely.
However, a recurring production failure had no durable, deduplicated work item.
Creating a new issue for every failed daily run would create noise, while giving
the collection, build, or publication jobs broad issue permission would weaken
their least-privilege boundary.

## Decision

Add one post-pipeline notification job. It runs only after a real `failure` in
fetch, build, or publish, selects the first failed stage in pipeline order, and
has only `issues: write`; it does not check out the repository or receive
`contents`, `actions`, Pages, OIDC, storage, or publication permission.

The job uses a stable hidden marker in an ordinary issue body to find an open,
non-pull-request issue for the selected stage. It creates that issue if absent;
otherwise it appends a compact update to the existing issue. The controlled
message contains only the stage name, immutable trigger SHA, and Actions run
link. It never copies raw exception text, source responses, request details,
credentials, or production data into an Issue.

Successful, skipped, and cancelled pipeline outcomes create no issue. A closed
failure issue is not reopened automatically; a later recurrence may create a
new issue. P10-11 does not dispatch a workflow or manufacture a failure for
live verification.

## Consequences

The owner receives one maintained open work item per active failure stage
without expanding any collection, build, or publication permission. The
notification job is itself observable in Actions and may fail visibly if GitHub
cannot record the notification; it cannot convert a failed production run into
a successful one. No statistic, source policy, generated output, public path,
front-end behavior, or durable data-store behavior changes.

---

# DEC-073 — Derive Melee workflow format from the verified whitelist

Status: `Accepted`

## Context

The manual Melee candidate workflow accepted an event ID but set its format to
`modern` unconditionally. The whitelist already contains each event's reviewed
Constructed format and the strict registry loader already rejects malformed,
unknown, disabled, and unverified entries. Keeping a separate hard-coded
workflow value could send a future approved non-Modern event through the wrong
rules and paths.

## Decision

Before any candidate baseline, retained-snapshot lookup, or live collection,
the workflow loads `configs/melee_events.yaml` through the existing strict
registry and calls `require_fetchable` for the supplied event ID. It exports
the resulting format only after confirming that the corresponding rule file is
present. All existing later workflow steps continue to use that one derived
`FORMAT` value.

The dispatch has no user-entered format input and no fallback value. A missing,
malformed, disabled, unverified, or unsupported entry stops before source
access. This decision does not add a whitelist event, enable an event, dispatch
the workflow, retain source responses, or alter the review-branch and manual
pull-request gates.

## Consequences

Future approved events can use their reviewed format without a second workflow
edit, while an event lacking a maintained rule file fails before it can fetch
or write candidate data. Existing Modern event `434455`, its protected bytes,
all statistical formulas, public paths, and front ends remain unchanged.

---

# DEC-074 — Package Python commands while retaining root-script compatibility

Status: `Accepted`

## Context

The project Python modules already live under `src/mtgmeta/`, but operators and
automation must set `PYTHONPATH=src` to use them as modules. Root-level scripts
remain referenced by tests and documentation, so removing or renaming them as
part of the packaging baseline would break established compatibility before the
Phase 11 legacy-entry-point review.

## Decision

Add a minimal `pyproject.toml` using setuptools, require Python 3.12 or newer,
and expose the existing catalog, MTGO, and Tabletop module entry points as
`mtgo-data-catalog`, `mtgo-data-mtgo`, and `mtgo-data-melee`. Include the
package's JSON alias data in the installation artifact.

Move only package-internal helpers that prevented installed execution into
`mtgmeta`: the public-schema helper and classification-report command logic.
Retain `public_contract.py` and `generate_classification_reports.py` at the
repository root as compatible entry points. The root report script preserves
its existing repository-root default and delegates to the installed package
implementation.

## Consequences

Operators may install the repository into a Python 3.12 virtual environment
and use supported commands without setting `PYTHONPATH`. Commands that read
repository configuration or data still require a repository checkout and an
explicit `--root .` where supported. Installation does not add credentials,
network calls, scheduled jobs, production-data changes, or a new build
framework. Root scripts remain until a separately authorized Phase 11 audit
and deletion decision.

---

# DEC-075 — Establish a narrow Ruff baseline for maintained package code

Status: `Accepted`

## Context

The first Ruff scan found 189 existing findings across root compatibility
scripts, tests, and package code, and would reformat 124 files. Treating that
as one mechanical task would obscure the P11-02 review and pull legacy-entry
point cleanup forward from its separately authorized Phase 11 work.

## Decision

Pin Ruff in the development dependencies and configure it for Python 3.12.
The initial CI baseline runs `python -B -m ruff check src` and selects only
the F rule family. This protects the maintained installable package against
undefined names and unused imports without prescribing a repository-wide
format or changing root-script compatibility behavior.

Remove two unused package imports. Preserve the four F821 findings in an
unreachable legacy self-test block with narrow inline `noqa` comments; the
module already raises before that block can run. The exception does not disable
F821 checks elsewhere in the package.

## Consequences

New F-family findings in maintained `src/` code now fail locally and in CI.
Root scripts, tests, E-style/layout rules, import sorting, and Ruff formatting
remain outside this task and require deliberate later scope. No production
data, statistic, public path, front-end source, workflow permission, or event
`434455` byte changes.

---

# DEC-076 — Establish a strict, narrow mypy baseline for stable shared modules

Status: `Accepted`

## Context

The shared card-name, deck-normalization, rule-validation, and classification
modules serve both MTGO and Tabletop processing. They already expose typed
interfaces, but Python alone cannot verify that values validated from external
documents are narrowed before they become internal rule identifiers.

The broader package still contains legacy compatibility scripts and modules
whose imports would create unrelated findings. Treating every existing module
as typed, or silencing the results with global ignores, would not establish a
meaningful baseline.

## Decision

Pin mypy 2.3.0 and its direct transitive dependencies in the development
requirements. Run mypy in strict mode on exactly these four stable shared
modules:

- `src/mtgmeta/card_names.py`;
- `src/mtgmeta/deck.py`;
- `src/mtgmeta/rules.py`;
- `src/mtgmeta/classifier.py`.

Set `follow_imports = "skip"` so imports outside that explicit initial scope
are not silently treated as part of the baseline. Preserve strict checking for
every listed module. Add the same `python -B -m mypy` command to the existing
read-only CI static-validation job.

Use a type guard for validated non-empty identifiers and an explicit optional
subtype branch. These changes clarify existing validation results without
changing classification behavior.

## Consequences

The selected shared modules now fail locally and in CI when their strict type
contract regresses. Expanding the typed surface, changing imported modules,
or introducing an ignore baseline requires a separately reviewed task. No
production data, statistic, public path, front-end source, workflow permission,
or event `434455` byte changes.

---

# DEC-077 — Use monthly review-only Dependabot proposals

Status: `Accepted`

## Context

The owner declined P11-04 after measurement showed that whole-package
coverage instrumentation would extend the required validation path to about
twenty minutes. The project still needs a small, reviewable mechanism to
surface maintenance updates for its pinned Python dependencies and GitHub
Actions references.

## Decision

Add the minimum Dependabot version-update configuration for the repository
root: one monthly `pip` entry and one monthly `github-actions` entry. Do not
configure grouping, auto-merge, private registries, assignees, labels, target
branches, or special permissions. Dependabot may open proposal pull requests;
each remains subject to ordinary CI and explicit human review and merge.

## Consequences

This decision does not install or upgrade dependencies, change production
workflows, grant repository write permissions, dispatch workflows, publish
data, or alter product behavior. P11-04 remains skipped and may be reconsidered
only as a separately authorized CI-economy task.

---

# DEC-078 — Defer draw-adjusted metric retirement to Phase 19

Status: `Accepted`

## Context

The Phase 8 production front end now presents the declared literal method:
normal played draws remain in the valid-match denominator and contribute zero
wins. MTGO and Tabletop generators, public Schemas, fixtures, retained legacy
JavaScript, and protected event `434455` nevertheless preserve older
draw-adjusted compatibility fields that count each normal draw as half a win.

P11-09 proposed extracting shared metric APIs while preserving both source
products' current bytes. The owner selected eventual removal of the
draw-adjusted calculation because it is not part of the final product's win-rate
meaning. Extracting that calculation now would invest in an obsolete contract
without advancing its safe removal.

## Decision

Skip P11-09. Do not create a shared API for the draw-adjusted compatibility
calculation and do not change current production data, Schemas, statistical
outputs, front-end behavior, or protected `434455` bytes during Phase 11.
P11-10 becomes the next separately authorized development task. P11-10 through
P11-12 retain their planned production-resource protection and legacy-entry
audit sequence.

Make draw-adjusted metric retirement the first compatibility-migration task in
Phase 19. That task must remove the calculation and obsolete fields from both
source products under an explicit Schema version, regenerate every affected
public document, update the protected `434455` manifest and rollback evidence,
remove retained legacy JavaScript dependencies, and pass full cross-product,
Schema, committed-baseline, and real-browser regression. It must not silently
assign the literal method to a field whose published meaning was draw-adjusted.

Until that separately authorized migration is accepted and published, existing
compatibility fields retain their historical meaning and bytes. No new product,
generator, or consumer may depend on them.

---

# DEC-079 - Version the 434455 compatibility closure for Selesnya Eldrazi Ramp

Status: `Accepted`

## Context

The 2026-08-02 MTGO production run stopped before publication because two
Selesnya Eldrazi Ramp decks selected the maintained `eldrazi-ramp` parent but
no subtype. The strict classifier correctly rejected that residual state.

Adding the explicit `eldrazi-ramp/selesnya` taxonomy leaf changes the rule
provenance embedded in the retained event `434455` classification overlay and
the complete hierarchy enumerated by its derived documents. The event's raw
snapshot and normalized event remain immutable, but their derived exact bytes
must not be changed silently under the version `1.0.0` compatibility contract.

## Decision

The owner authorizes this narrow compatibility migration. Add the explicit
Selesnya Eldrazi Ramp subtype and regenerate derived Modern documents from
their committed inputs using the prior MTGO statistics cutoff. Do not fetch,
retain, or publish new source responses; do not change statistical formulas,
schemas for product documents, front-end code, or public paths.

Advance `tests/fixtures/melee/434455_compatibility_manifest.json` and its
schema contract from `1.0.0` to `1.1.0`, recording the new deterministic bytes
for the classification overlay, opportunity ledger, and five event outputs.
The raw snapshot, normalized event, selected catalog projections, and every
event-performance sample remain unchanged. The regenerated MTGO windows add
only the zero-count `eldrazi-ramp/selesnya` hierarchy leaf.

## Consequences

Future exact-byte validation uses the explicit version `1.1.0` contract. The
same previously unclassified Selesnya deck signature is now classified without
weakening the residual-subtype stop for future unknown Eldrazi Ramp variants.

## Consequences

Phase 11 avoids throwaway abstraction work and retains its no-production-change
boundary. The current website remains unchanged because it already uses literal
records. Public JSON and unknown external consumers keep their present contract
until the deliberate versioned migration. Phase 19 must treat the removal as a
breaking data-contract change with explicit owner acceptance and a verified
rollback path, not as routine code cleanup.

---

# DEC-080 — Retire audited root compatibility entry points

Status: `Accepted`

## Context

P11-11 verified installed package replacements and current callers for all 26
repository-root Python files. The owner accepted its recommendation to keep
nine active workflow or publication tools, delete nine compatibility wrappers
and seven obsolete one-off scripts, remove two outputs of retired
identity-bearing diagnostics, and relocate one maintained aggregate-only
quality validator.

## Decision

Perform that exact cleanup in P11-12. Current tests and README commands must use
the installed commands or `mtgmeta` package APIs before the corresponding root
files are removed. Move `validate_standard_quality.py` to `tools/` and preserve
its frozen result exactly. Keep the Phase 3 entry-point inventory as an
explicitly historical snapshot instead of asserting that retired files still
exist.

Retain the nine active root workflow and publication tools identified by
P11-11. Do not change workflows, production data, generated statistics,
Schemas, public paths, either front end, or protected event `434455` bytes.

## Consequences

Supported operations have one package-command boundary and live tests no
longer depend on deleted wrappers. Historical audits continue to name former
commands accurately. An unrecorded external caller of a deleted root script
must migrate to the documented installed command; the parent commit and the
P11-12 pull-request diff remain the exact rollback source.

---

# DEC-081 — Separate live status from byte-preserved history

Status: `Accepted`

## Context

`docs/STATUS.yaml` had grown to about 286 KB because current authorization,
completed phase records, resolved blockers, maintenance evidence, and old task
results shared one file. README and tool-specific agent guides also repeated
authoritative scope and statistics or retained stale phase snapshots. That made
the small set of current facts harder to find and increased the risk that an
agent would follow obsolete state.

P11-13 must reduce that duplication without deleting evidence, weakening the
mandatory `AGENTS.md` entry point, changing operational commands, or altering
product behavior.

## Decision

Keep `docs/STATUS.yaml` as a small live-state document containing the current
phase, current task and authorization, recent completion handoff, blockers,
deferred decisions, active governance controls, and prohibited actions.

Preserve the complete pre-P11-13 STATUS byte-for-byte as
`docs/history/STATUS-2026-08-04-pre-P11-13.yaml`, identify its source commit and
SHA-256 in `docs/history/README.md`, and mark the directory non-authoritative.
Historical snapshots can explain earlier state but can never authorize work.

Keep `AGENTS.md` as the mandatory stable operating guide and authoritative
document router. Make `CLAUDE.md` and `.github/copilot-instructions.md` thin
adapters that point back to it instead of copying project rules or current
phase text. Keep README focused on current product orientation and supported
operator commands; detailed scope, formulas, architecture, history, and
workflow gates remain in their authoritative documents.

## Consequences

Current authorization is visible in an approximately 10 KB file while every
prior STATUS field remains recoverable from the byte-preserved snapshot. Agent
tools share one stable instruction source and cannot rely on a stale phase
copy. P11-13 changes no code, workflow, generated or source data, statistical
behavior, Schema, public path, front-end source, or protected event `434455`
byte. Cross-document fact consistency remains the separate P11-14 task.

---

# DEC-082 - Degrade bounded Videre source outages without suppressing MTGO updates

Status: `Accepted`

## Context

Scheduled production run `30853542523` exhausted three bounded attempts for
multiple Standard and Modern Videre requests because the third-party service
returned HTTP 500. The fetch job correctly prevented incomplete matchup data
from being presented as complete, but it also suppressed unrelated official
event, metagame, high-score, Top 8, Weekly Pickup, metadata, catalog, and
completeness updates. Manual run `30902426056` succeeded after Videre recovered.

The existing `videre-range-coverage-v1` contract already distinguishes usable
archives from admitted events with missing archives and exposes the counts,
event IDs, and resulting completeness rate to the browser. Missing matchup
source data therefore need not be converted to zero or hidden to permit other
product data to advance.

## Decision

After existing bounded retries, retryable Videre HTTP responses, timeouts, and
transport failures are source-unavailable warnings. The affected events create
no new matchup archive, remain visible as `missing` in completeness output, and
do not make the MTGO fetch command fail. Successfully collected inputs and all
other generated MTGO products may continue through the existing candidate
validation and publication boundary.

Do not generalize this exception. Non-retryable HTTP responses, malformed JSON
or response structures, invalid event identities, filesystem failures, and
unclassified exceptions remain fatal. Matchup generation continues to use
only usable retained archives and never invents zero-match rows for missing
events. The next scheduled run retries any event that still lacks an archive.

## Consequences

A temporary Videre outage can make matchup statistics less complete while the
rest of the MTGO product remains current. The front end already presents the
available, expected, deferred, missing, excluded, and completeness values, so
no front-end or Schema change is required. Workflow logs distinguish source
unavailability from fatal errors, and literal Markdown backticks in job
summaries no longer trigger unintended shell command substitution.
