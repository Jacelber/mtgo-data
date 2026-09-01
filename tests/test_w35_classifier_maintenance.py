from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import pytest

from mtgmeta.classifier import classify_deck
from mtgmeta.config import load_rule_set
from mtgmeta.melee.classification import (
    _adapt_decklist,
    build_classification_overlay_from_paths,
)


ROOT = Path(__file__).resolve().parents[1]


def _deck(*cards: tuple[str, int]) -> dict[str, list[dict[str, object]]]:
    return {
        "main_deck": [{"name": name, "qty": quantity} for name, quantity in cards],
        "sideboard": [],
    }


@pytest.mark.parametrize(
    ("cards", "expected_parent"),
    (
        (
            (
                ("Sazh's Chocobo", 4),
                ("Fabled Passage", 4),
                ("Earthbender Ascension", 3),
                ("Temple Garden", 1),
            ),
            "selesnya-landfall",
        ),
        (
            (
                ("Drake Hatcher", 3),
                ("Slickshot Show-Off", 3),
                ("Gandalf, Friend of the Shire", 3),
                ("Steam Vents", 2),
            ),
            "izzet-prowess",
        ),
        (
            (
                ("Enduring Curiosity", 3),
                ("Floodpits Drowner", 3),
                ("Watery Grave", 2),
            ),
            "dimir-midrange",
        ),
        (
            (
                ("Pinnacle Emissary", 3),
                ("Ravenous Robots", 3),
                ("Springleaf Drum", 3),
                ("Steam Vents", 2),
            ),
            "affinity",
        ),
        (
            (
                ("Eddymurk Crab", 3),
                ("Flow State", 3),
                ("Opt", 3),
                ("Watery Grave", 2),
            ),
            "dimir-spellementals",
        ),
        (
            (
                ("Ambitious Augmenter", 3),
                ("Ouroboroid", 3),
                ("Practiced Offense", 3),
                ("Godless Shrine", 1),
                ("Temple Garden", 1),
                ("Overgrown Tomb", 1),
            ),
            "abzan-offense",
        ),
    ),
)
def test_w35_standard_rules_cover_accepted_representatives(
    cards: tuple[tuple[str, int], ...], expected_parent: str
) -> None:
    result = classify_deck(
        load_rule_set(ROOT / "my_archetypes/standard.yaml"),
        _deck(*cards),
    )

    assert result.status == "classified"
    assert result.archetype_id == expected_parent


def test_melee_split_cards_preserve_reviewed_classifier_spellings() -> None:
    adapted, errors = _adapt_decklist(
        {
            "cards": [
                {"name": "Dead // Gone", "quantity": 2, "section": "main"},
                {"name": "Fire // Ice", "quantity": 3, "section": "main"},
                {"name": "Wear // Tear", "quantity": 1, "section": "main"},
                {"name": "SP//dr", "quantity": 1, "section": "sideboard"},
            ]
        }
    )

    assert errors == ()
    assert adapted == {
        "main_deck": [
            {"name": "Dead/Gone", "qty": 2},
            {"name": "Fire/Ice", "qty": 3},
            {"name": "Wear", "qty": 1},
        ],
        "sideboard": [{"name": "SP//dr", "qty": 1}],
    }


def test_w35_eldrazi_tron_color_boundary() -> None:
    rules = load_rule_set(ROOT / "my_archetypes/modern.yaml")
    colorless = classify_deck(
        rules,
        _deck(
            ("Urza's Mine", 4),
            ("Urza's Power Plant", 4),
            ("Urza's Tower", 4),
            ("Eldrazi Temple", 4),
            ("Expedition Map", 4),
            ("Karn, the Great Creator", 4),
            ("Thought-Knot Seer", 4),
            ("Ugin, Eye of the Storms", 4),
            ("Tezzeret, Cruel Captain", 2),
            ("Swamp", 1),
            ("Dismember", 3),
        ),
    )
    genuinely_black = classify_deck(
        rules,
        _deck(
            ("Urza's Mine", 4),
            ("Urza's Power Plant", 4),
            ("Urza's Tower", 4),
            ("Eldrazi Temple", 4),
            ("Tezzeret, Cruel Captain", 2),
            ("Swamp", 4),
            ("Thoughtseize", 4),
        ),
    )

    assert (colorless.archetype_id, colorless.subtype_id) == (
        "eldrazi-tron",
        "colorless",
    )
    assert (genuinely_black.archetype_id, genuinely_black.subtype_id) == (
        "eldrazi-tron",
        "mono-black",
    )


