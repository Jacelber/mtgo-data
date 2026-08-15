# Development Workflow

## Authority

This document governs workspace isolation, execution permissions, task contracts, validation gates, publication gates, and stop conditions. Existing project-scope, statistics, architecture, roadmap, decision, and status documents retain their existing authority. `docs/STATUS.yaml` controls current project state and task authorization.

For every task, read `AGENTS.md`, `docs/STATUS.yaml`, the relevant current-task
and current-phase roadmap subsections, and the Gate and authorization sections
needed for the task. Expand that set from the approved paths and artifact
impact: product-scope or navigation work requires `docs/PROJECT_SCOPE.md`;
statistical code, formulas, semantics, or artifacts require
`docs/STATISTICS_SPEC.md`; data, Schemas, public paths, production, privacy, or
retention work requires `docs/DATA_ARCHITECTURE.md`; and decision reading may
be limited to directly relevant entries. Read more when an authoritative
document changes, the impact is unclear, or the highest-strength process is
required. A path under `docs/` is not inherently low risk.

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
| 5: Owner acceptance and completion authority | Obtain owner review of the completed task. Acceptance authorizes continuous completion of that exact task. | Owner decision and accepted subject. | Stop pending owner confirmation. |
| 6: Accepted-task completion | Commit, publish a Ready PR, merge after required checks pass, and perform the task's applicable publication or production steps. | Completed accepted task. | Stop on failed checks, changed subject, conflict, permission blocker, or scope expansion. |

Never start the next task automatically.

## Artifact-impact and owner-acceptance protocol

At Gate 1, every task contract must declare the expected artifact impact before
implementation. Select every applicable value from this closed list:

- `none` — no committed, generated, rendered, or public artifact is expected
  to change;
- `internal_diagnostics` — only non-public diagnostics or reports are expected
  to change;
- `user_visible_ui` — a rendered user-visible page, interaction, copy, or
  layout is expected to change;
- `statistical_json_structure` — a public statistical JSON structure is
  expected to change; or
- `public_path` — a public URL, runtime request path, compatibility path, or
  Pages publication boundary is expected to change.

For pull requests, the PR body is the single machine-readable task declaration
source and must contain exactly one marker:

`<!-- artifact-impact: user_visible_ui -->`

Multiple applicable values use one comma-separated marker. Do not repeat the
task declaration in `docs/STATUS.yaml` or another machine-maintained field.
`docs/DEVELOPMENT_WORKFLOW.md` remains the authority for the closed value set.
Missing, unreadable, duplicate, empty, conflicting, or unknown declarations
stop the PR admission path for owner classification. They do not trigger an
unrelated catch-all test suite.

At Gate 1, list every planned unknown-path addition, deletion, and rename by
exact path and validation category. Do not use globs. The PR body repeats each
approved operation in one machine-readable marker:

`<!-- file-operation: add|docs|review-output/owner-review.md -->`

`<!-- file-operation: delete|docs|docs/obsolete.md -->`

`<!-- file-operation: rename|docs|docs/old.md|docs/history/old.md -->`

Known-path additions need no operation marker. Every declaration must match one
actual diff operation exactly, and every operation that requires a declaration
must be present. A known path cannot be assigned a different category.
Declarations select the minimal checks only; they do not authorize deletion,
public-path or statistical changes, credentials, production, or remote actions.

The declaration is a contract, not a prediction to revise after a test fails.
If a task declared `none` but Gate 3 or Gate 4 finds an artifact change, stop
and treat it as a contract mismatch. Do not describe the mismatch merely as a
baseline-test failure or accept it by updating a snapshot.

The PR admission script mechanically maps every added or modified known path to
one or more categories: documentation, UI, maintained Python, rules/data, and
governance. The targeted job runs only the checks assigned to those categories.
Pull-request maturity is not an input to validation strength. A title-only edit uses admission only;
a body or base edit reclassifies the subject.

Undeclared unknown-path additions, deletions, renames, malformed or stale
operation declarations, and incomplete GitHub evidence are not test questions.
They select `unclassified`: the aggregate check fails immediately with the
reason. Exact declared operations run only their declared minimal category.
Statistical meaning, public paths, production,
privacy, credentials, destructive migration, and remote writes still require
their separate Owner gates; a green targeted PR check never grants authority.

During Gate 3, run the smallest focused generator, renderer, or browser check
that can expose the declared impact. Before automated acceptance, inspect a
human-readable comparison: `git diff --stat`, the relevant `git diff`, and,
where useful, `git diff --numstat` or a bounded rendered screenshot or JSON
comparison. Record which files changed, whether they are within the declared
impact, and the relevant field, DOM, or runtime-request difference. This is a
fast review aid; it does not replace a validator or a complete diff review.

