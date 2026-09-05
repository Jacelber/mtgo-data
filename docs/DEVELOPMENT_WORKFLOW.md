# Development Workflow

## Authority

This document governs workspace isolation, execution permissions, task contracts, validation gates, publication gates, and stop conditions. Existing project-scope, statistics, architecture, roadmap, decision, and status documents retain their existing authority. The active Owner conversation controls the current task and its permissions. `docs/STATUS.yaml` records durable live project state; Git and GitHub record repository and merge facts; generated artifacts record their own provenance.

For every task, read `AGENTS.md`, `docs/STATUS.yaml`, the relevant current-phase
roadmap subsection, and the Gate and authorization sections
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

Require a fresh workspace for product-code, dependency, data, schema, architecture, or production-behavior changes; after untrusted code execution; when workspace integrity or isolation is uncertain; when credentials or persistent permissions may remain; for a different project; or whenever the owner requires it. For an approved focused task, anonymous read-only fetch of the approved public repository is allowed unless the task is explicitly fully offline. Workspace repair may proceed only within delegated local authority; stop if it would discard unknown work, alter a protected environment, access another workspace, use credentials, or compromise isolation. Fetch or repair does not authorize push, PR creation, merge, remote-branch deletion, or another task. Durable project facts belong in `docs/STATUS.yaml`; short-lived task authorization remains in the active Owner conversation, and publication facts remain in Git and GitHub. Never start a follow-up task automatically.

## Controlled workspace continuation

A workspace created during the current authorized task may continue after a compliant stop and clarification when repository identity and the authorized base remain verified, the worktree state is understood, isolation remains intact, no credential or remote-write capability was introduced, and the continuation is not a new task. This is not reuse for a different task.

## Gates

| Gate | Purpose | Output | Stop condition |
| --- | --- | --- | --- |
| 0: Owner intake | Define the requested task. | Approved task contract. | Stop if authority is absent. |
| 1: Scope and risk confirmation | Confirm scope, paths, permissions, and risks. | Confirmed boundaries. | Stop on scope or risk conflict. |
| 2: Disposable workspace bootstrap | Establish an isolated workspace. | Verified topology and runtime. | Stop if isolation or preflight fails. |
| 3: Autonomous isolated implementation | Perform permitted in-scope work. | Focused local change. | Stop on an unauthorized operation. |
| 4: Automated technical acceptance | Validate the change and map every required check to its actual execution contract. | Passing local evidence, resolved execution mapping, and explicit cloud-only pending items. | Stop on an unresolved local failure, invalid evidence, or unmapped requirement. |
| 5: Owner acceptance and completion authority | Obtain owner review of the completed task. Acceptance authorizes continuous completion of that exact task. | Owner decision and exact acceptance anchor. | Stop pending owner confirmation. |
| 6: Accepted-task completion | Commit, publish a Ready PR, satisfy required checks, merge, and perform the task's applicable publication or production steps. | Completed accepted task. | Stop when repair is ineligible or exhausted, the accepted subject changes, exact proof or permissions fail, a conflict appears, or scope expands. |

Never start the next task automatically.

## Artifact-impact and owner-acceptance protocol

At Gate 1, every task contract must declare the expected artifact impact before
implementation. Select every applicable value from this closed list:

- `none` — no product, generated, rendered, or public artifact is expected to
  change; internal governance and control-plane source changes do not by
  themselves constitute product artifact impact;
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

The repository PR template intentionally uses `REPLACE_ME`, which is not a
valid value. Before the first remote write, prepare the final body file and run
the publication preflight against the exact final base and head commits. The
preflight applies this same admission classifier locally; editing the remote PR
body to repair a preventable omission is not part of the normal publication
path.

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
same immutable subject. GOV-07 retired rolling-output byte baselines. GOV-08
replaced the accumulated ordinary suite with the trigger-specific inventory in
`docs/TEST_TRIGGER_MATRIX.md`; GOV-09 removed post-acceptance UI automation.
No workflow may invoke unbounded pytest.

