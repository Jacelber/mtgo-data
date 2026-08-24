# Development Roadmap

## Live-document contract

This document contains only the active phase, useful future phases, and their
acceptance criteria. It never authorizes work: read `docs/STATUS.yaml` for the
current task, blockers, and stop conditions. Product, statistical, and data
contracts remain in their dedicated specifications.

Completed and superseded roadmap detail is non-authoritative history:

- Phases 0–11 and superseded specifications:
  `docs/history/ROADMAP-PHASES-0-11.md`;
- completed Phase 12 tasks P12-01 through P12-09, P12-13A, and P12-15C:
  `docs/history/ROADMAP-PHASE-12-COMPLETED.md`.

## Phase index

| Phase | Objective | Status |
| --- | --- | --- |
| 12 | Productize loading, state, accessibility, sharing, and the MTGO Landing under one visual system. | Active; combined P12-11B/P12-12 Owner-accepted for Gate 6 completion; later tasks not authorized |
| 13 | Aggregate compatible multi-event matchups from raw counts. | Planned; not authorized |
| 14 | Add Pauper MTGO and approved Paupergeddon support. | Planned; not authorized |
| 15 | Add Pioneer through the established dual-product process. | Planned; not authorized |
| 16 | Add Legacy and approved Eternal Weekend Legacy support. | Planned; not authorized |
| 17 | Add qualifying Standard Tabletop events. | Planned; not authorized |
| 18 | Decide whether Vintage should be implemented. | Decision gate; not authorized |
| 19 | Complete release and long-term maintenance readiness. | Planned; not authorized |

---

# Phase 12 — Front-end productization, editorial landing, and visual system

Completed P12-01 through P12-09, P12-13A, and P12-15C detail is archived in
`docs/history/ROADMAP-PHASE-12-COMPLETED.md`.

## Objective

Make the existing static MTGO and Tabletop products faster, shareable,
accessible, resilient, and usable across desktop and mobile. Add a curated
MTGO weekly landing view while preserving statistical meaning, product
separation, and established public entry points.

The separately authorized `CLASSIFIER-RESTATEMENT-01` maintenance repair must
replace historical-classification equality with immutable source-fact checks,
restate every retained Top 8 week and base under one current classifier digest,
and stop for Owner acceptance before any remote or production action. It does
not authorize a classifier rule change or begin P12-10.

`WEEKLY-MAINTENANCE-WORKFLOW-01` establishes the non-Codex scheduler and
private handoff used before Landing work. The MTGO production workflow runs at
18:00 JST, emits a Schema-validated internal readiness artifact, and maintains
one deduplicated weekly Issue. The Owner then starts one exact review manually.
This infrastructure changes no public data or page and does not itself perform
classifier, visual-metadata, Pickup, or Landing decisions. After one accepted
no-publication rehearsal on current data, the Owner decides whether P12-10 may
begin under separate authorization.

## Remaining task sequence

10. `P12-10` — Landing weekly-facts producer and Pickup integration
    - the accepted weekly-maintenance no-publication rehearsal and separate
      2026-08-21 Owner authorization satisfied the start gate; local
      implementation and proportionate validation are complete, and the Owner
      accepted the unchanged subject for Gate 6 completion on 2026-08-21;
    - the completed gate covered every unresolved historical/current Unknown
      through the complete-decklist review carrier; the P12-03 classifier
      remediation, refreshed shadow, Owner threshold confirmation, known-state
      migration check, and representative-card approval are complete;
    - add the Schema-validated latest-only
      `stats/<format>/mtgo/landing/current.json` document under the reviewed
      manifest, catalog, workflow, production-candidate, and Pages-allowlist
      boundaries;
    - generate byte-deterministic structured changes, trends, raw counts,
      selected key-card identities, source event IDs, and the common classifier
      rule version or digest without generated Chinese or English prose;
    - extend the existing format-scoped Weekly Pickup candidates and manual
      publication fields for Landing headlines, positioning copy, and approved
      featured items; do not add parallel root-level candidate configuration;
    - refresh unreviewed provisional-week facts after additive late events,
      preserve reviewed content for explicit re-review, and never auto-publish
      an unreviewed candidate;
    - produce a Schema-valid no-event document and a Schema-valid empty-feature
      list when those are the truthful states; fail publication for malformed,
      internally inconsistent, or missing required Landing output;
    - exclude candidate, review-note, design, and other non-public working files
      from the Pages artifact, and prove that only the admitted current document
      is deployable;
    - preserve every pre-existing statistic, Pickup public document and history
      index, rule, comparison base, and protected `434455` byte. The P12-04B
      product-contract migration authorizes using Pickup as Landing's internal
      feature source, not deleting or rewriting those documents.
