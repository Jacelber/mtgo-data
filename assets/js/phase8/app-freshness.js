"use strict";

function freshnessNumber(value) {
  return value === null || value === undefined || Number.isNaN(Number(value))
    ? t("freshness.unknown")
    : String(value);
}

function freshnessPercent(value) {
  return value === null || value === undefined || Number.isNaN(Number(value))
    ? t("freshness.unknown")
    : pct(value);
}

function freshnessPeriod(period) {
  return period?.start && period?.end
    ? `${period.start} – ${period.end}`
    : null;
}

function freshnessRatio(observed, expected, rate) {
  return `${freshnessNumber(observed)} / ${freshnessNumber(expected)} · ${freshnessPercent(rate)}`;
}

function freshnessStrip(items) {
  const facts = items.filter(Boolean);
  return `<section class="freshness-strip" aria-label="${escapeHtml(t("freshness.label"))}">
    <strong class="freshness-title">${escapeHtml(t("freshness.label"))}</strong>
    <span class="freshness-facts">${facts.map(item => {
      const [key, label, rawValue] = item;
      const value = rawValue === null || rawValue === undefined || rawValue === ""
        ? t("freshness.unknown")
        : rawValue;
      const unknown = String(value).includes(t("freshness.unknown")) ? " freshness-unknown" : "";
      return `<span class="freshness-fact${unknown}" data-freshness-key="${escapeHtml(key)}">
        <small>${escapeHtml(t(`freshness.${label}`))}</small><b>${escapeHtml(value)}</b></span>`;
    }).join("")}</span>
  </section>`;
}

let freshnessLayoutFrame = 0;

function updateFreshnessLayouts(root = document) {
  root.querySelectorAll(".freshness-strip").forEach(strip => {
    strip.classList.remove("freshness-stacked");
    const title = strip.querySelector(".freshness-title");
    const facts = strip.querySelector(".freshness-facts");
    const style = getComputedStyle(strip);
    const innerWidth = strip.clientWidth
      - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
    const requiredWidth = title.scrollWidth
      + (parseFloat(style.columnGap) || 0) + facts.scrollWidth;
    strip.classList.toggle("freshness-stacked", requiredWidth > innerWidth + 0.5);
  });
}

function scheduleFreshnessLayouts(root = document) {
  cancelAnimationFrame(freshnessLayoutFrame);
  freshnessLayoutFrame = requestAnimationFrame(() => updateFreshnessLayouts(root));
}

window.addEventListener("resize", () => scheduleFreshnessLayouts());

function statisticsFreshness(meta, range, completeness) {
  const highScore = completeness.high_score_decklist_completeness || {};
  return freshnessStrip([
    ["period", "period", freshnessPeriod(range.period)],
    ["data-updated", "data_updated", meta.data_updated ? dateText(meta.data_updated) : null],
    ["rules-updated", "rules_updated", meta.rules_updated ? dateText(meta.rules_updated) : null],
    ["decks", "deck_count", freshnessNumber(range.total_decks)],
    ["high-score", "high_score_count", freshnessNumber(range.total_high_score)],
    ["top8", "top8_count", freshnessNumber(range.total_top8)],
    ["high-score-completeness", "high_score_completeness", freshnessRatio(
      highScore.observed_decklist_count,
      highScore.expected_decklist_count_display ?? highScore.expected_decklist_count,
      highScore.completeness_rate
    )],
  ]);
}

function landingFreshness(landing, range, completeness) {
  const highScore = completeness?.high_score_decklist_completeness || {};
  return freshnessStrip([
    ["period", "period", freshnessPeriod(landing.week)],
    ["events", "event_count", freshnessNumber(landing.populations?.current?.event_count)],
    ["decks", "deck_count", freshnessNumber(range?.total_decks)],
    ["high-score", "high_score_count", freshnessNumber(
      landing.populations?.current?.high_score_count
    )],
    ["top8", "top8_count", freshnessNumber(landing.populations?.current?.top8_count)],
    ["high-score-completeness", "high_score_completeness", freshnessRatio(
      highScore.observed_decklist_count,
      highScore.expected_decklist_count_display ?? highScore.expected_decklist_count,
      highScore.completeness_rate
    )],
  ]);
}

function matchupFreshness(completeness) {
  const coverage = completeness.matchup_coverage || {};
  return freshnessStrip([
    ["period", "period", freshnessPeriod(coverage.period || completeness.period)],
    ["matchup-coverage", "matchup_coverage", freshnessRatio(
      coverage.available_event_count,
      coverage.expected_event_count,
      coverage.completeness_rate
    )],
    ["deferred-events", "deferred_events", freshnessNumber(coverage.deferred_event_count)],
    ["missing-events", "missing_events", freshnessNumber(coverage.missing_event_count)],
    ["excluded-events", "excluded_events", freshnessNumber(coverage.excluded_event_count)],
  ]);
}

function top8Freshness(top8, weekEntry) {
  const placements = top8.events.flatMap(event => event.placements || []);
  return freshnessStrip([
    ["week", "week", freshnessPeriod(top8.week || weekEntry)],
    ["events", "event_count", freshnessNumber(weekEntry.event_count ?? top8.events.length)],
    ["placements", "placement_count", freshnessNumber(placements.length)],
    ["available-decks", "available_decks", freshnessNumber(
      placements.filter(placement => placement.deck_status === "available").length
    )],
  ]);
}

function pickupFreshness(week, document) {
  const existingCount = week.existing_count
    ?? (Array.isArray(document.existing_changes) ? document.existing_changes.length : null);
  const newCount = week.new_count
    ?? (Array.isArray(document.new_archetypes) ? document.new_archetypes.length : null);
  const featuredDeckCount = existingCount === null || newCount === null
    ? null
    : Number(existingCount) + Number(newCount);
  return freshnessStrip([
    ["week", "week", freshnessPeriod(week)],
    ["featured-decks", "featured_decks", freshnessNumber(featuredDeckCount)],
  ]);
}

function tabletopFreshness(scopeState, selectedEventIds, overview, scope, quality) {
  if (scopeState.multi_event) {
    return freshnessStrip([
      ["selected-events", "selected_events", freshnessNumber(selectedEventIds.length)],
    ]);
  }
  return freshnessStrip([
    ["event-date", "event_date", freshnessPeriod(overview.event.date)],
    ["selected-events", "selected_events", freshnessNumber(selectedEventIds.length)],
    ["scope-decks", "scope_decks", freshnessNumber(scope.participant_count)],
    ["submitted-decks", "submitted_decks", freshnessNumber(quality.counts.submitted_decklists)],
    ["unavailable-decks", "unavailable_decks", freshnessNumber(quality.counts.missing_or_unavailable_decklists)],
  ]);
}
