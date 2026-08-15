# mtgo-data

`mtgo-data` analyzes Constructed Magic: The Gathering tournament data. Current
public product coverage is summarized below.

Development proceeds one owner-authorized task at a time. Read [`AGENTS.md`](AGENTS.md)
before changing the repository. Current phase, task, authorization, blockers,
and stop conditions are recorded only in [`docs/STATUS.yaml`](docs/STATUS.yaml).
Completed-task history is indexed under [`docs/history/`](docs/history/README.md).

## Current public products

| Product | Public formats | Entry |
| --- | --- | --- |
| MTGO Environment Trends | Standard, Modern | `/index.html` |
| Tabletop Major Events | Modern (event `434455`) | `/melee/index.html` |

## Product boundaries

- MTGO and tabletop source data, normalized data, statistics, workflows,
  catalogs, and front ends remain separate.
- Tabletop events must be explicitly registered in
  [`configs/melee_events.yaml`](configs/melee_events.yaml); the project does
  not crawl all Melee tournaments.
- `/index.html` serves MTGO Environment Trends and `/melee/index.html` serves
  Tabletop Major Events.
- Public data paths and statistical meaning require an approved migration.

Use [`docs/PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md) for product scope,
[`docs/STATISTICS_SPEC.md`](docs/STATISTICS_SPEC.md) for metric definitions,
and [`docs/DATA_ARCHITECTURE.md`](docs/DATA_ARCHITECTURE.md) for data and public
path contracts.

## Local setup

Python 3.12 is the supported runtime for local validation and GitHub Actions.
Create a virtual environment, install pinned development dependencies, and
install this repository into that environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install .
```

The installation adds `mtgo-data-mtgo`, `mtgo-data-melee`, and
`mtgo-data-catalog`. It does not add credentials, network access, scheduled
jobs, or production-data changes.

## Read-only validation

Run the applicable checks from the repository root:

```powershell
.\.venv\Scripts\python.exe validate_repository.py
.\.venv\Scripts\python.exe -m ruff check src
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe validate_rules.py
.\.venv\Scripts\python.exe validate_rules.py path\to\versioned-rules.yaml
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format standard classification-reports --strict
.\.venv\Scripts\python.exe tools\validate_standard_quality.py
.\.venv\Scripts\python.exe validate_schemas.py
.\.venv\Scripts\python.exe -m pytest tests\test_cli_smoke.py
```

These commands validate repository content, maintained code, archetype rules,
classification diagnostics, public JSON Schemas, and the three offline command
entry points. The complete trigger-specific list is in
[`docs/TEST_TRIGGER_MATRIX.md`](docs/TEST_TRIGGER_MATRIX.md). Do not run an
unbounded test suite when a named smaller command answers the current risk.
These commands do not fetch tournament data or regenerate production statistics.

The Standard public-contract and frozen classification baselines are documented
in [`docs/audits/P1-11.md`](docs/audits/P1-11.md) and
[`docs/audits/P1-12.md`](docs/audits/P1-12.md). Generated public JSON uses the
Schema mapping in [`schemas/manifest.json`](schemas/manifest.json).

## Pages publication artifact

The public site is assembled from the allowlist in
[`configs/pages_publication.json`](configs/pages_publication.json). Build it
into a new directory outside the repository:

```powershell
.\.venv\Scripts\python.exe -B build_pages_artifact.py `
  --output C:\tmp\mtgo-data-pages-site `
  --report C:\tmp\mtgo-data-pages-report.json
```

The builder copies approved files without modifying their bytes, validates the
complete event `434455` compatibility closure, writes `.nojekyll`, and reports
repository, data-tree, and artifact sizes. It does not fetch data, commit files,
or deploy the site.

Production candidate comparison uses a temporary baseline that must not be
committed:

```powershell
.\.venv\Scripts\python.exe validate_production_candidate.py snapshot --output production-baseline.json
.\.venv\Scripts\python.exe validate_production_candidate.py validate --baseline production-baseline.json
```

## Tabletop event pipeline

Only an enabled, verified event in `configs/melee_events.yaml` may enter this
pipeline. Live collection, whitelist changes, candidate publication, and
production dispatch each require the applicable owner authorization.

### Collect a minimized source snapshot

The collection command defaults to a zero-side-effect request-plan dry run.
Live collection additionally requires `--complete --execute` and an approved
event-scoped HMAC key:

```powershell
.\.venv\Scripts\mtgo-data-melee.exe --event-id 434455
$env:MELEE_PARTICIPANT_HMAC_KEY_BASE64 = "<approved base64 secret>"
$env:MELEE_PARTICIPANT_HMAC_KEY_ID = "<approved non-secret key id>"
.\.venv\Scripts\mtgo-data-melee.exe --event-id 434455 --complete --execute
```

The secret must decode to at least 32 bytes and must never appear in the
repository, command history, workflow YAML, logs, or documentation. The
collector keeps responses in bounded memory, accepts only reviewed public
resource fields, replaces source participant IDs with event-scoped HMAC
references, and persists canonical minimized JSON. Interrupted collection may
resume only its verified frozen request plan. A partial directory is never a
valid retained input; a complete snapshot is promoted atomically under
`data_raw/melee/<event_id>/<UTC-snapshot>/`.

Privacy contact information and correction or removal handling are documented
in [`NOTICE.md`](NOTICE.md). HMAC recovery boundaries and the existing MTGO,
Pages, and Melee failure paths are summarized in
[`docs/OPERATIONS_RUNBOOK.md`](docs/OPERATIONS_RUNBOOK.md).

### Build and validate an event candidate

The following commands are read-only without `--execute`. The corresponding
`--execute` form atomically writes the described candidate. Replace the sample
snapshot only with the separately approved, complete snapshot path.

Normalize and retain the verified source snapshot:

```powershell
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.retention `
  --event-id 434455 `
  --snapshot data_raw/melee/434455/20260724T092458Z-01
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.retention `
  --event-id 434455 `
  --snapshot data_raw/melee/434455/20260724T092458Z-01 `
  --execute
```

Classify submitted decks with the shared Modern taxonomy:

```powershell
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.classification `
  --root . --format modern --event-id 434455 --strict
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.classification `
  --root . --format modern --event-id 434455 --execute --strict
```

Build the Constructed-opportunity ledger:

```powershell
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.opportunities `
  --root . --format modern --event-id 434455
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.opportunities `
  --root . --format modern --event-id 434455 --execute
```

Build event overview, deck, and quality statistics:

```powershell
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.stats `
  --root . --format modern --event-id 434455
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.stats `
  --root . --format modern --event-id 434455 --execute
```

Build the hierarchical matchup document:

```powershell
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.matchup `
  --root . --format modern --event-id 434455
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.matchup `
  --root . --format modern --event-id 434455 --execute
```

Build the event metadata and public event catalog:

```powershell
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.publish `
  --root . --format modern --event-id 434455
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.publish `
  --root . --format modern --event-id 434455 --execute
```

The retained normalized event and deterministic overlays are under
`data/<format>/melee/`; public event documents are under
`stats/<format>/melee/events/<event_id>/`. Exact schemas and producer-to-output
relationships are documented in `docs/DATA_ARCHITECTURE.md`.

### Operate an approved event

Adding a whitelist entry is not the same as publishing an event. After an
owner-approved pull request adds and verifies the complete entry, an authorized
operator selects **Melee production candidate** in GitHub Actions and enters
the exact event ID. The workflow derives the format from the whitelist; there
is no manual format field or Modern fallback.

Review the Actions summary and any `data/melee-<event_id>` candidate branch.
The workflow never opens a pull request, merges, or writes to `master`; those
remain separate owner-reviewed actions.

## Format-aware MTGO commands

The format argument is mandatory. The installed command works without setting
`PYTHONPATH`:

```powershell
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format standard fetch-events
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format standard fetch-matches
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format standard build-statistics
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format standard build-matchups
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format standard build-completeness
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format standard build-top8
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format standard pickup candidates --if-absent
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format standard generate-hierarchy
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format standard generate-metadata
.\.venv\Scripts\mtgo-data-catalog.exe --root .
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format standard classification-reports --strict
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format modern fetch-matches
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format modern build-statistics
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format modern build-matchups
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format modern build-completeness
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format modern build-top8
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format modern classification-reports --strict
```

Standard and Modern are complete public MTGO products. The format registry also
keeps official-event archive collection separate for incomplete formats. The
scheduled pipeline builds statistics, matchups, completeness, provisional then
sealed weekly Top 8 data and bases, metadata, the product catalog, hierarchy catalogs, strict
classification diagnostics, and Weekly Pickup candidates for enabled products.

Weekly Pickup publication is manual. Candidate generation never approves a
row, publishes a week, or changes known-archetype state. Candidates are
available immediately after a natural week ends and unreviewed candidates may
refresh when late events arrive during that week's seven-day provisional
window. After review and approval, publish with:

```powershell
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format <standard-or-modern> pickup publish
```

For a new Modern known-state bootstrap, run only under the applicable approval:

```powershell
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format modern generate-hierarchy
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format modern generate-metadata
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format modern pickup initialize-known
.\.venv\Scripts\mtgo-data-mtgo.exe --root . --format modern pickup candidates --if-absent
```

`initialize-known` refuses to overwrite existing state. Classification reports
omit player names, login IDs, and raw player records; `--strict` fails on an
unresolved conflict or invalid deck input.

## Repository layout

- `configs/`: manually maintained format, event, and publication policy.
- `data_raw/`: approved minimized source snapshots.
- `data/<format>/`: normalized source-specific data and deterministic overlays.
- `stats/<format>/`: generated source-specific product documents.
- `src/mtgmeta/`: maintained package code and command implementations.
- `schemas/`: versioned public and intermediate data contracts.
- `reports/`: generated de-identified operational diagnostics.
- `tests/fixtures/`: self-contained regression evidence.
- `docs/`: authoritative specifications, decisions, audits, live status, and
  non-authoritative history.
- `index.html` and `melee/index.html`: GitHub Pages product entries.

Generated statistics and manually maintained configuration have different
roles. Do not manually edit generated output as a permanent fix.

## Production operations

`.github/workflows/update.yml` runs the scheduled MTGO production pipeline
daily at `20:00 UTC` and may be manually dispatched on `master`. Read-only fetch
and build jobs exchange short-lived verified artifacts; only the final publish
job receives `contents: write`, stages the approved generated scopes, and
confirms the published commit.

An interrupted input collection may produce a seven-day checkpoint artifact.
It is reusable only for the same master commit and exact operation plan after
checksum and archive-boundary validation. It cannot reach generation or
publication while incomplete and is not durable storage.

On failure, a separate least-privilege notification job creates or updates one
ordinary open issue for the failed pipeline stage. It records only the stage,
commit, and workflow link; it cannot write repository contents. A successful
run creates no issue.

Before operating or changing production, review
[`docs/DEVELOPMENT_WORKFLOW.md`](docs/DEVELOPMENT_WORKFLOW.md),
[`docs/STATISTICS_SPEC.md`](docs/STATISTICS_SPEC.md), and the live
[`docs/STATUS.yaml`](docs/STATUS.yaml). Do not run an unapproved fetch or
production dispatch.

## Licensing and data notice

- Repository code is licensed under the [MIT License](LICENSE).
- Project-authored documentation and archetype rules are licensed under
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Tournament records, decklists, card names, artwork, trademarks, and other
  third-party materials are not relicensed by this repository.

See [`NOTICE.md`](NOTICE.md) for attribution, privacy contact, and third-party
data information.
