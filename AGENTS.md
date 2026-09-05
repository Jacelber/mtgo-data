# AGENTS.md

## Purpose

This is the mandatory entry point for every assistant and developer. It keeps
only rules needed on every task and routes conditional detail to its single
authoritative document.

## Start every task

1. Read `docs/STATUS.yaml`; confirm the current phase, active program or weekly
   cycle, durable blockers or unresolved decisions, and paused activities.
2. Read only the current-phase material in `docs/ROADMAP.md`.
3. Read the applicable Gate, artifact-impact, authorization, validation, and
   publication sections of `docs/DEVELOPMENT_WORKFLOW.md`.
4. Expand by impact:
   - product scope or navigation: `docs/PROJECT_SCOPE.md`;
   - statistics, formulas, semantics, or statistical artifacts:
     `docs/STATISTICS_SPEC.md`;
   - data, Schemas, public paths, production, privacy, or retention:
     `docs/DATA_ARCHITECTURE.md`;
   - scope, statistical, or governance precedent: only the relevant entries in
     `docs/DECISIONS.md`.
5. Read wider only when an authoritative document changes, impact is unclear,
   or the task requires the highest-strength process.

Authority remains, in order: this file, project scope, statistics
specification, data architecture, roadmap, decisions, status, then development
workflow. The active Owner conversation is the authority for the current task
and its permissions. `docs/STATUS.yaml` records durable live project state;
Git and GitHub record repository and merge facts; generated artifacts record
their own provenance. Existing code describes implementation, not necessarily
the approved target.

Files under `docs/history/`, audits, `PROJECT_NOTES.md`, pull requests, and Git
are evidence only. They never authorize current work.

## Stable product boundaries

The repository has two separate Constructed Magic products:

- **MTGO Environment Trends** at `/index.html`;
- **Tabletop Major Events** at `/melee/index.html`.

Their source data, normalized data, generated statistics, catalogs, and
front-end behavior remain separate. Shared utilities never justify merging
their results.

Tabletop uses only events registered in `configs/melee_events.yaml`. Mixed
events require reliable Draft, Constructed, playoff, and unknown labels;
unknown rounds are reported and excluded pending review.

## Task and authorization rules

Work one focused task at a time in a disposable isolated workspace unless the
Owner explicitly approves reuse. Inspect branch and worktree state before
editing, preserve unexplained changes, and develop off `master`.

An explicit Owner instruction in the active conversation authorizes only the
exact named task and lane. Do not require or create a STATUS-only change to
repeat that authority. Owner acceptance binds the approved objective, semantic
and visible result, protected scope, and task delta; it does not bind the task
to an obsolete base commit. Acceptance authorizes continuous completion of
that same task through local commit, one Ready PR, required CI, eligible bounded
pre-merge repair, merge, and applicable publication. A failed required check
closes the merge gate but does not by itself require new authorization. Follow
the accepted-task repair and base-refresh procedures in
`docs/DEVELOPMENT_WORKFLOW.md`; stop when a repair is ineligible, unproved, or
exhausts its limit, or when the subject or scope changes, a semantic dependency
is unproved, permissions block the documented path, or a new product,
statistical, editorial, or security decision is required. Never carry
authorization into another task or phase.

Before an authorized GitHub write, run
`tools/github_publication_preflight.ps1 -ActualPublicationContext -PrBodyFile
<path> -BaseCommit <sha> -HeadCommit <sha>` using the actual publication
context and the exact prepared PR body and final local commits; add
`-PythonExecutable <approved-python-executable>` and add
`-RequireWorkflowScope` when workflows changed. Only `READY` continues. The
preflight validates the body against the local diff before it contacts GitHub.
A bare `gh auth status` is never a credential verdict. Use the command-scoped
`gh` credential path in the workflow document and keep the local push URL
disabled.

Artifact-impact and file-operation declarations are task contracts, not test
inputs. List every planned unknown-path addition, deletion, and rename by exact
path before the operation. Missing or mismatched evidence stops as
`unclassified`; it never selects a catch-all suite. The exact marker formats
and categories are in the workflow document.

## Change controls

- Obtain an explicit decision before changing product scope or statistical
  meaning. Update every affected specification, producer, consumer, Schema,
  fixture, test, and label when such a change is approved.
- Fix generators instead of manually editing generated statistics.
- Keep documentation cleanup, large refactoring, ingestion, generated data,
  statistics, workflow redesign, and UI redesign in separate tasks unless the
  Owner explicitly combines them.
- Preserve public paths and legacy entry points until a reviewed compatibility
  or retirement plan proves replacements and rollback.
- Fetch only approved events, retain source responses only under the approved
  policy, and dispatch production only when the current task authorizes it.
- Keep stable classification IDs, priorities, conflict reporting, Unknown
  reporting, and same-format behavior across sources.
- Preserve least privilege, explicit concurrency, validation before
  publication, and useful failure reporting in GitHub Actions.
- Keep secrets, tokens, cookies, credentials, private user data, and real HMAC
  keys out of the repository.

## Verification and completion

Name the risk before running a check. Run the smallest subject that can answer
it and never repeat successful evidence for the same immutable subject. Review
the complete diff and changed paths before acceptance. UI work uses the Owner's
final browser review as its acceptance record; production validates the newly
generated candidate once at the output gate.

At every task completion:

- keep `docs/STATUS.yaml` limited to durable phase or program state, active
  weekly-cycle state, unresolved blockers or decisions, and paused activities;
- when completed task detail exists in `docs/ROADMAP.md`, move it in the same
  accepted task to the matching phase history file, update
  `docs/history/README.md`, and leave one compact history pointer;
- update roadmap order or phase acceptance only when it changed;
- record scope or statistical decisions in `docs/DECISIONS.md`;
- update Schemas, tests, and README only when their contracts changed;
- do not create a second PR solely to record identifiers already preserved by
  GitHub or Git.

A task is complete only when its required output, proportional verification,
documentation consistency, Owner acceptance, and applicable same-task
completion are finished. Stop afterward; do not begin the next task.

## Owner communication

Before formally implementing a task, give the Owner a development brief that
states:

- the current problem;
- the concrete development scope and how it will solve that problem;
- the effect expected after completion; and
- the recommended model, balancing implementation difficulty, risk, and token
  efficiency.

The Owner uses this brief to decide whether development should proceed.
Receiving, reviewing, discussing, relying on, or agreeing with the brief does
not authorize implementation. Begin formal development only after the Owner
gives separate, explicit authorization for that task.

Explain purpose and user-visible effect in plain language. When Owner action is
needed, give exact paths or commands, expected output, verification scope, and
a clear stop point. Inspect complete failure output before proposing unrelated
work.