def test_w35_affinity_and_azorius_artifact_boundary() -> None:
    rules = load_rule_set(ROOT / "my_archetypes/modern.yaml")
    artifact_core = (
        ("Mox Opal", 3),
        ("Urza's Saga", 3),
        ("Mishra's Bauble", 3),
    )
    affinity = classify_deck(
        rules,
        _deck(*artifact_core, ("Kappa Cannoneer", 3)),
    )
    sewer_combo = classify_deck(
        rules,
        _deck(
            *artifact_core,
            ("Oswald Fiddlebender", 1),
            ("Portable Hole", 2),
            ("Sewer-veillance Cam", 1),
            ("Grinding Station", 1),
            ("Hallowed Fountain", 1),
        ),
    )
    azorius_artifact = classify_deck(
        rules,
        _deck(
            *artifact_core,
            ("Oswald Fiddlebender", 1),
            ("Portable Hole", 2),
            ("Hallowed Fountain", 1),
        ),
    )
    generic_artifacts = classify_deck(rules, _deck(*artifact_core))

    assert (affinity.status, affinity.archetype_id) == ("classified", "affinity")
    assert (sewer_combo.status, sewer_combo.archetype_id) == (
        "classified",
        "sewer-combo",
    )
    assert sewer_combo.subtype_id == "azorius"
    assert (azorius_artifact.status, azorius_artifact.archetype_id) == (
        "classified",
        "azorius-artifact",
    )
    assert generic_artifacts.status == "unknown"


