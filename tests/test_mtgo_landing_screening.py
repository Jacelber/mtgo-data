from datetime import date
from types import SimpleNamespace

from mtgmeta.mtgo import landing_editorial as editorial
from mtgmeta.mtgo import landing_screening as screening


WEEK_START = date(2026, 8, 10)


def _policy(*, cards=(), continuity=None):
    return {
        "schema_version": "1.0",
        "thresholds": {
            "share_increase_pp": 5,
            "return_share": 0.03,
            "build_shift": 20,
            "build_reference_minimum": 8,
            "new_card_review_weeks": 2,
        },
        "identity_continuity": {
            "standard": continuity or {},
            "modern": {},
        },
        "release_sets": [
            {
                "code": "HOB",
                "arena_release_date": "2026-08-11",
                "release_source_url": "https://example.test/hob",
                "manifest_status": "frozen",
                "cards": list(cards),
            }
        ]
        if cards
        else [],
    }


def _record(
    player,
    archetype,
    archetype_id,
    *,
    rank,
    event_id,
    players=50,
    starttime="2026-08-14 18:00:00.0",
    card="Established Card",
    card_qty=4,
    high_score=True,
):
    return {
        "event_id": event_id,
        "deck_id": f"deck-{event_id}-{rank}",
        "archetype": archetype,
        "archetype_id": archetype_id,
        "subtype": None,
        "subtype_id": None,
        "player": player,
        "final_rank": rank,
        "swiss_score": 15,
        "player_count": players,
        "starttime": starttime,
        "is_top8": rank <= 8,
        "is_high_score": high_score,
        "main_deck": [{"name": card, "qty": card_qty}],
        "side_deck": [],
    }


def _unknown(index):
    return {
        "archetype": "Unknown",
        "archetype_id": "unknown",
        "is_high_score": True,
        "is_top8": False,
        "main_deck": [],
        "side_deck": [],
        "player": f"unknown-{index}",
    }


def _base(name):
    return {
        "name": name,
        "mean": {"Established Card": 4.0},
        "weights": {"Established Card": 1.0},
        "denom": 4.0,
        "core": [],
        "flex": [],
        "medoid_display": None,
        "sample_size": 8,
    }


def _prepare(monkeypatch, current, reference, historical, parent_bases=None):
    monkeypatch.setattr(screening, "week_records", lambda *args, **kwargs: current)
    periods = iter((reference, historical))
    monkeypatch.setattr(
        screening,
        "_records_in_period",
        lambda *args, **kwargs: next(periods),
    )
    monkeypatch.setattr(
        screening.stats,
        "build_base_pack",
        lambda *args, **kwargs: (parent_bases or {}, 0.0),
    )
    monkeypatch.setattr(
        screening.stats,
        "build_subtype_base_pack",
        lambda *args, **kwargs: ({}, 0.0),
    )
    monkeypatch.setattr(
        screening,
        "_record_identity",
        lambda record, _rules: {
            "identity_id": record["archetype_id"],
            "archetype_id": record["archetype_id"],
            "subtype_id": record["subtype_id"],
            "subtype": record["subtype"],
        },
    )


def test_screening_merges_reasons_and_keeps_later_rank_five_dragons(monkeypatch):
    dimir = _record(
        "claudioh", "Dimir Midrange", "dimir-midrange", rank=2, event_id="100"
    )
    boros = _record(
        "IronBeagle",
        "Boros Dragons",
        "boros-dragons",
        rank=3,
        event_id="101",
        card="Smaug the Magnificent",
    )
    spock_fifth = _record(
        "SpockVidaLoka",
        "Mono-Red Dragons",
        "mono-red-dragons",
        rank=5,
        event_id="102",
        card="Smaug the Magnificent",
    )
    spock_sixth = _record(
        "SpockVidaLoka",
        "Mono-Red Dragons",
        "mono-red-dragons",
        rank=6,
        event_id="103",
        players=53,
        card="Smaug the Magnificent",
    )
    azorius = _record(
        "Thief_Of_Crowns",
        "Azorius Oculus",
        "azorius-oculus",
        rank=7,
        event_id="104",
        card="The Eagles Are Coming!",
    )
    grixis = _record(
        "auzzie51", "Grixis Tablet", "grixis-tablet", rank=3, event_id="105"
    )
    jeskai = _record(
        "olbeda", "Jeskai Momo", "jeskai-momo", rank=6, event_id="106"
    )
    current = [
        dimir,
        boros,
        spock_fifth,
        spock_sixth,
        azorius,
        grixis,
        jeskai,
        *[_unknown(index) for index in range(3)],
    ]
    reference = [
        _record(
            "old",
            "Dimir Midrange",
            "dimir-midrange",
            rank=99,
            event_id="200",
        ),
        *[_unknown(index) for index in range(19)],
    ]
    _prepare(monkeypatch, current, reference, [])
    rules = SimpleNamespace(
        archetypes=(
            SimpleNamespace(id="dimir-midrange", subtypes=()),
            SimpleNamespace(id="boros-dragons", subtypes=()),
            SimpleNamespace(id="jeskai-momo", subtypes=()),
        )
    )

    candidates, _base, top8_count, candidate_count = (
        editorial.build_candidate_documents(
            [],
            rules,
            WEEK_START,
            {"Dimir Midrange", "Boros Dragons", "Azorius Momo"},
            _policy(
                cards=("Smaug the Magnificent", "The Eagles Are Coming!"),
                continuity={"jeskai-momo": {"known_as": ["Azorius Momo"]}},
            ),
            "standard",
        )
    )

    rows = candidates["existing_changes"] + candidates["new_archetypes"]
    by_player = {row["player"]: row for row in rows}
    assert top8_count == 7
    assert candidate_count == 5
    assert by_player["SpockVidaLoka"]["final_rank"] == 5
    assert {item["type"] for item in by_player["SpockVidaLoka"]["candidate_reasons"]} == {
        "new_card",
        "new_archetype",
    }
    assert {item["type"] for item in by_player["IronBeagle"]["candidate_reasons"]} == {
        "new_card"
    }
    assert by_player["claudioh"]["candidate_reasons"][0]["type"] == "share_increase"
    assert by_player["auzzie51"]["candidate_reasons"][0]["type"] == "new_archetype"
    assert "olbeda" not in by_player


