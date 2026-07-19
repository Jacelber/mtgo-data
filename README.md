# mtgo-data

`mtgo-data` analyzes Constructed Magic: The Gathering tournament data. The current production baseline is the Standard-focused **MTGO Environment Trends** site. A separate **Tabletop Major Events** product and additional Constructed formats are planned, but they are not yet production features.

The project is in Phase 1: engineering foundation and Standard baseline protection. Current task authorization and project status are recorded in [`docs/STATUS.yaml`](docs/STATUS.yaml).

The current Standard page compatibility baseline is documented in [`docs/audits/P1-11.md`](docs/audits/P1-11.md). Run `python -m pytest tests/test_standard_public_contract.py` for its automated checks and use [`docs/checklists/STANDARD_FRONTEND_SMOKE.md`](docs/checklists/STANDARD_FRONTEND_SMOKE.md) for browser verification.

The legacy Standard classification-quality baseline is documented in [`docs/audits/P1-12.md`](docs/audits/P1-12.md). Run `python validate_standard_quality.py` to verify frozen Unknown and multiple-match aggregates without reading mutable production data.

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
.\.venv\Scripts\python.exe validate_schemas.py
.\.venv\Scripts\python.exe -m pytest
```

These commands validate repository syntax and references, the current Standard archetype rules, the legacy Standard public JSON compatibility schemas, and the frozen Standard classification baseline. They do not fetch tournament data or regenerate production statistics.

The Schema mapping in `schemas/manifest.json` is versioned as `1.0.0`. It protects the structure of the existing unversioned Standard MTGO public JSON. Adding an embedded `schema_version` field to generated output requires a separate producer migration and is intentionally outside this compatibility-baseline task.

Pull requests and pushes to `master` run the same validation sequence through `.github/workflows/ci.yml`. The CI workflow has read-only repository permissions, does not persist checkout credentials, and does not fetch or regenerate production tournament data.

## Current repository layout

- `data/<format>/`: committed source event data; source-specific normalized paths will be added in later phases.
- `my_archetypes/standard.yaml`: current legacy Standard classification rules.
- `stats/standard/mtgo/`: generated Standard MTGO statistics consumed by the public page.
- `tests/fixtures/standard/`: self-contained Standard classification baseline.
- `docs/`: authoritative specifications, decisions, audits, status, and development workflow.
- `index.html`: current GitHub Pages entry point for MTGO Environment Trends.
- `.github/workflows/update.yml`: the single scheduled MTGO production pipeline, covering official event fetches, Videre matches, statistics, validation, and publication.

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