Before Gate 5, map every new or affected required validation to its exact test
or check, invocation, runtime environment and identity, existing evidence, and
cloud-only remainder. Confirm that selection logic actually executes the test,
that local simulation and publication identities are not confused, that
platform skips have an identified evidence owner, and that the asserted object
is the object the requirement protects. Read existing commands and configuration
first, reuse valid evidence, and run only the smallest check needed for a
specific unproved risk. Local Acceptance normally reports only whether this
mapping is complete, any unresolved exception, and the evidence that remains
cloud-only. Keep detail traceable in existing execution records; do not create
a permanent checklist or substitute an unsupported assertion that review
occurred.

At Gate 5, present the owner with the original declaration, the actual changed
artifact list, the relevant source or rendered diff, and verification matched
to the impact: browser behavior for `user_visible_ui`, field and consumer
evidence for `statistical_json_structure`, and compatibility plus Pages
evidence for `public_path`. A Phase 12 UI task, for example, declares
`user_visible_ui`, runs its focused renderer and browser check during Gate 3,
and shows the owner the final changed state and URL before acceptance. That
Owner review is the final UI acceptance evidence. Do not rerun automated UI or
browser tests afterward unless a user-visible file changes.

Acceptance covers the objective and task delta; product, business, statistical,
editorial, and security meaning; reviewed visible and public-path results;
artifact impact; Schema, data, retention, and privacy boundaries; protected
scope; and every decision requiring human judgment. Record the exact base and
head or staged tree, complete changed paths, and supporting evidence as the
original acceptance anchor. Later repair evidence supplements that anchor; it
never replaces or reinterprets it.

After acceptance, commit the unchanged reviewed UI tree and print its subject
marker with:

`.\.venv\Scripts\python.exe -B ci_master_admission.py
--owner-ui-marker-from origin/master`

Put the printed `owner-ui-accepted` marker in the PR body. The digest contains
only changed `index.html`, `assets/**`, and `melee/**` paths and their Git blob
identities. Status, test, package, and governance edits therefore do not
invalidate a UI review. PR admission recalculates the digest from the complete
GitHub file list and stops immediately if the marker is absent, duplicated, or
stale; it never substitutes another UI test. An active marker or
`user_visible_ui` declaration without a changed user-visible path also stops.

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

An explicit Owner instruction in the active conversation starts only the exact
named task and lane; no STATUS-only authorization change is required. Before
Owner acceptance, separate authorization is required for remote writes. Owner
acceptance then authorizes local commit, push, one Ready pull request,
required-check waiting, merge, and the accepted task's applicable publication
or production completion without repeated prompts, including an eligible
bounded repair before merge. The accepted subject is the approved objective,
semantic and visible result, protected scope, and task delta. It need not retain
an obsolete base commit, but may move only through the bounded repair and
mechanical refresh procedures below. A failed required check closes the merge
gate while the failure remains; apply the repair eligibility and limit rules
below before deciding whether Owner re-entry is required. Stop and return to the
Owner when those rules require it, the accepted subject or scope changes,
mechanical proof fails, an unproved semantic dependency appears, permissions
block the documented path, or a new product, statistical, editorial, or security
decision is required.
Acceptance never carries to another task or phase, unrelated credentials,
force-push, repository settings, secrets, or destructive action outside the
accepted contract.

Prohibited operations are Full access, direct development on `master`, reading
or copying credentials, protected-source modification, cross-project access,
force-push, and automatic next-task startup.

## Validation-failure handling

A validation failure does not itself require new Owner authorization. Before
acceptance, Codex may diagnose and repair it locally when the repair remains
within the approved task objective, introduces no unapproved semantics,
accesses no protected resource, requires no remote write, preserves the intended
validation guarantee, and is fully disclosed. After acceptance and before
merge, diagnosis, repair, local validation, commit, and same-PR publication may
continue only under the bounded-repair rules below. Local authority never
creates remote authority that has not yet been granted. Stop when completion
would require an unresolved human decision, material task or phase expansion,
sensitive access, protected-environment modification, acceptance of unexplained
production behavior, weakened validation, unauthorized remote write, or an
explicitly protected or prohibited path.

