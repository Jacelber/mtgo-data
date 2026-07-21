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

The repository may not yet contain every path described here. Migration must proceed through the phases defined in `ROADMAP.md` without breaking the current Standard MTGO page.

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
- new modules should receive tests before legacy code is removed;
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
│   ├── DECISIONS.md
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
│       │   └── pickup.py
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
- report partial failures;
- write source data through controlled paths.

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
- time-range aggregation;
- latest-complete-week logic;
- high-score statistics;
- Top 8 statistics;
- average decklists;
- representative decklists;
- construction deviation;
- recent change where applicable.

The generalized module must preserve existing Standard behavior unless a documented statistical change is approved.

### 5.4 `matchup.py`

Responsibilities:

- process the approved MTGO matchup source;
- retain source coverage metadata;
- calculate format-specific matchup outputs;
- use shared W-L-D utilities;
- avoid implying full event coverage when coverage is partial.

### 5.5 `pickup.py`

Responsibilities:

- Weekly Pickup;
- MTGO-specific weekly comparison;
- output generation for the MTGO front end.

Weekly Pickup does not belong in the Melee package.

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

During the Standard compatibility migration, only distinct legacy rule entries that already return the same legacy archetype may receive different subtype IDs. The initial known duplicate display-name groups are `4-Color Control` and `Izzet Aggro`. All other existing Standard archetypes must initially return no subtype. Choosing names and rules for additional archetypes or subtypes is a later, separately approved rule-development task.

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

The parent archetype fields are the compatibility contract. Subtype fields are supplementary and may be `null`. Reports and downstream consumers must not treat a subtype as an unrelated archetype.

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

The registry should eventually allow the front end and command-line tools to discover supported formats without hard-coding only Standard.

MTGO raw-event collection and product execution are separate states. `event_collection_enabled` authorizes only official event download, normalized archival storage, and fetched-ledger maintenance for that format. It does not authorize Videre fetching, classification, statistics, Pickup, catalogs, public output, or front-end exposure. Those operations continue to require the executable MTGO state and their declared capabilities.

During Phase 3, Standard, Pauper, Modern, Pioneer, Legacy, and Vintage retain their pre-migration official-event archive, while Standard remains the only executable MTGO product format. Non-Standard Videre collection is not implied by event archival.

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
    enabled: false
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
    notes: "Reference contract only; live fetching requires separate authorization"
```

This configuration does not by itself prove the exact round assignments. They must be verified during collection and normalization.

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

Existing Standard paths must not be moved until regression tests and front-end compatibility are in place.

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

Recommended files include:

```text
tournament.html
standings.json
rounds.json
matches.json
decklists.json
fetch_meta.json
```

If source endpoints require multiple pages, the implementation may store either:

- one combined raw response preserving source rows; or
- numbered source pages with a manifest.

### 10.1 Raw-data requirements

Raw files should preserve:

- source record IDs;
- source field names;
- original result strings;
- fetch timestamp;
- requested URL or endpoint;
- pagination information;
- status or error information.

Do not replace raw source values with normalized values in place.

### 10.2 Sensitive information

Do not store:

- authentication tokens;
- session cookies;
- private account information;
- unnecessary request headers containing credentials.

Only collect data required for approved public tournament analysis.

### 10.3 Raw-data retention

Raw data should be retained long enough to reproduce normalization and diagnose source changes.

The exact Git tracking or archival policy may depend on repository-size constraints and must be documented before large raw datasets are committed.

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

The normalizer resolves phase, stage, actual game format, participant status,
result type, points, and eligibility. Only internally consistent played results
in a reviewed Constructed Swiss phase of the event's configured format are
eligible for primary Constructed and matchup statistics. Draft, playoff, bye,
intentional-draw, no-show, drop, administrative, awarded, and unknown records
remain in normalized context but are ineligible. P5-06 output remains explicitly
non-publishable even when no unknown values remain; P5-07 owns the final quality
and publication gate.

---

## 12. Statistics-output layout

The public statistics root is:

```text
stats/
```

A global catalog should eventually be generated at:

```text
stats/catalog.json
```

The catalog should allow the front end to discover:

- product source;
- formats;
- available time ranges;
- available events;
- latest event;
- generated dates;
- schema versions;
- public JSON paths.

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
weekly_pickup.json
```

Actual available files should be listed in `index.json` or `stats/catalog.json`.

During migration, existing Standard output paths may remain as compatibility files until the front end uses the new catalog.

Do not remove a public path without a compatibility or migration plan.

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

### 12.3 Multi-event matchup output

A multi-event matrix may be generated dynamically or written as a generated artifact.

If written, it must retain:

- format;
- source;
- selected scope;
- included event IDs;
- included event names;
- W-L-D counts;
- generation time;
- schema version;
- compatibility checks.

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
- top-level navigation;
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
- compatible multi-event selection.

Shared rendering code may be reused, but MTGO and tabletop data must not be combined.

### 15.7 No statistical formulas only in UI

Primary statistical values must be generated or calculated through tested statistical code.

The front end may format values and combine explicitly supplied counts for approved interactive views, but a statistical rule must not exist only as undocumented JavaScript.

---

## 16. Test architecture

Tests belong under:

```text
tests/
```

Reusable test data belongs under:

```text
tests/fixtures/
```

### 16.1 Unit tests

Unit tests should cover:

