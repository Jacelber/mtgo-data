# GitHub Copilot repository adapter

`AGENTS.md` is the mandatory entry point and complete stable agent guide for
this repository. Read it first, then read every authoritative document it lists
in order before suggesting or changing repository content.

This adapter adds no project state or standing authorization:

- `docs/STATUS.yaml` controls the current phase, task, authorization, protected
  scope, blockers, and prohibited actions;
- `docs/DEVELOPMENT_WORKFLOW.md` controls isolation, approval, publication, and
  stop gates;
- `docs/PROJECT_SCOPE.md`, `docs/STATISTICS_SPEC.md`, and
  `docs/DATA_ARCHITECTURE.md` control product, metric, and data boundaries;
- `PROJECT_NOTES.md` and `docs/history/` are non-authoritative history.

Never infer approval from the roadmap, a historical snapshot, existing legacy
code, or this file. Keep MTGO and Tabletop data and products separate, do not
silently change statistics or generated data, do not develop on `master`, and
stop at every authorization boundary defined by the live status and workflow.