## Accepted-task bounded repair

After Gate 5 and before merge, an unsatisfied required validation closes the
merge gate but does not automatically require new repair authorization. A
repair may continue only when every condition below is proved:

1. The accepted objective, semantic and visible result, and product, business,
   statistical, editorial, and security decisions remain unchanged.
2. Artifact impact, public paths, Schemas, data, retention, and privacy
   boundaries remain unchanged.
3. Protected scope and explicit prohibited paths or resources remain untouched.
4. The repair adds no dependency, credential, secret, permission, repository
   setting, or external-service authority.
5. The intended validation guarantee remains at least as strong and the repair
   creates no new human policy decision.
6. The changed implementation, invocation, environment, harness, or fixture
   directly restores an accepted requirement or its effective validation, with
   a concrete supporting diff and evidence.
7. The work remains on the same task, branch, and unmerged pull request, and the
   repair-round limit remains available.

For each unsatisfied validation, first record the exact stage, command or test,
commit, environment, and log, then classify the cause as an implementation
defect, test-definition error, execution-entry omission, environment problem,
or infrastructure problem. Inspect only the directly connected selection
condition, invocation, runtime identity, fixture, and output criterion. Every
rerun must state what the prior failure supports, what evidence or hypothesis
changed, and what the smallest next check will prove. Without a new input,
diagnosis, or hypothesis, do not repeat the command. If the same root cause
recurs after repair, diagnose it again and stop when no evidenced in-scope next
step exists. If a test expectation materially conflicts with or leaves the
accepted requirement ambiguous, return to the Owner instead of choosing the
easier interpretation.

Required failing tests may not be deleted, skipped, xfailed, weakened, narrowed,
or rewritten to accept noncompliant behavior. Do not bypass a validator, weaken
fail-closed behavior, suppress a required trigger, or make a real-identity check
permanently unreachable. A disclosed platform exception remains an exception,
not passing evidence; its required complementary environment must be named.

The original acceptance anchor remains immutable. A legal repair may change the
implementation diff, tree, commit, and pull-request head. For every repair,
record the original anchor; the before and after commits; changed paths and
diff; the accepted requirement restored; affected validation; and final result.
Prove preservation from the actual delta, unchanged artifacts, and focused or
existing evidence. Evidence is invalidated only where the implementation,
fixture, environment, or input could affect it. Old-head CI never proves a new
head, and every new head must satisfy its exact required checks. An unsupported
preservation claim is a stop condition.

An `owner-ui-accepted` marker remains valid only under its existing blob-subject
rules. A repair that invalidates the marker or changes an Owner-reviewed UI or
public artifact returns to Gate 5; visual similarity is not reusable evidence.
Repair and accepted-task base refresh have separate counters and separate proof.
After a legal repair, its latest verified head is the task head to preserve in
the refresh procedure while the original acceptance anchor and repair history
remain recorded. Stop if the existing refresh helper cannot express or prove
that relationship. A mixed repair and refresh cannot evade either limit.

One repair round begins when an unsatisfied validation is followed by publishing
one repair group to the same pull request; publishing that head consumes the
round even if its run is later cancelled. Local diagnosis does not consume a
round. At most two post-acceptance remote repair rounds are allowed for one task,
and the count survives renamed failures, branch changes, new conversations, and
repeat acceptance. After the second round, any unsatisfied required validation
returns to the Owner unless the Owner explicitly adds a limited allowance while
preserving the accumulated count.

Before every repair-head remote write, prepare the accurate pull-request body
and run the existing publication preflight against the exact base and head, with
workflow scope when applicable. Only `READY` permits the documented
command-scoped push to the same branch and Ready pull request. Do not force-push,
rebase published history, or create a replacement pull request. Return to the
Owner immediately when eligibility cannot be proved, the limit is exhausted,
the accepted subject or a protected boundary changes, a new human decision or
privilege is needed, validation would weaken, exact refresh or merge proof
fails, or permissions block the documented path. The return report identifies
the root cause and evidence, attempted repairs, accumulated rounds, affected
boundary, and smallest next option.

