# Classifier R4 residual Unknown review

## Status and authorization boundary

The Owner authorized `CLASSIFIER-R4-RESIDUAL-UNKNOWN-REVIEW` for local
execution on 2026-08-11 under the agreed non-production review contract. R4
uses isolated workspace
`D:/dl/crawlerpj/.codex-workspaces/classifier-r4-20260811-01`, branch
`codex/classifier-r4-residual-unknown-review`, and accepted local R3 base
`7bf804684ac22dcf71560bacae4d3bc49c56f08f`. Push is disabled and the local
credential-helper override is empty.

The declared artifact impact is `internal_diagnostics`. R4 may add only the
offline review builder, focused tests, de-identified audit artifacts, and live
task status. It may not change production rules, the semantic-feature
manifest, classification reports, statistics, Pickup state, source data,
workflows, Schemas, front ends, public paths, or product behavior. Commit,
publication, production rule promotion, the Landing shadow, and P12-10 remain
separate Owner gates.

## Frozen review inputs

| Input | SHA-256 |
| --- | --- |
| Modern MTGO Unknown report | `8a1d3da8ca89ee132d12b4d3a91b190a3886618e39b9c075ca10cdc8ac9272e2` |
| Standard MTGO Unknown report | `62dd1af46b5148b7c83a41d70f82769a0f21bf235f0e02d06a0a2ff6bad3d0ce` |
| Modern Tabletop 434455 classification overlay | `fddc92a3cd09d12434370ec75c0225158e75a81a9dafc8228518dd36f7a77d63` |
| Modern production rules | `df9c55e78e8fd8ed9e6cb18b0117a4d2947f207a302fe7148b3da00deee74045` |
| Standard production rules | `d88c3342826343f07442c37d4652b4caac5be7f690d21122fc31884b63eb37f5` |

MTGO and Tabletop records retain separate source and event evidence. Their
statistics are not merged. The queue stores neither the source MTGO deck IDs
nor Tabletop participant IDs; task-scoped SHA-256 prefixes identify records.

## Candidate-family method

R4 computes quantity-weighted Jaccard similarity over main-deck card counts
within one format and joins pairs at an edge threshold of `0.55`. Connected
components are candidate review families, not archetype assignments. Every
family reports minimum, median, and maximum pairwise similarity and flags when
transitive linkage puts a pair below the edge threshold.

Each family includes a deterministic medoid representative, common and
75-percent-prevalent cards, separate source/event counts, and the three nearest
production rules. Rule proximity is an explanation aid based on the share of
positive conditions met plus exclusion failures; it does not select an
identity. Review order is Modern then Standard, recurring multi-event families
first, then same-event multiples and singletons.

## Initial queue

| Format | Unknown records | Candidate families | Recurring families | Singletons |
| --- | ---: | ---: | ---: | ---: |
| Modern | 188 | 88 | 37 | 51 |
| Standard | 117 | 59 | 16 | 43 |
| Total | 305 | 147 | 53 | 94 |

No current family contains multiple records confined to only one event. The
committed inputs do not expose one common cross-source performance field, so
the queue does not invent a high-score, Top 8, or Day 2 priority. Recurrence is
the auditable first-pass priority and competitive relevance remains an Owner
review input.

Every family begins with workflow status `pending_owner_review` and a null
disposition. The only final dispositions are `map_existing`, `new_identity`,
`intentional_unknown`, and `defer_insufficient_evidence`. The generator never
overwrites an existing disposition file and rejects it if its frozen family
inventory no longer matches.

## Initial local verification

- focused R4 tests: 7 passed using a workspace-local pytest base directory;
- Ruff for the R4 builder and tests: passed;
- deterministic artifact rewrite: passed;
- all 305 records occur exactly once in the 147-family queue;
- every nearest production rule has zero complete matches, consistent with the
  production Unknown inputs; and
- source MTGO deck IDs and Tabletop participant IDs are absent from the output.

The first default pytest attempt passed five tests but could not create two
`tmp_path` fixtures under the system temporary directory. That infrastructure
error was not treated as a pass; the complete focused test file then passed
with a workspace-local `--basetemp`.

## Accepted family 1 shadow result

The Owner assigned `modern-unknown-d0ef54702fd3` the `new_identity`
disposition with target parent `rakdos-persist` (`Rakdos Persist`). Its shadow
rule requires at least three each of `Persist`, `Archon of Cruelty`, `Faithless
Looting`, `Bloodghast`, and `Stitcher's Supplier`, requires zero `Abhorrent
Oculus`, and permits at most two main-deck `Living End`.

The final `Living End` boundary followed an explicit false-positive review.
Without it, two frozen lists already classified as `Living End / Rakdos` also
matched the proposed Persist core; both contain three-to-four `Living End` and
four `Electrodominance`. The Owner confirmed that those complete Living End
packages must remain Living End. The bounded shadow result is:

- all 13 records in the accepted family select `rakdos-persist`;
- no other one of the 188 current Modern Unknown records selects the rule;
- the 5,792-record frozen Modern corpus changes exactly 13 Unknown records to
  `rakdos-persist`, retains all 5,650 previously classified identities, and
  ends with 5,663 classified and 129 Unknown records;
- reversing archetype and rule order changes no selected identity;
- synthetic threshold, Oculus, and Rakdos Living End boundaries pass;
- 22 focused R4 and documentation tests pass; and
- Ruff, `git diff --check`, the production Modern-rule hash
  `df9c55e78e8fd8ed9e6cb18b0117a4d2947f207a302fe7148b3da00deee74045`,
  and protected event 434455 hash
  `0b4296a9573a4facf4cfde1ce98569156f78fde6f5d2a1d3d662b54e2889e710`
  confirm the production boundary remains unchanged.

## Owner-review stop

The Owner assigned `modern-unknown-c925796c2322` the `map_existing`
disposition with target `broodscale-combo/gruul`. The shadow changes only the
Gruul rule's main-deck `Blade of the Bloodchief` minimum from three to two;
the minimum of three `Basking Broodscale` and one `Stomping Ground` remain
unchanged. All 12 target records select the Gruul subtype, no other current
Modern Unknown record is captured, and two frozen Unknown records make the
same expected transition. All previously classified frozen identities remain
unchanged, rule-order reversal remains stable, and the focused R4 suite now
passes 23 tests.

The Owner assigned transitive candidate family `modern-unknown-4d4eaac6eb6a`
the `map_existing` disposition with a de-identified 4+3 partition. Four
low-count Relic/Ketramose records map to `esper-ketramose` through a new
two-copy path that caps `Phelia, Exuberant Shepherd` at two. Three remaining
records map to `esper-blink` through an Ephemerate/Frog/Solitude path that caps
main-deck `Wrath of the Skies` at two. All seven current records select their
accepted target, no other current Modern Unknown is captured, four frozen
Unknown records map to Esper Ketramose, no previously classified frozen
identity changes, and the focused R4 suite now passes 24 tests.

The Owner assigned `modern-unknown-8a9473ba2af0` the `new_identity`
disposition and split it into the new `scapeshift` parent with six `naya`
records and one `four-color` record. Both paths require the reviewed
Scapeshift/Valakut/Dryad/Icetill core and exclude `Amulet of Vigor`; the
Four-Color path additionally requires `Bring to Light` and reviewed white and
blue mana sources, while the Naya path excludes blue and black mana sources.

The broader Scapeshift/Valakut check also surfaced two later-ranked families
that the Owner explicitly accepted during the same review:

- all five records in `modern-unknown-f20f8e8714d9` receive the `new_identity`
  disposition and map to a separate `gruul-valakut` parent. They contain the
  Valakut/Dryad/Icetill/Vibrance/Wrenn engine, no Scapeshift, and no reviewed
  white, blue, or black main-deck mana source;
- singleton `modern-unknown-40c81d1ba673` receives the `map_existing`
  disposition and maps to `amulet-titan` through a narrow Scapeshift path that
  retains four `Amulet of Vigor`, three `Cultivator Colossus`, two `Primeval
  Titan`, and at least three `Urza's Saga`. The existing general Amulet paths
  are unchanged.

All 13 newly accepted records select exactly their reviewed targets, no other
current Modern Unknown is captured, and all 45 records across the six accepted
candidate families select their recorded identities. In the 5,792-record
frozen corpus, seven Unknown records map to Scapeshift, five to Gruul Valakut,
and one to Amulet Titan. Together with earlier accepted rules, the shadow ends
with 5,682 classified and 110 Unknown records; all 5,650 previously classified
identities remain unchanged and reversed rule order selects the same identity.
Synthetic color, Bring to Light, Scapeshift, Wrenn, Amulet, and Saga boundaries
pass. The focused R4 and documentation suite now passes 26 tests.

The Owner assigned recurring family `modern-unknown-9ad9a23fe35b` and
singleton `modern-unknown-9e8a95a158d5` separate `new_identity`
dispositions. They become independent `izzet-through-the-breach` and
`rakdos-through-the-breach` parents with no shared Through the Breach parent
and no subtypes. This preserves separate primary environment, performance,
conversion, representative-list, and matchup identities for the materially
different blue selection/protection and black-red graveyard shells.

The Izzet rule requires at least three each of `Through the Breach`, `Emrakul,
the Aeons Torn`, `Ugin's Labyrinth`, `Eldrazi Temple`, `Devourer of Destiny`,
`Kozilek's Command`, and `Talisman of Creativity`. The Rakdos rule requires
the first five shared cards plus at least three each of `Goryo's Vengeance`,
`Faithless Looting`, and `Talisman of Indulgence`; it does not force
`Thoughtseize` or `Yggdrasil, Rebirth Engine`.

All six current Izzet records and the one current Rakdos record select their
accepted parent, and no other current Modern Unknown is captured. In the
frozen corpus, five Unknown records map to Izzet Through the Breach and one
maps to Rakdos Through the Breach. The shadow now has 5,688 classified and
104 Unknown records; all 5,650 previously classified identities remain
unchanged, reversed rule order remains stable, and synthetic threshold and
cross-shell boundaries pass. The focused R4 and documentation suite now
passes 27 tests.

Historical Gruul Through the Breach remains an explicitly separate future
parent, but R4 adds neither an empty identity nor a speculative rule because
the current Unknown queue and frozen corpus contain no reviewed Gruul sample.
A rule may be proposed only when a representative sample reappears.

The Owner assigned recurring family `modern-unknown-f427d58c5e09` the
`map_existing` disposition with target `necrodominance/cosmogoyf`. The new
`Cosmogoyf Necrodominance` subtype reflects that `Necrodominance`, `Soul
Spike`, discard, and black interaction define the deck while `Cosmogoyf` is
its finisher. The existing `fling-goyf` parent and rule remain unchanged.

The subtype rule requires at least three each of `Necrodominance` and
`Cosmogoyf`, and explicitly excludes `Thud` and `Fling`. It does not require
`Rite of Consumption`, `Plunge into Darkness`, `Serum Powder`, or `Soul
Spike`, so future Necrodominance builds that retain the defining Cosmogoyf
finisher are not excluded by supporting-card churn.

All six current family records select `necrodominance/cosmogoyf`, no other
current Modern Unknown is captured, and the frozen corpus has no matching new
version. Its 5,688 classified and 104 Unknown totals therefore remain
unchanged. Synthetic minimum-count and exclusion boundaries pass; a complete
Thud/Plunge/Cosmogoyf core still selects `fling-goyf`. The focused R4 and
documentation suite now passes 28 tests.

