# P8-07 backend consumer bridge

Date: 2026-07-28

Branch: `codex/p8-07-backend-consumer-bridge`

Base: `024c63afc390201bc4fbadfd09e033c538624270`

## Authorized scope

- publish complete subtype labels without changing taxonomy;
- add literal Tabletop records while preserving legacy records;
- generate the global format/product availability catalog;
- publish Top 8 exact-deck deviation and immutable weekly comparison bases;
- update Schemas, manifests, candidate boundaries, workflows, tests, generated
  data, and authoritative documentation;
- do not change the production front end or begin P8-08.

## Historical policy

2026-W30 is the first safely reproducible immutable Top 8 week. Each retained
week has one `YYYY-Www-bases.json` companion. Regeneration of a week that
already declares this policy must be byte-identical or fail before overwrite.
Earlier weeks are not reconstructed from incomplete provenance.

A valid four-week base produces deviation and card differences with the
existing construction formula. An identity below the minimum sample threshold
retains its exact deck and publishes `base_status: unavailable` with null
deviation; the generator does not synthesize a comparison.

## Compatibility

- existing MTGO and Tabletop paths remain;
- legacy draw-adjusted rates remain byte-semantic compatibility fields;
- new target rates declare `wins_over_valid_matches`;
- no classifier, rule, fetch policy, event scope, or production UI changed;
- MTGO and Tabletop remain separate products.

## Verification contract

- focused bridge and affected-product tests;
- byte-reproducible generated Standard, Modern, and Tabletop documents;
- explicit mutation test for immutable Top 8 history;
- formal Schema and manifest validation;
- production-candidate path validation;
- repository, rule, workflow, and full pytest regression.

## Local result

- focused bridge and affected suites: 70 and 108 passed;
- full suite: 555 passed;
- public Schema manifest: 69 documents passed;
- repository validation: 116 Python, 1,582 JSON, 21 YAML, 30 references,
  and 1,821 hygiene checks passed;
- Standard and Modern rule validation passed;
- immutable same-week rebuild and deliberate mutation rejection passed.

The 2026-W30 baseline contains 64 Standard and 104 Modern exact decks. Valid
four-week bases produce deviation for 61 Standard and 100 Modern entries; the
remaining 3 and 4 entries publish explicit unavailable bases. The global
catalog contains six formats and eight currently available format/product
entries. No commit, push, pull request, merge, or workflow dispatch was
performed.