These repair rules end at merge. A post-merge publication or production failure
uses only an already applicable recovery authority; otherwise diagnose and
report without rollback, settings changes, dispatch, or a new repair pull
request. The observation-comment permission below permits evidence maintenance,
not code repair or deployment. DEC-165 makes this section effective only after
the governance change that introduced it merges; that governance task itself
completes under the prior failure-stop rule.

## Owner-minimal-operation observation

After DEC-165 takes effect, lock the first three ordinary engineering tasks that
have completed Gate 5 and first enter a Ready pull request, ordered by the
GitHub timestamp of Ready creation or first Draft-to-Ready conversion. Exclude
the DEC-165 governance task, consultation, and independent governance work.
Lock each sample at first Ready even if it later blocks, fails, is cancelled, or
does not complete; do not replace it with a later success. Count Owner re-entry
from that task's first Gate 5 acceptance through complete Remote Completion,
including pre-PR and post-merge events. Determine the sequence from all
qualifying pull requests, not only those that already contain an observation
comment. A task that never enters Ready is not a sample. Uncertain ordering or
eligibility is reported as insufficient evidence rather than guessed.

Each sampled task uses exactly one top-level comment on its existing pull
request as its observation and repair ledger. Create it once after first Ready,
then update the same comment by verified ID. Match the fixed marker, task ID, and
author identity; never select the last comment. Multiple matches or uncertain
identity stop evidence maintenance. Gate 5 completion authority includes this
one comment's creation and updates, including a final post-merge evidence update,
but grants no other comment, code, deployment, or pull-request authority. Record
the returned comment ID and URL and cite that URL from the existing task report.
An `evidence persistence blocker` report must preserve the unsaved content when
creation or update fails; the sample remains locked and is not replaced.

Use this format:

```text
<!-- owner-minimal-operation-observation:v1 -->
Owner Minimal Operation observation
- task_id / pr_url:
- first_ready_at / evidence:
- first_acceptance_at / accepted_subject_reference:
- status: completed | blocked | cancelled | in_progress
- first_required_validation_satisfied: yes | no | pending
- avoidable_validation_omission: yes | no | unknown
- mechanical_owner_reentry: <N>
- decision_owner_reentry: <N>
- owner_reentry_events: <none, or one short entry per request>
  - request_reference / reason:
    category: mechanical | decision
    stage: pre_pr | pre_merge | post_merge
    repair_authority_available: yes | no | unknown
    authority_reason: <within_scope | post_merge | limit_exhausted | permission_boundary | other reason>
- repair_rounds: <N>
- repeated_root_cause: yes | no | unknown
- authority_compliant: yes | no | unknown
- validation_weakened: yes | no | unknown
- accepted_subject_preserved: yes | no | unknown
- repair_evidence: <failure, paths, before/after commits, checks, links; or none>
```

`first_required_validation_satisfied` is `no` for a confirmed missing,
unexecuted, or invalid required check and `pending` only while normal evidence
is outstanding. `avoidable_validation_omission` requires evidence that Gate 4
could have found the omission from existing entries or environment assumptions.
Mechanical re-entry counts technical requests needed to continue the same task;
decision re-entry counts a new product, business, editorial, statistical, or
security decision. A technical request remains mechanical when authority was
unavailable, the repair limit was exhausted, it occurred post-merge, or the
Owner was asked to accept the same mechanical repair again. Progress updates,
completion reports, and later-task discussion do not count. Record each mixed
request once under its primary reason, with its stage and then-current authority.
A repeated root cause requires evidence that the same cause recurred
after repair or an explicit prevention requirement. Authority compliance,
validation strength, and accepted-subject preservation are independent findings;
use `unknown` when evidence is insufficient. An unnecessary Owner prompt adds
operation burden but is not by itself an authority violation; a correct stop
without repair authority remains compliant. `validation_weakened: yes` is a
boundary violation. No repair means zero rounds and `repair_evidence: none`.

