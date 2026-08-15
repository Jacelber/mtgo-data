from copy import deepcopy

from validate_output_invariants import (
    validate_matchup_document,
    validate_range_document,
)


def _cell(wins, losses, draws):
    matches = wins + losses + draws
    rate = round(wins / matches, 6) if matches else None
    interval = {"lower": max(0.0, (rate or 0) - 0.2), "upper": min(1.0, (rate or 0) + 0.2)} if matches else None
    return {
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "matches": matches,
        "literal_record": {
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "matches": matches,
            "win_rate": rate,
            "confidence_interval_95": interval,
        },
    }


def test_range_totals_and_shares_are_value_independent():
    document = {
        "total_decks": 3,
        "total_high_score": 2,
        "total_top8": 1,
        "archetypes": [
            {"id": "a", "count": 2, "high_score_count": 1, "high_score_share": 0.5, "top8_count": 1, "top8_share": 1.0},
            {"id": "b", "count": 1, "high_score_count": 1, "high_score_share": 0.5, "top8_count": 0, "top8_share": 0.0},
        ],
    }
    assert validate_range_document(document, "fixture") == []
    broken = deepcopy(document)
    broken["total_high_score"] = 3
    assert any("sum(high_score_count)" in item for item in validate_range_document(broken, "fixture"))


def test_matchup_records_are_symmetric_and_intervals_contain_estimates():
    matrix = {"a": {"b": _cell(2, 1, 1)}, "b": {"a": _cell(1, 2, 1)}}
    document = {"parent_matrix": matrix, "leaf_matrix": deepcopy(matrix)}
    assert validate_matchup_document(document, "fixture") == []
    document["parent_matrix"]["b"]["a"]["losses"] = 3
    assert any("asymmetric" in item for item in validate_matchup_document(document, "fixture"))


def test_zero_matches_remain_missing_not_zero_rate():
    matrix = {"a": {"a": _cell(0, 0, 0)}}
    document = {"parent_matrix": matrix, "leaf_matrix": deepcopy(matrix)}
    assert validate_matchup_document(document, "fixture") == []
    document["leaf_matrix"]["a"]["a"]["literal_record"]["win_rate"] = 0.0
    assert any("must not be encoded as zero" in item for item in validate_matchup_document(document, "fixture"))
