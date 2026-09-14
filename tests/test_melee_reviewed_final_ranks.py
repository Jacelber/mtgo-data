from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location(
    "refresh_final_ranks", Path(__file__).parents[1] / "tools/refresh_melee_final_standings.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def bracket():
    def match(label, winner, loser):
        return {"id": f"{label}-{winner}", "round_id": label, "competitors": [
            {"participant_id": winner, "result_type": "played_win"},
            {"participant_id": loser, "result_type": "played_loss"},
        ]}
    event = {"participants": list("abcdefgh"), "rounds": [
        {"source_label": label, "id": label, "stage": "playoff"}
        for label in ("Quarterfinals", "Semifinals", "Finals")
    ], "matches": [match("Quarterfinals", a, b) for a, b in zip("abcd", "efgh")]
        + [match("Semifinals", "a", "c"), match("Semifinals", "b", "d"),
           match("Finals", "b", "a")]}
    return {"ranks": {p: i for i, p in enumerate("abcdefgh", 1)}}, event


def test_reviewed_final_ranks_use_winner_identity_and_preserve_other_places():
    result, event = bracket()
    before = deepcopy(event)
    module.supplement_from_semifinals(result, event)
    assert result["ranks"] == dict(a=2, b=1, c=3, d=4, e=5, f=6, g=7, h=8)
    assert result["base_ranks"]["a"] == 1
    assert event == before
    # A base already ordered like the final must not be blindly swapped.
    module.supplement_from_semifinals(result, event)
    assert result["ranks"]["b"] == 1


def test_reviewed_final_ranks_reject_inconsistent_top_two():
    result, event = bracket()
    result["ranks"]["b"], result["ranks"]["c"] = 3, 2
    with pytest.raises(ValueError, match="bracket"):
        module.supplement_from_semifinals(result, event)


def test_no_show_opponent_administrative_result_uses_statistics_vocabulary():
    from mtgmeta.melee.opportunities import _source_opportunity
    competitor = {"participant_id": "a", "result_type": "administrative", "match_points": 3}
    row = _source_opportunity(
        participant_id="a", participant_status="dropped",
        round_={"id": "round1", "number": 1, "stage": "day1"},
        match={"id": "match1", "played": False, "constructed_statistics_eligible": False,
               "matchup_eligible": False},
        competitors=[competitor, {"participant_id": "b"}], competitor=competitor,
        disqualified_ids=set(), event_structure="constructed_day2",
    )
    assert row["result_type"] == "administrative_result"
    assert row["source_match_points"] == 3
    assert row["constructed_points"] == 0
    assert not row["win_rate_included"] and not row["matchup_included"]
