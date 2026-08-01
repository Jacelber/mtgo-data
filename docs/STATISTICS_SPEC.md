# Statistics Specification

## 1. Document purpose

This document defines the authoritative statistical rules for the `mtgo-data` project.

It applies to:

- MTGO Environment Trends;
- Tabletop Major Events sourced from approved Melee tournaments;
- shared statistical utilities;
- generated statistics JSON;
- front-end labels, tooltips, warnings, and quality reports;
- automated tests for statistical behavior.

Do not change a statistical formula only in implementation code.

Any intentional formula change must also update:

- this document;
- affected tests;
- affected JSON Schemas;
- `DECISIONS.md`;
- generated-data version information when compatibility is affected.

---

## 2. General principles

### 2.1 Constructed focus

The project measures Constructed deck performance.

For mixed Draft and Constructed events:

- Draft rounds are excluded from Constructed deck statistics;
- Draft points are excluded from Constructed average-point calculations;
- Draft matches are excluded from Constructed win rates;
- Draft matches are excluded from Constructed matchup matrices;
- overall standings points must not be used as Constructed deck points.

Limited results may be retained as source or contextual data when needed to verify event phases, advancement, or final standings.

### 2.2 Source separation

MTGO and tabletop data must not be combined into one statistic.

Do not combine them for:

- metagame share;
- high-score share;
- conversion;
- average points;
- win rate;
- matchup matrices;
- representative decklists.

Shared formulas may be implemented in common utility code, but their inputs and outputs must preserve the source identity.

### 2.3 Reconstruct from round-level data

For tabletop events, performance statistics should be reconstructed from round-level results whenever possible.

Final standings totals alone are not sufficient because they may include:

- Draft points;
- byes;
- intentional draws;
- awarded wins;
- playoff results;
- penalties;
- unplayed rounds;
- corrections not visible in deck records.

The normalized event data must preserve enough information to explain how each statistic was calculated.

### 2.4 Missing is not zero

Use `null` or an explicit unavailable state when a metric cannot be calculated reliably.

Do not display missing data as zero.

Examples:

- unknown Day 2 cut;
- unavailable round classification;
- missing decklist;
- unverified awarded win;
- unavailable theoretical round count;
- no valid matches.

### 2.5 No silent anomaly removal

Excluded or unresolved records must appear in a quality report.

Examples include:

- unknown round types;
- missing opponents;
- duplicate players;
- incomplete decklists;
- conflicting standings;
- unrecognized match results;
- suspected no-shows;
- suspected awarded wins;
- source totals that do not reconcile.

---

## 3. Core terminology

### 3.1 Deck

A deck is a valid Constructed decklist associated with one tournament player or one MTGO event result.

A deck without a reliable archetype match is classified as `Unknown`.

A missing or unusable decklist is not automatically the same as an `Unknown` archetype. The normalized data must distinguish:

- valid deck classified as a known archetype;
- valid deck classified as `Unknown`;
- missing decklist;
- invalid decklist;
- excluded player.

### 3.2 Archetype

An archetype is identified by a stable machine-readable archetype ID.

Display names may change without changing the archetype ID.

Statistics must aggregate by archetype ID rather than only by display name.

A classification result may also contain an optional subtype ID and subtype display name. A subtype is a rule-level variant within one parent archetype. Primary metagame, performance, and conversion statistics continue to aggregate by the parent archetype ID. Hierarchical matchup statistics are separately defined in section 11.8, and supplementary hierarchical MTGO range statistics are defined in section 16.3. Subtypes must not split or double-count the parent archetype population.

The Phase 2 compatibility migration may expose subtypes only for distinct legacy rule entries that already resolve to the same legacy archetype. It must not change any deck's parent archetype result. New subtype taxonomy and subtype-level statistical presentation require separate approval after the compatibility classifier is complete.

### 3.3 Theoretical round

A theoretical round is a scheduled Constructed Swiss round that a player was expected or eligible to play for the metric’s population.

Theoretical rounds are used to prevent early drops from inflating average points per round.

An unplayed theoretical round caused by an ordinary drop contributes:

- zero points to the numerator;
- one theoretical round to the denominator;
- no match to the win-rate or matchup denominator.

A player who did not qualify for Day 2 is not assigned Day 2 theoretical rounds.

### 3.4 Effective theoretical round

An effective theoretical round is a theoretical round after removing a round from which the player was officially exempt.

The main approved exemption is an official Top 8 lock procedure where a player stops playing and receives an administrative or awarded result.

Do not treat an ordinary drop as an exemption.

### 3.5 Played match

A played match is a real Constructed match with a recognized competitive result.

It does not include:

- bye;
- no-show;
- unplayed drop round;
- administrative result;
- Top 8 lock awarded win;
- unknown result;
- playoff result when calculating primary Swiss statistics;
- intentional draw reported as `0-0-3`.
- a match involving a participant whose event status is `disqualified`.

### 3.6 Match draw

A normal played match draw is a real match that ended drawn, such as a timed match ending with an appropriate game record.

A `0-0-3` intentional draw is treated separately and is not a played match for win-rate or matchup purposes.

---

## 4. Event structures

Every tabletop event must use one of the following structures.

### 4.1 `constructed_day2`

A pure Constructed event with a separate Day 2 field.

Primary scopes:

- Day 1 Constructed;
- Day 2 Constructed;
- Combined Constructed Swiss.

This mode may report Day 2 participation and conversion because advancement is based on the same Constructed competition, subject to event-specific rules.

### 4.2 `constructed_single_stage`

A pure Constructed event without a separate Day 2 field.

Primary scope:

- all Constructed Swiss rounds.

This mode uses a high-score region when an appropriate high-performing population is needed.

### 4.3 `mixed`

An event containing both Draft and Constructed phases.

Examples include Pro Tours and World Championships.

Primary scopes:

- Day 1 Constructed;
- Day 2 Constructed;
- all Constructed Swiss rounds.

For this mode:

- Draft is excluded from deck-performance calculations;
- overall standings score is not a Constructed score;
- overall Day 2 qualification is not a pure deck-performance conversion;
- Day 2 Constructed statistics describe a field selected partly by Draft performance;
- selection-bias warnings are mandatory.

---

## 5. Round classification

Each tabletop round must be assigned a normalized phase. Event stage, round phase, and actual game format are separate dimensions and must not be collapsed into one field.

Allowed primary values are:

- `draft`;
- `constructed`;
- `playoff`;
- `unknown`.

Every round should retain a stage designation when known:

- `day1`;
- `day2`;
- `playoff`;
- `other`.

Every round should also retain its actual game format, such as `limited`, `modern`, or `unknown`. This is necessary when a playoff uses a different format from the event's Constructed Swiss rounds. For example, a Draft Top 8 has stage `playoff`, phase `playoff`, and game format `limited`.

A normalized round should contain or allow derivation of:

- round ID;
- source round name;
- source round number;
- normalized round number;
- stage;
- phase;
- actual game format;
- whether it is Swiss;
- whether it is playoff;
- whether it counts toward each statistical scope.

An `unknown` round must not be included in primary Constructed statistics until reviewed or explicitly configured.

Round assignments should be verifiable through event configuration, official event information, and collected source data.

---

## 6. Result-type handling

Every normalized player-round result must have an explicit result type.

Recommended normalized values include:

- `played_win`;
- `played_loss`;
- `played_draw`;
- `intentional_draw`;
- `bye`;
- `no_show`;
- `drop_unplayed`;
- `awarded_win_top8_lock`;
- `administrative_result`;
- `unknown`;
- `draft_result`;
- `playoff_result`.

Result normalization must use explicit source evidence for each competitor. The
order of competitors in a source array is not evidence of winner or loser. A
played result is valid only when two identified competitors have a consistent
win/loss or draw/draw pair and compatible match points. Ambiguous records remain
`unknown` and are excluded.

