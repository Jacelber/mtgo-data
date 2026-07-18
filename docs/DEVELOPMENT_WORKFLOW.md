# Development Workflow

## Authority

This document governs workspace isolation, execution permissions, task contracts, validation gates, publication gates, and stop conditions. Existing project-scope, statistics, architecture, roadmap, decision, and status documents retain their existing authority. `docs/STATUS.yaml` controls current project state and task authorization.

## Isolation baseline

Use a fresh disposable native-Windows clone for each focused task, created with `--no-hardlinks` and independent internal Git metadata. Keep the protected source repository read-only. Disable the repository-local credential helper with an empty override. Disable push or redirect it to a non-repository sentinel destination. Never use Full access. WSL2 and Dev Containers may be reconsidered later but are not required.

## Controlled workspace reuse

A fresh disposable independent clone remains the default for every focused task. The owner may explicitly authorize reuse of an existing independent isolated workspace only for a directly related, low-risk governance, status, documentation, review, or cleanup task. Reuse is never automatic and its authorization does not carry over.

Before reuse, rerun Gate 2. Reuse requires a completed prior task; intact independent repository topology; no protected-source filesystem access; a clean worktree and index with no untracked or unknown files; no caches, bytecode, logs, or temporary artifacts; no unreviewed dependency or runtime mutation; no credential or persistent permission state; disabled push and credential helper; a fetch URL that does not point to the protected local repository; an explicitly verified current remote base; a new task branch created from that base; and a unique new task ID with explicit allowed paths.

Require a fresh workspace for product-code, dependency, data, schema, architecture, or production-behavior changes; after untrusted code execution; when workspace integrity or isolation is uncertain; when credentials or persistent permissions may remain; for a different project; or whenever the owner requires it. For an approved focused task, anonymous read-only fetch of the approved public repository is allowed unless the task is explicitly fully offline. Workspace repair may proceed only within delegated local authority; stop if it would discard unknown work, alter a protected environment, access another workspace, use credentials, or compromise isolation. Fetch or repair does not authorize push, PR creation, merge, remote-branch deletion, or another task. Stable project facts belong in `docs/STATUS.yaml`; short-lived Git publication steps should generally remain in Git/GitHub history unless they materially affect current authorization or project state. Never start a follow-up task automatically.

## Controlled workspace continuation

A workspace created during the current authorized task may continue after a compliant stop and clarification when repository identity and the authorized base remain verified, the worktree state is understood, isolation remains intact, no credential or remote-write capability was introduced, and the continuation is not a new task. This is not reuse for a different task.

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

An approved focused task grants delegated local execution authority for all reasonably necessary work inside its isolated disposable workspace: repository inspection, ordinary-file edits, test and fixture creation, repair of existing tests that block the task, temporary experiments and cleanup, task-local artifacts, approved Python execution, tests and validators, local branch creation, staging, local commits, task-local reset or revert operations, and diff, status, log, and topology inspection. This authority applies only to the approved task objective; it does not authorize another task or phase, a product or statistical decision, or remote publication.

Task-contract paths normally identify expected final deliverables, not absolute local experimentation boundaries. A path is an absolute boundary when explicitly protected, prohibited, sensitive, outside the task workspace, generated and non-editable, or otherwise explicitly restricted. A final change outside expected paths must directly support the task, have a documented technical justification, be disclosed in the final report, and not silently introduce a product, statistical, schema, data, workflow, or public-behavior change. Revert unrelated experimental changes before delivery.

Anonymous read-only clone and fetch of the approved public repository, and necessary public-documentation access, are allowed unless a task is explicitly fully offline. They do not authorize credentials, uploads, remote API writes, transmission to unrelated services, unapproved third-party execution, unrelated services or repositories, or system-level installation.

Separate Owner authorization is required for credentials or sensitive-resource access; product or statistical decisions; task or phase expansion; protected-environment changes; unexplained production-behavior changes; push, remote branch creation or deletion, pull-request operations, merge, tags, releases, workflow dispatch, deployments, repository-setting changes, secrets or variables, remote API mutations, protected-branch changes, and force-push. Local completion stops before remote publication unless separately authorized.

Prohibited operations are Full access, direct development on `master`, automatic push, PR, or merge, reading or copying credentials, protected-source modification, cross-project access, and automatic next-task startup.

## Validation-failure handling

A validation failure does not itself require new Owner authorization. Codex may diagnose and repair it locally when the repair remains within the approved task objective, introduces no unapproved product or statistical semantics, accesses no protected resource, requires no remote write, does not weaken the intended validation guarantee, and is fully disclosed. Stop when completion would require an unresolved product or statistical decision, material task or phase expansion, sensitive access, protected-environment modification, acceptance of unexplained production behavior, weakened validation, unauthorized remote write, or an explicitly protected or prohibited path.

## Codex task contracts

Every contract requires a unique task ID, exact workspace, objective, authoritative reading list, initial checks, expected deliverable paths, explicitly protected or prohibited paths, delegated local authority, separate remote-publication authority, validation, product or phase stop conditions, report title, and controlled conclusions.

## Python and dependencies

Prefer a valid task-local virtual environment. An approved focused task may create one and anonymously install repository-declared, explicitly constrained dependencies from an approved official package index for local tests and validators. The environment must remain uncommitted; system or global installation, manifest changes, undeclared packages, credentials, and private indexes require separate authorization. Disclose installation in the final report and report precisely if the declared environment cannot be established. Do not silently upgrade dependencies; dependency manifests remain authoritative.

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