The pull-request body remains the sole machine task declaration and must still
carry the exact current head, artifact impact, file operations, accepted subject,
and publication statements required by admission. The comment never replaces or
mutates that body. Do not create a file, issue, tracker, database, YAML or STATUS
field, CI artifact, dashboard, automation, or pilot task for this observation.

When the third sample reaches Remote Completion or its stop report, update that
sample's comment once with a three-task summary linking all three comment URLs.
Report three separate conclusions: Owner operation burden from mechanical and
decision re-entry; validation execution quality from omissions, first required
validation, repeated causes, and repair rounds; and authority and validation
boundaries from compliance, validation strength, and subject preservation.
Give a final observation-window conclusion only when all three tasks are
complete with sufficient comment evidence; otherwise report current facts and
unknowns. If no sample used bounded repair, state that the repair branch lacks a
real sample. Conclusions apply only to the Ready-PR observation window and do
not prove that all post-acceptance tasks avoid mechanical interruption.
Observation findings never authorize a new governance task.

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
2. **Production candidate validation** runs after authorized fetching and generation but before staging or publication. It compares the candidate with a baseline snapshot captured at the start of the run, permits only declared generated-data paths, rejects deletions and cross-product writes, parses changed JSON and YAML, verifies event and match document shape, prevents count regression, and retains strict classification, repository, rule, Schema, value-independent output invariants, generated consumer-contract, and exactly one MTGO plus one Melee real-number rendering smoke. Candidate checks derive their expectations from the candidate and specifications rather than historical hard-coded bytes or tournament values.
3. **Publication confirmation** reuses that candidate evidence. The immutable build artifact, its SHA-256, the generation-subject SHA-256, producer run and attempt, source commit, and generated publication commit are bound together. After push, confirmation checks the clean workspace and exact remote `master` SHA; Pages then verifies the same commit ancestry, commit trailers, producer jobs, artifact digest, and published bytes without rerunning candidate tests.

A clean-checkout production smoke proves only that the commands about to run
still cross their offline entry boundaries. It is not evidence that newly
fetched data is acceptable. The production candidate checks the current data
increment once at the output gate. Adding a new generated path or allowing an
automatic deletion requires explicit review of the candidate publication
boundary.

After fetching, the production workflow hashes the complete generation subject.
If that digest equals the latest published `Generation-Subject-SHA256` trailer,
the existing published bytes remain authoritative and the workflow skips the
CLI baseline, generation, candidate validation, packaging, publication, and
Pages dispatch. A missing prior trailer or any changed subject requires one new
candidate build and one validation pass.

### Allowlisted Pages build and cutover

`build_pages_artifact.py` is the repository-owned Pages packaging boundary. It
must build into a new directory outside the checkout from
`configs/pages_publication.json`, preserve source bytes, validate the complete
event `434455` compatibility closure, reject symbolic links and unsafe paths,
and report repository, data-tree, artifact, protected-file, and excluded-file
sizes. Pull requests may build the candidate but must not deploy it. Automatic
`master` deployment is path-filtered to the actual site inputs. Governance,
test, and other excluded-path changes do not start Pages. The deploy job may run
only for such a relevant `master` push or an accepted explicit dispatch on
`master`, and has only `pages: write` and `id-token: write`; it must not receive
repository write access or persisted Git credentials.

The only generated overlay currently admitted by that boundary is
`landing_card_images`, published under `assets/card-cache/v1/`. Its source
directory must be outside the checkout, match the current repository's
four-week Landing feature subject, contain no symbolic link or undeclared
file, and pass manifest byte and SHA-256 verification before copying. Pages
first looks for a non-expired `master` artifact named by that subject digest;
on a miss it builds from Scryfall Bulk Data and the image CDN. Pull requests
may build or reuse and verify the overlay but cannot retain it or deploy.
Only a relevant `master` push or accepted `master` dispatch may retain the
verified cache for 90 days. This process grants no repository write permission,
does not commit image binaries, and fails before Pages upload if any current
card is unresolved or invalid.

