# Data Architecture

## 1. Document purpose

This document defines the target code, data, configuration, output, test, front-end, and automation architecture of the `mtgo-data` repository.

It distinguishes:

- manually maintained source files;
- externally collected raw data;
- normalized event data;
- generated statistics;
- quality and classification reports;
- shared application code;
- source-specific application code;
- public front-end assets;
- temporary compatibility entry points.

This is a target architecture.

The repository may not yet contain every optional path described here. Changes
follow the current authorized plan and preserve supported product behavior;
ROADMAP supplies product direction, not a mandatory sequence of technical approvals.

Statistical behavior is defined in `STATISTICS_SPEC.md`.

Product scope is defined in `PROJECT_SCOPE.md`.

---

## 2. Architecture principles

### 2.1 Source separation

MTGO and Melee are different data sources and different product areas.

Their data must remain distinguishable at every stage:

- collection;
- raw storage;
- normalization;
- validation;
- statistics generation;
- publication;
- front-end loading;
- quality reporting.

Shared code must not remove source identity.

Every normalized event and generated statistics file must identify its source.

Recommended source IDs are:

- `mtgo`;
- `melee`.

### 2.2 Format separation

Format-specific data and rules must be separated using stable lowercase format IDs.

Approved or planned format IDs are:

- `standard`;
- `pauper`;
- `modern`;
- `pioneer`;
- `legacy`;
- `vintage`.

Display names may use capitalization, but paths and machine-readable IDs should use lowercase values.

### 2.3 Raw, normalized, and generated data

The project must distinguish three main data layers.

#### Raw data

Raw data is collected from an external source with as little transformation as practical.

Examples:

- source HTML;
- source API responses;
- source standings;
- source match rows;
- source decklist records.

Raw data exists for reproducibility and debugging.

#### Normalized data

Normalized data converts source-specific records into a stable internal model.

Examples:

- normalized players;
- normalized decks;
- normalized rounds;
- normalized matches;
- explicit result types;
- round-phase assignments;
- archetype classifications.

Statistics must use normalized data rather than parsing front-end HTML directly.

#### Generated output

Generated output is derived from normalized data.

Examples:

- event overview;
- metagame statistics;
- matchup matrix;
- average decklist;
- quality report;
- event catalog.

Generated output must not be manually edited as a substitute for changing the generator.

### 2.4 Configuration is not generated data

Manually reviewed configuration must remain separate from generated data.

Examples include:

- Melee event whitelist;
- format registry;
- event round overrides;
- result-type overrides;
- classification rules;
- display configuration.

Automation must not silently rewrite manually maintained configuration.

### 2.5 Static-site compatibility

The public site must remain compatible with GitHub Pages.

Generated JSON and static front-end assets must be readable without a running application server.

A mandatory Node.js build system or front-end framework is outside the current approved architecture unless separately approved.

### 2.6 Incremental migration

The target architecture must be introduced gradually.

During migration:

- existing Standard commands may remain available;
- root-level legacy scripts may remain as wrappers;
- existing public JSON paths may remain as compatibility outputs;
- needed legacy callers must have a working replacement before removal;
  verify the affected behavior, without requiring tests merely for a new module;
- large file moves must not be combined with statistical formula changes unless unavoidable.

---

## 3. Target repository layout

The target high-level structure is:

```text
mtgo-data/
├── .github/
│   ├── copilot-instructions.md
│   └── workflows/
│       ├── ci.yml
│       ├── update_mtgo.yml
│       └── fetch_melee.yml
├── assets/
│   ├── css/
│   │   └── site.css
│   └── js/
│       ├── common.js
│       ├── mtgo.js
│       ├── mtgo-stats.js
│       ├── matchup.js
│       └── melee-events.js
├── configs/
│   ├── formats.yaml
│   └── melee_events.yaml
├── data/
│   ├── standard/
│   ├── pauper/
│   ├── modern/
│   ├── pioneer/
│   ├── legacy/
│   └── vintage/
├── data_raw/
│   └── melee/
│       └── <event_id>/
├── docs/
│   ├── PROJECT_SCOPE.md
│   ├── STATISTICS_SPEC.md
│   ├── DATA_ARCHITECTURE.md
│   ├── ROADMAP.md
│   ├── GOVERNANCE.md
│   └── STATUS.yaml
├── melee/
│   └── index.html
├── my_archetypes/
│   ├── standard.yaml
│   ├── pauper.yaml
│   ├── modern.yaml
│   ├── pioneer.yaml
│   ├── legacy.yaml
│   └── vintage.yaml
├── reports/
│   ├── standard/
│   ├── pauper/
│   ├── modern/
│   ├── pioneer/
│   ├── legacy/
│   └── vintage/
├── schemas/
│   ├── archetype-rules.schema.json
│   ├── mtgo-event.schema.json
│   ├── melee-event.schema.json
│   ├── deck-stats.schema.json
│   ├── matchup.schema.json
│   ├── quality-report.schema.json
│   └── catalog.schema.json
├── src/
│   └── mtgmeta/
│       ├── __init__.py
│       ├── card_names.py
│       ├── classifier.py
│       ├── config.py
│       ├── deck.py
│       ├── metrics.py
│       ├── rules.py
│       ├── validation.py
│       ├── mtgo/
│       │   ├── __init__.py
│       │   ├── fetch.py
│       │   ├── normalize.py
│       │   ├── stats.py
│       │   ├── matchup.py
│       │   ├── landing.py
│       │   ├── landing_editorial.py
│       │   ├── landing_screening.py
│       │   └── metadata.py
│       └── melee/
│           ├── __init__.py
│           ├── client.py
│           ├── parser.py
│           ├── assembler.py
│           ├── normalize.py
│           ├── stats.py
│           ├── matchup.py
│           └── quality.py
├── stats/
│   ├── catalog.json
│   ├── standard/
│   ├── pauper/
│   ├── modern/
│   ├── pioneer/
│   ├── legacy/
│   └── vintage/
├── tests/
│   ├── fixtures/
│   ├── test_card_names.py
│   ├── test_classifier.py
│   ├── test_metrics.py
│   ├── test_rules.py
│   ├── test_schema_validation.py
│   ├── test_mtgo_regression.py
│   ├── test_melee_results.py
│   └── test_matchup.py
├── AGENTS.md
├── CLAUDE.md
├── LICENSE
├── NOTICE.md
├── README.md
├── index.html
├── requirements.txt
├── requirements-dev.txt
└── validate_rules.py
```

Not every optional format directory must be created before that format is implemented.

Do not create empty generated-data directories only to imitate the target tree.

---

## 4. Shared Python package

Shared reusable Python code belongs under:

```text
src/mtgmeta/
```

The shared package must not assume that all events are Standard or that all data comes from MTGO.

### 4.1 `config.py`

Responsibilities:

- load project configuration;
- validate supported format IDs;
- resolve repository-relative paths;
- load the format registry;
- load source-specific configuration;
- provide common configuration errors.

It must not contain hard-coded Standard-only paths.

### 4.2 `card_names.py`

Responsibilities:

- normalize card names;
- normalize whitespace and punctuation where approved;
- preserve original source card names;
- provide aliases only when explicitly maintained;
- detect unusable card-name records.

Card-name normalization must be shared between MTGO and Melee classification.

### 4.3 `deck.py`

Responsibilities:

- represent normalized deck cards;
- separate main deck and sideboard;
- calculate card quantities;
- convert source deck structures into classifier input;
- provide reusable deck-vector helpers where appropriate.

It must not fetch external data.

### 4.4 `rules.py`

Responsibilities:

- load format-specific YAML classification rules;
- validate rule structure;
- enforce archetype-ID uniqueness;
- enforce rule-ID uniqueness;
- validate explicit priorities;
- reject malformed conditions;
- expose normalized rule objects to the classifier.

Rule validation must not depend only on the front end.

### 4.5 `classifier.py`

Responsibilities:

- classify a normalized deck;
- evaluate all applicable rules;
- preserve every rule match;
- select the final archetype deterministically;
- use explicit priority;
- detect equal-priority or otherwise unresolved conflicts;
- return evidence for the selected match;
- return `Unknown` when no rule matches;
- produce data suitable for conflict and Unknown reports.

The classifier must not contain source-specific Melee or MTGO parsing.

### 4.6 `metrics.py`

Responsibilities:

- high-score threshold calculation;
- average points per theoretical round;
- W-L-D aggregation;
- match win-rate calculation;
- Wilson interval calculation;
- safe division;
- missing-value handling;
- reusable metagame-share and conversion helpers.

Formulas must follow `STATISTICS_SPEC.md`.

### 4.7 `validation.py`

Responsibilities:

- load JSON Schemas;
- validate normalized data;
- validate generated output;
- report file path and validation location;
- separate warnings from blocking failures;
- expose validation functions to command-line scripts and tests.

---

## 5. MTGO-specific package

MTGO-specific code belongs under:

```text
src/mtgmeta/mtgo/
```

### 5.1 `fetch.py`

Responsibilities:

- collect approved MTGO event data;
- preserve source identifiers;
- avoid refetching known events when appropriate;
- apply retries and timeouts;
- require an explicit playoff marker before deciding archive eligibility;
- require every published playoff deck to have matching Swiss standings and a
  final placement before storage;
- distinguish temporarily incomplete publication from structurally invalid
  identities or numeric fields;
- report partial failures;
- write source data through controlled paths.

Temporary semantic incompleteness enters the existing bounded retry and
two-day defer path. It produces no event file and no fetched-ledger entry.
Duplicate source player IDs, invalid collection types, or invalid rank/score
values are parser failures. Non-playoff events remain eligible for explicit
exclusion without requiring playoff-only standings and placement collections.

The explicit `refresh-event` command is the controlled repair path for an
already retained playoff event. It is not part of scheduled production
collection. The command downloads and validates the current official payload,
then requires exactly one existing archive with the same numeric event ID,
requested format, player identity set, and player-to-final-rank mapping. Only
after all invariants pass may it atomically replace that archive through a
same-directory temporary file. It does not add, remove, or rewrite a fetched
ledger entry. Any mismatch leaves the original archive byte-for-byte intact.

### 5.2 `normalize.py`

Responsibilities:

- convert MTGO event data into the normalized MTGO event model;
- normalize player and deck fields;
- preserve source score fields;
- derive or retain event metadata;
- prepare decks for the shared classifier.

### 5.3 `stats.py`

Responsibilities:

- format-parameterized MTGO statistics;
- one canonical classifier digest on every rolling-range, representative-deck,
  and statistics-catalog document generated from classified decks;
- reject retained players without a non-negative integer Swiss score or
  positive integer final rank;
- time-range aggregation;
- latest-complete-week logic;
- high-score statistics;
- Top 8 statistics;
- average decklists;
- representative decklists;
- source-backed event identity and official event name on rolling best and
  representative deck displays;
- construction deviation;
- recent change where applicable.

The generalized module must preserve existing Standard behavior unless a documented statistical change is approved.

The `stats/<format>/mtgo/decks_*w.json` representative-deck contract uses the
retained event's numeric `event_id` and official `description` as `event_name`.
These fields are display provenance, not statistics. Consumers may combine
them with the existing `player_count` and date-only projection of `starttime`;
they must not infer an event by matching date, player count, rank, or player.
The event-context deck contract was version `1.1.0`; the additive classifier
binding advances it to `1.2.0`. Existing Top 8 week and
comparison-base documents retain their own compatibility versions and do not
need event-context duplication in the expanded deck detail.

### 5.4 `matchup.py`

Responsibilities:

- process the approved MTGO matchup source;
- bind every matchup range and matchup catalog to the same canonical classifier
  digest used to classify its event decks;
- retain source coverage metadata;
- calculate format-specific matchup outputs;
- retain stable parent-archetype and selected-subtype identities for both sides
  of each eligible match;
- aggregate canonical directed W-L-D counts at the most specific selected
  identity;
- derive and validate parent-parent, subtype-parent, parent-subtype, and
  subtype-subtype rollups without averaging percentages;
- use shared W-L-D utilities;
- avoid implying full event coverage when coverage is partial.

### 5.5 Landing screening and metadata

Responsibilities:

- `landing_screening.py` owns private MTGO weekly candidate screening and
  reusable deck-selection helpers;
- `landing_editorial.py` owns the reviewed Landing source and workbook import;
- stable parent-ID tracking for every maintained format;
- known-state maintenance inside the private Landing review boundary;
- format metadata that identifies matchup source and measured archive
  coverage in `metadata.py`;
- a taxonomy-derived parent/subtype hierarchy catalog whose expandability is
  based on maintained subtype count in `metadata.py`;
- output generation for the MTGO front end.

Candidate generation is a review artifact, not a publication action. The
supported command is `landing-review prepare`; no standalone Pickup command,
capability, metadata catalog, or product renderer remains. Landing generation
does not read a published Pickup week. Standalone Pickup files remain frozen
compatibility and rollback resources and are not modified by this boundary.

The daily MTGO production workflow may generate one private weekly-maintenance
readiness artifact after a successful production result. That artifact binds
the exact publication commit, review week, format-specific event IDs and
classifier digests. Before creating that handoff, it requires the current rule
digest to match the latest Top 8 week and index, every indexed rolling-range and
representative-deck document, every indexed matchup document, and the maintained
hierarchy catalog. A missing or different binding stops the handoff rather than
allowing visual-metadata or Landing review to continue on a local overlay. Its
classification section contains the complete retained
Unknown diagnostic corpus, partitioned into unresolved records and exact
Owner-accepted intentional Unknown records, and includes each deck's complete
main deck and sideboard. It also carries classification blockers and Landing
screening candidate counts, and may report manual inputs or later producers as explicitly
unavailable. It is an Actions artifact and Issue handoff only: it is not
generated public data, does not enter `stats/catalog.json` or Pages, and does
not authorize a review or repository mutation. Its current operating contract
is `docs/WEEKLY_MAINTENANCE.md`.

`configs/mtgo_weekly_review_completions.yaml` is the maintained non-public
completion ledger. Legacy records retain their Top-8-only meaning: each format
binds the material Top 8 review digest and published Landing content digest.
Weekly V2 records instead bind the event IDs actually reviewed by the Owner,
the accepted classifier subject, one machine digest of every official weekly
classification through rank 32, and the published Landing content digest for
both formats. The ledger is not a per-rank database, source-mutation detector,
publication registry, or authorization source. A mismatch with the scope that
the record declares produces `revalidation_required`; an unchanged accepted
subject produces `completed`, and the deduplicated weekly Issue remains closed.

`configs/mtgo_intentional_unknowns.yaml` is the maintained non-public registry
for the only permitted unresolved-classification exception. Each record binds
format, event ID, stable deck ID and source file to an Owner acceptance date and
evidence pointer. The sole allowed reason code is `random_card_pile`; event age,
singleton status, sparse evidence, or a missing rule are invalid reasons. A
registry match is reported separately and never deleted from the underlying
diagnostic report.

### 5.6 `landing.py`

Responsibilities:

- select the latest closed Monday-through-Sunday week independently of whether
  that week contains an event;
- classify the current, previous, and aggregated previous-four-week
  populations once under one classifier digest;
- generate the accepted parent environment, movement, exit, and construction-
  shift facts without generated prose;
- read top copy and selected features from the same private format-scoped
  Landing review document;
- bind reviewed content to source events, classifier rules, exact deck
  destinations, and deterministic machine facts, preserving the last admitted
  document when re-review is required;
