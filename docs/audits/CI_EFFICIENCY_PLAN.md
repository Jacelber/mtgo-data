# CI efficiency evidence and decision plan

## Purpose

Reduce publication waiting only when measurement proves that a change preserves
the complete validation guarantee. This plan is a governance aid, not
authorization to skip tests, change triggers, change repository settings, or
modify the production workflow.

## Fixed boundaries

- Pull-request and `master` validation continue to run the complete pytest
  suite until a separately approved replacement has passed its own validation.
- The `committed_baseline` marker remains part of the complete suite and may
  not be omitted, weakened, or run against a mutable production candidate.
- Production candidate validation and post-publication commit confirmation are
  separate guarantees; CI timing evidence does not replace either one.
- Pages deployment, dependency installation, and source fetching are not
  assumed to be bottlenecks. Their measured duration must justify any work.
- No `paths-ignore` rule, test removal, trigger reduction, branch-protection
  change, CI sharding, or production-workflow change may begin from this plan
  alone.

## Evidence already available

The pre-observation audit found four successful historical PR-to-`master`
pairs. Their PR validations lasted 9m05s to 9m48s, their matching `master`
validations lasted 9m03s to 9m59s, and the pytest step occupied approximately
8m22s to 9m10s. Pages deployments lasted approximately 40–55 seconds.

PR #97 is the first instrumented pair. Its PR validation completed in 9m09s;
the matching `master` validation completed in 10m11s, with pytest taking
9m17s. The timing-summary step passed in both runs. The resulting GitHub
summary is the source of truth for marker-group totals and slow-test entries.

The production update workflow exposes step durations, including its complete
pytest step, but does not yet emit the same marker-group timing report. It
must therefore be evaluated as a separate population.

## Sample ledger and minimum collection target

Only completed successful runs count. Cancelled, failed, rerun, manually
aborted, queued-only, or materially different workflow-version runs are
recorded as context but excluded from median calculations.

