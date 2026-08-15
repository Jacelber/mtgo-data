# GOV-08 minimal test-set rebuild

Status: local implementation complete; pending Owner acceptance.

## Frozen scope before file operations

- Base: `78af1e59f6e7cb32309420c45d59a60d4b98c2e1`.
- Python inventory: 96 `test_*.py` files and at least 697 test functions.
- Retained existing Python test files: 5.
- Added Python test files: 1.
- Deleted Python test files: 91.
- JavaScript tests, browser tests, fixtures, product code, Schemas, rules, data,
  generated output, and public paths are protected from change.
- The exact additions and deletions below were declared before any such file
  operation. There are no renames.

## Additions

- `add|code|tests/test_cli_smoke.py`
- `add|docs|docs/TEST_TRIGGER_MATRIX.md`
- `add|docs|docs/audits/GOV-08-MINIMAL-TESTSET-REBUILD.md`

## Retained existing Python test files

- `tests/test_ci_master_admission.py`: governance-path routing only.
- `tests/test_ci_workflow.py`: workflow shape and no-heavy-PR contract only.
- `tests/test_documentation_history.py`: reduced live-document contract only.
- `tests/test_generated_consumer_contracts.py`: generated candidate consumer
  contract only.
- `tests/test_melee_privacy_validation.py`: reduced pre-persistence privacy
  boundary only.

## Exact deletions