11. `P12-11A` — Landing summary editorial boundary
    - retain every eligible machine summary candidate privately without a five-
      item truncation, and read every approved row plus exact localized copy
      from the already published Pickup `1.1.0` week; keep post-ban Owner-only;
    - require an explicit reviewed state and allow zero or more ordered human-
      final rows, each optionally linked to zero, one or multiple review-input
      IDs; allow complete human rewrite or unrelated content;
    - maintain a separate catalog of every current-week Top 8 deck, let each
      human-final row place any number of exact `deck:<deck ID>` tokens at the
      desired positions, derive localized displays and link order rather than
      asking the reviewer for names or URLs, and publish each token with its
      resolved structured deck identity; never publish machine candidates,
      review-input IDs, drafts, or review vocabulary; preserve the last admitted
      document when review is missing or stale;
    - use the published Pickup week as the sole source of reviewed Pickup
      content, keep the existing format-scoped candidate YAML as the sole
      Landing review-state store, and use XLSX only as a visually verified
      review carrier.
11B. `P12-11B` — Landing weekly summary and environment UI
    - the Owner accepted the final combined P12-11B/P12-12 browser subject on
      2026-08-22, authorizing same-task completion through one commit, one Ready
      pull request, required CI, normal merge, and merge-triggered Pages
      verification; P12-15, P12-16, and every other task remain separate gates;
    - render every reviewed human-final weekly-summary row without forcing a
      minimum or maximum, plus the environment composition strip and high-score-
      share structure list from the same P12-11A document;
    - show every archetype above the owner-approved high-score-share threshold;
      render current, previous-week, and aggregated previous-four-week high-score
      shares plus direction in the accepted A3 UI, while retaining their raw
      counts and denominators in the public data document; keep current Top 8
      values as supporting data only and do not apply a 20-deck exclusion;
    - make the composition segments and list rows use the same archetype set and
      the P12-02 shareable detail URL;
    - render text before progressively loaded key-card images and provide a
      useful no-event state;
    - keep this view non-default and reachable through its explicit P12-02 URL
      until the complete Landing is accepted in P12-16.
12. `P12-12` — Landing curated new-deck and new-technology panel
    - completion authority is shared with the accepted combined P12-11B/P12-12
      subject recorded above;
    - show every approved item for the selected feature week, with all
      `new_deck` items before all `new_technology` items, category, archetype,
      editorial positioning, four reviewer-selected cards, supporting facts,
      and a shareable full-deck link;
    - place one week selector inside the Landing feature panel, default it to
      the current week, and reuse the existing Pickup index and week documents;
      selecting history changes only this panel and never the current Landing
      brief, environment, composition, or construction-change facts;
    - render only the currently selected language, rerender the same item when
      the existing Chinese or English control changes, and do not introduce a
      side-by-side bilingual Landing mode;
    - reuse the common card-image preview, placeholder, and failure behavior;
    - use one disclosure action per item and the shared deck-detail view; show a
      stable-environment empty state when no item was approved, never expose a
      pending-review state or internal approval vocabulary, and introduce no
      standalone Weekly Pickup front-end state.
    - P12-15A through P12-15G, including P12-15E-UX, supersede the delivered
      Pickup handoff and history source. They preserve this accepted panel
      structure, ordering, cards, disclosure, language, empty-state, and
      deck-detail behavior except for the bounded DEC-114 navigation and
      interaction corrections.
13. `P12-13` — Large-matrix interaction, delivered as separately accepted
    sequential subtasks
    - `P12-13A` — completed matrix search and shared visible-projection
      foundation; its detailed contract is archived in
      `docs/history/ROADMAP-PHASE-12-COMPLETED.md`;
    - `BROODSCALE-SUBTYPE-AND-COMPOSITION-NAVIGATION-HOTFIX` — completed;
      its classifier and responsive composition-navigation contract is
      archived in `docs/history/ROADMAP-PHASE-12-COMPLETED.md`;
    - `P12-13B` — completed exact row filter, hierarchical disclosure, row
      detail navigation, responsive identity-column, and stable sticky-header
      behavior; its detailed contract is archived in
      `docs/history/ROADMAP-PHASE-12-COMPLETED.md`;
    - `P12-13C` — completed Owner-accepted mainstream matchup projection for
      both products, with source-specific 2% parent eligibility, preserved
      subtype/filter state, lazy MTGO share loading, and no statistical or
      public-data change; the decision contract is recorded in `DEC-100`;
    - `P12-13F` — bounded keyboard-horizontal movement: when keyboard
      focus is within a matchup matrix, let Left and Right move the horizontal
      matrix viewport while preserving the existing native Up and Down vertical
      behavior. Do not add URL state, wrapping, filter or disclosure mutation,
      four-direction cell-focus navigation, or a second matrix presentation;
    - P12-13F requires separate implementation authorization and Owner hands-on
      acceptance in a locally served browser against the final unchanged UI
      tree. Codex first completes focused automated and developer-browser checks,
      then supplies the exact local URL and keyboard checklist; a screenshot,
      automated result, or Codex-only walkthrough cannot substitute for the
      Owner's direct interaction and explicit decision;
    - P12-13F preserves the existing matchup formulas, literal W-L-D
      counts, confidence intervals, 20-match warning, public JSON, Schemas,
      workflows, public paths, and protected event `434455` bytes.
