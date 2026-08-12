# Classifier R2 Shadow Audit

## Status and stop boundary

This is the owner-accepted local, non-production implementation of the R2
contract. The owner accepted the shadow results on 2026-08-10 and separately
authorized only a local R2 commit. It executes the R1 identity contract through
a separate shadow path; production rule files and production callers do not
import or read the R2 rules. No Pickup state, generated statistics, workflow,
public path, protected Melee source, or production configuration is changed.

R2 stops at owner review. It does not authorize a commit, publication, R3,
production-rule migration, Pickup migration, generated-data refresh, or
P12-10.

After review, the owner separately authorized the R2 local commit only. Remote
publication and R3 remain unauthorized. The agreed future sequence is R3 for
the accepted production and Pickup migration, followed by a separately
contracted R4 review of residual Unknowns. R4 aims to resolve or explicitly
defer every repeated high-value Unknown family; it does not require Unknown to
reach zero.

## Implementation

- `src/mtgmeta/classifier_shadow.py` adds only the semantic counters needed by
  R1's color-source, actual-colored-spell, Equipment, and Phyrexian-mana
  boundaries, then calls the shared `classify_counts` engine.
- `docs/audits/classifier-r2/semantic_card_features.yaml` is an explicit,
  reviewed, R2-only feature manifest. It is deliberately not a general card
  database. An unlisted land or spell contributes no semantic marker, so the
  shadow fails closed rather than guessing.
- `tools/build_classifier_r2_shadow_rules.py` deterministically generates the
  complete Modern and Standard shadow YAML files from the byte-preserved
  production rules plus the R1 changes.
- `tools/run_classifier_r2_shadow.py` produces deterministic, de-identified
  corpus, event, Pickup, Unknown, priority, and compatibility evidence.

The local MTG knowledge skill did not include a usable bulk card metadata file
in this installation. Therefore, the semantic feature manifest is limited to
the card markers explicitly reviewed in R0/R1. Before R3 production migration,
the owner should either accept that narrow fail-closed manifest or authorize a
separate authoritative metadata expansion. R2 does not silently broaden it.

## Protected-byte proof

| Artifact | SHA-256 before and after | Result |
| --- | --- | --- |
| `my_archetypes/modern.yaml` | `3DF393EF3CBEBD655D6BE68BFAC8012E488673D52CBF663706906297378FE411` | unchanged |
| `my_archetypes/standard.yaml` | `DCEE23F09920290E16532C01A8AF5B7CA7106C73F5ED3F9626DE03200C6C063C` | unchanged |
| `data/modern/melee/events/434455.json` | `0B4296A9573A4FACF4CFDE1CE98569156F78FDE6F5D2A1D3D662B54E2889E710` | unchanged |
| Modern Pickup known state | `6C3868B160E61F61F5FBF509EB6E56AA4E8EFB61AB26D4EA5E0D467A10D2F178` | unchanged |
| Standard Pickup known state | `311E102E971D6E5B12DBBBF8E50D8DF1D34D44EC4AA6E15684C1F6C340156032` | unchanged |

## Complete committed-corpus result

| Format | Records | Baseline classified / Unknown | Shadow classified / Unknown | Multiple-match delta | Same-parent subtype-match delta | Shadow conflicts | Shadow residual subtype | Rule-order mismatches |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Modern | 5,792 | 5,664 / 128 | 5,650 / 142 | -495 | -90 | 0 | 0 | 0 |
| Standard | 3,936 | 3,865 / 71 | 3,868 / 68 | -86 | -21 | 0 | 0 | 0 |

The Modern net change is 14 additional Unknowns: 31 formerly classified decks
become Unknown and 17 former Unknowns become classified. The new Unknowns are
the intended fail-closed results for incomplete Persist, low-Frog Dimir Tempo,
unsupported Blink, one incomplete Grixis Goryo's, and one unsupported Prowess
construction. Standard resolves exactly three former Unknowns through the
approved two-copy Requiting Hex threshold.

