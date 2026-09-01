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

W35_REVIEWED_441441_PARTICIPANT_IDS = frozenset(
    {
        "participant-06645aaf15dfa097fcacb2e63af1b633de0d066b9e98cb482419341abd2de39d",
        "participant-06f074af0fba643267a2aa2a93e056bfb1a960c81c3f627a5d55726f357eeaea",
        "participant-10f62d54a05adb22175f85815d2c3128242e03fe8b928caa8f6dd857eff67108",
        "participant-1c44e49a0c4f574d8d49fd99c642acb4b5495b4d84c773243736ecf41f2cbc85",
        "participant-27bbf48fa52ae7ea66fa3458ad92a3a2fef93ebcdd5186312fc827a082cb0b60",
        "participant-2bd23c19e45f3ab13874f419381d5582e037478d84034c228ffb8e64e4f6531a",
        "participant-2d053efe55e44b6290b1b7655b702da7ed6e7a90a89aafde097e669c8d3a6be1",
        "participant-36ac49c4c827556ac70601615bc64d34012d1f915837ba9233aabfec1dc85192",
        "participant-3ba362b9b8f0cc1048b7e65223871f13b3862f3e1c9fc6d772f3c79dbf9960a9",
        "participant-4235519c0ec9a08d46bfb9639f80fc33640a1d0ec9bcda16136626f0de64f4e6",
        "participant-50082a2bdbd512118b28a8d2b390a3ac9501fcf5e5350a180b2d2eb6ed0623cb",
        "participant-53e310852b9d8dd2ed7edb42fdaf7ded35cc3af9ac24c1c09aaf44ea4751bcee",
        "participant-54933d6426cfa9bc78a4b0474c614d7f1cb5c0606e431fa7a175da0a163b60c5",
        "participant-5ae15dcfa639f9df2a7fa0f6c5a055635ac993b7491a6d4bdbff2b37c537ed77",
        "participant-6bb24075c36334a74fc27784ae8f9b474a406b8346f479855a82827e04d9cae1",
        "participant-6df2f8cbce4d5c8c75a8a1d2f2ae1b0fe2ebfd01ec2b0b9a99b6664091608e7b",
        "participant-75b20a9848f1fafa476bc2d99ea7b6043821e9e7ddde28b1f327ed90cc2f1427",
        "participant-968dd11158954fb5d23bf26cf6728a4fe8c7edda457284214690bd6faacedd54",
        "participant-969ce5a350a6a18c91a00f6935c40cb63bdd65efc31a7c868358f798a0c2b06d",
        "participant-977686529bb89dae7d262f62c5e0173481f9e393527cf05e342260b275a1b168",
        "participant-a27ec730c00aa8e42df25e38c65282a9b4afb06ee97dec1000ccea4b173b7876",
        "participant-a3e640d67fb708905acb22cc49473186d8fa187ccab1218f6a914e366aca1c65",
        "participant-a404a75274fd94b1df3c76af2e98e797416d653be64a5fbb31dd7ede01663156",
        "participant-a7d910e266f76e37994778b28d515d32e29a0185a3fbcc28a3e2600dc11cce66",
        "participant-b295f9e545d761ca793e24d80f4edd9877512bdb1f81ba09d1cf2e3a162ef460",
        "participant-b2e6db4ef07cfcdd26be0b8420c1150298f31b42b83ccd1a4a2b3a45d10d24af",
        "participant-b7d59f72ac992f6532a398a583263815b7bb366b21d67a41b92b9b882e2bbfd8",
        "participant-bb0139c2993fa9f59d788bc3f2994b0e5340aeea8699395d12f5ad11be73b95d",
        "participant-c01d4424eb75787755dd7c345fd2e23aafab788f4a228944a55e9a3a70f07ba1",
        "participant-c0683b438bb5ea1d117cb249469161f7c5855d3eeea47e17a9b68f00199b26df",
        "participant-ce75adf2610707063f373716bf9ef669a68c16a4d8c3633edc6bcc194e537ec5",
        "participant-dcfa73936e5e4745fd54ec4b52468ec44853022b4e22bc3a33b8d1d58ee28617",
        "participant-e2ef257bde6507e1976a4a37c5740e294ae62a909f1994cb3ff4295ce94e78ea",
        "participant-e8ab75cac9c003149e0f1aebf8c7e3b5f2a3d52eac616d40c0f46146f3f15a0e",
        "participant-ed361fe45751c6d083443b1ecd9d6272267995cd074262da83ce0873d9759807",
        "participant-f4c3e3e0be7dcb55b7d2e88fb85058bd3762f1d271454a318c06678bd80d829e",
        "participant-f688ed085f4b7d579ad5573e0a559576f3e4ab97af2c805cbc0cb18785f4faa3",
    }
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
def test_w35_standard_rules_cover_accepted_representatives(
    cards: tuple[tuple[str, int], ...], expected_parent: str
) -> None:
    result = classify_deck(
        load_rule_set(ROOT / "my_archetypes/standard.yaml"),
        _deck(*cards),
    )

    assert result.status == "classified"
    assert result.archetype_id == expected_parent


@pytest.mark.parametrize(
    "source_file",
    (
        "Standard_Challenge_32_12852775.json",
        "Standard_Challenge_16_12853170.json",
    ),
)
def test_w35_real_gandalf_decks_are_izzet_prowess(source_file: str) -> None:
    event = json.loads(
        (ROOT / "data/standard" / source_file).read_text(encoding="utf-8")
    )
    reviewed_decks = []
    for player in event["players"]:
        main_counts = Counter(
            {
                card["name"]: card["qty"]
                for card in player["main_deck"]
            }
        )
        if main_counts["Gandalf, Goblins' Bane"] >= 3:
            reviewed_decks.append(player)

    assert len(reviewed_decks) == 1
    result = classify_deck(
        load_rule_set(ROOT / "my_archetypes/standard.yaml"),
        reviewed_decks[0],
    )
    assert result.status == "classified"
    assert result.archetype_id == "izzet-prowess"


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
                ("Emry, Lurker of the Loch", 4),
                ("Tamiyo, Inquisitive Student", 4),
                ("Mox Amber", 4),
                ("Mox Opal", 4),
                ("Urza's Saga", 4),
                ("Mishra's Bauble", 4),
                ("Quantum Riddler", 4),
                ("Subtlety", 4),
                ("Island", 4),
                ("Kappa Cannoneer", 3),
            ),
            ("affinity", None),
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