- reject every current inline `deck:<ID>` token that has no exact selected
  feature; and
- generate `stats/<format>/mtgo/landing/current.json` plus the bounded
  `landing/features/index.json` and `landing/features/<week>.json` archive from
  that one reviewed source.

The feature archive contains only the bottom new-deck and new-technology
section. Its index records admitted weeks and explicit feature counts, including
zero. Zero-feature weeks remain machine-readable archive records but are not
selectable in the Landing UI. A selected non-empty historical feature week does
not change the current Landing brief, environment, composition, or construction
facts. Every feature carries one stable exact-deck `destination_id`; localized
names and prose are display content, not navigation identities.

Private review documents and continuity state remain under
`stats/<format>/mtgo/landing/review/` and are excluded from Pages. Public feature
documents contain only materialized reviewed output and the minimum source,
week, classifier, and content bindings needed to validate the archive.

`configs/mtgo_landing_visuals.yaml` is manual product metadata. Its two-card
parent or explicit subtype selections are not classifier evidence. Missing
metadata yields a text-only environment row rather than a guessed card.

---

## 6. Melee-specific package

Melee-specific code belongs under:

```text
src/mtgmeta/melee/
```

### 6.1 `client.py`

Responsibilities:

- retrieve approved Melee pages and endpoints;
- set request timeouts;
- implement retry and delay behavior;
- paginate source tables;
- preserve response metadata;
- identify fetch failures;
- avoid unapproved broad crawling.

The client must require or verify a whitelisted event ID before collection.

### 6.2 `parser.py`

Responsibilities:

- parse source HTML and JSON responses;
- preserve source IDs;
- parse tournament metadata;
- parse standings;
- parse decklist references;
- parse round names;
- parse match result text;
- return source-level parsed records without applying final statistics.

### 6.3 `assembler.py`

Responsibilities:

- associate standings, players, decklists, rounds, and matches;
- resolve source player IDs;
- create a complete event-level intermediate model;
- preserve unresolved associations for quality reporting;
- avoid silently deleting inconsistent players or matches.

### 6.4 `normalize.py`

Responsibilities:

- convert assembled source data into the normalized Melee event model;
- assign round phases;
- assign Day 1 and Day 2;
- assign normalized result types;
- preserve raw source result text;
- calculate theoretical-round eligibility;
- apply reviewed event-specific overrides;
- prepare decks for the shared classifier.

### 6.5 `stats.py`

Responsibilities:

- apply the correct event structure:
  - `constructed_day2`;
  - `constructed_single_stage`;
  - `mixed`;
- calculate event overview statistics;
- calculate Day 1, Day 2, and Combined scopes;
- process high-score metrics;
- process Day 2 metrics;
- process drop and completion diagnostics;
- exclude Draft and playoffs from primary Constructed statistics;
- handle Top 8 lock exemptions according to configuration and evidence.

### 6.6 `matchup.py`

Responsibilities:

- generate per-event matchup matrices;
- generate supported scope variants;
- exclude disallowed result types;
- reconcile inverse matrix cells;
- combine compatible events using raw W-L-D counts;
- preserve the included event ID list.

### 6.7 `quality.py`

Responsibilities:

- verify source-record totals;
- report missing decklists;
- report Unknown archetypes;
- report classification conflicts;
- report unknown rounds;
- report unknown result types;
- report no-shows;
- report drops;
- report byes and intentional draws;
- report awarded-win handling;
- reconcile standings, players, decks, and matches;
- determine blocking and non-blocking issues.

---

## 7. Classification-rule architecture

Format-specific classification rules belong under:

```text
my_archetypes/<format>.yaml
```

Examples:

```text
my_archetypes/standard.yaml
my_archetypes/pauper.yaml
my_archetypes/modern.yaml
my_archetypes/pioneer.yaml
my_archetypes/legacy.yaml
```

Vintage rules should not be added until Vintage implementation is approved.

### 7.1 Stable identifiers

Every archetype must have:

- a stable `id`;
- a display `name`;
- an explicit `priority`;
- one or more rules;
- stable rule IDs.

An archetype may additionally define optional subtypes. Every published subtype must have:

- a stable ID unique within its parent archetype;
- a display name;
- one or more associated rule IDs;
- an explicit parent archetype ID.

A rule may select a parent archetype and an optional subtype. Subtype selection must never change which parent archetype wins compatibility classification.

Example shape:

```yaml
schema_version: "1.0.0"
format: pauper

archetypes:
  - id: example-archetype
    name: Example Archetype
    priority: 100
    rules:
      - id: example-archetype-core
        priority: 100
        subtype_id: null
        conditions:
          all:
            - card: Example Card
              min_count: 4
```

This example defines structure only. It is not an approved real archetype rule.

The initial Standard migration exposed subtypes only for distinct legacy rules
within the same parent (`4-Color Control` and `Izzet Aggro`). That historical
mapping does not limit the current approved taxonomy. Implementation-only
changes preserve parent results and stable IDs; new names or rule meanings are
business choices within the current task plan, not a repeat migration stage.

### 7.2 Identifier rules

Archetype IDs and rule IDs should:

- use lowercase ASCII;
- use hyphens between words;
- remain stable after publication;
- not contain a date unless the date is part of the true identity;
- not depend on display-language text.

### 7.3 Priority rules

Priority must be explicit.

Do not depend on YAML file order as the only conflict-resolution mechanism.

The classifier must retain all matches before selecting the final result.

Equal-priority conflicting archetype matches must be reported and must not be silently resolved by file order.

### 7.4 Classification output

A classification result should retain at least:

- archetype ID;
- archetype display name;
- optional subtype ID;
- optional subtype display name;
- selected rule ID;
- selected priority;
- all matched archetype IDs;
- all matched rule IDs;
- conflict status;
- classification status;
- relevant evidence where practical.

The parent archetype fields are the compatibility contract. Subtype fields are supplementary and may be `null`. A null subtype is normal when the selected parent defines no subtypes. Under the current Standard and Modern taxonomies, a parent that defines subtypes must select one of them for every classified deck; a later null result under such a parent is blocking under the approved no-residual policy. Reports and downstream consumers must not treat a subtype as an unrelated archetype.

Recommended classification statuses are:

- `classified`;
- `unknown`;
- `conflict`;
- `invalid_deck`.

---

## 8. Configuration architecture

Manually maintained configuration belongs under:

```text
configs/
```

### 8.1 `formats.yaml`

The format registry should identify:

- format ID;
- display name;
- MTGO raw-event collection status;
- enabled sources;
- classification-rule path;
- public availability;
- implementation status;
- relevant output paths.

The registry supplies format discovery to the front end and command-line tools;
consumers must not assume that Standard is the only executable format.

MTGO raw-event collection and product execution are separate states. `event_collection_enabled` authorizes only official event download, normalized archival storage, and fetched-ledger maintenance for that format. It does not authorize Videre fetching, classification, statistics, Landing screening or generation, catalogs, public output, or front-end exposure. Those operations continue to require the executable MTGO state and their declared capabilities.

Executable state is capability-scoped rather than equivalent to public
availability. Commands honor the capability for their network or output effect;
event archival does not imply Videre collection or public catalog exposure.

Production processing distinguishes two registry-derived sets:

- **event-collection formats** have `event_collection_enabled: true` and receive only official MTGO event archives plus fetched-ledger maintenance unless they also qualify as a complete product;
- **complete product formats** have MTGO execution enabled and declare every production capability: classification, event and range statistics, matchup statistics, weekly Top 8 generation, Landing generation, metadata generation, and catalog generation.

The registry and public catalog checked on 2026-09-12 identify Standard, Modern
and Pauper as complete public MTGO products. All six listed formats retain
event collection; Pioneer and Legacy remain planned and Vintage awaits its
scope decision. Processing selection must agree with the registry and restrict
statistics/reports to eligible products. A change to selection needs focused
proof of included and excluded formats, not a workflow test on every delivery.
A planned or raw-archive-only format cannot gain generated product output
merely by being added to the event loop. Tabletop availability is independently
listed in its event catalogs: Modern `405590`, `441441`, `434455` and Pauper
`438329`; MTGO eligibility does not admit a Tabletop event.

Videre match collection has a narrower availability boundary than official MTGO
event collection. After bounded retries, retryable HTTP, timeout, and transport
failures are retained as explicit source-unavailable warnings for their event
IDs. They create no matchup archive but do not block transfer of the remaining
candidate into generation and validation. The completeness generator derives
those absent admitted archives as `missing`, while matchup generation consumes
only usable retained archives. Non-retryable responses, malformed response
contracts, invalid identities, and storage failures remain fatal and prevent
candidate publication.

Landing screening is candidate-only in scheduled automation. It generates as
soon as a natural week ends, including while that week is provisional. The
candidate and base reference record their source event IDs. If an additive
late event changes those IDs, an unreviewed candidate is refreshed; an approved
or commented candidate is retained and reported for human re-review. Candidate
generation may continue on error so that review preparation cannot suppress
unrelated generated data, but every product format must still be attempted.
Landing business acceptance follows the agreed task under GOVERNANCE. Known state is
maintained through the private Landing review boundary.

P6-08 initially regenerated the maintained hierarchy catalog only for Modern.
P6-09 moves Standard to the same shared hierarchical calculation, adds its
maintained hierarchy catalog, and makes both Standard and Modern public MTGO
formats. The production workflow now regenerates hierarchy catalogs for both
products. Standard retains its original name-keyed matchup fields as
compatibility aliases derived from the stable-ID parent rollup; those aliases
are not a separate statistical calculation.

Format event directories may contain only documents whose embedded MTGO format matches the configured project format. Classification generation fails closed when it encounters any cross-format document. Unsupported formats must not be retained inside a supported format's data directory or represented as classification exceptions; erroneous unsupported-format archives should be removed after review.

### 8.2 `melee_events.yaml`

This file is the authoritative Melee whitelist.

Each event entry should retain at least:

- event ID;
- source URL;
- name;
- format;
- series;
- event structure;
- enabled status;
- tabletop status;
- team-event flag;
- mixed-format flag;
- included phases;
- round assignments or overrides when necessary;
- Day 2 information when applicable;
- Top 8 lock handling when applicable;
- notes.

Example shape:

```yaml
schema_version: "1.0.0"

events:
  - id: "434455"
    url: "https://melee.gg/Tournament/View/434455"
    name: "Pro Tour Magic: The Gathering | Marvel Super Heroes"
    date:
      start: "2026-07-17"
      end: "2026-07-19"
    format: "modern"
    series: "pro_tour"
    structure: "mixed"
    enabled: true
    review_status: "verified"
    tabletop: true
    team_event: false
    mixed_format: true
    include:
      swiss: true
      playoffs: true
    phases:
      - id: "day1_draft"
        stage: "day1"
        round_phase: "draft"
        game_format: "limited"
        swiss: true
        rounds: [1, 2, 3]
      - id: "day1_modern"
        stage: "day1"
        round_phase: "constructed"
        game_format: "modern"
        swiss: true
        rounds: [4, 5, 6, 7, 8]
      - id: "day2_draft"
        stage: "day2"
        round_phase: "draft"
        game_format: "limited"
        swiss: true
        rounds: [9, 10, 11]
      - id: "day2_modern"
        stage: "day2"
        round_phase: "constructed"
        game_format: "modern"
        swiss: true
        rounds: [12, 13, 14, 15, 16]
      - id: "top8_draft"
        stage: "playoff"
        round_phase: "playoff"
        game_format: "limited"
        swiss: false
        source_labels: ["Quarterfinals", "Semifinals", "Finals"]
    advancement:
      day2_after_round: 8
      day2_minimum_match_points: 12
      top8_lock_supported: true
    reviewed_overrides: []
    statistics:
      default_match_scope: "all_constructed_swiss"
      constructed_game_format: "modern"
      include_playoffs: false
    source_evidence:
      - "https://magic.gg/news/pro-tour-marvel-super-heroes-viewers-guide"
    special_handling:
      - "Draft Swiss and the Draft Top 8 are excluded from Modern statistics."
    notes: "Phase 7 reference event; manual collection is enabled"
```

This configuration does not by itself prove the exact round assignments. They must be verified during collection and normalization.

`enabled: true` makes a verified whitelist entry eligible for the bounded
collector; the actual task must authorize the collection. It does not permit
broad event discovery, recurring execution or MTGO writes. The complete live
request command requires `--execute` and `--complete` as technical effect flags,
not separate Owner approvals.

Configuration alone writes no source or generated data. Collection produces the
retained snapshot and normalized input; classification, opportunity accounting
and event statistics consume that input. These are data dependencies within the
authorized delivery, not the completed P7-01/P7-02 stage-authorization sequence.

### 8.3 Event-specific overrides

Source anomalies may require reviewed overrides.

Overrides may include:

- round-phase mapping;
- Day 1 or Day 2 assignment;
- player identity correction;
- match-result correction;
- Top 8 lock identification;
- excluded source record;
- decklist association.

Every override must include:

- target record;
- reason;
- source or evidence;
- date;
- reviewer note.

Do not embed unexplained one-event exceptions directly in generic parser code.

---

## 9. MTGO data layout

Current MTGO event data is stored under format directories such as:

```text
data/standard/
```

The compatible multi-format layout is:

```text
data/<format>/
```

Examples:

```text
data/standard/
data/pauper/
data/modern/
data/pioneer/
data/legacy/
```

A Standard path change preserves required consumer compatibility; QUALITY defines affected proof.

### 9.1 MTGO event files

MTGO event filenames should preserve a stable event identity.

Every normalized or source-preserved event record must contain or allow derivation of:

- source;
- format;
- event ID;
- event name;
- event date;
- source URL when available;
- player count;
- theoretical round count;
- deck and result records;
- fetch or generation metadata;
- schema version when normalized.

Every retained MTGO playoff event must also contain a non-empty player list
whose `loginid` values are unique and whose `swiss_rank`, `swiss_score`, and
`final_rank` values are valid integers (`swiss_score` may be zero; ranks are
positive). Production-candidate validation applies this contract to every new
or modified retained event. Existing known exceptions must be repaired from
validated source data, not hand-edited.

### 9.2 Fetch state

Legacy `fetched.txt` may remain during migration.

The target implementation should eventually use source-aware state rather than one ambiguous global list.

Any replacement must:

- preserve existing known-event history;
- distinguish MTGO from Melee;
- avoid refetch loops;
- remain inspectable;
- be introduced with a migration procedure.

Do not delete `fetched.txt` before a verified replacement exists.

---

## 10. Melee raw-data layout

Raw Melee data belongs under:

```text
data_raw/melee/<event_id>/
```

For example:

```text
data_raw/melee/434455/
```

One immutable collection snapshot uses numbered source files plus a manifest:

```text
<utc-timestamp>-<sequence>/
  manifest.json
  tournament-001.html
  standings-<round_id>-<page>.json
  matches-<round_id>-<page>.json
  decklist-<decklist_guid>.json
```

The retained event `434455` uses legacy raw manifest `2.0.0`, which records each
source response's method, URL, page, content metadata, byte count, SHA-256,
request-body SHA-256 for DataTables POSTs, and applicable source round,
participant, and decklist identity. Parsers retain read compatibility with
stored manifest `1.0.0` fixtures. Neither legacy contract is used to regenerate
the frozen reference event.

