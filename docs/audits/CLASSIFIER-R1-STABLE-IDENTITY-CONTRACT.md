# CLASSIFIER-R1 — Stable identity and migration contract

## Result

R1 converts the completed Owner review into a machine-readable target identity
contract without changing production classification. It freezes:

- the exact Standard and Modern rule files on which the review was based;
- all 129 submitted parent-review outcomes;
- the accepted parent and subtype target identities;
- every retired-ID, split, merge, and display-name transition;
- the Weekly Pickup known-state migration plan; and
- the validation matrix required before any production rule is edited.

R1 does **not** select final numeric priorities, implement a shadow classifier,
edit `my_archetypes/*.yaml`, migrate Pickup state, refresh generated data, or
authorize P12-10. Those are later, separately controlled steps.

## Authority and evidence

The Owner authorized only `CLASSIFIER-R1-STABLE-IDENTITY-CONTRACT` local work
on 2026-08-10. The task started from remote `master` commit
`a99ca08a294f173c9a17fe6fd70c5e52d36cec98` in an independent clone with push
disabled.

The accepted R0 checkpoint is identified by SHA-256
`83B8685099A130CC95BB78679C72D113DD4F2FE62E4802ABB17D15A7978F84B3`.
The submitted workbook is identified by SHA-256
`D4A8817627BCBAF8DD63C1C3A0531DDF36A9B411D3D18CEF3DC17558BCF6DAF6`.
The checkpoint records 104 `同意现状` rows, 24 `需要修改` rows, one formerly
unreviewed Dimir Deceit row resolved by the Owner, and no unresolved Owner
identity or rule decisions.

Four rows originally marked `同意现状` receive explicitly accepted dependent
amendments from later R0 discussions:

- Modern Prowess receives the new Boros, Mono-Red, and Mardu routes and the
  accepted land-only color corrections from the Steel-Cutter review;
- Modern Jeskai Control excludes Chant and Scepter after the Chant split;
- Standard Jeskai Control yields the complete Inevitable Defeat shell to Dark
  Jeskai Control; and
- Standard Sultai Control receives or verifies the accepted three-color Bargain
  fallback below White Sultai Control.

These amendments do not alter the submitted status counts. They prevent an
earlier row-level approval from overriding a later, more specific Owner
decision.

## Deliverables

- `docs/audits/classifier-r1/identity_dictionary.yaml` defines the exact
  baseline projection and accepted target overlays.
- `docs/audits/classifier-r1/transition_map.yaml` defines stable-ID,
  display-name, subtype, targeted-reclassification, and Pickup migrations.
- `docs/audits/classifier-r1/validation_matrix.yaml` defines R2 shadow oracles,
  conflict boundaries, fail-closed cases, and cross-source checks.
- `tests/test_classifier_r1_contract.py` validates coverage, source digests,
  target uniqueness, transition completeness, Pickup planning, and R1's
  production-zero-change boundary.

The YAML documents are contracts, not production configuration. Production
rule loading must not read them.

## Target identity summary

The exact baseline contains 55 Modern parents with 55 subtypes and 74 Standard
parents with four subtypes. Applying the accepted identity overlay produces a
target dictionary of:

| Format | Target parents | Target subtypes |
| --- | ---: | ---: |
| Modern | 70 | 54 |
| Standard | 72 | 11 |

Modern loses one net subtype. Parent splits retire the old Persist, Goryo's,
Blink, and Eldrazi Ramp/Selesnya leaves while Living End, Death's Shadow,
Broodscale Combo, and Prowess add accepted leaves.

### Modern structural changes

- Split Persist into Grixis Persist, Agadeem Persist, and Esper Persist.
- Split Goryo's into Cremator, Esper, and Grixis parents.
- Rename `blue-black-tempo` to `dimir-tempo` and retain Dimir, Grixis, and Esper
  subtypes under the accepted tiered-fallback boundary.
- Replace Blink with seven independent parents: Esper Ketramose, Esper Blink,
  Azorius Blink, Jeskai Stoneforge, Jeskai Blink, Mardu Blink, and Orzhov Blink.
- Add Broodscale Combo/Simic and the independent Eldrazi Ramp Chant parent.
- Keep the `boros-land-destruction` ID but display it as Boros Ponza.
- Keep Chant Control only for Azorius and Jeskai Chant shells, separate
  traditional Azorius and Jeskai Control, and add Omnath Midrange.
