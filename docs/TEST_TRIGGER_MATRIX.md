# Test trigger matrix

## Rule

The default is no test. Run a check only when its named trigger occurs, use the
smallest listed subject, and do not repeat successful evidence for an unchanged
tree or generated candidate. A broad or unfamiliar path is not a reason to run
an unbounded suite.

## Retained Python tests

| File or node | Trigger | Purpose | Minimum subject |
| --- | --- | --- | --- |
| `tests/test_cli_smoke.py::test_mtgo_cli_smoke` | A post-fetch MTGO generation subject is new and generation will run | Prove the installed MTGO parser, format gate, and dispatch path can run offline before generating | One enabled format and one stubbed command |
| `tests/test_cli_smoke.py::test_melee_cli_smoke` | Melee production before live collection | Prove the Melee command accepts one verified event and remains a zero-write dry run | One registry event and one fake response plan |
| `tests/test_cli_smoke.py::test_catalog_cli_smoke` | Either production workflow has a new generation subject and will generate the catalog | Prove one minimal format can produce a consumer catalog | One temporary format with no available products |
| `tests/test_melee_privacy_validation.py` | Melee production before live collection, or a privacy boundary change | Prove the smallest minimized resource is accepted and a prohibited persisted key is rejected independently of Schema permissiveness | One valid tournament document and one invalid key |
| `tests/test_generated_consumer_contracts.py` | MTGO candidate generated, before packaging | Prove the newly generated candidate remains internally consumable | Current candidate documents only |
| `tests/test_mtgo_top8_restatement.py` | Top 8 generator, classifier digest, lifecycle contract, or Top 8 Schema changes | Prove retained source facts stay fixed while current-classifier identities restate deterministically, including explicit Unknown | Three synthetic source/classifier cases |
| `tests/test_mtgo_pickup_selection.py` and `tests/test_mtgo_pickup_provenance.py` | Weekly Pickup screening policy, representative selection, or candidate provenance changes | Prove exact Top 8 gating, route thresholds, continuity, reason merging, subtype-or-parent build comparison, later-date ties, and fail-closed provenance | Synthetic selection and provenance subjects only |
| `tests/test_documentation_history.py` | A live governance document changes | Enforce only the bounded live-status structure and history pointer | `docs/STATUS.yaml` only |
| `tests/test_ci_master_admission.py` and `tests/test_ci_workflow.py` | CI admission or workflow control changes | Prove known paths route minimally, unknown evidence stops, and PR CI contains no heavy fallback | Admission logic and workflow text only |
| `tests/test_weekly_maintenance_readiness.py` | Weekly readiness generator or private readiness Schema changes | Prove exact-week binding, complete unresolved-Unknown retention and decklists, strict intentional-random separation, Pickup availability, deterministic digesting, and fail-closed cross-format lifecycle | Synthetic Standard and Modern handoff only |

The public data/output rows remain bounded to their named subjects. The
documentation and CI rows are control-plane checks. The Pickup and weekly-
readiness rows are private review and handoff contracts; neither runs in a
production baseline.

## Non-pytest validators and UI checks

| Trigger | Command or check | Purpose | Repeat rule |
| --- | --- | --- | --- |
| Any targeted PR | `python -B validate_repository.py` | Catch broken repository references introduced by that PR | Once on the final PR head |
| Maintained Python changes | Ruff and mypy commands in `ci.yml` | Catch syntax/import and maintained type-contract failures | Once on the final PR head |
| Rules or public-data contract changes | `validate_rules.py` and `validate_schemas.py` | Reject invalid rules or public JSON structure | Once on the final PR head |
| Matchup model, matchup labels, or matchup i18n logic changes | `node --test tests/js/phase8-matchup-model.test.js` | Catch a broken matchup calculation or label contract before Owner browser review | Once on the final visible tree before Owner review |
| Browser request, cache, retry, refresh, or runtime-loading logic changes | `node --test tests/js/phase8-runtime.test.js` | Catch a broken request lifecycle before Owner browser review | Once on the final visible tree before Owner review |
| Owner completes browser review of a user-visible change | Record the `owner-ui-accepted` digest for changed `index.html`, `assets/**`, and `melee/**` blobs | Bind the PR to exactly the visible files the Owner reviewed without rerunning UI automation | Once after acceptance and the unchanged local commit; PR admission only compares the digest |
| MTGO candidate generated | Candidate boundary, repository, rules, Schema, output-invariant, consumer, and the two `production-pages.spec.js` rendering smokes in `update.yml` | Block publication when either public product cannot render a real number | Once for that immutable candidate before packaging |
| Melee candidate generated | Candidate boundary, repository, rules, and Schema checks in `fetch_melee.yml` | Block an invalid Melee publishable artifact | Once for that immutable candidate before staging |
| Generated commit pushed or exact-evidence recovery authorized | Exact remote-SHA confirmation plus production evidence admission | Bind an ancestor publication commit and its validated artifact digest, generation subject, producer run and attempt, source commit, and successful producer jobs to the immutable master Pages subject whose generated output still matches | Once for that immutable Pages subject; never recompute candidate evidence |
| Relevant site-input path reaches `master` outside production publication | Allowlisted Pages packaging and deployment | Publish an accepted UI, public-data, compatibility, or publication-boundary change | Once for that `master` commit; governance, test, and excluded-path changes do not trigger Pages |
| Production Pages deployment completes | Bound publication SHA and HTTP availability of `index.html`, `melee/index.html`, and `stats/catalog.json` | Confirm the exact admitted deployment has its two entry points and public catalog available | One request per resource for that deployment, with bounded transport retry only |
| GitHub preflight script or authentication-routing rule changes | Run the focused mocked preflight states, then run the script once without `-ActualPublicationContext` and once with it in the actual publication context | Prove ordinary context, structured authentication, permission, scope, and GitHub 5xx states fail closed while the authorized context can return `READY` | Once per final immutable authentication-control tree; never on unrelated tasks |

## No-trigger cases

- Documentation-only changes do not run CLI, data, privacy, or browser tests.
- Code or governance changes do not run a full pytest suite.
- CSS, copy, layout, or ordinary interaction changes with neither retained Node
  trigger receive Owner browser review but no generic automated UI suite.
- Owner acceptance of an unchanged UI subject does not trigger another browser
  run.
- A successful immutable candidate is not recalculated or retested downstream.
- An unchanged generation-subject digest runs no CLI baseline, generator,
  candidate validation, packaging, publication, or Pages job.
- A governance-only, test-only, or other non-site `master` change does not
  trigger Pages.
- Authentication preflight does not run during local development or CI unless
  its script or routing rule changed; operational publication runs it once per
  publication context.
- No change means no test.

## Retired UI checks

GOV-09 retired the generic browser preflight and the accessibility, card
preview, loading/retry, mobile-list, URL-state, and lazy-loading browser suites.
They have no trigger. `production-pages.spec.js` contains only the two output
gate rendering smokes; it is not a PR or ordinary local-development suite.
