# Test trigger matrix

## Rule

The default is no test. Run a check only when its named trigger occurs, use the
smallest listed subject, and do not repeat successful evidence for an unchanged
tree or generated candidate. A broad or unfamiliar path is not a reason to run
an unbounded suite.

## Retained Python tests

| File or node | Trigger | Purpose | Minimum subject |
| --- | --- | --- | --- |
| `tests/test_cli_smoke.py::test_mtgo_cli_smoke` | MTGO production before live collection | Prove the installed MTGO parser, format gate, and dispatch path can run offline | One enabled format and one stubbed command |
| `tests/test_cli_smoke.py::test_melee_cli_smoke` | Melee production before live collection | Prove the Melee command accepts one verified event and remains a zero-write dry run | One registry event and one fake response plan |
| `tests/test_cli_smoke.py::test_catalog_cli_smoke` | Either production workflow before it will generate the catalog | Prove one minimal format can produce a consumer catalog | One temporary format with no available products |
| `tests/test_melee_privacy_validation.py` | Melee production before live collection, or a privacy boundary change | Prove the smallest minimized resource is accepted and a prohibited persisted key is rejected independently of Schema permissiveness | One valid tournament document and one invalid key |
| `tests/test_generated_consumer_contracts.py` | MTGO candidate generated, before packaging | Prove the newly generated candidate remains internally consumable | Current candidate documents only |
| `tests/test_documentation_history.py` | A live governance document changes | Enforce only the bounded live-status structure and history pointer | `docs/STATUS.yaml` only |
| `tests/test_ci_master_admission.py` and `tests/test_ci_workflow.py` | CI admission or workflow control changes | Prove known paths route minimally, unknown evidence stops, and PR CI contains no heavy fallback | Admission logic and workflow text only |

The first five rows are the retained data/output test set. The final two rows
are control-plane checks and never run in a production baseline.

## Non-pytest validators and UI checks

| Trigger | Command or check | Purpose | Repeat rule |
| --- | --- | --- | --- |
| Any targeted PR | `python -B validate_repository.py` | Catch broken repository references introduced by that PR | Once on the final PR head |
| Maintained Python changes | Ruff and mypy commands in `ci.yml` | Catch syntax/import and maintained type-contract failures | Once on the final PR head |
| Rules or public-data contract changes | `validate_rules.py` and `validate_schemas.py` | Reject invalid rules or public JSON structure | Once on the final PR head |
| UI changes | `node --test tests/js/phase8-matchup-model.test.js` | Syntax/model smoke before Owner browser review | Once before the final Owner review |
| MTGO candidate generated | Candidate boundary, repository, rules, Schema, output-invariant, consumer, and `production-pages.spec.js` checks in `update.yml` | Block an invalid publishable artifact | Once for that immutable candidate before packaging |
| Melee candidate generated | Candidate boundary, repository, rules, and Schema checks in `fetch_melee.yml` | Block an invalid Melee publishable artifact | Once for that immutable candidate before staging |
| Generated commit pushed | Exact remote-SHA confirmation | Confirm publication identity without recomputing prior evidence | Once for that commit |

## No-trigger cases

- Documentation-only changes do not run CLI, data, privacy, or browser tests.
- Code or governance changes do not run a full pytest suite.
- Owner acceptance of an unchanged UI subject does not trigger another browser
  run.
- A successful immutable candidate is not recalculated or retested downstream.
- No change means no test.

## UI assets outside GOV-08

The remaining files under `tests/js/` and `tests/browser/` are unchanged by
GOV-08. Only the two commands named above have an automatic trigger. The other
browser specifications have no automatic trigger in the current workflow and
must not be run merely because they exist; GOV-09 owns their final disposition
and the Owner-browser acceptance contract.
