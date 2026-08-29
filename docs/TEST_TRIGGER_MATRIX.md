# Test trigger matrix

## Rule

The default is no test. Run a check only when its named trigger occurs, use the
smallest listed subject, and do not repeat successful evidence for an unchanged
tree or generated candidate. A broad or unfamiliar path is not a reason to run
an unbounded suite.

## Retained Python tests

| File or node | Trigger | Purpose | Minimum subject |
| --- | --- | --- | --- |
| `tests/test_ci_master_admission.py` | `ci_master_admission.py`, PR admission wiring, production-evidence admission, or this test changes | Prove exact changed paths select named checks, unknown evidence stops, exact merges remain bound, and production evidence fails closed | Exact admission nodes for the changed decision |
| `tests/test_ci_workflow.py` | A workflow file or this workflow-contract test changes | Prove permissions, dependencies, trigger routing, and publication gates remain bounded | Exact workflow nodes for the changed job chain |
| `tests/test_cli_smoke.py` | MTGO, Melee, Landing-review, or catalog CLI dispatch/package wiring changes; the Melee smoke also runs immediately before live collection | Prove only the changed command parser and dispatch path can run offline | The named CLI node, never the whole file by default |
| `tests/test_documentation_history.py` | `docs/STATUS.yaml`, live `docs/ROADMAP.md` history pointers, their currently named targets, or this test changes | Enforce bounded live-status fields and require live history pointers to resolve, without asserting completed-phase prose | The status node or pointer node |
| `tests/test_generated_consumer_contracts.py` | An MTGO candidate is generated, before packaging, or the cross-file consumer contract changes | Prove the current candidate is internally consumable without fixed historical-week facts | Current candidate documents only |
| `tests/test_landing_card_image_cache.py` | Rolling featured-card selection, Scryfall Bulk mapping, cache manifest, Pages generated-overlay admission, or their Schema/workflow changes | Prove exact four-week selection, deduplication, complete `normal` image generation without representative-art reuse, double-faced resolution, atomic failure, byte closure, and Pages overlay admission without contacting Scryfall | Synthetic Standard/Modern weeks, Bulk Data, and JPEG bytes only |
| `tests/test_card_names.py` | Shared maintained-alias, front-face, legacy single-slash lookup behavior, or this test changes | Prove one shared lookup entry supplies alias, double-faced, and legacy split-card candidates without changing `SP//dr`-style names | Four fixed card-name strings only |
| `tests/test_simple_card_localization.py` | Flat MTGCH lookup generation, current-Landing Chinese image selection, or this test changes | Prove product keys use shared candidates, unresolved batches narrow safely, name-only entries remain usable, result objects remain independent, and only current Landing images become local files | Synthetic product JSON, MTGCH records, and WebP bytes only |
| `tests/test_github_publication_preflight.py` | `tools/github_publication_preflight.ps1` or its focused mocked contract changes | Prove authentication, permission, scope, PR declaration, and transport failures remain fail closed | Changed preflight states only |
| `tests/test_melee_privacy_validation.py` | Melee production before live collection, or a privacy boundary change | Prove the smallest minimized resource is accepted and a prohibited persisted key is rejected independently of Schema permissiveness | One valid tournament document and one invalid key |
| `tests/test_melee_multi_event_matchup.py` | The pure Melee multi-event aggregator, its compatibility failure vocabulary, canonical identity union, raw-count roll-up, the shared `literal_match_record` or `wilson_interval` implementation it consumes, or this test changes | Prove synthetic same-format events aggregate only leaf W-L-D counts and fail closed on incompatible identity, Schema, source, format, scope, or quality inputs | The complete synthetic multi-event contract file |
| `tests/test_melee_multi_event_contract.py` | The versioned Melee multi-event result, catalog compatibility block or version, catalog producer wiring, catalog admission wrapper, either directly owned Schema, or this test changes | Prove legacy catalogs remain single-event compatible but multi-event ineligible, catalog evidence reconciles fail closed, and admitted results validate against the in-memory Schema | The complete synthetic versioned-contract file |
| `tests/test_melee_multi_event_parity.py` | The shared multi-event parity fixture, Python contract output consumed by JavaScript, JavaScript multi-event aggregator, or this test changes | Keep one Python-owned synthetic success result and rejection vocabulary as the exact cross-runtime contract without repeating the complete P13-01 or P13-02 suites | The complete shared parity fixture only |
| `tests/test_mtgo_fetch_recovery.py` | MTGO fetch retry classification, month traversal, transient exit code, or the matching recovery steps in `update.yml` change | Prove only explicitly transient source failures retry and stop subsequent collection safely | Synthetic response and command nodes only |
| `tests/test_mtgo_landing_editorial.py` | Landing workbook parsing/import, bilingual stages, review binding, or editorial schemas change | Prove blank-cell parsing, bilingual completeness, stale-binding rejection, deterministic import, and hash pinning with a generated minimal workbook | Generated one-scope OOXML carrier |
| `tests/test_mtgo_landing_screening.py` | Landing screening policy or representative selection changes | Prove exact Top 8 gating, thresholds, continuity, reason merging, build comparison, and later-date ties | Synthetic selection subjects only |
| `tests/test_mtgo_landing_screening_provenance.py` | Landing candidate provenance, classifier/selection digest binding, or review-preservation behavior changes | Prove stale candidates regenerate and reviewed subjects remain fail closed | Synthetic provenance subjects only |
| `tests/test_mtgo_landing.py` | Landing facts, reviewed-feature binding, latest-only production admission, or Pages private-file exclusions change | Prove generic no-event output, review binding, exact deck links, and public/private path separation | Synthetic Landing boundaries plus current-candidate cross-file binding |
| `tests/test_mtgo_metadata.py` | MTGO metadata generation, hierarchy ownership, Landing/Pickup metadata routing, or this test changes | Prove metadata points to Landing and keeps hierarchy counts owned by the generated hierarchy | One synthetic metadata subject |
| `tests/test_mtgo_top8_restatement.py` | Top 8 generator, classifier digest, lifecycle contract, or Top 8 Schema changes | Prove retained source facts stay fixed while current-classifier identities restate deterministically, including explicit Unknown | Three synthetic source/classifier cases |
| `tests/test_validate_repository_modes.py` | `validate_repository.py`, changed-scope Schema selection, `validate_schemas.py`, or this test changes | Prove changed-mode parsing and Schema validation exclude unrelated documents while full Schema validation retains the complete manifest | Synthetic changed and unrelated files |
| `tests/test_weekly_maintenance_readiness.py` | Weekly readiness generator or private readiness Schema changes | Prove exact-week Unknown binding, separately retained full-corpus Unknown evidence and decklists, strict intentional-random separation, Landing-screening availability, deterministic digesting, and fail-closed cross-format lifecycle | Synthetic Standard and Modern handoff only |

