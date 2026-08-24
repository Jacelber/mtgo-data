# P12-15G-1 Pickup retirement no-caller audit

## Decision

The repository does **not** yet have a whole-Pickup no-caller proof. The old
reader-facing Pickup route is normalized to Landing before rendering, but the
production workflow still calls Pickup candidate generation, weekly readiness
still reads Pickup candidate files, metadata and hierarchy generation still
live in `pickup.py`, and the generated consumer catalog still advertises a
standalone `weekly-pickup` product.

P12-15G-2 therefore must migrate active responsibilities before it removes the
standalone product and publisher. No file in this audit is authorized for
deletion, relocation, or modification by P12-15G-1.

## Subject and method

- Audited immutable baseline: `408f761fdfd1c0c8f7a7c6391c5b0e178db67ff6`.
- Audited surfaces: production workflow, CLI and capability registry, Landing
  generation and review import, metadata and hierarchy generation, consumer
  catalog, Pages allowlist, Schemas, repository validation, active Phase 8
  front end, tests, generated public contracts, and tracked Pickup documents.
- Method: exact tracked-file inventory plus repository-wide symbol, command,
  path, product-ID, and Schema-reference searches. A definition or tracked file
  was not treated as a caller by itself.
- P12-15G-2 pre-implementation correction: the initial active-reference command
  enumerated named directories plus `validate_repository.py` and therefore
  missed root-level `validate_production_candidate.py`. A full tracked-text
  `git grep` found that it requires `weekly_pickup` and admits new candidate
  YAML only below the old Pickup path. The implementation inventory below now
  includes it, and the final no-caller proof must search all tracked text rather
  than a hand-written directory list.
- Limit: this is a static repository and generated-contract audit. It does not
  dispatch production or mutate cloud state.

## Caller proof

| Layer | Exact caller or contract | Finding | Required disposition |
| --- | --- | --- | --- |
| Production | `.github/workflows/update.yml` (`pickup candidates --if-absent`) | Active caller for both MTGO formats | Migrate to a Landing-owned candidate-preparation command before removing `pickup candidates`. |
| Weekly readiness | `tools/generate_weekly_maintenance_readiness.py`, `schemas/weekly-maintenance-readiness.schema.json`, `tests/test_weekly_maintenance_readiness.py`, and the readiness issue text in `.github/workflows/update.yml` | Actively reads `stats/<format>/mtgo/pickup/candidates_<week>.yaml`; absence or stale classifier digest blocks readiness | Migrate the path and vocabulary together; preserve fail-closed readiness semantics. |
| Production candidate admission | `validate_production_candidate.py` and its focused assertions in `tests/test_mtgo_landing.py` | Requires `weekly_pickup` for complete product formats and admits dated candidate/base YAML only under `stats/<format>/mtgo/pickup/` | Replace the capability requirement and admit only Landing-owned `landing/review/candidates_<week>.yaml` and `base_reference_<week>.yaml`; continue rejecting reviewed week YAML as an automatic addition. |
| Landing review import | `src/mtgmeta/mtgo/landing_editorial.py` | `build_top8_subject` reads Pickup candidate evidence; `_known_ids_from_legacy` imports Pickup known state | Migrate to Landing-owned candidate and known-state sources before private Pickup paths can retire. |
| Landing generation | `src/mtgmeta/mtgo/landing.py` | Current generation reads Landing review files, but still imports many shared selection/deck helpers from `pickup.py`; obsolete published-Pickup helper code also remains | Move shared helpers to a neutral/Landing module, update callers, then delete the obsolete compatibility helpers. |
| CLI and capability | `src/mtgmeta/mtgo/__main__.py`, `src/mtgmeta/config.py`, `configs/formats.yaml`, `schemas/formats.schema.json` | `pickup` remains a command and `weekly_pickup` remains an enabled capability | Remove only after the production caller and required helper ownership have migrated. |
| Metadata and hierarchy | `src/mtgmeta/mtgo/__main__.py`, `src/mtgmeta/mtgo/pickup.py` | `generate-metadata` and `generate-hierarchy` call functions owned by `pickup.py` | Move these functions before deleting `pickup.py`. |
| Consumer catalog | `src/mtgmeta/catalog.py`, `schemas/consumer-catalog.schema.json`, `stats/catalog.json` | `weekly-pickup` remains an advertised product | Remove the product and regenerate the catalog after the front-end shell is retired. |
| MTGO metadata | `src/mtgmeta/mtgo/pickup.py`, `schemas/mtgo-meta.schema.json`, `stats/standard/mtgo/meta.json`, `stats/modern/mtgo/meta.json` | `pickup_catalog` still points to `pickup/index.json` because the frozen index exists | Set the compatibility field to `null` first; removal of the field itself is a separate public-Schema decision. |
| Repository/public contract | `validate_repository.py`, `tests/fixtures/standard/public_contract/contract.json`, `tests/test_generated_consumer_contracts.py` | Pickup index and week files remain required/validated public paths | Update only after catalog/metadata retirement; retain validation of frozen files while they remain declared artifacts. |
| Phase 8 front end | `assets/js/phase8/app-core.js`, `app.js`, `app-loading.js`, `app-mtgo.js`, `app-freshness.js`, `mtgo-controller.js`, `i18n.js` | Standalone state, renderer, loader, labels, and handlers remain in the bundle, although the legacy URL is normalized before the view is selected | Remove the standalone shell after preserving the redirect and renaming Landing-owned state. |
| Legacy URL compatibility | `assets/js/phase8/app-metadata.js`, `tests/js/phase8-metadata-sharing.test.js`, `tests/browser/production-pages.spec.js` | Active and required: `product=weekly-pickup&week=<week>` maps to `product=mtgo-landing&section=features&week=<week>` | Retain permanently unless a later explicit compatibility decision supersedes it. |
| Pages | `configs/pages_publication.json` | Private Pickup YAML/known-state files are excluded; public Pickup index/week JSON files are still eligible for Pages | Retain exclusions while any private files remain. Frozen public-document removal is separately gated. |
| Pickup document Schemas | `schemas/manifest.json`, `schemas/mtgo-pickup-index.schema.json`, `schemas/mtgo-pickup-week.schema.json` | Still validate tracked frozen public documents | Retain until those exact documents are separately accepted for deletion or relocation. |

