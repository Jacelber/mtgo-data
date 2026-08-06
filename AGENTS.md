# AGENTS.md

## Purpose

This file is the mandatory entry point for every AI assistant, coding agent,
and developer working on this repository. It defines stable operating rules;
it does not duplicate the full product, statistics, architecture, or current
task specifications.

Before analyzing or changing the repository, always read `AGENTS.md`,
`docs/STATUS.yaml`, the current task and phase subsections of
`docs/ROADMAP.md`, and the relevant Gate and authorization sections of
`docs/DEVELOPMENT_WORKFLOW.md`. Then expand the reading set according to the
approved paths and artifact impact:

- read `docs/PROJECT_SCOPE.md` for product-scope or navigation work;
- read `docs/STATISTICS_SPEC.md` for statistical code, formulas, semantics, or
  statistical artifacts;
- read `docs/DATA_ARCHITECTURE.md` for data, Schemas, public paths, production,
  privacy, or retention boundaries; and
- read only the directly relevant entries in `docs/DECISIONS.md`.

Read a wider authoritative set when an authoritative document itself changes,
the impact is unclear, or the task requires the highest-strength process. A
file is not low risk merely because it is under `docs/`. When multiple
documents apply, authority remains, in order: `AGENTS.md`, project scope,
statistics specification, data architecture, roadmap, decisions, status, then
development workflow. `PROJECT_NOTES.md` and files under `docs/history/` are
historical evidence, not current specifications. Existing code describes the
current implementation, not necessarily the approved target.

`docs/STATUS.yaml` is the live source of truth for the current phase, current
task, blockers, authorization, and prohibited next actions. Historical task
evidence belongs in `docs/history/`, audits, decisions, the roadmap, pull
requests, and Git history. Never use a historical snapshot to authorize work.

## Stable product boundaries

The repository analyzes Constructed Magic: The Gathering tournament data in
two separate products:

- **MTGO Environment Trends** at `/index.html`;
- **Tabletop Major Events** at `/melee/index.html`.

MTGO and tabletop may share reusable classification and statistical utilities,
but source data, normalized data, generated statistics, catalogs, workflows,
and front-end behavior remain separate. Never merge their event results into
one statistic.

The tabletop product uses only events explicitly registered in
`configs/melee_events.yaml`. Do not crawl arbitrary Melee events. Mixed events
require reliable Draft, Constructed, playoff, and unknown round labels; unknown
rounds must be reported and excluded pending review.

For full product scope and event policy, use `docs/PROJECT_SCOPE.md`. For exact
match-result treatment and formulas, use `docs/STATISTICS_SPEC.md`. For source,
normalized, generated, and public path boundaries, use
`docs/DATA_ARCHITECTURE.md`.

## Authorization and workspace rules

Before proposing or starting a task, read `docs/STATUS.yaml` and confirm:

- the current phase and task;
- local, commit, remote-publication, merge, and production authorization;
- active blockers and prohibited actions;
- the current working branch and protected paths.

Work one focused task at a time and use a disposable isolated workspace unless
another environment is explicitly approved. Do not develop directly on
`master`. Inspect branch and worktree state before editing, and do not overwrite
unexplained changes.

Local task authorization does not authorize credentials, push, pull-request
creation, merge, production dispatch, protected-branch changes, another task,
or another phase. Follow the exact gates and stop conditions in
`docs/DEVELOPMENT_WORKFLOW.md`.

The documented remote-mutation client is `gh`; do not first attempt PR creation
or merge through an unavailable connector and then misreport that local client
context as expired credentials. Use only the command-scoped credential method
defined in the workflow document after separate remote authorization.

Do not create a second pull request solely to record metadata that GitHub or
Git already records. Carry material status changes into the next already
authorized repository change or a separately approved closeout task.

## Change controls

- Do not silently change product scope or statistical meaning. If a user
  instruction conflicts with established scope, stop and request explicit
  confirmation.
- Do not manually edit generated statistics as a substitute for fixing their
  generator.
- Do not mix documentation cleanup, large refactoring, ingestion, generated
  data, statistical changes, workflow redesign, and front-end redesign in one
  task unless explicitly approved.
- Preserve public data paths and verified legacy entry points until an approved
  compatibility or retirement plan is validated.
- Do not fetch arbitrary events, retain new source responses, dispatch
  production, or change an event whitelist without explicit authorization.
- Do not introduce a mandatory front-end build framework unless separately
  approved.
- Do not commit secrets, tokens, cookies, credentials, private user data, or
  real HMAC keys.
- GitHub Actions changes must preserve least privilege, explicit concurrency,
  validation before publication, and useful failure reporting.

Any change to statistics must update the applicable specification, decision,
tests, Schema, output version, and front-end labels as required. Any data-shape
change must update producers, consumers, fixtures, Schemas, and compatibility
handling as required. Classification changes must preserve stable archetype
and rule IDs, explicit priorities, conflict reporting, Unknown reporting, and
shared same-format behavior across sources.

## Verification and documentation

Before committing, run checks proportionate to the changed scope and review the
complete diff. Preserve the current Standard regression baseline until its
replacement is explicitly verified. Do not delete a legacy entry point until
its replacement and live callers are verified.

At the completion of a development phase:

- update `docs/STATUS.yaml`;
- update `docs/ROADMAP.md` when phase status changes;
- record scope or statistical decisions in `docs/DECISIONS.md`;
- update Schemas and tests when data or statistics change;
- update README commands when supported operations change.

A task is not complete because files were edited. Required outputs, tests,
validation, regression review, documentation consistency, authorization, and
owner acceptance must all be satisfied where applicable.

## Guidance for a non-programmer owner

Work one task at a time. Explain the purpose and user-visible result in plain
language. When owner action is required, provide exact paths, commands,
expected output, verification scope, and a clear stop point. Provide commit or
publication commands only after the applicable authorization. If a command
fails, inspect or request its complete output before proposing unrelated work.