Event-specific corrections must be stored as reviewed configuration with the
source match ID, complete competitor identities and results, a reason, and
reviewable source URLs. In particular, `awarded_win_top8_lock` must not be
inferred from rank, late-round timing, or an apparent win alone.

### 6.1 Handling matrix

| Result type | Constructed points | Win-rate denominator | Matchup matrix | Theoretical round | Notes |
|---|---:|---:|---:|---:|---|
| Played win | 3 | Yes | Yes | Yes | Real Constructed match |
| Played loss | 0 | Yes | Yes | Yes | Real Constructed match |
| Played draw | 1 | Yes | Yes | Yes | Zero wins; remains in the literal valid-match denominator |
| Intentional draw `0-0-3` | 1 | No | No | Yes | Retain separately |
| Bye | 3 | No | No | Yes | No real opponent |
| No-show | 0 | No | No | Conditional | Must be reviewed |
| Drop/unplayed round | 0 | No | No | Yes | Prevents drop inflation |
| Top 8 lock awarded win | 0 | No | No | No, if verified exemption | Retain original source value |
| Other administrative result | Conditional | No by default | No | Conditional | Requires event-specific review |
| Unknown result | No | No | No | Conditional | Must appear in quality report |
| Draft result | No | No | No | No | Excluded from Constructed stats |
| Playoff result | No for primary Swiss metrics | No for primary Swiss win rate | No for primary matrix | No | May be shown separately |

### 6.2 Real wins and losses

Real Constructed wins and losses count toward:

- Constructed points;
- match win rate;
- matchup matrices;
- actual match count;
- theoretical-round completion.

### 6.3 Normal played draws

A normal played draw counts as:

- one Constructed point;
- one played match;
- a draw in matchup W-L-D records.

For the approved Phase 8 target visible win rate, it contributes zero wins and
remains in the valid-match denominator. The compatibility note in section 10
explains why already-published draw-adjusted outputs are not reinterpreted
until P8-04 completes the versioned migration.

### 6.4 Intentional draws reported as `0-0-3`

A result reported as `0-0-3` is treated as an intentional or unplayed draw.

It counts as:

- one point for average-point calculations;
- one theoretical round.

It does not count toward:

- played match count;
- match win rate;
- matchup matrix.

The output must preserve an intentional-draw count so users can understand how many points came from excluded draws.

Do not silently convert `0-0-3` into a normal played draw.

### 6.5 Byes

A verified bye counts as:

- three points for average-point calculations;
- one theoretical round.

It does not count toward:

- played match count;
- match win rate;
- matchup matrix.

Bye counts must be shown in quality or supporting statistics.

### 6.6 No-shows

A no-show is not a valid played match.

A no-show result must be excluded from:

- win rate;
- matchup matrix.

Whether it uses a theoretical round depends on the player’s event participation and the event structure.

Suspected no-shows must be listed in the quality report and must not be silently classified as ordinary played losses.

### 6.7 Drops

When a player drops before completing all scheduled rounds for the relevant scope:

- completed real matches retain their results;
- scheduled but unplayed rounds contribute zero points;
- scheduled but unplayed rounds remain in the theoretical-round denominator;
- unplayed rounds do not count as matches;
- unplayed rounds do not enter the matchup matrix.

This rule is designed to avoid inflating the average score of decks whose players dropped after poor results.

Example:

A player starts a five-round Constructed phase, loses the first two rounds, and drops.

The player contributes:

- 0 Constructed points;
- 5 theoretical Constructed rounds;
- 2 played matches;
- 2 match losses;
- 3 unplayed drop rounds.

The player’s average points per theoretical round is:

`0 / 5 = 0.00`

The player’s played match win rate is:

`0 / 2 = 0.00`

### 6.8 Top 8 lock awarded wins

Some professional events allow a player who has achieved the required number of match wins to stop playing before the end of Swiss rounds.

The source may display an awarded win or another administrative result for a round that was not played.

A result may be normalized as `awarded_win_top8_lock` only when supported by:

- official event rules or fact sheet;
- round-by-round evidence;
- standings evidence;
- event-specific configuration;
- or another reviewable source.

A verified Top 8 lock awarded win:

- contributes zero Constructed points to performance statistics;
- does not count as a played match;
- does not count toward win rate;
- does not enter the matchup matrix;
- does not count as an effective theoretical round;
- must be counted and displayed separately.

The original source result must remain available in raw or normalized metadata.

Do not infer every late-round win by a highly ranked player to be an awarded win.

### 6.9 Playoffs

Quarterfinals, semifinals, and finals are excluded from the primary Swiss statistics.

Reasons include:

- very small sample size;
- different pairing structure;
- elimination incentives;
- insufficient value for the primary archetype matrix.

Playoff results may be shown separately as event context, final placement, or deck detail.

They must not be merged silently into the primary Swiss win rate or matchup matrix.

### 6.10 Disqualified participants

A disqualified participant and their source records must remain in the
normalized archive for provenance, standings reconciliation, and review. Their
status must remain explicitly `disqualified`; do not collapse it into an
ordinary drop.

Every match involving a disqualified participant is excluded as a complete
match unit from:

- played-match win-rate samples;
- archetype matchup matrices;
- primary Constructed match-performance counts.

The opponent side of the same match is also excluded. Removing only one side
would break W-L-D conservation and could retain a result affected by the conduct
that caused the disqualification. Original results, points, rounds, opponents,
decklist, and standings remain available as contextual data. The quality output
must report the disqualified participant and the exclusion without treating a
reviewed disqualification as an unknown or blocking source error.

### 6.11 Mixed-event opportunity-ledger contract

Before calculating mixed-event deck or matchup aggregates, construct an
explicit participant-round ledger for the Day 1, Day 2, and combined
Constructed Swiss scopes.

The Day 1 population is the starting field. The Day 2 population contains only
players with actual or official Day 2 Swiss participation evidence. Day 2
Draft records may establish participation but never contribute Constructed
points, opportunities, win rate, or matchup results. A non-qualifier receives
no Day 2 Constructed theoretical rounds.

For every member of a scope, create one opportunity for every scheduled
Constructed Swiss round in that scope. A source match supplies its explicit
per-competitor result and points. A missing round may be synthesized only when
the participant has a reviewed terminal status:

- `dropped` becomes a zero-point `drop_unplayed` opportunity;
- `disqualified` remains an administrative unplayed opportunity and must not
  be relabeled as an ordinary drop;
- any other missing state fails review rather than being silently counted.

Each row must carry independent point, theoretical-round, effective-round,
win-rate, and matchup inclusion fields. The handling rules in sections
6.1–6.10 determine those fields. In particular, intentional draws and byes may
contribute points without entering match samples, Top 8 lock awards remove one
effective theoretical round, and disqualification exclusion is symmetric for
both sides of every affected match.

The combined scope is a raw-count union of Day 1 and Day 2. Its Constructed
points, theoretical rounds, effective theoretical rounds, match counts, and
special-result counts must reconcile exactly to the two component scopes.

---

## 7. Average points per theoretical round

### 7.1 Purpose

Average points per theoretical round measures point acquisition while limiting distortion from early drops.

It is a deck-performance metric distinct from played match win rate.

### 7.2 General formula

For archetype \(a\):


\[
APPR_a =
\frac{
\sum \text{included Constructed points for decks in } a
}{
\sum \text{effective theoretical Constructed rounds for decks in } a
}
\]

The valid range is normally:

- minimum: `0.00`;
- maximum: `3.00`.

The numerator may include points from:

- played wins;
- played draws;
- intentional draws;
- byes.

The numerator excludes:

- Draft points;
- playoff points;
- unverified administrative results;
- Top 8 lock awarded wins.

### 7.3 Micro-average requirement