The old browser route therefore has a no-standalone-renderer-invocation proof,
but the Pickup package, capability, private path, public catalog identity, and
module do not.

## Exact P12-15G-2 migration and cleanup inventory

All operations below are proposals for the next stage, not operations performed
by this audit.

### A. Migrate active responsibilities first

| Exact path | Proposed operation | Result |
| --- | --- | --- |
| `.github/workflows/update.yml` | Replace `pickup candidates` with the accepted Landing-owned preparation command; rename readiness issue vocabulary after its data contract changes. | Weekly production keeps preparing review material without a Pickup capability. |
| `src/mtgmeta/mtgo/__main__.py` | Add/use the Landing-owned preparation runner; move metadata/hierarchy imports to their real owners; remove `pickup`, `initialize-known`, and `publish` only after callers are gone. | CLI ownership matches the Landing workflow and retained shared generators. |
| `src/mtgmeta/mtgo/landing_editorial.py` | Own candidate preparation and the current known-state read; stop reading `stats/<format>/mtgo/pickup/*`. | Review import has no private Pickup-path dependency. |
| `src/mtgmeta/mtgo/landing.py` | Import neutral/Landing helpers; remove `_load_published_pickup`, `_summary_review_inputs`, and obsolete published-Pickup constants/branches after exact reference proof. | Current Landing generation no longer depends on the Pickup module or publisher shape. |
| `src/mtgmeta/mtgo/pickup.py` | Move candidate-selection helpers, policy loading, deck identity helpers, metadata generation, and hierarchy generation to accepted owners; then remove publisher/state code. Delete the file only if the post-migration reference scan proves it empty and caller-free. | No mixed-responsibility deletion and no accidental loss of Landing, metadata, or hierarchy behavior. |
| `tools/generate_weekly_maintenance_readiness.py` | Read the Landing-owned candidate/preparation artifact and emit Landing/review terminology while preserving digest and blocker checks. | Maintenance remains fail-closed on missing or stale weekly review material. |
| `schemas/weekly-maintenance-readiness.schema.json` | Migrate the matching property/path vocabulary with compatibility handling if required. | The readiness Schema matches the new producer. |
| `docs/WEEKLY_MAINTENANCE.md` | Replace Pickup-as-product instructions with Landing candidate screening and review instructions. | The operator follows the same chain that production executes. |
| `configs/mtgo_pickup_policy.yaml` | Retain the policy content; rename only if every code, documentation, and audit reference is migrated in the same accepted change. | Screening meaning is unchanged during product retirement. |
| `configs/formats.yaml` | Remove `weekly_pickup` after the new Landing command uses `landing_generation`. | Formats no longer advertise a retired capability. |
| `src/mtgmeta/config.py` | Remove `weekly_pickup` from recognized capabilities after the registry migration. | Capability validation matches the registry. |
| `schemas/formats.schema.json` | Remove the matching capability enum value. | Registry Schema matches runtime validation. |
| `src/mtgmeta/catalog.py` | Remove the `weekly-pickup` product tuple. | Generated catalogs stop advertising a standalone product. |
| `schemas/consumer-catalog.schema.json` | Remove `weekly-pickup` from product enums. | Catalog Schema matches the generated catalog. |
| `stats/catalog.json` | Regenerate from the migrated catalog producer. | All format entries omit the standalone product. |
| `schemas/mtgo-meta.schema.json` | Initially retain required `pickup_catalog` as nullable; do not remove it in the same compatibility step unless separately accepted as a public-Schema change. | Existing consumers can observe retirement as `null` without a field-shape break. |
| `stats/standard/mtgo/meta.json` | Regenerate with `pickup_catalog: null`. | Standard metadata stops pointing at the frozen Pickup index. |
| `stats/modern/mtgo/meta.json` | Regenerate with `pickup_catalog: null`. | Modern metadata stops pointing at the frozen Pickup index. |
| `validate_repository.py` | Stop requiring Pickup as a live Standard/front-end product; keep exact frozen-document checks only while those documents remain declared. | Validation distinguishes retired product identity from retained rollback artifacts. |
| `validate_production_candidate.py` | Remove the `weekly_pickup` capability requirement and migrate the exact new-path allowlist to Landing review candidate/base-reference filenames. | Scheduled generation can add only the new private machine artifacts and cannot add human-reviewed week documents. |
| `tests/fixtures/standard/public_contract/contract.json` | Remove Pickup from active front-end templates/catalogs when the live contract migrates. | Fixture describes Landing feature paths as the reader-facing contract. |
| `tests/test_generated_consumer_contracts.py` | Replace live Pickup-product assertions with Landing candidate/catalog retirement assertions; retain any frozen-document check explicitly required by the separate gate. | Regression coverage follows the new contract. |
| `tests/test_weekly_maintenance_readiness.py` | Migrate fixtures and assertions to the Landing-owned candidate artifact. | Readiness behavior remains covered. |
| `tests/test_mtgo_landing_editorial.py` | Test the moved candidate builder and Landing-owned known-state source. | Editorial import coverage follows the new owner. |
| `tests/test_mtgo_landing.py` | Replace direct Pickup helper/shape dependencies and delete obsolete published-Pickup compatibility tests. | Landing tests cover only supported inputs. |
| `tests/test_mtgo_pickup_selection.py` | Move still-valid selection-policy cases to a Landing screening test module, then delete this file. | Selection behavior remains covered without a Pickup product test identity. |
| `tests/test_mtgo_pickup_provenance.py` | Move still-valid candidate provenance/metadata cases to their new owners; delete publisher-only cases, then delete this file. | Provenance coverage survives responsibility migration. |