The Owner assigned recurring family `modern-unknown-5dc6814edc94` the
`new_identity` disposition and split the new `badgermole-combo` parent into
three `golgari` records and two `mono-green` records. Both rules require at
least three each of `Badgermole Cub`, `Leyline of Abundance`, `Green Sun's
Zenith`, and `Quirion Ranger`, and explicitly require zero `Vizier of
Remedies`. Reviewed main-deck mana sources distinguish the two subtypes.

One Mono-Green record contains four `Devoted Druid` and one `Quillspike`, but
it contains no `Vizier of Remedies` and no white source. The Owner confirmed
that Devoted Combo requires both Druid and Vizier, so the auxiliary
Druid/Quillspike package does not override the Badgermole core.

The existing `devoted-druid-combo` parent gains `abzan` and `selesnya`
subtypes without changing its stable parent ID or primary rule ID. Both paths
retain the existing Druid/Vizier/Nature's Rhythm core. Abzan requires reviewed
white and black main-deck sources, excludes red, and deliberately permits a
blue main-deck or sideboard splash. Selesnya requires a reviewed white source
and excludes reviewed blue, black, and red main-deck sources. All 17 frozen
Devoted Combo records retain their parent and primary rule and receive the
Abzan subtype; the current and frozen inputs contain no reviewed Selesnya
record, so that boundary is protected synthetically rather than credited as a
captured result.

All five current family records select their accepted Badgermole subtype and
no other current Modern Unknown is captured. Three frozen Unknown records map
to Golgari Badgermole, bringing the shadow to 5,691 classified and 101 Unknown
records. Reversed rule order remains stable. Synthetic checks cover Abzan,
Selesnya, blue-splash Abzan, Golgari Badgermole, Mono-Green Badgermole, the
Druid/Quillspike exception, and the mandatory Vizier boundary.
The focused R4 and documentation suite now passes 29 tests.

The Owner assigned recurring family `modern-unknown-7cdba8c5c977` a
partitioned `new_identity` disposition. Its three `Molten-Core Maestro`
records become a separate `dark-maestro` parent, while its two all-sorcery
tutor records become `coffers/umori`. Reviewing all Coffers records together
also resolved singleton `modern-unknown-6e6a2cffda6b` as `coffers/dimir` and
singleton `modern-unknown-85c03cc18342` as `coffers/golgari`.

The new `coffers` parent has `dimir`, `golgari`, and `umori` subtypes. Dimir
requires at least three each of `Cabal Coffers`, `Watery Grave`, and `Consult
the Star Charts`. Golgari represents the traditional Karn build and requires
at least three Coffers, three `Karn, the Great Creator`, and two `Underground
Mortuary`. Umori requires at least three each of Coffers, `Dark Petition`,
`Profane Tutor`, `Sylvan Scrying`, and `Bloodchief's Thirst`, and excludes
`Molten-Core Maestro`. Because production classification signatures are
mainboard-only, the Umori rule deliberately uses the reviewed all-sorcery
main-deck signature rather than the sideboard companion card.

Dark Maestro requires at least three each of Coffers, Dark Petition, and
Profane Tutor plus two Molten-Core Maestro. It remains a separate parent
because its five-mana spell-chain engine differs from Coffers control and is
incompatible with the Umori construction restriction. All four rules
explicitly exclude `Necrodominance`. Historical Mono-Black Coffers receives
neither an empty subtype nor a speculative rule because no current reviewed
sample exists.

All seven current Coffers-bearing Unknown records select their accepted
identity and no other current Modern Unknown is captured. The frozen corpus
maps three Unknown records to Dark Maestro and four to Coffers, bringing the
shadow to 5,698 classified and 94 Unknown records. All 5,650 previously
classified identities remain unchanged and reversed rule order remains
stable. Synthetic checks cover every positive threshold, the Necrodominance
exclusions, the Maestro/Umori split, all three Coffers subtypes, and the
intentional historical Mono-Black Unknown boundary. The focused R4 and
documentation suite now passes 30 tests.

The Owner assigned recurring family `modern-unknown-d8a3a621999d` a
`new_identity` disposition as the separate `eight-rack` parent, displayed as
`8-Rack`, with no subtype. Its five records share four `The Rack` and three
`Raven's Crime`; four records contain three `Smallpox`, while the fifth contains
none.

The accepted mainboard rule therefore requires at least three `The Rack` and
two `Raven's Crime`. It does not require `Smallpox`, `Bandit's Talent`, `Dauthi
Voidwalker`, or `Urza's Saga`: those cards describe current construction
choices but are not needed to identify the reviewed Rack discard engine.

All five records in the current family select `8-Rack`, and no other current
Modern Unknown is captured. The frozen corpus maps one Unknown record to
8-Rack, bringing the shadow to 5,699 classified and 93 Unknown records. All
5,650 previously classified identities remain unchanged and reversed rule
order remains stable. Synthetic checks cover both positive thresholds and
confirm that sideboard-only copies do not satisfy the mainboard rule. The
focused R4 and documentation suite now passes 31 tests.

The Owner assigned recurring family `modern-unknown-c810dd70e4c7` a
`new_identity` disposition as the separate `leyline-fling` parent, displayed as
`Leyline Fling`, with no subtype. The family remains separate from Prowess
because its defining plan copies pump spells with `Leyline of Resonance` and
converts the enlarged creature into direct damage through `Callous Sell-Sword`.

The accepted mainboard rule requires at least three each of `Leyline of
Resonance`, `Heartfire Hero`, `Callous Sell-Sword`, and `Monastery Swiftspear`.
It does not require `Blood Crypt`, a specific pump spell, or another color
source, so the identity follows the reviewed engine rather than the current
mana-base choice.

All four records in the current family select Leyline Fling, and no other
current Modern Unknown is captured. The frozen corpus maps four Unknown records
to Leyline Fling, bringing the shadow to 5,703 classified and 89 Unknown
records. All 5,650 previously classified identities remain unchanged and
reversed rule order remains stable. Synthetic checks cover all four positive
thresholds, the color-independent boundary, and the mainboard-only zone. The
focused R4 and documentation suite now passes 32 tests.

The Owner assigned recurring family `modern-unknown-ee53a8117d33` a
`map_existing` disposition to the existing `orzhov-blink` parent, displayed as
`Orzhov Blink`, with no new subtype. The existing strict
`orzhov-blink-primary` path remains unchanged; a separate
`orzhov-blink-splash` path recognizes the same reviewed engine when a utility
or splash land supplies another color.

The accepted mainboard rule requires at least three each of `Phelia,
Exuberant Shepherd`, `Overlord of the Balemurk`, `Solitude`, and `Thoughtseize`,
plus at least two each of `Ephemerate`, `Emperor of Bones`, and `Flickerwisp`.
It excludes `Psychic Frog`, `Quantum Riddler`, `Detective's Phoenix`, `Phlage,
Titan of Fire's Fury`, and `Goryo's Vengeance`, preserving the reviewed Esper,
Mardu, and Goryo boundaries without treating an isolated off-color land as a
new identity.

All four records in the current family select Orzhov Blink, and no other
current Modern Unknown is captured. Six frozen records satisfy the reviewed
signature: three already select the strict Orzhov Blink primary rule and three
additional Unknown records now map to Orzhov Blink. This brings the shadow to
5,706 classified and 86 Unknown records. All 5,650 previously classified
identities remain unchanged and reversed rule order remains stable. Synthetic
checks cover all seven positive thresholds, all five exclusions,
utility-splash recognition, and retention of the strict primary path. The
focused R4 and documentation suite now passes 33 tests.

The Owner assigned recurring family `modern-unknown-3e688b954ff0` a
`map_existing` disposition to the existing `eldrazi-aggro` parent. Review of
the current production rule established that `It That Heralds the End` is not
a required deck core, so R4 repairs the existing `eldrazi-aggro-primary` rule
rather than adding a fallback path, subtype, or parent.

The repaired mainboard rule requires at least three `Eldrazi Linebreaker`, the
only accepted positive core, and excludes `Basking Broodscale` to preserve the
reviewed Broodscale Combo boundary. `Glaring Fleshraker`, `Thought-Knot Seer`,
`It That Heralds the End`, Chalice, and big-mana components remain construction
choices rather than hard requirements.

All three records in the current family select Eldrazi Aggro, and no other
current Modern Unknown is captured. The frozen corpus maps three additional
Unknown records to Eldrazi Aggro; eighteen previously classified Eldrazi Aggro
records remain in the same identity, and the singleton Linebreaker Broodscale
record remains Gruul Broodscale Combo. This brings the shadow to 5,709
classified and 83 Unknown records. All 5,650 previously classified identities
remain unchanged and reversed rule order remains stable. Synthetic checks
cover the Linebreaker threshold, mainboard-only zone, removal of the old It
requirement, and the Broodscale exclusion. The focused R4 and documentation
suite now passes 34 tests.

The Owner jointly assigned recurring family `modern-unknown-5efeda24e2e7` and
singleton family `modern-unknown-73dd687413c6` a `new_identity` disposition as
the `mono-green-stompy` parent, displayed as `Mono-Green Stompy`, with no
subtype. The singleton's Badgermole, Disciple, and Endurance package is a
construction variation of the same reviewed aggressive green shell rather than
a separate identity.

The accepted mainboard rule requires at least three `Aspect of Hydra` and three
`Old-Growth Troll`. `Steel Leaf Champion`, `Frenzied Baloth`, `Green Sun's
Zenith`, both Hierarchs, Badgermole Cub, and minor black utility lands remain
construction choices rather than identity requirements.

All four jointly reviewed current records select Mono-Green Stompy, and no
other current Modern Unknown is captured. The frozen corpus maps four Unknown
records to the new parent, bringing the shadow to 5,713 classified and 79
Unknown records. All 5,650 previously classified identities remain unchanged
and reversed rule order remains stable. Synthetic checks cover both positive
thresholds and the mainboard-only zone. The focused R4 and documentation suite
now passes 35 tests.

The Owner assigned recurring family `modern-unknown-65dd853f8982` a
`map_existing` disposition to the existing `dredge` parent. Review of the
production rule established that `Burning Inquiry` is a variable construction
choice rather than a required Dredge core, so R4 repairs the existing
`dredge-primary` rule instead of adding a path, parent, or subtype.

The repaired mainboard rule retains at least three each of `Arclight Phoenix`,
`Creeping Chill`, and `Life from the Loam`, and removes the Burning Inquiry
threshold. `Stinkweed Imp`, `Golgari Thug`, `Exhibition Tidecaller`, and the
exact discard package remain construction choices.

All three records in the current family select Dredge, and no other current
Modern Unknown is captured. The frozen corpus maps three additional Unknown
records to Dredge while all twenty-two previously classified Dredge records
remain in the same identity. This brings the shadow to 5,716 classified and 76
Unknown records. All 5,650 previously classified identities remain unchanged
and reversed rule order remains stable. Synthetic checks cover all three
positive thresholds, removal of the old Burning Inquiry requirement, and the
mainboard-only zone. The focused R4 and documentation suite now passes 36
tests.

The Owner assigned recurring family `modern-unknown-6cdec22cea94` a
`new_identity` disposition as the `hardened-scales` parent, displayed as
`Hardened Scales`, with no subtype. The counter-artifact engine remains
separate from Affinity and Broodscale Combo.