Aggregate average points per round must use the total-points divided by total-rounds micro-average.

Do not calculate the simple average of already-calculated event or player averages when denominators differ.

Correct:


\[
\frac{\sum points}{\sum rounds}
\]

Not generally correct:


\[
\frac{\sum player\_averages}{number\_of\_players}
\]

### 7.4 MTGO average points

The current MTGO baseline infers theoretical Swiss rounds from event player count.

For each MTGO deck:

- use the event’s theoretical Swiss round count;
- use the player’s recorded Swiss score;
- treat unplayed rounds after a drop as zero-point theoretical rounds.

For an archetype across multiple events:


\[
MTGO\ APPR_a =
\frac{
\sum recorded\ Swiss\ points
}{
\sum event\ theoretical\ rounds
}
\]

Existing Standard behavior must be regression-tested before generalization.

### 7.5 Pure Constructed Day 1 average

For a `constructed_day2` event:


\[
Day1\ APPR_a =
\frac{
Day1\ Constructed\ points_a
}{
Day1\ effective\ theoretical\ Constructed\ rounds_a
}
\]

All valid starting decks are included unless explicitly excluded by data-quality rules.

Ordinary Day 1 drops retain all scheduled Day 1 Constructed rounds in the denominator.

### 7.6 Pure Constructed Day 2 average

Only players who actually qualified for or were officially included in Day 2 belong to the Day 2 population.

For archetype \(a\):


\[
Day2\ APPR_a =
\frac{
Day2\ Constructed\ points_a
}{
Day2\ effective\ theoretical\ Constructed\ rounds_a
}
\]

The denominator includes scheduled Day 2 Constructed rounds for each Day 2 participant, except verified Top 8 lock exemptions.

Ordinary Day 2 drops do not reduce the theoretical denominator.

Day 2 average points must be displayed with:

- Day 2 deck count;
- effective theoretical round count;
- played match count;
- completion rate;
- intentional-draw count;
- bye count;
- Top 8 lock count;
- awarded-win count;
- selection-bias notice when applicable.

Day 2 average points alone is not sufficient to describe Day 2 performance.

### 7.7 Mixed-event Day 1 Constructed average

For a `mixed` event, calculate only the Day 1 Constructed phase.

Example structure:

- Draft rounds 1–3;
- Constructed rounds 4–8.

Only rounds 4–8 belong to Day 1 Constructed statistics.

For archetype \(a\):


\[
Mixed\ Day1\ APPR_a =
\frac{
Day1\ Constructed\ points_a
}{
Day1\ effective\ theoretical\ Constructed\ rounds_a
}
\]

Draft points and the overall Day 1 standings total are excluded.

### 7.8 Mixed-event Day 2 Constructed average

For a mixed event, the Day 2 population has been selected using combined Draft and Constructed performance.

The calculation is:


\[
Mixed\ Day2\ APPR_a =
\frac{
Day2\ Constructed\ points_a
}{
Day2\ effective\ theoretical\ Constructed\ rounds_a
}
\]

This metric describes performance within the qualified field.

It must not be described as an unbiased continuation of the initial field.

The front end must display a notice similar to:

> Day 2 participants were selected using combined event performance, including Draft where applicable. Day 2 Constructed statistics describe the qualified field and may reflect player-selection effects.

### 7.9 Combined Constructed average

Combined Constructed average includes eligible Day 1 and Day 2 Constructed rounds.

For each player:

- include Day 1 Constructed theoretical rounds if the player was in the Day 1 field;
- include Day 2 Constructed theoretical rounds only if the player qualified for or officially participated in Day 2;
- remove verified Top 8 lock exemptions;
- do not assign Day 2 rounds to players who failed to qualify.

For archetype \(a\):


\[
Combined\ APPR_a =
\frac{
Day1\ points_a + Day2\ points_a
}{
Day1\ effective\ rounds_a + Day2\ effective\ rounds_a
}
\]

This is a phase-weighted micro-average.

It must be labeled as a combined qualified-field statistic rather than a statistic in which every starting player had the same opportunity to play every round.

---

## 8. High-score region

### 8.1 Purpose

The high-score region identifies decks finishing strictly above half of the maximum possible points for the applicable theoretical-round scope.

It is used when:

- an event has no separate Day 2 cut;
- a Constructed phase within a mixed event needs an independent performance threshold;
- MTGO events use the existing high-score logic;
- Day 1 or Day 2 phase performance requires a high-performing subset.

### 8.2 Threshold formula

For \(R\) theoretical rounds:


\[
HighScoreThreshold(R) =
3 \times \left(\left\lfloor \frac{R}{2} \right\rfloor + 1\right)
\]

This is equivalent to taking a score strictly above half of the maximum available points and rounding upward to an achievable three-point win tier.

Examples:

| Theoretical rounds | Maximum points | High-score threshold |
|---:|---:|---:|
| 3 | 9 | 6 |
| 4 | 12 | 9 |
| 5 | 15 | 9 |
| 6 | 18 | 12 |
| 7 | 21 | 12 |
| 8 | 24 | 15 |
| 9 | 27 | 15 |
| 10 | 30 | 18 |
| 11 | 33 | 18 |
| 12 | 36 | 21 |

This preserves the existing MTGO Standard threshold behavior.

### 8.3 High-score count

For archetype \(a\):


\[
HighScoreCount_a =
\text{number of decks in archetype } a
\text{ meeting the threshold}
\]

### 8.4 High-score share

High-score share measures representation inside the high-score population:


\[
HighScoreShare_a =
\frac{
HighScoreCount_a
}{
TotalHighScoreDecks
}
\]

This answers:

> What proportion of the high-score field is this archetype?

### 8.5 High-score conversion

High-score conversion measures the proportion of an archetype’s starting decks that reached the high-score region:


\[
HighScoreConversion_a =
\frac{
HighScoreCount_a
}{
InitialDeckCount_a
}
\]

This answers:

> What proportion of this archetype reached the high-score region?

High-score share and high-score conversion must not be confused.

### 8.6 MTGO Top 8 conversion

If MTGO outputs retain Top 8 conversion from the high-score field, label it separately:


\[
Top8ConversionFromHighScore_a =
\frac{
Top8Count_a
}{
HighScoreCount_a
}
\]

Do not use the generic field name `conversion` for multiple formulas in new schemas.

Preferred explicit field names are:

- `high_score_conversion`;
- `top8_conversion_from_high_score`;
- `day2_conversion`.

### 8.7 Mixed-event Day 1 high-score metrics

For a mixed event:

- use Day 1 Constructed points only;
- use Day 1 Constructed theoretical rounds only;
- include all valid starting Constructed decks;
- exclude Draft points.

These metrics provide a Constructed-only high-performing subset without using Draft-influenced Day 2 qualification.

### 8.8 Day 2 high-score metrics

Day 2 high-score performance may be reported for Day 2 participants.

Where effective theoretical rounds differ because of verified Top 8 locks, evaluate each player against the threshold for that player’s effective theoretical rounds.

Day 2 outputs should include:

- Day 2 high-score count;
- Day 2 high-score share;
- Day 2 high-score rate.

The Day 2 high-score rate is:


\[
Day2HighScoreRate_a =
\frac{
Day2HighScoreCount_a
}{
Day2DeckCount_a
}
\]

Use `rate` rather than `conversion` because the population already consists of Day 2 participants.

When effective round counts vary substantially, the output must expose the round-count distribution and display a comparability warning.

### 8.9 Mixed-event combined scope

Do not create a combined high-score count for a mixed event by adding Day 1
and Day 2 high-score decks. Day 2 is a selected population, players have
different opportunities across the two stages, and the same deck may qualify
in both stage-specific regions. P7-05 therefore reports high-score metrics for
Day 1 and Day 2 only. The all-Constructed-Swiss scope retains combined points,
opportunities, completion, and played-match records, but its high-score fields
are unavailable.

