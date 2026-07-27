# P8 MTGO Event Semantic Completeness Hotfix

Status: `completed_owner_accepted_publication_authorized`
Task type: focused production-ingestion guard
Base: `4dcb8d19f2b8e3a2f2182a9dbd4d0e970918bbf5` (`master`)
Branch: `codex/p8-hotfix-mtgo-event-completeness`
Date: 2026-07-27
Owner accepted: 2026-07-28

## Purpose

Prevent a newly published MTGO playoff event from being saved and permanently
ledgered while its decklists are available but its standings, Swiss values, or
final placements are still incomplete.

## Boundary

This hotfix changes:

- official MTGO source completeness validation;
- retry/defer diagnostics for temporarily incomplete playoff payloads;
- production-candidate validation for new or modified normalized event files;
- focused regression fixtures and tests;
- the documented source-admission contract.

It does not change:

- retained event `12847150` or `12844304`;
- `fetched.txt`;
- MTGO statistics, Pickup, reports, metadata, or public JSON;
- workflows or schedules;
- classification rules;
- front-end behavior;
- the separately controlled event-refresh task.

## Implemented source contract

A source payload must declare `inplayoffs` before it can be accepted or
excluded.

For a playoff event:

- decklists, standings, and final-rank collections must be non-empty lists;
- every record must be an object with a non-empty string or integer `loginid`;
- each collection rejects duplicate `loginid` values;
- every published deck must have a matching standing and final-rank record;
- Swiss rank and final rank must be positive integers;
- Swiss score must be a non-negative integer.

Missing collections, missing published-deck coverage, and missing values are
treated as temporary publication incompleteness. They use the existing five
within-run attempts and two-day scheduled-run grace period, produce
field-specific diagnostics, and create neither an event file nor a ledger
entry.

Invalid collection types, invalid record shapes, duplicate identities, and
invalid numeric values remain fatal parser/contract failures.

Non-playoff events retain their existing exclusion path and do not need
playoff-only standings or final-rank collections.

## Candidate-publication contract

Every new or modified normalized event file must:

- retain `inplayoffs=1`;
- contain a non-empty `players` list;
- use unique, non-empty player `loginid` values;
- provide valid `swiss_rank`, `swiss_score`, and `final_rank` values for every
  retained player.

This provides a second barrier if a producer ever bypasses or regresses the
source gate.

## Sequencing correction

The first implementation also made the statistics consumer fail closed on
missing Swiss evidence. The full test suite proved that this would
intentionally break the committed Modern statistics and Pickup baselines on
known retained event `12847150`.

That consumer change was removed from this hotfix. It must be activated in
`P8-REPAIR-MTGO-EVENTS-12847150-12844304` after both retained event files are
refreshed and a full archive audit reports zero remaining exceptions. This
keeps every intermediate `master` commit usable without weakening the final
standard.

## Validation

- focused fetch, candidate, production-workflow, and CI tests: 56 passed;
- complete repository pytest: 511 passed;
- repository validator:
  - Python: 109/109;
  - JSON: 1553/1553;
  - YAML: 17/17;
  - references: 30/30;
  - hygiene: 1774/1774;
- Standard rule validation: passed;
- public Schema validation: 52 documents passed;
- `git diff --check`: passed.

Anonymous no-write validation against the current official pages confirmed
that both audited events satisfy the new source contract:

| Event | Decklists | Standings | Final ranks | Result |
| --- | ---: | ---: | ---: | --- |
| `12847150` | 32 | 32 | 32 | complete |
| `12844304` | 32 | 32 | 32 | complete |

No response body, normalized event, identity data, or generated output from
the live check was retained.

## Stop point

The owner accepted this hotfix and authorized its commit, push, PR, and merge
on 2026-07-28. The same instruction separately authorizes local execution of
the second repair task after this hotfix is merged. Production workflow
execution and remote publication of the repair task remain unauthorized.
