from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def section(source: str, start: str, end: str) -> str:
    start_index = source.index(start)
    return source[start_index:source.index(end, start_index)]


def test_shared_strip_is_populated_by_each_active_product() -> None:
    freshness = (ROOT / "assets/js/phase8/app-freshness.js").read_text(
        encoding="utf-8"
    )
    mtgo = (ROOT / "assets/js/phase8/app-mtgo.js").read_text(encoding="utf-8")
    tabletop = (ROOT / "assets/js/phase8/app-tabletop.js").read_text(
        encoding="utf-8"
    )

    assert 'class="freshness-strip"' in freshness
    assert 'data-freshness-key="${escapeHtml(key)}"' in freshness
    assert "statisticsFreshness(meta, range, completeness)" in mtgo
    assert "matchupFreshness(completeness)" in mtgo
    assert "top8Freshness(top8, weekEntry)" in mtgo
    assert "pickupFreshness(week, document)" in mtgo
    assert "tabletopFreshness(" in tabletop


def test_product_mappings_use_only_their_supplied_facts() -> None:
    freshness = (ROOT / "assets/js/phase8/app-freshness.js").read_text(
        encoding="utf-8"
    )

    statistics = section(freshness, "function statisticsFreshness", "function matchupFreshness")
    matchup = section(freshness, "function matchupFreshness", "function top8Freshness")
    top8 = section(freshness, "function top8Freshness", "function pickupFreshness")
    pickup = section(freshness, "function pickupFreshness", "function tabletopFreshness")
    tabletop = freshness[freshness.index("function tabletopFreshness"):]

    assert "range.total_decks" in statistics
    assert "highScore.observed_decklist_count" in statistics
    assert "highScore.expected_decklist_count" in statistics
    assert "coverage.available_event_count" in matchup
    assert "coverage.expected_event_count" in matchup
    assert "coverage.missing_event_count" in matchup
    assert 'placement.deck_status === "available"' in top8
    assert "weekEntry.event_count" in top8
    assert "week.existing_count" in pickup
    assert "week.new_count" in pickup
    assert "scope.participant_count" in tabletop
    assert "quality.counts.submitted_decklists" in tabletop
    assert "quality.counts.missing_or_unavailable_decklists" in tabletop


def test_unknown_is_explicit_and_week_lifecycle_stays_internal() -> None:
    freshness = (ROOT / "assets/js/phase8/app-freshness.js").read_text(
        encoding="utf-8"
    )
    i18n = (ROOT / "assets/js/phase8/i18n.js").read_text(encoding="utf-8")
    top8 = section(freshness, "function top8Freshness", "function pickupFreshness")

    assert 't("freshness.unknown")' in freshness
    assert '"freshness.unknown": "未知"' in i18n
    assert '"freshness.unknown": "Unknown"' in i18n
    assert "provisional_through" not in top8
    assert "seal_on" not in top8
    assert "weekEntry.status" not in top8