---

## 9. Day 2 participation metrics

### 9.1 Pure Constructed events

For a pure Constructed event with a documented Day 2 cut, report:

#### Day 2 deck count


\[
Day2Count_a =
\text{number of Day 2 participants using archetype } a
\]

#### Day 2 metagame share


\[
Day2Share_a =
\frac{
Day2Count_a
}{
TotalDay2Decks
}
\]

#### Day 2 conversion


\[
Day2Conversion_a =
\frac{
Day2Count_a
}{
InitialDeckCount_a
}
\]

These metrics may be used as deck-performance indicators because advancement is based on the same Constructed event, while still acknowledging player-skill and pairing effects.

### 9.2 Mixed events

For a mixed event, Day 2 participation is influenced by both Draft and Constructed performance.

Therefore:

- Day 2 count may be shown;
- Day 2 share may be shown as a description of the qualified field;
- Day 2 participation may be shown as background information;
- Day 2 conversion must not be presented as a pure deck-performance metric;
- the primary deck-performance conversion for Day 1 should use the Day 1 Constructed high-score region.

If a raw Day 2 qualification rate is displayed for context, it must be labeled clearly as mixed-performance qualification and accompanied by a Draft-influence warning.

---

## 10. Match win rate

### 10.0 Implementation status and compatibility boundary

The formulas in this section are the approved target statistical meaning for
the public label `win rate` / `胜率`, frozen by DEC-053. P8-04 defines the
versioned target contract, fixture, and migration boundary. Existing generated
outputs and the deployed front end retain the pre-P8 draw-adjusted
compatibility fields. P8-06 adds parallel literal records to every MTGO matrix
cell and adds parent/leaf all-match and non-mirror records. It does not
reinterpret the legacy `win_rate` field in place.

A browser must not reinterpret a legacy percentage. A target record declares
`win_rate_method: "wins_over_valid_matches"`; an output without that declaration
remains governed by its existing Schema and producer behavior.

### 10.1 General formula

For valid played matches:


\[
MatchWinRate =
\frac{
Wins
}{
Wins + Losses + Draws
}
\]

Exclude:

- byes;
- intentional draws reported as `0-0-3`;
- no-shows;
- drop/unplayed rounds;
- awarded wins;
- administrative results;
- unknown results;
- Draft matches;
- playoffs from the primary Swiss win rate.

### 10.2 Archetype win rate

For archetype \(a\):


\[
WinRate_a =
\frac{
Wins_a
}{
Wins_a + Losses_a + Draws_a
}
\]

The output must retain:

- wins;
- losses;
- draws;
- valid match count;
- calculated win rate.

Do not store only the final percentage.

Target public rates are decimal fractions rounded to six decimal places. For a
non-empty record, the 95% Wilson interval uses `Wins` as successes and
`Wins + Losses + Draws` as trials, with `z = 1.96`, and rounds each bound to six
decimal places. Empty records use null for both the rate and interval rather
than zero.

### 10.3 All-match and mirror treatment

The primary archetype win rate and primary `overall` value include mirror
matches. A mirror is a valid played match, and normal draws in a mirror remain
visible information under the literal win-rate definition.

The matchup-matrix diagonal displays the real mirror W-L-D record, literal win
rate, confidence interval, and normal sample state. It must not be replaced by
an unavailable dash solely because it is a mirror.

Outputs must additionally retain a non-mirror record and rate as explicit
supporting analysis. Non-mirror is not the only primary visible rate.

Fields should be explicit, for example:

- `non_mirror_record`;
- `non_mirror_win_rate`;
- `all_match_record`;
- `all_match_win_rate`;
- `mirror_match_count`.

The front end should label which rate is displayed.

### 10.4 Day 1 Constructed win rate

Day 1 Constructed win rate uses valid played Constructed matches from Day 1 only.

Advantages:

- reflects the broader initial field;
- reduces Day 2 qualification-selection effects.

Limitations:

- early drops cause non-random missing matches;
- some archetypes may have small samples;
- players who start poorly may contribute fewer actual matches.

Day 1 completion and drop information must be available alongside the rate.

### 10.5 Day 2 Constructed win rate

Day 2 Constructed win rate uses valid played Constructed matches from Day 2 participants only.

It measures performance within the qualified field.

Limitations include:

- qualification selection;
- stronger average player population;
- Draft-influenced selection in mixed events;
- smaller archetype samples;
- Top 8 lock exemptions;
- intentional draws near the end of Swiss.

Day 2 win rate must be displayed with match count and selection-bias context.

### 10.6 All Constructed Swiss win rate

All Constructed Swiss win rate combines valid Day 1 and Day 2 Constructed Swiss matches.

It provides the largest available real-match sample.

It must be calculated from aggregated W-L-D counts:


\[
AllConstructedWinRate =
\frac{
W_{D1} + W_{D2}
}{
W_{D1} + W_{D2} + L_{D1} + L_{D2} + D_{D1} + D_{D2}
}
\]

Do not average the Day 1 and Day 2 percentages.

### 10.7 Default scope

For mixed-format event pages:

- average-point and high-score headline metrics should distinguish Day 1, Day 2, and Combined;
- the primary matchup and overall win-rate view may default to all Constructed Swiss rounds;
- users must be able to switch to Day 1 only and Day 2 only;
- Day 1 win rate should be visible as a comparison;
- the event configuration may override the default if quality checks justify it.

A default-scope override must be recorded in event configuration and explained in generated metadata.

### 10.8 Per-event overview and deck-statistics contract

For the P7-05 mixed-event output, `overview.json` and `decks.json` expose
`day1`, `day2`, and `all_constructed` scopes. Day 1 and Day 2 use their own
participant populations; the combined scope is a micro-aggregation of the
underlying opportunity rows and does not pretend that all starting players had
equal Day 2 access.

P9-04 extends this contract by explicit event structure:

- `constructed_day2` exposes `day1`, `day2`, and `all_constructed`; its
  primary advancement metric is `day2_conversion`, calculated for the Day 2
  field and each parent/subtype as evidenced Day 2 decks divided by the
  corresponding initial deck count. High-score fields are unavailable for
  this structure and it must not inherit the mixed Draft-selection warning.
- `constructed_single_stage` exposes only `all_constructed`; it has no
  fictional Day 1 or Day 2 scope. Its primary advancement metric is
  `high_score_conversion`, using the threshold in section 8 and each deck's
  effective theoretical round count.
- `mixed` retains its existing three scopes, selection-bias warning, stage
  high-score metrics, and byte-compatible output.

Rates are recalculated from their raw denominators. Parent/subtype additive
counts must conserve deck counts, points, theoretical and effective rounds,
played W-L-D participations, and available high-score counts. Existing
draw-adjusted records remain compatibility fields; the nested
`literal_record` continues to declare and calculate
`wins_over_valid_matches`.

Every overview parent row is calculated directly from the participants and
opportunities assigned to that parent. The output also includes an explicit
`Unknown` parent bucket in deck-count, opportunity, point, completion, and
played-record denominators. Unknowns must not be dropped or redistributed.

When an observed parent defines maintained subtypes, its row contains the
complete maintained subtype list in taxonomy order, including zero-observation
subtypes. Each subtype row is calculated directly from participants assigned
to that subtype. Subtype deck counts, points, theoretical rounds, effective
rounds, result counts, and all-match W-L-D records must sum to the parent row.
The parent remains the default view. A parent is marked expandable only when
the maintained taxonomy defines at least two subtypes.