At Gate 4, every automated check must state the risk it answers and use the
smallest subject that can answer it. Do not repeat successful evidence for the
same immutable subject. Byte-level committed baselines and the full pytest suite
are not PR admission requirements. Their retirement is a separate GOV-07/GOV-08
change; until then they may remain available for a specifically authorized
diagnosis, but they are not the default proof of correctness.

At Gate 5, present the owner with the original declaration, the actual changed
artifact list, the relevant source or rendered diff, and verification matched
to the impact: browser behavior for `user_visible_ui`, field and consumer
evidence for `statistical_json_structure`, and compatibility plus Pages
evidence for `public_path`. A Phase 12 UI task, for example, declares
`user_visible_ui`, runs its focused renderer and browser check during Gate 3,
shows the owner the changed state and screenshot or URL before acceptance, and
and shows the owner the changed state and screenshot or URL before acceptance.
That owner review is the final UI acceptance evidence for the reviewed commit;
do not rerun automated browser tests afterward unless the UI subject changes.

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

Before Owner acceptance, separate authorization is required for remote writes.
Owner acceptance then authorizes local commit, push, one Ready pull request,
required-check waiting, merge, and the accepted task's applicable publication
or production completion without repeated prompts. The accepted subject must
remain byte-identical except for publication metadata that GitHub creates.
Stop and return to the Owner when a required check fails, the diff or scope
changes, a merge conflict appears, permissions block the documented path, or a
new product/statistical decision is required. Acceptance never carries to
another task or phase, unrelated credentials, force-push, repository settings,
secrets, or destructive action outside the accepted contract.

Prohibited operations are Full access, direct development on `master`, reading
or copying credentials, protected-source modification, cross-project access,
force-push, and automatic next-task startup.

## Validation-failure handling

A validation failure does not itself require new Owner authorization. Codex may diagnose and repair it locally when the repair remains within the approved task objective, introduces no unapproved product or statistical semantics, accesses no protected resource, requires no remote write, does not weaken the intended validation guarantee, and is fully disclosed. Stop when completion would require an unresolved product or statistical decision, material task or phase expansion, sensitive access, protected-environment modification, acceptance of unexplained production behavior, weakened validation, unauthorized remote write, or an explicitly protected or prohibited path.

## Codex task contracts

Every contract requires a unique task ID, exact workspace, objective, authoritative reading list, initial checks, expected deliverable paths, explicitly protected or prohibited paths, delegated local authority, validation, acceptance-continuation applicability, product or phase stop conditions, report title, and controlled conclusions.

A bounded batch contract may group small, non-production tasks only when they
share one area and artifact impact. It must state:

- `batch_id`;
- `objective`;
- `artifact_impact`;
- `allowed_paths`;
- `prohibited_changes`;
- `allowed_actions`; and
- `stop_conditions`.

One batch may share one isolated workspace, authorization, branch, pull
request, and final complete CI run. The final report must still disclose every
sub-item separately. Merge, production dispatch, real production-data writes,
secret/HMAC/credential operations, workflow write-permission expansion, public
path deletion, statistical-meaning changes, incompatible Schema migration, and
privacy-boundary changes always require separate authorization.

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
not delegated to an unrelated catch-all suite.

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

1. **Targeted pull-request validation** uses complete changed-file evidence to map known paths and exact predeclared file operations to documentation, UI, code, data, and governance checks. It never runs full pytest, committed byte baselines, or Playwright. Undeclared or mismatched unknown additions, deletions, renames, malformed declarations, or unavailable evidence fails quickly as `unclassified`. The aggregate check remains present. An exact two-parent merge may use confirmation only when admission proves the exact PR number, base SHA, head SHA, workflow identity, validation class, expected successful jobs, and pre-merge completion time.
2. **Production candidate validation** runs after authorized fetching and generation but before staging or publication. It compares the candidate with a baseline snapshot captured at the start of the run, permits only declared generated-data paths, rejects deletions and cross-product writes, parses changed JSON and YAML, verifies event and match document shape, prevents count regression, and retains strict classification, repository, rule, Schema, value-independent output invariants, generated consumer-contract, and one generated-page browser smoke. Candidate checks derive their expectations from the candidate and specifications rather than historical hard-coded bytes or tournament values.
3. **Publication confirmation** runs after the generated commit is pushed. It requires a clean production workspace and confirms that the remote `master` commit equals the locally published commit.

