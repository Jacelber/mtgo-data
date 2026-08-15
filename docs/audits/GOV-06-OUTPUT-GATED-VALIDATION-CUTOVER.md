# GOV-06 output-gated validation cutover

## Purpose

GOV-06 changes the default from “run everything” to “run only the check that
answers a named risk.” The public product is the generated artifact, so the
strong semantic gate is in update.yml after generation and before packaging.
Pull requests receive only path-targeted feedback. Unknown evidence stops for
owner classification and does not buy certainty by spending twenty minutes.

The full remediation sequence and authorization state are recorded in
docs/GOVERNANCE_REMEDIATION.yaml. Only GOV-06 is locally authorized.

## Validation stages after GOV-06

| Trigger | Purpose | Smallest test items |
| --- | --- | --- |
| PR opened, synchronized, reopened, or body/base edited | Classify the immutable changed-file subject | Admission API/path/status/declaration checks only |
| Known documentation path | Prevent broken live-document references/policy | Repository validator plus test_documentation_history.py |
| Known maintained Python path | Catch package syntax/name/type errors | Repository validator, Ruff F on src, existing mypy scope |
| Known rules/schema/generated-data path | Catch invalid rule or public shape changes | Both rule validators and Schema validator |
| Known workflow/governance path | Protect the classifier and CI wiring being changed | Only test_ci_master_admission.py and test_ci_workflow.py |
| Known UI path, before owner review | Catch syntax/model breakage, not visual behavior | Repository JavaScript syntax plus one native model smoke |
| Owner completes browser review of UI | Establish final UI acceptance evidence | No automated rerun; record the reviewed immutable commit at publication time |
| Production build has generated a candidate | Prevent internally inconsistent public numbers | Candidate scope, repository/rules/Schema checks, range totals/shares, matchup conservation/symmetry/interval checks, existing consumer smoke, one generated-page Chromium smoke |
| Exact merge reaches master | Confirm, do not repeat, the PR evidence | Exact base/head/class/job-matrix lookup only |
| Known-path addition | Use the existing category without extra governance | The category's existing minimal checks |
| Predeclared unknown addition, deletion, or rename | Verify the exact approved operation and run only its category | Exact marker-to-diff match plus the category's existing minimal checks |
| Undeclared/mismatched operation or incomplete API evidence | Ask for correction without wasting compute | No test; aggregate fails with the reason |

Each row has a distinct subject and purpose. A successful check is not repeated
later against the same immutable subject. Snapshot retirement and ordinary-suite
reconstruction are separate GOV-07 and GOV-08 tasks; GOV-06 removes them from
the PR critical path but does not delete them.

File-operation declarations use exact paths and do not accept globs. Known-path
additions do not require a marker. Unknown-path additions, deletions, and
renames require one marker per operation in the approved task contract and PR
body. The declaration is classification evidence, not authorization.

## New output invariants

validate_output_invariants.py encodes no expected tournament number. It checks:

- top-level archetype counts equal the document totals;
- high-score and Top 8 shares equal their counts divided by their totals;
- every matchup has matches = wins + losses + draws;
- A-versus-B wins equal B-versus-A losses and draws are symmetric;
- the literal record agrees with its matrix cell;
- a reported Wilson interval contains its point estimate; and
- no-match samples remain missing instead of being represented as a zero rate.

Subtype equality is not enabled in GOV-06 because current documents legitimately
contain parent records without a named subtype, so that assertion would reject
the existing valid output. Melee documents retain their separate Schema,
candidate, consumer, and generated-page gates; their different structure is not
forced into the MTGO validator.

## Explicit non-actions

This local task does not delete snapshot tests, run production, fetch data,
change statistical formulas, change public paths, change UI behavior, commit,
push, open a pull request, merge, or deploy.
