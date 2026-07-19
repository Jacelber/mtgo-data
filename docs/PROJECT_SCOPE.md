# Project Scope

## 1. Document purpose

This document defines the approved product scope of the `mtgo-data` repository.

It describes:

- the products being built;
- the supported data sources and formats;
- the event inclusion policy;
- the required user-facing features;
- the separation between MTGO and tabletop tournament statistics;
- the development order;
- explicit out-of-scope items.

Detailed statistical formulas are defined in `STATISTICS_SPEC.md`.

Technical directories and data structures are defined in `DATA_ARCHITECTURE.md`.

Development phases and acceptance criteria are defined in `ROADMAP.md`.

---

## 2. Product objective

The project analyzes constructed Magic: The Gathering tournament data and presents archetype-level metagame and performance statistics.

The project is focused primarily on Constructed formats.

Limited results may be collected when necessary to understand the structure of a mixed-format event, but Limited results must not be included in Constructed deck-performance statistics.

The repository will support two separate product areas:

1. **MTGO Environment Trends**
2. **Tabletop Major Events**

These products may share classification logic and reusable statistical utilities, but their event data and generated statistics must remain separate.

---

## 3. Product A: MTGO Environment Trends

### 3.1 Purpose

MTGO Environment Trends analyzes recurring Magic Online tournament results over time.

It is intended to show:

- the current online metagame;
- archetype representation;
- high-performing archetypes;
- changes across time ranges;
- representative deck construction;
- matchup performance where reliable match data is available.

### 3.2 Supported formats

The current implementation supports Standard only.

The planned supported formats are:

- Standard;
- Pauper;
- Modern;
- Pioneer;
- Legacy;
- Vintage, only if approved in a later phase.

All formats should eventually use shared classification infrastructure while keeping format-specific classification rules.

### 3.3 Required MTGO features

The MTGO product should retain or develop the following capabilities:

- format selection;
- one-week statistics;
- four-week statistics;
- twelve-week statistics;
- longer historical ranges when supported by existing data;
- archetype deck counts;
- metagame share;
- high-score counts and proportions;
- high-score conversion;
- Top 8 information where present in source events;
- average points per theoretical round;
- representative or average decklists;
- deck-construction deviation;
- Weekly Pickup;
- matchup and win-rate statistics based on the appropriate MTGO match source;
- Unknown deck reporting;
- classification conflict reporting;
- data update date and data-quality information.

The existing Standard page must remain functional during refactoring.

---

## 4. Product B: Tabletop Major Events

### 4.1 Purpose

Tabletop Major Events analyzes selected large-scale tabletop Constructed tournaments.

Melee may be used as the primary tournament data source, but the user-facing product name should be “Tabletop Major Events,” not simply “Melee.”

This product is event-oriented rather than time-window-oriented.

Each event should be independently inspectable.

### 4.2 Supported formats

The planned tabletop formats are:

- Pauper;
- Modern;
- Pioneer;
- Legacy;
- Standard when an approved event uses Standard;
- Vintage, only if approved in a later phase.

A format should use the same archetype identities and classification rules across MTGO and tabletop data whenever the deck-format rules are equivalent.

MTGO and tabletop statistics must still be generated and displayed separately.

### 4.3 Required event-page behavior

Each approved tabletop event must have its own selectable event view.

A format page should default to the latest enabled event for that format.

The tabletop product should provide at least two main views.

#### View A: Event overview

The event overview is calculated for one event only.

It may include:

- event metadata;
- valid deck count;
- Unknown deck count;
- archetype count;
- initial metagame share;
- average points per applicable theoretical Constructed round;
- overall Constructed match win rate;
- Day 1 Constructed performance;
- Day 2 Constructed performance;
- high-score representation and conversion where applicable;
- Day 2 representation and conversion where statistically applicable;
- data completeness and quality warnings;
- result-type exclusions;
- decklists and final standings as supporting information.

The exact columns depend on the event structure and are defined in `STATISTICS_SPEC.md`.

#### View B: Matchup matrix

The matchup matrix shows archetype-versus-archetype Constructed match performance.

It must support:

- one event;
- optional consolidation of multiple approved events;
- consolidation only among compatible events of the same Constructed format;
- Day 1 Constructed scope where available;
- Day 2 Constructed scope where available;
- all Constructed Swiss rounds;
- sample sizes;
- win, loss, and draw counts;
- confidence intervals or low-sample warnings.

The consolidated matrix must aggregate underlying match counts rather than averaging already-calculated event win rates.

MTGO matches must never be included in a tabletop matchup matrix.

---

## 5. MTGO and tabletop separation

MTGO and tabletop data represent different tournament environments and must not be merged into one metagame share, conversion rate, average score, or matchup statistic.

The following must remain separate:

- source data;
- normalized event data;
- event catalogs;
- generated statistics;
- front-end product sections;
- update workflows;
- quality reports;
- source-specific metadata.