A clean-checkout baseline test protects reproducibility across code and rule changes; it is not evidence that newly fetched data is acceptable. A production candidate check protects the current data increment; it does not replace fixture-based unit and regression tests. Adding a new generated path or allowing an automatic deletion requires explicit review of the candidate publication boundary.

### Allowlisted Pages build and cutover

`build_pages_artifact.py` is the repository-owned Pages packaging boundary. It
must build into a new directory outside the checkout from
`configs/pages_publication.json`, preserve source bytes, validate the complete
event `434455` compatibility closure, reject symbolic links and unsafe paths,
and report repository, data-tree, artifact, protected-file, and excluded-file
sizes. Pull requests may build the candidate but must not deploy it. The Pages
deploy job may run only for `master` pushes or the accepted explicit
production-publication dispatch on `master`, and has only `pages: write` and
`id-token: write`; it must not receive repository write access or persisted Git
credentials.

When a production data publication changes `master`, its publish job must first
confirm the remote `master` commit and then explicitly dispatch the allowlisted
Pages workflow on `master`, as defined by DEC-084. GitHub does not trigger the
Pages push workflow from a commit made with that production workflow's own
`GITHUB_TOKEN`. A no-change production publication does not dispatch Pages;
pull-request builds remain non-deploying, and the Pages deployment job retains
its existing no-repository-write boundary.

The initial cutover is separately gated from local implementation, commit, and
pull-request review. Before changing the repository setting, capture the active
Pages configuration and a successful deployment artifact. The P10-07 recovery
baseline is legacy branch-root publication from `master` at `/`. Immediately
before an authorized merge, change the Pages source to GitHub Actions, merge the
already validated exact PR head, wait for the custom deployment, and verify both
product entry points plus their runtime JSON requests. Do not dispatch a data
workflow as part of this cutover.

If the first custom deployment or front-end verification fails, restore the
captured legacy `master` `/` Pages source and confirm a managed Pages build
succeeds. The prior artifact and configuration record are recovery evidence,
not a second data archive. Keep the recovery procedure until at least one
scheduled MTGO data commit is followed by a successful custom Pages deployment
and owner-visible front-end verification.

### Validation economy

Use the following ladder and reuse every result that remains valid for the same
code tree, environment layer, test node ID, and relevant inputs:

1. Run the smallest focused test while iterating.
2. Run the impacted subsystem suite after the implementation stabilizes.
3. Do not rerun a passed test in the same tree and layer because another test
   failed. An unknown failure permits only the failed node ID and smallest
   affected set to run again during diagnosis.
4. Record a known, controlled local infrastructure error as
   `accepted_infrastructure_exception`; preserve the unaffected passed evidence
   and do not relabel the exception as a test pass or trigger a complete rerun.
5. A relevant code, fixture, dependency, bootstrap, or input change invalidates
   only the evidence it can affect. The resulting tree receives its first
   applicable validation. Documentation-only edits do not invalidate code
   tests unless they change executable examples, manifests, workflows, or test
   discovery.
6. The final pull-request head receives one independent targeted CI run.
   Do not rerun the same failed workflow head. Diagnose it and, when a repair is
   required, validate the new head once. A red required check is never manually
   described as green.

Every pytest process must use a basetemp outside the repository. The maintained
pytest bootstrap rejects an internal explicit path before collection and
selects a process-unique external sibling path for local runs. GitHub Actions
passes a shard-specific path under `RUNNER_TEMP`. Do not create a repository
local `.pytest_cache`, `.codex-test-temp`, or other basetemp as a workaround for
an inaccessible system temporary directory.

After one successful targeted PR run, exact two-parent merge admission reuses
that evidence through `pr-confirmation`; it does not rerun pytest, browser, or
static validation. Missing, changed, conflicting, or unavailable evidence
fails closed as `unclassified` without starting a catch-all suite.

UI work receives one local owner browser review after syntax/model smoke. That
review is final for the reviewed immutable subject. Production retains one
generated-page Chromium smoke before packaging because it checks a different
subject: the newly generated candidate.

Legacy ordinary and committed-baseline tests remain available only until the
separately authorized GOV-07/GOV-08 retirement work. They are not PR gates and
must not be run merely because the changed path is broad or unfamiliar.

Record the validated commit or tree identity in the task evidence. Do not rerun
the same expensive command when no relevant input changed, and do not run every
validator after every small edit.

### CI timing observation

The PR workflow has a five-minute job ceiling, not a target. Measure admission
and category runtimes from representative successful runs. If a category
regularly exceeds one minute, identify the exact slow item and remove duplicate
coverage or replace its subject with the smallest fixture; do not restore a
catch-all suite.