@pytest.mark.parametrize(
    ("cards", "expected_identity"),
    (
        (
            (
                ("Mox Opal", 4),
                ("Urza's Saga", 4),
                ("Mishra's Bauble", 4),
                ("Sewer-veillance Cam", 3),
                ("Grinding Station", 3),
                ("Malevolent Rumble", 4),
            ),
            ("sewer-combo", "simic"),
        ),
        (
            (
                ("Mox Opal", 4),
                ("Urza's Saga", 4),
                ("Mishra's Bauble", 4),
                ("Sewer-veillance Cam", 3),
                ("Grinding Station", 3),
                ("Loki, God of Mischief", 4),
                ("Island", 3),
                ("Breeding Pool", 1),
            ),
            ("sewer-combo", "mono-blue"),
        ),
        (
            (
                ("Mox Opal", 4),
                ("Urza's Saga", 4),
                ("Mishra's Bauble", 4),
                ("Sewer-veillance Cam", 3),
                ("Grinding Station", 2),
                ("Island", 5),
                ("Gran-Gran", 3),
                ("Rona, Herald of Invasion", 3),
                ("Retraction Helix", 3),
            ),
            ("sewer-combo", "mono-blue"),
        ),
        (
            (
                ("Mox Opal", 4),
                ("Urza's Saga", 4),
                ("Mishra's Bauble", 4),
                ("Sewer-veillance Cam", 3),
                ("Grinding Station", 3),
                ("Ragavan, Nimble Pilferer", 2),
                ("Steam Vents", 2),
            ),
            ("sewer-combo", "izzet"),
        ),
        (
            (
                ("Mox Opal", 4),
                ("Urza's Saga", 4),
                ("Mishra's Bauble", 4),
                ("Portable Hole", 4),
                ("Hallowed Fountain", 2),
            ),
            ("azorius-artifact", None),
        ),
        (
            (
                ("Jeskai Ascendancy", 3),
                ("Emry, Lurker of the Loch", 4),
                ("Tamiyo, Inquisitive Student", 4),
                ("Mox Amber", 4),
                ("Mox Opal", 4),
                ("Urza's Saga", 4),
                ("Mishra's Bauble", 4),
                ("Portable Hole", 4),
                ("Hallowed Fountain", 2),
                ("Steam Vents", 2),
            ),
            ("jeskai-ascendancy-combo", None),
        ),
        (
            (
                ("Mox Opal", 4),
                ("Urza's Saga", 4),
                ("Cori-Steel Cutter", 4),
                ("Experimental Synthesizer", 4),
                ("Legion Extruder", 4),
                ("Shrapnel Blast", 4),
            ),
            ("mono-red-artifact", None),
        ),
        (
            (
                ("Basim Ibn Ishaq", 4),
                ("Bilbo, Thief in the Night", 3),
                ("Emry, Lurker of the Loch", 4),
                ("Tamiyo, Inquisitive Student", 4),
                ("Mox Amber", 4),
                ("Mox Opal", 4),
                ("Watery Grave", 2),
            ),
            ("dimir-legends", None),
        ),
        (
            (
                ("Coretapper", 4),
                ("Astral Cornucopia", 4),
                ("Everflowing Chalice", 4),
                ("Mystic Forge", 3),
                ("Karn, the Great Creator", 4),
                ("Eldrazi Temple", 4),
            ),
            ("dice-factory-eldrazi", None),
        ),
        (
            (
                ("Asmoranomardicadaistinaculdacar", 2),
                ("The Underworld Cookbook", 4),
                ("Ovalchase Daredevil", 4),
                ("Academy Manufactor", 4),
                ("Time Sieve", 4),
                ("Mox Opal", 4),
            ),
            ("dimir-asmo", None),
        ),
    ),
)
def test_w35_artifact_unknown_clusters_have_exact_accepted_identities(
    cards: tuple[tuple[str, int], ...],
    expected_identity: tuple[str, str | None],
) -> None:
    result = classify_deck(
        load_rule_set(ROOT / "my_archetypes/modern.yaml"),
        _deck(*cards),
    )

    assert result.status == "classified"
    assert (result.archetype_id, result.subtype_id) == expected_identity