The approved successor contract uses minimized manifest `4.0.0`. Every source
response is parsed in bounded memory before persistence. The snapshot contains
canonical JSON for tournament, standings, matches, and decklists; no unfiltered
source response body is written. Each response row distinguishes transient
`source_sha256` / `source_bytes` from the minimized file's `sha256` / `bytes`,
records `persisted_content_type: json`, and copies the public Melee `Player.ID`
as the positive-decimal-string `source_participant_id`. The top-level
`participant_identity` records scheme `source-participant-id-v1` and has no key
ID or secret. The implemented HMAC v3 contract remains read-compatible but is
not authorized for another live collection.

Complete event collection begins from the exact whitelisted tournament page,
discovers completed round IDs there, paginates the public standings and match
DataTables endpoints, and follows only decklist GUIDs exposed by the primary
standings. It must remain sequential and rate-limited and must reject redirects,
cross-host or unexpected paths, changing page totals, unsafe identities, and
configured response, record, or byte limits.

Large complete events use one event-local resumable staging area:

```text
data_raw/melee/<event_id>/
  .complete-in-progress/
  .complete-in-progress.json
```

The approved checkpoint `3.0.0` records collection identity, the destination
snapshot name, scheme `source-participant-id-v1`, every completed minimized
response's allowlisted metadata and digest, and the frozen complete-plan count
and SHA-256. It may retain the direct source participant context needed by the
frozen request plan and contains no HMAC material or key ID. A resume must
verify the exact event, plan hash, existing file byte count, and SHA-256 before
fetching a missing response. Verified responses are not downloaded again.

The complete collector has separate reviewed hard ceilings of 5,000 decklists
and 10,000 responses. The ordinary manually configured raw-request client
retains its 500-response ceiling. Both collectors retain the per-response and
total-byte limits.

The staging directory has no `manifest.json` while incomplete and is not a
valid parser, retention, normalization, statistics, or publication input.
After every planned response is verified, the successor collector writes manifest
`4.0.0` and atomically renames the staging directory to the immutable snapshot
name. Progress reports expose completed response count, planned response count,
accumulated persisted bytes, and reused response count.

### 10.1 Raw-data requirements

Legacy v1/v2 raw files preserve:

- source record IDs;
- source field names;
- original result strings;
- fetch timestamp;
- requested URL or endpoint;
- pagination information;
- status or error information.

Do not replace a retained legacy source value in place. Future v4 snapshots are
new immutable minimized collections, not rewrites of a legacy snapshot. V3
HMAC snapshots remain valid historical inputs and are not rewritten.

### 10.2 Sensitive information

Do not store:

- authentication tokens;
- session cookies;
- private account information;
- unnecessary request headers containing credentials.

Only collect data required for approved public tournament analysis.
The reviewed public Melee participant ID is an approved join and provenance
field; this does not authorize any other account or profile field.

### 10.3 Raw-data retention

Raw data should be retained long enough to reproduce normalization and diagnose source changes.

For the first approved reference event, retain exactly one complete raw
snapshot in Git together with its manifest and canonical normalized event. The
snapshot must be a direct immutable child of
`data_raw/melee/<event_id>/`, must use manifest Schema `2.0.0`, and must contain
exactly the regular files named by that manifest. Each response's byte count
and SHA-256 must be verified before normalization. Repository attributes treat
`data_raw/**` as byte-preserved source evidence and explicitly unsets both text
and end-of-line conversion for those files.

Incomplete staging directories, duplicate fetch logs, credentials, cookies,
private headers, and unrelated source responses are not retained as production
snapshots. A failed complete-event collection may remain only as its
event-local checkpoint and staging directory. Safe resume requires the same
event identity and frozen request-plan hash and reuses only files whose size
and SHA-256 still match the checkpoint. Any changed, untracked, or mismatched
file fails closed. An incomplete staging directory cannot be normalized,
committed as the event snapshot, or published.

The retained event `434455` snapshot contains source-published tournament
metadata, participant names and IDs, standings, matches, and submitted
decklists required for the approved product. These third-party records remain
subject to `NOTICE.md` and are not relicensed as project code. Any later refresh
must create a separate snapshot, pass the same boundary, and receive an
explicit repository-size and production-input review before it can replace or
supplement the reference input. The maintained writer
a future approved event must use manifest `4.0.0`; it must not create a new
source-preserving v2 production snapshot or a new HMAC v3 snapshot.

Do not silently discard raw data after generating statistics.

---

## 11. Melee normalized-data layout

Normalized Melee events belong under:

```text
data/<format>/melee/events/<event_id>.json
```

Example:

```text
data/modern/melee/events/434455.json
```

A normalized event should contain logical sections for:

- metadata;
- source provenance;
- event structure;
- format;
- phases;
- rounds;
- players;
- decks;
- matches;
- classification;
- exclusions;
- normalization warnings;
- schema version.

Round identity must keep three independent dimensions:

- `stage`: `day1`, `day2`, `playoff`, or `other`;
- `round_phase`: `draft`, `constructed`, `playoff`, or `unknown`;
- `game_format`: the actual game format, such as `limited` or `modern`.

This separation is required because the initial reference event has a Draft playoff. A single `playoff` value cannot by itself prove whether the games were Limited or Constructed.

### 11.1 Player identity

Prefer stable source player IDs.

Display names alone must not be assumed unique.

If a source ID is unavailable, any generated identity must be event-scoped and documented.

### 11.2 Deck identity

Each normalized deck should be associated with:

- event ID;
- player ID;
- phase or format where relevant;
- original decklist reference;
- normalized main deck;
- normalized sideboard;
- classification result.

### 11.3 Match identity

Each normalized match should retain:

- event ID;
- round ID;
- phase;
- day;
- player IDs;
- deck IDs where available;
- source result text;
- normalized result type;
- winner or draw state;
- points assigned for statistics;
- flags for inclusion in:
  - points;
  - win rate;
  - matchup matrix;
  - theoretical rounds;
- exclusion reason where applicable.

The source result text must not be discarded.

### 11.4 Evidence-based result normalization

Stored source match records may retain explicit per-competitor outcome text and
match points in addition to competitor IDs. The parser may accept the earlier
identity-only fixture shape for compatibility, but identity-only records cannot
be promoted to played wins or losses by competitor order.

Whitelist Schema 3.0.0 adds optional `reviewed_overrides`. Each override is
event-scoped and must have review status `verified`, name one source match, declare whether it was played,
provide complete participant result records, explain the correction, and cite
at least one HTTPS source. Duplicate override IDs, duplicate match targets,
identity mismatches, malformed played-result pairs, and unsupported Top 8 lock
awards fail closed.

Whitelist Schema 3.1.0 remains read-compatible with 3.0.0 and adds the optional
event-scoped `advancement.qualified_result_type`. It is the only automatic
interpretation of Melee's overloaded `Qualified` match status beyond the legacy
reviewed Top 8 lock case, and its closed values are `bye` and
`awarded_win_top8_lock`. The latter still requires
`top8_lock_supported: true`. A 3.0.0 registry cannot carry the new field, so
existing admitted events retain their prior result meaning.

The normalizer resolves phase, stage, actual game format, participant status,
result type, points, and eligibility. Only internally consistent played results
in a reviewed Constructed Swiss phase of the event's configured format are
eligible for primary Constructed and matchup statistics. Draft, playoff, bye,
intentional-draw, no-show, drop, administrative, awarded, and unknown records
remain in normalized context but are ineligible. P5-06 output remains explicitly
non-publishable until it passes the separate quality and publication boundary.

Participant status `disqualified` remains distinct from an ordinary drop. All
source records for that participant remain normalized, but every match involving
them is excluded as a complete match unit from Constructed win-rate and matchup
eligibility. The match evidence records the exclusion reason, and the quality
gate emits one non-blocking participant-level warning.

### 11.5 Quality and publication boundary

Normalized Melee event Schema 2.2.0 retains read compatibility with the
committed 2.1.0 synthetic contract and adds snapshot-qualified raw provenance
for production input. It also tightens the relationship among played
results, statistical eligibility, blocking issues, quality status, and the
`publishable` flag. The P5-07 quality gate deep-copies its input, validates the
complete document against that Schema both before and after assessment, and
checks reviewed event metadata, provenance digests, identity uniqueness,
cross-record references, round-to-phase agreement, result semantics, and
Constructed Swiss eligibility.

The gate is fail-closed. A publication payload can be built only when the event
is explicitly enabled and verified, no blocking issue remains, and at least one
verified played match belongs to the configured Constructed Swiss scope. Unknown
semantics, mismatched or dangling identities, malformed eligibility, missing
primary standings, missing raw-artifact integrity evidence, and Schema failures
block publication.

Missing or unavailable decklists are retained as deterministic non-blocking
warnings because matches can remain trustworthy without complete decklists. No
numeric decklist-coverage or sample-size threshold is introduced; those values
remain governed by OPEN-002. The publication boundary returns canonical UTF-8
JSON bytes and performs no file write, network request, classification, or
statistical generation. Repeating it with the same logical input therefore
produces identical bytes and SHA-256 values.

### 11.6 Canonical normalized-event retention

P7-02 converts one complete, verified snapshot into
`data/<format>/melee/events/<event_id>.json`. The command validates the raw
manifest and exact file set, parses and normalizes every response, applies the
existing Schema and semantic quality gate, then performs one atomic write.
Production provenance includes the immutable snapshot directory in every raw
artifact path.

The source snapshot's `fetched_at` is also the deterministic normalization
epoch. Rebuilding from the same snapshot must therefore produce identical
bytes and SHA-256. If the canonical path already contains different bytes, the
command fails for review instead of overwriting it. This retention step does
not classify decks, generate statistics, publish a public catalog, dispatch a
workflow, or modify either front end.

### 11.7 Deterministic classification overlay

P7-03 keeps canonical normalized input immutable and stores derived
classification separately at:

```text
data/<format>/melee/classifications/<event_id>.json
```

The overlay joins to the normalized event by `participant_id`. It contains one
record for every submitted decklist in the event's Constructed format and
retains the selected parent archetype, optional subtype, selected rule and
priority, every matched rule with condition evidence, top-priority matches,
overridden matches, conflict evidence, and sanitized errors. An Unknown record
also carries normalized main-deck and sideboard evidence so taxonomy gaps can
be reviewed without scanning unrelated event records.

The file header records the normalized-event path, byte-level SHA-256, Schema
version and decklist counts, plus the shared taxonomy path, byte-level SHA-256,
rule Schema version, and maintained parent, rule, and subtype counts. It uses
no wall clock or Git-history value. Repeating classification with identical
input and rules must therefore produce byte-identical UTF-8 JSON.

Strict classification blocks downstream use when any unresolved conflict,
invalid deck, or null subtype under a parent with maintained subtypes exists.
Unknown classifications remain visible and non-blocking. A null subtype under
a parent with no maintained subtypes remains a normal non-expandable parent
classification. Classification describes the submitted deck and therefore
includes a disqualified participant's retained decklist; P7-04 and later
statistics remain responsible for excluding disqualified match records.

The Melee adapter only converts source card sections into the shared
`main_deck` and `sideboard` shape. It does not contain source-specific
archetype rules. The normalized event, raw snapshot, shared Modern taxonomy,
MTGO products, workflows, and front ends remain unchanged by this overlay.

### 11.8 Deterministic Constructed-opportunity ledger

P7-04 introduced the mixed-event ledger. P9-03 generalizes its construction
through the normalized event's explicit `event_structure`, while keeping the
same path:

```text
data/<format>/melee/opportunities/<event_id>.json
```

The ledger hashes both the canonical normalized event and its classification
overlay. It joins classification by stable `participant_id` and emits one row
for every scheduled Constructed Swiss opportunity in the structure's declared
population:

- `mixed` and `constructed_day2` expose `day1`, `day2`, and
  `all_constructed`;
- `constructed_single_stage` exposes only `all_constructed`;
- pure structures reject Draft rounds, and every structure excludes playoffs.

Mixed and pure Day 2 events record the starting field and an independently
evidenced Day 2 population. A single-stage event records every starter without
inventing Day 1, Day 2, or a cut population.

The classification overlay continues to contain only submitted decklists in
the event's Constructed format. The ledger covers the larger participant set:
participants whose normalized decklist is explicitly `missing` or
`unavailable` receive a ledger classification status of `unavailable` with no
archetype or subtype identity. Any other mismatch between submitted decklists
and classification records fails closed. This preserves participant and match
facts without fabricating an Unknown classification.

Each opportunity preserves the source match and official match points when
present, while independently recording:

- whether the point result contributes to Constructed point totals;
- theoretical and effective theoretical-round inclusion;
- win-rate inclusion;
- matchup inclusion;
- explicit exclusion reasons.

Ordinary missing rounds for a participant whose source status is `dropped`
become zero-point `drop_unplayed` opportunities. A missing round for any
participant whose source status is `no_show` becomes a zero-point `no_show`
opportunity: Melee defines that status as terminal for later pairing, while the
ledger preserves it separately from a voluntary or staff-recorded drop. The
synthesized rows attribute later unplayed opportunities to that terminal cause;
they do not claim a new no-show incident in every round. A missing round for
any non-terminal status fails closed instead of being guessed. Mixed-event Day 2
membership is established from actual Day 2 Swiss participation, including
Draft evidence. Pure Day 2 membership uses actual Day 2 Constructed Swiss
participation. A qualified participant who later drops retains the scheduled
qualified-field opportunities; non-qualifiers receive none.

A verified `awarded_win_top8_lock` retains its source result but contributes
zero Constructed points and no effective theoretical round. Matches involving
a disqualified participant retain both sides and official point context but
remain symmetrically excluded from win-rate and matchup use. The participant's
later missing rounds remain explicit administrative opportunities rather than
being mislabeled as an ordinary drop.

The file contains no wall-clock or Git-derived value. Identical event and
classification bytes must rebuild byte-identically. P9-03 preserves the
committed mixed-event ledger bytes while adding the two pure strategies. It
does not create overview, deck, matchup, or other public statistics; later
Phase 9 tasks consume the generalized ledger.

### 11.9 Deterministic per-event overview and deck statistics

P7-05 consumes four immutable inputs: the normalized event, classification
overlay, opportunity ledger, and maintained format taxonomy. The generated
documents record the repository-relative path, Schema version, and exact
SHA-256 value of every input. A digest or identity mismatch fails before any
output write.

The deterministic candidates are:

```text
stats/<format>/melee/events/<event_id>/overview.json
stats/<format>/melee/events/<event_id>/decks.json
stats/<format>/melee/events/<event_id>/quality.json
```

`overview.json` aggregates parent archetypes and their maintained subtype
children. `decks.json` preserves one participant-keyed audit record with
classification, decklist, official standing context, eligibility, and the
same structure-declared statistical scopes. P9-04 dispatches those two
documents as follows:

- `mixed` keeps `day1`, `day2`, and `all_constructed`, including the existing
  mixed-event selection-bias warning and stage high-score metrics;
- `constructed_day2` keeps the same three scopes, removes the mixed-event
  warning, makes high-score metrics unavailable, and reports
  `day2_conversion` for the Day 2 field and each parent/subtype identity;
- `constructed_single_stage` emits only `all_constructed` and calculates its
  high-score population and `high_score_conversion` from each participant's
  effective theoretical rounds.

Statistics Schema `1.1.0` keeps the complete participant count in every scope,
uses only classified plus explicit Unknown submitted decks as the
metagame-share denominator, and reports unavailable decklists separately.
Event-level points and result facts remain in the opportunity totals. The
matchup document retains its compatible `1.0.0` matrix contract, adds the
optional `decklist_unavailable` exclusion count, and admits a physical match
only when both competitors have deck identities.

