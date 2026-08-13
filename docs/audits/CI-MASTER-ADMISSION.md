# Pull-request validation and master-admission design

## Purpose

CI separates pull-request maturity from validation strength. Draft and Ready
pull requests use the same artifact-impact and changed-file classification.
Locally completed work is published Ready by default; Draft is optional only
for explicitly requested incomplete-work review.

The workflow also avoids repeating an already successful pull-request suite
after an exact two-parent merge to `master`. Direct pushes and every unproven
merge still run complete validation.

## Pull-request classification

The read-only `admission` job defaults and fails safe to `full`. It reads the
single PR-body `artifact-impact` marker and the complete GitHub changed-file
list. Changed files are read in 100-item pages up to the GitHub API's 3,000-file
limit. Added and modified files are the only statuses eligible for a focused
class. Missing, malformed, stale, conflicting, incomplete, over-limit, or
unavailable evidence selects `full`.

| Class | Required evidence | Successful execution jobs |
| --- | --- | --- |
| `focused-docs` | Exactly `internal_diagnostics`; only added or modified Markdown under `docs/audits/` or `docs/history/`; no CI-admission authority document | Admission, focused PR validation, aggregate |
| `focused-ui` | Exactly `user_visible_ui`; only added or modified paths from the explicit CSS/browser-test allowlist | Admission, focused PR validation, Playwright production pages, aggregate |
| `full` | Every other declaration, path, status, or evidence state | Admission, repository/rules/Schemas, both exact pytest shards, Playwright production pages, aggregate |
| `metadata-only` | An `edited` event proves that neither body nor base changed | Admission and aggregate only |

The focused UI allowlist is deliberately limited to:

- `assets/css/phase8-base.css`;
- `assets/css/phase8-candidate.css`;
- `tests/browser/production-pages.spec.js`;
- `tests/browser/url-state.spec.js`; and
- `tests/browser/view-lazy-loading.spec.js`.

Application state, runtime, controllers, data models, i18n, legacy assets, HTML,
public paths, workflows, authoritative documents, backend code, Schemas,
statistics, baselines, generated data, deletion, and rename are not focused UI.
Focused UI runs repository JavaScript validation, the native Node frontend
suite, and the complete applicable Playwright production-page suite.

The workflow does not subscribe to `ready_for_review` or
`converted_to_draft`. A state-only transition therefore creates no duplicate
run. `opened`, `synchronize`, `reopened`, and `edited` remain subscribed because
they can create or change the validation subject. Body and base edits reclassify
the subject; title-only edits take the `metadata-only` aggregate path. Missing
`edited` change metadata selects `full`.

## Exact-merge confirmation

A `push` to `master` may select `pr-confirmation` only when all predicates hold:

1. the pushed commit has exactly two parents;
2. GitHub associates exactly one merged PR targeting `master` with that commit;
3. the merge SHA and the current PR base and head equal the pushed commit and
   its first and second parents;
4. the current PR number, body declaration, merged timestamp, and complete
   changed-file list are readable and internally consistent;
5. current evidence still classifies as `focused-docs`, `focused-ui`, or
   `full`;
6. a successful `.github/workflows/ci.yml` run exists for the exact head and
   completed before merge;
7. its successful job names equal the class matrix above, including exactly one
   aggregate job;
8. the aggregate contains successful steps recording the exact PR number, base
   SHA, head SHA, and validation class; and
9. changed-file evidence is complete across all required pages, while workflow
   run and job responses are complete within their supported single 100-item
   GitHub API page.

A stale run, wrong PR/base/head/workflow/class, missing or extra successful job,
changed declaration, changed file classification, post-merge completion,
pagination, malformed response, timeout, or API error selects `full`.

## Retained guarantees and failure visibility

The established check name remains `Repository validation (Python 3.12)` and is
present for every triggered path. Its shell contract accepts only the five
explicit execution matrices: `focused-docs`, `focused-ui`, `full`,
`metadata-only`, and `pr-confirmation`. Any unexpected success/skip combination
fails.

Complete validation retains Ruff, mypy, actionlint, repository/rule/Schema
validation, both exact complementary pytest shards, strict committed-baseline
tests, and Playwright. The admission token remains limited to `actions: read`,
`contents: read`, and `pull-requests: read`; checkout never persists
credentials. Timeouts, concurrency cancellation, summaries, and failure output
remain explicit. The workflow cannot fetch tournament data, commit, push,
deploy, or publish.

## Production boundary

The production workflow is unchanged. It still runs clean-checkout validation
before fetching, production-candidate validation after generation, and remote
commit confirmation after publication. A direct or otherwise unproved
`master` update always selects `full`.

## Deterministic and remote acceptance

Tests cover Draft/Ready equivalence, each focused class, all mandatory-full
families, malformed declarations, file statuses, unsupported pagination,
title/body/base edits, exact job matrices, current declaration and file
reclassification, stale runs, wrong subjects, API failures, and the retained
complete path.

The GOV-03 pull request itself declares `none` but changes workflow and
authoritative governance paths, so it must select `full` once for its final
unchanged head. Remote acceptance requires that Ready run to pass the complete
matrix and aggregate. Do not create a Draft cycle to test removed triggers.

## Rollback

Rollback restores the preceding workflow and admission implementation from the
parent commit. No data, statistics, Schema, production workflow, public path,
Pages content, or repository setting requires migration.
