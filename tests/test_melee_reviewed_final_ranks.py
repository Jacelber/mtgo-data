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


def test_reviewed_exception_rejects_unapproved_event_before_reading_or_fetching(tmp_path):
    with pytest.raises(ValueError, match="not approved"):
        module.refresh(tmp_path, "459699", reviewed_semifinals=True)


def owner_final_bracket():
    result, event = bracket()
    event["metadata"] = {"event_id": "440878"}
    event["participants"] = [{"id": p, "display_name": "Alexander von Stange" if p == "b" else p}
                             for p in "abcdefgh"]
    event["matches"] = [m for m in event["matches"] if m["round_id"] != "Finals"]
    return result, event


def test_owner_final_fills_ranks_without_inventing_a_source_match():
    result, event = owner_final_bracket()
    original = deepcopy(event)
    module.supplement_from_semifinals(result, event, owner_final_440878=True)
    assert event == original
    assert result["ranks"] == dict(a=2, b=1, c=3, d=4, e=5, f=6, g=7, h=8)
    assert result["base_ranks"] == {p: i for i, p in enumerate("abcdefgh", 1)}
    assert result["decisive_match_id"] is None
    assert result["reviewed_final_result"]["score"] == "2-0"
    assert result["reviewed_final_result"]["winner_participant_id"] == "b"
    assert "用户确认" in result["note"]["zh"]


def test_owner_final_cannot_apply_to_another_event_or_nonfinalist():
    result, event = owner_final_bracket()
    event["metadata"]["event_id"] = "414849"
    with pytest.raises(ValueError, match="only for event 440878"):
        module.supplement_from_semifinals(result, event, owner_final_440878=True)
    event["metadata"]["event_id"] = "440878"
    event["participants"][1]["display_name"] = "b"
    event["participants"][2]["display_name"] = "Alex von Stange"
    with pytest.raises(ValueError, match="semifinal winner"):
        module.supplement_from_semifinals(result, event, owner_final_440878=True)


def test_owner_final_does_not_suppress_an_inconsistent_official_final():
    result, event = owner_final_bracket()
    event["matches"].append({"id": "official-final", "round_id": "Finals", "competitors": [
        {"participant_id": "a", "result_type": "played_win"},
        {"participant_id": "b", "result_type": "played_loss"}]})
    with pytest.raises(ValueError, match="contradicts"):
        module.supplement_from_semifinals(result, event, owner_final_440878=True)


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