- Split Hollow One into Hollowvine and Rakdos Hollow One, with Rakdos and Mardu
  leaves under the latter.
- Give Living End five explicit leaves and no generic fallback.
- Keep `steel-cutter/izzet` under the display name Izzet Steel-Cutter; add
  Rakdos Steel-Cutter and Mono-Red Artifact parents; correct dependent Prowess
  routes.
- Add Grixis, Dimir, and Rakdos Death's Shadow leaves.
- Replace `blue-eldrazi` with the Mono-Blue Tron identity.

### Standard structural changes

- Merge Izzet Aggro's two card-named leaves into the parent.
- Replace Azorius Tempo with Azorius Prison.
- Merge Jeskai Manufacturing into Boros Manufacturing and add Jeskai, Mardu,
  and Boros leaves.
- Replace Simic Kona with Kona Omniscience and add Temur, Bant, and Simic leaves.
- Split 4-Color Control into Dark Jeskai Control and White Sultai Control while
  preserving the accepted Jeskai and Sultai boundaries.
- Keep ID `4-color-allies` but display it as Allies Kindred.
- Merge Boros Leyline and Mono-Red Leyline into Leyline Aggro with Izzet, Gruul,
  Boros, Rakdos, and Mono-Red leaves.
- Keep Dimir Deceit's parent and rule IDs and lower only Requiting Hex from
  three to two.

## Stable identity and compatibility rules

1. A display-name-only change retains its parent and rule IDs.
2. A one-to-one ID rename has one explicit compatibility transition.
3. A split, merge, or targeted subset is never represented as a false alias;
   it is resolved by the accepted target rules in the shadow.
4. Every retired parent is covered by the transition map.
5. Subtypes never split parent-level statistics or Weekly Pickup known state.
6. A parent that defines subtypes must select exactly one of them for every
   classified deck. There is no implicit `Other` leaf.
7. Explicitly unsupported hybrids remain `Unknown`.
8. The same format taxonomy is used by MTGO and Tabletop, while their inputs,
   statistics, reports, and public documents remain separate.

## Weekly Pickup migration contract

Modern currently keys known state by stable parent ID; Standard still uses
legacy display names. R1 records both exact source hashes and proposes a dry-run
migration without modifying either file.

All new parents derived from a known family are initialized as known. This is
required to prevent an ID split or rename from being misreported as a new deck.
Subtype changes do not alter parent-based known state. Existing reviewed
candidates, comments, approvals, and published Pickup weeks remain untouched
unless a later task explicitly authorizes their migration.

R2 must show the complete added, removed, retained, and false-new-prevention
sets. R3 may apply the accepted migration only together with the accepted
production taxonomy.

## R2 shadow-classifier contract

R2 is a separate task. It may implement the target rules in an isolated shadow
path, but it must not switch production classification. Its required output is:

- a de-identified deck-level before/after transition report for the complete
  committed Standard and Modern corpora;
- exact classified, Unknown, multiple-match, same-parent subtype-match, and
  conflict deltas;
- the final globally unique numeric priorities and rule IDs;
- proof that YAML order does not change the selected identity;
- focused synthetic cases for unobserved or fail-closed boundaries;
- same-format MTGO/Tabletop comparison, including event `434455` without
  changing its protected bytes;
- the Standard frozen baseline and Modern P6-01 compatibility comparison; and
- a Pickup known-state dry run.

The R0 checkpoint sometimes says exact priorities were deferred to an "R1
shadow". The Owner-approved staged contract now uses R1 for identity freeze and
R2 for the complete shadow. No semantic decision is changed by that sequencing
normalization.

## Stop point

R1 stops after local validation and Owner review. It does not authorize a
commit, push, pull request, merge, production dispatch, production classifier
edit, Pickup migration, generated-artifact refresh, R2, or P12-10.

## Later-stage reproducibility handoff

The Owner later accepted and locally committed R1, accepted and locally
committed R2, and authorized R3 local implementation on 2026-08-11. R3 records
frozen pre-migration rule and Pickup paths in the R1 identity dictionary and
transition map. R1's evidence therefore remains anchored to its reviewed input
bytes; this note does not change the historical R1 authorization boundary.
