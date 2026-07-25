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
| Matched PR and merged-`master` pairs | 4 historical pairs | 1 pair (PR #97) | 6 instrumented pairs | 5 pairs |
| Production data-update runs | 3 successful step-duration examples | 0 marker-group reports | 3 post-plan successful runs | 3 runs |
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
