# Development Workflow

## Authority

This document governs workspace isolation, execution permissions, task contracts, validation gates, publication gates, and stop conditions. Existing project-scope, statistics, architecture, roadmap, decision, and status documents retain their existing authority. `docs/STATUS.yaml` controls current project state and task authorization.

## Isolation baseline

Use a fresh disposable native-Windows clone for each focused task, created with `--no-hardlinks` and independent internal Git metadata. Keep the protected source repository read-only. Disable the repository-local credential helper with an empty override. Disable push or redirect it to a non-repository sentinel destination. Deny network access by default and never use Full access. WSL2 and Dev Containers may be reconsidered later but are not required.

## Controlled workspace reuse

A fresh disposable independent clone remains the default for every focused task. The owner may explicitly authorize reuse of an existing independent isolated workspace only for a directly related, low-risk governance, status, documentation, review, or cleanup task. Reuse is never automatic and its authorization does not carry over.

Before reuse, rerun Gate 2. Reuse requires a completed prior task; intact independent repository topology; no protected-source filesystem access; a clean worktree and index with no untracked or unknown files; no caches, bytecode, logs, or temporary artifacts; no unreviewed dependency or runtime mutation; no credential or persistent permission state; disabled push and credential helper; a fetch URL that does not point to the protected local repository; an explicitly verified current remote base; a new task branch created from that base; and a unique new task ID with explicit allowed paths.

Require a fresh workspace for product-code, dependency, data, schema, architecture, or production-behavior changes; after untrusted code execution; when workspace integrity or isolation is uncertain; when credentials or persistent permissions may remain; for a different project; or whenever the owner requires it. Repairing a workspace or fetching a current base requires explicit authorization and does not authorize push, PR creation, merge, branch deletion, or another task. Stable project facts belong in `docs/STATUS.yaml`; short-lived Git publication steps should generally remain in Git/GitHub history unless they materially affect current authorization or project state. Never start a follow-up task automatically.

## Gates

| Gate | Purpose | Output | Stop condition |
| --- | --- | --- | --- |
| 0: Owner intake | Define the requested task. | Approved task contract. | Stop if authority is absent. |
| 1: Scope and risk confirmation | Confirm scope, paths, permissions, and risks. | Confirmed boundaries. | Stop on scope or risk conflict. |
| 2: Disposable workspace bootstrap | Establish an isolated workspace. | Verified topology and runtime. | Stop if isolation or preflight fails. |
| 3: Autonomous isolated implementation | Perform permitted in-scope work. | Focused local change. | Stop on an unauthorized operation. |
| 4: Automated technical acceptance | Validate the change. | Passing validation evidence. | Stop on unresolved validation failure. |
| 5: Owner product acceptance | Obtain owner review of the completed task. | Owner decision. | Stop pending owner confirmation. |
| 6: Separately authorized remote publication | Publish only when separately authorized. | Explicitly authorized remote result. | Stop without publication authorization. |

Never start the next task automatically.

## Permission classes

Autonomous sandbox operations include repository reads, in-scope ordinary-file edits, task-local temporary files, approved offline checks, and status and diff inspection.

Auto-review operations, only in the isolated task workspace, include Git topology checks when protected metadata is involved, task-branch creation, Git ref and index writes, staging in-scope files, local commits, approved Python execution, and narrowly scoped offline external execution.

Separate owner authorization is required for network access, package installation or upgrade, credential use, push, PR creation, merge, protected-branch changes, remote-branch deletion, force-push, deployment or production changes, data or schema migration, scope expansion, and starting an unapproved task.

Prohibited operations are Full access, direct development on `master`, automatic push, PR, or merge, reading or copying credentials, protected-source modification, cross-project access, and automatic next-task startup.

## Codex task contracts

Every contract requires a unique task ID, exact workspace, objective, authoritative reading list, initial checks, allowed paths, allowed and prohibited operations, validation, stop conditions, report title, and controlled conclusions.

## Python and dependencies

Prefer a valid task-local virtual environment. An explicitly verified base interpreter plus approved offline package path is permitted. Network installation requires separate owner authorization. Do not silently upgrade dependencies; dependency manifests remain authoritative.

## Git

Use focused English branch names and commit messages. Make small reviewable local commits. Route protected Git metadata access through Auto-review when required. Never commit directly to `master` or push automatically. Verify dynamic hashes from the active repository. Do not remove lock files without safely proving that they are stale and unowned.

## Validation

Review the complete diff; run applicable tests and validators; verify changed paths; check for secrets and credentials; check English-language compliance; confirm generated output remains unchanged unless authorized; confirm a clean final worktree; and report unknowns rather than guessing.

## Language

Repository and Git/GitHub content must be English. Codex contracts, criteria, stop conditions, and reports must be English. User-facing orchestration outside the repository may be Chinese. Preserve commands, paths, identifiers, hashes, package names, and raw output. Do not alter existing files solely for language or style consistency. Stop if non-English repository content could be introduced.

## Pause and authorization

A paused project permits read-only analysis and explicitly authorized governance or maintenance tasks. A pause does not authorize product development. P1-05 requires explicit owner authorization. One task's authorization does not authorize another task.

## Disposal

Retain task workspaces until acceptance and any separately authorized publication are complete. Never push capability-probe workspaces. Disposal must be deliberate and must not affect the protected source repository.
