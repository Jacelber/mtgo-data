# Gate 4 master-admission design

## Purpose

Gate 4 removes one specific duplication: a normal pull request that has already
passed the complete clean-checkout suite should not repeat that same complete
suite after an exact merge to `master`.

This is not a test reduction. Pull requests still run static validation and
both exact complementary pytest shards. Direct pushes and every unproven
`master` update still run that same complete validation.

## Trigger decision

The workflow begins with a read-only `admission` job. Its default and fail-safe
result is `full`.

| Event or evidence | Selected path |
| --- | --- |
| `pull_request` | Complete static validation and both pytest shards |
| `workflow_dispatch` | Complete static validation and both pytest shards |
| Direct one-parent push to `master` | Complete static validation and both pytest shards |
| Squash, rebase, octopus, or otherwise non-exact merge | Complete static validation and both pytest shards |
| GitHub API error, timeout, malformed response, missing job, stale run, or ambiguous PR | Complete static validation and both pytest shards |
| Exact two-parent PR merge with all predicates below | Lightweight merged-PR confirmation |

The lightweight path requires all of these predicates:

1. the event is a `push` to `refs/heads/master`;
2. the pushed commit has exactly two parents;
3. GitHub associates exactly one merged PR with that merge commit;
4. the PR targets `master`;
5. the PR merge SHA equals the pushed SHA;
6. the PR base and head SHAs equal the merge commit's first and second parents;
7. a successful run of `.github/workflows/ci.yml` exists for that exact PR head;
8. the run completed before the PR was merged;
9. static validation and both pytest shards each confirm that their checked-out
   merge commit's parents equal the PR event's exact base and head SHAs;
10. the same run reports success for static validation, the ordinary pytest
    shard, the committed-baseline pytest shard, and the established aggregate
    check; and
11. the aggregate job contains a successful subject step recording the exact
    PR number, base SHA, and head SHA.

The last predicate proves that the successful PR run used the same base/head
pair as the final merge. A successful run for an older base, another PR, or only
the same head commit is insufficient.

## Retained validation and failure visibility

The established check name remains `Repository validation (Python 3.12)`.

- In `full` mode it passes only after static validation and both pytest shards
  pass.
- In `pr-confirmation` mode it passes only after the admission evidence is
  complete and the lightweight confirmation job succeeds.
- Any unexpected mix of completed and skipped jobs fails the aggregate check.
- The admission reason, PR number, and prior workflow run ID are written to the
  workflow summary.

The admission token has only `actions: read`, `contents: read`, and
`pull-requests: read`. The workflow cannot fetch tournament data, commit, push,
or publish.

## Production publication boundary

The production workflow is unchanged. It still runs:

1. the complete clean-checkout pytest suite before fetching;
2. production-candidate validation after fetching and generation; and
3. published-commit and clean-workspace confirmation after pushing.

Generated commits pushed with the production workflow's built-in
`GITHUB_TOKEN` do not recursively trigger the ordinary `push` workflow. If a
future publisher does trigger it, the generated commit is a direct one-parent
push and therefore selects `full`, never `pr-confirmation`.

## Tests and acceptance

Local deterministic tests cover:

- the one allowed exact-merge confirmation;
- direct-push fallback;
- base/head mismatch;
- a missing pytest shard;
- a mismatched PR/base/head subject;
- validation that completed after merge; and
- GitHub API failure.

Remote acceptance requires one real PR and its resulting `master` run:

1. the PR run must execute static validation and both pytest shards;
2. all collected tests must be selected exactly once across the two shards;
3. the aggregate PR check must pass and expose the exact subject step;
4. after an exact merge, the `master` run must report
   `exact_validated_merge`;
5. the post-merge run must skip static validation and both pytest shards;
6. the lightweight confirmation and established aggregate check must pass; and
7. Pages behavior and the production workflow must remain unchanged.

## Remote acceptance result

Gate 4 was published through pull request 120. Its exact PR validation run
`30344264614` passed static validation and both complementary pytest shards:
555 ordinary tests and nine committed-baseline tests, with 564 tests selected
exactly once and the aggregate check successful.

The resulting exact two-parent merge
`491f5d79c7931e429272225b12485b82eb33d178` triggered master run
`30345131617`. Admission reported `exact_validated_merge`, identified pull
request 120 and prior run `30344264614`, skipped static validation and both
pytest shards, and passed the lightweight confirmation plus the established
aggregate check. The run completed in approximately 35 seconds. Pages run
`30345130308` also passed.

This evidence satisfies the remote acceptance criteria. Direct pushes,
non-exact merges, manual dispatches, and missing or ambiguous evidence continue
to fail safe to the complete suite.

## Rollback

Rollback is a single workflow change: remove the admission and confirmation
jobs, remove their conditions, and restore the aggregate job to require static
validation and pytest on every trigger. `ci_master_admission.py` and its focused
tests can then be removed. No data, statistics, schemas, production workflow, or
public path needs migration.