14. `P12-14` — Cancelled by Owner
    - the accepted mobile matrix is retained as implemented; no separate
      single-archetype vertical opponent view will be added;
    - the shared card-image preview and its failure behavior were already
      delivered and accepted in P12-09 and subsequent Landing validation, so
      they will not be redeveloped as a second task;
    - this cancellation does not remove P12-16's complete cross-device
      verification requirement.
15. `P12-15` — Metadata and sharing
    - completed and published through the accepted metadata, attribution,
      language-memory, favicon, share-image, and legacy-URL compatibility
      subject;
    - add description, Open Graph, favicon, canonical URL, language memory, and
      required Scryfall and Wizards attribution;
    - provide appropriate Landing metadata without presenting machine facts as
      human editorial claims;
    - define a canonical Landing feature URL and map legacy
      `product=weekly-pickup&week=<week>` state to
      `product=mtgo-landing&section=features&week=<week>`, with the week scoped
      only to the feature panel.
15A. `P12-15A` — Landing editorial-pipeline route map
    - document the approved replacement of the obsolete public Pickup handoff
      before any workbook, producer, public-data, front-end, or cleanup change;
    - define the Landing-owned private review source, latest document, bounded
      feature archive, W27/W33 recovery set, ordered task gates, rollback, and
      deletion conditions in `docs/LANDING_EDITORIAL_PIPELINE.md`;
    - update the current weekly-maintenance, product-scope, architecture,
      decision, roadmap, and status authorities consistently;
    - stop for Owner acceptance with no page, workbook, code, workflow,
      generated data, public path, or Schema change.
15B. `P12-15B` — Landing-only review workbook
    - preserve existing Owner text and the corrected Modern order while
      replacing the mixed seven-sheet carrier with `Review Control`, `Landing
      Copy`, `Featured Decks`, `All Top 8`, and `Field Guide`;
    - put selected-deck identity and exact `deck:<ID>` tokens directly in the
      copy sheet and omit internal input IDs, generated labels, and unknown
      implementation columns from Owner input;
    - make every exact deck referenced in retained or draft top copy a
      mandatory `KEEP` row in `Featured Decks`, with no top-copy-only role;
    - remove the manual feature-order and localized-title inputs: feature order
      is derived from category plus exact deck-token appearance in final top
      copy, and the title is derived from the format/classifier identity's
      bilingual name;
    - preload Standard W27, Standard W33, and Modern W33 recovery rows, render
      every sheet, and stop for Owner completion without changing the page.
15C. `P12-15C` — Content completion and bilingual review
    - completed detail is archived in
      `docs/history/ROADMAP-PHASE-12-COMPLETED.md`; P12-15D remains a separate
      authorization gate.
15D. `P12-15D` — Internal Landing editorial backend
    - completed detail and accepted results are archived in
      `docs/history/ROADMAP-PHASE-12-COMPLETED.md`; P12-15E remains a separate
      authorization gate.
15-HF. `P12-15-HF` — Emergency Melee entry recovery and static home link
    - completed detail and accepted results are archived in
      `docs/history/ROADMAP-PHASE-12-COMPLETED.md`; P12-15E remains a separate
      authorization gate.
15-HF2. `P12-15-HF2` — Production smoke compatibility recovery
    - replace the obsolete fixed Pickup count and archetype assertion with a
      candidate-derived check of the accepted legacy URL to Landing Features
      contract, without changing runtime code, public data, or workflow behavior;
    - verify governance and JavaScript syntax locally, then validate the browser
      contract once on the newly generated production candidate after Owner
      acceptance and accepted-task completion.
15-HF2B. `P12-15-HF2B` — Retained Landing production compatibility recovery
    - keep the last admitted Landing readable when newer unreviewed statistics
      exist, without combining periods or weakening format validation;
    - make the remaining production matchup smoke checks independent of rolling
      archetype order and row position, then stop for new Owner acceptance before
      any commit or production recovery.