### B. Remove the proven-dead standalone browser shell after A

| Exact path | Exact cleanup |
| --- | --- |
| `assets/js/phase8/app-core.js` | Remove `weekly-pickup` product order/label/surface entries; replace `pickupWeekFile` and `pickupOpen` with Landing feature state where still active. |
| `assets/js/phase8/app.js` | Remove standalone parse/serialize/render/week/toggle branches and the product-click compatibility branch made redundant by route normalization. |
| `assets/js/phase8/app-loading.js` | Remove standalone staging; rename the active Landing feature-week and disclosure state. |
| `assets/js/phase8/app-mtgo.js` | Remove `pickupDeck` and `pickupView`. |
| `assets/js/phase8/app-freshness.js` | Remove `pickupFreshness`. |
| `assets/js/phase8/mtgo-controller.js` | Remove `loadPickupIndex`, `loadPickupDocument`, `loadPickup`, and `stagePickup`. |
| `assets/js/phase8/i18n.js` | Remove strings used only by the standalone Pickup page; keep any text still rendered by Landing. |
| `assets/css/phase8-base.css` | Remove selectors used only by the deleted renderer; keep or rename any selector still used by Landing error anchoring. |
| `assets/css/phase8-candidate.css` | Remove standalone Pickup layout/head responsive rules. |
| `tests/js/phase8-pickup.test.js` | Delete after the renderer functions are removed. |
| `tests/js/phase8-landing.test.js` | Rename Pickup-derived test state to Landing feature state and retain Landing behavior coverage. |

