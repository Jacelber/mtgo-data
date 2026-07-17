# AGENTS.md

## Purpose

This file is the mandatory entry point for any AI assistant, coding agent, or human developer working on this repository.

Before changing code, data structures, statistics, workflows, or front-end behavior, read the authoritative documents listed below.

Do not infer the project scope only from existing legacy code. The repository is being reorganized from a Standard-only MTGO project into a multi-format constructed-data project with separate MTGO and Melee products.

---

## Authoritative document order

Read the following files in this order:

1. `AGENTS.md`
2. `docs/PROJECT_SCOPE.md`
3. `docs/STATISTICS_SPEC.md`
4. `docs/DATA_ARCHITECTURE.md`
5. `docs/ROADMAP.md`
6. `docs/DECISIONS.md`
7. `docs/STATUS.yaml`

Additional instructions:

- `PROJECT_NOTES.md` is a historical record and is not the current specification.
- Existing code describes the current implementation, not necessarily the intended final architecture.
- If documents conflict, use the document appearing earlier in the list above.
- If a current user instruction conflicts with the established project scope, stop and request explicit confirmation before changing the scope.
- Do not silently redefine statistical metrics.

Some documents in the list may be added progressively during Phase 0. Until Phase 0 is complete, do not begin feature refactoring unless explicitly instructed.

---

## Project objective

The project analyzes constructed Magic: The Gathering tournament data.

It has two separate product areas:

1. **MTGO Environment Trends**
2. **Tabletop Major Events**

The second product uses selected Melee tournament data, but the user-facing product name should be “Tabletop Major Events” rather than simply “Melee.”

The project should eventually support these constructed formats:

- Standard
- Pauper
- Modern
- Pioneer
- Legacy
- Vintage, if approved later

The intended format-development order is:

1. Preserve Standard as the regression baseline.
2. Generalize the existing Standard-only MTGO pipeline.
3. Implement Pauper for MTGO and the selected Paupergeddon Melee event.
4. Implement Modern.
5. Implement Pioneer.
6. Implement Legacy.
7. Decide whether to implement Vintage.

---

## MTGO and Melee separation

MTGO and Melee may share reusable classification and statistical utility code, but their source data, normalized event data, generated statistics, and front-end product behavior must remain separate.

Do not merge MTGO and Melee event results into one statistic.

Shared capabilities may include:

- card-name normalization;
- archetype IDs;
- archetype classification;
- YAML rule loading;
- rule priority handling;
- rule conflict detection;
- Unknown classification reporting;
- common win-rate calculations;
- confidence intervals;
- high-score threshold helpers;
- reusable deck and card utilities.

MTGO-specific capabilities include:

- rolling time ranges;
- MTGO event fetching;
- weekly metagame statistics;
- high-score and Top 8 statistics;
- average decklists;
- deck-construction deviation;
- Weekly Pickup;
- Videre-based matchup data.

Melee-specific capabilities include:

- manually whitelisted events;
- standings and round parsing;
- Day 1 and Day 2 separation;
- mixed Draft and Constructed phase handling;
- drop, bye, intentional-draw, no-show, and awarded-win handling;
- per-event statistics;
- optional same-format multi-event matchup aggregation.

---

## Melee event inclusion policy

Do not automatically crawl all Melee tournaments.

Only collect events explicitly registered in:

`configs/melee_events.yaml`

Target event categories are:

- World Championships;
- Pro Tours;
- Regional Championships;
- Magic Spotlight Series;
- Paupergeddon main events;
- Eternal Weekend Legacy main events;
- Eternal Weekend Vintage main events, if Vintage is enabled later.

Exclude:

- team events;
- pure Limited events;
- side events;
- qualifiers not explicitly approved;
- unrelated local tournaments;
- events not present in the whitelist.

Mixed-format events are allowed only when their Constructed rounds can be identified reliably.

---

## Melee statistical modes

Melee events must be assigned one of these structures:

1. `constructed_day2`
   - Pure Constructed event with a Day 2 cut.

2. `constructed_single_stage`
   - Pure Constructed event without a separate Day 2 cut.

3. `mixed`
   - Draft plus Constructed, such as a Pro Tour or World Championship.

Do not apply one event structure’s statistical rules to another structure without an explicit specification change.

---

## Mixed-format event principles

For mixed Draft and Constructed events:

- Draft results must not be included in Constructed deck-performance statistics.
- Overall standings points must not be treated as Constructed deck points.
- Day 2 qualification must not be presented as a pure deck-performance conversion metric because qualification is influenced by Draft results.
- Every round must be labeled as one of:
  - `draft`
  - `constructed`
  - `playoff`
  - `unknown`
- Unknown round types must be reported and reviewed instead of silently counted.

The product should provide separate scopes where data permits:

- Day 1 Constructed;
- Day 2 Constructed;
- all Constructed Swiss rounds;
- playoffs as contextual results only.

For mixed events:

- Day 1 Constructed metrics measure the broad initial field.
- Day 2 Constructed metrics measure the qualified field and must show sample size and selection-bias warnings.
- Combined Constructed win rate may include Day 1 and Day 2 real Constructed Swiss matches.
- Matchup matrices should allow switching between all Constructed Swiss rounds, Day 1 only, and Day 2 only.
- Day 2 average score must not be shown as the only measure of Day 2 deck performance.

---

## Match result handling

The detailed formulas belong in `docs/STATISTICS_SPEC.md`.

At minimum, preserve these principles:

- Real wins and losses count toward points, win rate, and matchup statistics.
- Normal played draws count toward points and may count as half a win in win-rate calculations.
- Intentional draws reported as `0-0-3` award standings points but are excluded from win-rate and matchup calculations.
- Byes may award standings points but are excluded from win-rate and matchup calculations.
- No-shows are excluded and must be reported.
- Dropped or unplayed scheduled rounds contribute zero points when the applicable metric uses theoretical rounds.
- Official awarded wins after a player has locked Top 8 must not be treated as played matches.
- Awarded-win rounds are excluded from win-rate and matchup statistics.
- Awarded-win rounds may be exempted from effective theoretical rounds when the official event structure confirms that the player no longer had to play.
- Draft rounds are excluded from Constructed statistics.
- Playoff matches are excluded from primary Swiss performance statistics and the primary matchup matrix.

These cases must be represented explicitly in normalized data. Do not rely only on final standings totals.

---

## Front-end boundaries

The current `index.html` is the MTGO product and must continue working during refactoring.

The intended top-level navigation is:

- MTGO Environment Trends
- Tabletop Major Events

The intended front-end structure is:

- `/index.html` for MTGO;
- `/melee/index.html` for tabletop major events;
- shared static assets under `/assets/`.

The existing monolithic `index.html` must be split before major multi-format front-end expansion.

The split must preserve current behavior, appearance, data paths, and GitHub Pages compatibility. Do not introduce a mandatory JavaScript build framework unless separately approved.

---

## Engineering requirements

Before major feature expansion, the project must add or improve:

- `README.md`;
- code license and data notice;
- production and development dependency lists;
- pytest tests;
- rule validation;
- archetype IDs;
- rule IDs;
- explicit rule priorities;
- classification conflict reports;
- Unknown classification reports;
- JSON Schemas with schema versions;
- CI checks;
- GitHub Actions permissions using least privilege;
- workflow concurrency controls;
- useful workflow summaries and failure reporting;
- regression protection for the current Standard page and data pipeline.

Generated data and manually maintained source configuration must be distinguishable.

Do not manually edit generated statistics as a substitute for fixing the generator.

---

## Git and change-safety rules

- Do not make development changes directly on `master`.
- Use a dedicated branch for each phase or focused task.
- Preserve the current Standard implementation until regression checks exist.
- Prefer small, reviewable commits.
- Do not combine documentation, large refactoring, new data ingestion, and front-end redesign in one commit.
- Before committing, run the checks required by the current phase.
- Do not delete legacy entry points until replacements are verified.
- Do not rename public data paths without a compatibility plan.
- Do not commit secrets, credentials, access tokens, or private user data.
- Do not overwrite unexplained local changes.
- If repository state is not clean, inspect it before proceeding.

---

## Required task format for AI assistants

When guiding a non-programmer, work one task at a time.

For each task, provide:

1. purpose;
2. exact target file path;
3. exact operations;
4. complete copyable file content when applicable;
5. commands to run;
6. expected output;
7. verification steps;
8. commit commands;
9. a clear stop point for user confirmation.

Do not provide several large file-creation tasks at once unless explicitly requested.

If a command fails, ask for the complete error output before proposing unrelated changes.

---

## Documentation maintenance

At the completion of every development phase:

- update `docs/STATUS.yaml`;
- update `docs/ROADMAP.md` if phase status changed;
- add a record to `docs/DECISIONS.md` if a scope or statistical decision changed;
- update schemas when normalized or output data structures change;
- update tests when statistical behavior changes;
- update README instructions when commands or workflows change.

A code change that alters statistics without updating the relevant specification and tests is incomplete.

---

## Current phase source of truth

The current implementation phase is not hard-coded in this file.

Before starting or proposing any task, read `docs/STATUS.yaml` and confirm:

- `current_phase`;
- `next_approved_task`;
- active blockers, if any;
- `prohibited_next_actions`;
- the current working branch.

`AGENTS.md` defines stable repository-wide operating rules. `docs/STATUS.yaml` is authoritative for current phase, task completion state, known blockers, and the next approved action.

Do not begin a later phase or an unapproved task unless the project owner explicitly approves the change and the project status is updated.
