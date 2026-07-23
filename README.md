# mtgo-data

`mtgo-data` analyzes Constructed Magic: The Gathering tournament data. The current production baseline is the Standard-focused **MTGO Environment Trends** site. A separate **Tabletop Major Events** product and additional Constructed formats are planned, but they are not yet production features.

The project is in Phase 3: generalizing the MTGO pipeline while Standard remains the only executable format. Current task authorization and project status are recorded in [`docs/STATUS.yaml`](docs/STATUS.yaml).

The current Standard page compatibility baseline is documented in [`docs/audits/P1-11.md`](docs/audits/P1-11.md). Run `python -m pytest tests/test_standard_public_contract.py` for its automated checks and use [`docs/checklists/STANDARD_FRONTEND_SMOKE.md`](docs/checklists/STANDARD_FRONTEND_SMOKE.md) for browser verification.

The legacy Standard classification-quality baseline is documented in [`docs/audits/P1-12.md`](docs/audits/P1-12.md). Run `python validate_standard_quality.py` to verify frozen Unknown and multiple-match aggregates without reading mutable production data.

Standard public JSON embeds `schema_version: "1.0.0"`. The producer migration and compatibility proof are documented in [`docs/audits/P1-13.md`](docs/audits/P1-13.md); run `python validate_schemas.py` to verify all declared outputs.

## Product boundaries

- MTGO and tabletop source data, normalized data, statistics, workflows, and front ends remain separate.
- Tabletop events must be explicitly whitelisted; the project does not crawl all Melee tournaments.
- Standard remains the regression baseline until the shared pipeline is protected by sufficient tests and schemas.
- Existing public Standard JSON paths must remain compatible unless a migration plan is approved.

Read [`AGENTS.md`](AGENTS.md) before changing the repository. Product scope, statistical definitions, architecture, roadmap, decisions, live status, and development controls are maintained under [`docs/`](docs/).

## Local setup

Python 3.12 is the currently exercised local runtime. One GitHub Actions workflow still uses Python 3.11, whose compatibility has not yet been fully reproduced locally.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Runtime dependencies are pinned in `requirements.txt`. Test and validation dependencies are pinned in `requirements-dev.txt`.

## Validation

Run the read-only repository validator, rule validator, and tests from the repository root:

```powershell
.\.venv\Scripts\python.exe validate_repository.py
.\.venv\Scripts\python.exe validate_rules.py
.\.venv\Scripts\python.exe validate_rules.py path\to\versioned-rules.yaml
.\.venv\Scripts\python.exe generate_classification_reports.py --strict
.\.venv\Scripts\python.exe validate_schemas.py
.\.venv\Scripts\python.exe -m pytest
```

These commands validate repository syntax and references, Standard archetype rules, versioned shared rule files, generated classification diagnostics, Standard JSON Schemas, and the frozen Standard classification baseline. They do not fetch tournament data or regenerate production statistics.

The complete pytest suite is a clean-checkout gate. Tests marked `committed_baseline` reproduce the current committed Standard snapshot using its own versioned dates, timestamps, and aggregate metadata, then require byte-identical generator output. They must not be interpreted as validation of a checkout after live production data has been added. The production workflow separately captures a dynamic baseline and runs `validate_production_candidate.py` after fetching and generation:

```powershell
.\.venv\Scripts\python.exe validate_production_candidate.py snapshot --output production-baseline.json
.\.venv\Scripts\python.exe validate_production_candidate.py validate --baseline production-baseline.json
```

The baseline file is a temporary workflow artifact and must not be committed. Candidate validation permits only the declared MTGO generated-data scope, rejects deletions and cross-product writes, validates changed documents and dynamic count deltas, and runs before staging or publication.

## Melee raw-response client

Phase 5 provides a separately controlled raw-response client for explicitly enabled events in `configs/melee_events.yaml`. The command defaults to a zero-side-effect dry run; live requests additionally require the explicit `--execute` flag:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -B -m mtgmeta.melee --event-id 434455
.\.venv\Scripts\python.exe -B -m mtgmeta.melee --event-id 434455 --execute
.\.venv\Scripts\python.exe -B -m mtgmeta.melee --event-id 434455 --complete --execute
```

`--complete` discovers the enabled event's completed rounds, paginates its public standings and match endpoints, and retrieves only decklists referenced by the primary standings. It has no dry-run form because the request plan is discovered from the live tournament page. The reference event `434455` is currently disabled, so all forms reject it before network or filesystem activity. Enabling an event and executing a live fetch require separate project-owner authorization. Completed raw snapshots use `data_raw/melee/<event_id>/<UTC-snapshot>/`; re-fetching creates a new snapshot instead of overwriting prior source evidence.

## Format-aware MTGO commands

The production MTGO pipeline uses one explicit command entry point. Set `PYTHONPATH` to `src` when running it from a source checkout:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format standard fetch-events
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format standard fetch-matches
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format standard build-statistics
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format standard build-matchups
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format standard pickup candidates --if-absent
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format standard generate-metadata
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format standard classification-reports --strict
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format modern fetch-matches
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format modern build-statistics
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format modern build-matchups
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format modern classification-reports --strict
```