def test_434455_owner_accepted_mono_blue_artifact_is_narrowly_classified() -> None:
    event = json.loads(
        (ROOT / "data/modern/melee/events/434455.json").read_text(encoding="utf-8")
    )
    required_cards = {
        "Emry, Lurker of the Loch",
        "Tamiyo, Inquisitive Student",
        "Mox Amber",
        "Mox Opal",
        "Urza's Saga",
        "Mishra's Bauble",
        "Quantum Riddler",
        "Subtlety",
    }
    reviewed_participants = set()
    for decklist in event["decklists"]:
        main_names = {
            card["name"].split(" // ", maxsplit=1)[0]
            for card in decklist["cards"]
            if card["section"] == "main"
        }
        if required_cards <= main_names and "Kappa Cannoneer" not in main_names:
            reviewed_participants.add(decklist["participant_id"])

    refreshed_overlay = build_classification_overlay_from_paths(
        ROOT / "data/modern/melee/events/434455.json",
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

    assert len(reviewed_participants) == 1
    assert selected == {
        participant_id: ("mono-blue-artifact", None)
        for participant_id in reviewed_participants
    }
    assert refreshed_overlay["summary"]["unknown"] == 0


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
    reviewed_participants = W35_REVIEWED_441441_PARTICIPANT_IDS
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