Pure-event documents declare their primary `advancement_metric`. Their deck
records mark overall standings points as Constructed-only context, while the
mixed document retains the existing non-Constructed-context flag. Existing
draw-adjusted record fields remain compatibility data and their nested
`literal_record` remains the target wins-over-valid-matches statistic.

`quality.json` reconciles source, classification, ledger, exclusions, and
applicable stage populations without copying the full source archive. P9-05
generalizes the complete three-document path and CLI to all structures.
Mixed and pure Day 2 quality reports conserve Day 1 plus Day 2 against the
combined scope. Single-stage quality reports validate one exact
`all_constructed` scope and omit the inapplicable `day2_participants` count.
Only mixed events receive the Draft-influenced Day 2 selection-bias issue.
Clean quality remains `ready`; warning-bearing quality remains `warning`.

Parent rows remain the default aggregation. Only parents observed in the event
are emitted, plus the explicit Unknown bucket. For each observed
subtype-defining parent, all maintained subtypes are emitted, including empty
states, and their additive fields must conserve the parent exactly. A
subtype-defining parent with an unassigned classified deck blocks generation
under the no-residual rule.

P9-04 extends the compatible `1.0.0` overview and decks Schemas without
changing the retained mixed document shape. P9-05 compatibly extends the
quality Schema to the same three structures. Structure conditionals require
the exact scope set, the pure-event advancement metric, the pure Day 2
conversion field, and the correct overall-points context flag. The committed
mixed event `434455` remains the byte-stability oracle for overview, decks,
and quality.

The generator has a read-only default and an explicit `--execute` write path.
It does not contact Melee or MTGO, modify any retained input, or write a
catalog. P7-06 adds `matchup.json`; P7-07 owns `meta.json`, the format event
catalog, manifest/public packaging, and workflow integration. Phase 8 owns
front-end presentation.

### 11.10 Deterministic per-event hierarchical matchup statistics

P7-06 reuses the P7-05 input validation boundary and reads the same normalized
event, classification overlay, opportunity ledger, and maintained taxonomy.
It verifies the opportunity-ledger digest again immediately before
aggregation, then writes only:

```text
stats/<format>/melee/events/<event_id>/matchup.json
```

The document carries the same four-path provenance object as the P7-05
outputs. It contains no wall-clock, checkout, branch, or Git-history value and
must rebuild byte-identically from unchanged inputs.

The hierarchy is taken from the rebuilt P7-05 all-Constructed overview: its
ordered parent nodes, all maintained subtype leaves, non-subtype parent
leaves, and Unknown become a complete stable event matrix domain. The
leaf-level matrix is canonical. The parent matrix is a deterministic
row-and-column rollup of the leaf counts. P9-05 dispatches the matchup scope
set from the validated event structure:

- `mixed` and `constructed_day2` contain `day1`, `day2`, and
  `all_constructed`;
- `constructed_single_stage` contains only `all_constructed`.

Each emitted scope contains:

- included round numbers and physical-match reconciliation;
- reviewed exclusion counts;
- ordered parent and leaf identities;
- complete parent and leaf matrices, including zero cells;
- non-mirror overall parent and leaf records;
- raw W-L-D counts, derived rates, and 95% Wilson intervals.

The overview and opportunity ledger must declare the same structure and exact
ordered scope set. A mismatch fails before aggregation. Pure structures do not
inherit the mixed Day 2 selection-bias warning. The compatible matchup Schema
uses structure conditionals to prohibit fictional stage scopes.

The command is read-only unless `--execute` is supplied. It does not fetch a
source, modify retained data, change taxonomy, write MTGO output, or publish a
catalog. Public discovery, manifest governance, `meta.json`, and workflow
integration remain separate publication responsibilities.

### 11.11 Deterministic event publication packaging

The event metadata producer currently reconstructs the selected event statistics
and compares their bytes so that descriptors bind the intended derived documents.
This is the producer's selected-event consistency operation, not a standing
regression suite or a request to rerun completed work for each task stage. It writes only:

```text
stats/<format>/melee/events/<event_id>/meta.json
stats/<format>/melee/index.json
```

`meta.json` binds overview, decks, matchup, and quality by relative path,
Schema version, byte size, and SHA-256. It also carries the shared immutable
input provenance, scopes, default scope, and reviewed quality issue codes.
`index.json` is the format-level discovery boundary and points to the five
event documents. Neither document contains wall-clock or Git-derived state.

P9-05 makes both documents structure-aware. They advertise the exact scope
order rebuilt in the event overview and reject a whitelist structure that
does not match it. A clean internal quality status of `ready` is represented
as the public catalog status `pass`; `warning` is preserved. This translation
keeps generator terminology separate from the public discovery contract
without changing any retained mixed-event bytes. The compatible meta and
catalog Schemas accept all three structures and require only
`all_constructed` for a single-stage event.

P13-02 advances future format catalogs to Schema `1.1.0`. Every `1.1.0`
event entry contains a versioned `matchup_compatibility` block binding the
Melee/Tabletop identity, Constructed format, `all_constructed` scope, matchup
Schema and SHA-256, taxonomy Schema and SHA-256, and non-blocking quality.
Catalog Schema `1.0.0` remains valid for historical single-event discovery but
is ineligible for multi-event admission because it lacks that compatibility
information. Current catalogs use `1.2.0` as described below; changes use the
maintained producer rather than manually editing generated JSON.

P13-07 advances future multi-event-eligible catalogs to Schema `1.2.0` and
adds a required top-level `active_taxonomy` block containing its own Schema
version plus the current format taxonomy Schema and SHA-256. The maintained
publisher derives the block from the same taxonomy input used for the
deterministic event rebuild. Every selected event's `matchup_compatibility`
taxonomy identity must equal the catalog active identity. Catalog `1.1.0`
remains Schema-valid historical evidence but is no longer multi-event
eligible; this prevents two mutually equal stale event projections from
authorizing one another.

When the maintained classifier changes, a later authorized event publication
must regenerate the derived event cohort before those events regain multi-
event eligibility. Raw and normalized inputs remain immutable. A stale event
is rejected as selected rather than silently omitted, and no consumer may
downgrade the active taxonomy to recover compatibility.

The overview, decks, matchup, quality, meta, and catalog documents are all
declared in `schemas/manifest.json`. The source-specific candidate validator
allows only the selected event's immutable new raw snapshot, normalized
Melee-derived inputs, event statistics, and format catalog. It rejects
deletions, retained-raw mutation, another event, another format, and every
MTGO path.

The manual Melee workflow is separate from `update.yml`. It starts only through
`workflow_dispatch`. Before source resolution it resumes an existing
`data/melee-<event_id>` review branch when present and merges the dispatch's
exact `master` commit without rebasing or force-pushing. An event with canonical
normalized input on either that branch or `master` reuses the exact immutable
snapshot recorded by that input; only a new event without canonical input
performs a complete live fetch. Immediately after successful retention, the
workflow commits and verifies a branch checkpoint containing only the event's
raw snapshot and canonical normalized event. Derived classification,
opportunity, statistics, and catalog work begins after that checkpoint, so a
later-stage failure cannot discard the source evidence or require recollection.
The workflow pushes changed data only to `data/melee-<event_id>` for later
review. It cannot push
`master`, create a pull request, merge, or run on a schedule. These are boundaries
of the collection workflow; Codex completes the same authorized delivery's PR,
merge and publication through the delivery path without another stage approval.

P10-12 resolves the Constructed format before any candidate baseline, retained
snapshot lookup, or live request. It loads the authoritative whitelist through
the strict registry parser and requires the selected event to be both enabled
and verified. The resulting format becomes the workflow's sole `FORMAT` value
for all data paths, classification rules, statistics, publication, and staged
candidate paths. A missing, disabled, unverified, malformed, or unsupported
entry fails before source access and has no fallback format. Manual dispatch,
review-branch publication and source boundaries are preserved.

### 11.12 Reference-event compatibility manifest

The W35 derived-data closure migration updates the version `1.8.0`
compatibility boundary for mixed Melee event `434455` in
`tests/fixtures/melee/434455_compatibility_manifest.json`. Its exact-byte set
contains the raw snapshot manifest, normalized event, classification overlay,
opportunity ledger, and five event-specific public documents. The raw manifest
is a closure root: validation also verifies the unique path, byte count, and
SHA-256 of every one of its 483 declared responses and rejects any undeclared
file in the retained snapshot directory.

Version `1.8.0` keeps the raw snapshot manifest and normalized event
byte-identical while rebinding the classification overlay, opportunity ledger,
and five event documents to the Owner-accepted W35 Modern taxonomy. All 362
submitted decks remain classified with zero Unknown, conflicts, or invalid
records. Relative to `1.7.0`, exactly two event `434455` decks leave the former
Affinity result: one becomes `mono-blue-artifact` and one becomes
`sewer-combo/azorius`. Opportunity totals, scope populations, and result facts
remain unchanged. The rebuilt `434455` opportunity ledger advances from its
stale `1.0.0` output to the already maintained `1.1.0` missing-decklist-aware
Schema without adding a new field or statistical meaning. The maintained
hierarchy and matchup matrices expand to the new taxonomy. No source response
is fetched or rewritten.

The same deterministic migration rebuilds event `441441` from its retained
normalized event. Its 574 participants consist of 564 classified submitted
decks, seven Owner-reviewed Unknown submitted decks, and three unavailable
decklists represented only in the opportunity ledger. Both events' metadata
and matchup compatibility now bind to one active Modern taxonomy; their source
data and statistics remain separate.

The format event catalog and global consumer catalog are expandable indexes,
not immutable event payloads. Their complete bytes are excluded from the
compatibility digest set. Validation instead freezes the complete selected
`434455` event entry in `stats/modern/melee/index.json` and the Modern
`tabletop-major-events` product route in `stats/catalog.json`. Unrelated event,
format, product, default-selection, ordering, and volatile generation metadata
may change when their own tasks authorize that work, provided the selected
projection remains unchanged. The `1.8.0` selected projection uses catalog
schema `1.2.0`, binds its root to the active taxonomy, and freezes the event's
matchup compatibility evidence so later multi-event growth fails closed on a
taxonomy mismatch.

Shared whitelist and taxonomy files are not exact-byte members of the event
manifest. Protected `434455` derived bytes and their embedded provenance remain
the compatibility result. Any deliberate exact-byte change requires a new
manifest version, replacement evidence, a decision record, and separate owner
approval. Future privacy snapshot versions must not regenerate the retained v2
reference snapshot.

### 11.13 Future-event participant and field minimization

The current collection contract uses minimized resource document `2.0.0`, complete snapshot manifest
`4.0.0`, and checkpoint `3.0.0` in the implemented collection contract.
Each admitted participant context copies the public Melee `Player.ID` exactly as
positive-decimal-string `source_participant_id`. The value is an opaque source
identifier: it may be shared across Melee events, but the project does not
guarantee global or permanent upstream stability.

The source ID remains available in approved raw and normalized Git records for
joins and provenance. Generated products continue using the existing
event-scoped derived `participant_id`; this contract adds no raw source-ID field to a
Pages artifact or front-end response. Because public Git is the durable archive,
the source ID remains publicly accessible and potentially cross-event linkable
even when the Pages artifact omits it.

The field-minimization boundary is unchanged. The collector parses each bounded
response in memory and persists only exact resource allowlists. Source-published
display name, event, standing, match, and decklist fields remain separately
approved; unused account, profile, preference, duplicate identity, credential,
cookie, and private-header fields remain prohibited.

Legacy v1/v2 and completed HMAC v3 snapshots remain read-compatible and need no
secret for downstream parsing or generation. The protected `434455` v2 bytes
and derived compatibility result are not migrated. The successor writer has no
HMAC creation, key storage, key ID, rotation, injection, or recovery lifecycle.
The implemented v4 writer is the current collection path; do not reintroduce
HMAC creation for new collections. Existing supported snapshots remain readable
under their own versions without replaying a writer-acceptance stage.

### 11.14 Minimized-resource validation and privacy requests

P10-04 established `schemas/melee-minimized-resource.schema.json` as the primary
contract for minimized tournament, standings, matches, and decklist documents.
The successor `2.0.0` Schema must retain strict resource-specific object shapes,
reject additional properties at every persisted level, constrain event, round,
decklist, URL, and positive-decimal source-participant formats, and apply both
before canonical serialization and after a persisted resource is read.
Generation, resume, parsing, assembly, and retention therefore continue sharing
the same fail-closed resource boundary.

A minimized decklist response contains zero or one decklist. Zero is valid only
when the live parser has verified that Melee returned both an empty `Records`
array and an empty `Components` array for the requested decklist identity. The
empty resource is persisted as `decklists: []`; normalization then retains the
standing and reference while assigning the participant's decklist status
`unavailable`. A nonempty response with no recognized cards is
still rejected as a source-compatibility error.

An exact-key recursive scan supplements the Schema for source identity,
account, profile, preference, and unused deck metadata keys identified by the
P10-01/P10-03 audits. The scan is called only for one decoded minimized
resource. It does not scan string values, documentation, source responses,
the repository as a whole, or immutable v1/v2 snapshots. The Schema remains
the authoritative allowlist; the scan is defense against a future contract
change accidentally admitting a previously rejected source key.

`NOTICE.md` publishes `djacerror@gmail.com` as the project contact and defines
the information needed for correction or removal review. Current content
correction, upstream-source requests, and Git-history rewriting are distinct
operations with different scope. A product correction does not silently expand
into Git-history rewriting or removal of source records.

### 11.15 Public history and removal scope

Public Git history, current Pages content, other clones, forks and third-party
caches are distinct copies. A branch force-push cannot update GitHub-managed
pull-request refs or external copies. History-only rewriting does not remove
current exposure while the same paths remain served. Removing approved raw
paths changes the retained-data and compatibility boundary and requires the
corresponding explicit business/privacy decision. Product rollback cannot undo
past disclosure. Historical restoration observations are evidence for their
original objects, not a standing instruction to perform another history rewrite.

### 11.16 Source retention and deployable-package storage

The public product repository retains the already approved source evidence,
normalized inputs, generated data, reviewed configuration and code. Field
minimization controls which new source fields enter public Git; a private
recovery repository does not retroactively make those retained records private.
GitHub Pages serves an explicitly selected static package, independently of the
repository root. Temporary workflow artifacts can transfer inputs or candidates
but are not the sole durable recovery store. Complete deployment packages and
private candidates use the GitHub-only archive described in DELIVERY.
No new source retention, raw-path removal or history rewrite is implied.

### 11.17 Allowlisted Pages artifact implementation

P10-07 implements the selected A+ publication boundary without changing the
public Git archive. `configs/pages_publication.json` admits the two static entry
points, the fetched ledger, and the `assets/`, `data/`, `data_raw/`, `melee/`,
`reports/`, and `stats/` product trees. Before P12-15F it excludes private
Pickup candidate, comparison-base, and known-state files while retaining
approved Pickup history and `landing/current.json`. The P12-15F boundary also
excludes `landing/review/` while admitting `landing/features/`.
`build_pages_artifact.py` copies those
paths into a new external directory, generates an empty `.nojekyll`, rejects
unsafe paths and symbolic links, verifies every copied byte, enforces the
one-gibibyte site ceiling, and validates the complete event `434455`
compatibility closure before producing a size and digest report.