The remaining 42 Modern same-parent multiple-subtype matches are all recorded
in the deck-level report. They are priority-resolved overlaps, chiefly 17
Prowess/Lessons records plus retained pre-R1 Rhinos, Eldrazi Ramp, Soultrader,
and Broodscale overlaps; none is a residual subtype, equal-priority tie, or
order-dependent selection.

## R1 family results on the committed corpora

### Modern

| Family | Shadow result |
| --- | --- |
| Persist | Grixis 205; Agadeem 16; Esper 8; incomplete former Persist becomes Unknown or a complete higher parent |
| Goryo's | Cremator 3; Esper 274; Grixis 13; one incomplete former Grixis list becomes Unknown |
| Dimir Tempo | 176 total: Dimir 106, Grixis 44, Esper 26; six low-core former lists become Unknown |
| Blink split | Esper Ketramose 7; Esper Blink 111; Azorius Blink 0; Jeskai Stoneforge 3; Jeskai Blink 158; Mardu 19; Orzhov 3 |
| Broodscale Combo | Mono-Green 125; Gruul 117; Golgari 3; Simic 2; no residual subtype |
| Boros Ponza | Stable ID and rule membership retained; display name changed only in shadow |
| Eldrazi Ramp Chant | 0 committed-corpus positives; 112 retained Eldrazi Ramp records; approved complete rule is covered synthetically |
| Control split | Chant 204; traditional Azorius 26; traditional Jeskai 13; Omnath Midrange 4 |
| Hollow One split | Hollowvine 15; Rakdos Hollow One 29, partitioned Rakdos 27 / Mardu 2 |
| Living End | 169 total: Four-Color 1, Temur 71, Sultai 77, Bant 18, Rakdos 2; no fallback |
| Steel-Cutter / Prowess | Izzet Steel-Cutter 38; Rakdos Steel-Cutter 4; Mono-Red Artifact 2; Prowess 298 |
| Prowess leaves | Izzet 222; Temur 36; Grixis 13; Jeskai 2; Lessons 18; Boros 5; Mono-Red 2; Mardu 0 current, with synthetic positive coverage |
| Death's Shadow | Grixis 9; Dimir 1; Rakdos 3; no generic fallback |
| Mono-Blue Tron | 8, including the approved recovered Unknown |

The R1 oracle and the committed corpus are not the same snapshot. In
particular, the committed corpus contains no positive Eldrazi Ramp Chant,
Azorius Blink, Mardu Prowess, or several older Standard variants. These zeros
are reported rather than filled by inferred records. Every approved rule has a
focused executable positive test, but synthetic coverage is not presented as
observed usage.

### Standard

| Family | Shadow result |
| --- | --- |
| Izzet Aggro | 40, all without artificial subtype IDs |
| Azorius Prison | 54 |
| Boros Manufacturing | 24: Boros 16, Jeskai 8, Mardu 0 current; no residual subtype |
| Kona Omniscience | 35: Simic 11, Temur 24, Bant 0 current; mixed Temur/Bant marker fixture remains Unknown |
| Control split | Dark Jeskai 1; White Sultai 4; retained Jeskai 37; retained Sultai 13 |
| Allies Kindred | 2; stable parent ID and rules, display name only |
| Leyline Aggro | 4: Izzet 1, Boros 2, Rakdos 1; unsupported multi-color fixture remains Unknown |
| Dimir Deceit | 29: 26 retained plus exactly 3 resolved two-Hex Unknowns |

The smaller current counts versus the R1 historical oracles are exact corpus
deltas, not silently refreshed baselines. The committed Standard fixture is
read-only throughout R2.

## Precedence and fail-closed checks

- All 119 Modern rule priorities and all 82 Standard rule priorities are
  globally unique within their format; all rule IDs are unique.
- Reversing both parent and rule YAML order changes zero of 9,728 selections.
- Complete Mono-Blue and Boros Belcher rules outrank the broad Chant core.
- Eldrazi Ramp Chant and Omnath Midrange outrank Chant Control when complete.
- Azorius Energy outranks an overlapping Azorius Blink construction.
- Goryo's without the required Frog threshold, Grixis Goryo's with Ephemerate,
  low-core Dimir Tempo, and markerless Living End remain Unknown.
