# mtgo-data

`mtgo-data` analyzes Constructed Magic: The Gathering tournament data. The
public **MTGO Environment Trends** product supports Standard and Modern. The
separate **Tabletop Major Events** product publishes the explicitly whitelisted
Modern reference event `434455`. Other configured Constructed formats may have
official MTGO event archives without yet being complete public products.

Phase 9 is complete. Post-Phase-9 governance and development proceed one
separately authorized task at a time while MTGO and tabletop products remain
source-separated. Current task authorization and project status are recorded
in [`docs/STATUS.yaml`](docs/STATUS.yaml).

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

Python 3.12 is the supported runtime for local validation, GitHub Actions CI,
the manual Melee workflow, Pages artifact builds, and the scheduled MTGO
production update. Python 3.11 is not a supported project runtime.

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

## Pages publication artifact

The public site is assembled from the explicit product-path policy in
`configs/pages_publication.json`. The builder requires a new output directory,
copies approved files without modifying their bytes, validates the complete
event `434455` compatibility closure, writes `.nojekyll`, and reports repository,
data-tree, and artifact sizes:

```powershell
.\.venv\Scripts\python.exe -B build_pages_artifact.py `
  --output C:\tmp\mtgo-data-pages-site `
  --report C:\tmp\mtgo-data-pages-report.json
```

The output directory must not already exist and must be outside the repository.
This command does not fetch data, change statistics, commit files, or deploy a
site. `.github/workflows/pages.yml` performs the same fresh build for relevant
pull requests. Only a push to `master` may upload and deploy the verified Pages
artifact, and that deployment becomes active only after the repository Pages
source is separately changed from the legacy branch-root mode to GitHub Actions.

The complete pytest suite is a clean-checkout gate. Tests marked `committed_baseline` reproduce the current committed Standard snapshot using its own versioned dates, timestamps, and aggregate metadata, then require byte-identical generator output. They must not be interpreted as validation of a checkout after live production data has been added. The production workflow separately captures a dynamic baseline and runs `validate_production_candidate.py` after fetching and generation:

```powershell
.\.venv\Scripts\python.exe validate_production_candidate.py snapshot --output production-baseline.json
.\.venv\Scripts\python.exe validate_production_candidate.py validate --baseline production-baseline.json
```

The baseline file is a temporary workflow artifact and must not be committed. Candidate validation discovers the six raw-event collection formats and the complete Standard and Modern products from `configs/formats.yaml`. It permits only their declared generated-data scopes, rejects deletions and cross-product writes, validates changed documents and per-format count deltas, and runs before staging or publication.

## Melee raw-response client

Phase 5 provides a separately controlled raw-response client for explicitly enabled events in `configs/melee_events.yaml`. The command defaults to a zero-side-effect dry run; live requests additionally require the explicit `--execute` flag:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -B -m mtgmeta.melee --event-id 434455
$env:MELEE_PARTICIPANT_HMAC_KEY_BASE64 = "<approved base64 secret>"
$env:MELEE_PARTICIPANT_HMAC_KEY_ID = "<approved non-secret key id>"
.\.venv\Scripts\python.exe -B -m mtgmeta.melee --event-id 434455 --complete --execute
```

The command without `--execute` remains a request-plan dry run. The historical
source-preserving client is not an approved future production-retention path.
`--complete` discovers the enabled event's completed rounds, paginates its
public standings and match endpoints, and retrieves only decklists referenced
by the primary standings. It has no dry-run form because the request plan is
discovered from the live tournament page. For future snapshots, manifest v3
holds each source response only in bounded memory, applies the reviewed
resource allowlist, replaces source participant IDs with event-scoped
HMAC-SHA256 references, and writes only canonical minimized JSON. The collector
freezes that plan before bulk retrieval, writes per-response progress to
stderr, and checkpoints each verified minimized response under the event
directory. Re-running the same command after an interruption resumes only a
checkpoint with the same non-secret key ID and does not download already
verified files. The partial directory is never a valid retention input; only a
complete manifest is atomically promoted to
`data_raw/melee/<event_id>/<UTC-snapshot>/`.

The HMAC secret must decode to at least 32 bytes. Do not place a real value in
the repository, command history, workflow YAML, logs, or documentation. P10-03
defines this environment interface but does not provision a production secret;
live collection and secret/workflow configuration each require separate owner
authorization. The manifest records only the key ID and never the key.

The minimized resource documents are validated against
`schemas/melee-minimized-resource.schema.json` before persistence and again
when read. Privacy contact information and the correction or removal request
procedure are documented in [`NOTICE.md`](NOTICE.md).

The verified reference event `434455` is the only enabled Melee event; every
live fetch still requires separate project-owner authorization. A successful
re-fetch creates a new immutable snapshot instead of overwriting prior source
evidence.

P7-02 retains a complete immutable v2 or v3 snapshot as the canonical normalized production input
only after validating its manifest, response coverage, file set, byte counts,
SHA-256 values, parsed identities, normalized semantics, and publication
quality:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.retention `
  --event-id 434455 `
  --snapshot data_raw/melee/434455/20260724T092458Z-01
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.retention `
  --event-id 434455 `
  --snapshot data_raw/melee/434455/20260724T092458Z-01 `
  --execute