15E. `P12-15E` — Landing feature archive and recovery preview
    - add versioned `landing/features/index.json` and
      `landing/features/<week>.json` contracts, consumers, catalogs, Pages
      admission, and focused tests;
    - generate Standard W27, Standard W33, and Modern W33 from the completed
      review source and build one local preview while preserving the accepted
      Landing structure and all design elements not explicitly amended below;
    - resolve every admitted inline Landing-copy deck token to its exact
      selected feature in the applicable format and feature week: select that
      week, expand the item, move it into view, and expose a stable URL/focus
      destination. Keep the exact Top 8 route only as a legacy defensive
      fallback; new unmatched reviewed content is invalid;
    - verify both languages, both formats, historical selection, deck links,
      card display, responsive behavior, and explicit empty weeks, then stop
      for hands-on Owner acceptance.
15E-I18N. `P12-15E-I18N` — Classifier-name localization across retained views
    - begin only after hands-on acceptance of the P12-15E data-backed local
      preview; keep this separate from classifier rules, statistical meaning,
      and the accepted UI structure;
    - generate and admit one format-scoped public bilingual name contract from
      the P12-15D repository-managed catalog, preserving the classifier
      taxonomy as the English authority and the Owner-approved Chinese values;
    - make Landing, every retained MTGO view, and classifier-backed Tabletop
      views resolve parent and subtype labels by stable IDs and selected
      language instead of matching or reusing English display text;
    - keep English pages unchanged, require approved Chinese coverage for known
      identities, and handle Unknown or other non-classifier UI vocabulary
      through the existing interface localization boundary;
    - verify Chinese and English independently across Standard, Modern, every
      retained MTGO view, applicable Tabletop views, direct URLs, language
      switching, desktop, and 390px width, then stop for hands-on Owner
      acceptance.
15E-UX. `P12-15E-UX` — Feature-release interaction corrections
    - begin only after hands-on acceptance of P12-15E and P12-15E-I18N and
      before the cloud cutover; keep this focused on the five Owner-approved
      interaction and deck-context corrections discovered during recovery
      review;
    - after a desktop or mobile composition-segment activation expands a deck,
      scroll the newly revealed detail into a perceptible viewport position and
      preserve keyboard focus and reduced-motion behavior;
    - at mobile widths, move the accepted 90 by 63 representative-card stack
      lower relative to the archetype heading and remove the excessive lower
      whitespace without changing image size, overlap direction, or desktop
      placement;
    - add one shared fixed bottom-right return-to-top control to the Landing,
      all retained MTGO views, and Tabletop, with safe-area spacing, keyboard
      access, localized accessible naming, reduced-motion behavior, and no
      content obstruction at 390 pixels;
    - carry the official source event identity and name into current rolling
      MTGO best and representative deck records without changing event bytes or
      statistical values; display date only plus event name and player count in
      Landing Environment and MTGO Statistics details;
    - in Top 8, keep event context in the table rather than duplicating it in
      the deck detail, and highlight both the current placement cell and its
      event header across direct-link and close behavior;
    - verify all five corrections in the same local release candidate and
      stop for hands-on Owner acceptance;
    - the Owner accepted the complete cumulative recovery candidate, including
      the final mobile Landing row interaction corrections, on 2026-08-24;
      cloud publication remains the separately gated P12-15F task.
15F. `P12-15F` — Cloud cutover
    - begin only after hands-on acceptance of P12-15E, P12-15E-I18N, and
      P12-15E-UX;
    - authorized on 2026-08-24 to reuse and publish the exact accepted
      cumulative workspace; no accepted UI, content, data, or interaction may
      change during cutover;
    - after the production-recovery insertion advanced cloud master to
      `f4ae158`, preserve its W34 production data and retained-Landing runtime,
      regenerate only the accepted representative-deck event context, and stop
      for renewed Owner acceptance of the final integrated UI bytes before the
      first remote write;
    - publish the accepted latest Landing, feature archive, feature-aware deck
      destinations, public bilingual classifier-name contract, localized
      retained-view consumers, and interaction corrections together; switch
      the feature selector from Pickup history to Landing feature history, and
      verify the merge-triggered Pages deployment;
    - prove that live Landing requests no Pickup week document while preserving
      the tested legacy URL redirect and retaining old files for rollback;
    - stop after verified cutover; cleanup remains a separate task.
