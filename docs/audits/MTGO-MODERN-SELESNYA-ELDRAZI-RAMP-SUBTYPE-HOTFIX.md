# Modern Selesnya Eldrazi Ramp subtype hotfix audit

Date: 2026-08-03

Branch: `codex/fix-eldrazi-ramp-subtype`

Base commit: `c448332b1444b3734bd3fcf5eb37d8f4d1777e9e`

Status: local implementation complete; awaiting owner acceptance before commit.

## Production failure

The scheduled MTGO production run
[`30766943971`](https://github.com/Jacelber/mtgo-data/actions/runs/30766943971)
completed collection and statistics building, then stopped while building Modern
matchup statistics:

```text
classified archetype 'eldrazi-ramp' defines subtypes but selected none
```

The strict stop preserved the no-residual-subtype policy. The publish job was
skipped, so the failed run did not write generated production data.

## Reproduction and classification evidence

The failed run's temporary fetch artifact contained two identical Modern decks
with the following relevant main-deck evidence:

- four `Sowing Mycospawn`;
- four `Ugin's Labyrinth`;
- four `Eldrazi Temple`;
- four `Talisman of Unity`;
- two `Temple Garden`;
- four `Windswept Heath`;
- no `Fight Rigging`; and
- no `Eldrazi Linebreaker`.

Both decks matched `eldrazi-ramp-fallback`, which deliberately selects no
subtype. No participant identity or raw source response is retained by this
hotfix.

## Resolution

The existing `eldrazi-ramp` parent gains the explicit `selesnya` subtype. Rule
`eldrazi-ramp-selesnya` has priority `6435`, below the existing Temur rule and
above the existing Simic rule. It requires the witnessed Eldrazi Ramp core plus
`Talisman of Unity` and `Temple Garden`, while retaining the fallback's
exclusions for `Fight Rigging` and `Eldrazi Linebreaker`.

The fallback remains strict. It still selects no subtype for any future Eldrazi
Ramp build that does not match a maintained colour signature.

Reclassifying the temporary failed candidate after the rule change found two
`eldrazi-ramp/selesnya` decks and zero Eldrazi Ramp decks with a null subtype.

## Compatibility boundary

This hotfix changes one maintained Modern classification rule and its taxonomy
contract. It deterministically regenerates the existing Modern derived data
from their committed inputs, including the protected event `434455` closure.
It does not fetch or retain new source data, change statistical formulas,
workflows, front-end files, or public paths.

Because the retained `434455` derived bytes deliberately change, the
compatibility manifest advances from `1.0.0` to `1.1.0`. Its immutable raw
snapshot, normalized event, selected catalog projections, and all statistical
samples remain unchanged; the changed bytes are limited to classification
taxonomy provenance and the newly declared zero-count Selesnya leaf.

## Validation

- Production-candidate reclassification: two `eldrazi-ramp/selesnya` decks
  and zero Eldrazi Ramp residual subtypes.
- Focused classification, compatibility, matchup, and statistics regression:
  `101 passed`.
- Full ordinary suite: `672 passed, 9 deselected`.
- Committed-baseline suite: `9 passed, 672 deselected`.
- Modern rule validation: pass.
- Public generated JSON Schema validation: `69` documents pass.
- Repository validation: 145 Python, 9 JavaScript, 1,636 JSON, 23 YAML,
  40 references, and 1,961 hygiene checks pass.
- Ruff and mypy: pass.

No browser source changed, so no manual browser acceptance is required for this
classification and generated-data hotfix. No production workflow was manually
dispatched.