@pytest.mark.parametrize(
    ("cards", "expected_identity"),
    (
        (
            (
                ("Mox Opal", 4),
                ("Urza's Saga", 4),
                ("Mishra's Bauble", 4),
                ("Sewer-veillance Cam", 3),
                ("Grinding Station", 3),
                ("Malevolent Rumble", 4),
                ("Kethis, the Hidden Hand", 4),
                ("Emry, Lurker of the Loch", 4),
                ("Mox Amber", 4),
            ),
            ("kethis-combo", None),
        ),
        (
            (
                ("Mox Opal", 4),
                ("Urza's Saga", 4),
                ("Mishra's Bauble", 4),
                ("Sewer-veillance Cam", 3),
                ("Grinding Station", 3),
                ("Malevolent Rumble", 4),
                ("Song of Creation", 3),
                ("Emry, Lurker of the Loch", 4),
                ("Mox Amber", 4),
            ),
            ("song-of-creation", None),
        ),
        (
            (
                ("Mox Opal", 4),
                ("Urza's Saga", 4),
                ("Mishra's Bauble", 4),
                ("Sewer-veillance Cam", 3),
                ("Grinding Station", 3),
                ("Island", 3),
                ("Emry, Lurker of the Loch", 4),
                ("Cori-Steel Cutter", 4),
            ),
            ("steel-cutter", "izzet"),
        ),
        (
            (
                ("Mox Opal", 4),
                ("Urza's Saga", 4),
                ("Mishra's Bauble", 4),
                ("Emry, Lurker of the Loch", 4),
                ("Tamiyo, Inquisitive Student", 4),
                ("Mox Amber", 4),
                ("Portable Hole", 2),
                ("Jeskai Ascendancy", 3),
                ("Cori-Steel Cutter", 4),
                ("Hallowed Fountain", 1),
                ("Steam Vents", 1),
            ),
            ("jeskai-ascendancy-combo", None),
        ),
        (
            (
                ("Mox Opal", 4),
                ("Urza's Saga", 4),
                ("Mishra's Bauble", 4),
                ("Emry, Lurker of the Loch", 4),
                ("Tamiyo, Inquisitive Student", 4),
                ("Mox Amber", 4),
                ("Portable Hole", 3),
                ("Jeskai Ascendancy", 3),
                ("Oswald Fiddlebender", 3),
                ("Sewer-veillance Cam", 1),
                ("Grinding Station", 1),
                ("Hallowed Fountain", 1),
                ("Steam Vents", 1),
            ),
            ("sewer-combo", "azorius"),
        ),
        (
            (
                ("Basim Ibn Ishaq", 3),
                ("Bilbo, Thief in the Night", 3),
                ("Emry, Lurker of the Loch", 4),
                ("Tamiyo, Inquisitive Student", 4),
                ("Mox Amber", 4),
                ("Mox Opal", 4),
                ("Erayo, Soratami Ascendant", 3),
                ("Watery Grave", 2),
            ),
            ("erayo", None),
        ),
    ),
)
def test_w35_new_artifact_rules_respect_accepted_engine_precedence(
    cards: tuple[tuple[str, int], ...],
    expected_identity: tuple[str, str | None],
) -> None:
    result = classify_deck(
        load_rule_set(ROOT / "my_archetypes/modern.yaml"),
        _deck(*cards),
    )

    assert result.status == "classified"
    assert (result.archetype_id, result.subtype_id) == expected_identity


def test_441441_oswald_artifact_decks_use_the_azorius_identity() -> None:
    event = json.loads(
        (ROOT / "data/modern/melee/events/441441.json").read_text(encoding="utf-8")
    )
    reviewed_participants = {
        decklist["participant_id"]
        for decklist in event["decklists"]
        if "Oswald Fiddlebender" in {card["name"] for card in decklist["cards"]}
        and "Portable Hole" in {card["name"] for card in decklist["cards"]}
        and "Kappa Cannoneer" not in {card["name"] for card in decklist["cards"]}
    }
    refreshed_overlay = build_classification_overlay_from_paths(
        ROOT / "data/modern/melee/events/441441.json",
        ROOT / "my_archetypes/modern.yaml",
        ROOT,
    )
    selected = {
        record["participant_id"]: (
            record["selected"]["archetype_id"],
            record["selected"]["subtype_id"],
        )
        for record in refreshed_overlay["records"]
        if record["participant_id"] in reviewed_participants
    }

    assert len(reviewed_participants) == 4
    assert selected == {
        participant_id: ("sewer-combo", "azorius")
        for participant_id in reviewed_participants
    }
    outcomes = Counter(
        "Unknown"
        if record["classification_status"] == "unknown"
        else record["selected"]["archetype_id"]
        + (
            f"/{record['selected']['subtype_id']}"
            if record["selected"]["subtype_id"] is not None
            else ""
        )
        for record in refreshed_overlay["records"]
    )
    assert outcomes["affinity"] == 29
    assert outcomes["sewer-combo/azorius"] == 4
    assert outcomes["sewer-combo/mono-blue"] == 1
    assert outcomes["jeskai-ascendancy-combo"] == 2
    assert outcomes["Unknown"] == 7