The accepted mainboard rule requires at least three `Hardened Scales`, the
identity's only required core. `Arcbound Ravager`, `Walking Ballista`, `Zabaz,
the Glimmerwasp`, `Agatha's Soul Cauldron`, `Mox Opal`, and `Urza's Saga`
remain construction choices rather than hard requirements.

All three records in the current family select Hardened Scales, and no other
current Modern Unknown is captured. The frozen corpus maps three Unknown
records to the new parent, bringing the shadow to 5,719 classified and 73
Unknown records. All 5,650 previously classified identities remain unchanged
and reversed rule order remains stable. Synthetic checks cover the positive
threshold and mainboard-only zone. The focused R4 and documentation suite now
passes 37 tests.

The Owner assigned recurring family `modern-unknown-94aa91fd1ab6` a
`map_existing` disposition to the existing `izzet-wizards` parent. R4 repairs
the existing `izzet-wizards-primary` rule rather than adding a rule path,
parent, subtype, or semantic manifest.

The repaired rule retains at least two `Snapcaster Mage` and at least three
`Flame of Anor` in the mainboard, removes the `Lightning Bolt` threshold, and
directly lists 41 reviewed white spells as zero-count exclusions across the
mainboard and sideboard. White-producing lands alone do not define Jeskai, and
`Apostle's Blessing` remains color-neutral for this classification because it
can be cast through Phyrexian mana. The Owner accepted the bounded maintenance
risk that a future unlisted white spell can temporarily fall to Izzet until the
inline exclusions are updated.

All three records in the current family select Izzet Wizards, and no other
current Modern Unknown is captured. The frozen corpus maps one Unknown record
to Izzet Wizards and intentionally migrates `modern-baseline-1079`,
`modern-baseline-1208`, and `modern-baseline-5419` from Izzet Wizards to Jeskai
Control because each contains a reviewed white spell. This brings the shadow
to 5,720 classified and 72 Unknown records; the other 5,647 previously
classified parent identities remain unchanged, and reversed rule order remains
stable. Synthetic checks cover both positive thresholds, removal of the Bolt
requirement, every reviewed white exclusion in both zones, white-producing
lands, and the Phyrexian-mana exception. The focused R4 and documentation suite
now passes 38 tests.

The Owner assigned recurring family `modern-unknown-becb8c1f6ef5` a
`map_existing` disposition to the existing `golgari-yawgmoth` parent rather
than Badgermole Combo. The three identical mainboards use four each of
`Yawgmoth, Thran Physician`, `Young Wolf`, `Chord of Calling`, `Birthing
Ritual`, `Badgermole Cub`, and `Marionette Apprentice`; Grist is the omitted
construction choice that caused the production miss.

R4 leaves the original `Yawgmoth >= 3` plus `Grist >= 1` primary rule intact
and adds one lower-priority supplemental path requiring at least three
`Yawgmoth, Thran Physician` and at least two `Young Wolf` in the mainboard.
Young Wolf is the accepted long-standing sacrifice core. Birthing Ritual,
Badgermole Cub, Chord of Calling, Marionette Apprentice, and Grist are not
additional requirements. A future Yawgmoth construction that abandons Young
Wolf is intentionally held for explicit rule review rather than absorbed by a
one-card catch-all.

All three records in the current family select Golgari Yawgmoth through the new
path, and no other current Modern Unknown is captured. The frozen corpus maps
three Unknown records to Golgari Yawgmoth, bringing the shadow to 5,723
classified and 69 Unknown records. All previously classified parent identities
remain unchanged; the 75 existing Golgari Yawgmoth records continue to select
the original higher-priority Grist path where applicable, and reversed rule
order remains stable. Synthetic checks cover both thresholds, both zones, the
unchanged Grist path, and deterministic precedence when both paths match. The
focused R4 and documentation suite now passes 39 tests.

The Owner assigned recurring family `modern-unknown-cb589e90e894` a
`new_identity` disposition as the `asmo-persist` parent, displayed as `Asmo
Persist`, with no subtype. The Cookbook construction remains separate from
traditional Rakdos Persist because its discard, removal, and resource engine
is materially different.

The accepted mainboard rule requires at least three each of `Persist`, `Archon
of Cruelty`, `Faithless Looting`, `Asmoranomardicadaistinaculdacar`, `The
Underworld Cookbook`, and `Ovalchase Daredevil`. Ovalchase Daredevil is an
absolute identity requirement rather than a replaceable support card.
`Monument to Endurance`, `Mox Opal`, `Emperor of Bones`, and `Urza's Saga`
remain construction choices; one reviewed list already omits Monument.

All three records in the current family select Asmo Persist, and no other
current Modern Unknown is captured. The frozen corpus maps three Unknown
records to the new parent, bringing the shadow to 5,726 classified and 66
Unknown records. No previously classified frozen identity migrates because of
this rule, and reversed rule order remains stable. Synthetic checks cover all
six required thresholds, the mainboard-only zone, Asmo precedence over a
hypothetical traditional Rakdos hybrid, and the existing higher-priority
Grixis Oculus boundary. The focused R4 and documentation suite now passes 40
tests.

The Owner assigned recurring family `modern-unknown-f6c2df4d63d4` a
`new_identity` disposition as the `izzet-storm` parent, displayed as `Izzet
Storm`, with no subtype. It remains separate from Ruby Storm because the blue
creature-reducer and card-selection construction uses no Ruby Medallion.

The accepted mainboard rule requires at least three `Ral, Monsoon Mage`, three
`Stormcatch Mentor`, and two `Past in Flames`, and requires zero `Ruby
Medallion`. `Flow State`, `Desperate Ritual`, `Pyretic Ritual`, `Manamorphose`,
`Grapeshot`, and individual blue card-selection spells remain construction
choices. In particular, Flow State is not required because the reviewed older
Izzet Storm construction predates it while retaining the Ral, Mentor, and Past
in Flames engine.

All three records in the current family select Izzet Storm, and no other
current Modern Unknown is captured. The frozen corpus maps three Unknown
records to the new parent, bringing the shadow to 5,729 classified and 63
Unknown records. No previously classified frozen identity migrates because of
this rule, and reversed rule order remains stable. Synthetic checks cover all
three positive thresholds, the mainboard-only zone, the zero-Ruby boundary,
and selection of the existing Ruby Storm parent once three Ruby Medallion are
present. The focused R4 and documentation suite passed 41 tests at that review
point.

The Owner assigned recurring family `modern-unknown-08e0d37d950d` a
`new_identity` disposition as the `eldrazi-ouroboroid` parent, displayed as
`Eldrazi Ouroboroid`, with no subtype. It remains separate from the accepted
Linebreaker-based Eldrazi Aggro identity, Ugin's Labyrinth Eldrazi Ramp, and
the established Badgermole and Broodscale combo identities.

The accepted mainboard rule requires at least three `Ouroboroid`, three
`Badgermole Cub`, three `Eldrazi Temple`, and three `Sowing Mycospawn`.
`Thought-Knot Seer`, `Green Sun's Zenith`, `Springheart Nantuko`, `Kozilek's
Command`, and the tutor package remain construction choices. Rule priority is
below the reviewed Eldrazi, Badgermole Combo, and Broodscale Combo paths so a
future dual match retains the established identity.

The shadow captures exactly the family's two records and no other current
Unknown record. The frozen 5,792-record corpus now reports 5,731 classified and
61 Unknown records, with 85 parents, 145 rules, globally unique numeric rule
priorities, and no migration of a previously classified record beyond the
three already reviewed Izzet Wizards to Jeskai Control corrections. Synthetic
coverage checks every positive threshold, mainboard-only behavior, and
precedence for Eldrazi Aggro, Eldrazi Ramp, Badgermole Combo, and Mono-Green
Broodscale Combo. The focused R4 and documentation suite now passes 42 tests.

The Owner assigned recurring family `modern-unknown-0fc20ed0d1a8` a
`new_identity` disposition as the `sultai-persist` parent, displayed as
`Sultai Persist`, with no subtype. It remains separate from Grixis, Agadeem,
Esper, Rakdos, and Asmo Persist; every established Persist identity keeps its
higher rule priority.

The accepted mainboard rule requires at least three `Persist`, three `Archon
of Cruelty`, three `Psychic Frog`, and three `Malevolent Rumble`. `Eyetwitch`,
`Stitcher's Supplier`, `Witherbloom Charm`, `Flare of Malice`, `Abhorrent
Oculus`, `Emperor of Bones`, and the remaining sacrifice or self-mill package
remain construction choices.

A complete scan of 212 current Modern event files and 6,784 deck records
captures exactly the two reviewed records, both previously Unknown, with no
additional Sultai Persist match. These records are outside the frozen corpus,
so the 5,792-record baseline remains 5,731 classified and 61 Unknown records.
The shadow now has 86 parents and 146 rules with globally unique numeric
priorities. Synthetic coverage checks each positive threshold, mainboard-only
behavior, and higher-priority selection of Grixis, Agadeem, Esper, Rakdos, and
Asmo Persist for future hybrid lists. The focused R4 and documentation suite
now passes 43 tests.

The Owner assigned recurring family `modern-unknown-1309d5fb5ce4` a
`new_identity` disposition as the `golgari-delirium` parent, displayed as
`Golgari Delirium`, with no subtype. The reviewed Saga and Moonshadow builds
share 53 of 60 main-deck cards and the complete sideboard, so `Urza's Saga`
and its toolbox artifacts plus `Moonshadow` and `Street Wraith` remain
construction choices rather than subtype boundaries.

The accepted mainboard rule requires at least three `Nethergoyf`, three
`Omnivorous Flytrap`, three `Mishra's Bauble`, and two `Witherbloom Command`.
It also requires reviewed black and green mana sources while excluding
reviewed white, blue, and red main-deck mana sources. Existing explicit
identities retain higher priority.

A complete scan of 212 current Modern event files and 6,784 aggregated deck
records captures exactly the two reviewed records, both previously Unknown,
with no additional Golgari Delirium match. The frozen corpus maps the same two
Unknown records to the new parent, bringing the 5,792-record baseline to 5,733
classified and 59 Unknown records. The shadow now has 87 parents and 147 rules
with globally unique numeric priorities. Synthetic coverage checks every
positive threshold, mainboard-only behavior, both accepted construction
packages, required black-green sources, every excluded main-deck color, and
selection of the existing Rakdos Death's Shadow identity for a future hybrid.
The focused R4 and documentation suite now passes 44 tests.

The Owner assigned recurring family `modern-unknown-17c806aab0e8` a
`new_identity` disposition as the `bogles` parent, displayed as `Bogles`, with
no subtype and no color restriction. The accepted mainboard rule requires at
least three `Slippery Bogle`, three `Gladecover Scout`, and three `Ethereal
Armor`. These two hexproof creatures and the defining Aura payoff are
sufficient to identify the archetype.

`Daybreak Coronet` is explicitly not required. It, `Kor Spiritdancer`,
`Light-Paws`, `Rancor`, the Umbra mix, `Sheltered by Ghosts`, `Spirit Mantle`,
`Reprieve`, and the remaining Aura package remain construction choices.

A complete scan of 212 current Modern event files and 6,784 aggregated deck
records captures exactly the two reviewed records, both previously Unknown,
with no additional Bogles match. The frozen corpus maps one Unknown record to
the new parent, bringing the 5,792-record baseline to 5,734 classified and 58
Unknown records. The shadow now has 88 parents and 148 rules with globally
unique numeric priorities. Synthetic coverage checks all three thresholds,
mainboard-only behavior, both accepted construction packages, the absence of
`Daybreak Coronet`, color-agnostic behavior, and rejection of an Aura shell
that lacks both required hexproof creatures. The focused R4 and documentation
suite now passes 45 tests.