| Population | Existing usable baseline | Instrumented at plan publication | Minimum before a CI-design decision | Remaining target |
| --- | ---: | ---: | ---: | ---: |
| Matched PR and merged-`master` pairs | 4 historical pairs | 20 pairs (PR #97 through #116) | 6 instrumented pairs | 0 pairs |
| Production data-update runs | 3 successful step-duration examples | 3 post-plan successful runs | 3 post-plan successful runs | 0 runs |
| Pages deployments | 4 successful examples | 1 additional #97 deployment | No collection task unless duration becomes material | 0 |

The six instrumented pairs should come from ordinary approved work, not from
empty commits or artificial benchmark pull requests. For each pair, record the
PR number, head SHA, merge SHA, PR run ID, `master` run ID, workflow version,
job duration, pytest-step duration, ordinary-test call time,
`committed_baseline` call time, selected/completed counts, and the five
slowest test calls. Retain links to the Actions runs rather than copying logs.

For production runs, record run ID, whether publication produced a commit,
job duration, clean-checkout pytest-step duration, fetch duration, generation
duration, candidate-validation duration, and publication-confirmation result.
Do not infer marker-group timings that the current production workflow does
not report.

## Gate 1 review — 2026-07-28

The evidence threshold is met. Twenty successful PR-to-`master` pairs from
PR #97 through PR #116 use the same instrumented CI workflow. Across those
pairs:

- PR jobs have a 595-second median and a 385-to-666-second range;
- PR pytest steps have a 552-second median and a 348-to-612-second range;
- merged-`master` jobs have a 628-second median and a 348-to-666-second range;
- merged-`master` pytest steps have a 578.5-second median and a
  314-to-610-second range;
- pytest therefore occupies approximately 92 percent of both populations.

The latest six pairs have PR and `master` pytest medians of 592 and 596.5
seconds respectively, confirming that repository growth has added roughly
40-to-64 seconds relative to the first six pairs. The same slow calls recur
in all twelve latest runs: Modern fixed-reference regeneration averages
94.71 seconds, Modern Pickup metadata 60.59 seconds, the Standard Phase 3
fixed-reference product 41.19 seconds, and each of three repeated Schema
validation calls approximately 33 seconds.

Production runs `30193812741`, `30220282843`, and `30306215892` use the same
production-workflow version and all completed successfully. Their median job
duration is 901 seconds; the clean-checkout suite contributes 450 seconds,
MTGO event fetching 192 seconds, product statistics 82 seconds, and Videre
fetching 34 seconds. Production remains a separate population and no
marker-group time is inferred.

Gate 1 therefore identifies complete pytest execution as the dominant,
recurrent CI cost and shows more than one minute of plausible optimization
space. This finding authorizes no behavior change by itself. Gate 2 remains
blocked on a separately approved branch-protection review, and any Gate 3
sharding prototype still must prove complete, disjoint collection and measured
wall-clock improvement.

PR #117 run `30327216251` is contextual evidence only and is excluded from
the medians. The former 15-minute job ceiling cancelled the suite at 96
percent before pytest could render seven already-recorded byte-identity
failures. The focused repair restores the exact generated-file byte contract
and raises the safety ceiling to 30 minutes without changing test selection.

## Decision sequence

### Gate 1 — evidence review

Begin only after the sample ledger reaches both minimum targets. Calculate the
median and range for PR job duration, `master` job duration, pytest-step
duration, ordinary-test call time, `committed_baseline` call time, and the
recurrence of the slowest test calls. Compare matching PR and `master` runs;
do not compare unrelated commits as a pair.

Success criterion: the review can name a measured dominant cost and show that
it recurs across the collected sample. Stop with no CI behavior change if
timing is volatile, no single cost dominates, or the apparent saving is below
one minute at the median.

### Gate 2 — branch-protection decision

Before reducing the validation performed after a merge, separately review and
authorize `master` branch protection. At minimum, evaluate requiring the PR
validation check and prohibiting force pushes. The current absence of branch
protection or a ruleset means post-merge validation remains a direct-push
safety boundary.

Success criterion: the repository setting and its effects on direct pushes,
PR merges, production-generated commits, and recovery are documented and
owner-approved. Stop if that governance choice is not approved; retain the
existing full `master` validation.

The 2026-07-28 read-only review is recorded in
`docs/audits/CI-BRANCH-PROTECTION.md`. It confirms that no protection or
ruleset is active and identifies a repository ruleset as the minimum viable
control. The proposed rule requires PR validation from the official
`github-actions` integration, blocks deletion and force pushes, and grants
only that integration a bypass for the existing validated production-data
publisher. The authorized disabled-mode creation attempt was rejected with
HTTP 422 because the built-in GitHub Actions integration is not eligible as a
bypass actor for this personal-account ruleset source. No full ruleset was
created. The owner instead approved repository ruleset `19874624`, which is
active on `master` and blocks deletion and non-fast-forward pushes without
changing PR, check, merge, or production-publisher behavior. Gate 3 may
prototype disjoint complete-suite sharding without reducing validation, but
Gate 4 remains closed until a separately approved publisher identity or
admission-check design establishes a mandatory PR-check boundary.

### Gate 3 — optional test-sharding design

Only if Gate 1 identifies test execution as the dominant recurrent cost, design
a local prototype that assigns every collected test exactly once. A likely
candidate is a normal-test job plus a `committed_baseline` job, but that is a
hypothesis rather than a committed architecture.

The prototype must prove all of the following before any trigger change:

1. the union of shard node IDs equals the complete-suite node-ID set;
2. the shards are disjoint;
3. both shards preserve failure exit status and summary output;
4. repository, rule, and Schema validation retain their current coverage;
5. the slowest recurring work is actually parallelized rather than duplicated;
6. the measured wall-clock improvement is at least one minute at the median;
7. no production or public behavior changes.

Stop if the prototype duplicates a dominant baseline, introduces order or
shared-state failures, or cannot demonstrate the stated saving.

The 2026-07-28 local prototype is recorded in
`docs/audits/CI-TEST-SHARDING.md`. Its exact complementary marker expressions
partitioned all 555 pre-change node IDs into 546 ordinary and 9
committed-baseline tests with no intersection, missing IDs, or duplicates.
Independent local runs passed in 337.98 and 135.67 seconds, projecting a
135.67-second critical-path reduction. The workflow prototype retains separate
static validation and an aggregate established check name.

The owner authorized remote publication, and PR #119 run `30337562027` passed
static validation, both exact complementary shards, and the aggregate check.
The remote run selected all 556 tests exactly once: 547 ordinary and 9
committed-baseline. It completed in approximately 10m32s versus the accepted
15m06s serial PR #118 baseline, an observed reduction of approximately 4m34s.
Gate 3 therefore meets its remote acceptance threshold.

### Gate 4 — optional post-merge trigger decision

Consider a lighter `master` confirmation only after Gates 1 through 3 succeed
and branch protection is active. The design must retain a full validation path
for direct pushes and demonstrate that the required PR validation ran against
the mergeable change. Production-generated commits remain subject to their
existing production validation layers.

Success criterion: the design documents exact event predicates, direct-push
handling, failure visibility, rollback, and the validation that is retained.
This is a high-risk governance change and always requires separate owner
authorization and a Sol-high implementation task.

The owner authorized Gate 4 local implementation on 2026-07-28. The isolated
`codex/ci-gate4-master-trigger` task implements a fail-safe admission job:
pull requests and manual runs remain full; direct pushes, non-exact merges,
missing or stale evidence, API failures, and ambiguous metadata remain full;
only a successful PR run that records the final merge's exact PR number, base
SHA, and head SHA may use lightweight post-merge confirmation. The established
aggregate check name is retained, production validation and publication are
unchanged, and the complete predicates and rollback are documented in
`docs/audits/CI-MASTER-ADMISSION.md`. Local deterministic validation is
complete. Gate 4 remains pending owner acceptance, separate remote-publication
authorization, and real PR/post-merge acceptance evidence.

## Explicit non-priorities

Do not work on dependency caching unless fresh evidence shows installation is
material; historical installation time was seconds. Do not optimize Pages
deployment unless its duration becomes material. Do not add broad path filters
because rule, generated-data, schema, workflow, and front-end dependencies are
cross-layer. Do not create benchmark-only PRs just to fill the sample ledger.

## Operating record

After each qualifying PR, merged `master` run, and production run, append one
compact row to this document's sample ledger in the next already-authorized
governance or development change. Do not create a status-only pull request for
each row. At Phase 7 closeout, consolidate the evidence and state whether Gate
1 is met, blocked, or no longer warranted.

## Model guidance

- Evidence collection and ledger updates: Terra medium.
- Branch-protection review, sharding prototype, and trigger redesign: Sol high.
- A narrowly mechanical workflow-summary formatting fix: Sol medium.