15G. `P12-15G` — Pickup retirement cleanup
    - prove no production, catalog, metadata, Pages, test, or front-end caller
      needs the standalone Pickup product or publisher;
    - migrate candidate preparation, known-state reads, readiness, hierarchy,
      and metadata to Landing-owned or neutral modules and paths;
    - remove only proven-dead page, navigation, style, publisher, capability,
      catalog identity, and dedicated test code; retain the legacy URL redirect
      and nullable metadata compatibility field;
    - require candidate-path output equivalence and a full tracked-file
      no-caller search before acceptance;
    - delete or relocate frozen Pickup documents only with exact path
      declarations, replacement verification, rollback evidence, and separate
      Owner acceptance.
16. `P12-16` — Cross-device and visual-system closeout
    - begin only after P12-15A through P12-15G, including P12-15E-I18N and
      P12-15E-UX, are complete or a named legacy compatibility artifact is
      explicitly deferred by the Owner;
    - verify the Landing plus the four retained top-level product views in
      Chinese and English independently, both public MTGO formats, the protected
      Tabletop product, desktop, 390px width, language switching, URL
      restoration, and zero application console errors;
    - after the complete Landing, empty states, failure fallback, direct links,
      and Pages artifact are accepted, make it the bare `/index.html` MTGO
      default while retaining every explicit existing product URL through a
      compatible destination;
    - verify that `weekly-pickup` is absent from product navigation, product
      order, and standalone identity after P12-15G while old URLs still open the
      requested Landing feature week. Preserve only explicitly deferred
      rollback artifacts;
    - reverify the P12-15E-UX composition reveal, mobile representative-card
      alignment, shared return-to-top control, source-backed event context, and
      current Top 8 placement highlight across the applicable retained views;
    - reverify that every classifier-backed parent and subtype label follows
      the selected language across all retained views without changing stable
      classifier identity or statistical meaning;
    - verify that no future format can be catalog-public without an admitted
      Landing and all required MTGO products, while the Standard and Modern
      migration exceptions both satisfy this invariant at closeout;
    - compare request count, transferred bytes, readable-content timing, image
      request behavior, and layout stability with the P12-01 baseline; stop for
      review on an unexplained material regression rather than inventing an
      arbitrary pre-measurement limit;
    - keep the default-product selection independently reversible and exercise
      a local rollback that restores the prior statistics default without
      deleting the Landing document or changing any explicit public URL;
    - audit every migrated view against the accepted visual-system contract and
      record any intentionally deferred component rather than silently leaving
      a second visual language.

This phase does not authorize changing the existing 20-match warning,
migrating the Tabletop null threshold into generated data, merging MTGO and
Tabletop statistics, claiming statistical significance from interval overlap,
automatically publishing editorial candidates, presenting the DEC-083 internal
week lifecycle as a user warning, or changing an established generated path.
The new public-data boundary is the format-scoped Landing product after separate
P12-03 contract acceptance and P12-10 implementation authorization. Phase 12
publishes only the latest complete Landing document plus the P12-15E bounded
feature archive; it does not authorize historical complete-Landing browsing or
cross-classification-version trend analysis. Selecting an approved historical
feature week inside the feature section does not change that rule.

## Acceptance criteria

Phase 12 is complete when:

- overview views avoid unnecessary large-document requests;
- supported state survives sharing, reload, back, and forward navigation;
- the selected visual system governs the Landing, shared shell, and every
  migrated existing view without a required framework or build step;
- the Landing answers what changed, what the current environment looks like,
  and what new decks or technology were manually selected, using one
  format-scoped structured source;
- the bare MTGO entry changes to the Landing only in P12-16 after complete
  acceptance, while existing explicit product links remain compatible and old
  Weekly Pickup links resolve to the corresponding Landing feature week;
- machine facts, fixed translations, and human editorial copy remain separate,
  and no unreviewed candidate reaches the public product;
- no 20-deck filter or unsupported statistical-significance claim is introduced;
- chart names, order, and colors do not imply false equivalence or changing
  identity;
- keyboard and mobile users can operate Landing links and inspect large
  matrices without traversing thousands of tab stops;
- failure states can retry safely and progressive images do not block readable
  content or shift established layout;
- every retained classification-derived Top 8 artifact uses one current
  classifier digest, while immutable source facts and unavailable comparisons
  produce no false environment-change claim;
- real-browser acceptance passes across the required products, formats,
  languages, and viewport sizes, with exactly one selected language rendered at
  a time;
- the Pages artifact contains the admitted latest Landing document but no
  candidate, review, design, or other working file;
- measured loading behavior has no unexplained material regression, and the
  bare-entry Landing cutover has a verified reversible default-state rollback;
- all pre-existing public JSON paths, statistical formulas, and protected
  `434455` bytes remain unchanged, while the new Landing documents pass their
  versioned Schema and production-publication boundaries.