The format argument is mandatory. Standard supports the complete current product command set. Modern is executable for classification, event statistics, Videre fetching, and hierarchical matchup generation, but remains non-public; Modern Pickup, metadata, workflow publication, and front-end selection are enabled only in later Phase 6 tasks. Official MTGO event raw-data collection is controlled separately by `event_collection_enabled`; Standard, Pauper, Modern, Pioneer, Legacy, and Vintage retain the legacy daily event archive. `fetch-events` checks the current and previous calendar month by default and accepts repeatable `--month YYYY-MM` overrides. `fetch-matches` accepts optional numeric event IDs and `--force`. Classification reports may be directed to a disposable location with `--output-dir`.

Weekly Pickup publication remains a separate manual approval step. After reviewing and approving a candidate YAML, run `python -B -m mtgmeta.mtgo --format standard pickup publish`. The scheduled workflow generates candidates only and preserves an existing candidate file for the latest complete week.

Modern has the same local, non-public preparation path. Bootstrap its stable-ID
known state once, generate the maintained hierarchy and metadata, and then
create the weekly review file:

```powershell
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format modern generate-hierarchy
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format modern generate-metadata
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format modern pickup initialize-known
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format modern pickup candidates --if-absent
```

`initialize-known` refuses to overwrite existing state. Modern candidate rows
carry stable parent IDs and optional subtype information, but selection and
publication remain manual. Generating candidates does not approve a row,
publish a week, or update known state. Modern remains absent from the public
format catalog and front end until the separately approved P6-09 migration.

`generate_classification_reports.py` remains a legacy Standard compatibility command. The production workflow now uses the format-aware command above. The reports omit player names, login IDs, and raw player records while retaining event context, stable pseudonymous deck IDs, matched rule evidence, and Unknown decklists. `--strict` returns a failure when an unresolved classification conflict or invalid deck input is present. These reports are operational diagnostics and are not consumed by the current front end.

The root-level `batch_mtgo.py`, `fetch_videre_matches.py`, `stats_standard.py`, `stats_matchup.py`, `weekly_pickup.py`, and `gen_meta.py` commands remain compatibility entry points. They are no longer production-workflow dependencies and are not removed during Phase 3 migration. Candidate generation never publishes or changes the known-archetype state by itself.

The Schema mapping in `schemas/manifest.json` is versioned as `1.0.0`. It protects the existing Standard MTGO page-consumed JSON and the classification diagnostic reports; every declared output embeds `schema_version: "1.0.0"`.

Pull requests and pushes to `master` run the clean-checkout validation sequence through `.github/workflows/ci.yml`. The CI workflow has read-only repository permissions, does not persist checkout credentials, and does not fetch or regenerate production tournament data. The production workflow adds candidate-data acceptance and published-commit confirmation as separate validation layers.

## Current repository layout

- `data/<format>/`: committed source event data; source-specific normalized paths will be added in later phases.
- `configs/formats.yaml`: validated registry of known formats, raw-event collection state, product execution state, capabilities, and format-specific paths.
- `my_archetypes/standard.yaml`: current legacy Standard classification rules.
- `src/mtgmeta/`: shared normalization, classification, configuration, and format-aware MTGO event-I/O, rolling-statistics, Videre, matchup, Weekly Pickup, metadata, catalog, and report-routing utilities.
- `schemas/classification-rules.schema.json`: machine-readable contract for versioned shared rule files.
- `reports/standard/mtgo/`: generated, de-identified Standard classification diagnostics.
- `stats/standard/mtgo/`: generated Standard MTGO statistics consumed by the public page.
- `tests/fixtures/standard/`: self-contained Standard classification baseline.
- `docs/`: authoritative specifications, decisions, audits, status, and development workflow.
- `index.html`: current GitHub Pages entry point for MTGO Environment Trends.
- `.github/workflows/update.yml`: the single scheduled MTGO production pipeline, using the explicit Standard MTGO command for official event fetches, Videre matches, statistics, Pickup candidates, metadata, de-identified classification diagnostics, validation, and publication.

Generated statistics and source configurations serve different roles. Do not manually edit generated statistics as a substitute for fixing their generator.

## Production operations

The production scripts and `.github/workflows/update.yml` fetch data and write committed outputs. The production workflow runs daily at `20:00 UTC` and may also be dispatched manually on `master`. It is not part of the read-only PR validation sequence. Before running or changing it, review:

- [`docs/audits/P1-01.md`](docs/audits/P1-01.md) for the current entry-point and workflow inventory;
- [`docs/STATISTICS_SPEC.md`](docs/STATISTICS_SPEC.md) for metric definitions;
- [`docs/DEVELOPMENT_WORKFLOW.md`](docs/DEVELOPMENT_WORKFLOW.md) for isolation, authorization, validation, and publication gates.

Do not develop directly on `master`, run unapproved production fetches, or begin a task that is not authorized by the project owner.

## Licensing and data notice

- Repository code is licensed under the [MIT License](LICENSE).
- Project-authored documentation and archetype classification rules are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Tournament records, decklists, card names, artwork, trademarks, and other third-party materials are not relicensed by this repository.

See [`NOTICE.md`](NOTICE.md) for scope, attribution, and third-party data information.
