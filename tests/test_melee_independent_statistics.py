"""STATISTICS_SPEC §§3, 5–10: hand-counted expectations, not stored outputs."""
import pytest

from melee_synthetic import source_fixture, derived


@pytest.mark.parametrize("day1_rounds", [2, 3])
@pytest.mark.parametrize("playoff_format", ["limited", "modern"])
def test_raw_mixed_rounds_and_opportunity_denominators(tmp_path, day1_rounds, playoff_format):
    _, event, path, _ = source_fixture(tmp_path, day1_rounds=day1_rounds, playoff_format=playoff_format)
    # Check phase parsing before the ledger can reject missing draft players.
    assert [r["round_phase"] for r in event["rounds"]].count("draft") == 2
    classification, ledger, statistics, matchup = derived(tmp_path, event, path)
    extra = day1_rounds - 2
    # Day 1: A beats B, A/B draw; C bye then drops; D has byes only.
    # An extra round adds A's win, B's loss, C's unplayed round and D's bye.
    # Day 2: A/B intentional draw, then A locks and B receives a bye.
    expected = {"day1": (4, 4 * day1_rounds, 4 * day1_rounds, 14 + 6 * extra),
                "day2": (2, 4, 3, 5),
                "all_constructed": (4, 4 * day1_rounds + 4, 4 * day1_rounds + 3, 19 + 6 * extra)}
    for scope, counts in expected.items():
        actual = ledger["scope_summaries"][scope]
        assert tuple(actual[k] for k in ("participant_count", "theoretical_rounds",
            "effective_theoretical_rounds", "constructed_points")) == counts
    for scope in ("day1", "all_constructed"):
        record = statistics["overview"]["scopes"][scope]["literal_record"]
        assert (record["wins"], record["losses"], record["draws"], record["matches"]) == (1 + extra, 1 + extra, 2, 4 + 2 * extra)
        assert record["win_rate"] == pytest.approx((1 + extra) / (4 + 2 * extra), abs=1e-6)
        assert matchup["scopes"][scope]["included_match_count"] == 2 + extra
    assert statistics["overview"]["scopes"]["day2"]["literal_record"]["win_rate"] is None
    rounds = {r["id"]: r for r in event["rounds"]}
    for match in event["matches"]:
        r = rounds[match["round_id"]]
        if r["round_phase"] in {"draft", "playoff"}:
            assert match["played"] is True
            assert match["constructed_statistics_eligible"] is False
            assert match["matchup_eligible"] is False
    assert ledger["scope_summaries"]["all_constructed"]["result_counts"] == {
        "awarded_win_top8_lock": 1, "bye": 4 + extra, "drop_unplayed": 1 + extra,
        "intentional_draw": 2, "played_draw": 2, "played_loss": 1 + extra, "played_win": 1 + extra}
    scope = statistics["overview"]["scopes"]["day1"]
    assert (scope["submitted_deck_count"], scope["known_deck_count"],
            scope["unknown_deck_count"], scope["unavailable_deck_count"]) == (3, 2, 1, 1)
    assert len(classification["records"]) == 3  # D's missing deck is not an Unknown deck.
    parent = next(a for a in scope["archetypes"] if a["archetype_id"] == "alpha")
    assert parent["deck_count"] == sum(s["deck_count"] for s in parent["subtypes"]) == 2
    record = parent["match_record"]["all_matches"]["literal_record"]
    assert (record["wins"], record["losses"], record["draws"]) == (1 + extra, 1 + extra, 2)
    assert parent["match_record"]["non_mirror"]["literal_record"]["matches"] == 0
    # Legacy compatibility percentages retain their historical meaning.
    assert parent["match_record"]["all_matches"]["win_rate"] == 0.5


def test_raw_disqualification_excludes_whole_match_without_deleting_source(tmp_path):
    _, event, path, _ = source_fixture(tmp_path, dq=True)
    _, ledger, statistics, matchup = derived(tmp_path, event, path)
    assert len(event["participants"]) == 4
    assert len(event["matches"]) == 10
    # B is DQ: both A's and B's observations disappear, including their draw.
    assert ledger["scope_summaries"]["day1"]["disqualified_matches_excluded"] == 2
    # The unaffected C/D match survives overall, even though D has no decklist.
    assert statistics["overview"]["scopes"]["all_constructed"]["literal_record"]["matches"] == 2
    assert matchup["scopes"]["all_constructed"]["included_match_count"] == 0


@pytest.mark.parametrize("fault", ["draft", "lock", "dq"])
def test_hand_counted_cases_detect_production_semantic_faults(tmp_path, monkeypatch, fault):
    from dataclasses import replace
    from mtgmeta.melee import normalize
    if fault == "draft":
        original = normalize._phase_for_round
        def phase(source, event):
            result = original(source, event)
            return replace(result, round_phase="constructed", game_format="modern") if result.round_phase == "draft" else result
        monkeypatch.setattr(normalize, "_phase_for_round", phase)
    elif fault == "lock":
        original = normalize._source_result
        def result(source, event):
            played, rows = original(source, event)
            for row in rows:
                if row["result_type"] == "awarded_win_top8_lock":
                    row["result_type"] = "bye"
            return played, rows
        monkeypatch.setattr(normalize, "_source_result", result)
    else:
        original = normalize._participant_status
        monkeypatch.setattr(normalize, "_participant_status", lambda row: "active" if row.status_text == "Disqualified" else original(row))
    with pytest.raises(AssertionError):
        if fault == "dq":
            test_raw_disqualification_excludes_whole_match_without_deleting_source(tmp_path)
        else:
            test_raw_mixed_rounds_and_opportunity_denominators(tmp_path, 2, "limited")