```

The first command is a zero-side-effect path plan. `--execute` writes
`data/modern/melee/events/434455.json` atomically. Reusing the same verified
snapshot must produce byte-identical output; a different result cannot silently
replace the retained input. Interrupted complete-event fetches remain
ineligible for parsing or retention but may resume their exact frozen request
plan after every existing response passes its stored byte-count and SHA-256
check.

P7-03 classifies every submitted Modern decklist from the retained event with
the same shared taxonomy used by MTGO Modern. The read-only command builds and
strictly validates the overlay in memory; `--execute` atomically writes the
participant-keyed result:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.classification `
  --root . --format modern --event-id 434455 --strict
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.classification `
  --root . --format modern --event-id 434455 --execute --strict
```

The output is `data/modern/melee/classifications/434455.json`. It records the
exact normalized-event and rule-file SHA-256 values, preserves every matched
rule and condition evidence, retains reviewable deck evidence for Unknowns,
and blocks strict generation on conflicts, invalid inputs, or an unassigned
subtype under a parent that defines subtypes. It does not rewrite the
normalized event or change MTGO statistics.

P7-04 converts the retained event and classification overlay into an explicit
mixed-event Constructed-opportunity ledger. The first command is read-only;
`--execute` atomically writes the deterministic candidate:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.opportunities `
  --root . --format modern --event-id 434455
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.opportunities `
  --root . --format modern --event-id 434455 --execute
```

The output is `data/modern/melee/opportunities/434455.json`. It records one
row for every scheduled Day 1 or qualified-field Day 2 Constructed Swiss
opportunity, including unplayed drop rounds, byes, intentional draws,
disqualification exclusions, and verified Top 8 lock exemptions. It excludes
Draft and playoffs and does not calculate archetype aggregates, win rates, or
matchup matrices; those remain P7-05 and P7-06 work.

P7-05 turns the retained event, classification overlay, opportunity ledger,
and unchanged Modern taxonomy into deterministic per-event overview, deck,
and quality statistics. The first command is read-only; `--execute` atomically
writes the three candidates:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.stats `
  --root . --format modern --event-id 434455
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.stats `
  --root . --format modern --event-id 434455 --execute
```

The outputs are `overview.json`, `decks.json`, and `quality.json` under
`stats/modern/melee/events/434455/`. They retain separate Day 1, Day 2, and
all-Constructed-Swiss scopes, direct parent and maintained-subtype metrics,
explicit Unknown rows, raw W-L-D samples, Wilson intervals, and reviewed
quality exclusions. A combined high-score metric is intentionally absent
because the two stages have different participant populations. P7-05 does not
generate `matchup.json`, `meta.json`, a public event catalog, a workflow, or
front-end behavior; those remain later tasks.