The following may be shared:

- card-name normalization;
- archetype IDs;
- archetype names;
- classification rule loading;
- rule priority logic;
- classification conflict detection;
- Unknown reporting infrastructure;
- deck utility functions;
- common mathematical helpers;
- win-rate calculations;
- confidence-interval functions;
- JSON Schema validation infrastructure.

Shared code must not erase source-specific information.

---

## 6. Tabletop event inclusion policy

### 6.1 Whitelist requirement

Tabletop events must be registered manually in:

`configs/melee_events.yaml`

The presence of an event on Melee is not sufficient for collection.

The system must not automatically crawl or publish every available Melee event.

Each whitelist entry should identify at least:

- Melee tournament ID;
- source URL;
- event name;
- date or date range;
- Constructed format;
- event series;
- event structure;
- enabled or disabled status;
- relevant phases or rounds;
- notes about special handling.

### 6.2 Included official event categories

The target official event categories are:

- Magic World Championship;
- Pro Tour;
- Regional Championship;
- Magic Spotlight Series.

An event is included only when:

- it is explicitly whitelisted;
- relevant Constructed rounds can be identified;
- decklists and results are sufficiently complete;
- the target format is supported or is being added in the current phase.

### 6.3 Included non-official event categories

The approved special event categories are:

- Paupergeddon main events for Pauper;
- Eternal Weekend main events for Legacy;
- Eternal Weekend main events for Vintage, if Vintage support is approved.

Other community events require a separate scope decision before inclusion.

### 6.4 Excluded events

Exclude the following unless a later documented decision explicitly approves them:

- team events;
- pure Limited events;
- side events;
- small local events;
- preliminary events;
- qualifiers not explicitly approved;
- events without usable decklists;
- events whose Constructed rounds cannot be reliably identified;
- events outside the whitelist;
- mixed-format statistics that combine Draft and Constructed performance into one deck-performance metric.

---

## 7. Event structures

Every tabletop event must declare one of the following statistical structures.

### 7.1 Pure Constructed with Day 2

Configuration value:

`constructed_day2`

Examples may include two-day Regional Championships or Paupergeddon events with a documented Day 2 cut.

This mode may report:

- initial metagame;
- Day 1 Constructed performance;
- Day 2 participation;
- Day 2 conversion;
- Day 2 Constructed performance;
- combined Constructed Swiss performance.

### 7.2 Pure Constructed without Day 2

Configuration value:

`constructed_single_stage`

Examples may include single-stage large Constructed events.

This mode may report:

- initial metagame;
- high-score region representation;
- high-score conversion;
- average points per theoretical round;
- Constructed match win rate.

### 7.3 Mixed Draft and Constructed

Configuration value:

`mixed`

Examples include Pro Tours and World Championships.

For mixed events:

- Draft rounds must be excluded from Constructed deck-performance statistics;
- overall standings points must not be used as Constructed deck points;
- Day 2 qualification must not be presented as a pure deck conversion metric;
- Day 1 and Day 2 Constructed results must be separable;
- all Constructed Swiss results may be shown as an additional scope;
- Day 2 results must include selection-bias context;
- playoffs must remain separate from primary Swiss statistics.

---

## 8. Initial reference event

The first tabletop implementation target is:

- Event: Paupergeddon Summer 2026 Main Event
- Melee tournament ID: `438329`
- Format: Pauper
- Source URL: `https://melee.gg/Tournament/View/438329`

This event is used to implement and validate:

- whitelist-based collection;
- Melee raw-data preservation;
- standings collection;
- decklist collection;
- round and match collection;
- Pauper classification;
- pure Constructed event statistics;
- Day 1 and Day 2 handling where supported by source data;
- per-event overview;
- per-event matchup matrix;
- data-quality reporting.

The implementation must verify the event structure from collected data and configuration rather than assuming that all events follow the same structure.

---

## 9. Front-end scope

### 9.1 Top-level navigation

The product should expose two clear top-level sections:

- MTGO Environment Trends
- Tabletop Major Events

The source name “Melee” may appear in event metadata but should not be the only user-facing description of the tabletop product.

### 9.2 MTGO page

The existing root page remains the MTGO entry point:

`/index.html`

The current Standard behavior must be protected while the page is split and generalized.

### 9.3 Tabletop page

The tabletop entry point should be:

`/melee/index.html`

The page should allow users to select:

- format;
- event;
- event overview;
- matchup matrix;
- matchup scope;
- compatible events for consolidated matchup statistics.

### 9.4 Static-site requirement

The site must remain compatible with GitHub Pages.

The initial refactor should use static HTML, CSS, JavaScript, and generated JSON.

Do not introduce a mandatory front-end build system or framework unless a later decision explicitly approves it.

### 9.5 Existing page split

The current monolithic `index.html` must be split before major multi-format front-end expansion.

The initial target structure is:

- `/index.html`;
- `/melee/index.html`;
- `/assets/css/site.css`;
- `/assets/js/common.js`;
- `/assets/js/mtgo.js`;
- additional focused JavaScript modules when justified.

The split must preserve existing behavior, visual presentation, language behavior, data paths, and GitHub Pages deployment.

---

## 10. Classification scope

Each archetype definition must have a stable machine-readable archetype ID.

An archetype may optionally contain stable machine-readable subtype identities. A subtype describes an existing rule-level variant within one archetype; it is not a separate archetype and must not change archetype-level compatibility or aggregation.

During the initial shared-classifier migration:

- the selected archetype must remain identical to the approved legacy Standard result;
- only legacy rules that already produce the same archetype through distinct rule entries may become distinct subtypes;
- archetypes without an existing duplicate rule path must return no subtype;
- no new archetype or additional subtype taxonomy may be introduced until the compatibility classifier is complete and separately approved.

Classification rules must support:

- rule IDs;
- explicit priorities;
- deterministic evaluation;
- full-match inspection;
- conflict reporting;
- Unknown reporting;
- format-specific rule files;
- regression testing.

The intended rule files are:

- `my_archetypes/standard.yaml`;
- `my_archetypes/pauper.yaml`;
- `my_archetypes/modern.yaml`;
- `my_archetypes/pioneer.yaml`;
- `my_archetypes/legacy.yaml`;
- `my_archetypes/vintage.yaml`, only if Vintage is approved.

Adding a new source for an existing format should reuse the same archetype identities where possible.

Source-specific parsing differences must not require duplicate archetype identities.

Future front-end work should consider how to expose subtype information without replacing, splitting, or double-counting the parent archetype. Phase 2 does not require a subtype visual redesign.

---

## 11. Development order

Development must proceed in the following broad order:

1. Finalize authoritative project documentation.
2. Protect the existing Standard implementation with a baseline and regression tests.
3. Add engineering foundations:
   - README;
   - license and notices;
   - dependency lists;
   - pytest;
   - rule validation;
   - JSON Schemas;
   - CI;
   - safer GitHub Actions.
4. Extract and validate the shared classifier.
5. Generalize the Standard-only MTGO pipeline.
6. Split the existing MTGO front end without changing behavior.
7. Implement the whitelist-based Melee collection and normalization pipeline.
8. Implement Pauper classification.
9. Implement MTGO Pauper statistics.
10. Implement the Paupergeddon reference event.
11. Implement the tabletop event overview and matchup matrix.
12. Implement pure Constructed single-stage event handling.
13. Implement mixed Draft and Constructed event handling.
14. Implement compatible multi-event tabletop matchup aggregation.
15. Add Modern to both applicable product areas.
16. Add Pioneer to both applicable product areas.
17. Add Legacy to both applicable product areas.
18. Add Standard tabletop events when an approved event is available.
19. Decide whether to implement Vintage.
20. Complete cleanup, operational documentation, and release procedures.

Detailed phases and acceptance criteria belong in `ROADMAP.md`.

---

## 12. Engineering-quality scope

The project must add or improve:

- a concise root README;
- an explicit code license;
- data-source and data-rights notices;
- production dependency definitions;
- development dependency definitions;
- automated tests;
- classification-rule validation;
- classification conflict reports;
- Unknown classification reports;
- versioned JSON Schemas;
- generated-data validation;
- GitHub Actions with least-privilege permissions;
- workflow concurrency controls;
- workflow summaries;
- failure reporting;
- reproducible commands;
- regression checks for existing Standard output;
- documentation for non-programmer maintenance.

These requirements are part of the development plan, not optional final cleanup.

---

## 13. Out of scope

The following are outside the current approved scope:

- combining MTGO and tabletop results into one statistic;
- automatically scraping all Melee tournaments;
- supporting every Magic format immediately;
- using overall mixed-event standings points as deck-performance points;
- treating Draft results as Constructed deck results;
- using playoff results as the primary matchup sample;
- publishing unsupported events without review;
- replacing the static site with a server application;
- requiring a front-end framework or build pipeline;
- deleting legacy Standard code before regression protection exists;
- manually editing generated statistics instead of fixing their generators;
- implementing Vintage before a separate approval decision.

---

## 14. Scope-change procedure

A change affects project scope when it modifies:

- supported formats;
- supported event categories;
- source separation;
- primary statistical products;
- event inclusion policy;
- front-end product boundaries;
- development order;
- explicitly excluded functionality.

Scope changes must:

1. be confirmed explicitly;
2. be recorded in `DECISIONS.md`;
3. update this document when necessary;
4. update `STATISTICS_SPEC.md` if metrics are affected;
5. update `DATA_ARCHITECTURE.md` if paths or structures are affected;
6. update `ROADMAP.md` and `STATUS.yaml`;
7. add or update tests before implementation is considered complete.

Do not make undocumented scope changes only in code.