def test_441441_final_artifact_review_has_exact_owner_accepted_identities() -> None:
    event = json.loads(
        (ROOT / "data/modern/melee/events/441441.json").read_text(encoding="utf-8")
    )
    participant_ids = {
        participant["display_name"]: participant["id"]
        for participant in event["participants"]
        if participant["display_name"] in {"Jezza", "Nathan Basser", "Samuel Loy"}
    }
    refreshed_overlay = build_classification_overlay_from_paths(
        ROOT / "data/modern/melee/events/441441.json",
        ROOT / "my_archetypes/modern.yaml",
        ROOT,
    )
    selected_by_participant = {
        record["participant_id"]: (
            record["selected"]["archetype_id"],
            record["selected"]["subtype_id"],
        )
        for record in refreshed_overlay["records"]
        if record["participant_id"] in participant_ids.values()
    }

    assert participant_ids.keys() == {"Jezza", "Nathan Basser", "Samuel Loy"}
    assert selected_by_participant == {
        participant_ids["Jezza"]: ("sewer-combo", "mono-blue"),
        participant_ids["Nathan Basser"]: ("jeskai-ascendancy-combo", None),
        participant_ids["Samuel Loy"]: ("jeskai-ascendancy-combo", None),
    }


def test_441441_owner_rejected_off_format_decks_remain_unknown() -> None:
    event = json.loads(
        (ROOT / "data/modern/melee/events/441441.json").read_text(encoding="utf-8")
    )
    participant_ids = {
        participant["display_name"]: participant["id"]
        for participant in event["participants"]
        if participant["display_name"] in {"ZacM0306", "tshady"}
    }
    refreshed_overlay = build_classification_overlay_from_paths(
        ROOT / "data/modern/melee/events/441441.json",
        ROOT / "my_archetypes/modern.yaml",
        ROOT,
    )
    status_by_participant = {
        record["participant_id"]: record["classification_status"]
        for record in refreshed_overlay["records"]
        if record["participant_id"] in participant_ids.values()
    }

    assert participant_ids.keys() == {"ZacM0306", "tshady"}
    assert status_by_participant == {
        participant_ids["ZacM0306"]: "unknown",
        participant_ids["tshady"]: "unknown",
    }


def test_441441_reviewed_unknown_cohort_has_exact_accepted_outcomes() -> None:
    accepted_overlay = json.loads(
        (ROOT / "data/modern/melee/classifications/441441.json").read_text(
            encoding="utf-8"
        )
    )
    reviewed_participants = {
        record["participant_id"]
        for record in accepted_overlay["records"]
        if record["classification_status"] == "unknown"
    }
    refreshed_overlay = build_classification_overlay_from_paths(
        ROOT / "data/modern/melee/events/441441.json",
        ROOT / "my_archetypes/modern.yaml",
        ROOT,
    )

    outcomes: Counter[str] = Counter()
    for record in refreshed_overlay["records"]:
        if record["participant_id"] not in reviewed_participants:
            continue
        if record["classification_status"] == "unknown":
            outcomes["Unknown"] += 1
            continue
        selected = record["selected"]
        identity = selected["archetype_id"]
        if selected["subtype_id"] is not None:
            identity += f"/{selected['subtype_id']}"
        outcomes[identity] += 1

    assert len(reviewed_participants) == 37
    assert outcomes == Counter(
        {
            "Unknown": 7,
            "burn/boros": 2,
            "infect/simic": 2,
            "leyline-fling": 2,
            "rhinos/temur": 2,
            "abzan-auras": 1,
            "altar-combo": 1,
            "amalia-combo": 1,
            "angels": 1,
            "azorius-blink": 1,
            "azorius-land-denial": 1,
            "dice-factory-eldrazi": 1,
            "dredge": 1,
            "dwarves": 1,
            "eldrazi-tron/colorless": 1,
            "eldrazi-tron/mono-green": 1,
            "elves": 1,
            "five-color-humans": 1,
            "golgari-roots": 1,
            "grixis-creativity-goryos": 1,
            "grixis-persist": 1,
            "gruul-midrange": 1,
            "rakdos-delirium": 1,
            "rakdos-midrange": 1,
            "ruby-ponza": 1,
            "scapeshift/gruul": 1,
            "sorin-morophon": 1,
        }
    )
    assert refreshed_overlay["quality"]["status"] == "pass"