P14-02A makes `stats/` and `reports/` conditional format trees rather than
unconditional recursive grants. Their format child must be registered and
public, with executable MTGO capabilities and every required MTGO product.
The source `stats/catalog.json` must agree with the registry-derived catalog
before packaging; it is the sole global exception to the format-tree filter.
Private and unregistered format outputs are excluded even when an explicit
site-file entry names them. Existing review exclusions, approved raw archives,
and the event `434455` compatibility closure remain intact. Format registry,
catalog admission code, and pinned runtime dependencies are Pages inputs.

Cache-A adds one generated Pages overlay at `assets/card-cache/v1/`. The
overlay is built outside the repository and is never a Git-tracked input. Its
Schema-governed manifest binds the exact rolling Landing subject, every
declared image path, byte count, SHA-256, source, and feature-week use. The
Pages packager accepts the overlay only after independently recomputing the
subject and verifying a closed, symlink-free bundle; its bytes count toward
both the 64-MiB overlay ceiling and the existing one-gibibyte site ceiling.
Repository representative JPEGs may be referenced by the manifest but are not
duplicated into the overlay.

The policy is a publication boundary, not a confidentiality claim. Python
source, tests, internal governance documents, and development configuration
remain available through public Git but are not site payloads. New approved
product data enters selected product trees only within approved scope and
with applicable result verification; a new repository path outside those trees cannot
become a Pages path merely because it was committed.

Content-affecting resource preparation occurs before the candidate is finalized.
The deployment and recovery paths consume that package without source access,
classification or regeneration. Current supported operations and runtime
credentials are defined in DELIVERY, not in historical workflow descriptions.
The original Pages baseline is historical evidence only; neither legacy Pages
source settings nor old governance are a recovery mechanism.

---

## 12. Statistics-output layout

The public statistics root is:

```text
stats/
```

A global format-first consumer catalog is generated at:

```text
stats/catalog.json
```

The catalog allows the front end to discover:

- whether each approved product is available for each known format;
- the first available product for format-switch fallback;
- the public metadata or product-catalog path;
- planned and decision-gated formats without inventing an empty product.

The catalog is generated from the format registry and actual published product
catalogs. It does not make a non-public format available merely because raw
event archives exist.

### 12.1 MTGO output

Target MTGO output belongs under:

```text
stats/<format>/mtgo/
```

Examples:

```text
stats/standard/mtgo/
stats/pauper/mtgo/
```

Possible files include:

```text
index.json
1w.json
4w.json
12w.json
36w.json
matchup.json
top8_decks.json
weekly_pickup.json
```

Actual available files should be listed in `index.json` or `stats/catalog.json`.

During migration, existing Standard output paths may remain as compatibility files until the front end uses the new catalog.

Do not remove a public path without a compatibility or migration plan.

Hierarchical matchup output must describe:

- stable parent-archetype nodes and display names;
- stable subtype nodes and their parent IDs;
- whether a parent is expandable under the maintained taxonomy;
- canonical directed W-L-D counts at the most specific selected identity;
- enough source, period, coverage, and exclusion metadata to reproduce the
  fully collapsed parent matrix.

The stored hierarchy must support independent row-axis and column-axis rollups.
It must not materialize a different authoritative statistic for every possible
front-end expansion state. Parent and subtype rates are calculated from the
applicable supplied W-L-D counts. A parent with no subtype definitions and a
parent with exactly one subtype are non-expandable presentation nodes.

Do not create an implicit residual subtype. If a classified deck has a null
subtype under a parent that defines subtypes, generation stops with a visible
quality failure. OPEN-005 resolved this representation question by requiring
generation to stop rather than synthesizing, omitting, or reassigning a subtype.

The format-level hierarchy catalog is independent of the currently observed
time window. It contains the complete maintained taxonomy, stable parent and
composite subtype IDs, display names, subtype membership, and a taxonomy-based
`expandable` flag. A parent is expandable only when it defines at least two
subtypes. Matchup documents and the hierarchy catalog must be generated from
the same shared hierarchy function and reconcile exactly.

MTGO format metadata references the statistics, matchup, and hierarchy
catalogs. It records the approved matchup source and exact event/archive
coverage counts within the explicitly approved event set, including approved
official events without stored archives. Orphan/unapproved archives remain
retained but are excluded from public metadata coverage. Pickup publication is always
represented as a null compatibility-catalog reference. Feature-history
availability comes from the Landing feature
index; an explicitly reviewed empty week is represented in that index rather
than by inventing or omitting a review result.

Beginning with P6-09, Standard and Modern matchup documents use this same
hierarchical contract. The front end reads canonical leaf W-L-D counts and
derives the selected parent/subtype axis view. Standard's legacy
`archetype_order`, `overall`, and `matrix` fields remain temporary compatible
aliases generated from `parent_order`, `parent_overall`, and `parent_matrix`.

MTGO rolling-range and deck-construction documents use a parallel additive
hierarchy:

- each range, representative-deck, and statistics-catalog document records the
  canonical classifier digest that produced its identities;
- every range document keeps its existing parent rows and nests `subtypes`
  only beneath an observed parent that defines maintained subtypes;
- every nested range row carries the stable subtype ID, parent ID, display
  name, direct counts, direct rates, parent share, and subtype-specific
  construction deviation;
- every decks document keeps its existing parent entry and nests the complete
  maintained subtype list with subtype-specific best-deck and average-deck
  payloads;
- subtype construction bases are calculated independently from each subtype's
  own four-week records and never reuse or proportionally split the parent
  base;
- maintained zero-observation subtypes remain explicit so a future front end
  can distinguish taxonomy from current volume;
- parent-only projections remain compatible with the Phase 6 outputs.

The range and decks files remain source-separated MTGO products. They do not
consume Melee records, and Phase 7's Modern Pro Tour pipeline must not write to
or aggregate into them. The existing production statistics command regenerates
the additive hierarchy for every MTGO format that has range-statistics
capability; no second subtype-only workflow or public path is introduced.

P8-05 adds a dedicated weekly Top 8 product generated from admitted MTGO
events. Its public files are:

- `stats/<format>/mtgo/top8/index.json`, validated by
  `schemas/mtgo-top8-index.schema.json`;
- `stats/<format>/mtgo/top8/YYYY-Www.json`, validated by
  `schemas/mtgo-top8-week.schema.json`.
- `stats/<format>/mtgo/top8/YYYY-Www-bases.json`, validated by
  `schemas/mtgo-top8-comparison-bases.schema.json`.

The `weekly_top8` capability gates generation independently for each format.
The metadata document exposes `top8_catalog` only when the catalog exists, and
the production workflow regenerates Top 8 after range and matchup statistics
and before metadata.

Each weekly document includes:

- complete-week and event identity;
- event date and finishing position;
- stable parent and subtype identity;
- a stable self-contained subtype display label;
- an exact decklist reference or explicit missing-deck state;
- a same-week subtype or parent construction-base reference governed by the
  same provisional/sealed lifecycle;
- exact-deck deviation and card differences when that base has sufficient
  samples, or an explicit unavailable state otherwise.

P8-07 establishes 2026-W30 as the first historical baseline. A newly complete
Monday-through-Sunday week remains provisional for seven days. Within that
window, the producer may add late-discovered events; the next Monday seals event
membership. At every lifecycle state, prior event IDs, dates, ranks, players,
player counts, exact main decks, exact sideboards, and missing-deck states are
immutable source facts.

Top 8 identities, comparison bases, average decks, deviation values, and card
differences are derived artifacts. The producer rebuilds every indexed week
and companion base under the current classifier, stores one common
`classifier_digest` in every week, base, and index, and rejects a mixed-digest
closure. The digest covers the explicit classifier engine version, normalized
rule values, and the bound semantic-feature manifest. An Unknown result is a
valid explicit derived identity; conflicts and invalid decks remain blocking.
Same source facts plus the same digest rebuild week and base bytes
deterministically. A digest change may alter derived values but never relaxes
source-fact or sealed-membership checks. The de-identified
`classification_impact` section in the existing index records identity and
comparison-base changes for review and is not a pass condition; it introduces
no new public path. The index records `status`, `provisional_through`, and
`seal_on` for every week.

Phase 8 may also extend MTGO metadata or range documents with approved
completeness payloads. Matchup completeness must retain the expected/admitted,
available, missing, and excluded event counts for the selected interval.
High-score decklist completeness must retain the reviewed theoretical and
observed counts, unsupported-event states, and formula version. The browser
must not infer either denominator from presentation rows.

### 12.1.1 Phase 8 consumer-contract freeze

These are the semantic consumer requirements established in Phase 8. Retained
legacy fields preserve their declared meaning until a versioned migration;
no front end may reinterpret a legacy percentage as a new statistic.

The target public contract requires:

- all-match W-L-D counts, valid-match count, literal all-match win rate, and
  confidence interval for every overview identity and matchup cell;
- an explicit non-mirror W-L-D record and non-mirror rate as supporting output;
- real diagonal mirror records under the same matrix contract as other cells;
- generated self-contained subtype display labels and stable detail identities;
- generated catalog availability and public paths for the format/product shell;
- range-specific Videre coverage with named observed and expected/admitted
  event counts, deferred/missing/excluded counts, rate or unavailable state,
  and formula version;
- high-score decklist completeness with named observed and theoretical counts,
  reviewed eligibility/exclusions, rate or unavailable state, and formula
  version;
- complete-week MTGO Top 8 event/rank/exact-deck records plus subtype-base
  provenance or an explicit missing-deck state; and
- direct Tabletop event/per-scope overall summaries, event structure, supported
  scopes, quality context, and compatible multi-event matchup counts.

Field names, Schema versions, compatibility aliases, producer paths and rounding
must agree between a changed producer and its consumers. Verify affected
relationships when changing that contract, retaining meaningful compatibility
examples. The completed P8 task sequence imposes no prerequisite audit, producer
stage approval or repeat consumer regression on current work.

### 12.1.2 P8-04 versioned target contract

`schemas/phase8-public-contract.schema.json` is the executable `1.0.0` target
contract for the P8-03 consumers. Its representative document is
`tests/fixtures/phase8_public_contract.json`, retained as business migration
evidence. Current public results must satisfy the applicable data relationships;
QUALITY defines when and how to check them, without reviving historical test schedules.

The contract covers:

- literal all-match and non-mirror W-L-D records with an explicit
  `wins_over_valid_matches` method;
- range-specific Videre available, deferred, missing, and excluded events;
- event-level and range-level modeled high-score decklist completeness;
- self-contained parent/subtype identities and stable detail references;
- complete-week MTGO Top 8 events with exactly eight explicit placements;
- direct Tabletop event structure, supported scopes, per-scope summaries, and
  matchup compatibility.

This Schema is intentionally not mapped in `schemas/manifest.json`: it validates
the migration target, not any current public file. P8-04 left the 52 existing
manifest mappings unchanged. P8-05 introduces compatible product-specific Top
8 Schemas and four mapped Standard/Modern documents, bringing the production
manifest to 56 documents.

P8-06 adds a capability-gated completeness product:

```text
stats/<format>/mtgo/completeness/index.json
stats/<format>/mtgo/completeness/1w.json
stats/<format>/mtgo/completeness/4w.json
stats/<format>/mtgo/completeness/12w.json
stats/<format>/mtgo/completeness/36w.json
```

`schemas/mtgo-completeness-index.schema.json` validates discovery and
`schemas/mtgo-completeness-range.schema.json` reuses the frozen P8-04
completeness definitions. Standard and Modern contribute ten mapped documents,
bringing the production manifest to 66 documents. MTGO metadata exposes
`completeness_catalog`, while the previous format-global `matchup_coverage`
block remains a compatibility diagnostic.

The MTGO matchup documents remain on their existing paths. P8-06 adds a
`literal_record` beside every legacy matrix cell and adds
`parent_match_records` and `leaf_match_records` for all-match and non-mirror
identity totals. The old draw-adjusted fields remain compatibility aliases;
the browser selects the new records only by their explicit
`wins_over_valid_matches` method.

The Tabletop overview and hierarchical matchup documents follow the same
additive migration: legacy draw-adjusted records remain, while every target
record includes a nested `literal_record`. MTGO range, deck, hierarchy,
matchup, and Tabletop overview/matchup subtype nodes expose `display_name`, so
browser code never reconstructs a full subtype label.

The scheduled producer order is event and match collection, range statistics,
matchup statistics, completeness, Top 8, Landing screening, latest Landing,
hierarchy, metadata, the global consumer catalog, and diagnostics. Candidate
validation admits only the reviewed completeness documents, Top 8 week/base
names, latest-only Landing document, and `stats/catalog.json`; arbitrary
generated paths remain blocked.
Affected consumers must read the candidate's actual identities, counts,
percentages and dates. Use the result and mechanism checks selected under
QUALITY; packaging alone does not trigger consumer suites or a Chromium baseline.

### 12.2 Melee output

Target Melee output belongs under:

```text
stats/<format>/melee/
```

The format-level event catalog is:

```text
stats/<format>/melee/index.json
```

Per-event output belongs under:

```text
stats/<format>/melee/events/<event_id>/
```

Recommended files are:

```text
meta.json
overview.json
decks.json
matchup.json
quality.json
```

Example:

```text
stats/modern/melee/events/434455/meta.json
stats/modern/melee/events/434455/overview.json
stats/modern/melee/events/434455/decks.json
stats/modern/melee/events/434455/matchup.json
stats/modern/melee/events/434455/quality.json
```

P7-05 and P7-06 directly Schema-validate `overview.json`, `decks.json`,
`quality.json`, and `matchup.json` for event `434455`. These are deterministic
event-output candidates but are not yet discoverable through a public catalog
or governed by the public-output manifest. P7-07 owns that publication
boundary.

### 12.3 Multi-event matchup output

A Phase 13 multi-event matrix is generated dynamically in memory under
`schemas/melee-multi-event-matchup.schema.json` version `1.0.0`. Its inputs
are validated per-event matchup and metadata documents plus the active
version `1.2.0` format catalog. The result retains:

- Melee source, Tabletop product, Constructed format, and
  `all_constructed` scope;
- sorted included event IDs and aligned names;
- each input's catalog-relative metadata and matchup paths, matchup Schema and
  SHA-256, and taxonomy Schema and SHA-256;
- catalog, compatibility-block, and active-taxonomy Schema versions;
- the stable hierarchy, raw W-L-D counts, parent roll-up, rates, intervals,
  low-sample state, and contributing event IDs; and
- source, included, excluded, and directed-observation reconciliation.

The result is not a declared generated public output in P13-02, so it has no
manifest mapping, generated path, or generation timestamp. If a later task
writes it as an artifact, that task must separately define its path, manifest
mapping, deterministic identity, timestamp policy, producer, consumer, and
migration behavior.

Do not identify a multi-event output only by an unstable display name.

A deterministic key or a sorted event-ID list should be used.

---

## 13. Reports layout

Human-review and machine-readable reports belong under:

```text
reports/<format>/
```

Source-specific subdirectories may be used:

```text
reports/<format>/mtgo/
reports/<format>/melee/
```

Recommended reports include:

```text
classification_conflicts.json
unknown_decks.json
rule_validation.json
schema_validation.json
data_quality.json
```

Event-specific reports may use:

```text
reports/<format>/melee/<event_id>/
```

### 13.1 Conflict reports

A classification conflict report should retain:

- source;
- format;
- event ID;
- player or deck ID;
- matched archetypes;
- matched rules;
- priorities;
- relevant evidence;
- selected result, if deterministic;
- blocking status.