### C. Retain, not clean up in P12-15G

- `assets/js/phase8/app-metadata.js`: retain `normalizedRoute` and its exact
  `weekly-pickup` mapping.
- `tests/js/phase8-metadata-sharing.test.js`: retain the legacy-route unit test.
- `tests/browser/production-pages.spec.js`: retain the legacy-route browser test.
- `configs/mtgo_pickup_policy.yaml`: retain the accepted screening rules unless
  an exact same-change rename is accepted.
- `stats/standard/mtgo/landing/review/2026-W27.yaml`
- `stats/standard/mtgo/landing/review/2026-W33.yaml`
- `stats/standard/mtgo/landing/review/known_archetypes.json`
- `stats/modern/mtgo/landing/review/2026-W33.yaml`
- `stats/modern/mtgo/landing/review/known_archetypes.json`
- `stats/standard/mtgo/landing/features/2026-W27.json`
- `stats/standard/mtgo/landing/features/2026-W33.json`
- `stats/standard/mtgo/landing/features/index.json`
- `stats/modern/mtgo/landing/features/2026-W33.json`
- `stats/modern/mtgo/landing/features/index.json`
- `tools/migrate_classifier_r3_pickup.py` and
  `tools/migrate_classifier_r5_pickup.py`: retain as historical migration tools;
  they are not runtime callers.
- `docs/audits/classifier-r2/baseline_pickup/modern_known_archetypes.json`
- `docs/audits/classifier-r2/baseline_pickup/standard_known_archetypes.json`
- `docs/audits/classifier-r2/results/pickup_dry_run.json`
- `docs/audits/classifier-r4/baseline_pickup/modern_known_archetypes.json`
- `docs/audits/classifier-r4/baseline_pickup/standard_known_archetypes.json`
- `docs/audits/p12-10-readiness/pickup_review_contract.json`: retain as audit
  evidence, not live authority.
- `docs/audits/CLASSIFIER-PICKUP-REVIEW-CORRECTIONS-20260815.md` and
  `docs/audits/P12-10-READINESS-PICKUP-CONTRACT.md`: retain as audit evidence,
  not live authority.
- `tests/fixtures/mtgo/format_pipeline_contract.json`: retain as the historical
  Phase 3 migration contract; no runtime/test caller was found. It must not be
  used as current authorization.
- `assets/css/site.css` and `assets/js/mtgo.js`: retain for P12-16 or a separately
  declared legacy-entry cleanup. Active `index.html` and `melee/index.html` load
  Phase 8 assets, but P12-15G must not silently broaden into whole-legacy-bundle
  removal.
- `schemas/mtgo-landing.schema.json`: retain `pickup_document_digest` as an
  existing public compatibility/provenance field unless a separate Schema
  decision accepts its replacement.

## Exact documents requiring a separate Owner gate

These files are not cleanup targets in the initial P12-15G-2 code migration.
Their current SHA-256 values provide rollback identity. Any later deletion or
relocation must name the selected files again and prove the listed Landing
replacement or an accepted archival destination.

### Frozen public documents

