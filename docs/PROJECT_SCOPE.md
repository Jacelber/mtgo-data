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

- a curated weekly Landing overview of what changed and what the current
  environment looks like;
- the current online metagame;
- archetype representation;
- high-performing archetypes;
- changes across time ranges;
- representative deck construction;
- matchup performance where reliable match data is available.

### 3.2 Supported formats

As checked against the public catalog on 2026-09-12, Standard, Modern and Pauper
are public MTGO products, each with Landing, statistics, matchups and weekly
Top 8 entries. Official event collection also retains archives for Pioneer,
Legacy and Vintage; archive collection alone does not make them public products.
Pioneer and Legacy remain planned; Vintage requires a product-scope decision.
Catalog availability is not a claim that every current UI behavior is defect-free.

The scoped formats are:

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
- a complete-week view of admitted MTGO event Top 8 decklists;
- average points per theoretical round;
- representative or average decklists;
- deck-construction deviation;
- a repository-managed Landing editorial screening, approval, known-state, and
  feature-history capability that is not a standalone user-facing product;
- matchup and win-rate statistics based on the appropriate MTGO match source;
- Unknown deck reporting;
- classification conflict reporting;
- data update date and data-quality information.

Parent archetypes are the default aggregation. Where maintained subtypes exist,
the product must support taxonomy-driven expansion without changing or
double-counting the parent result. Deck-construction comparison is based on the
most specific maintained identity: subtype-specific for a subtype-defining
parent and parent-specific only when the parent defines no subtypes.

MTGO source completeness must be visible rather than implied. The product must
show range-specific matchup-source coverage and a reviewed theoretical-versus-
observed high-score decklist completeness measure with their raw numerators,
denominators, exclusions, and unavailable states.

The existing Standard page must remain functional during refactoring.

After Phase 12 closeout, a complete public MTGO format includes an admitted
Landing product together with official statistics, matchup win rates, weekly
Top 8 decklists, and every other format-applicable required product. Its
Landing includes the approved new-deck and new-technology feature section fed
by the internal Landing editorial capability; a separate Pickup product is not
required. A future format must not become public through a partial launch that
omits Landing. Standard and Modern completed their transition from pre-Landing
products; that historical migration exception does not permit a new partial launch.

The weekly maintenance process follows [WEEKLY_MAINTENANCE](WEEKLY_MAINTENANCE.md).
Machines supply screening facts and reasons; the Owner selects features and
authors Chinese copy. Machine-written editorial suggestions require an explicit
Owner request. Human final Landing content is authoritative. The
Owner may rewrite, replace, omit, or independently author that content; machine
evidence does not define the permitted editorial conclusion. Publication and necessary repository work follow the current authorized plan
and agreed business acceptance under GOVERNANCE.

---

## 4. Product B: Tabletop Major Events

### 4.1 Purpose

Tabletop Major Events analyzes selected large-scale tabletop Constructed tournaments.

Melee may be used as the primary tournament data source, but the user-facing product name should be “Tabletop Major Events,” not simply “Melee.”

This product is event-oriented rather than time-window-oriented.

Each event should be independently inspectable.

### 4.2 Supported formats

As checked against the public event catalogs on 2026-09-12, Tabletop supports
Modern events `405590`, `441441` and the protected reference event `434455`
(default `405590`), plus Paupergeddon `438329` for Pauper. Other scoped tabletop
formats have no public event entry. New events must satisfy the approved event
policy and belong to the current authorized delivery; registration is not proof
of public availability.

The scoped tabletop formats are:

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

- Event: Pro Tour Magic: The Gathering® | Marvel Super Heroes
- Melee tournament ID: `434455`
- Constructed format: Modern
- Event structure: `mixed`
- Date range: 2026-07-17 through 2026-07-19
- Source URL: `https://melee.gg/Tournament/View/434455`

This event is used to implement and validate:

- whitelist-based collection;
- Melee raw-data preservation;
- standings collection;
- decklist collection;
- round and match collection;
- Modern classification;
- mixed Draft and Constructed event statistics;
- Day 1 and Day 2 Constructed separation;
- Draft and Draft-playoff exclusion from Constructed statistics;
- per-event overview;
- per-event matchup matrix;
- data-quality reporting.

The reference event has three Draft Swiss rounds followed by five Modern Swiss rounds on each of Day 1 and Day 2, then a Draft Top 8 playoff. The normalized model must therefore represent event stage, round phase, and game format independently. The implementation must still verify source records during collection rather than assuming that all Pro Tours follow this structure.

Pauper MTGO and Paupergeddon `438329` were publicly admitted in Phase 14. The
Modern reference event remains a compatibility subject, not the only public
Tabletop event or a prerequisite phase to repeat for later work.