The public data/output rows remain bounded to their named subjects. The
documentation and CI rows are control-plane checks. The Landing-screening and weekly-
readiness rows are private review and handoff contracts; neither runs in
production candidate validation.

## Non-pytest validators and UI checks

| Trigger | Command or check | Purpose | Repeat rule |
| --- | --- | --- | --- |
| Any targeted PR | `python -B validate_repository.py --changed-from <base-sha>` | Parse changed maintained files and run only directly coupled repository-reference contracts | Once on the final PR head |
| Maintained Python changes | Ruff and mypy commands in `ci.yml` | Catch syntax/import and maintained type-contract failures | Once on the final PR head |
| One format's rule file, shared rule validator, or direct rule contract changes | `validate_rules.py` for only the affected format, or both formats for a shared validator change | Reject invalid classifier rules without validating the unrelated format | Once on the final PR head |
| A mapped ordinary public JSON document changes | `python -B validate_schemas.py --changed-from <base-sha>` | Validate only changed documents covered by the current manifest | Once on the final PR head |
| A Schema, Schema manifest, or Schema validator changes | `python -B validate_schemas.py` | Prove the complete declared public contract migration | Once on the final PR head |
| Cache-A external-source integration changes | One read-only build of the current rolling subject from Scryfall Oracle Cards Bulk Data and image CDN into an external temporary directory, followed by local verification | Prove every current featured name resolves to a complete `normal` card image and the real immutable bundle closes without writing images to Git or reusing representative art | Once on the final Cache-A tree before Owner review; never from automated tests |
| Cache-B manifest admission, recent-week image selection, or older-week fallback changes | `node --test tests/js/phase8-runtime.test.js tests/js/phase8-landing.test.js tests/js/phase8-card-preview.test.js tests/js/phase8-landing-controller.test.js`, then focused local browser review with deterministic local failure/fallback fixtures and Scryfall image requests left unstarted | Prove recent admitted weeks use one local source for inline and preview, older or unavailable cache subjects fall back, and the existing paced/group retry path remains usable without contacting Scryfall | Once on the final visible tree before Owner review at desktop, 390px, and 412px |
| Chinese card-name or card-image implementation changes | Focused generated-map parsing and current-Landing local-file existence checks, plus the smallest Node contract that covers Chinese local, Chinese MTGCH, English local, and English Scryfall selection | Prove the flat lookup and four source-selection outcomes used by the product; reuse the accepted MTGCH source/direct-image evidence and do not repeat availability, latency, cache, image-size, Bulk-snapshot, or provenance-manifest trials | Once on the final `L10N-SIMPLE` tree before Owner review; mandatory changed-scope repository checks still apply |
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