| Exact path | SHA-256 | Replacement evidence |
| --- | --- | --- |
| `stats/modern/mtgo/pickup/2026-W33.json` | `56f5db957e819cc4acb3e915f09f245038117cd2f3c05d4727437f99883c6d11` | `stats/modern/mtgo/landing/features/2026-W33.json` exists. |
| `stats/modern/mtgo/pickup/index.json` | `5c9a3f880562ad18f61fd85ca9bc80386843178d9a74e797ae0a7425b505d573` | `stats/modern/mtgo/landing/features/index.json` exists. |
| `stats/standard/mtgo/pickup/2026-W27.json` | `8fde187d498bb609b0e7d8c24ec05adf6a94b2d449bf51a43cdd7d7b12ae026f` | `stats/standard/mtgo/landing/features/2026-W27.json` exists. |
| `stats/standard/mtgo/pickup/2026-W33.json` | `fdbfb057c08823ee573791b3843107fd649b8f82dc5ebf460a12b833898cc431` | `stats/standard/mtgo/landing/features/2026-W33.json` exists. |
| `stats/standard/mtgo/pickup/index.json` | `981ad70b8bad6dcb5eb9d7c0ef1343df9b30092b861cd1ce8d50b0f6f3d2c927` | `stats/standard/mtgo/landing/features/index.json` exists. |

`schemas/mtgo-pickup-index.schema.json`,
`schemas/mtgo-pickup-week.schema.json`, and the four matching entries in
`schemas/manifest.json` remain required while the frozen public documents stay
tracked. Their later removal belongs to the same separate document gate.

### Private candidate, base-reference, and known-state documents

The current W34 candidate/base-reference pairs are active production and
readiness inputs. Older files are rollback/evidence artifacts. None may be
removed until the Landing-owned preparation path has produced and consumed an
equivalent current-week subject and the Owner accepts an exact archive/delete
set.

Modern exact paths:

- `stats/modern/mtgo/pickup/base_reference_2026-W29.yaml`
- `stats/modern/mtgo/pickup/base_reference_2026-W30.yaml`
- `stats/modern/mtgo/pickup/base_reference_2026-W31.yaml`
- `stats/modern/mtgo/pickup/base_reference_2026-W32.yaml`
- `stats/modern/mtgo/pickup/base_reference_2026-W33.yaml`
- `stats/modern/mtgo/pickup/base_reference_2026-W34.yaml`
- `stats/modern/mtgo/pickup/candidates_2026-W29.yaml`
- `stats/modern/mtgo/pickup/candidates_2026-W30.yaml`
- `stats/modern/mtgo/pickup/candidates_2026-W31.yaml`
- `stats/modern/mtgo/pickup/candidates_2026-W32.yaml`
- `stats/modern/mtgo/pickup/candidates_2026-W33.yaml`
- `stats/modern/mtgo/pickup/candidates_2026-W34.yaml`
- `stats/modern/mtgo/pickup/known_archetypes.json`

Standard exact paths:

- `stats/standard/mtgo/pickup/base_reference_2026-W28.yaml`
- `stats/standard/mtgo/pickup/base_reference_2026-W29.yaml`
- `stats/standard/mtgo/pickup/base_reference_2026-W30.yaml`
- `stats/standard/mtgo/pickup/base_reference_2026-W31.yaml`
- `stats/standard/mtgo/pickup/base_reference_2026-W32.yaml`
- `stats/standard/mtgo/pickup/base_reference_2026-W33.yaml`
- `stats/standard/mtgo/pickup/base_reference_2026-W34.yaml`
- `stats/standard/mtgo/pickup/candidates_2026-W28.yaml`
- `stats/standard/mtgo/pickup/candidates_2026-W29.yaml`
- `stats/standard/mtgo/pickup/candidates_2026-W30.yaml`
- `stats/standard/mtgo/pickup/candidates_2026-W31.yaml`
- `stats/standard/mtgo/pickup/candidates_2026-W32.yaml`
- `stats/standard/mtgo/pickup/candidates_2026-W33.yaml`
- `stats/standard/mtgo/pickup/candidates_2026-W34.yaml`
- `stats/standard/mtgo/pickup/known_archetypes.json`

`configs/pages_publication.json` must retain its three private-Pickup exclusion
patterns until every matching private file has been relocated or removed. The
exclusions may be removed only in the same separately accepted operation that
makes them unnecessary.

## P12-15G-2 implementation order

1. Introduce the Landing-owned weekly candidate/preparation artifact and
   command without changing the accepted screening policy or review outcome.
2. Migrate production, readiness, review import, known state, documentation,
   and their focused tests to the new path; prove the current complete week is
   equivalent before disabling the old writer.
