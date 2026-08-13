# Standard Spellementals mainboard Talent boundary

## Task contract

The Owner authorized `STANDARD-SPELLEMENTALS-TALENT-BOUNDARY` for local
implementation on 2026-08-13 and then accepted commit, remote publication,
and merge. The declared artifact impact is `statistical_json_structure`.
Manual production dispatch, the Landing shadow, threshold selection,
representative cards, and P12-10 remain separately unauthorized.

The task uses the fresh independent workspace
`D:/dl/crawlerpj/.codex-workspaces/standard-spellementals-talent-boundary-20260813-01`,
branch `codex/standard-spellementals-talent-boundary`, first developed from
remote `master` commit `96a3721e74715f4357dd995bcc510ebda1036eb1`. Before
publication it was rebased onto `b03a162c48cacef40b4201fea381da84d500dc9e`,
which includes the merged `CLASSIFIER-DISPLAY-NAME-DEDUPE` PR #202 and PR #203.
Push remains disabled by default and the repository-local credential helper is
empty; publication uses the documented command-scoped `gh` credential path.

## Problem

The Standard `izzet-spellementals-primary` rule counted Eddymurk Crab,
Sunderflock, and Hearth Elemental across both main deck and sideboard. A
Prowess deck with four mainboard Stormchaser's Talent, four Slickshot Show-Off,
and four Boomerang Basics therefore matched both Izzet Spellementals and Izzet
Prowess when it carried Sunderflock in its sideboard. The higher existing
Spellementals priority selected the wrong parent.

## Authorized boundary

Keep every stable parent ID, rule ID, priority, and existing condition. Add
exactly one condition to `izzet-spellementals-primary`:

```yaml
- card: Stormchaser's Talent
  zone: main
  exact_count: 0
```

The explicit `main` zone is material. Six reviewed Spellementals records have
zero mainboard Talent and two sideboard Talent; all six must remain Izzet
Spellementals. The task does not constrain Sunderflock by zone and does not
change the Izzet Prowess rule or either rule's priority.

## Exact classification impact

A complete read-only comparison against the accepted R5 production baseline
found:

- current Standard: 4,829 records, with exactly 102 transitions from
  `izzet-spellementals` to `izzet-prowess` through
  `izzet-prowess-primary`;
- current statuses remain 4,821 classified and eight Unknown;
- frozen Standard: 3,936 records, with exactly 56 transitions from
  `izzet-spellementals` to `izzet-prowess` through
  `izzet-prowess-primary`;
- frozen statuses remain 3,928 classified and eight Unknown; and
- no other parent, subtype, rule, priority, conflict, invalid-deck result, or
  Unknown status changes.

Real-deck regression coverage uses both affected records from event `12851116`
and protects the sideboard-Talent Spellementals record at index 21 of event
`12845647`. Participant identities are not recorded in this audit.

## Generated scope and protected boundaries

The maintained offline generators refresh only the existing Standard MTGO
classification reports, 1/4/12/36-week statistics and matchups, completeness,
hierarchy, metadata, catalog references, and already indexed W30-W32 Top 8
documents. No Pickup candidate, approval, published week, known-archetype
state, source event, retained response, Modern or Tabletop artifact, event
whitelist, Schema, formula, workflow, front-end source, public path, or new Top
8 week changes.

The accepted R4 shadows and R5 promotion tools remain byte-preserved historical
evidence. A production-contract test defines current Standard as the exact R5
document plus the one Owner-authorized condition; Modern remains byte-identical
to R5.

## Validation and stop point

The local result passed:

- 30 focused rule, production-contract, and real-deck regression tests;
- the complete ordinary pytest shard: 950 passed and eight deselected;
- the committed-baseline pytest shard: eight passed and 950 deselected;
- Ruff and the strict four-module mypy baseline;
- repository validation: 159 Python, 17 JavaScript, 1,752 JSON, 51 YAML, 56
  references, and 2,180 hygiene checks;
- Standard rule validation and 77 public JSON Schema checks;
- three native Node tests and 77 real-Chromium Playwright tests; and
- `git diff --check`.

The first ordinary-shard attempt used a repository-local `--basetemp`. Its 949
passes and one failure showed that the later repository-validator smoke test
correctly encountered intentionally invalid UTF-8, JSON, YAML, and Python
fixtures left under that directory. After the test-only directory was removed,
the failed smoke test passed alone and the complete shard passed with an
external basetemp, matching clean-checkout CI placement. This was a validation
environment error, not a product failure.

The final path audit found no changed file outside the declared rules,
Standard reports and statistics, tests, and governance documentation. Both the
multiple-match and overridden-match reports fall from 1,079 to 977 records,
exactly removing the 102 corrected dual matches; no Spellementals-selected
record remains paired with Prowess in either report. Committed-baseline tests
prove every regenerated public document is byte-reproducible.

Publish one Ready pull request and merge only after complete CI succeeds. Then
verify the exact remote master and automatic Pages deployment. Do not dispatch
production, rerun the Landing shadow, or start P12-10 without separate
authorization.