- Apostle's Blessing and Mutagenic Growth do not create a splash color.
- Kona Temur-plus-Bant, unsupported multicolor Leyline, and subthreshold white
  Sultai fixtures remain Unknown.

## Same-format Tabletop evidence

Event `434455` contributes 362 submitted Modern decklists and uses the same
Modern shadow rules as MTGO while retaining separate event data:

- baseline: 352 classified, 10 Unknown, 76 multiple matches;
- shadow: 351 classified, 11 Unknown, 64 multiple matches;
- shadow conflicts: 0; residual subtype: 0;
- participant identifiers retained in the report: false;
- source SHA-256 before and after: identical.

## Compatibility and Pickup dry run

The Modern P6-01 fixture remains untouched. The comparison covers all 5,792
Modern records: 2,929 retain the same parent label and 2,863 change parent
label relative to that older taxonomy. Every transition bucket remains in
`summary.json`; R2 does not accept or refresh P6-01.

The Pickup dry run changes no file:

- Modern: 54 current keys would become 69; remove 6 retired source parents and
  add 21 accepted targets. All 21 additions are initialized as known, preventing
  false new-archetype claims.
- Standard: 62 current display-name keys would become 60; remove 7 retired
  names and add 5 accepted names. All 5 additions are initialized as known.

The complete added, removed, retained, and false-new-prevention sets are in
`results/pickup_dry_run.json`.

## Deterministic evidence

| Output | SHA-256 |
| --- | --- |
| `results/summary.json` | `925E74A5B5F70C4733D00A8208D61F32F8717D6C56F6B7976197BA7A462D3284` |
| `results/deck_transitions.jsonl` | `476CC3CC55A0B86F396296CCC1E868E990F61B792605A26DAE163CEE5BDDD501` |
| `results/unknown_evidence.json` | `2CFD78F2DF991D91CDF1EF324D9CF17FB72558413C7E7D4B35B46887027BD506` |
| `results/event_434455_comparison.json` | `6590A1A863CE25C3ED46EC9601699AB45529073FADCA802E4E157F0BE312C0E3` |
| `results/pickup_dry_run.json` | `3929BCB2632CA7E0A92DC583EC096B4F7C8EACBAF2C1B64D6020FDF6498ABC1E` |

The deck-level output has exactly 9,728 lines. Each record uses a deterministic
20-character deck hash derived from format, ordinal, and normalized card
counts; source record IDs, players, participants, usernames, and accounts are
not copied.

## Validation

- R2 focused tests: 82 passed.
- R2 plus the existing focused classifier, shared-classifier, report, Modern
  taxonomy, migration-contract, Standard baseline/corpus, and Melee suites:
  138 passed.
- Ruff: passed for every R2 Python file and test.
- Complete CI-equivalent pytest shards: ordinary 843 passed / 8 deselected;
  committed-baseline 8 passed / 843 deselected.
- Repository validator: 2,096 files passed syntax, reference, and hygiene
  checks. Production and shadow rule validation, public Schema validation,
  the established mypy baseline, and strict checks of both new shadow modules
  passed.

## Owner review questions for a later authorization gate

R2 itself is executable and deterministic. Before any separately authorized
R3, owner review should explicitly decide whether to accept:

1. the exact committed-corpus deltas above, including zero-current-observation
   rules that have synthetic coverage only; and
2. the narrow fail-closed semantic manifest or a separately scoped,
   authoritative metadata expansion.

## R3 reproducibility handoff

On 2026-08-11 the Owner separately authorized R3 local production migration and
accepted the narrow fail-closed manifest option. R3 freezes the exact R2 source
rules and Pickup states under `docs/audits/classifier-r2/baseline_rules/` and
`docs/audits/classifier-r2/baseline_pickup/`. The R2 builders and tests read
those frozen paths, so this historical audit remains reproducible after the
production files change. This handoff does not retroactively change R2's shadow
results or authorize R3 commit or publication.