The Owner assigned recurring family `modern-unknown-1dc1d7391989` a
`new_identity` disposition that adds two separate color-bounded parents with
no subtypes: `temur-reclamation`, displayed as `Temur Reclamation`, and
`bant-reclamation`, displayed as `Bant Reclamation`. This also corrects the
three current Bant Reclamation records that the production baseline labels as
Chant Control / Azorius.

Both accepted rules require at least three main-deck `Wilderness Reclamation`
and reviewed main-deck mana sources for all three named colors. Temur excludes
reviewed white and black main-deck sources and actual spells in either deck or
sideboard; Bant similarly excludes reviewed red and black sources and spells.
`Growth Spiral`, `Galvanic Discharge`, `Traumatic Critique`, `Counterspell`,
`Consult the Star Charts`, `Orim's Chant`, `Planar Genesis`, Teferi, sweepers,
and other interaction or payoff packages remain construction choices.

The Reclamation parents outrank Izzet Wizards, Chant Control, and generic
control, while Omnath Midrange retains higher priority. Unsupported
four-color and other color-group Reclamation builds remain Unknown unless an
existing explicit identity applies.

A complete scan of 212 current Modern event files and 6,784 aggregated deck
records captures exactly the two reviewed Unknown records as Temur
Reclamation and moves exactly three Chant Control / Azorius records to Bant
Reclamation. The frozen corpus maps two Unknown records to Temur Reclamation
and two Chant Control / Azorius records to Bant Reclamation, bringing the
5,792-record baseline to 5,736 classified and 56 Unknown records. The shadow
now has 90 parents and 150 rules with globally unique numeric priorities.
Synthetic coverage checks the Reclamation threshold, all required and excluded
color sources, reviewed sideboard spell splashes, replaceable Temur and Bant
packages, Temur precedence over Izzet Wizards, Bant precedence over Chant
Control, Omnath Midrange precedence, and unsupported four-color and Sultai
fallbacks. The focused R4 and documentation suite now passes 46 tests.

The Owner assigned recurring family `modern-unknown-26c7d5185a8c` a
`map_existing` disposition to the new `landfall` subtype of the existing
`badgermole-combo` parent. This is a landfall branch of the same combo family,
not Maverick: it retains the reviewed Badgermole Cub, Green Sun's Zenith,
Quirion Ranger, Springheart Nantuko, and Ashaya engine while replacing the
Leyline support package with Icetill Explorer and landfall support.

The reviewed mainboard rule requires at least three `Badgermole Cub`, three
`Green Sun's Zenith`, two `Quirion Ranger`, three `Springheart Nantuko`, one
`Ashaya, Soul of the Wild`, and three `Icetill Explorer`. It explicitly
excludes `Leyline of Abundance` and `Vizier of Remedies`. `Earthbender
Ascension`, `Nature's Rhythm`, color splash, and other toolbox cards remain
construction choices. The existing Golgari and Mono-Green subtype IDs and
rules remain unchanged.

A complete scan of 212 current Modern event files and 6,784 aggregated deck
records captures exactly the two reviewed Unknown records, from separate
events, with no additional match or migration from an existing identity. The
frozen corpus likewise maps two Unknown records to Badgermole Combo / Landfall,
bringing the 5,792-record baseline to 5,738 classified and 54 Unknown records.
The shadow remains at 90 parents and now has 151 rules with globally unique
numeric priorities. Synthetic coverage checks every required threshold, both
explicit exclusions, and the separation from the existing Leyline and Devoted
Combo branches. The focused R4 and documentation suite now passes 46 tests.

The Owner assigned recurring family `modern-unknown-3effd912c863` a
`map_existing` disposition to the existing `jeskai-blink` parent. The two
records are ordinary Jeskai Blink builds with a reduced two-copy Phelia package,
not a separate construction path: both retain Quantum Riddler, Solitude, the
Jeskai mana base, and the same value-midrange plan, while carrying no Stoneforge
Mystic or equipment package.

The accepted shadow repair keeps the stable `jeskai-blink-primary` rule ID and
priority and changes only its mainboard `Phelia, Exuberant Shepherd` threshold
from three to two. The existing Quantum Riddler, Solitude, red-source,
Stoneforge Mystic, black-source, green-source, and Goryo's Vengeance boundaries
remain unchanged. Fable of the Mirror-Breaker, Ephemerate, Phlage, Ragavan,
Galvanic Discharge, Counterspell, and other value or interaction packages remain
construction choices rather than becoming a second rule path.

A complete scan of 212 current Modern event files and 6,784 aggregated deck
records captures exactly the two reviewed Unknown records, from separate
events, without migrating any existing identity. The frozen corpus likewise
maps two Unknown records to Jeskai Blink, bringing the 5,792-record baseline to
5,740 classified and 52 Unknown records. The shadow remains at 90 parents and
151 rules with globally unique IDs and numeric priorities. Synthetic coverage
checks the repaired Phelia threshold, the unchanged Riddler, Solitude, color,
Stoneforge, and Goryo boundaries, the absence of construction-package
requirements, and Jeskai Stoneforge precedence. The focused R4 and
documentation suite now passes 47 tests.

The Owner assigned recurring family `modern-unknown-6e45259d4cbc` a
`new_identity` disposition as the separate `mardu-vial` parent with no
subtype. The reviewed lists are not Mardu Energy: they omit Ocelot Pride and
do not use Energy as a shared resource engine. Guide of Souls and Ajani are
value creatures in an Aether Vial, Imperial Recruiter, and Chthonian Nightmare
toolbox and recursion plan rather than identity requirements.

The reviewed mainboard rule requires at least three `Aether Vial`, three
`Imperial Recruiter`, two `Chthonian Nightmare`, and three `Solitude`.
`Guide of Souls`, `Ajani, Nacatl Pariah`, `Galvanic Discharge`, `Emperor of
Bones`, `Phyrexian Tower`, `Seasoned Pyromancer`, and the remaining toolbox
cards are construction choices. The `mardu-vial-primary` priority is 686250,
below `mardu-energy-primary` at 687000 and `mardu-energy-nightmare` at 686500,
so a future hybrid satisfying a complete Energy signature remains Mardu
Energy.

A complete scan of 212 current Modern event files and 6,784 aggregated deck
records captures exactly the two reviewed Unknown records, from separate
events, without migrating an existing identity or adding a multiple match.
The frozen corpus likewise maps only its two corresponding Unknown records to
Mardu Vial, bringing the 5,792-record baseline to 5,742 classified and 50
Unknown records. The shadow now has 91 parents and 152 rules with globally
unique IDs and numeric priorities. Synthetic coverage checks every required
threshold, the mainboard-only zone, the optional construction packages, and
both existing Mardu Energy precedence paths. The focused R4 and documentation
suite now passes 48 tests.

The Owner assigned recurring family `modern-unknown-7098cf8e171a` a
`map_existing` disposition to the existing `agadeem-persist` parent with no
subtype. The two reduced-Crypt lists retain the Eyetwitch, Stitcher's Supplier,
Phyrexian Tower, Persist, and Archon of Cruelty game plan of the established
Agadeem lists; replacing three Crypt of Agadeem and Street Wraith slots with
additional lands and interaction does not create a separate BG Persist or
Black Lessons identity.

The existing `agadeem-persist-primary` rule and its three-Crypt threshold
remain unchanged. A mutually exclusive `agadeem-persist-reduced-crypt` path
requires at least three main-deck `Persist`, three `Archon of Cruelty`, three
`Eyetwitch`, three `Stitcher's Supplier`, three `Phyrexian Tower`, and one or
two `Crypt of Agadeem`. `Emperor of Bones`, `Overlord of the Balemurk`, `Street
Wraith`, interaction, and the green splash remain construction choices. The
supplemental rule priority is 639400, below Grixis, the original Agadeem path,
Esper, Asmo, Rakdos, and Sultai Persist, so every established explicit Persist
identity retains precedence for a future hybrid.

A complete scan of 212 current Modern event files and 6,784 aggregated deck
records captures exactly the two reviewed Unknown records, from separate
events, without migrating an existing identity or adding a multiple match. The
19 current Agadeem Persist records selected by the original rule remain on that
rule. The frozen corpus likewise maps only the two corresponding Unknown
records to Agadeem Persist, bringing the 5,792-record baseline to 5,744
classified and 48 Unknown records. The shadow remains at 91 parents and now has
153 rules with globally unique IDs and numeric priorities. Synthetic coverage
checks every lower and upper threshold, the mainboard-only boundary, optional
construction packages, mutual exclusion from the original path, and precedence
for every established Persist identity. The focused R4 and documentation suite
now passes 49 tests.

The Owner assigned recurring family `modern-unknown-724659bc0555` a
`map_existing` disposition to the existing `jeskai-energy` parent with no
subtype. Both lists retain the Guide of Souls, Ocelot Pride, Ajani, and red
Energy shell while using one or two main-deck Quantum Riddler plus reviewed
blue mana sources. They are neither Boros Energy nor Jeskai Blink, and reduced
Riddler count does not create a separate Jeskai Ocelot identity.

The accepted shadow repair keeps the stable `jeskai-energy-primary` rule ID and
priority. It retains at least three main-deck `Ajani, Nacatl Pariah` and three
`Guide of Souls`, adds at least three `Ocelot Pride` and one reviewed main-deck
red mana source, and lowers `Quantum Riddler` from three copies to one. Ocelot
preserves the accepted Guide-plus-Ocelot Energy identity, while the red source
and main-deck Riddler establish Jeskai rather than Azorius or Boros.
`Galvanic Discharge`, Ragavan, Goblin Bombardment, Phlage, Fable, Mockingbird,
Ranger-Captain, Solitude, Phelia, and other value or interaction cards remain
construction choices.

A complete scan of 212 current Modern event files and 6,784 aggregated deck
records captures exactly the two reviewed Unknown records, from separate
events, without migrating an existing identity or adding a multiple match. The
27 current Jeskai Energy records already selected by the original rule and all
928 Boros Energy records remain on their existing identities. The frozen corpus
likewise maps only the two corresponding Unknown records to Jeskai Energy,
bringing the 5,792-record baseline to 5,746 classified and 46 Unknown records.
The shadow remains at 91 parents and 153 rules with globally unique IDs and
numeric priorities. Synthetic coverage checks every positive threshold, the
mainboard-only Riddler boundary, the reviewed red-source requirement, optional
red construction packages, Boros and Azorius separation, and Mardu Energy
precedence. The focused R4 and documentation suite now passes 50 tests.

The Owner assigned recurring family `modern-unknown-77bb2b4214a3` a
`new_identity` disposition as a separate `gruul-midrange` parent with no
subtype. Both lists use the same accelerated Blood Moon and Karn toolbox plan;
their single main-deck `Pillage` does not make land destruction the defining
Ponza identity, and they do not contain the accepted Aspect/Troll core of
Mono-Green Stompy.

The accepted shadow rule requires at least three main-deck `Karn, the Great
Creator`, three `Blood Moon`, and three `Utopia Sprawl`. `Fanatic of Rhonas`,
`Malevolent Rumble`, Endurance, Arbor Elf, Vibrance, Fable, Pillage, removal,
and the Karn wishboard remain construction choices so both the current build
and historical threat packages retain the same parent. The new parent and
primary rule use globally unique priority 660500, between Boros Ponza and
Oculus Ritual.

