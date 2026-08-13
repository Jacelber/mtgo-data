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
| 5: Owner product acceptance | Obtain owner review of the completed task. | Owner decision. | Stop pending owner confirmation. |
| 6: Separately authorized remote publication | Publish only when separately authorized. | Explicitly authorized remote result. | Stop without publication authorization. |

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
select complete validation.

The declaration is a contract, not a prediction to revise after a test fails.
If a task declared `none` but Gate 3 or Gate 4 finds an artifact change, stop
and treat it as a contract mismatch. Do not describe the mismatch merely as a
baseline-test failure or accept it by updating a snapshot.

The effective validation path is the strictest result required by the declared
impact, actual changed paths and file statuses, any low-cost observable DOM,
JSON, snapshot, or committed-artifact difference, and the mandatory-full
conditions below. The declaration may never lower the result implied by the
other evidence. Pull-request maturity is not an input to validation strength.
Both Draft and Ready pull requests use the same conservative changed-path
allowlists, and locally completed work is published Ready by default. Draft is
optional only when the Owner explicitly requests remote incomplete-work review.
Unknown paths or classification failures select complete validation.

Focused documentation validation requires the single declaration
`internal_diagnostics`, added or modified Markdown files only under the approved
`docs/audits/` or `docs/history/` paths, and no CI-admission authority document.
Focused UI validation requires the single declaration `user_visible_ui` and
added or modified files only from the repository-maintained explicit CSS and
browser-test allowlist in `ci_master_admission.py`. Application state, runtime,
controller, data-model, i18n, legacy asset, HTML, public-path, workflow,
authoritative-document, backend, Schema, statistical, baseline, generated-data,
deletion, and rename changes require complete validation.

Complete validation and the applicable separate Owner authorization are
mandatory for statistical definitions, formulas, or semantics; Schema or
compatibility changes; public paths; production fetch, dispatch, or real-data
writes; workflow write-permission changes; secrets, HMAC, or credentials;
privacy or retention boundaries; deletion, rename, or destructive migration;
baseline refreshes or expected statistical-artifact changes; unknown paths;
or incomplete GitHub evidence.

During Gate 3, run the smallest focused generator, renderer, or browser check
that can expose the declared impact. Before the full suite, inspect a
human-readable comparison: `git diff --stat`, the relevant `git diff`, and,
where useful, `git diff --numstat` or a bounded rendered screenshot or JSON
comparison. Record which files changed, whether they are within the declared
impact, and the relevant field, DOM, or runtime-request difference. This is a
fast review aid; it does not replace a validator or a complete diff review.

Gate 4 retains the strict committed-baseline behavior. Do not add a non-failing
review mode, an automatic baseline-acceptance command, or a test bypass.
Committed-baseline tests continue to require byte-identical outputs against the
committed snapshot. A declared and owner-accepted artifact-contract change may
require an explicit, separately reviewed snapshot edit followed by the same
strict validation; it is never accepted by a review-mode test or automation.

At Gate 5, present the owner with the original declaration, the actual changed
artifact list, the relevant source or rendered diff, and verification matched
to the impact: browser behavior for `user_visible_ui`, field and consumer
evidence for `statistical_json_structure`, and compatibility plus Pages
evidence for `public_path`. A Phase 12 UI task, for example, declares
`user_visible_ui`, runs its focused renderer and browser check during Gate 3,
shows the owner the changed state and screenshot or URL before acceptance, and
then runs the unchanged strict Gate 4 suite. The owner accepts the disclosed
change, not an opaque statement that refreshed baselines pass.

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

1. **Clean-checkout code and committed-baseline validation** runs in read-only CI according to artifact impact, actual changed paths, and complete GitHub evidence rather than Draft or Ready state. Strictly allowlisted documentation runs repository and live-document-policy checks. Strictly allowlisted UI runs repository and native Node validation plus the complete applicable Playwright production-page suite. Every other pull request, every manual validation dispatch, every direct `master` push, and any `master` push whose prior validation cannot be proved exactly runs complete validation. The complete path includes the pytest suite partitioned into exact complementary `ordinary` and `committed_baseline` shards on independent runners. State-only Draft-to-Ready and Ready-to-Draft transitions do not trigger the workflow; relevant body or base edits reclassify the subject, while title-only edits use an admission-only metadata path. The aggregate check remains present for every triggered path. An exact two-parent PR merge may use the lighter post-merge confirmation only when the read-only admission job reclassifies the current declaration and complete file set, proves the successful PR run covered the final merge's exact PR number, base SHA, head SHA, workflow identity, validation class, expected successful jobs, and pre-merge completion time. Missing, stale, changed, ambiguous, paginated beyond support, or unavailable evidence fails safe to the complete suite. Tests marked `committed_baseline` intentionally reproduce generators, diagnostics, and public outputs from the current committed production snapshot and require byte-identical results. Volatile dates, timestamps, and aggregate counts come from the committed snapshot metadata rather than a previous run's hard-coded values. These tests must run before any production fetch mutates the checkout. The exact admission predicates, allowlists, job matrix, production boundary, failure visibility, remote acceptance, and rollback are defined in `docs/audits/CI-MASTER-ADMISSION.md`.
2. **Production candidate validation** runs after authorized fetching and generation but before staging or publication. It compares the candidate with a baseline snapshot captured at the start of the run, permits only declared generated-data paths, rejects deletions and cross-product writes, parses changed JSON and YAML, verifies event and match document shape, prevents event, match, or fetched-ledger count regression, and retains strict classification, repository, rule, Schema, generated consumer-contract, and focused generated-page browser validation. Candidate acceptance and generated consumer tests must use structural invariants and values derived from the current candidate rather than historical hard-coded deck, event, archetype, matrix-row, percentage, or date expectations.
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

Real-browser validation must run a single Chromium launch-and-close preflight
before Playwright starts its web server or collects the full browser matrix. A
systemic launch failure such as `spawn EPERM`, a missing browser executable, or
an unusable browser runtime must stop that command immediately; it must not be
repeated once per browser test. The maintained local server uses the already
required Node.js runtime rather than a separately discovered Python command.

The ordinary CI shard enforces a 120-second per-test call ceiling from the
existing timing report. A slower ordinary call is a test-architecture failure:
move full committed-snapshot reproduction to the strict complementary baseline
shard, replace a production-corpus contract test with a representative fixture,
or share immutable setup without weakening the assertion. Do not raise the
ceiling merely to accommodate repeated full-corpus generation.

Record the validated commit or tree identity in the task evidence. Do not rerun
the same expensive command when no relevant input changed, and do not run every
validator after every small edit.

### CI timing observation

The read-only validation workflow records timing from each complementary
pytest shard. Each GitHub summary reports the selected and completed test
counts, call-time totals, and the 25 slowest completed calls for that shard.
The aggregate check retains the established `Repository validation (Python
3.12)` name and passes only after static validation and both shards pass.
Timing reports are observation aids only: they must not suppress failures or
replace the complete-suite requirement. Use representative successful PR,
`master`, and production runs before proposing trigger changes or test
removal.

The validation job has a 30-minute safety ceiling. This is a failure-reporting
boundary, not a duration target: the 2026-07-28 Gate 1 review found that the
former 15-minute ceiling could cancel an otherwise progressing complete suite
before pytest printed its failure details. Raising the ceiling does not change
test selection, triggers, permissions, or the requirement to investigate
duration growth.

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

Remote publication remains a separate Gate 6 authorization. After that
authorization and before the first remote write:

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
