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

## Statistical warning thresholds

Status: `Proposed`

The project still needs exact thresholds for:

- low matchup sample warnings;
- Day 1 versus all-Constructed difference warnings;
- minimum sample size for confidence intervals;
- event publication quality failures.

These values should be finalized in `docs/STATISTICS_SPEC.md` and covered by tests.

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

Only committed `CMODERN` event records may enter the baseline. Files whose embedded format is `CPREMODERN` or another format remain excluded even if stored under `data/modern/`. The frozen fixture must be de-identified and contain no participant, account, standing, event, or source identifiers.

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