A complete scan of 212 current Modern event files and 6,784 aggregated deck
records captures exactly the two reviewed Unknown records, from separate
events, without migrating an existing identity or adding a multiple match. The
current shadow therefore reaches 6,728 classified and 56 Unknown records. The
frozen corpus likewise maps only the two corresponding Unknown records to
Gruul Midrange, bringing the 5,792-record baseline to 5,748 classified and 44
Unknown records. The shadow now has 92 parents and 154 rules with globally
unique IDs and numeric priorities. Synthetic coverage checks every positive
threshold, mainboard-only behavior, and both historical and current optional
construction packages. The focused R4 and documentation suite now passes 51
tests.

The Owner assigned recurring family `modern-unknown-8f8d03c40bec` a
`new_identity` disposition as a separate `mono-blue-namor` parent with no
subtype. The two counterspell shells use Namor as their defining threat but do
not contain the traditional Lord of Atlantis Merfolk core and are not
Goblin Charbelcher decks.

The accepted rule requires at least three main-deck `Namor the Sub-Mariner`
and three `Archmage's Charm`, excludes `Lord of Atlantis` and `Goblin
Charbelcher`, and excludes reviewed white, black, red, and green main-deck
mana sources and reviewed off-color spells in either zone. Disrupting Shoal,
Force of Negation, Vodalian Hexcatcher, Svyelun, Spreading Seas, and Harbinger
of the Seas remain construction choices. Phyrexian-neutral cards do not create
a splash. The new parent and primary rule use globally unique priority 622500,
above the existing Izzet Wizards rule.

A complete scan of 212 current Modern event files and 6,784 aggregated deck
records captures exactly the two reviewed Unknown records without migrating
an existing identity or adding a multiple match. The current shadow reaches
6,730 classified and 54 Unknown records. One corresponding frozen record maps
to Mono-Blue Namor, bringing the 5,792-record baseline to 5,749 classified and
43 Unknown records. The shadow has 93 parents and 155 rules with globally
unique IDs and numeric priorities. Synthetic coverage checks both positive
thresholds, the Merfolk and Belcher precedence boundaries, reviewed off-color
sources and spells, and the Phyrexian-mana exception. The focused R4 and
documentation suite passes 52 tests.

The Owner assigned recurring family `modern-unknown-c64dc8e87f67` a
`new_identity` disposition as a separate `golgari-goryos` parent with no
subtype. Both lists use `Dina's Guidance` and `Formidable Speaker` to support a
black-green Goryo's Vengeance graveyard plan. They are neither Esper Persist
nor a generic Golgari Persist identity, and the existing color-specific
Goryo's parents remain separate.

The accepted rule requires at least three main-deck `Goryo's Vengeance`, three
`Dina's Guidance`, and three `Formidable Speaker`, requires reviewed black and
green main-deck mana sources, and excludes reviewed white, blue, and red
main-deck mana sources. `Persist`, `Unmarked Grave`, `Shifting Woodland`,
`Archon of Cruelty`, and individual legendary targets remain construction
choices. The new parent and primary rule use globally unique priority 641150,
between Esper and Grixis Goryo's.

A complete scan of all 6,784 current Modern decks captures exactly the two
reviewed Unknown records, without migrating an existing identity or adding a
multiple match. The current shadow reaches 6,732 classified and 52 Unknown
records. The frozen corpus likewise maps only its two corresponding Unknown
records to Golgari Goryo's, bringing the 5,792-record baseline to 5,751
classified and 41 Unknown records. The shadow now has 94 parents and 156 rules
with globally unique IDs and numeric priorities. Synthetic coverage checks all
three positive thresholds, black-green source requirements, white-blue-red
source exclusions, mainboard-only behavior, optional Persist and Woodland
packages, and existing Esper Goryo's precedence. The focused R4 and
documentation suite passes 53 tests.

Continue with the next ranked pending family `modern-unknown-cdcb142b2233`.
Do not promote any proposal into production, commit, publish, rerun the Landing
shadow, or begin P12-10.

The Owner assigned recurring cross-source family
`modern-unknown-cdcb142b2233` a `map_existing` disposition to the existing
`Prowess / Izzet` identity. Both lists retain the Cutter, Lava Dart, Bolt,
Bauble, Preordain, and Stormchaser's Talent spell-velocity plan; one replaces
Dragon's Rage Channeler with Soul-Scar Mage, while the other reduces
Monastery Swiftspear to two copies. Neither list contains the Emry engine of
the separate Izzet Steel-Cutter parent.

The accepted repair keeps the stable `prowess-izzet` rule ID and priority
672200. It continues to require at least three main-deck `Cori-Steel Cutter`
and `Lava Dart` plus two `Preordain`, reduces `Monastery Swiftspear` from three
copies to two, removes the `Dragon's Rage Channeler` requirement, and retains
the reviewed white, black, and green spell exclusions in either zone. DRC,
Soul-Scar Mage, Slickshot, Stormchaser's Talent, Boomerang Basics, Expressive
Iteration, and Experimental Synthesizer remain construction choices. The
higher-priority Lessons subtype and Emry-based Izzet Steel-Cutter rule remain
unchanged.

A complete scan of all 6,784 current MTGO Modern decks adds only the reviewed
MTGO record, bringing the current shadow to 6,733 classified and 51 Unknown
records without a multiple match. The 5,792-record frozen corpus likewise adds
only its corresponding record, reaching 5,752 classified and 40 Unknown. A
full replay of all 362 Tabletop decklists preserves every existing Prowess
identity and maps only the reviewed Tabletop Unknown record to Prowess/Izzet.
Across the complete 188-record Modern owner-review input, only the two reviewed
family members are newly captured. The shadow remains at 94 parents and 156
rules with globally unique IDs and numeric priorities. Synthetic coverage
checks every positive threshold, mainboard-only behavior, both threat
packages, off-color subtype routing, and Lessons and Steel-Cutter precedence.
The focused R4 and documentation suite passes 55 tests.

Continue with the next ranked pending family `modern-unknown-d000dbc93b85`.
Do not promote any proposal into production, commit, publish, rerun the Landing
shadow, or begin P12-10.

The Owner assigned recurring family `modern-unknown-d000dbc93b85` a
`new_identity` disposition as a separate `solemnity-prison` parent with no
subtype. The reviewed lists use Solemnity with Nine Lives and Phyrexian Unlife
as their damage-prevention lock. Their light blue splash does not change that
game-plan identity, while the color-neutral parent avoids forcing current and
historical Naya or four-color constructions into separate identities.

The accepted shadow adds two mutually exclusive mainboard paths. The first
requires at least three `Solemnity` and three `Nine Lives`. The second requires
at least three `Solemnity` and three `Phyrexian Unlife` while capping `Nine
Lives` at two. This preserves the reviewed Nine Lives build and the evidenced
Unlife-only construction without allowing both rules to match one list.
`United Battlefront`, `Greater Auramancy`, `Sterling Grove`, `Solitary
Confinement`, and color sources remain construction choices. No speculative
`Luminous Broodmoth` or `Enduring Ideal` exclusion is added; the current
Broodmoth/Solemnity singleton naturally misses both partner-card paths. The
parent and rules use globally unique priorities 673700 and 673600.

A complete scan of all 6,784 current MTGO Modern decks captures exactly the
two reviewed Unknown records, from separate events, bringing the current
shadow to 6,735 classified and 49 Unknown without a multiple match. The
5,792-record frozen corpus likewise maps only `modern-baseline-0932` and
`modern-baseline-1029`, reaching 5,754 classified and 38 Unknown. Across the
complete 188-record Modern owner-review input, only the two reviewed family
members are captured, and all 362 Tabletop event 434455 decklists retain their
existing identities. The shadow now has 95 parents and 158 rules with globally
unique IDs and numeric priorities. Synthetic coverage checks both positive
paths, every threshold, mainboard-only behavior, optional assembler and
protection cards, mutual exclusivity, and the Broodmoth boundary. The focused
R4 and documentation suite passes 56 tests.

Continue with the next ranked pending family `modern-unknown-d8545120ffef`.
Do not promote any proposal into production, commit, publish, rerun the Landing
shadow, or begin P12-10.

The Owner assigned recurring family `modern-unknown-d8545120ffef` a
`new_identity` disposition as a separate `mono-green-trudge` parent with no
subtype rather than Fight Rigging or Badgermole Combo. The reviewed lists use
Slumbering Trudge to enable The Great Henge as their primary card-advantage
engine, while Fanatic of Rhonas supplies burst mana and the Badgermole,
Ashaya, Quirion Ranger, and Springheart Nantuko package supplies an optional
combo finish.

The accepted mainboard rule requires at least three `Slumbering Trudge` and
three `The Great Henge`, permits at most two `Fight Rigging`, and excludes the
reviewed white, blue, black, and red main-deck mana-source features. This keeps
three-or-more-Rigging constructions in the existing Fight Rigging identity and
leaves future true splashes Unknown pending review. `Badgermole Cub`, `Fanatic
of Rhonas`, `Life's Legacy`, `Ouroboroid`, `Green Sun's Zenith`, `Ashaya, Soul
of the Wild`, `Quirion Ranger`, `Springheart Nantuko`, `Summoner's Pact`, and
`Craterhoof Behemoth` remain construction choices. The new parent and primary
rule use globally unique priority 641050 between Grixis Goryo's and Fight
Rigging.

A complete scan of all 6,784 current MTGO Modern decks captures exactly the
two reviewed Unknown records, from separate events, bringing the current
shadow to 6,737 classified and 47 Unknown without a multiple match. Of the 96
current lists with at least three Slumbering Trudge, the other 94 remain Fight
Rigging and none contains three The Great Henge. The 5,792-record frozen
corpus likewise maps only `modern-baseline-2919` and `modern-baseline-3126`,
reaching 5,756 classified and 36 Unknown. Across the complete 188-record
Modern owner-review input, only the two reviewed family members are captured,
and all 362 Tabletop event 434455 decklists retain their existing identities.
The shadow now has 96 parents and 159 rules with globally unique IDs and
numeric priorities. Synthetic coverage checks both positive thresholds,
mainboard-only behavior, optional construction packages, the two-versus-three
Fight Rigging boundary, four off-color source exclusions, and Tabletop. The
focused R4 and documentation suite passes 57 tests.

Continue with the next ranked pending family `modern-unknown-e8a1b553a175`.
Do not promote any proposal into production, commit, publish, rerun the Landing
shadow, or begin P12-10.

The Owner assigned recurring family `modern-unknown-e8a1b553a175` a
`new_identity` disposition as a separate `grixis-tempo` parent rather than a
second path under the existing Dimir Tempo red-splash subtype. Both reviewed
lists use four `Ragavan, Nimble Pilferer` alongside four `Psychic Frog`, four
`Fatal Push`, `Watery Grave`, and `Steam Vents`, while omitting Counterspell.
The proactive one-drop plan is materially different from a Counterspell-based
Dimir shell that adds red chiefly for cards such as Meltdown, Fire Magic, or
Flame of Anor.