---

# Phase 13 — Multi-event raw-count matchup aggregation

## Objective

Allow matchup matrices to combine selected events without merging unrelated overview statistics.

## Required work

### Aggregation eligibility

Only combine events that:

- use the same Constructed format;
- use compatible archetype IDs;
- pass schema validation;
- pass required quality checks;
- are explicitly selected;
- expose the requested matchup scope.

### Aggregation method

Aggregate raw counts:

- wins;
- losses;
- played draws;
- valid matches.

Do not average already calculated percentages.

### Default exclusions

Exclude from primary matchup aggregation:

- mirror matches from overall non-mirror win rate;
- byes;
- no-shows;
- intentional draws;
- official awarded wins;
- Draft rounds;
- unknown rounds;
- unknown results;
- playoffs, unless a separate playoff view is explicitly selected.

### Scope behavior

The matrix must identify whether it uses:

- all Constructed Swiss;
- Day 1 Constructed only;
- Day 2 Constructed only.

For mixed events, the default may be all Constructed Swiss, but Day 1 and Day 2 scopes must remain available where data permits.

For the initial multi-event product, selecting two or more compatible events
forces `all_constructed`, the only scope common to all three approved event
structures. Day 1 and Day 2 remain selectable only for one event that declares
those scopes. A later expansion of multi-event stage-specific aggregation
requires a separate compatibility decision.

## Task sequence

1. Freeze compatibility rules for source, Constructed format, schema version,
   archetype identity, quality status, and supported scope.
2. Aggregate underlying eligible W-L-D counts and recalculate all rates and
   intervals from those counts.
3. Keep event overview documents independent and do not average event rates.
4. Limit initial multi-event selection to `all_constructed` as required by
   DEC-061.
5. When a second event is selected, switch to `all_constructed`; when selection
   returns to one event, restore its prior scope only if the catalog still
   declares that scope.
6. Persist selected event identities through the canonical multi-event URL
   representation reserved by P12-02; selected events are durable user state,
   while transient expanded table rows remain outside the URL.
7. Keep the production multi-event entry disabled until at least two compatible
   real events are approved. Synthetic contracts may prove the engineering
   capability but do not constitute real production acceptance.

## Acceptance criteria

Phase 13 is complete when:

- single-event and multi-event matrices reconcile from raw counts;
- cross-format selection is impossible;
- incompatible schema versions are rejected or migrated;
- sample size is displayed;
- low-sample warnings are displayed;
- confidence intervals are generated where specified;
- scope selection is visible;
- overview metrics remain per-event rather than merged.

---

# Phase 14 — Pauper MTGO and Paupergeddon

## Objective

Add Pauper to both product tracks after the Modern reference path and reusable event strategies are stable.

## Required work

Use the shared classifier and stable Pauper archetype identities for both
sources while keeping MTGO and Tabletop inputs, outputs, statistics, catalogs,
and product behavior separate. Depend on the engineering and front-end
baselines established by Phases 10 through 12.

Pauper must publish an admitted Landing under the Phase 12 contract in the same
public launch as its other required MTGO products. Until that complete set is
ready, the format remains unavailable in the public catalog.

## Task sequence

1. Add Pauper archetype rules.
2. Add Pauper rule fixtures.
3. Validate Pauper rule IDs and priorities.
4. Run Pauper MTGO classification.
5. Generate Pauper MTGO statistics.
6. Validate Pauper MTGO output.
7. Register the approved Paupergeddon main event.
8. Normalize and validate that event as `constructed_day2`.
9. Generate event-specific Pauper statistics.
10. Enable Pauper in both front ends only when its reviewed Landing and every
    required product are produced and admitted together.

## Acceptance criteria

Phase 14 is complete when:

- shared Pauper archetype IDs are used by both sources;
- MTGO and Melee data remain separate;
- MTGO and Melee statistics remain separate;
- Pauper rules pass validation;
- Standard and Modern regression tests pass;
- front-end format selection is catalog-driven;
- Pauper is not public until Landing and every required MTGO product are
  admitted together;
- quality reports are available.

---

# Phase 15 — Pioneer

## Objective

Add Pioneer using the established shared-classifier and dual-product process.

## Required work

Use the established shared-classifier and dual-product process without copying
or forking the Standard-only pipeline. Depend on the engineering and front-end
baselines established by Phases 10 through 12.

Pioneer must admit a reviewed Landing and every required MTGO product in one
public launch. It remains unavailable in the public catalog until that set is
complete.

## Task sequence