The played records expose raw W-L-D counts, match count, win rate, and a 95%
Wilson interval. Both all-match and non-mirror records are retained; the
non-mirror record excludes opponents assigned to the same displayed identity.
The Phase 8 consumer applies the DEC-060 shared low-sample presentation warning
when the valid-match count is fewer than 20. Consumers must still use the
retained sample size and interval rather than treating the warning as a
reliability gate or treating an unavailable rate as zero.

The participant-level `decks.json` preserves source-published player identity,
standing context, submitted decklist, classification, and the same three
statistical scopes. A disqualified participant's archival deck and official
Constructed point fields remain present as frozen by the opportunity ledger,
while all affected played matches remain excluded from win-rate and later
matchup calculations.

---

## 11. Matchup matrix

### 11.1 Matrix definition

For a row archetype \(A\) against column archetype \(B\), store the result from archetype \(A\)’s perspective:

- wins by \(A\);
- losses by \(A\);
- draws;
- valid match count;
- match win rate.


\[
MatrixWinRate_{A,B} =
\frac{
Wins_{A,B} + 0.5 \times Draws_{A,B}
}{
Wins_{A,B} + Losses_{A,B} + Draws_{A,B}
}
\]

The inverse cell must reconcile:

- \(Wins_{A,B} = Losses_{B,A}\);
- \(Losses_{A,B} = Wins_{B,A}\);
- draws must match;
- valid match counts must match.

### 11.2 Primary exclusions

The primary matrix excludes:

- mirrors, unless a mirror cell is shown separately;
- byes;
- `0-0-3` intentional draws;
- no-shows;
- unplayed drop rounds;
- awarded wins;
- administrative results;
- unknown result types;
- Draft;
- playoffs.

### 11.3 Unknown archetypes

Matches involving a valid but unclassified deck must remain available for reconciliation and quality reporting.

The front end may hide the `Unknown` row and column by default, but the generated data should preserve them or preserve equivalent accounting information.

A known archetype’s overall record against an Unknown opponent must not be silently attributed to another archetype.

### 11.4 Scope controls

When data is available, the tabletop matrix should support:

- `all_constructed_swiss`;
- `day1_constructed`;
- `day2_constructed`.

Playoff matches may be provided in a separate contextual dataset but not as a primary matrix scope.

### 11.5 Single-event matrix

A single-event matrix uses only matches from one event.

Every matrix output must identify:

- source;
- format;
- event ID;
- event name;
- scope;
- included rounds;
- excluded result counts;
- generation time;
- schema version.

### 11.6 Multi-event matrix

A multi-event tabletop matrix may combine multiple events only when they are compatible.

Minimum compatibility requirements are:

- same Constructed format;
- same source product;
- supported normalized schema versions;
- compatible round scopes;
- no unresolved event-level round classification;
- events explicitly selected or enabled for consolidation.

Combine underlying counts:


\[
CombinedW = \sum W_i
\]


\[
CombinedL = \sum L_i
\]


\[
CombinedD = \sum D_i
\]

Then calculate:


\[
CombinedWinRate =
\frac{
CombinedW
}{
CombinedW + CombinedL + CombinedD
}
\]

Normal played draws remain in the denominator and do not contribute a
fractional win. This is the same literal `wins_over_valid_matches` method used
by single-event target records.

Do not calculate the simple average of event win-rate percentages.

The output must list every included event ID.

MTGO data must never be included in a tabletop multi-event matrix.

The initial cross-structure presentation policy exposes only
`all_constructed` when two or more events are selected. This is the common
scope across `mixed`, `constructed_day2`, and
`constructed_single_stage`. The combined matrix aggregates underlying valid
Constructed Swiss W-L-D counts and does not average event rates.

When exactly one event is selected, the consumer may expose every scope
declared by that event. A single-stage event exposes only `all_constructed`;
the absent Day 1 and Day 2 scopes are omitted rather than presented as empty
data. When multiple events are selected, Day 1 and Day 2 controls may remain
visible as disabled explanatory controls, but they cannot select or retain a
stage-specific scope. Adding a second event while a stage-specific scope is
active switches deterministically to `all_constructed`.

This conservative presentation rule does not assert that compatible Day 1 or
Day 2 raw-count aggregation is mathematically impossible. Enabling such a
multi-event scope later requires a separate reviewed compatibility contract
for event structures, cut rules, missing stages, and selection effects.

### 11.7 Multiple decks or deck changes

If event rules allow a player to use different Constructed decks in different phases, the normalized data must associate each match with the correct deck and archetype.

Do not assign every match automatically to the player’s first or final deck without verification.

If the correct phase-specific deck cannot be determined, affected matches must be excluded and reported.

### 11.8 Hierarchical parent and subtype matchups

The default matchup matrix remains the parent-archetype matrix. A hierarchical
matchup output may additionally allow the row axis and column axis to expand
independently from a parent archetype into its defined subtypes.

The statistical generator must retain each eligible competitor's stable parent
archetype ID and selected subtype ID, when one is selected. It must aggregate
canonical directed W-L-D counts at the most specific selected identity and make
the following views derivable from those counts:

- parent archetype against parent archetype;
- subtype against parent archetype;
- parent archetype against subtype;
- subtype against subtype.

Every displayed rate must be calculated from the summed W-L-D counts using the
formula in section 11.1. Do not average already-calculated parent, subtype, row,
column, event, or time-window percentages.

Collapsing all subtype nodes beneath a parent must reproduce that parent's
parent-level W-L-D counts exactly. Expanding or collapsing either axis must not
change the number of underlying eligible matches, double-count a match, or
change the fully collapsed parent matrix.

A parent archetype with no subtype definitions is a complete non-expandable
node. A classified deck under such a parent correctly has `subtype_id: null`;
this is not a residual or Unknown classification. A parent with exactly one
defined subtype is also non-expandable in the front end, although the generated
data may retain that subtype for audit and future compatibility. Expandability
is determined by the maintained taxonomy, not by how many subtype samples
happen to appear in one time window.

The current Standard and Modern rules contain no classified deck under a parent
that defines subtypes without also selecting one of those subtypes. If that
state appears later, it is a blocking classification or data-quality condition
under the approved no-residual policy. The generator must not silently omit the
deck, attribute it to another subtype, or invent an `Other` or `Unspecified`
subtype.

Unknown archetypes remain governed by section 11.3. A subtype is never treated
as an unrelated parent archetype.

Before the hierarchical matchup front end is accepted, Standard must be run
through the same shared hierarchical calculation used for Modern. Its fully
collapsed parent matrix must reproduce the existing Standard parent-level
matchup output. This migration is required even if the legacy Standard public
files remain available temporarily as compatibility outputs.

### 11.9 P7-06 mixed-event matchup contract

The event-level Melee matchup document uses the scope IDs `day1`, `day2`, and
`all_constructed`, with `all_constructed` as the default. Only complete
physical matches for which both opportunity-ledger rows have
`matchup_included: true` enter a matrix. Each included physical match produces
exactly two directed observations. A one-sided inclusion, non-reciprocal
opponent reference, or non-inverse result is a blocking error.

The canonical matrix level is the complete leaf set derived from the P7-05
event hierarchy. A leaf is a maintained subtype for a subtype-defining parent,
the parent itself when it defines no subtype, or the explicit Unknown node.
All maintained leaves and every row-column cell are emitted even when their
sample is zero. The complete parent matrix is obtained by independently
rolling both leaf axes up to their parents; it is not recalculated from
percentages.

Sibling-subtype matches are non-mirror observations at leaf level but are
parent mirrors after collapse. Consequently, subtype overall records exclude
only the same leaf, while parent overall records exclude the complete parent
diagonal. Parent non-mirror records must reproduce the corresponding P7-05
overview records exactly.

Each cell and overall record contains raw wins, losses, draws, valid-match
count, win rate, and a 95% Wilson interval. A zero-sample rate and interval are
`null`. Existing Tabletop output may retain `low_sample_threshold: null` as a
compatibility field; the Phase 8 consumer applies the DEC-060 shared
presentation value of 20 to both source products. A future generated-contract
migration may publish that value directly, but must preserve the same warning
meaning and source separation.