The current 6,784-deck MTGO scan contains 47 lists selected by the existing
`dimir-tempo-grixis` rule. Forty-five remain Counterspell-based red splashes;
two already use at least three Ragavan together with the reviewed Frog and
red-source core. The accepted shadow therefore adds a separate
`grixis-tempo-ragavan` rule requiring at least three main-deck `Fatal Push`,
`Psychic Frog`, and Ragavan plus at least one `Watery Grave` and `Steam Vents`.
It excludes `Goryo's Vengeance`, `Persist`, `Death's Shadow`, and reviewed
white or green main-deck mana sources. Counterspell is deliberately not
constrained, so the zero-Counterspell Riddler build and the three-Counterspell
DRC build remain one proactive Grixis identity.

The stable `dimir-tempo-grixis` rule ID and existing internal `grixis` and
`esper` subtype IDs remain intact. Their visible names become `Dimir Red
Splash` and `Dimir White Splash`, and the red-splash rule permits at most two
Ragavan. This makes the two identities mutually exclusive without changing
the production rule file or semantic-feature manifest.

A complete scan classifies exactly the two reviewed Unknown records and
migrates exactly two already classified current records from
`dimir-tempo/grixis` to `grixis-tempo`, with one rule match per record. Current
MTGO status becomes 6,739 classified and 45 Unknown. The 5,792-record frozen
corpus remains 5,756 classified and 36 Unknown, with exactly one reviewed
`dimir-tempo/grixis -> grixis-tempo` migration. No other record in the
188-record Modern owner-review input is captured, and all 362 Tabletop event
434455 decklists retain their existing identities. The shadow now has 97
parents and 160 rules with globally unique IDs and numeric priorities.
Synthetic coverage checks every positive threshold, both zero and four
Counterspell, both reviewed construction packages, all explicit engine and
off-color exclusions, mainboard-only behavior, splash labels, mutual
exclusivity, and Tabletop. The focused R4 shadow suite passes 40 tests.

The Owner assigned singleton family `modern-unknown-014e15a41666` a
`map_existing` disposition to the existing `Soultrader` parent with a new
`orzhov / Orzhov` subtype. The reviewed list contains the complete Warren
Soultrader, Gravecrawler, and Marionette Apprentice combo core with Godless
Shrine, while Guide of Souls, Ocelot Pride, Knight-Errant of Eos, and
Chthonian Nightmare supply a white-black creature shell. Its identity is the
Soultrader combo rather than Mardu Energy, and it does not justify a separate
parent.

The accepted shadow adds `soultrader-orzhov` at priority 687100, above Mardu
Energy. It requires at least three main-deck `Warren Soultrader`,
`Gravecrawler`, and `Marionette Apprentice` plus one main-deck `Godless
Shrine`. It excludes reviewed blue, green, and red main-deck mana sources and
reviewed off-color spells in either zone. `Guide of Souls`, `Ocelot Pride`,
`Ajani, Nacatl Pariah`, `Knight-Errant of Eos`, `Chthonian Nightmare`,
`Orcish Bowmasters`, `Sephiroth, Fabled SOLDIER`, and `Overlord of the
Balemurk` remain construction choices. A synthetic Energy hybrid deliberately
matches both rules, with Soultrader winning by priority.

A complete scan of all 6,784 current MTGO Modern decks captures exactly the
reviewed Unknown record and migrates no classified record, bringing the
current shadow to 6,740 classified and 44 Unknown. The 5,792-record frozen
corpus likewise maps only `modern-baseline-4703`, reaching 5,757 classified
and 35 Unknown. No other record in the 188-record Modern owner-review input is
captured, and all 362 Tabletop event 434455 decklists retain their existing
identities. The shadow remains at 97 parents and now has 161 rules with
globally unique IDs and numeric priorities. Synthetic coverage checks every
positive threshold, mainboard-only behavior, optional construction cards,
Energy precedence, all reviewed off-color exclusions, and Tabletop. The
focused R4 shadow suite passes 41 tests.

The Owner assigned singleton family `modern-unknown-0b995bbade03` a
`new_identity` disposition as a separate `grixis-dress-down` parent with no
subtype rather than broad Grixis Control or Dimir Tempo's red-splash subtype.
The reviewed list uses four each of Dress Down, Nulldrifter, and Kroxa, Titan
of Death's Hunger as its engine and threats while omitting Counterspell,
Psychic Frog, Orcish Bowmasters, and Ragavan. This materially differs from the
existing Counterspell-based Dimir Red Splash and proactive Grixis Tempo
identities.

The accepted mainboard rule requires at least three `Dress Down`,
`Nulldrifter`, and `Kroxa, Titan of Death's Hunger` plus one `Steam Vents` and
`Watery Grave`. It excludes `Goryo's Vengeance`, `Persist`, `Death's Shadow`,
reviewed white and green main-deck mana sources, and reviewed white and green
spells in either zone. `Fatal Push`, `Consign to Memory`, `Traumatic Critique`,
`Force of Negation`, and `Consult the Star Charts` remain construction
choices. Priority 638050 places the identity below Grixis Tempo and above
Dimir Tempo's red splash. Four-color Dress Down remains Unknown pending
separate local evidence.

A complete scan of all 6,784 current MTGO Modern decks captures exactly the
reviewed Unknown record and migrates no classified record, bringing the
current shadow to 6,741 classified and 43 Unknown. The other current list with
at least three Dress Down and Nulldrifter lacks Kroxa and remains Izzet Through
the Breach. The 5,792-record frozen corpus remains at 5,757 classified and 35
Unknown, with no Grixis Dress Down match. No other record in the 188-record
Modern owner-review input is captured, and all 362 Tabletop event 434455
decklists retain their existing identities. The shadow now has 98 parents and
162 rules with globally unique IDs and numeric priorities. Synthetic coverage
checks every positive threshold, mainboard-only behavior, optional
construction cards, priority against both neighboring tempo identities,
explicit engine exclusions, white and green source and spell exclusions,
four-color boundaries, and Tabletop. The focused R4 shadow suite passes 42
tests.

The Owner assigned singleton family `modern-unknown-157abe8132a0` a
`map_existing` disposition to the existing `grixis-goryos` parent with no new
subtype. The reviewed list retains four each of `Atraxa, Grand Unifier`,
`Faithless Looting`, and `Psychic Frog` and three `Emperor of Bones`, but uses
only one `Goryo's Vengeance`. Its engine and target package are the same as
the established Grixis Goryo's lists; Emperor supplies the supplemental
reanimation path rather than establishing a separate identity.

The accepted shadow preserves `grixis-goryos-primary` unchanged and adds the
mutually exclusive `grixis-goryos-emperor` path at priority 641090. The new
mainboard path requires one or two `Goryo's Vengeance` and at least three each
of `Emperor of Bones`, `Atraxa, Grand Unifier`, `Faithless Looting`, and
`Psychic Frog`; it excludes `Ephemerate` and `Persist`. Three or more Goryo's
continue through the original priority-641100 primary, while a zero-Goryo's
Emperor build remains Unknown pending separate evidence. `Griselbrand`, `Sin,
Spira's Punishment`, `Thoughtseize`, `Force of Negation`, `Consign to Memory`,
`Tainted Indulgence`, `Bitter Triumph`, and other discard outlets remain
construction choices.

A complete scan of all 6,784 current MTGO Modern decks captures exactly the
reviewed Unknown record and migrates no classified record, bringing the
current shadow to 6,742 classified and 42 Unknown. All 14 current lists that
satisfy the original Grixis Goryo's primary remain selected by that rule
without an additional match. The 5,792-record frozen corpus maps only
`modern-baseline-3801` through the new path, reaching 5,758 classified and 34
Unknown. No other record in the 188-record Modern owner-review input is
captured, and all 362 Tabletop event 434455 decklists retain their existing
identities. The shadow remains at 98 parents and now has 163 rules with
globally unique IDs and numeric priorities. Synthetic coverage checks both
low-Goryo's counts, the zero/three-copy boundaries, every positive threshold,
the unchanged original primary, mainboard-only behavior, optional construction
cards, the Ephemerate and Persist exclusions, and Tabletop. The focused R4
shadow suite passes 43 tests.

The Owner assigned singleton family `modern-unknown-174b94f4f2e0` a
`new_identity` disposition as a separate `mono-white-humans` parent with no
subtype. The later `modern-unknown-c588af306ed2` Five-Color Humans family will
receive a different parent and remains pending at its own queue position. The
two lists share 27 of 60 main-deck card slots, but 33 slots differ; their
sideboards share only two of 15 slots. Their common Vial, Champion, Lieutenant,
Guide, Adeline, and Cavern skeleton therefore does not override the materially
different mono-white and rainbow tribal packages.

The accepted mainboard rule requires at least three `Aether Vial`, `Champion
of the Parish`, `Thalia's Lieutenant`, and `Coppercoat Vanguard` plus at least
five `Plains`. It excludes `Ocelot Pride`, reviewed blue, black, red, and green
main-deck mana sources, and reviewed off-color spells in either zone. `Adeline,
Resplendent Cathar`, `Guide of Souls`, `Esper Sentinel`, `Ranger-Captain of
Eos`, `Voice of Victory`, and `Witch Enchanter` remain construction choices.
Priority 683500 is globally unique and leaves a complete Guide-plus-Ocelot
Energy hybrid to the existing Energy rules.

A complete scan of all 6,784 current MTGO Modern decks captures exactly the
reviewed Unknown record and migrates no classified record, bringing the
current shadow to 6,743 classified and 41 Unknown. The observed Five-Color
Humans record remains Unknown because it has no Coppercoat Vanguard and only
two Plains. The 5,792-record frozen corpus maps only
`modern-baseline-2386`, reaching 5,759 classified and 33 Unknown. No other
record in the 188-record Modern owner-review input is captured, and all 362
Tabletop event 434455 decklists remain outside the new identity. The shadow
now has 99 parents and 164 rules with globally unique IDs and numeric
priorities. Synthetic coverage checks every positive threshold, mainboard-only
behavior, optional construction cards, all reviewed off-color exclusions, the
Guide-plus-Ocelot Energy boundary, the observed Five-Color Humans boundary,
and Tabletop. The focused R4 shadow suite passes 44 tests.

The Owner assigned singleton family `modern-unknown-1926eb946776` a
`new_identity` disposition as a separate `gruul-cragganwick` parent with no
subtype. The official Magic.gg April 16, 2026 Metagame Mentor article names an
almost identical April 5 RCQ Top 8 list "Gruul Cragganwick" and describes its
primary line as ramping into `Cragganwick Cremator` while holding `Yargle and
Multani` to deal 18 damage. The repository sample differs only in fetch-land
distribution and one sideboard slot. Its `Monstrous Emergence` plus `Screaming
Nemesis` line is a fallback rather than a separate identity.

The accepted mainboard rule requires at least three `Cragganwick Cremator`,
`Yargle and Multani`, `Badgermole Cub`, and `Blood Moon` plus reviewed red and
green mana sources. It excludes reviewed white, blue, and black main-deck mana
sources, `Goryo's Vengeance`, and `Emrakul, the Aeons Torn`. `Formidable
Speaker`, `Monstrous Emergence`, `Screaming Nemesis`, `The Underworld Cookbook`,
and `Urza's Saga` remain construction choices. No generic black-spell exclusion
is added because Yargle is the combo payload despite its black mana symbol.
Priority 641310 is globally unique and sits immediately above the existing
priority-641300 `cremator-goryos-primary` rule.

