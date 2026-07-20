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

`generate_classification_reports.py` remains the legacy Standard command and now resolves its event, rule, and report paths through `configs/formats.yaml`; `--format standard` may be supplied explicitly. The reports omit player names, login IDs, and raw player records while retaining event context, stable pseudonymous deck IDs, matched rule evidence, and Unknown decklists. `--strict` returns a failure when an unresolved classification conflict or invalid deck input is present. These reports are operational diagnostics and are not consumed by the current front end.

The Schema mapping in `schemas/manifest.json` is versioned as `1.0.0`. It protects the existing Standard MTGO page-consumed JSON and the classification diagnostic reports; every declared output embeds `schema_version: "1.0.0"`.

Pull requests and pushes to `master` run the same validation sequence through `.github/workflows/ci.yml`. The CI workflow has read-only repository permissions, does not persist checkout credentials, and does not fetch or regenerate production tournament data.

## Current repository layout

- `data/<format>/`: committed source event data; source-specific normalized paths will be added in later phases.
- `configs/formats.yaml`: validated registry of known formats, execution state, capabilities, and format-specific paths.
- `my_archetypes/standard.yaml`: current legacy Standard classification rules.
- `src/mtgmeta/`: shared normalization, classification, configuration, and format-aware MTGO event-I/O, rolling-statistics, Videre, matchup, and report-routing utilities.
- `schemas/classification-rules.schema.json`: machine-readable contract for versioned shared rule files.
- `reports/standard/mtgo/`: generated, de-identified Standard classification diagnostics.
- `stats/standard/mtgo/`: generated Standard MTGO statistics consumed by the public page.
- `tests/fixtures/standard/`: self-contained Standard classification baseline.
- `docs/`: authoritative specifications, decisions, audits, status, and development workflow.
- `index.html`: current GitHub Pages entry point for MTGO Environment Trends.
- `.github/workflows/update.yml`: the single scheduled MTGO production pipeline, covering official event fetches, Videre matches, statistics, classification diagnostics, validation, and publication.

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