def test_build_shift_uses_parent_base_when_no_subtype_is_maintained(monkeypatch):
    traft = _record(
        "Traft", "Orzhov Lifegain", "orzhov-lifegain", rank=1, event_id="300"
    )
    other = _record(
        "YourDoom25", "Orzhov Lifegain", "orzhov-lifegain", rank=4, event_id="301"
    )
    reference = [
        _record(
            f"old-{index}",
            "Orzhov Lifegain",
            "orzhov-lifegain",
            rank=99,
            event_id=f"4{index:02d}",
        )
        for index in range(8)
    ]
    _prepare(
        monkeypatch,
        [traft, other],
        reference,
        [],
        {"orzhov-lifegain": _base("Orzhov Lifegain")},
    )
    monkeypatch.setattr(
        screening,
        "deck_deviation",
        lambda record, _base, _d99=None: {"Traft": 45, "YourDoom25": 11}.get(
            record["player"], 0
        ),
    )
    rules = SimpleNamespace(
        archetypes=(SimpleNamespace(id="orzhov-lifegain", subtypes=()),)
    )

    candidates, _base_reference, _top8_count, candidate_count = (
        editorial.build_candidate_documents(
            [],
            rules,
            WEEK_START,
            {"Orzhov Lifegain"},
            _policy(),
            "standard",
        )
    )

    assert candidate_count == 1
    row = candidates["existing_changes"][0]
    assert row["player"] == "Traft"
    reason = row["candidate_reasons"][0]
    assert reason["type"] == "build_shift"
    assert reason["identity_level"] == "parent"
    assert reason["score"] == 45


def test_same_new_card_package_prefers_result_and_merges_return(monkeypatch):
    third = _record(
        "IronBeagle",
        "Boros Dragons",
        "boros-dragons",
        rank=3,
        event_id="410",
        players=50,
        card="Smaug the Magnificent",
        card_qty=3,
    )
    fifth = _record(
        "IronBeagle",
        "Boros Dragons",
        "boros-dragons",
        rank=5,
        event_id="411",
        players=60,
        starttime="2026-08-16 18:00:00.0",
        card="Smaug the Magnificent",
        card_qty=4,
    )
    historical = [
        _record(
            "older",
            "Boros Dragons",
            "boros-dragons",
            rank=99,
            event_id="409",
        )
    ]
    _prepare(monkeypatch, [third, fifth], [], historical)
    rules = SimpleNamespace(
        archetypes=(SimpleNamespace(id="boros-dragons", subtypes=()),)
    )

    candidates, _base_reference, _top8_count, candidate_count = (
        editorial.build_candidate_documents(
            [],
            rules,
            WEEK_START,
            {"Boros Dragons"},
            _policy(cards=("Smaug the Magnificent",)),
            "standard",
        )
    )

    assert candidate_count == 1
    row = candidates["existing_changes"][0]
    assert row["event_id"] == "410"
    assert row["final_rank"] == 3
    assert {reason["type"] for reason in row["candidate_reasons"]} == {
        "new_card",
        "return",
    }
    new_card = next(
        reason for reason in row["candidate_reasons"] if reason["type"] == "new_card"
    )
    assert new_card["cards"] == [
        {"name": "Smaug the Magnificent", "main_qty": 3, "side_qty": 0}
    ]


def test_better_record_uses_later_result_after_rank_and_event_size_tie():
    earlier = _record(
        "same",
        "Example",
        "example",
        rank=5,
        event_id="500",
        starttime="2026-08-14 18:00:00.0",
    )
    later = _record(
        "same",
        "Example",
        "example",
        rank=5,
        event_id="501",
        starttime="2026-08-16 18:00:00.0",
    )

    assert screening.better_record(earlier, later) is later
