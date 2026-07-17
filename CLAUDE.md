# Claude Project Instructions

## Mandatory first step

Before analyzing, planning, editing, or generating code for this repository, read:

1. `AGENTS.md`
2. `docs/PROJECT_SCOPE.md`
3. `docs/STATISTICS_SPEC.md`
4. `docs/DATA_ARCHITECTURE.md`
5. `docs/ROADMAP.md`
6. `docs/DECISIONS.md`
7. `docs/STATUS.yaml`
8. `docs/DEVELOPMENT_WORKFLOW.md`

These documents define the authoritative project scope, statistics, architecture, development order, confirmed decisions, and current progress.

Do not use this file as a replacement for those documents.

`docs/DEVELOPMENT_WORKFLOW.md` defines isolation, approval, publication, and stop rules. `docs/STATUS.yaml` controls project pause and task authorization.

---

## Historical information

`PROJECT_NOTES.md` is historical context.

It may explain how the current repository evolved, but it is not the current specification.

Existing code also describes the current implementation rather than the complete approved target architecture.

If historical notes or legacy code conflict with the authoritative documents, follow the authoritative documents.

Do not silently resolve a genuine conflict. Report it and request project-owner confirmation.

---

## Project summary

This repository analyzes Constructed Magic: The Gathering tournament data.

It contains two separate product areas:

1. MTGO Environment Trends
2. Tabletop Major Events

The tabletop product may use Melee as a data source.

MTGO and Melee may share classification logic and reusable statistical utilities, but they must keep separate:

- source data;
- normalized data;
- generated statistics;
- event catalogs;
- front-end behavior.

Never merge MTGO and Melee results into one metagame statistic.

---

## Current development state

Read `docs/STATUS.yaml` before starting work.

At the time this file was created, the project was in:

**Phase 0 — Authoritative documentation**

During Phase 0:

- create and review documentation only;
- do not refactor the production Standard pipeline;
- do not implement the shared classifier;
- do not add MTGO Pauper;
- do not fetch Melee events;
- do not generate Paupergeddon statistics;
- do not split the production `index.html`;
- do not change production GitHub Actions behavior.

The current phase may change later. Always use `docs/STATUS.yaml` rather than relying only on the phase written above.

---

## Required development behavior

Before changing a file:

1. identify the current phase;
2. confirm that the requested change belongs to that phase;
3. inspect the existing file and related tests;
4. identify whether the file is manually maintained or generated;
5. check whether the change affects public paths, statistics, schemas, or automation;
6. present a small implementation plan;
7. avoid unrelated changes.

After changing a file:

1. inspect the diff;
2. run applicable tests;
3. run rule validation where applicable;
4. run schema validation where applicable;
5. check for unintended Standard regressions;
6. update documentation when behavior changed;
7. update `docs/STATUS.yaml` when task status changed.

Do not edit generated JSON manually as a substitute for changing its generator.

---

## Instructions for guiding the project owner

The project owner does not have a programming background.

When providing implementation guidance:

1. give one task at a time;
2. explain the purpose;
3. give the exact target path;
4. provide complete copyable file content when needed;
5. provide exact commands;
6. describe expected output;
7. provide verification commands;
8. provide commit commands only when the task is ready to commit;
9. stop and wait for confirmation before the next task.

Do not provide several large file-creation tasks in one response unless explicitly requested.

Do not assume that an error can be ignored.

If a command fails, request the complete command output before proposing unrelated changes.

Avoid nested Markdown code fences in copyable documents because they may break the copy region.

---

## Git safety rules

Do not develop directly on `master`.

Before editing:

- check the current branch;
- check `git status`;
- do not overwrite unexplained local changes.

Use focused branches and commits.

Do not combine these in one large commit unless explicitly approved:

- documentation;
- architecture refactoring;
- new event ingestion;
- statistical changes;
- generated data;
- front-end redesign;
- workflow redesign.

Do not delete legacy scripts until their replacements are verified.

Do not break existing public JSON paths without an approved compatibility plan.

Do not commit:

- access tokens;
- credentials;
- cookies;
- private data;
- environment secrets.

---

## Statistical change control

Do not invent or silently alter statistical definitions.

Before changing statistical behavior, read:

- `docs/STATISTICS_SPEC.md`
- relevant entries in `docs/DECISIONS.md`

A statistical behavior change is incomplete unless it also includes, where applicable:

- updated specification;
- updated decision record;
- updated tests;
- updated JSON Schema;
- updated output schema version;
- updated front-end labels;
- updated `docs/STATUS.yaml`.

Important accepted principles include:

- Draft rounds do not count in Constructed deck statistics.
- Intentional draws reported as `0-0-3` do not count in played-match win rate or matchup matrices.
- Byes do not count in played-match win rate or matchup matrices.
- Ordinary unplayed rounds after a drop remain zero-point theoretical opportunities for applicable average-point metrics.
- Official awarded wins after a confirmed Top 8 lock are not played wins.
- Playoffs are excluded from primary Swiss performance statistics.
- Day 2 mixed-event results require sample-size and selection-bias context.
- Multi-event matchup aggregation adds raw counts rather than averaging percentages.

The detailed formulas in `docs/STATISTICS_SPEC.md` are authoritative.

---

## Classification change control

Classification is shared across MTGO and Melee for the same format.

Do not create source-specific duplicate archetype identities unless explicitly approved.

Classification rules must use:

- stable archetype IDs;
- stable rule IDs;
- explicit priorities;
- validation;
- Unknown reporting;
- conflict reporting.

Do not rely on YAML file order as an undocumented tie-breaker.

Do not silently resolve equal-priority conflicts.

When changing classification rules:

1. identify affected formats;
2. run known-deck fixtures;
3. run negative fixtures;
4. inspect Unknown changes;
5. inspect conflict changes;
6. compare against the approved baseline;
7. report classification changes clearly.

---

## Melee event restrictions

Do not fetch arbitrary Melee events.

Only events enabled in `configs/melee_events.yaml` may be processed.

Approved categories are defined in `docs/PROJECT_SCOPE.md` and `docs/DECISIONS.md`.

Do not include unapproved:

- team events;
- pure Limited events;
- side events;
- local events;
- qualifiers;
- events absent from the whitelist.

Mixed events require explicit round-phase identification.

Unknown event phases must be reported and excluded until reviewed.

---

## Front-end restrictions

The MTGO and tabletop products must remain separate.

Use:

- `/index.html` for MTGO Environment Trends;
- `/melee/index.html` for Tabletop Major Events.

The initial `index.html` split is a preservation task, not a redesign task.

During the initial split, preserve:

- appearance;
- labels;
- language behavior;
- JSON paths;
- controls;
- charts;
- decklist behavior;
- Weekly Pickup;
- matchup behavior;
- GitHub Pages compatibility.

Do not introduce a mandatory build system, bundler, or front-end framework unless explicitly approved.

---

## GitHub Actions restrictions

Workflow changes must use least-privilege permissions.

CI should normally use read-only repository contents permission.

Only workflows that must commit generated updates may use contents write permission.

Every update workflow must define explicit concurrency behavior.

Do not disable or delete an existing production workflow until its current role is verified.

Do not allow failed validation to publish incomplete or malformed generated data.

---

## Scope-change procedure

Stop and request explicit project-owner confirmation before:

- merging MTGO and Melee statistics;
- adding event categories outside the approved policy;
- enabling unrestricted Melee event discovery;
- including team or pure Limited events;
- changing intentional-draw handling;
- changing bye handling;
- treating awarded wins as played wins;
- counting Draft in Constructed statistics;
- using playoffs as the primary performance sample;
- changing the approved format order;
- enabling Vintage before its decision gate;
- introducing a mandatory front-end framework;
- breaking public JSON paths;
- removing unverified legacy entry points.

After approval, update:

- `docs/DECISIONS.md`;
- the affected specification;
- tests;
- schemas where applicable;
- `docs/STATUS.yaml`.

---

## Completion standard

A task is not complete merely because code was written.

A task is complete only when:

- requested output exists;
- applicable tests pass;
- validation passes;
- regressions are checked;
- data-quality issues are visible;
- documentation is consistent;
- the diff is reviewed;
- task status is updated;
- the project owner confirms completion when required.

When uncertain, prefer stopping with a precise explanation over making an undocumented assumption.
