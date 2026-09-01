from __future__ import annotations

from pathlib import Path

import pytest

from mtgmeta.classifier import classify_deck
from mtgmeta.config import load_rule_set
from mtgmeta.melee.classification import _adapt_decklist


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_CORE = (
    ("Mox Opal", 4),
    ("Urza's Saga", 4),
    ("Mishra's Bauble", 4),
)
EMRY_CORE = (
    *ARTIFACT_CORE,
    ("Emry, Lurker of the Loch", 4),
    ("Tamiyo, Inquisitive Student", 4),
    ("Mox Amber", 4),
)


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
                ("Gandalf, Goblins' Bane", 3),
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
def test_standard_owner_rule_contracts(
    cards: tuple[tuple[str, int], ...], expected_parent: str
) -> None:
    result = classify_deck(
        load_rule_set(ROOT / "my_archetypes/standard.yaml"),
        _deck(*cards),
    )

    assert (result.status, result.archetype_id) == ("classified", expected_parent)


def test_melee_split_card_adapter_contract() -> None:
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


@pytest.mark.parametrize(
    ("cards", "expected"),
    (
        (
            (
                ("Urza's Mine", 4),
                ("Urza's Power Plant", 4),
                ("Urza's Tower", 4),
                ("Eldrazi Temple", 4),
                ("Expedition Map", 3),
                ("Karn, the Great Creator", 1),
                ("Tezzeret, Cruel Captain", 2),
                ("Swamp", 1),
                ("Dismember", 3),
            ),
            ("classified", "eldrazi-tron", "colorless"),
        ),
        (
            (
                ("Urza's Mine", 4),
                ("Urza's Power Plant", 4),
                ("Urza's Tower", 4),
                ("Eldrazi Temple", 4),
                ("Tezzeret, Cruel Captain", 2),
                ("Swamp", 4),
                ("Thoughtseize", 4),
            ),
            ("classified", "eldrazi-tron", "mono-black"),
        ),
        (
            (*ARTIFACT_CORE, ("Kappa Cannoneer", 3)),
            ("classified", "affinity", None),
        ),
        (
            (
                *ARTIFACT_CORE,
                ("Oswald Fiddlebender", 1),
                ("Portable Hole", 2),
                ("Sewer-veillance Cam", 1),
                ("Grinding Station", 1),
                ("Hallowed Fountain", 1),
            ),
            ("classified", "sewer-combo", "azorius"),
        ),
        (
            (
                *ARTIFACT_CORE,
                ("Portable Hole", 4),
                ("Hallowed Fountain", 2),
            ),
            ("classified", "azorius-artifact", None),
        ),
        (ARTIFACT_CORE, ("unknown", None, None)),
        (
            (
                *ARTIFACT_CORE,
                ("Sewer-veillance Cam", 3),
                ("Grinding Station", 3),
                ("Malevolent Rumble", 4),
            ),
            ("classified", "sewer-combo", "simic"),
        ),
        (
            (
                *ARTIFACT_CORE,
                ("Sewer-veillance Cam", 3),
                ("Grinding Station", 3),
                ("Loki, God of Mischief", 4),
                ("Island", 3),
                ("Breeding Pool", 1),
            ),
            ("classified", "sewer-combo", "mono-blue"),
        ),
        (
            (
                *ARTIFACT_CORE,
                ("Sewer-veillance Cam", 3),
                ("Grinding Station", 2),
                ("Island", 5),
                ("Gran-Gran", 3),
                ("Rona, Herald of Invasion", 3),
                ("Retraction Helix", 3),
            ),
            ("classified", "sewer-combo", "mono-blue"),
        ),
        (
            (
                *ARTIFACT_CORE,
                ("Sewer-veillance Cam", 3),
                ("Grinding Station", 3),
                ("Ragavan, Nimble Pilferer", 2),
                ("Steam Vents", 2),
            ),
            ("classified", "sewer-combo", "izzet"),
        ),
        (
            (
                *EMRY_CORE,
                ("Portable Hole", 4),
                ("Jeskai Ascendancy", 3),
                ("Hallowed Fountain", 2),
                ("Steam Vents", 2),
            ),
            ("classified", "jeskai-ascendancy-combo", None),
        ),
        (
            (
                *ARTIFACT_CORE,
                ("Cori-Steel Cutter", 4),
                ("Experimental Synthesizer", 4),
                ("Legion Extruder", 4),
                ("Shrapnel Blast", 4),
            ),
            ("classified", "mono-red-artifact", None),
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
            ("classified", "dimir-legends", None),
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
            ("classified", "dice-factory-eldrazi", None),
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
            ("classified", "dimir-asmo", None),
        ),
        (
            (
                *ARTIFACT_CORE,
                ("Sewer-veillance Cam", 3),
                ("Grinding Station", 3),
                ("Malevolent Rumble", 4),
                ("Kethis, the Hidden Hand", 4),
                ("Emry, Lurker of the Loch", 4),
                ("Mox Amber", 4),
            ),
            ("classified", "kethis-combo", None),
        ),
        (
            (
                *ARTIFACT_CORE,
                ("Sewer-veillance Cam", 3),
                ("Grinding Station", 3),
                ("Malevolent Rumble", 4),
                ("Song of Creation", 3),
                ("Emry, Lurker of the Loch", 4),
                ("Mox Amber", 4),
            ),
            ("classified", "song-of-creation", None),
        ),
        (
            (
                *ARTIFACT_CORE,
                ("Sewer-veillance Cam", 3),
                ("Grinding Station", 3),
                ("Island", 3),
                ("Emry, Lurker of the Loch", 4),
                ("Cori-Steel Cutter", 4),
            ),
            ("classified", "steel-cutter", "izzet"),
        ),
        (
            (
                *EMRY_CORE,
                ("Portable Hole", 3),
                ("Jeskai Ascendancy", 3),
                ("Oswald Fiddlebender", 3),
                ("Sewer-veillance Cam", 1),
                ("Grinding Station", 1),
                ("Hallowed Fountain", 1),
                ("Steam Vents", 1),
            ),
            ("classified", "sewer-combo", "azorius"),
        ),
        (
            (
                *EMRY_CORE,
                ("Quantum Riddler", 4),
                ("Subtlety", 4),
                ("Island", 4),
            ),
            ("classified", "mono-blue-artifact", None),
        ),
        (
            (
                *EMRY_CORE,
                ("Quantum Riddler", 4),
                ("Subtlety", 4),
                ("Island", 4),
                ("Kappa Cannoneer", 3),
            ),
            ("classified", "affinity", None),
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
            ("classified", "erayo", None),
        ),
    ),
)
def test_modern_owner_rule_contracts(
    cards: tuple[tuple[str, int], ...],
    expected: tuple[str, str | None, str | None],
) -> None:
    result = classify_deck(
        load_rule_set(ROOT / "my_archetypes/modern.yaml"),
        _deck(*cards),
    )

    assert (result.status, result.archetype_id, result.subtype_id) == expected