3. Move shared selection/deck helpers plus metadata/hierarchy generators out of
   `pickup.py`; prove all retained commands and Landing generation use the new
   owners.
4. Remove the standalone Phase 8 renderer/loader/state/styles and the Pickup
   CLI publisher/capability. Preserve and test the legacy URL normalization.
5. Remove the consumer-catalog product, emit `pickup_catalog: null`, regenerate
   affected contracts, and update live repository validation.
6. Re-run the no-caller search across workflow, production, catalog, metadata,
   Pages, tests, front end, and public requests. Stop if any undeclared caller
   remains.
7. Present the exact frozen/private document set, replacement equivalence, and
   rollback hashes for separate Owner acceptance. Do not delete or relocate
   those documents as an implicit part of code cleanup.

## Rollback boundary

- Keep all exact Pickup documents listed above unchanged through the initial
  code migration.
- Keep the legacy URL redirect and both its unit and browser tests.
- Make the P12-15G-2 code/catalog migration one focused commit so reverting that
  commit restores the old command, capability, catalog, metadata pointer, and
  browser shell without reconstructing data.
- Before any separately accepted document removal, verify the recorded hash,
  archive or Git rollback identity, and the exact corresponding Landing feature
  week/index.
- A failed equivalence check, missing current-week Landing candidate subject,
  non-null live Pickup catalog reference, or remaining runtime request is a
  stop condition, not permission to delete around the failure.

## P12-15G-1 stop

The next action is Owner review of this caller proof and exact inventory. The
Owner has authorized P12-15G as a whole, but explicitly limited current
execution to P12-15G-1. P12-15G-2 may begin only after acceptance of this audit;
no public-path change, document deletion, publication, merge, deployment, or
production dispatch is authorized by this audit.

## P12-15G-2 local implementation evidence

The Owner accepted P12-15G-1 and authorized P12-15G-2 on 2026-08-24. The local
candidate implements the accepted inventory without deleting, renaming,
relocating, or modifying any frozen Pickup document or Pickup document Schema.

### Replacement equivalence

The new `landing-review prepare` producer generated Standard and Modern W34
candidate and four-week base-reference documents into a disposable directory.
Parsed YAML equality against the corresponding old Pickup-path W34 documents
was exact:

| Format | Candidate equal | Base reference equal |
| --- | --- | --- |
| Standard | yes | yes |
| Modern | yes | yes |

Both formats now read stable parent IDs from their Landing-owned known-state
files. This corrects the migration boundary without changing the candidate
selection result.

### Final no-caller proof

A full working-tree search, supplemented by the repository validator's tracked
file inventory, found:

- no active `weekly_pickup` capability, Pickup renderer/state/freshness symbol,
  Pickup controller load/stage function, Pickup data attribute, or Pickup i18n
  product/source key;
- no runtime read or write of old Pickup candidate, base-reference, or
  known-state paths;
- no import of `src/mtgmeta/mtgo/pickup.py`;
- exactly three active `weekly-pickup` references: route normalization in
  `app-metadata.js`, its unit test, and its browser test; and
- no standalone Pickup entry in `stats/catalog.json`, while both MTGO metadata
  documents emit `pickup_catalog: null`.

The frozen index/week documents, their Schemas and manifest entries, Pages
private-path exclusions, historical tools, and public
`pickup_document_digest` compatibility field remain intentionally retained and
are not active product callers.

### Validation

- Ruff changed-file check: pass.
- Focused Python tests: 82 passed.
- Phase 8 JavaScript tests: 34 passed.
- Repository validation: Python 84/84, JavaScript 20/20, JSON 1854/1854,
  YAML 68/68, references 55/55, hygiene 2316/2316.
- Local browser: the legacy Standard W33 URL canonicalized to
  `product=mtgo-landing&section=features&week=2026-W33`; the feature section and
  W33 selector rendered, product navigation contained only the five supported
  products, no console error appeared, and the local request log contained no
  `/mtgo/pickup/` request.

The Owner accepted this exact P12-15G-2 local candidate on 2026-08-24. That
acceptance authorizes normal completion of the unchanged task; production
dispatch, P12-16, and any frozen-document removal remain outside this evidence.
