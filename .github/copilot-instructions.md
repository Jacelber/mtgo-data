# GitHub Copilot Repository Instructions

## Read the authoritative documentation

Before suggesting repository-wide changes, read:

1. `AGENTS.md`
2. `docs/PROJECT_SCOPE.md`
3. `docs/STATISTICS_SPEC.md`
4. `docs/DATA_ARCHITECTURE.md`
5. `docs/ROADMAP.md`
6. `docs/DECISIONS.md`
7. `docs/STATUS.yaml`

Use `docs/STATUS.yaml` to determine the current phase and next approved task.

Do not treat `PROJECT_NOTES.md` as the current specification. It is historical context.

Existing code represents the current implementation and may contain legacy Standard-only assumptions.

---

## Product boundaries

This repository has two separate product areas:

- MTGO Environment Trends
- Tabletop Major Events

The tabletop product may use Melee as a source.

MTGO and Melee may share reusable classification and metrics code, but they must keep separate:

- source data;
- normalized event data;
- generated statistics;
- catalogs;
- user-facing product behavior.

Never suggest merging MTGO and Melee results into one metagame statistic.

---

## Current phase control

Always inspect `docs/STATUS.yaml` before suggesting implementation work.

When the project is in Phase 0:

- suggest documentation changes only;
- do not refactor production Python code;
- do not implement Melee fetching;
- do not add Pauper processing;
- do not split production `index.html`;
- do not redesign GitHub Actions.

Do not suggest work from a later roadmap phase unless the project owner explicitly approves it.

---

## Python guidance

Prefer:

- Python 3.12-compatible code;
- small focused modules;
- explicit function inputs and outputs;
- `pathlib` for new path handling;
- deterministic output;
- descriptive exceptions;
- structured logging where appropriate;
- type hints for new reusable code;
- tests for new statistical behavior.

Avoid:

- format-specific copies of complete pipelines;
- hidden global state;
- undocumented path assumptions;
- silent exception handling;
- manually edited generated output;
- new dependencies without updating dependency files.

Keep temporary compatibility with verified legacy entry points until their replacements are tested.

---

## Classification guidance

Classification logic is shared across MTGO and Melee for the same format.

Rules must support:

- stable archetype IDs;
- stable rule IDs;
- explicit priorities;
- validation;
- Unknown reporting;
- conflict reporting.

Do not use YAML order as an undocumented conflict resolution method.

Do not silently resolve equal-priority conflicts.

When classification behavior changes, suggest corresponding updates to:

- fixtures;
- tests;
- Unknown reports;
- conflict reports;
- documentation.

---

## Statistical guidance

Do not invent formulas from nearby code or UI labels.

Use `docs/STATISTICS_SPEC.md` as the statistical authority.

Preserve these established principles:

- Draft rounds do not count in Constructed deck-performance statistics.
- Intentional draws reported as `0-0-3` do not count in played-match win rate or matchup matrices.
- Byes do not count in played-match win rate or matchup matrices.
- Ordinary unplayed rounds after a drop remain zero-point scheduled opportunities for applicable theoretical-round metrics.
- Official awarded wins after a confirmed Top 8 lock are not real played wins.
- Playoffs do not belong in primary Swiss performance metrics.
- Day 1, Day 2, and all-Constructed scopes must remain distinguishable.
- Mixed-event Day 2 data requires sample-size and selection-bias context.
- Multi-event matchup aggregation uses raw counts rather than averaging percentages.
- Display percentages should retain reproducible raw numerators and denominators.

A statistical change should include, where applicable:

- updated specification;
- updated decision record;
- updated tests;
- updated schema;
- updated schema version;
- updated front-end label.

---

## Melee event guidance

Do not suggest unrestricted Melee crawling.

Only events enabled in `configs/melee_events.yaml` may be processed.

Approved event categories and exclusions are defined in:

- `docs/PROJECT_SCOPE.md`
- `docs/DECISIONS.md`

Melee event structures are:

- `constructed_day2`
- `constructed_single_stage`
- `mixed`

Mixed events require explicit identification of:

- Draft rounds;
- Constructed rounds;
- playoff rounds;
- unknown rounds.

Unknown rounds and unknown results must be reported and excluded until reviewed.

---

## Data guidance

Keep these categories separate:

- manually maintained configuration;
- raw source data;
- normalized event data;
- generated statistics;
- quality reports;
- front-end assets.

Do not suggest manual changes to generated JSON as a permanent fix.

Generated data must be reproducible from source data and configuration.

Important normalized and generated structures should have explicit schema versions.

When changing a data structure, suggest:

- schema updates;
- validation updates;
- fixture updates;
- consumer updates;
- compatibility or migration handling.

---

## Front-end guidance

Keep the product pages separate:

- `/index.html` for MTGO Environment Trends;
- `/melee/index.html` for Tabletop Major Events.

The first split of the monolithic `index.html` is a behavior-preservation task.

During that split, do not change:

- appearance;
- existing labels;
- language behavior;
- public JSON paths;
- controls;
- charts;
- decklist behavior;
- Weekly Pickup behavior;
- matchup behavior.

Do not introduce a mandatory front-end framework, bundler, or build step unless explicitly approved.

Maintain GitHub Pages compatibility.

---

## GitHub Actions guidance

Use least-privilege permissions.

CI should normally use:

- read-only repository contents permission.

Only a workflow that must commit generated updates may use:

- repository contents write permission.

Every update workflow should have:

- explicit concurrency;
- deterministic dependency installation;
- tests;
- validation;
- useful workflow summaries;
- publication blocked after validation failure.

Do not delete or disable an existing production workflow before its current responsibility is verified.

---

## Testing and validation

When suggesting new behavior, also suggest the applicable tests.

Relevant checks may include:

- pytest;
- rule validation;
- schema validation;
- Standard regression comparison;
- Unknown report review;
- conflict report review;
- data-quality report review;
- front-end smoke tests.

Do not describe a task as complete only because code compiles.

A task is complete only after applicable behavior and output are verified.

---

## Git safety

Do not suggest direct development on `master`.

Before repository edits, check:

- current branch;
- working-tree status;
- unexplained local changes.

Do not suggest deleting legacy code until replacements are verified.

Do not suggest committing:

- tokens;
- credentials;
- cookies;
- private data;
- environment secrets.

Avoid combining documentation, refactoring, statistical changes, generated data, front-end redesign, and workflow redesign in one large commit.

---

## Guidance for this project owner

The project owner does not have a programming background.

When generating instructions:

- provide one task at a time;
- state the purpose;
- state the exact target path;
- provide complete copyable content when needed;
- provide exact commands;
- describe expected output;
- provide verification steps;
- wait for confirmation before continuing.

Avoid nested Markdown code fences inside a larger copyable document.

If a command fails, request the complete output before suggesting unrelated changes.

---

## Scope-change warning

Require explicit project-owner confirmation before suggesting:

- merged MTGO and Melee statistics;
- new event categories outside the whitelist policy;
- unrestricted Melee discovery;
- team-event inclusion;
- pure Limited event inclusion;
- changed intentional-draw handling;
- changed bye handling;
- awarded wins treated as played wins;
- Draft included in Constructed statistics;
- playoffs used as the primary performance sample;
- a changed format-development order;
- Vintage enabled before its decision gate;
- a mandatory front-end framework;
- broken public JSON paths;
- unverified legacy entry-point removal.

Approved scope changes must be recorded in `docs/DECISIONS.md`.
