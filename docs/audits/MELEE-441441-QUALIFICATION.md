# Melee event 441441 qualification

Date: 2026-08-31

Task: `MELEE-441441-QUALIFICATION`

Scope: read-only qualification and structure evidence only

## Outcome

Event `441441`, **Magic Spotlight: The Hobbit™ Main Event**, passes the
qualification gate for a later Modern tabletop whitelist admission. The
supported structure is `constructed_day2`. No whitelist, source response,
normalized data, generated statistic, workflow, or public artifact changed in
this task.

This result authorizes no later stage. Owner acceptance of this evidence and
separate authorization are required before a whitelist admission task may
begin.

## Identity and eligibility

| Field | Verified value | Evidence |
| --- | --- | --- |
| Canonical source | `https://melee.gg/Tournament/View/441441` | The Melee page resolves to the same numeric event ID and title. |
| Event | Magic Spotlight: The Hobbit™ Main Event | Melee event header and the official Spotlight announcement |
| Series | `spotlight_series` | Wizards identifies the Brisbane event as part of the Magic Spotlight Series. |
| Main event | Yes | The Melee title says “Main Event”; Wizards separately describes the main event and its Top 8 awards. |
| Tournament type | Tabletop | Melee event metadata |
| Team event | No | Public standings, decklists, and match paths identify individual players; no team unit is present in the inspected evidence. |
| Constructed format | `modern` | Melee metadata and rules; Wizards describes the main event as Modern Constructed. |
| Mixed format | No | Both days are explicitly Modern Constructed; no Draft or other format phase is listed. |
| Source status | Ended | Melee event metadata on 2026-08-31 |
| Joined field | 570 players | Melee event metadata on 2026-08-31; this is not yet a collected participant count. |

The official Spotlight weekend is August 28–30, 2026. The Melee main-event
page starts at 08:30 JST on August 29, equivalent to 09:30 in Brisbane, and
the rules define two competition days. The later whitelist admission should
therefore use main-event dates `2026-08-29` through `2026-08-30`, while
retaining the official weekend dates as contextual evidence.

## Structure mapping

The event is a pure Constructed event with a separate Day 2 field, so the
approved structure is `constructed_day2`.

| Proposed phase | Stage | Source rounds | Phase | Game format | Swiss |
| --- | --- | --- | --- | --- | --- |
| `day1_modern` | `day1` | 1–9 | `constructed` | `modern` | true |
| `day2_modern` | `day2` | 10–15 | `constructed` | `modern` | true |
| `top8_modern` | `playoff` | Quarterfinals, Semifinals, Finals | `playoff` | `modern` | false |

Verified advancement and statistics boundaries:

- Day 2 occurs after round 9;
- players with at least 18 match points advance to Day 2;
- six additional Swiss rounds produce the Top 8 after round 15;
- the three playoff labels are contextual and must remain excluded from
  primary Modern Swiss statistics;
- `include.swiss` may be true and `include.playoffs` may retain playoff source
  context, while `statistics.include_playoffs` remains false.

No reviewed override or special Top 8 lock treatment is justified by the
qualification evidence. Such handling must not be invented during whitelist
admission and may be added only if later candidate evidence proves it.

## Public result and decklist evidence

The read-only inspection sampled the standings after rounds 1, 9, and 15 and
after the quarterfinals. Each sampled view displayed individual standings,
records, points, and public decklist links. A representative first-place
decklist displayed:

- an individual player and a link back to event `441441`;
- a complete 60-card Modern main deck and 15-card sideboard;
- opponent, result, and decklist context across rounds 1–18, corresponding to
  15 Swiss rounds and the three playoff rounds.

This is qualification evidence, not a completeness census. Exact participant,
standing, decklist, round, match, eligible-opportunity, missing-decklist, and
unknown-round counts remain mandatory candidate-acceptance checks after a
separately authorized production collection. No source response was retained
by this task.

## Sources

- [Melee event 441441](https://melee.gg/Tournament/View/441441)
- [Wizards of the Coast: Prepare for Magic Spotlight: The Hobbit™ in Brisbane and Dallas](https://magic.gg/news/prepare-for-magic-spotlight-the-hobbit-in-brisbane-and-dallas)
- [Wizards of the Coast: Metagame Mentor — Modern with Magic: The Gathering® | The Hobbit™](https://www.magic.gg/news/metagame-mentor-modern-with-the-hobbit)

## Gate decision

**PASS — qualification evidence is complete for owner review.**

There is no material uncertainty requiring the optional disposable rehearsal
before whitelist admission. The recommended next task, only after owner
acceptance and separate authorization, is
`MELEE-441441-WHITELIST-ADMISSION`. It should add the single reviewed event
entry using the mapping above and run only the whitelist-focused validation
defined by the fixed admission runbook.