Excluded physical matches remain counted by reviewed reason for each scope:
bye, intentional draw, no-show, verified Top 8 lock award, administrative
result, disqualified participant, or unknown. Draft, playoffs, and ordinary
unplayed scheduled opportunities never become source matchup matches.

---

## 12. Confidence intervals and sample size

### 12.1 Required counts

Every displayed win rate must retain its sample size.

A percentage without a valid match count is incomplete.

### 12.2 Confidence interval

Where confidence intervals are shown, use a 95% Wilson score interval.

For a record containing draws, use:


\[
effective\ wins = wins + 0.5 \times draws
\]


\[
n = wins + losses + draws
\]

The resulting Wilson interval is an approximation for the half-win treatment of draws and should be documented in output metadata.

### 12.3 Low-sample warnings

The Phase 8 display threshold is shared across MTGO and Tabletop matchup
consumers:

- fewer than 20 valid matches: low-sample warning;
- 20 or more valid matches: no warning solely because of sample count.

A warning does not require deleting the statistic and reaching 20 matches does
not imply that the estimate is reliable. The actual sample count and 95%
Wilson interval remain available for interpretation.

The front end should reduce visual certainty rather than pretending the value is precise.

### 12.4 No valid matches

When valid match count is zero:

- win rate must be `null`;
- confidence interval must be `null`;
- the front end must display `N/A` or an equivalent unavailable label;
- do not display `0%`.

---

## 13. Metagame share

### 13.1 Initial metagame share

For archetype \(a\):


\[
InitialMetagameShare_a =
\frac{
InitialDeckCount_a
}{
TotalValidInitialDecks
}
\]

The denominator includes valid classified decks and valid `Unknown` decks unless a generated field explicitly states otherwise.

Missing or invalid decklists must be reported separately.

### 13.2 Day 2 metagame share

For archetype \(a\):


\[
Day2MetagameShare_a =
\frac{
Day2DeckCount_a
}{
TotalValidDay2Decks
}
\]

For mixed events, this describes the qualified field but is not a pure Constructed conversion result.

### 13.3 High-score share

High-score share uses the high-score population as its denominator and must not be labeled simply as metagame share.

---

## 14. Day 2 performance presentation

### 14.1 Day 2 average is necessary but insufficient

Day 2 average points should be displayed, but it must not be used alone.

For each archetype, the Day 2 view should include, where available:

- Day 2 deck count;
- Day 2 field share;
- Day 2 average points per effective theoretical Constructed round;
- Day 2 high-score count;
- Day 2 high-score share;
- Day 2 high-score rate;
- Day 2 non-mirror match win rate;
- Day 2 W-L-D record;
- valid match count;
- effective theoretical round count;
- completed-round rate;
- intentional-draw count;
- bye count;
- Top 8 lock player count;
- awarded-win count;
- confidence interval;
- low-sample warning.

### 14.2 Why multiple metrics are required

Average points and match win rate measure different things.

Average points per theoretical round:

- includes the effect of ordinary drops;
- includes standings points from byes and intentional draws;
- uses scheduled opportunity as the denominator;
- is sensitive to official exemptions.

Match win rate:

- uses only played matches;
- excludes byes and intentional draws;
- is not directly penalized for unplayed drop rounds;
- is more suitable for matchup analysis.

High-score rate:

- measures how often a Day 2 deck reached a strong Day 2 point result;
- may be sensitive to varying effective round counts.

These metrics must be interpreted together.

### 14.3 Top 8 lock reporting

When Top 8 lock rules affect Day 2:

- show the number of affected players;
- show the number of exempted rounds;
- show the number of source-reported awarded wins;
- exclude those wins from played-match statistics;
- exclude verified exempted rounds from effective theoretical rounds;
- include an event-level explanatory note.

If lock status is uncertain, do not silently apply the exemption.

---

## 15. Drop and coverage diagnostics

### 15.1 Purpose

Day 1-only statistics can be affected by early drops.

Day 1 plus Day 2 statistics can be affected by qualification selection.

The system must expose diagnostics for both forms of bias rather than claiming that one scope is unbiased.

### 15.2 Completion rate

For a population:


\[
CompletionRate =
\frac{
CompletedOrOfficiallyExemptTheoreticalRounds
}{
ScheduledTheoreticalRounds
}
\]

The output should also retain:

- theoretical rounds;
- played matches;
- intentional draws;
- byes;
- exempted rounds;
- unplayed drop rounds.

### 15.3 Archetype-level completion

Completion diagnostics should be available per archetype when sample size permits.

This helps identify whether one archetype’s Day 1 match sample is unusually affected by early drops.

### 15.4 Drop distribution

Quality or supporting output should record:

- number of players dropping;
- round after which they dropped;
- record at drop when available;
- archetype;
- number of unplayed theoretical rounds.

### 15.5 Phase comparison

For each archetype with sufficient samples, the system should retain:

- Day 1 win rate;
- Day 2 win rate;
- all Constructed Swiss win rate;
- difference between Day 1 and all-Constructed rate;
- difference between Day 1 and Day 2 rate.

A large difference should produce a contextual warning, not an automatic claim of causation.

The initial recommended difference warning is five percentage points when both compared samples meet the configured minimum.

---

## 16. MTGO-specific statistics

### 16.1 Time ranges

MTGO statistics are aggregated over complete event-date ranges such as:

- 1 week;
- 4 weeks;
- 12 weeks;
- 36 weeks when retained by the existing product.

The exact available ranges must be listed in generated index data rather than assumed only by the front end.

### 16.2 Latest complete week

The existing Standard implementation identifies a latest complete calendar week.

This behavior must be preserved by regression tests before the pipeline becomes format-parameterized.

### 16.3 Hierarchical range statistics

Every MTGO rolling-range document continues to use parent archetypes as its
primary, default aggregation. When an observed parent defines maintained
subtypes, its statistics row additionally contains the complete maintained
subtype list in taxonomy order. A parent with no maintained subtype definitions
has no subtype collection.

Each subtype row is calculated directly from the deck records assigned to that
subtype. It must contain:

- stable subtype ID, parent ID, and display name;
- deck count and its share of the parent count;
- high-score count and share of the range-wide high-score population;
- Top 8 count and share of the range-wide Top 8 population;
- conversion, using that subtype's Top 8 count divided by its high-score count;
- average points per theoretical round from that subtype's own records;
- average construction deviation from that subtype's own four-week base.

Do not derive subtype rates by apportioning a parent rate or by averaging
already-calculated percentages. For each parent, subtype deck, high-score, and
Top 8 counts must sum exactly to the parent counts. A maintained subtype with no
records in the selected range remains present with zero counts and null
sample-dependent rates. This makes taxonomy membership and expandability
independent of short-lived event volume.

The parent row remains authoritative and must reproduce the Phase 6 parent-only
result byte-for-byte when supplementary subtype fields and newly exposed stable
parent IDs are projected away. Adding the subtype layer must not change totals,
Unknown handling, thresholds, range dates, or parent ranking.

### 16.4 Average deck and deviation

Average decklists, representative decklists, Core/Flex classification, construction deviation, and recent construction change are MTGO product features.

These calculations are not automatically required for tabletop event pages.

Their detailed existing behavior should be documented and regression-tested during the Standard baseline phase before intentional formula changes.

For a parent with maintained subtypes, each subtype's representative deck,
average deck, Core/Flex list, deviation, and recent construction change are
recalculated from that subtype's own records. The same four-week base,
minimum-sample threshold, and formulas used by the parent calculation apply
independently to each subtype. A subtype below the base threshold may still
publish its best observed deck, but its average-deck sample is zero and its
base-dependent values remain unavailable. A zero-observation subtype publishes
no best deck and an empty average-deck state.