The evidence counts, decision gates, stop conditions, and model guidance for
any CI-efficiency work are maintained in
`docs/audits/CI_EFFICIENCY_PLAN.md`. Treat that plan as the required sequence:
collect representative runs first, then decide whether a separately authorized
governance, sharding, or trigger task is justified.

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

Owner acceptance supplies Gate 6 completion authority for the exact accepted
task. Before the first remote write:

1. confirm the final local commit, clean status, current branch, and intended
   base;
2. inspect the fetch and disabled push URLs;
3. in the same execution context that will publish, run
   `gh auth status -h github.com` and
   `gh api user --jq .login`;
4. confirm repository write permission without mutating it:
   `gh api repos/Jacelber/mtgo-data --jq .permissions.push` must return `true`;
5. if `.github/workflows/**` changed, confirm that the active token includes the
   required `workflow` scope;
6. keep the workspace's disabled push sentinel and empty local credential
   helper intact; do not restore or persist a real push URL;
7. use only the repository-specific `gh` publication path below.

Do not use a push as a credential probe and do not rotate through unrelated
fallback publication mechanisms after a `403`. First distinguish the expected
local disabled-push sentinel from a real GitHub authorization or token-scope
failure. If preflight fails, stop once, report the missing permission or
configuration, and preserve the local commit.

For this repository, generic GitHub app or connector mutation preferences are
superseded by this repository-specific path. GitHub app and connector tools may
be used read-only, but do not attempt branch creation, file writes, Git-data
writes, PR creation, or merge through them before falling back to `gh`.

Use these commands, substituting the approved workspace, branch, title, body
file, and PR number:

```powershell
git -c safe.directory=<workspace> `
  -c credential.helper= `
  -c "credential.helper=!gh auth git-credential" `
  push https://github.com/Jacelber/mtgo-data.git <branch>

gh pr create --repo Jacelber/mtgo-data --base master --head <branch> `
  --title "<title>" --body-file <body-file>

gh pr checks <pr-number> --repo Jacelber/mtgo-data --watch --interval 20
gh pr view <pr-number> --repo Jacelber/mtgo-data `
  --json state,headRefOid,mergeable,statusCheckRollup,url
gh pr merge <pr-number> --repo Jacelber/mtgo-data --merge --delete-branch
```

The command-scoped `safe.directory` and credential helper do not modify global
or repository-local configuration. A disabled push sentinel error means the
explicit approved URL was not used. `/dev/tty`, username-prompt, or credential
helper errors mean Git did not obtain the already-checked `gh` credential; they
do not prove token expiration. Describe a token as invalid or expired only
when both `gh auth status` and `gh api user` fail with an authentication error
in the actual publication context. Otherwise report a credential-context or
helper-path failure and retry only the documented path.

A pull request cannot contain its own not-yet-known merge commit. Therefore,
implementation pull requests should record stable task results and validation,
while GitHub remains the source of truth for their publication steps and merge
identity. Do not automatically create a second status-only pull request after
every implementation pull request. Close exact merge metadata in the next
already-authorized governance or development change, or at phase closeout. If
the owner explicitly requires immediate exact metadata, create at most one
intentional documentation closure change; never create a second change solely
to finalize that closure change.

Before merging the implementation PR, update durable project state and the
next owner-authorization stop in that same PR without inventing not-yet-known
identifiers. Report the actual PR number, merge SHA, workflow run IDs, and Pages
result in the final handoff. Leave those exact publication fields absent or
explicitly deferred in the repository until the next already-authorized
development or governance PR, then reconcile them as part of that PR's normal
documentation maintenance. Do not create or switch to a
`publication-record`, `status`, `reconciliation`, or `finalization` branch
solely for those identifiers. An immediate documentation PR is allowed only
when the owner explicitly requests it or when stale durable state would
otherwise authorize unsafe work; explain the exception before creating it.

## Evidence and context economy

Inspect evidence progressively:

1. search for exact paths, identifiers, states, and failure messages;
2. read bounded relevant sections rather than whole large files;
3. request compact counts or structured summaries before detailed records;
4. retrieve only failed job and failed step logs before expanding to full logs;
5. never dump large generated JSON, fixtures, or complete CI logs when a
   targeted query answers the question.

Keep completed-task validation and publication evidence in the pull request and
Git whenever those systems already record it. `docs/STATUS.yaml` stores live
state, authorization, blockers, and the next planned task; ordinary tasks do
not require a separate history entry by default. Add durable history only when
the evidence is not otherwise preserved or a phase-closeout contract requires
it.

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