1. Add Pioneer archetype rules.
2. Add Pioneer fixtures.
3. Validate rule IDs and priorities.
4. Add Pioneer MTGO processing.
5. Validate Pioneer MTGO statistics.
6. Register an approved Pioneer Melee event.
7. Normalize and validate the event.
8. Generate event-specific Pioneer statistics.
9. Enable Pioneer in both front ends only when Landing and every required
   product are generated and admitted together.

## Acceptance criteria

Phase 15 is complete when:

- Pioneer uses the generalized MTGO pipeline;
- Pioneer uses the shared classifier;
- MTGO and Melee remain separate;
- no copied Standard-only pipeline is introduced;
- rules, tests, schemas, and catalogs are updated;
- Pioneer is not public without an admitted Landing and complete required
  product set;
- prior-format regression tests pass.

---

# Phase 16 — Legacy and Eternal Weekend

## Objective

Add Legacy using the established process, including approved Eternal Weekend Legacy main events.

## Required work

Use the established shared-classifier and dual-product process for Legacy, and
retain the approved Eternal Weekend main-event boundary. Depend on the
engineering and front-end baselines established by Phases 10 through 12.

Legacy must admit a reviewed Landing and every required MTGO product in one
public launch. It remains unavailable in the public catalog until that set is
complete.

## Task sequence

1. Add Legacy archetype rules.
2. Add Legacy fixtures.
3. Validate rule IDs and priorities.
4. Add Legacy MTGO processing.
5. Validate Legacy MTGO statistics.
6. Register an Eternal Weekend Legacy main event.
7. Normalize and validate the event.
8. Generate event-specific Legacy statistics.
9. Enable Legacy in both front ends only when Landing and every required
   product are generated and admitted together.

### Event restrictions

Only approved Eternal Weekend main events may be included under this policy.

Do not include:

- side events;
- trials;
- qualifiers;
- team events;
- unrelated Legacy events not present in the whitelist.

## Acceptance criteria

Phase 16 is complete when:

- only the approved main event is included;
- side events remain excluded;
- shared Legacy archetype IDs are stable;
- MTGO and Melee remain separate;
- Legacy is not public without an admitted Landing and complete required
  product set;
- prior-format regressions pass;
- front-end catalogs are updated.

---

# Phase 17 — Standard Tabletop events

## Objective

Enable qualifying Standard tabletop events after the Melee pipeline is stable.

## Required work

Only Standard events matching the approved event policy may be added.

Standard MTGO and Standard Melee must remain separate in:

- raw data;
- normalized data;
- generated statistics;
- catalogs;
- front-end presentation.

Qualifying mixed-format Standard events must use the mixed-event strategy.

## Task sequence

1. Select only owner-approved Standard events that satisfy the whitelist and
   event-category policy.
2. Validate each event's source completeness and declared structure.
3. Reuse the shared Standard classifier without merging MTGO and Tabletop data.
4. Generate event-specific Tabletop statistics and quality evidence.
5. Validate mixed, Constructed Day 2, or single-stage behavior as applicable.
6. Enable each event through the catalog only after separate owner approval.
7. Run Standard MTGO regression and cross-product browser acceptance.

## Acceptance criteria

Phase 17 is complete when:

- Standard tabletop events use the shared Standard classifier;
- no MTGO and Melee statistics are merged;
- mixed-format rules are applied where required;
- current Standard MTGO behavior remains compatible;
- data quality and source metadata are visible.

---

# Phase 18 — Vintage decision gate

## Objective

Decide whether Vintage support should be implemented.

## Required work

Review:

- available MTGO Vintage data;
- Eternal Weekend Vintage data quality;
- decklist completeness;
- matchup completeness;
- classification maintenance cost;
- expected user value;
- front-end impact;
- automation impact;
- long-term operational cost.

## Task sequence

1. Audit the available MTGO and Eternal Weekend Vintage evidence.
2. Estimate classification, data-quality, front-end, automation, and ongoing
   maintenance cost.
3. Present approve, defer, and reject options to the owner.
4. Stop for an explicit owner decision.
5. If approved, add separately authorized implementation tasks using the
   established process; do not enable Vintage through this decision task.

### Possible outcomes

The project owner may:

1. approve Vintage and implement it using the established process;
2. defer Vintage with a documented reason;
3. reject Vintage from the current scope.

## Acceptance criteria

Phase 18 is complete when:

- the decision is recorded in `docs/DECISIONS.md`;
- `docs/PROJECT_SCOPE.md` is updated;
- `docs/STATUS.yaml` is updated;
- the roadmap is updated if implementation phases change;
- Vintage is not enabled before the decision is recorded.

---

# Phase 19 — Release and long-term maintenance closeout

