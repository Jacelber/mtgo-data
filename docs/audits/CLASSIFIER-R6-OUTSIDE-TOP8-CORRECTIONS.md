# Classifier R6 outside-Top-8 corrections

Date: 2026-08-26

Branch: `codex/classifier-r6-outside-top8-corrections`

Base commit: `ed0001c58b0dddaa58b8291d3346d746941354cd`

Status: Owner accepted the local implementation and authorized continuous
same-task completion through commit, one Ready PR, required CI, and merge.
Production generation and Phase 13 remain outside this task.

## Scope and impact

The Owner authorized the combined local implementation after accepting the
Eldrazi Tron audit and the other proposed classifier corrections. The declared
artifact impact is `statistical_json_structure`: the maintained classifier and
bilingual-name sources change what later production generation will emit, but
this task does not generate or hand-edit production-derived documents.

The maintained changes are limited to:

- Modern Chant Control color classification;
- the boundary between independent `eldrazi-tron` and `tron` parents;
- one Standard Bant Jackal identity;
- complete bilingual names for the new identities; and
- the live task, decision, and audit records.

The existing Dimir and Mono-Blue Erayo parents remain unchanged.

## Eldrazi Tron boundary audit

The pre-implementation audit covered 243 retained Modern event files and 7,776
decks. Of 327 decks selected as Eldrazi Tron, 323 play exactly four main-deck
`Eldrazi Temple` and four copies of each of `Urza's Mine`,
`Urza's Power Plant`, and `Urza's Tower`. The remaining four play zero Temple
and the complete Urza-land set. All four are narca lists previously selected by
`eldrazi-tron-mono-green`:

| Event | Date | Rank | Accepted result |
| --- | --- | ---: | --- |
| `12841354` | 2026-05-02 | 27 | `tron/mono-green` |
| `12843812` | 2026-06-07 | 12 | `tron/mono-green` |
| `12844347` | 2026-06-15 | 26 | `tron/mono-green` |
| `12852731` | 2026-08-21 | 26 | `tron/selesnya` |

The first three lists contain at least two `Zimone's Experiment`, a Forest,
and no non-green main-deck mana source. The last list contains four each of
`Sowing Mycospawn`, `Bilbo's Gambit`, and `Talisman of Unity`, plus Forest and
Plains. Nine other full-Tron, no-Temple decks are already selected by the
separate `mono-blue-tron` parent and are outside the accepted change.

## Implemented rules

Every existing Eldrazi Tron rule now adds main-deck `Eldrazi Temple >= 4` and
`Urza's Power Plant >= 4` to its existing signature. This retains all 323
Temple-based results and excludes exactly the four audited no-Temple lists.

The independent `tron` parent contains:

- `tron-mono-green-zimone` at priority `648100`;
- `tron-selesnya-bilbos-gambit` at priority `648090`.

Chant Control adds disjoint Esper and Azorius paths: Esper requires a black
spell and no red spell, while Azorius requires neither a red nor black spell.
Jeskai retains the higher red-spell path. Standard adds
`bant-jackal-brightglass` at priority `31100` with the reviewed Jackal, Elves,
Gearhulk, and white-source signature.

## Complete retained-corpus comparison

A read-only comparison classified the same 13,020 retained Standard and Modern
decks with the base and changed rules. Exactly six selected results differ:

| Transition | Count |
| --- | ---: |
| `chant-control/azorius` to `chant-control/esper` | 1 |
| `eldrazi-tron/mono-green` to `tron/mono-green` | 3 |
| `eldrazi-tron/mono-green` to `tron/selesnya` | 1 |
| `selesnya-offense` to `bant-jackal` | 1 |

The final corpus has 13,014 classified decks and six retained Unknown decks,
with zero conflicts and zero invalid decks. Current relevant identity counts
are 323 Eldrazi Tron decks, three Mono-Green Tron decks, one Selesnya Tron
deck, one Esper Chant Control deck, and one Bant Jackal deck. The three Dimir
Erayo and two Mono-Blue Erayo results are unchanged.

The five Owner-supplied examples resolve as required:

- stefansson30952, Modern `12852736`, rank 9:
  `chant-control/esper`;
- aspiringspike, Modern `12852731`, rank 17: unchanged
  `mono-blue-erayo`;
- AgentP, Modern `12852736`, rank 24: unchanged `mono-blue-erayo`;
- narca, Modern `12852731`, rank 26: `tron/selesnya`;
- filpin, Standard `12852733`, rank 13: `bant-jackal`.

## Validation and stop point

The Modern and Standard rule validators pass. The official bilingual catalog
validator reports complete coverage with 332 names: 246 parents and 86
subtypes. The rule-triggered Top 8 restatement contract passes all three tests,
the bilingual JavaScript resolver passes all three tests, and the final live
status contract passes its one triggered test. Final changed-scope repository
validation passes four YAML files, 16 references, and six hygiene entries;
`git diff --check` also passes.

After Owner acceptance, complete the unchanged task through commit, one Ready
PR, required CI, and merge. Do not dispatch production, regenerate production
artifacts, refresh weekly evidence, begin Phase 13, or start another task.