A complete scan of all 6,784 current MTGO Modern decks finds five lists with
`Cragganwick Cremator` or `Yargle and Multani`: exactly the reviewed Unknown
record satisfies the new rule, while all four existing Cremator Goryo's lists
retain `Goryo's Vengeance` and `Emrakul, the Aeons Torn` and remain unchanged.
The reviewed list and a representative Cremator Goryo's list share only seven
of 24/23 unique main-deck cards and have a quantity-weighted Jaccard similarity
of 0.20. The current shadow reaches 6,744 classified and 40 Unknown. The
5,792-record frozen corpus maps only `modern-baseline-0212`, reaching 5,760
classified and 32 Unknown. No other record in the 188-record Modern owner-review
input is captured, and all 362 Tabletop event 434455 decklists remain outside
the new identity. The shadow now has 100 parents and 165 rules with globally
unique IDs and numeric priorities. Synthetic coverage checks every positive
threshold, mainboard-only behavior, optional construction cards, reviewed
off-color mana-source exclusions, the Goryo's and Emrakul boundaries, Cremator
Goryo's precedence, and Tabletop. The focused R4 shadow suite passes 45 tests.

Continue with the next ranked pending family `modern-unknown-251a8dc88b65`.
Do not promote any proposal into production, commit, publish, rerun the Landing
shadow, or begin P12-10.

The Owner expanded singleton family `modern-unknown-251a8dc88b65` into an
immediate full Hammer Time shadow refactor and jointly accepted the later
singleton `modern-unknown-745246ddeb2a` ahead of its queue position. Both map
to the existing `hammer-time` parent and specifically to its new `jeskai`
subtype. The parent retains stable `azorius` and `mono-white` subtype and rule
IDs and gains explicit `boros` and `jeskai` subtypes.

The reviewed traditional core is at least three main-deck `Colossus Hammer`
and `Puresteel Paladin`. It no longer requires `Metallic Rebuke` or
`Stoneforge Mystic`. The mutually exclusive Kellan path requires at least
three `Colossus Hammer`, three `Kellan, the Fae-Blooded`, and two
`Super-Soldier Serum` while permitting at most two `Puresteel Paladin`.
`Metallic Rebuke`, `Stoneforge Mystic`, `Sigarda's Aid`, `Leyline Axe`,
`Battlefield Improvisation`, Mox Opal, Ornithopter, and Urza's Saga remain
construction choices.

Subtype routing uses the accepted reviewed semantic manifest rather than one
named dual land. White, blue, and red main-deck mana sources plus colored
spells in either zone distinguish Mono-White, Azorius, Boros, and Jeskai. Two
mutually exclusive Jeskai paths cover a reviewed red main-deck source or, when
no reviewed red source exists, a red spell in either zone. This preserves the
project's main-and-sideboard splash policy: the traditional family with
Hallowed Fountain and sideboard `Wear/Tear` is Jeskai, as are the Kellan list
and the existing list with Sacred Foundry. Reviewed black or green sources and
spells remain outside all Hammer paths.

A complete replay of all 6,784 current MTGO Modern decks selects exactly 23
Hammer Time lists: 17 Azorius, three Jeskai, two Boros, and one Mono-White.
Both reviewed Unknown records become Jeskai, bringing the current shadow to
6,746 classified and 38 Unknown. Two already classified Mono-White records
with red cards move to Boros, and one Azorius record with Sacred Foundry moves
to Jeskai. Every Hammer record has exactly one Hammer rule match; every other
current identity remains unchanged by this refactor.

The 5,792-record frozen corpus selects exactly 21 Hammer lists: 16 Azorius,
two Jeskai, two Boros, and one Mono-White. One frozen Unknown becomes Jeskai,
two Mono-White records move to Boros, and one Azorius record moves to Jeskai,
bringing the frozen shadow to 5,761 classified and 31 Unknown. All 362
Tabletop event 434455 decklists retain their prior identities and none matches
Hammer Time. The shadow remains at 100 parents and now has 169 rules with
globally unique IDs and priorities. Synthetic coverage checks all six paths,
positive thresholds, mainboard-only core behavior, construction-card freedom,
Kellan/Puresteel exclusivity, sideboard splash routing, black and green
boundaries, and Tabletop. The focused R4 shadow suite passes 46 tests.

Continue with the next ranked pending family `modern-unknown-2726cf0be0bf`.
Do not promote any proposal into production, commit, publish, rerun the Landing
shadow, or begin P12-10.

The Owner accepted singleton family `modern-unknown-2726cf0be0bf` as a new
`izzet-twin` parent with no subtype. Its reviewed mainboard rule requires at
least two `Splinter Twin`, at least three `Fear of Missing Out`, and reviewed
blue and red mana sources. Reviewed white, black, and green main-deck mana
sources and spells in either zone are excluded so a future off-color Twin list
returns to Unknown for explicit review.