### 16.5 Weekly Pickup

Weekly Pickup remains an MTGO-specific product feature.

It must not be applied automatically to isolated tabletop events.

### 16.6 MTGO matchup source

MTGO matchup data may come from a different collection mechanism than MTGO decklist and standings data.

The generated metadata must identify the source and coverage of matchup records.

Do not imply complete match coverage when only a subset is available.

For a format with hierarchical matchup data, metadata must report:

- the matchup source name;
- the number of admitted official events;
- the number with and without stored matchup archives;
- the total stored matchup archives;
- the number of stored archives that do not correspond to an admitted official
  statistics event.

These are coverage diagnostics, not estimates of unobserved match results. A
format without a manually published Weekly Pickup index must use a null Pickup
catalog reference; candidate files are not public statistics.

Weekly Pickup remains parent-archetype based. Stable parent IDs determine
whether an archetype is already known, while subtype ID and display name may be
retained as informational review fields. Subtypes do not split the base pack,
the existing/new decision, or the Pickup population.

### 16.7 Phase 8 MTGO source-completeness contracts

Phase 8 must expose two separate completeness products. They must not be merged
or presented as general confidence in all MTGO statistics.

MTGO matchup-source completeness uses formula version
`videre-range-coverage-v1`. For the selected closed interval:

\[
ExpectedEvents =
AvailableEvents + DeferredEvents + MissingEvents
\]

\[
MatchupCompleteness =
\frac{AvailableEvents}{ExpectedEvents}
\]

An available event has a usable approved matchup archive. A deferred event is
an admitted event whose source is known to be temporarily incomplete and is
eligible for retry. A missing event is admitted but has no usable archive and
is not currently deferred. Excluded events are retained as diagnostics but do
not enter either numerator or denominator. If the admitted expected population
cannot be established or is empty, the rate is unavailable, not zero.

The output must retain:

- expected or admitted official events in the selected interval;
- events with a usable approved matchup archive;
- missing, deferred, and excluded events;
- the raw numerator and denominator;
- the resulting rate or an explicit unavailable state;
- source and formula version.

MTGO high-score decklist completeness uses formula version
`mtgo-high-score-binomial-v1`. It is an explicit model estimate, not a claim
that tournament pairings are independent.

For each eligible event, infer its Swiss round count \(R\) from the existing
reviewed MTGO player-count-to-round table. Let \(T\) be the existing event
high-score threshold in match points and let \(k\) be the minimum decisive-win
count that reaches that threshold. Under the documented fair, decisive,
independent-match model:

\[
ExpectedHighScoreDecklists_e =
N_e \sum_{w=k_e}^{R_e}
\binom{R_e}{w} \left(\frac{1}{2}\right)^{R_e}
\]

where \(N_e\) is the event player count. Keep each event expectation unrounded,
then sum:

\[
ExpectedHighScoreDecklists =
\sum_e ExpectedHighScoreDecklists_e
\]

\[
HighScoreDecklistCompleteness =
\min\left(
\frac{ObservedUsableHighScoreDecklists}
{ExpectedHighScoreDecklists},
1
\right)
\]

The displayed expected count is the summed raw expectation rounded to the
nearest integer with halves rounded up. The displayed rate is rounded to six
decimal places. `exceeds_model` is true when the observed count is greater than
the raw expectation even though the displayed completeness rate is capped at
one.

An event is unsupported, excluded from both observed and expected totals, and
reported explicitly if it lacks a valid player count, a reviewed round model,
the applicable Swiss high-score threshold, or the Swiss-score evidence needed
to identify observed high-score decklists. Unsupported events never contribute
an assumed zero. If no eligible event remains, the result is unavailable.

Official MTGO playoff archives have a stricter source-admission boundary.
Before a newly fetched event may be normalized, stored, or added to the fetched
ledger, every published deck must have one matching standing with a positive
Swiss rank and non-negative Swiss score and one matching positive final rank.
All three source collections must use non-empty, unique player identifiers.
Temporarily absent records or values use the bounded retry and publication
grace policy; invalid types, values, or duplicate identities are structural
failures.

This admission rule prevents new unsupported archives. The two known retained
legacy defects (`12847150` and `12844304`) were repaired from validated official
source payloads in `P8-REPAIR-MTGO-EVENTS-12847150-12844304`. The repair
preserved event identity, format, player identities, final ranks, and deck
contents while restoring the missing Swiss evidence.

Statistical consumption is now fail closed. Every retained player consumed by
the MTGO statistics generator must have a non-negative integer Swiss score and
a positive integer final rank. Missing or invalid evidence is an error and must
not be coerced to zero or a fallback placement. A full retained-archive audit
must report zero semantic exceptions before affected statistics are generated
or published.

The output must retain:

- the reviewed theoretical high-score decklist count derived from eligible
  event round and participant structures;
- the observed usable high-score decklist count;
- unsupported or indeterminate events;
- the raw numerator and denominator;
- the resulting rate or an explicit unavailable state;
- source and formula version.

Both completeness outputs retain their formula version, interval, raw counts,
event identities, exclusions or unsupported reasons, rate, and unavailable
reason. The browser must never estimate either denominator.

P8-06 publishes one range document for each configured 1-, 4-, 12-, and
36-week interval at:

```text
stats/<format>/mtgo/completeness/<weeks>w.json
```

The catalog is:

```text
stats/<format>/mtgo/completeness/index.json
```

The catalog and range documents are generated for Standard and Modern under
the `completeness_reporting` capability. MTGO metadata exposes them through
`completeness_catalog`.

The current Videre fetch layer has no durable deferred-event ledger.
Accordingly, production completeness does not infer `deferred` from a missing
archive. An admitted event without a usable non-empty archive is `missing`
unless a future reviewed source-status record supplies explicit temporary
incompleteness evidence. This keeps the rate reproducible and prevents an
unverified absence from being removed from the denominator.

P8-06 also adds `literal_record` to every MTGO parent and leaf matrix cell.
Each range document exposes `parent_match_records` and `leaf_match_records`;
each identity record contains `all_matches`, `non_mirror`, and the physical
`mirror_match_count`. The existing `parent_overall`, `leaf_overall`, Standard
name aliases, and their draw-adjusted compatibility fields remain available
until the production front end migrates in P8-09.

### 16.8 Weekly MTGO Top 8 decklist presentation data

The weekly Top 8 product groups admitted MTGO events by complete Monday-through-
Sunday weeks. Every admitted event in that week contributes ranks 1 through 8
exactly once. It must preserve event identity, date, finish, player count,
stable parent and subtype identity, source provenance, and explicit missing-
deck states. A missing deck remains a ranked placeholder with null identity,
exact deck, and comparison values; it must not be omitted or silently replaced.

Selecting one entry displays the exact event deck, not a representative deck.
If the selected identity belongs to a subtype-defining parent, its deviation
and comparison average use that subtype's independently calculated construction
base under section 16.4. A parent with no maintained subtype uses its parent
base. The weekly product must not create a cross-subtype average or reclassify a
deck in browser code.

P8-05 formalizes this product as
`stats/<format>/mtgo/top8/YYYY-Www.json`, with discovery through
`stats/<format>/mtgo/top8/index.json`. P8-07 extends the producer with one
immutable `YYYY-Www-bases.json` companion for each retained weekly document.
Every available placement embeds the exact main deck and sideboard, carries a
stable identity, and references the companion base whose `base_period_end`
equals the selected week's Sunday. Where the four-week minimum sample exists,
the producer also emits deviation and card differences using the section 16.4
formula. Where it does not, `base_status` is `unavailable` and deviation fields
are null rather than inferred.