When an active MTGO production run finds that remote `master` no longer equals
its immutable source commit, it must not publish, rebase, or force-push the old
candidate. The first stale run may request one replacement `update.yml` run on
current `master`; the replacement repeats the complete production pipeline and
cannot request a third run. This internal bounded handoff is part of the
already-triggered scheduled or explicitly dispatched production operation. It
does not grant a user or agent standing authority to dispatch production, reuse
old candidate evidence, or close the failure Issue.

If the production push succeeds before another commit advances `master`, the
publish job may continue only after proving its generated-data commit remains
an ancestor of the current tip. The allowlisted Pages workflow still admits and
compares the exact production evidence; a diverged commit or content mismatch
fails closed.

When a production data publication changes `master`, its publish job must first
confirm the remote `master` commit and then explicitly dispatch the allowlisted
Pages workflow on `master`, as defined by DEC-084. GitHub does not trigger the
Pages push workflow from a commit made with that production workflow's own
`GITHUB_TOKEN`. The production dispatch must carry the exact publication commit,
producer run and attempt, source commit, generation-subject digest, and validated
output digest. Partial evidence fails closed. An explicitly authorized manual or
dispatch carries none of those production fields and remains a separate path.
An exact-evidence recovery carries all six fields and binds them to the immutable
master dispatch subject. A no-change production run does not dispatch Pages;
pull-request builds remain non-deploying, and the Pages deployment job retains
its existing no-repository-write boundary.

After a production deployment, do not rerun candidate, Schema, invariant,
consumer, or browser tests. The minimum downstream confirmation is the bound
publication SHA plus HTTP availability of `index.html`, `melee/index.html`, and
`stats/catalog.json`, once for that deployment.

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

The retained Python set is the explicit trigger inventory in
`docs/TEST_TRIGGER_MATRIX.md`. A broad or unfamiliar path is not a reason to run
every retained test; unknown evidence stops for classification instead.

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

## Accepted-task base refresh

Owner acceptance binds the accepted task delta and result, not a permanently
fixed base. When `master` advances after acceptance, define:

- `A` as the base on which the Owner accepted the task;
- `B` as the accepted task head;
- `C` as the newly fetched current `master`; and
- `D` as the candidate produced by merging `C` into the task branch at `B`.

If `C` equals `A`, no refresh is needed. Otherwise, automation may continue
only when all of the following are mechanically proved:

1. `A` is an ancestor of both `B` and `C`, and `A..B` contains a task delta;
2. the path operations in `A..B` and `A..C` do not overlap, including the
   footprints of modifications, deletions, and renames;
3. merging `C` into the branch at `B` produces no conflict and `D` has exact
   parents `B,C` in that order;
4. the `C..D` operation stream exactly equals the accepted `A..B` operation
   stream, and every task path retains its exact accepted Git tree entry from
   `B`; therefore non-task content in `D` remains exactly `C`; and
5. the existing trigger matrix and publication preflight are rerun against the
   exact combined subject with base `C` and head `D`.

Use the following two-stage operational path. Record the resolved full SHAs as
`A`, `B`, `C`, and `D`; placeholders below are not persistent state:

```powershell
git fetch --no-tags origin `
  refs/heads/master:refs/remotes/origin/master
git rev-parse --verify <A>^{commit}
git rev-parse --verify <B>^{commit}
git rev-parse --verify origin/master^{commit}  # record as C
git rev-parse --verify HEAD                    # must equal B

python -B ci_master_admission.py --verify-accepted-refresh `
  --accepted-base <A> --accepted-head <B> `
  --current-base <C> `
  --repository-root <workspace>

# Continue only after READY_TO_MERGE.
git merge --no-ff --no-edit <C>
git rev-parse --verify HEAD                    # record as D

python -B ci_master_admission.py --verify-accepted-refresh `
  --accepted-base <A> --accepted-head <B> `
  --current-base <C> --refreshed-head <D> `
  --repository-root <workspace>