P7-06 generates the source-separated hierarchical matchup candidate from the
same four validated inputs. The first command is read-only; `--execute`
atomically writes `stats/modern/melee/events/434455/matchup.json`:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.matchup `
  --root . --format modern --event-id 434455
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.matchup `
  --root . --format modern --event-id 434455 --execute
```

The document defaults to all Constructed Swiss and also retains separate Day
1 and Day 2 scopes. Its complete 29-parent and 55-leaf matrices include
explicit zero cells, Unknown, raw W-L-D counts, and 95% Wilson intervals.
Leaf cells are canonical; parent cells are independent row-and-column rollups
of those leaves. Only opportunity-ledger rows with symmetric
`matchup_included: true` enter the matrices. The retained Tabletop document
keeps its compatibility value `low_sample_threshold: null`; the Phase 8
consumer applies the DEC-060 presentation warning below 20 valid matches
without changing those backend bytes. P7-06 did not create catalog, manifest,
workflow, or front-end behavior; those were completed by P7-07 and Phase 8.

P7-07 packages the verified event for public discovery. The first command is
read-only; `--execute` atomically writes the event `meta.json` and Modern
Melee `index.json`:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.publish `
  --root . --format modern --event-id 434455
.\.venv\Scripts\python.exe -B -m mtgmeta.melee.publish `
  --root . --format modern --event-id 434455 --execute
```

The metadata binds the exact overview, decks, matchup, and quality bytes by
Schema version, size, and SHA-256. The catalog exposes only the enabled,
verified reference event. All six Melee public documents are governed by
`schemas/manifest.json`. `.github/workflows/fetch_melee.yml` is manual-only
and source-separated: after a separately authorized dispatch it builds one
event candidate and may push only `data/melee-<event_id>` for review. It never
pushes `master`, creates a pull request, or merges. An already retained
canonical event reuses its exact immutable snapshot; only a newly approved
event without canonical input performs a live fetch.

## Format-aware MTGO commands