An unresolved equal-priority conflict should fail strict validation.

### 13.2 Unknown reports

An Unknown report should retain enough deck evidence to improve rules without requiring manual inspection of unrelated files.

It should not expose secrets or private data.

### 13.3 Generated-report rule

Reports are generated outputs.

Do not manually edit them to make validation pass.

Fix:

- the source parser;
- normalized data;
- configuration;
- classification rules;
- or validation logic.

Then regenerate the report.

---

## 14. JSON Schema architecture

JSON Schemas belong under:

```text
schemas/
```

Initial target schemas are:

```text
schemas/archetype-rules.schema.json
schemas/mtgo-event.schema.json
schemas/melee-event.schema.json
schemas/deck-stats.schema.json
schemas/matchup.schema.json
schemas/quality-report.schema.json
schemas/catalog.schema.json
```

Additional schemas may be added when they represent a stable, separately validated contract.

### 14.1 Schema version

Normalized and generated JSON must contain:

```json
{
  "schema_version": "1.0.0"
}
```

The exact version may change before first implementation, but all files governed by a schema must use an explicit version.

### 14.2 Version changes

Use a new major schema version when a change breaks existing consumers.

Examples:

- removing required fields;
- renaming public fields;
- changing field meaning;
- changing an object into an array;
- changing rate units.

Use a compatible minor or patch change when adding optional fields or clarifying validation without breaking existing readers.

### 14.3 Rate representation

Store rates as decimal fractions.

Example:

```json
{
  "win_rate": 0.534
}
```

This represents `53.4%`.

Do not mix decimal fractions and percentage values in the same field across outputs.

### 14.4 Required provenance

Published generated files should identify enough provenance to reproduce them.

Recommended fields include:

- source;
- format;
- event IDs or date range;
- generated timestamp;
- generator version or Git commit when practical;
- schema version;
- input references;
- warnings.

---

## 15. Front-end architecture

### 15.1 Entry points

The MTGO entry point remains:

```text
/index.html
```

The tabletop entry point is:

```text
/melee/index.html
```

The visible analysis hierarchy is format-first. A shared shell retains the
selected format while routing to the products available for that format:

- MTGO weekly Landing;
- MTGO official event statistics;
- MTGO matchup win rates;
- MTGO weekly Top 8 decklists;
- Tabletop Major Events.

After the P12-15F cutover, approved feature content comes from the Landing-owned
feature archive, not a separately routed product or a public Pickup handoff.
Legacy Pickup URLs remain compatibility inputs as defined in section 25.5.

The shell must obtain product availability and public paths from generated
catalogs. Routing between entry points must not combine MTGO and tabletop
payloads, caches, or statistical state.

### 15.2 Shared assets

Shared front-end assets belong under:

```text
/assets/
```

Initial target files are:

```text
assets/css/site.css
assets/js/common.js
assets/js/mtgo.js
assets/js/melee-events.js
assets/js/matchup.js
```

Additional files should be introduced by responsibility rather than creating one new monolithic file.

### 15.3 `common.js`

Responsibilities may include:

- shared fetch helpers;
- safe JSON loading;
- shared formatting;
- date formatting;
- percentage formatting;
- error messages;
- format-first and product navigation;
- shared language utilities where appropriate.

It must not contain all MTGO and Melee product logic.

### 15.4 `mtgo.js`

Responsibilities may include:

- MTGO page initialization;
- format selection;
- time-range selection;
- MTGO catalog loading;
- coordination of MTGO-specific components.

### 15.5 `melee-events.js`

Responsibilities may include:

- tabletop format selection;
- event selection;
- latest-event default;
- overview loading;
- Day 1, Day 2, and Combined scope controls;
- quality-warning display.

### 15.6 `matchup.js`

Responsibilities may include:

- matchup table rendering;
- W-L-D display;
- scope switching;
- confidence intervals;
- low-sample styling;
- compatible multi-event selection;
- default collapsed parent-archetype rows and columns;
- independent expansion and collapse of one parent on either axis;
- a global control that expands or collapses all eligible parents;
- suppression of subtype controls for parents with zero or one defined
  subtype;
- calculation of interactive rollups only from explicitly supplied canonical
  W-L-D counts.

Shared rendering code may be reused, but MTGO and tabletop data must not be combined.

The optional mainstream matchup projection uses one shared parent-ID
eligibility interface with separate source adapters. The MTGO adapter does not
add a document or an initial-page request: on first activation it reads and
caches the existing range-statistics document for the active matchup interval,
then supplies parent `high_score_share` values. The Tabletop adapter supplies
parent `metagame_share` values from the already loaded active-scope Overview.
Neither adapter may substitute matchup volume, consume the other source, or
persist a derived public document.

The projection passes qualifying parent IDs to shared matchup rendering. It
filters both visible axes by parent family after preserving the exact row
selection and disclosure state, and a qualifying parent's maintained subtype
nodes remain available through the existing hierarchy. Missing or failed share
loading leaves the complete matrix active and exposes a retryable UI state. No
Schema, catalog, public path, generated artifact, or source cache boundary is
added.

### 15.7 No statistical formulas only in UI

Primary statistical values come from the defined statistical producers; the UI does not invent parallel formulas.

The front end may format values and combine explicitly supplied counts for approved interactive views, but a statistical rule must not exist only as undocumented JavaScript.

When rollup logic changes, use independently calculable counts to verify the
affected parent/subtype projection and its consumer. Unchanged rollup evidence
remains reusable. JavaScript may select and sum the approved canonical
count cells for an interaction, but it must not infer classification, invent a
subtype, average percentages, or define a different eligibility rule.

Under the literal-rate contract, a visible `Win Rate` / `胜率` is calculated from the
supplied all-match W-L-D record as `W / (W + L + D)`. The browser may format it
or roll up supplied canonical counts; the versioned producer defines the meaning
and retains the existing compatibility fields until their approved migration.

### 15.8 Hierarchical statistics and deck-detail presentation

All hierarchical statistics default to parent archetypes. A maintained parent
with at least two subtypes may expand; a parent with zero or one subtype is a
non-expandable presentation node. Matchup axes expand independently, and one
global control may expand or collapse all eligible parents.

A subtype must have a stable self-contained public display label, such as
`Grixis Prowess`, in addition to its stable subtype ID and parent membership.
Presentation code must not rename classifier identities or guess a label from
color words. The generated label's field and compatibility meaning must agree
between producer and consumer.

The shared producer composes this label from maintained taxonomy names rather
than a color-name dictionary. If a parent name begins with the exact name of
one of its maintained subtypes, that subtype name is the replaceable base
prefix: the selected subtype name is joined to the remaining parent suffix.
For example, `Rakdos Hollow One` plus subtype `Mardu` becomes
`Mardu Hollow One`, and `Dimir Tempo` plus subtype `Dimir Red Splash` becomes
`Dimir Red Splash Tempo`. Otherwise the producer retains the existing
`<subtype> <parent>` composition. Stable parent IDs, subtype IDs, maintained
taxonomy names, and classification results do not change.

Deck-construction details use the most specific maintained identity:

- selecting an expandable parent expands its subtypes and does not display an
  averaged cross-subtype deck;
- selecting a subtype displays the subtype's independently generated
  representative, average, deviation, and recent-change data;
- selecting a parent with no maintained subtypes may display its existing
  parent-level detail;
- a weekly Top 8 selection displays the exact event deck while reusing the same
  detail component and subtype comparison base.

### 15.9 Design and data compatibility

The shared shell uses catalog-driven availability and separate MTGO and Tabletop
controllers. Retain both public entry paths and the approved data meanings when
changing UI or producers. A changed payload must reach its actual consumer with
the needed fields, labels, missing states and compatible identities intact.
Inspect that affected result; do not repeat the completed Phase 8 audit,
prototype, backend, page-switch and all-product acceptance sequence.

Historical prototypes and legacy assets explain compatibility needs. They are
not a permanent byte-equality oracle or a frozen rollback target. Current
recovery restores the applicable complete archived product under DELIVERY.

Local HTML/CSS/JavaScript prototypes are the default design method. An external
generative design service is not part of the required architecture and may be
used within the task's authorization under GOVERNANCE, with the actual design
need, cost, transmitted context and data minimization considered. Its output is advisory and does not
replace repository specifications, tests, or owner acceptance.

### 15.10 Shareable URL state

The two established entry paths remain `/index.html` and
`/melee/index.html`. P12-02 extends their query state without changing those
paths or any runtime JSON request path.

Both surfaces use `format`, `product`, and `lang`. The active product may add:

- `range`, `sort`, and `dir` for range and table-order state;
- `week` for a selected weekly MTGO document;
- `event`, `view`, and `scope` for Tabletop Major Events; and
- `detail` for a stable archetype, subtype, or exact-deck identity.

Values must be validated against the active catalog and loaded product
document. Unsupported or stale values fall back to the product default and are
removed when an extended URL is canonicalized. User changes to durable state
create browser-history entries. Reload and `popstate` restore the same supported
state without changing statistical meaning or combining product caches.

The parameter `events` is reserved for Phase 13 as sorted, unique event IDs
joined by commas. P12-02 does not read or write that parameter. Transient
expanded row or column sets, hover state, chart pins, and Landing feature expansion
remain outside the URL. A stable subtype `detail` may derive the minimum parent
expansion needed to reveal that detail; the derived expansion itself is not
serialized.

---

## 16. Verification responsibility

[QUALITY](QUALITY.md) defines necessary results, finite core mechanisms and
valid result reuse. Historical fixtures do not trigger checks merely by existing.
Data schemas define shape; they do not independently prove counts, business
meaning, actual resource rendering or authorization.

## 17. Command-line entry points

During migration, existing root scripts may remain available.

Target commands should become format-parameterized and source-explicit.

Illustrative command shapes are:

```text
python -m mtgmeta.mtgo.fetch --format pauper
python -m mtgmeta.mtgo.stats --format pauper
python -m mtgmeta.melee.client --event-id 434455
python -m mtgmeta.melee.stats --event-id 434455
```

These command shapes are architectural examples, not confirmation that the modules already provide executable command-line interfaces.

Supported commands are documented in README or entry help; necessary callers must reach their replacement before an old command is removed.

### 17.1 Retired compatibility wrappers

P11-12 removed the temporary root compatibility wrappers after the installed
package commands, package APIs, workflows, tests, and current README commands
were verified. Supported MTGO operations now use `mtgo-data-mtgo --root .
--format <id> <command>` or the equivalent `python -m mtgmeta.mtgo` form.
Shared helpers are imported from `mtgmeta`. Frozen Standard classification
corpora describe their historical subject; they are not a current aggregate quality gate.

Historical audits and the Phase 3 inventory continue to name the former files
as evidence of the migration. Their presence in those records does not make
them current executable entry points. The parent commit and P11-12 pull-request
diff are the rollback source for every removed file.

---

## 18. Dependency architecture

Production dependencies belong in:

```text
requirements.txt
```

Development and test dependencies belong in:

```text
requirements-dev.txt
```

`requirements-dev.txt` should include:

```text
-r requirements.txt
```

Dependencies should be introduced only when used.

Expected categories include:

- HTTP requests;
- YAML parsing;
- HTML parsing;
- JSON Schema validation.

Development dependencies include:

- pytest;
- related test tools when justified.

Do not rely on undeclared packages installed only on one developer’s machine.

---

## 19. Source operations and delivery separation

MTGO's existing daily schedule remains 09:00 UTC. Melee operations remain
explicitly event-scoped. Fetch, generation and product publication are different
side effects; completed input is reused. Source-specific inputs and derived
products remain separate. There is only one supported Pages writer.
Operational commands, credentials, candidate handoff and recovery live in
[DELIVERY](DELIVERY.md); workflow runtime state does not authorize new work.

### MTGO source-response meaning

Each requested monthly listing is observed three times and the observations
are unioned with recorded links. A link does not become invalid merely because
MTGO later removes it from an older listing: completed links remain skipped and
unfinished links remain directly retryable from the discovery ledger.

An MTGO event-page response is accepted only when its final origin and path
still identify the requested event and its embedded payload satisfies the
existing complete event contract. A redirect away from that event path or a
response without the embedded decklist marker is a transient source-delivery
failure. The first request keeps the ordinary cache behavior; later attempts in
the existing five-attempt loop request cache revalidation. A still-incomplete
event inside the publication grace period remains deferred. Outside that grace
period it blocks the current operation but enters the existing three-round
bounded source-recovery path; a persistently incomplete event still blocks
build and publication. This recovery retains no response body or cookie,
expands no URL scope, and changes no request count, timeout, recovery delay, or
checkpoint contract.

An incomplete input checkpoint is recovery material, not a complete generated
candidate. It cannot be represented as successfully collected input. Recovery
reuses completed operations whose inputs and collection plan still apply;
unrelated commit changes alone do not invalidate collection. Discovery ledgers
retain observed links and processed, retained, excluded or deferred states.

Source data, generated candidates and private review materials retain their
separate visibility policies. Ordinary summaries and failure notices contain
controlled stage/context and run links, not raw responses, cookies or secrets.

## 20. File naming and identifier conventions

### 20.1 Paths

Repository paths should:

- use lowercase names where practical;
- use forward-slash form in documentation;
- avoid spaces;
- avoid source ambiguity.

Windows developers may use PowerShell paths such as:

```text
.\docs\DATA_ARCHITECTURE.md
```

Repository documentation should use platform-neutral paths such as:

```text
docs/DATA_ARCHITECTURE.md
```

### 20.2 Dates and times

Use:

- ISO 8601 dates: `2026-07-11`;
- UTC timestamps for generated metadata;
- explicit timezone indicators.

Example:

```text
2026-07-16T04:00:00Z
```

Do not store an ambiguous generated time without timezone information.

### 20.3 Event IDs

Source event IDs must be stored as strings when serialized if the source may use values outside assumptions about integer range or formatting.

Recommended example:

```json
{
  "source": "melee",
  "event_id": "434455"
}
```

### 20.4 Stable keys

Use stable machine-readable IDs for:

- format;
- source;
- event;
- archetype;
- rule;
- round;
- player;
- deck;
- match.

Display names must not be the only relational key.

---

## 21. Generated versus manually maintained files

### 21.1 Manually maintained files

Examples:

- `AGENTS.md`;
- files under `docs/`;
- files under `configs/`;
- files under `my_archetypes/`;
- source code;
- tests;
- JSON Schemas;
- front-end source files;
- workflow definitions.

### 21.2 Externally collected files

Examples:

- MTGO event source data;
- Melee raw HTML;
- Melee raw API or table responses.

These are not manually authored but should remain source-preserving.

### 21.3 Generated files

Examples:

- files under `stats/`;
- classification reports;
- quality reports;
- normalized event files produced by a repeatable pipeline;
- generated catalogs.

Generated files should include provenance when practical.

### 21.4 Editing rule

If a generated file is incorrect:

1. identify the source, configuration, normalization, classification, or generator error;
2. fix the responsible input or code;
3. rerun the generator;
4. validate the regenerated result.

Do not manually patch only the generated JSON and leave the generator incorrect.

---

## 22. Compatibility meaning

Preserve required Standard and other existing product behavior unless an explicit
business change is approved. Public URLs have real consumers: a path change needs
a compatible replacement or coordinated consumer migration. Legacy paths may
exit after their required callers have moved; their existence alone does not
freeze old code, snapshots or governance. QUALITY determines affected proof.
DELIVERY restores complete deployable products without reverting governance.
Scope, verification and Owner decisions follow GOVERNANCE rather than separate
phase-specific controls.

