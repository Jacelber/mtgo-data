# Development Workflow

## Authority

This document governs workspace isolation, execution permissions, task contracts, validation gates, publication gates, and stop conditions. Existing project-scope, statistics, architecture, roadmap, decision, and status documents retain their existing authority. `docs/STATUS.yaml` controls current project state and task authorization.

## Isolation baseline

Use a fresh disposable native-Windows clone for each focused task, created with `--no-hardlinks` and independent internal Git metadata. Keep the protected source repository read-only. Disable the repository-local credential helper with an empty override. Disable push or redirect it to a non-repository sentinel destination. Never use Full access. WSL2 and Dev Containers may be reconsidered later but are not required.

The repository-level `.gitattributes` file fixes recognized text files to LF.
This is defense in depth, not a substitute for the mandatory Windows clone
bootstrap below.

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

## Mandatory Gate 2 bootstrap

Run the following sequence for every new native-Windows disposable workspace.
Replace placeholders with the approved source, workspace, task branch, and
non-repository sentinel:

```powershell
git -c core.autocrlf=false clone --no-hardlinks <source> <workspace>
git -C <workspace> config core.autocrlf false
git -C <workspace> config --local --replace-all credential.helper '""'
git -C <workspace> remote set-url --push origin <disabled-sentinel>
git -C <workspace> switch -c codex/<focused-task>
git -C <workspace> status --porcelain=v1 --untracked-files=all
git -C <workspace> config --get core.autocrlf
git -C <workspace> remote -v
```

The initial status output must be empty, `core.autocrlf` must be `false`, the
repository must have independent Git metadata, and the push URL must not be a
real repository. These are fail-closed checks. If a fresh checkout is dirty,
do not edit files, normalize line endings, restore blobs, or attempt an in-place
repair. Record the cause, abandon that disposable workspace, and bootstrap a
new one correctly. In particular, setting `core.autocrlf=false` after a normal
Windows clone does not undo conversion already performed by the initial
checkout.

At Gate 2, also establish the declared Python environment and confirm that the
commands required by the task contract are available. Do not discover missing
runtime dependencies only after implementation is complete.

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

The task contract must distinguish audit or baseline import, shared-framework
integration, taxonomy or statistical decisions, product enablement, workflow
changes, and front-end changes. Convenience is not authority to pull work from
a later task into the current task. Before technical acceptance, compare the
actual changed paths and behavior with the contract and remove or explicitly
disclose out-of-scope work.

## Change-impact discovery

Before changing a capability state, schema, public path, generated output,
status vocabulary, or other cross-layer contract, search the complete
repository for the old value and its consumers. The search must cover, as
applicable, `configs/`, source code, tests, schemas, documentation, front-end
assets, and workflows. Create a short invalidation map:

| Changed contract | Required consumers to inspect |
| --- | --- |
| Capability or lifecycle state | registry, command guards, closeout tests, status documents, workflows |
| Schema or normalized field | parser, generator, schema, fixtures, validators, front end |
| Public or generated path | producer, consumer, compatibility wrapper, Pages behavior, workflow allowlist |
| Match or player status | archival model, eligibility rules, statistics, diagnostics, fixtures |
| Source-format boundary | discovery filter, normalized metadata, output partition, provenance checks |

Module-local tests are not sufficient evidence that a repository-wide contract
was updated. A missed old-state assertion should be found by impact discovery,
not left for the final full suite.

## Python and dependencies

Prefer a valid task-local virtual environment. An approved focused task may create one and anonymously install repository-declared, explicitly constrained dependencies from an approved official package index for local tests and validators. The environment must remain uncommitted; system or global installation, manifest changes, undeclared packages, credentials, and private indexes require separate authorization. Disclose installation in the final report and report precisely if the declared environment cannot be established. Do not silently upgrade dependencies; dependency manifests remain authoritative.

## Git

Use focused English branch names and commit messages. Make small reviewable local commits. Route protected Git metadata access through Auto-review when required. Never commit directly to `master` or push automatically. Verify dynamic hashes from the active repository. Do not remove lock files without safely proving that they are stale and unowned.

Tests and generators must not depend on checkout depth, the current branch,
wall-clock time, or mutable live Git history. Inject Git and clock results when
testing command or timestamp propagation. Committed-baseline expectations must
derive volatile values from committed artifact metadata.

## Validation

Review the complete diff; run applicable tests and validators; verify changed paths; check for secrets and credentials; check English-language compliance; confirm generated output remains unchanged unless authorized; confirm a clean final worktree; and report unknowns rather than guessing.

Repository validation uses three distinct layers. Do not treat them as interchangeable:

1. **Clean-checkout code and committed-baseline validation** runs in read-only CI for pull requests and pushes to `master`. It includes the complete pytest suite. Tests marked `committed_baseline` intentionally reproduce generators, diagnostics, and public outputs from the current committed production snapshot and require byte-identical results. Volatile dates, timestamps, and aggregate counts come from the committed snapshot metadata rather than a previous run's hard-coded values. These tests must run before any production fetch mutates the checkout.
2. **Production candidate validation** runs after authorized fetching and generation but before staging or publication. It compares the candidate with a baseline snapshot captured at the start of the run, permits only declared generated-data paths, rejects deletions and cross-product writes, parses changed JSON and YAML, verifies event and match document shape, prevents event, match, or fetched-ledger count regression, and retains strict classification, repository, rule, and Schema validation. Candidate acceptance must use dynamic deltas rather than historical hard-coded deck or event counts.
3. **Publication confirmation** runs after the generated commit is pushed. It requires a clean production workspace and confirms that the remote `master` commit equals the locally published commit.