The production MTGO pipeline uses one explicit command entry point. Set `PYTHONPATH` to `src` when running it from a source checkout:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format standard fetch-events
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format standard fetch-matches
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format standard build-statistics
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format standard build-matchups
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format standard build-completeness
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format standard build-top8
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format standard pickup candidates --if-absent
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format standard generate-hierarchy
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format standard generate-metadata
.\.venv\Scripts\python.exe -B -m mtgmeta.catalog --root .
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format standard classification-reports --strict
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format modern fetch-matches
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format modern build-statistics
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format modern build-matchups
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format modern build-completeness
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format modern build-top8
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format modern classification-reports --strict
```

The format argument is mandatory. Standard and Modern are complete public MTGO products and support the same command set. The scheduled workflow runs Videre collection, statistics, hierarchical matchups, range-specific completeness, complete-week Top 8, Pickup candidate preparation, metadata, the global consumer catalog, hierarchy catalogs, and strict classification diagnostics for both formats. `build-completeness` writes `stats/<format>/mtgo/completeness/index.json` and the catalogued 1-, 4-, 12-, and 36-week documents; these keep Videre available/missing event identities and modeled-versus-observed high-score decklist counts separate. `build-top8` retains each catalogued `YYYY-Www.json` with an immutable same-week `YYYY-Www-bases.json`; an existing frozen week must rebuild byte-identically. `python -B -m mtgmeta.catalog --root .` writes `stats/catalog.json` from the format registry and actual published product catalogs. Official MTGO event raw-data collection is controlled separately by `event_collection_enabled`; Standard, Pauper, Modern, Pioneer, Legacy, and Vintage continue to receive the daily official-event archive, while the four incomplete products receive no Videre, statistics, report, or metadata generation. `fetch-events` checks the current and previous calendar month by default and accepts repeatable `--month YYYY-MM` overrides. `fetch-matches` accepts optional numeric event IDs and `--force`. Each Videre page request makes at most three attempts for HTTP 408, 425, 429, 5xx, connection errors, and timeouts, with a bounded delay between attempts. Explicit `400 No results found` responses remain non-failing missing archives; non-transient HTTP errors and exhausted retries remain publication-blocking failures. Classification reports may be directed to a disposable location with `--output-dir`.

Weekly Pickup publication remains a separate manual approval step. After reviewing and approving a candidate YAML, run `python -B -m mtgmeta.mtgo --format <standard-or-modern> pickup publish`. The scheduled workflow generates candidates only and preserves an existing candidate file for the latest complete week. A failure in one format's candidate preparation does not prevent the other format from being attempted and does not by itself block the remaining production pipeline.

Modern uses the same public product path. Bootstrap its stable-ID known state
once, generate the maintained hierarchy and metadata, and then create the
weekly review file:

```powershell
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format modern generate-hierarchy
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format modern generate-metadata
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format modern pickup initialize-known
.\.venv\Scripts\python.exe -B -m mtgmeta.mtgo --format modern pickup candidates --if-absent
```

`initialize-known` refuses to overwrite existing state. Modern candidate rows
carry stable parent IDs and optional subtype information, but selection and
publication remain manual. Generating candidates does not approve a row,
publish a week, or update known state.

The MTGO front end exposes Standard and Modern through one format selector.
The matchup matrix defaults to collapsed parent archetypes. Parents with at
least two maintained subtypes expose independent row and column expansion
buttons, and the global control expands or collapses every eligible parent.
Parents with zero or one subtype remain non-expandable. Interactive cells are
recalculated from canonical W-L-D counts; displayed percentages are never
averaged together.

`generate_classification_reports.py` remains a legacy Standard compatibility command. The production workflow now uses the format-aware command above. The reports omit player names, login IDs, and raw player records while retaining event context, stable pseudonymous deck IDs, matched rule evidence, and Unknown decklists. `--strict` returns a failure when an unresolved classification conflict or invalid deck input is present. These reports are operational diagnostics and are not consumed by the current front end.

The root-level `batch_mtgo.py`, `fetch_videre_matches.py`, `stats_standard.py`, `stats_matchup.py`, `weekly_pickup.py`, and `gen_meta.py` commands remain compatibility entry points. They are no longer production-workflow dependencies and are not removed during Phase 3 migration. Candidate generation never publishes or changes the known-archetype state by itself.

The Schema mapping in `schemas/manifest.json` is versioned as `1.0.0`. It protects the existing Standard MTGO page-consumed JSON and the classification diagnostic reports; every declared output embeds `schema_version: "1.0.0"`.

Pull requests and pushes to `master` run the clean-checkout validation sequence through `.github/workflows/ci.yml`. The CI workflow has read-only repository permissions, does not persist checkout credentials, and does not fetch or regenerate production tournament data. The production workflow adds candidate-data acceptance and published-commit confirmation as separate validation layers.

## Current repository layout

- `data/<format>/melee/`: retained normalized events and deterministic
  classification and opportunity-ledger overlays for approved tabletop events.
- `configs/formats.yaml`: validated registry of known formats, raw-event collection state, product execution state, capabilities, and format-specific paths.
- `my_archetypes/standard.yaml`: current legacy Standard classification rules.
- `src/mtgmeta/`: shared normalization, classification, configuration, and format-aware MTGO event-I/O, rolling-statistics, Videre, matchup, Weekly Pickup, metadata, catalog, and report-routing utilities.
- `schemas/classification-rules.schema.json`: machine-readable contract for versioned shared rule files.
- `reports/standard/mtgo/`: generated, de-identified Standard classification diagnostics.
- `stats/standard/mtgo/`: generated Standard MTGO statistics consumed by the public page.
- `tests/fixtures/standard/`: self-contained Standard classification baseline.
- `docs/`: authoritative specifications, decisions, audits, status, and development workflow.
- `index.html`: current GitHub Pages entry point for MTGO Environment Trends.
- `.github/workflows/update.yml`: the single scheduled MTGO production pipeline, retaining all six official event archives and generating the complete Standard and non-public Modern product data with per-format candidate validation before publication.

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