## 23. Data flow

### 23.1 MTGO data flow

The target MTGO flow is:

```text
MTGO source
  → MTGO fetch
  → MTGO source/event data
  → MTGO normalization
  → shared classification
  → MTGO statistics and matchup generation
  → schema validation
  → stats/<format>/mtgo/
  → MTGO front end
```

### 23.2 Melee data flow

The target Melee flow is:

```text
configs/melee_events.yaml
  → whitelist verification
  → Melee client
  → data_raw/melee/<event_id>/
  → parser and assembler
  → Melee normalization
  → data/<format>/melee/events/<event_id>.json
  → shared classification
  → event statistics and matchup generation
  → quality and schema validation
  → stats/<format>/melee/events/<event_id>/
  → Tabletop Major Events front end
```

### 23.3 Multi-event matchup flow

```text
compatible normalized Melee events
  → validate per-event meta and matchup Schemas
  → admit same-format event IDs through catalog 1.1 compatibility evidence
  → reconcile matchup and taxonomy versions and SHA-256 values
  → select all_constructed
  → aggregate raw W-L-D counts
  → calculate rates and intervals
  → validate the versioned in-memory result
  → render consolidated matrix
```

MTGO records do not enter this flow.
Catalog `1.0.0` remains a valid single-event discovery input but stops at the
multi-event admission boundary. A missing event, missing compatibility block,
digest mismatch, blocking quality state, unsupported Schema, or identity
mismatch fails closed before the result is exposed to a consumer.

---

## 24. Contract changes

Changes to public paths, source separation, normalized shape, identifiers,
schemas, package boundaries or consumer contracts must keep their actual
producers and consumers compatible. Record changed meaning in this specification
and obtain any necessary Owner decision under GOVERNANCE. Implement and verify
only affected behavior under QUALITY. A file move does not itself create an
additional approval or full regression requirement.

## 25. MTGO Landing contract

### 25.1 Public product and history boundary

Landing is a format-scoped MTGO product with product ID `mtgo-landing`. Its
public editorial documents are:

```text
stats/<format>/mtgo/landing/current.json
stats/<format>/mtgo/landing/features/index.json
stats/<format>/mtgo/landing/features/<week>.json
```

Landing may also carry `data_files`, binding its range, high-score completeness,
environment decks and four-week comparison decks to
`landing/weeks/<week>/{range,completeness,environment_decks,feature_decks}.json`.
These files are generated from the admitted events and the same classifier as
that Landing week. Rolling updates must not replace these dependencies with
the latest rolling range. The consumer rejects a wrong week, format or
classifier; legacy Landing documents without the binding retain their existing
period-match fallback. The optional binding is an additive schema revision.
Week snapshots contain public derived data only, never editorial review files.

The documents are versioned and discovered through `stats/catalog.json`.
`current.json` remains the only complete latest Landing document. The feature
index and week documents are a bounded archive of the bottom new-deck and
new-technology section, not a public historical Landing contract. Selecting a
prior feature week does not replace or reinterpret the current Landing brief,
environment, composition, or construction-change facts.

The explicit Landing URL remains:

```text
/index.html?format=<format>&product=mtgo-landing&lang=<zh|en>
```

Landing is the current default for public MTGO formats in the catalog. The bare
entry follows that catalog default; explicit product URLs remain usable. A new
default experience is an Owner choice in the task plan, not a replay of P12-16.

### 25.2 Responsibility separation

The public document combines three validated sources without merging their
authority:

- deterministic machine facts contain weeks, populations, raw counts, shares,
  deltas, construction scores, stable identities, source event IDs, and the
  classifier rule digest;
- fixed Chinese and English interface templates remain front-end i18n assets
  and are not generated prose;
- approved editorial fields originate in the format-scoped private Landing
  review path and remain human-authored localized alternatives.

Machine facts and machine drafts are aids, not editorial authority. The Owner
may accept, edit, delete, replace, or ignore them; may write content unrelated
to a machine conclusion; and may choose to publish no editorial copy. A source
or digest binding detects a stale review baseline but does not claim that human
copy is logically derived from, limited by, or endorsed by the machine facts.

Only one active language is rendered. Pending candidates, reviewer notes,
design files, and non-public configuration do not enter the Pages artifact.

### 25.3 Required public-document structure

The P12-10 Schema must require, at minimum:

- `schema_version`, `product`, and `format`;
- current-week ID, start, and end dates;
- document state `ready` or `no_events`;
- sorted unique `source_event_ids` and a common classifier rule digest;
- current, previous-week, and previous-four-week population descriptors;
- a comparison-availability value and explicit unavailable reason;
- the fixed `0.03` environment threshold;
- environment rows with stable parent identity, display name, three-period
  high-score counts, denominators and shares, current Top 8 supporting values,
  and zero or two manually selected key-card identities;
- separate `other_classified` and `unknown` aggregates;
- zero to five structured `share_move`, `exit`, or `build_shift`
  observations with the evidence required by `STATISTICS_SPEC.md` section 24;
- zero or more approved `new_deck` or `new_technology` feature items with exact
  deck identity, a format-scoped classifier identity, a catalog-derived
  localized title, Owner-reviewed localized positioning, supporting facts,
  and four reviewer-selected cards; and
- enough source and review binding to detect a late-event fact change without
  silently reusing stale editorial content.

`new_entry` and `notable` are not public fields. New decks come only from
approved Landing feature items. A known-archetype return is a `share_move`
state.

### 25.4 Manual representative cards

Environment-list key cards are manually maintained product metadata keyed by
stable parent or subtype identity and kept outside classifier rule files and
generated statistics. The format-scoped source is maintained under `configs/`
for the approved classifier identities described in section 25.7.

An explicit subtype pair takes priority. Parent cards may be used only when the
configuration explicitly permits parent fallback. If neither is available,
the row remains readable and text-only; the generator must not guess. A
configured card absent from every current related deck creates a review
diagnostic rather than an automatic replacement. An image request failure
uses a dimensionally stable placeholder while retaining the card name.

Representative-card selections are Owner-reviewed product metadata, not values
to infer from the classification rules or arbitrary current program output.

### 25.5 Landing editorial screening and feature history

Landing owns one format-scoped screening, review, and publication boundary. The
useful candidate logic previously grouped under Weekly Pickup is migrated into
that boundary; a public Pickup publication is not an intermediate source for
Landing.

The screening producer examines only exact ranks one through eight and
preserves the complete Top 8 population before route-specific representative
selection. `configs/mtgo_pickup_policy.yaml` remains the maintained path for screening thresholds,
strategic-identity continuity aliases, official release dates, and frozen
new-to-Magic manifests. Renaming that path must update its actual callers and
preserve the policy meaning, without reopening P12-15D. Pending future manifests fail closed for the new-card
route rather than being inferred from a set code.

Candidate evidence records every route that selected one exact event-deck. It
may include share populations, active release and card-package facts,
known-state continuity evidence, or the comparable four-week construction
base. Reason tags merge only when the same exact deck satisfies several routes.
Different exact decks remain separate. The Owner may reject all machine
candidates or add any other exact Top 8 deck.

The private review source is:

```text
stats/<format>/mtgo/landing/review/<week>.yaml
stats/<format>/mtgo/landing/review/known_archetypes.json
```

The format-scoped bilingual classifier-name catalog and private validators are:

```text
configs/mtgo_archetype_names.yaml
schemas/mtgo-archetype-names.schema.json
schemas/mtgo-landing-review.schema.json
```

The catalog is repository-managed but not a public Pages path. Its English
display is derived from the current parent/subtype taxonomy and its Chinese
display is the Owner-approved value imported from the review carrier. The
catalog and every `landing/review/` path are excluded from the Pages artifact.

Landing feature documents may serialize catalog-derived localized titles. The
format-scoped public bilingual name contract is generated from the private
catalog for other retained views. Retained MTGO and applicable Tabletop consumers resolve parent and
subtype labels from stable IDs through that contract. They do not use display
text as identity, and the public contract does not change classifier rules or
statistical meaning.

The public contract path is shared by the separate MTGO and Tabletop consumers
for the same Constructed format:

```text
stats/<format>/archetype_names.json
```

It contains only stable parent/subtype identity and approved English/Chinese
display values. `Unknown` remains interface vocabulary rather than a maintained
classifier identity. The normal `generate-hierarchy` production step validates
the complete private catalog and regenerates this contract for each maintained
format; missing, stale, unapproved, or duplicate coverage blocks generation.

Pages admission explicitly excludes `landing/review/`. The week document binds
the format, review week, source event IDs, classifier digest,
screening-policy digest, machine-fact digest, complete Top 8 link catalog,
candidate evidence, selected features, final localized copy, and explicit
review states. Machine evidence and provenance constrain freshness only; they
do not constrain the Owner's editorial conclusions.

Readiness, workbook validation/import, and Landing generation obtain that
machine-fact digest from the same exact-week Landing fact builder. The digest
covers the complete Landing fact payload and the admitted observation slice;
a separate digest of Top 8 rows, event IDs, or known archetype IDs is not an
equivalent binding. A candidate that already carries a different machine-fact
digest is stale and fails closed.

Known-archetype continuity state advances after the classified weekly baseline
is accepted, independently of whether the Owner selects any feature. An
explicitly reviewed empty feature list is valid and must not prevent state
maintenance. During active Landing authoring, a changed event set, classifier
digest, policy digest, fact digest, or link catalog marks that private review
source stale and preserves the last admitted public Landing until explicit
re-review. After the whole weekly workflow is recorded complete, lifecycle
revalidation instead compares the material Top 8 review subject and admitted
Landing content; a global classifier digest change with no reviewed-content
change does not reset the week to an unstarted state.

The default conversation/Web workflow is defined in [WEEKLY_MAINTENANCE](WEEKLY_MAINTENANCE.md).
Accepted conversation content is stored in the same private week document and
validated against the exact review subject before generation. XLSX is an optional
alternative input, not a mandatory intermediate or duplicate Owner review.
Conversation review version `1.2.0` uses `content_sha256`, the canonical digest of
`format`, `week`, and `review`, instead of claiming an XLSX `workbook_sha256`.
`tools/import_landing_conversation.py` requires accepted content and its original
machine bindings, checks those against the current subject, and validates before
writing. Legacy `1.0.0`/`1.1.0` workbook binding semantics remain unchanged.
The optional Landing-only XLSX review carrier contains `Review Control`, `Landing Copy`,
`Featured Decks`, `All Top 8`, and `Field Guide`. It is not a database. Accepted
content is validated and imported into the private week document before preview
or publication. The Owner is not asked to provide internal input IDs, stable
classifier IDs, generated link labels, or arbitrary URLs.

`Review Control` carries immutable scope and calculated completeness only. The
Owner submits authored Chinese content once in chat and later edits or accepts
English once; duplicate approval cells are not machine facts. Read-only
`chinese` and `bilingual` validation stages bind the submitted workbook hash and
validate actual content. Import writes that accepted content within the current
authorized task; reuse the valid content check when its workbook and source
remain applicable, without a separate authorization stage.

The Landing workbook supplies read-only review context, ordered Landing copy and bilingual editing, selected
features with category/positioning/four cards, all exact Top 8 decks, and field
guidance. Links derive from selected deck IDs; there is no independent link-only
selection or editable feature-order authority. It carries business content,
not a second task-authorization record.

The shared review-workbook intake reads XLSX cells from raw OOXML, including
explicit shared-string, inline-string, cached-formula, numeric, boolean, and
true-blank semantics. A referenced empty shared string normalizes to a true
blank; the numeric index is never content. Every Owner-returned workbook passes
through `tools/review_workbook_intake.py` before semantic interpretation. When
the issued workbook is retained, its normalized cell values are compared with
the returned workbook and only the resulting semantic differences may carry
Owner intent. Product importers reuse this reader and bind the accepted
workbook SHA-256 before writing any private review file. Repeated import of the
same immutable workbook and repository subject is deterministic; a workbook
byte change, incomplete stage content, source identity change, or intake error
fails before admission.

Explicit `[[card:English Name]]` or `[[card:English Name|display label]]` tokens
in localized Top copy use the existing card localization and preview interaction.
`tools/prepare_landing_copy.py` recognizes exact names from the shared bilingual
catalog and inserts these tokens without changing the displayed prose. It preserves
existing tokens, reports ambiguous mentions, and does not infer Owner acceptance.
These references also enter current Landing localization demand. The
Owner does not need to type internal syntax.

Top copy may embed zero or more exact `deck:<20-hex deck ID>` tokens at any
desired positions. Non-empty localized versions use the same token set, but
their prose and token positions may differ. The producer derives localized
archetype-player-rank displays, URL, order, and exact event/deck identity from
the complete Top 8 catalog. Only the generated display becomes a hyperlink;
the surrounding sentence remains ordinary text.

Each approved feature carries category, derived category-local order, a stable
format/classifier identity, a catalog-derived localized title,
Owner-reviewed localized positioning, exact deck identity and decklist,
supporting facts, and four unique reviewer-selected cards from that deck. The
bilingual catalog is keyed by `(format, parent_id, subtype_id-or-none)`; English
comes from the classifier taxonomy and Chinese requires Owner confirmation.
Classifier maintenance fails closed when a new or renamed public identity lacks
catalog coverage.

There is no item-count limit. Landing renders `new_deck` before
`new_technology`. Inside a category, order follows exact deck-token appearance
in final top copy, reading kept copy rows in order and multiple tokens left to
right. Features absent from top copy are appended deterministically by retained
source order and exact deck ID. This derived order may be serialized for the
reader but is not an Owner input. Landing uses one disclosure action with the
shared deck-detail presentation. Review state and reviewer terminology never
enter public output.

Publication writes the reviewed latest Landing and the selected feature week
together:

```text
stats/<format>/mtgo/landing/current.json
stats/<format>/mtgo/landing/features/index.json
stats/<format>/mtgo/landing/features/<week>.json
```

The current document and feature-week document share the exact reviewed
feature subject. A missing or invalid required feature document blocks the
cutover rather than silently appearing as an empty week. A deliberately empty
week requires an explicit reviewed-empty state.

#### Feature-card image cache (Cache-A and Cache-B)

For each maintained format, Cache-A anchors at the latest week present in that
format's public feature index and selects that ISO week plus its three immediate
ISO predecessors. Missing weeks inside the interval do not pull older weeks
into the window. The cache subject is the normalized union of every
`features.items[].featured_cards[].name` in the selected week documents across
Standard and Modern; it does not include complete decklists or environment
representative cards merely because they exist elsewhere.

The builder resolves every name from one gzip-compressed Scryfall Oracle Cards
JSONL Bulk Data snapshot, including a named face of a double-faced card, and
fetches its complete `normal` card JPEG from a validated HTTPS
`*.scryfall.io` URL. Repository representative-card images are cropped art for
a different UI role and are never cache inputs. All names must resolve and all
bytes must validate before the external bundle is atomically admitted. The
manifest uses Schema `1.1.0` governed by
`schemas/landing-card-image-cache.schema.json`; generated files live only in a
workflow artifact and the Pages payload, not in Git. The Schema version is part
of the subject digest, so a legacy `1.0.0` mixed-image artifact cannot satisfy
the full-card subject.