```

The first invocation proves ancestry, disjoint path operations, and a conflict-
free automatic Git merge, then returns `READY_TO_MERGE`. The second additionally
proves the exact parents, operation stream, accepted tree entries, current-base
content, and automatic merge tree, then returns
`READY_FOR_EXACT_VALIDATION`. Neither state proves semantic independence or
authorizes a remote write. `NO_REFRESH_REQUIRED` applies only when `C` equals
`A`; every `STOP` returns to the Owner.

After `READY_FOR_EXACT_VALIDATION`, classify the exact local `C..D` diff with
`ci_master_admission.py --validate-pr-body <body-file> --base-commit <C>
--head-commit <D> --repository-root <workspace>`, run only the focused commands
selected by that output and `docs/TEST_TRIGGER_MATRIX.md`, and then run the
existing publication preflight with `-BaseCommit <C> -HeadCommit <D>`. Publish
through the documented command-scoped path. Pushing `D` to an existing PR
branch triggers `synchronize`, which must validate that exact combined subject;
a not-yet-published task follows the ordinary Ready-PR opening path with the
same `C,D` subject. Evidence from old `A..B` is invalid for both paths.

Do not build a general dependency graph, semantic-impact engine, or persistent
dependency registry for this decision. If review exposes a semantic dependency
that cannot be proved safe mechanically, a product-behavior or statistical-
meaning change, or any change to the accepted result, stop and return to the
Owner. Merge conflicts, task-path overlap, parent mismatch, and content drift
also stop. The PR #351 `A/B/C/M` shape is retained as a synthetic successful
policy case, while exact-merge admission remains fail closed.

One accepted task may make at most two refresh attempts before returning to the
Owner. This counter exists only in the active completion run; never persist it
in STATUS, a registry, or another governance layer. Do not force-push. After a
successful refresh, run the existing publication preflight against `C,D`, push
the same branch by the documented command-scoped path, let the `synchronize`
event validate the exact combined subject, refetch `master` immediately before
merge, and apply this procedure again only within the remaining retry bound.

When a bounded repair precedes refresh, substitute its latest legally verified
head for the task head `B` used by this mechanical procedure, while retaining
the original Gate 5 anchor and complete repair evidence. This substitution does
not reset either counter or reuse old-head CI. Stop when the helper cannot prove
the resulting exact subject.

## Publication preflight and records

Owner acceptance supplies Gate 6 completion authority for the exact accepted
task. Before the first remote write, and again after any accepted-task base
refresh:

1. confirm the final local commit, clean status, current branch, and intended
   base;
2. prepare the exact PR body file that will be supplied to `gh pr create`,
   replacing the template's invalid artifact-impact placeholder and adding any
   required file-operation or Owner UI evidence;
3. inspect the fetch and disabled push URLs;
4. in the same execution context that will publish, run the repository's only
   credential-verdict and PR-contract entry point against the final commits:
   `tools/github_publication_preflight.ps1 -ActualPublicationContext
   -PrBodyFile <body-file> -BaseCommit <base-sha> -HeadCommit <head-sha>
   -PythonExecutable <approved-python-executable>`; use the same interpreter
   used for local checks. Codex must use
   `require_escalated` for this call;
5. add `-RequireWorkflowScope` when `.github/workflows/**` changed;
6. require the script's `READY` state before publication;
7. keep the workspace's disabled push sentinel and empty local credential
   helper intact; do not restore or persist a real push URL;
8. use only the repository-specific `gh` publication path below, with the same
   unchanged head commit and body file validated above.

The preflight states have one handling rule each:

- `READY` continues through the commands below;
- `PR_CONTRACT_INVALID` reports the exact missing, invalid, stale, or mismatched
  local evidence and stops before any GitHub call;
- `LOCAL_VALIDATION_ERROR` reports a broken local validator invocation and
  stops before any GitHub call;
- `RETRY_ACTUAL_CONTEXT` retries the same script once in the actual publication
  context without an Owner prompt, then reports a context failure if unchanged;
- `AUTH_REJECTED` stops and permits an Owner login request;
- `PERMISSION_MISSING` reports the exact identity, push-permission, or workflow-
  scope mismatch; and
- `NETWORK_ERROR` reports network or GitHub availability failure.

The preflight first uses `ci_master_admission.py` to derive GitHub-compatible
file evidence from the exact local base-to-head diff and applies the same PR
body classifier used by CI. It then reads the active account, authentication
state, and scopes from `gh auth status --json hosts`; JSON mode requires
inspecting the structured account state rather than treating exit code zero as
authentication success. It does not depend on a second authenticated-user API
request. The repository permission endpoint remains authoritative for push
permission, and GitHub HTTP 5xx responses are `NETWORK_ERROR`, not missing
credential context.

Do not use a push as a credential probe or interpret raw `gh` output as a
credential verdict. Preserve the local commit and disabled push sentinel when
the state is not `READY`.

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
do not override the preflight state. Report authentication rejection only when
the script returns `AUTH_REJECTED`; otherwise retain its exact failure class and
retry only the documented path.

A pull request cannot contain its own not-yet-known merge commit. Therefore,
implementation pull requests should record stable task results and validation,
while GitHub remains the source of truth for their publication steps and merge
identity. Do not automatically create a second status-only pull request after
every implementation pull request. Close exact merge metadata in the next
already-authorized governance or development change, or at phase closeout. If
the owner explicitly requires immediate exact metadata, create at most one
intentional documentation closure change; never create a second change solely
to finalize that closure change.

Before merging the implementation PR, update durable project state in that
same PR only when the phase, active program or weekly cycle, unresolved
blockers or decisions, or paused activities changed. Do not invent not-yet-
known identifiers. Report the actual PR number, merge SHA, workflow run IDs,
and Pages result in the final handoff. Leave those exact publication fields to
Git and GitHub. Do not create or switch to a
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
Git whenever those systems already record it. `docs/STATUS.yaml` stores only
durable phase or program state, active weekly-cycle state, unresolved blockers
or decisions, and paused activities; ordinary tasks do not require a separate
history entry by default. Add durable history only when the evidence is not
otherwise preserved or a phase-closeout contract requires it.

This rule reduces both diagnostic noise and repeated work. A truncated output
is a signal to narrow the query, not to repeat the same broad read.

The evidence behind these controls is summarized in
`docs/audits/DEVELOPMENT_PROCESS_RETROSPECTIVE_2026-07.md`.

### Live-document maintenance

Keep the always-read layer bounded by responsibility:

- `AGENTS.md` contains only stable every-task steps, hard boundaries, and
  conditional reading pointers;
- `docs/STATUS.yaml` contains only durable phase or program state, active
  weekly-cycle state, unresolved blockers or decisions, and paused activities;
- `docs/ROADMAP.md` contains the active phase, useful future phases, and their
  acceptance criteria; and
- `docs/history/` preserves completed or superseded detail and never
  authorizes work.

When a completed task has detailed material in the live roadmap, move that
material to the corresponding phase history file in the same accepted task,
update `docs/history/README.md`, and leave only the remaining plan plus one
compact pointer. GitHub and Git retain ordinary validation, publication, and
merge identifiers; do not copy them into a growing live narrative.

## Language

Repository and Git/GitHub content must be English. Codex contracts, criteria, stop conditions, and reports must be English. User-facing orchestration outside the repository may be Chinese. Preserve commands, paths, identifiers, hashes, package names, and raw output. Do not alter existing files solely for language or style consistency. Stop if non-English repository content could be introduced.

## Pause and authorization

A paused project permits read-only analysis and governance or maintenance tasks
explicitly authorized in the active Owner conversation. A pause does not
authorize product development. One task's authorization does not authorize
another task.

## Disposal

Retain task workspaces until acceptance and any separately authorized publication are complete. Never push capability-probe workspaces. Disposal must be deliberate and must not affect the protected source repository.