The catalog accumulates complete weeks from the first safely established
historical baseline, 2026-W30. Once an index entry declares
`immutable_weekly_comparison_bases`, regeneration must produce byte-identical
week and base documents or fail before overwriting either file. Earlier weeks
are not backfilled unless a separate task can reproduce and validate their
original same-period construction inputs.

---

## 17. Tabletop per-event outputs

Each tabletop event should generate enough information for the following logical outputs.

### 17.1 Event metadata

Includes:

- event ID;
- event name;
- format;
- source URL;
- event structure;
- event dates;
- scheduled rounds;
- phase assignments;
- advancement information;
- fetch time;
- generation time;
- schema version.

### 17.2 Overview

Includes:

- deck counts;
- metagame shares;
- average-point metrics;
- high-score metrics;
- Day 2 metrics;
- win-rate metrics;
- sample sizes;
- exclusion counts;
- warnings.

P8-07 preserves the existing draw-adjusted overview records as compatibility
data and adds `literal_record` to each all-match and non-mirror record. The
literal method is wins divided by wins, losses, and normal played draws.

### 17.3 Deck data

Includes:

- player;
- archetype ID;
- display archetype;
- decklist;
- standings context;
- phase participation;
- relevant records.

### 17.4 Matchup data

Includes:

- scope;
- included events;
- matrix W-L-D counts;
- win rates;
- confidence intervals;
- sample warnings;
- excluded result counts.

### 17.5 Quality data

Includes:

- source record totals;
- missing decklists;
- Unknown classifications;
- classification conflicts;
- unknown rounds;
- unknown results;
- no-shows;
- byes;
- intentional draws;
- drops;
- awarded wins;
- reconciliation failures;
- blocking and non-blocking warnings.

---

## 18. Rounding and output precision

### 18.1 Stored values

Generated JSON should preserve enough precision for recalculation and display.

Recommended storage:

- counts as integers;
- rates as decimal fractions from `0` to `1`;
- average points as numeric values from `0` to `3`;
- confidence bounds as decimal fractions;
- raw numerator and denominator fields alongside calculated values.

### 18.2 Display values

Recommended front-end display:

- metagame and conversion rates: one decimal percentage point;
- win rates: one decimal percentage point;
- average points per round: two decimal places;
- confidence intervals: one decimal percentage point;
- counts: integers.

Example:

- stored win rate: `0.5346`;
- displayed win rate: `53.5%`.

### 18.3 Calculation order

Do not round intermediate W-L-D counts, point totals, or denominators.

Round only the final stored or displayed calculated value according to the output contract.

---

## 19. Data-quality gates

An event must not be silently published as complete when primary statistics cannot be trusted.

Potential blocking conditions include:

- event not present in whitelist;
- format mismatch;
- missing event structure;
- substantial unresolved round classification;
- missing primary standings;
- match rows that cannot be associated with players;
- duplicate identities that materially affect results;
- decklist coverage below an approved threshold;
- unresolved result types affecting primary statistics;
- failure to reconcile matchup cells;
- JSON Schema failure.

Non-blocking warnings may include:

- small samples;
- limited Day 2 population;
- a small number of Unknown decks;
- confirmed byes;
- confirmed intentional draws;
- confirmed drops;
- verified Top 8 lock exemptions.

Blocking thresholds must be configurable and documented.

For the Phase 5 normalized-event boundary, the following deterministic checks
apply before any classification or statistical output exists:

- the event must be explicitly enabled and verified in the whitelist;
- the normalized event must pass its versioned JSON Schema before and after
  quality assessment;
- reviewed metadata, raw-artifact integrity digests, stable identities, and all
  cross-record references must reconcile;
- match result semantics and Constructed/matchup eligibility must agree with the
  reviewed round phase, actual format, Swiss flag, and per-competitor result;
- at least one verified played match must belong to the configured Constructed
  Swiss scope;
- any unresolved or blocking issue makes the event non-publishable.

A missing or unavailable decklist is a non-blocking warning at this ingestion
boundary. It does not make a match result untrustworthy by itself. This rule
does not establish a decklist-coverage threshold for later classification or
public statistics; that coverage threshold remains unresolved. The matchup
sample presentation warning is separately resolved by DEC-060: the Phase 8
consumer warns below 20 valid matches without treating the threshold as a
reliability or publication gate.

---

## 20. Required statistical tests

Automated tests must cover at least:

- high-score threshold examples;
- average points using theoretical rounds;
- early `0-2` drop behavior;
- early `0-9` or equivalent drop behavior;
- played win and loss handling;
- normal played draw handling;
- `0-0-3` intentional-draw exclusion from win rate;
- bye exclusion from win rate;
- no-show exclusion;
- awarded-win exclusion;
- disqualified-participant match exclusion with both match sides retained;
- Top 8 lock theoretical-round exemption;
- Draft exclusion;
- playoff exclusion;
- Day 1 scope;
- Day 2 scope;
- Combined Constructed scope;
- non-qualifiers not receiving Day 2 theoretical rounds;
- W-L-D aggregation;
- mirror exclusion;
- matchup inverse-cell reconciliation;
- multi-event raw-count aggregation;
- missing data returning `null`;
- low-sample warnings;
- source separation between MTGO and tabletop data.

Regression tests must also preserve the existing Standard outputs before major refactoring.

---

## 21. Interpretation requirements

The front end and generated metadata must avoid misleading labels.

Use explicit labels such as:

- Initial metagame share;
- High-score share;
- High-score conversion;
- Day 2 field share;
- Day 2 conversion;
- Day 1 Constructed average points;
- Day 2 Constructed average points;
- Combined Constructed average points;
- Day 1 Constructed win rate;
- Day 2 Constructed win rate;
- All Constructed Swiss win rate;
- Non-mirror win rate.

Do not use a generic label such as `conversion` when multiple conversion denominators exist.

Do not describe:

- mixed-event Day 2 qualification as pure deck conversion;
- awarded wins as played match wins;
- byes as matchup wins;
- intentional draws as played match draws;
- missing values as zero;
- a low-sample percentage as conclusive;
- combined Day 1 and Day 2 data as free from selection bias.

---

## 22. Approved default presentation

### 22.1 Pure Constructed with Day 2

Default overview should show:

- initial metagame;
- Day 1 performance;
- Day 2 participation and conversion;
- Day 2 performance;
- Combined Constructed performance;
- quality and sample warnings.

Default matchup scope may use all Constructed Swiss rounds, with Day 1 and Day 2 switches.

### 22.2 Pure Constructed without Day 2

Default overview should show:

- initial metagame;
- average points per theoretical round;
- high-score count;
- high-score share;
- high-score conversion;
- overall Constructed win rate;
- quality and sample warnings.

### 22.3 Mixed events

Default overview should separate:

- Day 1 Constructed;
- Day 2 Constructed;
- Combined Constructed.

For mixed events:

- Day 1 high-score performance is the primary Constructed-only advancement-style metric;
- Day 2 statistics describe the selected qualified field;
- Day 2 average must be accompanied by Day 2 win rate, high-score rate, sample size, completion, and Top 8 lock information;
- all Constructed Swiss may be the default matchup scope;
- Day 1-only and Day 2-only switches are required;
- a selection-bias notice is required.

---

## 23. Unresolved implementation details

The following may be finalized during implementation without changing the approved statistical principles:

- exact low-sample visual style;
- exact configurable decklist-coverage blocking threshold;
- exact wording of front-end tooltips;
- whether confidence intervals are displayed directly in every table cell or in details;
- how hidden `Unknown` matrix rows are exposed to users;
- event-specific detection method for Top 8 lock results;
- event-specific handling of unusual administrative penalties.

Any resolution must be recorded in configuration, tests, or `DECISIONS.md` as appropriate.

Implementation details must not contradict the formulas and exclusions in this document.
