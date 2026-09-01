# Test trigger matrix

## Rule

The default is no test. Run a check only when its named trigger occurs, use the
smallest listed subject, and do not repeat successful evidence for an unchanged
tree or generated candidate. A broad or unfamiliar path is not a reason to run
an unbounded suite.

## Retained Python tests

Every row is machine enforced. The independent oracle must exist before the
implementation runs; current output is never an allowed oracle. Adding,
deleting, or renaming a Python test requires an exact inventory update in the
same change.

| File | Trigger | Purpose | Minimum subject | Independent oracle |
| --- | --- | --- | --- | --- |
| `tests/test_card_names.py` | Shared card-name candidate behavior or this test changes | Preserve alias, front-face, and legacy split-card lookup | Four fixed strings | `synthetic` |
| `tests/test_ci_master_admission.py` | Admission logic, PR evidence routing, or this test changes | Keep known paths targeted and unknown evidence fail closed | Exact changed admission nodes | `policy` |
| `tests/test_ci_workflow.py` | A workflow or this test changes | Preserve permissions, dependencies, minimal routing, and publication gates | Exact changed workflow nodes | `workflow` |
| `tests/test_cli_smoke.py` | One CLI dispatch/package boundary changes or pre-collection Melee smoke | Prove the named offline entry point dispatches | The named CLI node | `synthetic` |
| `tests/test_classifier_rule_contracts.py` | Standard/Modern rules, shared classifier, Melee deck adapter, or this test changes | Preserve Owner-defined discriminating rule and adapter boundaries without reading live events | One synthetic representative per distinct boundary | `owner-rule-contract` |
| `tests/test_documentation_history.py` | Live status/history pointers or this test changes | Keep live governance bounded and pointers resolvable | The changed status or pointer node | `policy` |
| `tests/test_generated_consumer_contracts.py` | A fresh MTGO candidate or consumer contract changes | Prove current candidate documents are internally consumable without historical totals | Current candidate invariants only | `current-candidate-invariant` |
| `tests/test_github_publication_preflight.py` | Publication preflight or this test changes | Keep authentication, permission, scope, and transport states fail closed | Changed preflight states | `policy` |
| `tests/test_landing_card_image_cache.py` | Landing card cache selection/build/admission changes | Prove complete deterministic cache closure without network access | Synthetic weeks, Bulk records, and image bytes | `synthetic` |
| `tests/test_melee_candidate_validation.py` | Melee candidate boundary or this test changes | Reject cross-event, deletion, and unrelated candidate writes | Synthetic baseline and candidate paths | `synthetic` |
| `tests/test_melee_missing_decklist_contract.py` | Missing-decklist ledger/statistics behavior or its Schema changes | Keep unavailable decklists distinct from Unknown and conserve coverage | Five synthetic participants and one played-match subject | `synthetic` |
| `tests/test_melee_multi_event_contract.py` | Versioned multi-event result/catalog contract or this test changes | Preserve compatibility admission and Schema vocabulary | Synthetic same-format catalogs | `synthetic` |
| `tests/test_melee_multi_event_matchup.py` | Multi-event matchup aggregation or shared math changes | Preserve leaf W-L-D roll-up and incompatibility rejection | Synthetic same-format matrices | `synthetic` |
| `tests/test_melee_multi_event_parity.py` | Cross-runtime parity fixture or aggregator changes | Preserve one Python/JavaScript contract vocabulary | One shared synthetic fixture | `synthetic` |
| `tests/test_melee_privacy_validation.py` | Melee collection privacy boundary or this test changes | Accept supported identities and reject a persisted key | One legacy, one direct-ID, and one invalid subject | `policy` |
| `tests/test_melee_source_identity.py` | Source identity/minimization/checkpoint contract or this test changes | Preserve public source IDs without a new HMAC key | Synthetic source responses and checkpoint | `external-contract` |
| `tests/test_mtgo_fetch_recovery.py` | Fetch retry/month traversal/transient classification changes | Retry only explicitly transient source failures | Synthetic HTTP responses and commands | `external-contract` |
| `tests/test_mtgo_landing.py` | Landing facts, review binding, or public/private admission changes | Preserve value-independent document and lifecycle invariants | Synthetic boundaries plus current-candidate mutation checks | `current-candidate-invariant` |
| `tests/test_mtgo_landing_editorial.py` | Editorial workbook/import/binding changes | Preserve deterministic workbook parsing and stale-binding rejection | Generated one-scope OOXML carrier | `current-candidate-invariant` |
| `tests/test_mtgo_landing_screening.py` | Screening policy or representative selection changes | Preserve thresholds, continuity, merging, and ties | Synthetic selection subjects | `synthetic` |
| `tests/test_mtgo_landing_screening_provenance.py` | Screening provenance or classifier binding changes | Reject stale candidates and preserve reviewed subjects | Synthetic provenance subjects | `synthetic` |
| `tests/test_mtgo_metadata.py` | MTGO metadata ownership/routing changes | Keep hierarchy ownership and Landing routing explicit | One synthetic metadata subject | `synthetic` |
| `tests/test_mtgo_top8_restatement.py` | Top 8 generator/digest/lifecycle contract changes | Restate identities while retaining synthetic source facts | Three synthetic source/classifier cases | `synthetic` |
| `tests/test_pages_compatibility.py` | Protected catalog-projection compatibility changes | Permit unrelated growth and reject protected projection drift | One synthetic protected projection | `protected-compatibility` |
| `tests/test_pauper_rules.py` | Pauper taxonomy/rules/contract fixture changes | Give every rule one Owner-approved representative without fixed inventory totals | One fixture case per rule and boundary | `owner-rule-contract` |
| `tests/test_simple_card_localization.py` | Flat MTGCH localization generation changes | Preserve key resolution, fallback, and output isolation | Synthetic product records and image bytes | `synthetic` |
| `tests/test_validate_repository_modes.py` | Repository validator, test inventory, or Schema mode changes | Keep changed/full validation and test admission fail closed | Synthetic repository paths and inventory rows | `policy` |
| `tests/test_validate_schemas.py` | Schema manifests or Schema validator changes | Require dynamic mappings and validate declared documents | Schema manifests and mapped instances | `schema` |
| `tests/test_weekly_maintenance_readiness.py` | Weekly readiness generator/private Schema changes | Preserve review-week and retained-queue separation | Synthetic Standard and Modern handoff | `synthetic` |