## Objective

Prove that the completed product, data, and operational system can be released,
recovered, rolled back, and maintained without relying on undocumented project
history or unverified compatibility entry points.

## Required work

- complete only the compatibility cleanup that remains after Phase 11 owner
  review, beginning with the DEC-078 draw-adjusted metric retirement;
- publish current operator documentation for MTGO, Tabletop, Landing and Weekly
  Pickup editorial review, late-event re-review, storage, Pages, workflows,
  schemas, rules, quality review, rollback, and recovery;
- exercise the selected public-data and archive-storage design end to end;
- run regression across every approved format and both product areas;
- define long-term ownership, maintenance cadence, incident handling, and
  release evidence;
- retain rollback paths until the release is accepted.

## Task sequence

1. Retire the draw-adjusted win-rate calculation and compatibility fields under
   a dedicated versioned contract migration. Update the statistical
   specification, Schemas, generators, fixtures, tests, public MTGO and
   Tabletop documents, the protected `434455` manifest, legacy JavaScript, and
   rollback evidence without silently changing an existing field's meaning.
2. Reconcile the final list of other compatibility entry points and remove only
   those whose replacements and rollback paths are verified.
3. Complete the operator runbooks and non-programmer maintenance instructions,
   including weekly Landing and Pickup candidate review, publication, valid
   empty states, additive late-event re-review, stale-content diagnosis, and
   Landing fallback recovery.
4. Perform backup restoration, workflow recovery, publication rollback, and
   Pages recovery drills.
5. Exercise the production pipeline from approved source collection through
   data publication without bypassing validation or review gates.
6. Run full cross-format, cross-product, Schema, rule, repository, and
   real-browser regression.
7. Resolve or explicitly defer every release-blocking Unknown, conflict,
   quality, privacy, compatibility, and operational issue.
8. Obtain owner acceptance, publish the approved release tag, and record the
   maintenance responsibility and cadence.

## Acceptance criteria

Phase 19 is complete when:

- compatibility cleanup is approved, verified, documented, and reversible;
- no production generator or retained front-end asset calculates a draw as
  half a win, and the sole published win-rate meaning is declared as
  `wins_over_valid_matches` under the migrated Schema contract;
- written operations cover routine refresh, event addition, Landing and Pickup
  editorial review, late-event re-review, quality review, schema migration,
  deployment, rollback, and recovery;
- Pages, selected data storage, and production workflows pass an end-to-end
  recovery exercise;
- all approved formats and both product areas pass their regression contracts;
- production pages and public paths remain compatible;
- a release tag is published only after separate owner authorization;
- long-term ownership and maintenance cadence are recorded in
  `docs/STATUS.yaml`.

---

# Unnumbered candidate — Environment Trends

## Objective

Evaluate a possible historical Environment Trends capability without treating
it as part of Phase 12 or as approved product scope.

Phase 12 publishes only a latest-state `landing/current.json`. That current
document, its Git history, and the existing Weekly Pickup archive do not by
themselves authorize historical Landing browsing or establish an authoritative
cross-week trend series.

## Required work

- identify an authoritative historical weekly snapshot source;
- define missing-week behavior;
- define comparability across classification-rule changes;
- determine required `docs/PROJECT_SCOPE.md` and
  `docs/STATISTICS_SPEC.md` changes;
- decide whether immutable Landing-week retention is appropriate and how it
  remains comparable across classification-rule and Schema versions;
- decide whether the capability is an extension of the current Environment
  Trends product.

## Task sequence

1. Prepare a documentation-only feasibility proposal.
2. Present the scope, statistical, data, and maintenance choices to the owner.
3. Stop unless the owner explicitly approves adding this candidate to the
   numbered roadmap.

## Acceptance criteria

This candidate may enter the numbered roadmap only when the owner has approved
its product scope, historical data source, missing-data rules, classification
comparability policy, statistical specification changes, retention and
migration policy, and maintenance cost. It must not treat Phase 12's
latest-only document or Git history as an approved historical product source.

---

# Completion and change control

At task completion, keep docs/STATUS.yaml live-only. When completed task detail
exists in this roadmap, move it in the same accepted task to the corresponding
phase file under docs/history/, update the history index, and leave only the
remaining plan plus a compact history pointer here. Git and the pull request
retain ordinary validation and publication evidence.

Use `docs/DEVELOPMENT_WORKFLOW.md` for task gates, artifact impact, validation,
Owner acceptance, publication, and stop conditions. Record scope or statistical
decisions in `docs/DECISIONS.md`. Historical files never authorize work.

# Current approved action

The current approved task is defined only in `docs/STATUS.yaml`.