- card-name normalization;
- rule loading;
- rule validation;
- deterministic classification;
- conflicts;
- Unknown results;
- statistical formulas;
- result-type handling;
- matchup aggregation;
- schema validation.

### 16.2 Regression tests

Regression tests must protect the current Standard implementation before major refactoring.

Regression fixtures should be small enough for routine CI while still representing important behavior.

Large production datasets should not be required for every unit-test run.

### 16.3 Melee fixture tests

Melee tests should use stored, reduced fixtures representing:

- standings;
- pagination;
- decklists;
- normal match results;
- normal draws;
- `0-0-3`;
- byes;
- drops;
- Day 1 and Day 2;
- Draft rounds;
- playoffs;
- Top 8 lock awarded wins;
- malformed or missing records.

Tests must not depend on live Melee availability for routine CI.

### 16.4 Schema tests

Schema tests should validate:

- representative valid files;
- required-field failures;
- invalid source IDs;
- invalid format IDs;
- invalid rate ranges;
- missing schema versions;
- incompatible result-type values.

---

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

Final commands must be documented in `README.md` and tested before legacy commands are removed.

### 17.1 Temporary compatibility wrappers

Existing scripts such as:

- `classify_standard.py`;
- `stats_standard.py`;
- `stats_matchup.py`;
- `batch_mtgo.py`;
- `weekly_pickup.py`;

may temporarily call the new package.

A wrapper should:

- preserve the old command where practical;
- display deprecation information only after the replacement is stable;
- avoid duplicating the full implementation;
- be removed only in a documented cleanup phase.

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

## 19. GitHub Actions architecture

Target workflows belong under:

```text
.github/workflows/
```

### 19.1 `ci.yml`

Purpose:

- run on pull requests and relevant pushes;
- install declared development dependencies;
- validate classification rules;
- run pytest;
- validate representative JSON files;
- prevent unsafe merges.

Permissions should default to:

```yaml
permissions:
  contents: read
```

CI should not receive write permission without a specific reason.

### 19.2 `update_mtgo.yml`

Purpose:

- scheduled and manual MTGO updates;
- fetch approved MTGO data;
- generate format statistics;
- run validation;
- run tests;
- commit only generated changes after checks pass.

It should use:

- explicit `contents: write`;
- a dedicated concurrency group;
- `cancel-in-progress: false` unless a later decision changes it;
- a workflow summary;
- no-op handling when no files change.

### 19.3 `fetch_melee.yml`

Purpose:

- manually fetch or refresh a whitelisted Melee event;
- verify whitelist membership;
- preserve raw source records;
- normalize data;
- classify decks;
- generate event statistics;
- run schema and quality validation;
- publish changes through a reviewable branch or pull request.

It should not perform unrestricted site-wide crawling.

Permissions must be limited to the steps actually used.

### 19.4 Existing workflows

Existing workflows such as `scrape.yml` and `update.yml` must be reviewed before replacement.

Do not leave two scheduled workflows running the same MTGO update command.

The migration must:

1. identify the currently active production workflow;
2. add the replacement;
3. test it manually;
4. disable or remove the duplicate schedule;
5. verify the next scheduled run;
6. document the change.

### 19.5 Failure reporting

Initial failure reporting should use:

- failed Action status;
- GitHub’s normal workflow notifications;
- `$GITHUB_STEP_SUMMARY`;
- uploaded diagnostic artifacts when useful.

Automatic issue creation is not required initially.

---

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

## 22. Compatibility and migration rules

### 22.1 Standard protection

Before changing the Standard pipeline:

- capture representative current outputs;
- add regression fixtures;
- define expected current behavior;
- test the existing public page;
- preserve recovery through Git history or a baseline tag.

### 22.2 Public path protection

Before changing a JSON URL used by `index.html`:

- locate all consumers;
- provide a compatibility file or coordinated front-end change;
- test through a local HTTP server;
- test GitHub Pages path behavior;
- document the migration.

### 22.3 No simultaneous uncontrolled rewrite

Do not combine all of the following in one uncontrolled change:

- classification rewrite;
- data-path migration;
- statistical formula changes;
- front-end redesign;
- workflow replacement.

Each should have a separate verification point.

### 22.4 Legacy cleanup

Legacy code and paths may be removed only when:

- the replacement exists;
- tests pass;
- generated outputs are validated;
- front-end consumers have migrated;
- workflows use the replacement;
- documentation has been updated;
- rollback is possible through Git history.

---

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
  → select same-format event IDs
  → select compatible Constructed scope
  → aggregate raw W-L-D counts
  → calculate rates and intervals
  → validate included event list
  → render consolidated matrix
```

MTGO records do not enter this flow.

---

## 24. Architecture-change procedure

A change is an architecture change when it affects:

- public data paths;
- source separation;
- normalized event structure;
- stable IDs;
- schema versions;
- package boundaries;
- workflow responsibilities;
- front-end entry points;
- generated-output contracts.

An architecture change must:

1. be recorded in `DECISIONS.md`;
2. update this document;
3. update affected JSON Schemas;
4. update tests;
5. update `ROADMAP.md` or `STATUS.yaml` when phase scope changes;
6. include a migration or compatibility plan;
7. preserve existing Standard behavior unless a statistical change is separately approved.

Do not implement a new architecture only through undocumented directory creation.