- `delete|code|tests/test_classification_reports.py`
- `delete|code|tests/test_classifier_r1_contract.py`
- `delete|code|tests/test_classifier_r2_shadow.py`
- `delete|code|tests/test_classifier_r3_pickup.py`
- `delete|code|tests/test_classifier_r3_production.py`
- `delete|code|tests/test_classifier_r4_unknown_review.py`
- `delete|code|tests/test_classifier_r5_pickup.py`
- `delete|code|tests/test_classifier_r5_production.py`
- `delete|code|tests/test_dependabot_config.py`
- `delete|code|tests/test_embedded_schema_version.py`
- `delete|code|tests/test_format_registry.py`
- `delete|code|tests/test_frontend_asset_split.py`
- `delete|code|tests/test_generated_output_determinism.py`
- `delete|code|tests/test_hierarchical_matchup_frontend.py`
- `delete|code|tests/test_melee_434455_compatibility.py`
- `delete|code|tests/test_melee_assembler.py`
- `delete|code|tests/test_melee_candidate_validation.py`
- `delete|code|tests/test_melee_classification.py`
- `delete|code|tests/test_melee_client.py`
- `delete|code|tests/test_melee_config.py`
- `delete|code|tests/test_melee_contracts.py`
- `delete|code|tests/test_melee_matchup.py`
- `delete|code|tests/test_melee_normalize.py`
- `delete|code|tests/test_melee_opportunities.py`
- `delete|code|tests/test_melee_parser.py`
- `delete|code|tests/test_melee_phase5_closeout.py`
- `delete|code|tests/test_melee_phase7_activation.py`
- `delete|code|tests/test_melee_privacy.py`
- `delete|code|tests/test_melee_production_data.py`
- `delete|code|tests/test_melee_publication.py`
- `delete|code|tests/test_melee_quality.py`
- `delete|code|tests/test_melee_retention.py`
- `delete|code|tests/test_melee_statistics.py`
- `delete|code|tests/test_melee_structure_statistics.py`
- `delete|code|tests/test_melee_workflow.py`
- `delete|code|tests/test_modern_classifier_integration.py`
- `delete|code|tests/test_modern_pickup_metadata.py`
- `delete|code|tests/test_modern_rule_migration_contract.py`
- `delete|code|tests/test_modern_statistics.py`
- `delete|code|tests/test_modern_taxonomy.py`
- `delete|code|tests/test_mtgo_cli.py`
- `delete|code|tests/test_mtgo_completeness.py`
- `delete|code|tests/test_mtgo_event_io.py`
- `delete|code|tests/test_mtgo_fetch_checkpoint.py`
- `delete|code|tests/test_mtgo_format_pipeline_contract.py`
- `delete|code|tests/test_mtgo_matchup.py`
- `delete|code|tests/test_mtgo_pickup.py`
- `delete|code|tests/test_mtgo_statistics.py`
- `delete|code|tests/test_mtgo_subtype_statistics.py`
- `delete|code|tests/test_mtgo_top8.py`
- `delete|code|tests/test_mypy_baseline.py`
- `delete|code|tests/test_node_test_suite.py`
- `delete|code|tests/test_output_invariants.py`
- `delete|code|tests/test_p12_10_readiness_contract.py`
- `delete|code|tests/test_pages_artifact.py`
- `delete|code|tests/test_pages_workflow.py`
- `delete|code|tests/test_phase12_accessibility_baseline.py`
- `delete|code|tests/test_phase12_chart_semantics.py`
- `delete|code|tests/test_phase12_freshness_strip.py`
- `delete|code|tests/test_phase12_shared_visual_foundation.py`
- `delete|code|tests/test_phase3_closeout.py`
- `delete|code|tests/test_phase6_closeout.py`
- `delete|code|tests/test_phase7_closeout.py`
- `delete|code|tests/test_phase8_closeout.py`
- `delete|code|tests/test_phase8_consumer_bridge.py`
- `delete|code|tests/test_phase8_mtgo_production_entry.py`
- `delete|code|tests/test_phase8_production_candidate.py`
- `delete|code|tests/test_phase8_public_contract.py`
- `delete|code|tests/test_phase8_real_data_review.py`
- `delete|code|tests/test_phase8_tabletop_production_entry.py`
- `delete|code|tests/test_phase9_pure_constructed_contract.py`
- `delete|code|tests/test_phase9_structure_consumer.py`
- `delete|code|tests/test_playwright_baseline.py`
- `delete|code|tests/test_production_candidate_validation.py`
- `delete|code|tests/test_production_workflow.py`
- `delete|code|tests/test_publication_governance_docs.py`
- `delete|code|tests/test_pytest_temp_guard.py`
- `delete|code|tests/test_python_packaging.py`
- `delete|code|tests/test_ruff_baseline.py`
- `delete|code|tests/test_shared_classifier.py`
- `delete|code|tests/test_shared_normalization.py`
- `delete|code|tests/test_shared_rules.py`
- `delete|code|tests/test_standard_classification_corpus.py`
- `delete|code|tests/test_standard_classification.py`
- `delete|code|tests/test_standard_classifier_integration.py`
- `delete|code|tests/test_standard_public_contract.py`
- `delete|code|tests/test_standard_quality_baseline.py`
- `delete|code|tests/test_standard_rule_migration_contract.py`
- `delete|code|tests/test_validate_repository.py`
- `delete|code|tests/test_validate_rules.py`
- `delete|code|tests/test_validate_schemas.py`

## Acceptance target

The two production workflows must not invoke unbounded pytest. Their pre-fetch
test execution, excluding dependency installation, must remain under 60 seconds
and consist only of the CLI and privacy checks required by the path about to
run. Publication candidate validators remain at the output gate and are not
duplicated before fetching.

## Local result

- Exact file-operation comparison: 91 declared deletions, 91 actual deletions,
  three declared additions, three actual additions, and zero renames.
- Retained inventory: six Python test files and 34 test functions.
- Workflow inventory: no unbounded pytest command; every production pytest
  invocation names test paths and an external basetemp.
- Changed behavior: 10 directly affected nodes passed once in 0.37 seconds.
- Final live-status subject: its one positive contract node passed in 0.03
  seconds after the completion record was written; negative-policy nodes were
  not repeated.
- Broken-reference risk: `validate_repository.py` passed once with Python 71,
  JavaScript 18, JSON 1770, YAML 52, references 57, and hygiene 2178.
- Intentionally not run: full pytest, unchanged generated-consumer tests,
  Schema/rule validators, output generators, live fetch, browser tests,
  production, and deployment.