Cache-B is the browser consumer for this verified overlay. The runtime admits
only the exact manifest path `assets/card-cache/v1/manifest.json`; image paths
remain ordinary static browser resources and cannot be used as JSON inputs.
For the selected format and Feature week, the controller accepts the manifest
only when its identity is supported, that exact week is listed in the format's
`selected_weeks`, and every used card has one exact-name mapping to an
allowlisted generated full-card cache path. Inline cards and their
preview/modal use the same selected image source. Legacy `1.0.0` manifests and
repository representative-card paths are rejected as cache inputs.

Weeks outside the manifest's admitted rolling window continue to request the
exact card image from Scryfall on demand. A missing, unavailable, unsupported,
or path-unsafe manifest also degrades to that same behavior instead of making
Landing unavailable. The existing paced one-at-a-time image queue retains its
per-attempt timeout, bounded automatic retry, placeholder, card preview, and
Feature-group manual retry behavior for either source. The Scryfall search
link and attribution remain unchanged.

#### Simple card localization boundary

The current localization architecture has removed the versioned `assets/card-localization/v1/` sidecar, immutable
printing-identity manifest, Scryfall Bulk candidate, English-byte proxy,
content-addressed overlay, and separate B1/B2/C admission route from the
current architecture. The deleted localization builder, Schema, and synthetic
contract are not production dependencies.

English card names already emitted by the existing product generators remain
the lookup keys. `card_names.py` owns the maintained-alias, front-face, and
legacy single-slash lookup candidates shared by localization and existing
classification consumers. The localization builder calls that shared entry
and does not contain a second name normalizer.

The Pages build creates `assets/card-localization/cards.json`, one small flat
map from each resolved English product key to an MTGCH Chinese display name,
the selected result record's validated canonical MTGCH card-page URL, and, when
available, the exact MTGCH Chinese image URL. It also creates
`assets/card-localization/images/<sha256-of-English-key>.webp` only for current
default-Landing keys with a Chinese image. Both are generated outside Git
history and admitted as one allowlisted Pages overlay. The browser delivery
rule is intentionally small:

- current default-Landing images are local Pages files for the selected
  language, reusing the existing English Landing cache and adding only the
  corresponding Chinese files;
- every other Chinese image uses its mapped MTGCH image URL on demand;
- every other English image keeps the existing Scryfall on-demand URL;
- Chinese decklist links use the mapped canonical MTGCH card page while English
  and unmapped links retain the existing Scryfall search destination;
- Landing environment representative cards keep the same configured cropped
  art as their inline image in both languages; their hover, focus, touch
  preview, and external link use the same language-aware complete image and
  provider selected for an ordinary card link, while current Feature cards
  retain complete card images; and
- a missing Chinese value falls back to the existing English name and image;
  a present Chinese name without a Chinese image keeps that Chinese name and
  falls back only the image.

The Owner-recorded MTGCH permission and required attribution still apply.
The existing full-card image reuse conditions are preserved here as part of
the migration of approved business constraints; no new permission is granted:

An admitted official image remains byte-for-byte original. Do not convert,
recompress, crop, filter, recolor, distort, watermark, overlay, or remove its
artist, copyright, or legal notices. Keep the admitted subject bounded to cards
used by the product; do not create a Scryfall or MTGCH mirror or proxy.

An admitted MTGCH community-rendered image remains byte-for-byte as supplied by
MTGCH. Do not relabel it as official or convert, recompress, crop, filter,
recolor, distort, watermark, overlay, or remove embedded legal or artist
notices. Identity-ambiguous, non-MTGCH third-party, or separately unpermitted
material fails closed unless a separate permission decision covers that exact
class. The absence of an MTGCH per-record source field is not evidence that an
MTGCH-supplied image is unknown third-party material. The existing English
complete-card image remains the fallback.

Historical source and browser trials already establish the selected source and
direct-image feasibility and must not be repeated as implementation gates.
Feature verification covers the affected generated map, declared local
Landing files and source-selection outcomes under QUALITY. There is no separate localization
Schema, source-snapshot proof, per-card provenance class, capacity-proxy
experiment, or staged optional-overlay admission.

Candidate preparation may reuse the already verified public-resource bundle as an Actions cache. Its
artifact name is bound to the exact public-product card-name set, current
Landing card-name set, localization builder, shared card-name normalizer, and
maintained alias input. Only a non-expired artifact produced from `master` may
satisfy that subject. A separate bounded preparation job builds only a missing
subject, verifies either source before handoff, and passes the verified bundle
to the unchanged 20-minute allowlisted Pages build. The cache adds no public
manifest, Schema, path, lookup field, or browser contract; the published
overlay remains exactly `cards.json` plus its declared current-Landing images.

Existing Pickup history remains frozen migration and rollback input:

```text
stats/<format>/mtgo/pickup/index.json
stats/<format>/mtgo/pickup/<week>.json
```

No new Pickup week is published after P12-15F. The legacy files are not deleted,
renamed, relocated, or modified without an approved compatibility change;
they retain frozen business history, not workflow authority or a governance rollback path. A legacy URL using
`product=weekly-pickup&week=<week>` continues to
resolve to `product=mtgo-landing&section=features&week=<week>`. The `week`
parameter affects only the feature section.

### 25.6 Availability and failure states

After Phase 12 closeout, a public format is valid only when its admitted
Landing and all of its required MTGO products are available together. Future
formats therefore have no catalog-level fallback that permits a public partial
launch without Landing. Catalog, production-candidate, and Pages validation
must reject that state.

Standard and Modern are the explicit migration exceptions because their
existing public products predate Landing. They remain online during Phase 12
and must satisfy the complete-product rule at P12-16. A runtime failure to load
an admitted Landing is different from missing capability: the shell remains
usable, offers retry, and provides a deterministic route to statistics.

Valid degradations are limited to Schema-valid `no_events`, an empty approved-
feature list, unavailable comparison values with reasons, text-only missing
key-card configuration, a single-language editorial fallback under the
existing language policy, and external-image placeholders. These states do
not permit malformed or internally inconsistent generated data.

At 390px, layout may stack values, scroll bounded regions, defer images, or
replace images with placeholders. It must retain the archetype name, current,
previous-week and previous-four-week values, movement direction, feature
category, and stable detail navigation.

### 25.7 Classifier-backed Landing identities

Landing uses approved stable parent/subtype identities and reviewed representative
cards. Historical Phase 12 planning stops are retired. Current business screening
thresholds remain in the Landing sections and STATISTICS_SPEC; this migration
does not change their values or require repeating historical shadow runs.

## 26. Classifier-derived artifact closure

`my_archetypes/<format>.yaml` remains the canonical classifier subject. The
closure operation discovers current public formats and their admitted products
from the existing catalogs; it does not add a dependency registry. A derived
artifact is current when it either binds that canonical subject directly or is
reachable through verified exact upstream SHA-256 links to an artifact that
does. Direct classifier digests are therefore limited to boundaries where the
existing SHA chain is insufficient:

- MTGO statistics, matchup, Top 8, hierarchy, Landing, and classification
  reports bind the canonical classifier subject directly;
- `stats/<format>/archetype_names.json` binds both the current classifier
  identity set and the format rows in `configs/mtgo_archetype_names.yaml`, plus
  their combined projection subject;
- each Melee classification overlay binds the canonical classifier subject and
  retained normalized event bytes directly; opportunity, event output, meta,
  and catalog documents continue through their existing exact SHA chain.

`stats/<format>/melee/index.json` is the current/public Melee event authority.
Every event it lists must resolve back to an enabled, verified Tabletop entry in
the source registry and have one complete overlay-to-catalog chain; missing,
stale, mixed, disabled, or unregistered public references prevent a healthy
result. An enabled and verified registry entry that is not in the public catalog
is eligible input, not public admission, and does not enter
classifier closure. Extra approved name rows are governed by the existing name
authority: they block only when that authority requires exact catalog equality.
The closure operation never creates, translates, renames, or accepts an
archetype identity.

`python -m mtgmeta.classifier_closure ... inspect` is read-only. The default
`converge` operation creates a staging tree from retained repository inputs,
rebuilds only stale deterministic families, validates protected-input
fingerprints, allowed paths, exact-SHA closure, and the affected JSON Schemas,
and reports the plan. It never fetches historical data. `converge --execute` materializes the prepared result only when included in
the current authorized task; it is not a new technical approval stage. Ordinary convergence materializes one fully
validated format at a time. Reviewed MTGO publication may explicitly co-stage
multiple already accepted public formats when their derived families are stale
at the same time: one external tree is generated and fully validated before one
rollback transaction materializes the complete named set. Candidate files and
rollback bytes are prepared beside their targets; any replacement or final-
inspection failure restores the exact pre-execute tree. A retained staging tree
may be used for diagnosis.

The format states are `CURRENT`, `STALE_REGENERABLE`,
`BLOCKED_OWNER_REVIEW`, and `INVALID`. A format is current only with zero
stale, missing, mixed-subject, or unexplained artifacts. An Owner blocker is a
valid fail-closed outcome, not a tool fault. Examples include missing approved
bilingual identity coverage, an intentional Unknown conflict, or a material
change to an accepted Landing result. Historical Landing and frozen Pickup
artifacts are outside automatic closure.

For a current public Melee event, closure also discovers any applicable
protected compatibility manifest through the existing Pages publication
configuration. A mismatch in classifier-derived exact bytes or its selected
catalog projection is `BLOCKED_OWNER_REVIEW` until an explicitly approved
manifest-version migration records the new exact subject. The manifest remains
Owner-protected and is never materialized by `converge`; immutable snapshot or
normalized-source drift is invalid rather than regenerable.

Inspection does not classify, generate, materialize or fetch. Those operations
remain explicit and their results are reusable under QUALITY and DELIVERY.

### MTGO reviewed publication membership

Private executable formats reuse the same statistical producers with retained
format-isolated inputs. They do not call the public membership resolver or
claim a public admission: metadata remains the supported unbound 1.0 shape,
and classification reports retain `all_available_events` scope. Public
formats keep metadata 1.1 binding and `all_admitted_events` report scope.
Private generator destinations must remain outside Pages-admitted trees.
Production selects only registered complete public MTGO products; event-only
archival eligibility remains a separate existing registry capability.
When an enabled, verified event in `configs/melee_events.yaml` belongs to a
format, that format's complete-public product set also requires
`stats/<format>/melee/index.json`. The registry-derived requirement prevents a
format from exposing only its four MTGO products while omitting its admitted
Tabletop product.
Statistical/report manifest mappings cover registered executable formats
dynamically and require embedded format identity to match the output path.
This changes neither formulas nor classifier rules. Human Landing/name decisions remain business judgments in the current task.
Pauper first publication is complete; historical phase gates have no authority.

#### Explicit private review execution

P14-03A adds a small ordered format/week scope boundary for executable MTGO
formats. It validates registry membership, the operation capability, format
path identity, duplicate formats, and completed ISO weeks. Default operations
still resolve only the complete public format set; a non-public format requires
an explicit private scope and repository-external output.

Private Landing review `1.1.0` binds the selected format's approved name rows.
Private Landing current `1.3.0` binds only that format's visual configuration.
Historical review and Landing versions retain their whole-catalog and
whole-visual digest rules. Feature archives, name projections, and card-cache
documents keep their existing versions while accepting a registry-validated
format identifier. Readiness `1.8.0` records `input.repository_sha`, carries no
production identity, and represents public admission fields as not applicable.
These contracts do not make a format public and do not authorize collection,
publication, ledger mutation, or Pages inclusion.

An executable, registered, non-public MTGO format with the `classification`
capability may produce a repository-external first-name review diagnostic.
`weekly_classification_name_bootstrap` version `1.0.0` retains the ordinary
weekly classifier subject, events, records, priority records, and no-decklist
boundary, but adds the complete taxonomy's parent and subtype rows as
`name_candidates`. Existing approved Chinese names are reference values;
missing values and every `chinese_suggestion` remain null. Its
`bootstrap_subject_digest` covers the complete document except that digest
field itself. It has no `classification_review_digest`, is pending Owner
review, and is never formal classification or completion evidence.

The `data_admissions` section of completion configuration 1.2 is a separate
authority from its `records` section. Each format has a fixed grandfathered
initial ID set and explicit Owner-accepted full-classification week sets, with
exact retained-source bindings. Public generators never infer admission from
Weekly `completed`, Landing status, directory growth, or an event-date cutoff.
The initial baseline is an existing-public-scope migration, not a claim that
the Owner historically reviewed all rows. Existing legacy completion evidence
is preserved without changing its meaning.

A format reaching its first public release uses
`owner_accepted_initial_public_scope`, not the grandfathered migration type.
That initial record binds explicit event IDs and retained source bytes, the
accepted classifier subject, the exact classification-review digest, the date
after the complete natural week, and Owner acceptance evidence. The two initial
types remain distinct so a newly reviewed product never creates false
historical-review evidence.

`mtgmeta.mtgo.publication.resolve_scope` resolves each format's continuous
approved natural-week frontier; `public_events` supplies the common retained
membership to event-dependent producers. Later accepted weeks cannot pass a
nonempty unaccepted week. Empty-gap observations permit continuous advancement
but do not authorize later arrivals. A late unlisted ID remains pending.

| Public product | Membership / provenance boundary |
| --- | --- |
| Rolling statistics and representative decks | `stats` public loader |
| Hierarchical matchup | `matchup` public loader before classification and archive aggregation |
| Top 8 weeks and comparison bases | `top8` through the shared public statistics loader |
| Weekly/range completeness | `completeness` through the shared public statistics loader |
| Public classification reports | `classification_reports_cli` through `public_events`; scope `all_admitted_events` |
| Source-coverage metadata | Same public event set; excludes orphan/pending archives from public coverage |
| Landing current machine facts | Shared public loader and approved frontier; content admission remains separate |
| Landing feature archives | Existing accepted content only; every referenced event must be admitted |
| Hierarchy and bilingual-name projection | Existing rule/name authorities, not an event-population filter; no new names or taxonomy |
| Format/global catalogs | Existing generated product references; never discover pending events independently |
| Frozen Pickup / historical compatibility products | Not regenerated or newly admitted; retained paths remain within the initial approved history |

`meta.json` 1.1 records one approved scope digest and an exact-byte map of the
format's existing MTGO public JSON tree. This binds the complete candidate
without adding the same digest to every downstream JSON. Read-only repository
and classifier-closure inspection checks scope, byte closure, event references,
and matching active data frontiers; it never classifies or generates data.
Classification reports use 1.2 to label their narrower public scope explicitly.
Private audit/report APIs still inspect the entire retained corpus; pending
results may be written only to task-local or Pages-excluded review carriers.

The explicit format publication operation forms a complete selected candidate
before materialization and obtains only the affected necessary proof under QUALITY. It reuses classifier-closure replacement/rollback, detects
concurrent protected/input/output drift, and never fetches. Production transfers the selected verified candidate through DELIVERY. No partial producer result is a publication subject. Data publication
leaves the last accepted Landing intact; the existing frontend rejects
cross-week companion facts. Later accepted Landing publication and actual
maintenance completion remain separate evidence.

Private readiness 1.7 is required because 1.6 has one shared review week and
requires identical format windows. In 1.7, review week, public week, data
acceptance, Landing preparation and completion are per-format. It retains the
private artifact carrier, exact production identity, full human classification
review, retained-corpus diagnostic queue, bounded metadata-delta timing,
deduplicated notices, and explicit completion checks. Legacy 1.6 and legacy
Top-8-only completion remain readable. No public readiness endpoint is added.