---

## 9. Front-end scope

### 9.1 Navigation hierarchy

The primary analysis selector is the Constructed format.

After selecting a format, the user should be able to choose the products
available for that format:

- MTGO weekly Landing;
- MTGO official event statistics;
- MTGO matchup win rates;
- MTGO weekly Top 8 decklists;
- Tabletop Major Events.

The Landing feature section may select the current or a prior approved feature
week from the Landing-owned feature archive. That section-level control does
not create a separate product and does not change the week used by the Landing
brief, environment, or construction-change facts. Existing Pickup week files
are migration and rollback inputs, not the continuing source of new Landing
content.

Every exact deck retained in current reviewed weekly-brief copy must also be a
selected item in the applicable Landing feature week. Its link selects that
week, expands the exact item, and moves it into view. A newly reviewed
top-copy-only deck is invalid and must be corrected before generation. The
exact MTGO Top 8 destination remains only as a defensive compatibility route
for legacy documents and for Top 8 links outside reviewed Landing copy.

Feature titles are not weekly editorial inputs. They are the localized deck
name derived from the selected deck's stable format/classifier identity.
Feature order is likewise derived: each format displays new decks before new
technology, then follows exact deck links in the final top copy from row order
and left to right; features not mentioned in top copy appear last in their
category. The Owner continues to control category, positioning, representative
cards, and all top-copy prose.

The approved bilingual classifier-name catalog is also the display authority
for classifier-backed parent and subtype labels across the Chinese variants of
the Landing, every retained MTGO view, and applicable Tabletop views. English
variants continue to use the classifier taxonomy's English names. Consumers
must resolve these labels from stable format, parent, and subtype identities;
they must not infer identity by matching display text. This cross-view consumer
behavior is distinct from the private catalog and classifier maintenance;
changing display consumers does not by itself change classification rules.

Card names and complete card images remain separate from
classifier-backed archetype labels. The English source card name remains the
stable lookup and compatibility value. Existing product generation already
applies the maintained card-name aliases and card-face normalization used by
the English image path; card localization must consume those results and must
not create another conversion layer.

The implemented localization uses one flat
English-name lookup for the MTGCH Chinese display name and exact MTGCH image
URL. Current default-Landing images are the only localization images stored in
Pages. Other Chinese views load the mapped MTGCH image on demand; English views
retain the existing local Landing images and Scryfall on-demand images.
Missing Chinese data falls back to the existing English name and image.

MTGCH Chinese names and community-rendered full-card images remain inside the
approved product scope under the Owner's recorded project-specific permission
from the MTGCH founder. They must retain the required source attribution and
must not be presented as a general or transferable MTGCH license. User-
submitted, third-party, and source-unknown images remain outside scope.

Availability must come from generated catalogs rather than a hard-coded
assumption that every format supports every product.

MTGO Environment Trends and Tabletop Major Events remain clear, separately
identified source products. The format-first navigation may connect their
separate entry points and retain the selected format, but it must not merge
their data loading or statistics. The source name “Melee” may appear in event
metadata but should not be the only user-facing description of the tabletop
product.

The visible site title on both production entries is also the script-independent
home control. It links to the bare `/index.html` MTGO entry rather than a
specific product query, so it remains usable during initialization failure and
automatically follows the currently configured default MTGO product.

### 9.2 MTGO page

The existing root page remains the MTGO entry point:

`/index.html`

Retain supported Standard behavior and public URLs when changing the shared page.

The MTGO page must default hierarchical statistics and matchup axes to parent
archetypes. Eligible parents may expand into maintained subtypes individually
or through one global control. Parents with zero or one maintained subtype must
not expose a redundant expansion control. Visible subtype labels must remain
self-contained when the parent row is replaced.

Both matchup products may offer one default-off mainstream projection that
applies the same qualifying parent-family set to the row and column axes. A
parent qualifies at a stored share of at least 2%: current-range parent
high-score share for MTGO and current-scope parent metagame share for Tabletop.
These source-specific statistics must remain separately named and loaded;
neither may be presented as a cross-product or universal metagame share.
`Unknown` is not a mainstream archetype. A qualifying parent retains its full
maintained subtype disclosure, and disabling the projection restores the
complete matrix without changing source counts or a user's exact row selection.

The MTGO page should also provide a complete-week Top 8 decklist view. Selecting
a listed deck should use the same detail structure as MTGO statistics while
showing the exact event deck, its subtype-based deviation, and its subtype
average deck.