`Flow State`, Mishra's Bauble, `Tamiyo, Inquisitive Student`, `Expressive
Iteration`, `Force of Negation`, and the remaining interaction package remain
construction choices. No speculative `Deceiver Exarch` or `Pestermite` path is
added because none of the reviewed current, frozen, or Tabletop records contains
a traditional Twin sample.

A complete replay of all 6,784 current MTGO Modern decks selects exactly one
Izzet Twin list, the reviewed family record from event 12841352. It moves from
Unknown to Izzet Twin, bringing the current shadow to 6,747 classified and 37
Unknown; no other current identity changes. The corresponding frozen record
`modern-baseline-0807` also moves from Unknown to Izzet Twin, bringing the
5,792-record frozen shadow to 5,762 classified and 30 Unknown. All 362 Tabletop
event 434455 decklists retain their prior identities and none matches Izzet
Twin. The shadow now has 101 parents and 170 rules with globally unique IDs and
priorities. Synthetic coverage checks both positive thresholds, mainboard-only
core behavior, optional shell cards, main-deck mana boundaries, sideboard spell
splashes, absence of speculative traditional paths, the frozen corpus, and
Tabletop. The focused R4 shadow suite passes 47 tests.

Continue with the next ranked pending family `modern-unknown-28864e4b6383`.
Do not promote any proposal into production, commit, publish, rerun the Landing
shadow, or begin P12-10.

## Owner bulk preclassification protocol for the remaining Modern singletons

Before reviewing rank 45, the Owner changed the handling method for the
remaining Modern queue. The queue snapshot contains exactly 38 pending Modern
families and 38 records, all singletons: 37 MTGO records and one registered
Tabletop record. Rather than continuing one family at a time, these records are
now supplied together in the editable workbook
`R4_Modern_38_singleton_owner_preclassification.xlsx`. Its immutable evidence
is tied to queue SHA-256
`cd94cbf4b2a6e369e19334e56612069d1945f211525ee698200217bd3ecf2c2b`; the
unmodified workbook baseline has SHA-256
`4b3c4fcf20e5fcf63dc1861ce921d79ddec16c1886cb3e6d4e2955f15c6d370b`.

The Owner will preclassify each record with a parent, optional subtype, and key
cards, and will explicitly mark records that require joint discussion or should
remain Unknown. This workbook is an internal diagnostic input only. Its entries
do not become rules automatically and do not authorize production edits,
commit, publication, merge, or P12-10.

When the completed workbook returns, first verify the workbook structure, all
38 Family/Record ID pairs, and the immutable queue hash. Review the records
marked for discussion first. Then confirm every proposed classification against
the full decklist, existing rules, conflicts, priority, the current/frozen
Modern corpora, and the registered Tabletop corpus before writing any
Owner-accepted shadow rule. Preserve Unknown for unresolved or unsupported
records.

This change is Modern-specific. The current Standard queue still contains 59
families and 117 records, including multi-record clusters, so Standard will
continue to begin with the existing cluster-first review method. No Standard
review is started by this protocol change.

## Owner bulk preclassification batch 1

The Owner authorized the first workbook-derived batch of nine Modern
singletons for local R4 shadow evaluation. Eight records are current MTGO
Unknowns and one is the registered Tabletop event 434455 Unknown. No network
research was used. The returned workbook supplied the intended identities and
key-card direction; implementation then checked existing-rule overlap,
priority, and corpus effects before recording each disposition as
`owner_accepted` and `map_existing`.

The batch adds nine shadow-only rules and one subtype without adding a parent:

- `deaths-shadow-grixis-frog` maps the Tabletop Psychic Frog build to
  `deaths-shadow/grixis`, with the established Stubborn Denial path kept
  mutually exclusive;
- `five-color-ritual-omnath` keeps the Four-Color Ritual value build under the
  stable `five-color-ritual` identity and separates it from the Hellkite path;
- `boros-land-destruction-boom-wildfire` and
  `boros-land-destruction-boom-classic` cover the reviewed Wildfire and
  Stone Rain/Pillage Boros Ponza builds;
- `grixis-persist-wizards` covers the reviewed Trainer, Critique, and Tamiyo
  Grixis Persist build while excluding Goryo's Vengeance;
- `grixis-tempo-bowmasters`, `grixis-tempo-counterspell`, and
  `grixis-tempo-drc-frog` cover the three reviewed Grixis Tempo structures,
  retain the existing parent, and exclude reanimation, Death's Shadow, and
  reviewed white or green main-deck mana sources; and
- `prowess-rakdos` adds the `rakdos` subtype to Prowess, requires the Cutter,
  Lava Dart, DRC, Swiftspear, Blood Crypt, and black-spell structure, and
  excludes Nethergoyf and off-color spells so Rakdos Steel-Cutter, Mardu, and
  Grixis remain separate.

A complete replay of all 6,784 current MTGO Modern decks selects exactly the
eight intended MTGO records, all previously Unknown: one Grixis Persist, three
Grixis Tempo, two Boros Ponza, one Rakdos Prowess, and one Five-Color Ritual.
The current shadow therefore moves from 6,747 classified and 37 Unknown to
6,755 classified and 29 Unknown. No previously classified MTGO record changes
identity, every selected batch rule has exactly one match, and no other current
record selects a batch rule.

The 5,792-record frozen corpus changes exactly seven corresponding Unknown
records: one Grixis Persist, two Grixis Tempo, two Boros Ponza, one Rakdos
Prowess, and one Five-Color Ritual. It moves from 5,762 classified and 30
Unknown to 5,769 classified and 23 Unknown. No frozen classified identity
migrates and reordered-rule evaluation produces the same identities.

Against all 362 registered Tabletop event 434455 decklists, the only change
from the pre-batch R4 shadow is deck index 279 moving from Unknown to
`deaths-shadow/grixis` through `deaths-shadow-grixis-frog`. Every other
Tabletop identity is unchanged. The shadow remains at 101 parents and now has
179 rules with globally unique IDs and priorities. Synthetic coverage checks
all nine positive paths, the Stubborn Denial and Hellkite handoffs, reanimation
and color boundaries, the Grixis Tempo maximum-count boundaries, and the
Rakdos Steel-Cutter handoff. The focused R4 shadow suite passes 48 tests.

Stop before owner bulk preclassification batch 2. Do not promote any proposal
into production, commit, publish, rerun the Landing shadow, or begin P12-10.

## Owner bulk preclassification batch 2

The Owner authorized a second workbook-derived batch containing 12 Modern MTGO
singletons across 11 reviewed identities. The two Primal Prayers records share
one parent and one rule. All dispositions are recorded as `owner_accepted` and
`new_identity`; no production classifier file is changed.

The batch adds 11 shadow-only parents and 11 rules:

- `izzet-extra-turns-primary` requires the reviewed Tablet of Discovery, Time
  Warp, and Temporal Mastery core, Izzet mana, and no reviewed off-color source
  or spell;
- `jund-goblins-primary` requires Birthing Ritual, Ignoble Hierarch,
  Conspicuous Snoop, Blood Crypt, and Stomping Ground;
- `thopter-sword-bant` creates the `thopter-sword` parent with a `bant` subtype
  for the reviewed Foundry, Sword, Rumble, and Bant-land structure;
- `rakdos-aggro-primary` requires Super Shredder, Moonshadow, Ragavan, and Blood
  Crypt;
- `primal-prayers-combo-primary` requires Primal Prayers, Guide of Souls, and
  Ocelot Pride and has priority over Energy;
- `naya-midrange-primary` requires Ragavan, Phlage, Wrenn and Six, and reviewed
  Naya mana sources;
- `five-color-elementals-primary` requires Birthing Ritual, Omnath, and Risen
  Reef while excluding Shardless Agent so Five-Color Ritual remains separate;
- `cheerios-primary` requires Sram, Bone Saw, and Kite Shield;
- `shape-anew-primary` follows the Owner's current broad direction and requires
  only three main-deck Shape Anew;
- `glimpse-of-tomorrow-primary` follows the reviewed identity and requires only
  three main-deck Glimpse of Tomorrow; and
- `izzet-cauldron-primary` requires Vivi Ornitier and Agatha's Soul Cauldron.

A complete replay of all 6,784 current MTGO Modern decks changes exactly the
12 intended records from Unknown to their reviewed identities. No already
classified record changes identity, each selected record has one rule match,
and no other current record selects a batch rule. The current shadow therefore
moves from 6,755 classified and 29 Unknown to 6,767 classified and 17 Unknown.

The 5,792-record frozen corpus changes exactly nine corresponding Unknown
records: one each to Rakdos Aggro, Glimpse of Tomorrow, Bant Thopter Sword,
Jund Goblins, Naya Midrange, Izzet Extra Turns, and Cheerios, plus two to Primal
Prayers Combo. It moves from 5,769 classified and 23 Unknown to 5,778 classified
and 14 Unknown. No frozen classified identity migrates and reordered-rule
evaluation produces the same identities. Izzet Cauldron, Shape Anew, and
Five-Color Elementals are newer than the frozen corpus and have no frozen hit.

All 362 registered Tabletop event 434455 decklists retain their pre-batch
identity. The shadow now has 112 parents and 190 rules with globally unique IDs
and numeric priorities. Synthetic coverage checks all positive thresholds,
below-threshold handoffs, Izzet off-color exclusions, Primal Prayers precedence
over Boros Energy, the Shardless Agent exclusion, and Tabletop. The focused R4
shadow suite passes 49 tests.

Stop before owner bulk preclassification batch 3. Do not promote any proposal
into production, commit, publish, rerun the Landing shadow, or begin P12-10.

## Owner bulk preclassification batch 3

The Owner authorized a third workbook-derived batch containing eight Modern
MTGO singletons across seven reviewed identities. The two Rakdos Delirium
records share one parent and one rule. All eight dispositions are recorded as
`owner_accepted` and `new_identity`; no production classifier file is changed.
No network research was used.

The batch adds seven shadow-only parents and seven rules:

- `domain-persist-primary` requires Persist, Archon of Cruelty, Leyline of the
  Guildpact, and Scion of Draco and has priority over Domain Zoo;
- `dimir-persist-primary` requires Persist, Archon of Cruelty, Psychic Frog,
  and Watery Grave while excluding reviewed non-Dimir main-deck sources and
  non-Dimir spells in either zone;
- `azorius-miracles-primary` requires Brainsurge, Terminus, and Hallowed
  Fountain and has priority over Chant Control;
- `sultai-flicker-primary` requires Ghostly Flicker, Drowner of Truth, Psychic
  Frog, Breeding Pool, and Watery Grave while excluding reviewed white and red
  sources and spells;
- `domain-blink-primary` requires Phelia, Exuberant Shepherd, Leyline Binding,
  and Overlord of the Balemurk;
- `rakdos-delirium-primary` requires the reviewed Nethergoyf, Dragon's Rage
  Channeler, Fear of Missing Out, Moonshadow, Detective's Phoenix, Mishra's
  Bauble, and Blood Crypt structure while excluding Hollow One, Cori-Steel
  Cutter, and Death's Shadow; and
- `five-color-humans-primary` requires Aether Vial, Champion of the Parish,
  Thalia's Lieutenant, Cavern of Souls, Secluded Courtyard, and Meddling Mage.

A complete replay of all 6,784 current MTGO Modern decks changes exactly 17
identities from the pre-batch shadow: the eight intended Unknown records move
to the seven reviewed identities, two existing Domain Zoo records move to
Domain Persist, and seven existing Chant Control records move to Azorius
Miracles. No other identity changes. The current shadow therefore moves from
6,767 classified and 17 Unknown to 6,775 classified and 9 Unknown.

The 5,792-record frozen corpus changes exactly 14 identities: the eight
corresponding Unknown records move to the reviewed identities, two Domain Zoo
records move to Domain Persist, and four Chant Control records move to Azorius
Miracles. It moves from 5,778 classified and 14 Unknown to 5,786 classified and
6 Unknown. Reordered-rule evaluation produces the same identities.

All 362 registered Tabletop event 434455 decklists retain their pre-batch
identity. The shadow now has 119 parents and 197 rules with globally unique IDs
and numeric priorities. Synthetic coverage checks every positive path,
below-threshold and color-boundary handoffs, Domain Zoo and Chant precedence,
the Rakdos Delirium exclusions, the Five-Color Humans separation, current and
frozen corpus transitions, order stability, and Tabletop. The focused R4
shadow suite passes 50 tests.

Stop before owner bulk preclassification batch 4. Do not promote any proposal
into production, commit, publish, rerun the Landing shadow, or begin P12-10.

## Owner bulk preclassification batch 4

The Owner authorized the fourth workbook-derived batch after two decision
rounds. Nine Modern MTGO singleton families map to eight new shadow-only parent
identities because the white-splash and Dimir records share one Dimir Unearth
rule. No network research was used. Workbook reconciliation also confirmed that
`modern-unknown-86014f893ae1`, not the already accepted Grixis Tempo family
`modern-unknown-bb82db02b4ee`, is the Izzet Tempo input. The earlier Grixis
Tempo disposition remains unchanged.

The batch adds eight parents and eight rules:

- `dimir-unearth-primary` requires Abhorrent Oculus, Unearth, Thought Scour,
  Psychic Frog, and Watery Grave; it excludes Birthing Ritual, Goryo's
  Vengeance, and Persist while permitting a white splash;
- `dimir-goryos-primary` requires Goryo's Vengeance, Atraxa, Psychic Frog, and
  Watery Grave and excludes reviewed non-Dimir main-deck mana sources;
- `izzet-tempo-primary` requires Ragavan, Counterspell, Tamiyo, and Steam Vents,
  excludes Psychic Frog, and applies the reviewed off-color source and spell
  boundaries;
- `rakdos-midrange-primary` requires the reviewed Ragavan, Dauthi Voidwalker,
  Orcish Bowmasters, Seasoned Pyromancer, Thoughtseize, and Blood Crypt core;
- `yawgmoth-energy-primary` requires two Yawgmoth plus Guide of Souls, Ocelot
  Pride, Young Wolf, and Birthing Ritual, and outranks traditional Yawgmoth when
  both structures match;
- `sultai-tempo-primary` requires Ice-Fang Coatl, Counterspell, Fatal Push,
  Breeding Pool, and Watery Grave, excludes Oculus Ritual markers, and applies
  reviewed white and red color boundaries;
- `solemnity-blink-primary` requires Solemnity, Balemurk, Phelia, and Solitude
  while excluding Nine Lives and Phyrexian Unlife so Solemnity Prison remains
  separate; and
- `mono-black-saga-primary` is the globally lowest-priority fallback. It
  requires Urza's Saga, Nethergoyf, Mishra's Bauble, Thoughtseize, and four
  Swamps, excludes reviewed competing identities and nonblack spells, permits
  black-producing fetch targets, and always yields to an established match.

A complete replay of all 6,784 current MTGO Modern decks changes exactly 16
identities from the pre-batch shadow. The nine remaining Unknown records move
to the eight reviewed parents. Seven records previously selected as Dimir Tempo
move to Dimir Unearth because they contain the same accepted Oculus, Unearth,
Thought Scour, and Psychic Frog engine. The current shadow therefore moves from
6,775 classified and nine Unknown to all 6,784 classified. No other current
identity changes.

The 5,792-record frozen corpus changes exactly eight identities: six remaining
Unknown records move to five reviewed parents, and two Dimir Tempo records move
to Dimir Unearth. Dimir Goryo's, Yawgmoth Energy, and Solemnity Blink are newer
than the frozen corpus and have no frozen hit. The frozen shadow therefore
moves from 5,786 classified and six Unknown to all 5,792 classified. Reordered
rules produce identical selections.

All 362 registered Tabletop event 434455 decklists retain their pre-batch
identity. The shadow now has 127 parents and 205 rules with globally unique IDs
and numeric priorities. Synthetic coverage checks all positive and
below-threshold cases, mainboard-only cores, exclusion handoffs, color
boundaries, Yawgmoth Energy precedence, Solemnity Prison precedence, the
lowest-priority Mono-Black Saga fallback, complete current and frozen corpus
transitions, rule-order stability, and Tabletop.

Stop for Owner acceptance of batch 4. Do not promote any proposal into
production, commit, publish, rerun the Landing shadow, begin Standard review,
or begin P12-10.

## Modern owner-review closeout

The Owner accepted batch 4 and the complete Modern R4 shadow on 2026-08-12.
All 88 Modern candidate families now have an explicit `owner_accepted`
disposition: 61 are `new_identity` and 27 are `map_existing`; none remains
pending, intentionally Unknown, or deferred. Standard remains a separate,
unstarted review with all 59 candidate families still pending.

The machine-readable checkpoint at
`docs/audits/classifier-r4/modern_closeout.yaml` binds the accepted Modern
decisions to exact SHA-256 values for the disposition file, shadow rules,
shadow generator, frozen review queue, and Owner-edited workbook. It also
freezes the unchanged production Modern rule and protected event 434455 source
hashes. A focused test recomputes every repository-managed hash and fails if a
later Standard edit silently changes any accepted Modern input or result.

The accepted shadow classifies all 6,784 current and all 5,792 frozen Modern
records, leaves all 362 registered Tabletop identities unchanged from their
pre-batch state, and still changes no production rule. The Owner separately
authorized one local commit for this Modern closeout. That one-time authority
does not authorize Standard development, a later Standard commit, production
promotion, publication, the Landing shadow, or P12-10.

Closeout validation passed with 70 focused R4/documentation tests and 918
complete repository tests. Ruff, `git diff --check`, production rule
validation, and repository validation also passed; the latter checked 151
Python files, 17 JavaScript files, 1,713 JSON files, 40 YAML files, 56
references, and 2,120 hygiene entries. The first complete closeout invocation
placed pytest's deliberate invalid-file fixtures in an unignored repository
root temporary directory, so its real-validator smoke test correctly failed
with 917 other tests passing. After removing that task-created directory and
moving `--basetemp` under the ignored `.venv`, the independent validator and
the complete 918-test rerun both passed.