The public data/output rows remain bounded to their named subjects. The
documentation and CI rows are control-plane checks. The Landing-screening and weekly-
readiness rows are private review and handoff contracts; neither runs in
production candidate validation.

## Non-pytest validators and UI checks

| Trigger | Command or check | Purpose | Repeat rule |
| --- | --- | --- | --- |
| Any targeted PR | `python -B validate_repository.py --changed-from <base-sha>` | Parse changed maintained files and run only directly coupled repository-reference contracts | Once on the final PR head |
| Maintained Python changes | Ruff and mypy commands in `ci.yml` | Catch syntax/import and maintained type-contract failures | Once on the final PR head |
| One format's rule file, shared rule validator, or direct rule contract changes | `validate_rules.py` for only the affected format plus the matching node in `tests/test_classifier_rule_contracts.py`; a direct contract-file change runs that one file | Reject malformed rules and prove only the independently specified semantic boundary | Once on the final PR head |
| A mapped ordinary public JSON document changes | `python -B validate_schemas.py --changed-from <base-sha>` | Validate only changed documents covered by the current manifest | Once on the final PR head |
| A Schema, Schema manifest, or Schema validator changes | `python -B validate_schemas.py` | Prove the complete declared public contract migration | Once on the final PR head |
| Cache-A external-source integration changes | One read-only build of the current rolling subject from Scryfall Oracle Cards Bulk Data and image CDN into an external temporary directory, followed by local verification | Prove every current featured name resolves to a complete `normal` card image and the real immutable bundle closes without writing images to Git or reusing representative art | Once on the final Cache-A tree before Owner review; never from automated tests |
| Cache-B manifest admission, recent-week image selection, or older-week fallback changes | `node --test tests/js/phase8-runtime.test.js tests/js/phase8-landing.test.js tests/js/phase8-card-preview.test.js tests/js/phase8-landing-controller.test.js`, then focused local browser review with deterministic local failure/fallback fixtures and Scryfall image requests left unstarted | Prove recent admitted weeks use one local source for inline and preview, older or unavailable cache subjects fall back, and the existing paced/group retry path remains usable without contacting Scryfall | Once on the final visible tree before Owner review at desktop, 390px, and 412px |
| Chinese card-name, card-image, or card-link implementation changes | Focused generated-map parsing and current-Landing local-file existence checks, plus the smallest Node contract that covers Chinese local, Chinese MTGCH, English local, English Scryfall, language-selected decklist links, touch-preview destinations, and representative-art preservation when affected | Prove the flat lookup, source-selection outcomes, exact MTGCH card-page links, and language-invariant Landing representative art used by the product; reuse the accepted MTGCH source/direct-image evidence and do not repeat availability, latency, cache, image-size, Bulk-snapshot, or provenance-manifest trials | Once on the final localization tree before Owner review; mandatory changed-scope repository checks still apply |
| Archetype localization/name resolver or its public contract changes | `node --test tests/js/phase8-archetype-names.test.js` | Preserve stable-ID bilingual lookup and malformed-catalog rejection | Once on the final visible tree before Owner review |
| Landing controller archive selection or Pickup-retirement routing changes | `node --test tests/js/phase8-landing-controller.test.js` | Exclude empty feature weeks and avoid retired Pickup loading using synthetic weeks | Once on the final visible tree before Owner review |
| Matchup model or JavaScript multi-event reference changes | `node --test tests/js/phase8-matchup-model.test.js` | Catch a broken single-event calculation or cross-runtime multi-event contract before Owner review | Once on the final model tree before Owner review |
| Tabletop combined-result rendering, included-event identity, combined sample presentation, or its bilingual explanatory labels change | `npx playwright test tests/browser/phase13-tabletop-rendering.spec.js` with synthetic catalog and event routes | Prove the admitted in-memory result is visibly rendered with its event set, sample, interval, warning, and locked scope while Overview remains single-event | Once on the final P13-05 visible tree before Owner review |
| Tabletop event-set admission, multi-event loading, staged-refresh atomicity, or DEC-061 scope transition changes | `node --test tests/js/phase8-tabletop-controller.test.js` | Prove the complete selected set is catalog-admitted and validated before use or cache commit while single-event scope remains independent | Once on the final controller tree before Owner review |
| Canonical Tabletop `events` URL, matchup-selection history, reload or `popstate`, or Overview transition changes | `npx playwright test tests/browser/phase13-tabletop-state.spec.js` with synthetic catalog and event routes | Prove the real browser owns one canonical selected set without reviving a generic UI suite or using a public second event | Once on the final state-transition tree before Owner review |
| Browser request, cache, retry, refresh, runtime-loading, or retained-Landing companion-period logic changes | `node --test tests/js/phase8-runtime.test.js` | Catch a broken request lifecycle and prove that a last-admitted Landing drops newer companion facts without weakening format validation | Once on the final visible tree before Owner review |
| Shared card-image queue pacing, attempt timeout, progressive retry, or stale-view cancellation changes | `node --test tests/js/phase8-card-preview.test.js tests/js/phase8-landing.test.js` | Prove one-at-a-time paced starts, per-attempt timeout ownership, bounded recovery, inline Feature retry, and unchanged four-card Landing markup without contacting Scryfall | Once on the final visible tree before Owner review |
| Landing rendering or freshness presentation changes | `node --test tests/js/phase8-landing.test.js` | Preserve reviewed Landing copy and environment facts while unmatched companion deck-count and completeness values degrade to unknown | Once on the final visible tree before Owner review |
| Production entry HTML, shared bootstrap dependencies, cross-entry navigation, or title-home behavior changes | `node --test tests/js/phase8-metadata-sharing.test.js`, focused direct-Tabletop and MTGO → Tabletop → Back → title-home browser path, and changed-scope `validate_repository.py` entry inventory | Reject missing or misordered shared dependencies and prove that entry failure does not remove the static home recovery path | Once on the final visible tree before Owner review |
| Owner completes browser review of a user-visible change | Record the `owner-ui-accepted` digest for changed `index.html`, `assets/**`, and `melee/**` blobs | Bind the PR to exactly the visible files the Owner reviewed without rerunning UI automation | Once after acceptance and the unchanged local commit; PR admission only compares the digest |
| MTGO candidate generated | Candidate boundary, full repository validation, rules, Schema, output-invariant, consumer, and the candidate-derived `production-pages.spec.js` publication smoke in `update.yml` | Block publication when either required public entry cannot render candidate-derived data or the legacy Pickup path cannot render the last admitted Landing feature | Once for that immutable candidate before packaging |
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
- An unchanged generation-subject digest runs no generator,
  candidate validation, packaging, publication, or Pages job.
- MTGO production has no pre-build CLI baseline. CLI smoke runs only for CLI
  dispatch/package wiring changes; actual fetch, build, candidate, and
  publication gates own production safety.
- A governance-only, test-only, or other non-site `master` change does not
  trigger Pages.
- An unregistered, stale, duplicate, week/event-specific, invalid-oracle, or
  repository-live data/report oracle test fails repository validation before
  any catch-all test can run.
- Authentication preflight does not run during local development or CI unless
  its script or routing rule changed; operational publication runs it once per
  publication context.
- No change means no test.

## Retired UI checks

GOV-09 retired the generic browser preflight and the accessibility, card
preview, loading/retry, mobile-list, URL-state, and lazy-loading browser suites.
GOV-10 also retired feature-level filter, scrolling, layout, and detail
assertions from the production hard gate. They have no generic trigger.
`production-pages.spec.js` contains only publication-blocking output smoke
derived from the current candidate; it is not a PR or ordinary local-development
suite.