For both MTGO and Tabletop Major Events, the primary visible `胜率` is literal
valid-match win percentage: wins divided by valid wins, losses, and normal
played draws. Primary overview and overall values include mirror matches, and
the matchup diagonal displays real mirror W-L-D information. Non-mirror win
rate is supporting information. Existing published output retains its
compatibility behavior until the versioned P8-04 migration is implemented; a
browser must not reinterpret a legacy rate locally.

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

The completed page split uses static HTML, CSS and focused JavaScript assets.
The format-first shared shell keeps independent MTGO and Tabletop controllers.
Historical prototypes explain the design; they are not a permanent correctness
oracle or the current recovery version.

The production target structure remains:

- `/index.html`;
- `/melee/index.html`;
- `/assets/css/site.css`;
- `/assets/js/common.js`;
- `/assets/js/mtgo.js`;
- additional focused JavaScript modules when justified.

Changes must preserve approved behavior, supported languages, public data paths,
source separation and GitHub Pages compatibility. Retire a compatibility asset
only when its needed callers have a working replacement or its retirement is an
approved scope change; this does not require repeating P8-08/P8-09/P8-10.

Use a stable local preview when the task needs an Owner experience decision.
External design services are optional and must fit the actual authorized cost,
privacy and scope. Neither prototypes nor an extra service review are mandatory
stages for an ordinary repair. Current product recovery uses the applicable
complete archived deployment described in DELIVERY, not a frozen legacy page.

---

## 10. Classification scope

Each archetype definition must have a stable machine-readable archetype ID.

An archetype may optionally contain stable machine-readable subtype identities. A subtype describes an existing rule-level variant within one archetype; it is not a separate archetype and must not change archetype-level compatibility or aggregation.

When changing implementation without an approved taxonomy change, preserve
parent classification and stable identities. Subtype detail must not split or
double-count parent populations. The completed initial Standard migration is
historical evidence, not a continuing prohibition on approved new subtypes.
New archetypes or subtype meanings are business decisions in the task plan.

Classification rules must support:

- rule IDs;
- explicit priorities;
- deterministic evaluation;
- full-match inspection;
- conflict reporting;
- Unknown reporting;
- format-specific rule files;
- inspectable same-input classification changes against approved outcomes.

The intended rule files are:

- `my_archetypes/standard.yaml`;
- `my_archetypes/pauper.yaml`;
- `my_archetypes/modern.yaml`;
- `my_archetypes/pioneer.yaml`;
- `my_archetypes/legacy.yaml`;
- `my_archetypes/vintage.yaml`, only if Vintage is approved.

Adding a new source for an existing format should reuse the same archetype identities where possible.

Source-specific parsing differences must not require duplicate archetype identities.

Subtype presentation must retain the parent relationship without replacing,
splitting or double-counting the parent archetype.

---

## 11. Development order

Phases 0 through 9 established the authoritative specifications, Standard
regression baseline, shared classification and MTGO infrastructure, split
static front end, Modern MTGO product, approved mixed-event Modern reference
product, and reusable pure Constructed event strategies.

Phases 10 through 14 have completed. The following sequence records delivered
foundations and future product direction, not recurring technical approval stages:

1. Phase 10 — data governance, compliance, and production operations.
2. Phase 11 — engineering baseline, test structure, and documentation reduction.
3. Phase 12 — front-end productization and sharing readiness.
4. Phase 13 — compatible multi-event raw-count matchup aggregation.
5. Complete the shared card-name and card-image localization
   foundation required before Phase 14.
6. Phase 14 — Pauper MTGO and the approved Paupergeddon event.
7. Phase 15 — Pioneer.
8. Phase 16 — Legacy and Eternal Weekend.
9. Phase 17 — Standard Tabletop events when an approved event is available.
10. Phase 18 — the Vintage decision gate.
11. Phase 19 — release and long-term maintenance closeout.

ROADMAP records development order. Current Owner instructions and the confirmed
plan determine task scope under GOVERNANCE; STATUS records durable facts.

Detailed phases and acceptance criteria belong in `ROADMAP.md`.

---

## 12. Delivery quality

The product retains explicit licensing and source notices, versioned data
contracts, conflict/Unknown reporting, usable public interfaces and reproducible
operations. Validation policy belongs to [QUALITY](QUALITY.md), collaboration
to [GOVERNANCE](GOVERNANCE.md), and publication/recovery to [DELIVERY](DELIVERY.md).
This product specification does not prescribe a standing test suite or workflow gates.

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
- removing a required Standard consumer behavior without a compatible replacement;
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

Owner decides intentional scope changes under GOVERNANCE. Record the resulting
meaning here and in affected statistics/data contracts. Update roadmap or status
only when their actual facts change; obtain proportionate proof under QUALITY.

Do not make undocumented scope changes only in code.