A clean-checkout baseline test protects reproducibility across code and rule changes; it is not evidence that newly fetched data is acceptable. A production candidate check protects the current data increment; it does not replace fixture-based unit and regression tests. Adding a new generated path or allowing an automatic deletion requires explicit review of the candidate publication boundary.

### Validation economy

Use the following ladder and rerun only the layer invalidated by a change:

1. Run the smallest focused test while iterating.
2. Run the impacted subsystem suite after the implementation stabilizes.
3. Run the complete suite once after final code, rules, schemas, fixtures, and
   generated outputs are settled.
4. If the complete suite fails, repair the cause, rerun the failing test and
   impacted suite, then run one final complete suite.
5. After a successful complete suite, documentation-only edits require
   documentation and repository validators locally; they do not require
   another complete local code suite unless they change executable examples,
   fixtures, manifests, workflows, or test discovery. Remote CI may still run
   the complete suite.

Record the validated commit or tree identity in the task evidence. Do not rerun
the same expensive command when no relevant input changed, and do not run every
validator after every small edit.

### External-source and live validation

Fixture tests prove deterministic parsing, not current source compatibility.
When a task claims real-source integration, technical acceptance must include
an approved read-only live smoke test against the exact source shape, followed
by deterministic fixture coverage for the observed contract.

Enumerate source status values before defining statistical eligibility.
Archival retention and statistical inclusion are separate decisions: records
such as disqualified players may be retained while being excluded from win
rate and matchup statistics. Unknown statuses or round types must be reported
and must not be silently coerced into a counted state.

Classify source failures before deciding workflow behavior:

- incomplete or not-yet-published records are deferred and retried by a later
  scheduled run;
- a confirmed source-contract or parser break is fatal;
- unknown cases are surfaced for review.

For stored data in an unexpected product or format directory, trace provenance
before changing the current crawler. Distinguish historical import
contamination from a present ingestion-boundary defect, and enforce embedded
format identity at the generation boundary.

Intermittent third-party UI failures require reproduction, a cache-independent
reload, and network inspection before a code change. A correct destination link
combined with a transient hover-image failure is not by itself evidence of an
application defect.

## Publication preflight and records

Remote publication remains a separate Gate 6 authorization. After that
authorization and before the first remote write:

1. confirm the final local commit, clean status, current branch, and intended
   base;
2. inspect the fetch and disabled push URLs;
3. run `gh auth status`;
4. confirm repository write permission through a read-only repository metadata
   query;
5. if `.github/workflows/**` changed, confirm that the active token includes the
   required `workflow` scope;
6. restore the real push URL only after those checks pass;
7. use the single standard path: local Git push, pull-request creation, checks,
   and authorized merge.

Do not use a push as a credential probe and do not rotate through unrelated
fallback publication mechanisms after a `403`. First distinguish the expected
local disabled-push sentinel from a real GitHub authorization or token-scope
failure. If preflight fails, stop once, report the missing permission or
configuration, and preserve the local commit.

A pull request cannot contain its own not-yet-known merge commit. Therefore,
implementation pull requests should record stable task results and validation,
while GitHub remains the source of truth for their publication steps and merge
identity. Do not automatically create a second status-only pull request after
every implementation pull request. Close exact merge metadata in the next
already-authorized governance or development change, or at phase closeout. If
the owner explicitly requires immediate exact metadata, create at most one
intentional documentation closure change; never create a second change solely
to finalize that closure change.

## Evidence and context economy

Inspect evidence progressively:

1. search for exact paths, identifiers, states, and failure messages;
2. read bounded relevant sections rather than whole large files;
3. request compact counts or structured summaries before detailed records;
4. retrieve only failed job and failed step logs before expanding to full logs;
5. never dump large generated JSON, fixtures, or complete CI logs when a
   targeted query answers the question.

This rule reduces both diagnostic noise and repeated work. A truncated output
is a signal to narrow the query, not to repeat the same broad read.

The evidence behind these controls is summarized in
`docs/audits/DEVELOPMENT_PROCESS_RETROSPECTIVE_2026-07.md`.

## Language

Repository and Git/GitHub content must be English. Codex contracts, criteria, stop conditions, and reports must be English. User-facing orchestration outside the repository may be Chinese. Preserve commands, paths, identifiers, hashes, package names, and raw output. Do not alter existing files solely for language or style consistency. Stop if non-English repository content could be introduced.

## Pause and authorization

A paused project permits read-only analysis and explicitly authorized governance or maintenance tasks. A pause does not authorize product development. P1-05 requires explicit owner authorization. One task's authorization does not authorize another task.

## Disposal

Retain task workspaces until acceptance and any separately authorized publication are complete. Never push capability-probe workspaces. Disposal must be deliberate and must not affect the protected source repository.
