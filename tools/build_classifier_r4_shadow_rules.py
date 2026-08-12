"""Build non-production R4 rules for owner-accepted Unknown dispositions."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from copy import deepcopy
from functools import partial
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "CLASSIFIER-R4-RESIDUAL-UNKNOWN-REVIEW"
R3_BASE_COMMIT = "7bf804684ac22dcf71560bacae4d3bc49c56f08f"
PRODUCTION_MODERN_SHA256 = (
    "df9c55e78e8fd8ed9e6cb18b0117a4d2947f207a302fe7148b3da00deee74045"
)
RAKDOS_PERSIST_FAMILY = "modern-unknown-d0ef54702fd3"
ASMO_PERSIST_FAMILY = "modern-unknown-cb589e90e894"
GRUUL_BROODSCALE_FAMILY = "modern-unknown-c925796c2322"
ESPER_VALUE_FAMILY = "modern-unknown-4d4eaac6eb6a"
SCAPESHIFT_FAMILY = "modern-unknown-8a9473ba2af0"
GRUUL_VALAKUT_FAMILY = "modern-unknown-f20f8e8714d9"
GRUUL_MIDRANGE_FAMILY = "modern-unknown-77bb2b4214a3"
MONO_BLUE_NAMOR_FAMILY = "modern-unknown-8f8d03c40bec"
GOLGARI_GORYOS_FAMILY = "modern-unknown-c64dc8e87f67"
IZZET_PROWESS_FAMILY = "modern-unknown-cdcb142b2233"
SOLEMNITY_PRISON_FAMILY = "modern-unknown-d000dbc93b85"
MONO_GREEN_TRUDGE_FAMILY = "modern-unknown-d8545120ffef"
GRIXIS_TEMPO_FAMILY = "modern-unknown-e8a1b553a175"
ORZHOV_SOULTRADER_FAMILY = "modern-unknown-014e15a41666"
GRIXIS_DRESS_DOWN_FAMILY = "modern-unknown-0b995bbade03"
GRIXIS_GORYOS_EMPEROR_FAMILY = "modern-unknown-157abe8132a0"
MONO_WHITE_HUMANS_FAMILY = "modern-unknown-174b94f4f2e0"
GRUUL_CRAGGANWICK_FAMILY = "modern-unknown-1926eb946776"
HAMMER_KELLAN_FAMILY = "modern-unknown-251a8dc88b65"
IZZET_TWIN_FAMILY = "modern-unknown-2726cf0be0bf"
HARDENED_SCALES_FAMILY = "modern-unknown-6cdec22cea94"
IZZET_WIZARDS_FAMILY = "modern-unknown-94aa91fd1ab6"
GOLGARI_YAWGMOTH_FAMILY = "modern-unknown-becb8c1f6ef5"
AMULET_SCAPESHIFT_FAMILY = "modern-unknown-40c81d1ba673"
COSMOGOYF_NECRO_FAMILY = "modern-unknown-f427d58c5e09"
BADGERMOLE_FAMILY = "modern-unknown-5dc6814edc94"
BADGERMOLE_LANDFALL_FAMILY = "modern-unknown-26c7d5185a8c"
BOGLES_FAMILY = "modern-unknown-17c806aab0e8"
RECLAMATION_FAMILY = "modern-unknown-1dc1d7391989"
JESKAI_BLINK_FAMILY = "modern-unknown-3effd912c863"
MARDU_VIAL_FAMILY = "modern-unknown-6e45259d4cbc"
AGADEEM_PERSIST_REDUCED_CRYPT_FAMILY = "modern-unknown-7098cf8e171a"
JESKAI_ENERGY_LOW_RIDDLER_FAMILY = "modern-unknown-724659bc0555"
COFFERS_DIMIR_FAMILY = "modern-unknown-6e6a2cffda6b"
DARK_MAESTRO_UMORI_FAMILY = "modern-unknown-7cdba8c5c977"
DREDGE_FAMILY = "modern-unknown-65dd853f8982"
COFFERS_GOLGARI_FAMILY = "modern-unknown-85c03cc18342"
EIGHT_RACK_FAMILY = "modern-unknown-d8a3a621999d"
ELDRAZI_AGGRO_FAMILY = "modern-unknown-3e688b954ff0"
ELDRAZI_OUROBOROID_FAMILY = "modern-unknown-08e0d37d950d"
SULTAI_PERSIST_FAMILY = "modern-unknown-0fc20ed0d1a8"
GOLGARI_DELIRIUM_FAMILY = "modern-unknown-1309d5fb5ce4"
IZZET_THROUGH_THE_BREACH_FAMILY = "modern-unknown-9ad9a23fe35b"
IZZET_STORM_FAMILY = "modern-unknown-f6c2df4d63d4"
LEYLINE_FLING_FAMILY = "modern-unknown-c810dd70e4c7"
MONO_GREEN_STOMPY_FAMILY = "modern-unknown-5efeda24e2e7"
MONO_GREEN_STOMPY_COMPANION_FAMILY = "modern-unknown-73dd687413c6"
ORZHOV_BLINK_SPLASH_FAMILY = "modern-unknown-ee53a8117d33"
RAKDOS_THROUGH_THE_BREACH_FAMILY = "modern-unknown-9e8a95a158d5"
HAMMER_TRADITIONAL_FAMILY = "modern-unknown-745246ddeb2a"
GRIXIS_DEATHS_SHADOW_FAMILY = "modern-unknown-4de73a0d7f6e"
FOUR_COLOR_RITUAL_FAMILY = "modern-unknown-6255c07f9176"
BOROS_PONZA_WILDFIRE_FAMILY = "modern-unknown-64ca17c0a88d"
GRIXIS_PERSIST_WIZARDS_FAMILY = "modern-unknown-782af94428f3"
GRIXIS_TEMPO_BOWMASTERS_FAMILY = "modern-unknown-7ca40990f449"
RAKDOS_PROWESS_FAMILY = "modern-unknown-87d0e54d5345"
BOROS_PONZA_CLASSIC_FAMILY = "modern-unknown-8e1de8a754a2"
GRIXIS_TEMPO_COUNTERSPELL_FAMILY = "modern-unknown-bb82db02b4ee"
GRIXIS_TEMPO_DRC_FROG_FAMILY = "modern-unknown-e03b46d95002"
IZZET_EXTRA_TURNS_FAMILY = "modern-unknown-28864e4b6383"
JUND_GOBLINS_FAMILY = "modern-unknown-3ab0e49c176d"
THOPTER_SWORD_BANT_FAMILY = "modern-unknown-4639ca7147ab"
RAKDOS_AGGRO_FAMILY = "modern-unknown-465f32dfb900"
PRIMAL_PRAYERS_RECRUITER_FAMILY = "modern-unknown-46baf67c1642"
NAYA_MIDRANGE_FAMILY = "modern-unknown-5e167b22ccb6"
FIVE_COLOR_ELEMENTALS_FAMILY = "modern-unknown-6e1c14f7b030"
CHEERIOS_FAMILY = "modern-unknown-7194c067c7e5"
SHAPE_ANEW_FAMILY = "modern-unknown-92354c51b659"
GLIMPSE_OF_TOMORROW_FAMILY = "modern-unknown-b35428553e0c"
PRIMAL_PRAYERS_ZENITH_FAMILY = "modern-unknown-d3e8d417dbf5"
IZZET_CAULDRON_FAMILY = "modern-unknown-f9b8736e59a5"
DIMIR_PERSIST_FAMILY = "modern-unknown-47921f86891e"
DOMAIN_PERSIST_FAMILY = "modern-unknown-4f48c58e17cb"
SULTAI_FLICKER_FAMILY = "modern-unknown-99f4f6946fe2"
AZORIUS_MIRACLES_FAMILY = "modern-unknown-a570ab7c1ee0"
DOMAIN_BLINK_FAMILY = "modern-unknown-a987668fb382"
RAKDOS_DELIRIUM_PHOENIX_FAMILY = "modern-unknown-bade2031fce6"
FIVE_COLOR_HUMANS_FAMILY = "modern-unknown-c588af306ed2"
RAKDOS_DELIRIUM_CASEY_FAMILY = "modern-unknown-ca0967fb3ab9"
DIMIR_UNEARTH_WHITE_SPLASH_FAMILY = "modern-unknown-4a8e9a81cd25"
IZZET_TEMPO_FAMILY = "modern-unknown-86014f893ae1"
DIMIR_GORYOS_FAMILY = "modern-unknown-8b9d88b4d4c6"
RAKDOS_MIDRANGE_FAMILY = "modern-unknown-9e72ce2f6c78"
YAWGMOTH_ENERGY_FAMILY = "modern-unknown-b5243e1c56bb"
SULTAI_TEMPO_FAMILY = "modern-unknown-b58b3b755e16"
SOLEMNITY_BLINK_FAMILY = "modern-unknown-bcc1db022ac3"
DIMIR_UNEARTH_DIMIR_FAMILY = "modern-unknown-d49bd3453662"
MONO_BLACK_SAGA_FAMILY = "modern-unknown-d6c7e03a49ef"

IZZET_WIZARDS_REVIEWED_WHITE_SPELLS = (
    "Beza, the Bounding Spring",
    "Blossoming Calm",
    "Celestial Purge",
    "Dovin's Veto",
    "Elesh Norn, Mother of Machines",
    "Ephemerate",
    "Erode",
    "Get Lost",
    "Hallowed Moonlight",
    "High Noon",
    "Kaheera, the Orphanguard",
    "Kor Firewalker",
    "March of Otherworldly Light",
    "No More Lies",
    "Orim's Chant",
    "Oust",
    "Path to Exile",
    "Phlage, Titan of Fire's Fury",
    "Pinnacle Starcage",
    "Prismatic Ending",
    "Reprieve",
    "Rest for the Weary",
    "Rest in Peace",
    "Silence",
    "Solitude",
    "Sphinx's Revelation",
    "Sunset Revelry",
    "Supreme Verdict",
    "Suppression Ray",
    "Teferi, Hero of Dominaria",
    "Teferi, Time Raveler",
    "Temporary Lockdown",
    "Terminus",
    "The Wandering Emperor",
    "Thraben Charm",
    "Timeless Dragon",
    "Voice of Victory",
    "Wear/Tear",
    "White Orchid Phantom",
    "Wrath of the Skies",
    "Zirda, the Dawnwaker",
)


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _read_mapping(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a mapping")
    return value


def _accepted_shadow_families(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "docs" / "audits" / "classifier-r4" / "dispositions.yaml"
    document = _read_mapping(path)
    if (
        document.get("task_id") != TASK_ID
        or document.get("base_commit") != R3_BASE_COMMIT
    ):
        raise ValueError(f"{path}: unexpected R4 disposition identity")
    families = document.get("families")
    if not isinstance(families, list):
        raise ValueError(f"{path}: families must be a list")
    return {
        item["family_id"]: item
        for item in families
        if isinstance(item, dict)
        and item.get("owner_accepted") is True
        and item.get("disposition") in {"map_existing", "new_identity"}
    }


def _add_rakdos_persist(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "rakdos-persist" for item in archetypes):
        raise ValueError("rakdos-persist already exists in the production baseline")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "esper-persist"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one esper-persist insertion anchor")
    archetypes.insert(
        anchors[0] + 1,
        {
            "id": "rakdos-persist",
            "name": "Rakdos Persist",
            "priority": 639600,
            "rules": [
                {
                    "id": "rakdos-persist-primary",
                    "priority": 639600,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {"card": "Persist", "zone": "main", "min_count": 3},
                            {
                                "card": "Archon of Cruelty",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Faithless Looting",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Bloodghast",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Stitcher's Supplier",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Abhorrent Oculus",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "Living End",
                                "zone": "main",
                                "max_count": 2,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_mardu_vial(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "mardu-vial" for item in archetypes):
        raise ValueError("mardu-vial already exists in the production baseline")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "mardu-energy"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one mardu-energy insertion anchor")
    archetypes.insert(
        anchors[0] + 1,
        {
            "id": "mardu-vial",
            "name": "Mardu Vial",
            "priority": 686250,
            "rules": [
                {
                    "id": "mardu-vial-primary",
                    "priority": 686250,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Aether Vial",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Imperial Recruiter",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Chthonian Nightmare",
                                "zone": "main",
                                "min_count": 2,
                            },
                            {
                                "card": "Solitude",
                                "zone": "main",
                                "min_count": 3,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_mono_white_humans(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "mono-white-humans" for item in archetypes):
        raise ValueError("mono-white-humans already exists in the production baseline")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "esper-energy"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one esper-energy insertion anchor")
    off_color_conditions = [
        {
            "card": f"__classifier-semantic-main-{color}-source__",
            "zone": "main",
            "exact_count": 0,
        }
        for color in ("blue", "black", "red", "green")
    ] + [
        {
            "card": f"__classifier-semantic-any-{color}-spell__",
            "zone": "any",
            "exact_count": 0,
        }
        for color in ("blue", "black", "red", "green")
    ]
    archetypes.insert(
        anchors[0] + 1,
        {
            "id": "mono-white-humans",
            "name": "Mono-White Humans",
            "priority": 683500,
            "rules": [
                {
                    "id": "mono-white-humans-primary",
                    "priority": 683500,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Aether Vial",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Champion of the Parish",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Thalia's Lieutenant",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Coppercoat Vanguard",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {"card": "Plains", "zone": "main", "min_count": 5},
                            {
                                "card": "Ocelot Pride",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            *off_color_conditions,
                        ]
                    },
                }
            ],
        },
    )


def _add_gruul_cragganwick(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "gruul-cragganwick" for item in archetypes):
        raise ValueError("gruul-cragganwick already exists in the production baseline")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "cremator-goryos"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one cremator-goryos insertion anchor")
    archetypes.insert(
        anchors[0],
        {
            "id": "gruul-cragganwick",
            "name": "Gruul Cragganwick",
            "priority": 641310,
            "rules": [
                {
                    "id": "gruul-cragganwick-primary",
                    "priority": 641310,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Cragganwick Cremator",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Yargle and Multani",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Badgermole Cub",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Blood Moon",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "__classifier-semantic-main-red-source__",
                                "zone": "main",
                                "min_count": 1,
                            },
                            {
                                "card": "__classifier-semantic-main-green-source__",
                                "zone": "main",
                                "min_count": 1,
                            },
                            {
                                "card": "__classifier-semantic-main-white-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-main-blue-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-main-black-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "Goryo's Vengeance",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "Emrakul, the Aeons Torn",
                                "zone": "main",
                                "exact_count": 0,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_agadeem_persist_reduced_crypt_path(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    matches = [item for item in archetypes if item.get("id") == "agadeem-persist"]
    if len(matches) != 1:
        raise ValueError("expected exactly one agadeem-persist parent")
    rules = matches[0].get("rules")
    if not isinstance(rules, list):
        raise ValueError("agadeem-persist has no rule list")
    if any(item.get("id") == "agadeem-persist-reduced-crypt" for item in rules):
        raise ValueError("agadeem-persist-reduced-crypt already exists")
    rules.append(
        {
            "id": "agadeem-persist-reduced-crypt",
            "priority": 639400,
            "subtype_id": None,
            "conditions": {
                "all": [
                    {"card": "Persist", "zone": "main", "min_count": 3},
                    {
                        "card": "Archon of Cruelty",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {
                        "card": "Crypt of Agadeem",
                        "zone": "main",
                        "min_count": 1,
                        "max_count": 2,
                    },
                    {"card": "Eyetwitch", "zone": "main", "min_count": 3},
                    {
                        "card": "Stitcher's Supplier",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {
                        "card": "Phyrexian Tower",
                        "zone": "main",
                        "min_count": 3,
                    },
                ]
            },
        }
    )


def _add_asmo_persist(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "asmo-persist" for item in archetypes):
        raise ValueError("asmo-persist already exists in the production baseline")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "esper-persist"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one esper-persist insertion anchor")
    archetypes.insert(
        anchors[0] + 1,
        {
            "id": "asmo-persist",
            "name": "Asmo Persist",
            "priority": 639650,
            "rules": [
                {
                    "id": "asmo-persist-primary",
                    "priority": 639650,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {"card": "Persist", "zone": "main", "min_count": 3},
                            {
                                "card": "Archon of Cruelty",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Faithless Looting",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Asmoranomardicadaistinaculdacar",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "The Underworld Cookbook",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Ovalchase Daredevil",
                                "zone": "main",
                                "min_count": 3,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_sultai_persist(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "sultai-persist" for item in archetypes):
        raise ValueError("sultai-persist already exists in the production baseline")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "esper-persist"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one esper-persist insertion anchor")
    archetypes.insert(
        anchors[0] + 1,
        {
            "id": "sultai-persist",
            "name": "Sultai Persist",
            "priority": 639500,
            "rules": [
                {
                    "id": "sultai-persist-primary",
                    "priority": 639500,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {"card": "Persist", "zone": "main", "min_count": 3},
                            {
                                "card": "Archon of Cruelty",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Psychic Frog",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Malevolent Rumble",
                                "zone": "main",
                                "min_count": 3,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_golgari_goryos(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "golgari-goryos" for item in archetypes):
        raise ValueError("golgari-goryos already exists in the production baseline")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "esper-goryos"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one Esper Goryo's insertion anchor")
    archetypes.insert(
        anchors[0] + 1,
        {
            "id": "golgari-goryos",
            "name": "Golgari Goryo's",
            "priority": 641150,
            "rules": [
                {
                    "id": "golgari-goryos-primary",
                    "priority": 641150,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Goryo's Vengeance",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Dina's Guidance",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Formidable Speaker",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "__classifier-semantic-main-black-source__",
                                "zone": "main",
                                "min_count": 1,
                            },
                            {
                                "card": "__classifier-semantic-main-green-source__",
                                "zone": "main",
                                "min_count": 1,
                            },
                            *(
                                {
                                    "card": f"__classifier-semantic-main-{color}-source__",
                                    "zone": "main",
                                    "exact_count": 0,
                                }
                                for color in ("white", "blue", "red")
                            ),
                        ]
                    },
                }
            ],
        },
    )


def _add_grixis_goryos_emperor_path(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    matches = [item for item in archetypes if item.get("id") == "grixis-goryos"]
    if len(matches) != 1:
        raise ValueError("expected exactly one grixis-goryos parent")
    rules = matches[0].get("rules")
    if not isinstance(rules, list):
        raise ValueError("grixis-goryos has no rule list")
    if any(item.get("id") == "grixis-goryos-emperor" for item in rules):
        raise ValueError("grixis-goryos-emperor already exists")
    rules.append(
        {
            "id": "grixis-goryos-emperor",
            "priority": 641090,
            "subtype_id": None,
            "conditions": {
                "all": [
                    {
                        "card": "Goryo's Vengeance",
                        "zone": "main",
                        "min_count": 1,
                        "max_count": 2,
                    },
                    {
                        "card": "Emperor of Bones",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {
                        "card": "Atraxa, Grand Unifier",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {
                        "card": "Faithless Looting",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {
                        "card": "Psychic Frog",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {"card": "Ephemerate", "zone": "main", "exact_count": 0},
                    {"card": "Persist", "zone": "main", "exact_count": 0},
                ]
            },
        }
    )


def _add_golgari_delirium(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "golgari-delirium" for item in archetypes):
        raise ValueError("golgari-delirium already exists in the production baseline")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "deaths-shadow"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one deaths-shadow insertion anchor")
    archetypes.insert(
        anchors[0] + 1,
        {
            "id": "golgari-delirium",
            "name": "Golgari Delirium",
            "priority": 619500,
            "rules": [
                {
                    "id": "golgari-delirium-primary",
                    "priority": 619500,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Nethergoyf",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Omnivorous Flytrap",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Mishra's Bauble",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Witherbloom Command",
                                "zone": "main",
                                "min_count": 2,
                            },
                            {
                                "card": "__classifier-semantic-main-black-source__",
                                "zone": "main",
                                "min_count": 1,
                            },
                            {
                                "card": "__classifier-semantic-main-green-source__",
                                "zone": "main",
                                "min_count": 1,
                            },
                            {
                                "card": "__classifier-semantic-main-white-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-main-blue-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-main-red-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_bogles(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "bogles" for item in archetypes):
        raise ValueError("bogles already exists in the production baseline")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "steel-cutter"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one steel-cutter insertion anchor")
    archetypes.insert(
        anchors[0] + 1,
        {
            "id": "bogles",
            "name": "Bogles",
            "priority": 673500,
            "rules": [
                {
                    "id": "bogles-primary",
                    "priority": 673500,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Slippery Bogle",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Gladecover Scout",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Ethereal Armor",
                                "zone": "main",
                                "min_count": 3,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_solemnity_prison(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "solemnity-prison" for item in archetypes):
        raise ValueError("solemnity-prison already exists in the production baseline")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "steel-cutter"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one steel-cutter insertion anchor")
    archetypes.insert(
        anchors[0] + 1,
        {
            "id": "solemnity-prison",
            "name": "Solemnity Prison",
            "priority": 673700,
            "rules": [
                {
                    "id": "solemnity-prison-nine-lives",
                    "priority": 673700,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Solemnity",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Nine Lives",
                                "zone": "main",
                                "min_count": 3,
                            },
                        ]
                    },
                },
                {
                    "id": "solemnity-prison-unlife",
                    "priority": 673600,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Solemnity",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Phyrexian Unlife",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Nine Lives",
                                "zone": "main",
                                "max_count": 2,
                            },
                        ]
                    },
                },
            ],
        },
    )


def _add_mono_green_trudge(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "mono-green-trudge" for item in archetypes):
        raise ValueError("mono-green-trudge already exists in production")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "fight-rigging"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one Fight Rigging insertion anchor")
    archetypes.insert(
        anchors[0],
        {
            "id": "mono-green-trudge",
            "name": "Mono-Green Trudge",
            "priority": 641050,
            "rules": [
                {
                    "id": "mono-green-trudge-primary",
                    "priority": 641050,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Slumbering Trudge",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "The Great Henge",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Fight Rigging",
                                "zone": "main",
                                "max_count": 2,
                            },
                            {
                                "card": "__classifier-semantic-main-white-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-main-blue-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-main-black-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-main-red-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_grixis_tempo(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "grixis-tempo" for item in archetypes):
        raise ValueError("grixis-tempo already exists in production")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "dimir-tempo"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one Dimir Tempo insertion anchor")
    dimir_tempo = archetypes[anchors[0]]
    expected_subtypes = [
        {"id": "dimir", "name": "Dimir"},
        {"id": "grixis", "name": "Grixis"},
        {"id": "esper", "name": "Esper"},
    ]
    if dimir_tempo.get("subtypes") != expected_subtypes:
        raise ValueError("Dimir Tempo production subtypes changed from reviewed base")
    grixis_rules = [
        item
        for item in dimir_tempo.get("rules", [])
        if item.get("id") == "dimir-tempo-grixis"
    ]
    if len(grixis_rules) != 1:
        raise ValueError("expected exactly one Dimir Tempo Grixis rule")
    expected_grixis_rule = {
        "id": "dimir-tempo-grixis",
        "priority": 638000,
        "subtype_id": "grixis",
        "conditions": {
            "all": [
                {"card": "Fatal Push", "zone": "main", "min_count": 3},
                {"card": "Counterspell", "zone": "main", "min_count": 3},
                {"card": "Watery Grave", "zone": "main", "min_count": 1},
                {"card": "Steam Vents", "zone": "main", "min_count": 1},
            ]
        },
    }
    if grixis_rules[0] != expected_grixis_rule:
        raise ValueError("Dimir Tempo Grixis rule changed from reviewed base")

    dimir_tempo["subtypes"] = [
        {"id": "dimir", "name": "Dimir"},
        {"id": "grixis", "name": "Dimir Red Splash"},
        {"id": "esper", "name": "Dimir White Splash"},
    ]
    grixis_rules[0]["conditions"]["all"].append(
        {
            "card": "Ragavan, Nimble Pilferer",
            "zone": "main",
            "max_count": 2,
        }
    )
    archetypes.insert(
        anchors[0],
        {
            "id": "grixis-tempo",
            "name": "Grixis Tempo",
            "priority": 638100,
            "rules": [
                {
                    "id": "grixis-tempo-ragavan",
                    "priority": 638100,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Fatal Push",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Psychic Frog",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Ragavan, Nimble Pilferer",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Watery Grave",
                                "zone": "main",
                                "min_count": 1,
                            },
                            {
                                "card": "Steam Vents",
                                "zone": "main",
                                "min_count": 1,
                            },
                            {
                                "card": "Goryo's Vengeance",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "Persist",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "Death's Shadow",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-main-white-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-main-green-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_grixis_dress_down(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "grixis-dress-down" for item in archetypes):
        raise ValueError("grixis-dress-down already exists in production")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "dimir-tempo"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one Dimir Tempo insertion anchor")
    archetypes.insert(
        anchors[0],
        {
            "id": "grixis-dress-down",
            "name": "Grixis Dress Down",
            "priority": 638050,
            "rules": [
                {
                    "id": "grixis-dress-down-primary",
                    "priority": 638050,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {"card": "Dress Down", "zone": "main", "min_count": 3},
                            {
                                "card": "Nulldrifter",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Kroxa, Titan of Death's Hunger",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Steam Vents",
                                "zone": "main",
                                "min_count": 1,
                            },
                            {
                                "card": "Watery Grave",
                                "zone": "main",
                                "min_count": 1,
                            },
                            {
                                "card": "Goryo's Vengeance",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "Persist",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "Death's Shadow",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-main-white-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-main-green-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-any-white-spell__",
                                "zone": "any",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-any-green-spell__",
                                "zone": "any",
                                "exact_count": 0,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_orzhov_soultrader_subtype(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    matches = [item for item in archetypes if item.get("id") == "soultrader"]
    if len(matches) != 1:
        raise ValueError("expected exactly one Soultrader parent")
    soultrader = matches[0]
    expected = {
        "id": "soultrader",
        "name": "Soultrader",
        "priority": 619000,
        "subtypes": [
            {"id": "golgari", "name": "Golgari"},
            {"id": "sultai", "name": "Sultai"},
            {"id": "dimir", "name": "Dimir"},
        ],
        "rules": [
            {
                "id": "soultrader-sultai",
                "priority": 619000,
                "subtype_id": "sultai",
                "conditions": {
                    "all": [
                        {
                            "card": "Warren Soultrader",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {
                            "card": "Birthing Ritual",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {
                            "card": "Marionette Apprentice",
                            "zone": "main",
                            "min_count": 3,
                        },
                    ]
                },
            },
            {
                "id": "soultrader-dimir",
                "priority": 618900,
                "subtype_id": "dimir",
                "conditions": {
                    "all": [
                        {"card": "Gravecrawler", "zone": "main", "min_count": 3},
                        {"card": "Unearth", "zone": "main", "min_count": 3},
                        {
                            "card": "Marionette Apprentice",
                            "zone": "main",
                            "min_count": 3,
                        },
                    ]
                },
            },
            {
                "id": "soultrader-golgari",
                "priority": 618800,
                "subtype_id": "golgari",
                "conditions": {
                    "all": [
                        {"card": "Gravecrawler", "zone": "main", "min_count": 3},
                        {
                            "card": "Chthonian Nightmare",
                            "zone": "main",
                            "min_count": 2,
                        },
                        {
                            "card": "Overgrown Tomb",
                            "zone": "main",
                            "min_count": 1,
                        },
                    ]
                },
            },
        ],
    }
    if soultrader != expected:
        raise ValueError("Soultrader production rules changed from reviewed base")

    soultrader["priority"] = 687100
    soultrader["subtypes"].append({"id": "orzhov", "name": "Orzhov"})
    soultrader["rules"].insert(
        0,
        {
            "id": "soultrader-orzhov",
            "priority": 687100,
            "subtype_id": "orzhov",
            "conditions": {
                "all": [
                    {
                        "card": "Warren Soultrader",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {"card": "Gravecrawler", "zone": "main", "min_count": 3},
                    {
                        "card": "Marionette Apprentice",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {"card": "Godless Shrine", "zone": "main", "min_count": 1},
                    {
                        "card": "__classifier-semantic-main-blue-source__",
                        "zone": "main",
                        "exact_count": 0,
                    },
                    {
                        "card": "__classifier-semantic-main-green-source__",
                        "zone": "main",
                        "exact_count": 0,
                    },
                    {
                        "card": "__classifier-semantic-main-red-source__",
                        "zone": "main",
                        "exact_count": 0,
                    },
                    {
                        "card": "__classifier-semantic-any-blue-spell__",
                        "zone": "any",
                        "exact_count": 0,
                    },
                    {
                        "card": "__classifier-semantic-any-green-spell__",
                        "zone": "any",
                        "exact_count": 0,
                    },
                    {
                        "card": "__classifier-semantic-any-red-spell__",
                        "zone": "any",
                        "exact_count": 0,
                    },
                ]
            },
        },
    )


def _add_reclamation_parents(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    added_ids = {"temur-reclamation", "bant-reclamation"}
    if any(item.get("id") in added_ids for item in archetypes):
        raise ValueError(
            "a Reclamation parent already exists in the production baseline"
        )
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "chant-control"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one chant-control insertion anchor")

    omnath_matches = [
        item for item in archetypes if item.get("id") == "omnath-midrange"
    ]
    if len(omnath_matches) != 1:
        raise ValueError("expected exactly one Omnath Midrange parent")
    omnath = omnath_matches[0]
    omnath_rules = omnath.get("rules")
    if (
        omnath.get("priority") != 307000
        or not isinstance(omnath_rules, list)
        or len(omnath_rules) != 1
        or omnath_rules[0].get("id") != "omnath-midrange-primary"
        or omnath_rules[0].get("priority") != 307000
    ):
        raise ValueError("Omnath Midrange changed from the reviewed production base")
    omnath["priority"] = 623700
    omnath_rules[0]["priority"] = 623700

    archetypes[anchors[0] : anchors[0]] = [
        {
            "id": "temur-reclamation",
            "name": "Temur Reclamation",
            "priority": 623500,
            "rules": [
                {
                    "id": "temur-reclamation-primary",
                    "priority": 623500,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Wilderness Reclamation",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "__classifier-semantic-main-blue-source__",
                                "zone": "main",
                                "min_count": 1,
                            },
                            {
                                "card": "__classifier-semantic-main-red-source__",
                                "zone": "main",
                                "min_count": 1,
                            },
                            {
                                "card": "__classifier-semantic-main-green-source__",
                                "zone": "main",
                                "min_count": 1,
                            },
                            {
                                "card": "__classifier-semantic-main-white-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-main-black-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-any-white-spell__",
                                "zone": "any",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-any-black-spell__",
                                "zone": "any",
                                "exact_count": 0,
                            },
                        ]
                    },
                }
            ],
        },
        {
            "id": "bant-reclamation",
            "name": "Bant Reclamation",
            "priority": 623400,
            "rules": [
                {
                    "id": "bant-reclamation-primary",
                    "priority": 623400,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Wilderness Reclamation",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "__classifier-semantic-main-white-source__",
                                "zone": "main",
                                "min_count": 1,
                            },
                            {
                                "card": "__classifier-semantic-main-blue-source__",
                                "zone": "main",
                                "min_count": 1,
                            },
                            {
                                "card": "__classifier-semantic-main-green-source__",
                                "zone": "main",
                                "min_count": 1,
                            },
                            {
                                "card": "__classifier-semantic-main-red-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-main-black-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-any-red-spell__",
                                "zone": "any",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-any-black-spell__",
                                "zone": "any",
                                "exact_count": 0,
                            },
                        ]
                    },
                }
            ],
        },
    ]


def _add_izzet_storm(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "izzet-storm" for item in archetypes):
        raise ValueError("izzet-storm already exists in the production baseline")
    anchors = [
        index for index, item in enumerate(archetypes) if item.get("id") == "ruby-storm"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one ruby-storm insertion anchor")
    archetypes.insert(
        anchors[0],
        {
            "id": "izzet-storm",
            "name": "Izzet Storm",
            "priority": 214100,
            "rules": [
                {
                    "id": "izzet-storm-primary",
                    "priority": 214100,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Ral, Monsoon Mage",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Stormcatch Mentor",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Past in Flames",
                                "zone": "main",
                                "min_count": 2,
                            },
                            {
                                "card": "Ruby Medallion",
                                "zone": "main",
                                "exact_count": 0,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_izzet_twin(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "izzet-twin" for item in archetypes):
        raise ValueError("izzet-twin already exists in the production baseline")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "izzet-wizards"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one Izzet Wizards insertion anchor")
    archetypes.insert(
        anchors[0],
        {
            "id": "izzet-twin",
            "name": "Izzet Twin",
            "priority": 622100,
            "rules": [
                {
                    "id": "izzet-twin-primary",
                    "priority": 622100,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Splinter Twin",
                                "zone": "main",
                                "min_count": 2,
                            },
                            {
                                "card": "Fear of Missing Out",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "__classifier-semantic-main-blue-source__",
                                "zone": "main",
                                "min_count": 1,
                            },
                            {
                                "card": "__classifier-semantic-main-red-source__",
                                "zone": "main",
                                "min_count": 1,
                            },
                            {
                                "card": "__classifier-semantic-main-white-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-main-black-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-main-green-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-any-white-spell__",
                                "zone": "any",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-any-black-spell__",
                                "zone": "any",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-any-green-spell__",
                                "zone": "any",
                                "exact_count": 0,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_eldrazi_ouroboroid(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "eldrazi-ouroboroid" for item in archetypes):
        raise ValueError("eldrazi-ouroboroid already exists in the production baseline")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "eldrazi-aggro"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one eldrazi-aggro insertion anchor")
    archetypes.insert(
        anchors[0] + 1,
        {
            "id": "eldrazi-ouroboroid",
            "name": "Eldrazi Ouroboroid",
            "priority": 315900,
            "rules": [
                {
                    "id": "eldrazi-ouroboroid-primary",
                    "priority": 315900,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Ouroboroid",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Badgermole Cub",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Eldrazi Temple",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Sowing Mycospawn",
                                "zone": "main",
                                "min_count": 3,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _relax_gruul_broodscale_blade(document: dict[str, Any]) -> None:
    rules = [
        rule
        for archetype in document["archetypes"]
        if archetype.get("id") == "broodscale-combo"
        for rule in archetype["rules"]
        if rule.get("id") == "broodscale-combo-gruul"
    ]
    if len(rules) != 1:
        raise ValueError("expected exactly one Gruul Broodscale rule")
    conditions = [
        item
        for item in rules[0]["conditions"]["all"]
        if item.get("card") == "Blade of the Bloodchief"
    ]
    if conditions != [
        {"card": "Blade of the Bloodchief", "zone": "main", "min_count": 3}
    ]:
        raise ValueError("Gruul Broodscale Blade baseline changed")
    conditions[0]["min_count"] = 2


def _add_esper_value_paths(document: dict[str, Any]) -> None:
    archetypes = {item["id"]: item for item in document["archetypes"]}
    ketramose = archetypes.get("esper-ketramose")
    blink = archetypes.get("esper-blink")
    if not isinstance(ketramose, dict) or not isinstance(blink, dict):
        raise ValueError("expected Esper Ketramose and Esper Blink parents")

    primary = [
        item
        for item in ketramose["rules"]
        if item.get("id") == "esper-ketramose-primary"
    ]
    if len(primary) != 1:
        raise ValueError("expected exactly one Esper Ketramose primary rule")
    low_count = deepcopy(primary[0])
    low_count["id"] = "esper-ketramose-low-count"
    low_count["priority"] = 632850
    for condition in low_count["conditions"]["all"]:
        if condition["card"] in {"Relic of Progenitus", "Ketramose, the New Dawn"}:
            condition["min_count"] = 2
    low_count["conditions"]["all"].append(
        {
            "card": "Phelia, Exuberant Shepherd",
            "zone": "main",
            "max_count": 2,
        }
    )
    ketramose["rules"].append(low_count)

    blink["rules"].append(
        {
            "id": "esper-blink-ephemerate",
            "priority": 632650,
            "subtype_id": None,
            "conditions": {
                "all": [
                    {"card": "Ephemerate", "zone": "main", "min_count": 2},
                    {"card": "Quantum Riddler", "zone": "main", "min_count": 3},
                    {"card": "Solitude", "zone": "main", "min_count": 3},
                    {"card": "Psychic Frog", "zone": "main", "min_count": 3},
                    {
                        "card": "Wrath of the Skies",
                        "zone": "main",
                        "max_count": 2,
                    },
                    {
                        "card": "__classifier-semantic-main-red-source__",
                        "zone": "main",
                        "exact_count": 0,
                    },
                    {
                        "card": "__classifier-semantic-main-green-source__",
                        "zone": "main",
                        "exact_count": 0,
                    },
                    {
                        "card": "Goryo's Vengeance",
                        "zone": "main",
                        "exact_count": 0,
                    },
                    {"card": "Persist", "zone": "main", "exact_count": 0},
                ]
            },
        }
    )


def _add_amulet_scapeshift_path(document: dict[str, Any]) -> None:
    archetypes = {item["id"]: item for item in document["archetypes"]}
    amulet = archetypes.get("amulet-titan")
    if not isinstance(amulet, dict):
        raise ValueError("expected Amulet Titan parent")
    amulet["rules"].append(
        {
            "id": "amulet-titan-scapeshift",
            "priority": 666700,
            "subtype_id": None,
            "conditions": {
                "all": [
                    {"card": "Amulet of Vigor", "zone": "main", "min_count": 4},
                    {"card": "Scapeshift", "zone": "main", "min_count": 3},
                    {"card": "Cultivator Colossus", "zone": "main", "min_count": 3},
                    {"card": "Primeval Titan", "zone": "main", "min_count": 2},
                    {"card": "Urza's Saga", "zone": "main", "min_count": 3},
                ]
            },
        }
    )


def _add_scapeshift(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "scapeshift" for item in archetypes):
        raise ValueError("scapeshift already exists in the production baseline")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "amulet-titan"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one Amulet Titan insertion anchor")
    common = [
        {"card": "Scapeshift", "zone": "main", "min_count": 2},
        {"card": "Valakut, the Molten Pinnacle", "zone": "main", "min_count": 3},
        {"card": "Dryad of the Ilysian Grove", "zone": "main", "min_count": 3},
        {"card": "Icetill Explorer", "zone": "main", "min_count": 3},
        {"card": "Amulet of Vigor", "zone": "main", "exact_count": 0},
    ]
    archetypes.insert(
        anchors[0] + 1,
        {
            "id": "scapeshift",
            "name": "Scapeshift",
            "priority": 666600,
            "subtypes": [
                {"id": "naya", "name": "Naya"},
                {"id": "four-color", "name": "Four-Color"},
            ],
            "rules": [
                {
                    "id": "scapeshift-four-color",
                    "priority": 666600,
                    "subtype_id": "four-color",
                    "conditions": {
                        "all": common
                        + [
                            {"card": "Bring to Light", "zone": "main", "min_count": 2},
                            {
                                "card": "__classifier-semantic-main-white-source__",
                                "zone": "main",
                                "min_count": 1,
                            },
                            {
                                "card": "__classifier-semantic-main-blue-source__",
                                "zone": "main",
                                "min_count": 1,
                            },
                            {
                                "card": "__classifier-semantic-main-black-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                        ]
                    },
                },
                {
                    "id": "scapeshift-naya",
                    "priority": 666500,
                    "subtype_id": "naya",
                    "conditions": {
                        "all": common
                        + [
                            {
                                "card": "__classifier-semantic-main-white-source__",
                                "zone": "main",
                                "min_count": 1,
                            },
                            {
                                "card": "__classifier-semantic-main-blue-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-main-black-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "Bring to Light",
                                "zone": "main",
                                "exact_count": 0,
                            },
                        ]
                    },
                },
            ],
        },
    )


def _add_gruul_valakut(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "gruul-valakut" for item in archetypes):
        raise ValueError("gruul-valakut already exists in the production baseline")
    anchors = [
        index for index, item in enumerate(archetypes) if item.get("id") == "scapeshift"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one Scapeshift insertion anchor")
    archetypes.insert(
        anchors[0] + 1,
        {
            "id": "gruul-valakut",
            "name": "Gruul Valakut",
            "priority": 666400,
            "rules": [
                {
                    "id": "gruul-valakut-primary",
                    "priority": 666400,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Valakut, the Molten Pinnacle",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Dryad of the Ilysian Grove",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Icetill Explorer",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {"card": "Vibrance", "zone": "main", "min_count": 3},
                            {"card": "Wrenn and Six", "zone": "main", "min_count": 3},
                            {"card": "Scapeshift", "zone": "main", "exact_count": 0},
                            {
                                "card": "Amulet of Vigor",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-main-white-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-main-blue-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "__classifier-semantic-main-black-source__",
                                "zone": "main",
                                "exact_count": 0,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_gruul_midrange(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "gruul-midrange" for item in archetypes):
        raise ValueError("gruul-midrange already exists in the production baseline")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "boros-land-destruction"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one Boros Ponza insertion anchor")
    archetypes.insert(
        anchors[0] + 1,
        {
            "id": "gruul-midrange",
            "name": "Gruul Midrange",
            "priority": 660500,
            "rules": [
                {
                    "id": "gruul-midrange-primary",
                    "priority": 660500,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Karn, the Great Creator",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Blood Moon",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Utopia Sprawl",
                                "zone": "main",
                                "min_count": 3,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_mono_blue_namor(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "mono-blue-namor" for item in archetypes):
        raise ValueError("mono-blue-namor already exists in the production baseline")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "izzet-wizards"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one Izzet Wizards insertion anchor")
    exclusions = [
        {
            "card": f"__classifier-semantic-main-{color}-source__",
            "zone": "main",
            "exact_count": 0,
        }
        for color in ("white", "black", "red", "green")
    ] + [
        {
            "card": f"__classifier-semantic-any-{color}-spell__",
            "zone": "any",
            "exact_count": 0,
        }
        for color in ("white", "black", "red", "green")
    ]
    archetypes.insert(
        anchors[0],
        {
            "id": "mono-blue-namor",
            "name": "Mono-Blue Namor",
            "priority": 622500,
            "rules": [
                {
                    "id": "mono-blue-namor-primary",
                    "priority": 622500,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Namor the Sub-Mariner",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Archmage's Charm",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Lord of Atlantis",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {
                                "card": "Goblin Charbelcher",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            *exclusions,
                        ]
                    },
                }
            ],
        },
    )


def _add_izzet_through_the_breach(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "izzet-through-the-breach" for item in archetypes):
        raise ValueError("izzet-through-the-breach already exists in production")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "eldrazi-ramp-chant"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one Eldrazi Ramp Chant insertion anchor")
    archetypes.insert(
        anchors[0] + 1,
        {
            "id": "izzet-through-the-breach",
            "name": "Izzet Through the Breach",
            "priority": 646800,
            "rules": [
                {
                    "id": "izzet-through-the-breach-primary",
                    "priority": 646800,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Through the Breach",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Emrakul, the Aeons Torn",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Ugin's Labyrinth",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {"card": "Eldrazi Temple", "zone": "main", "min_count": 3},
                            {
                                "card": "Devourer of Destiny",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Kozilek's Command",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Talisman of Creativity",
                                "zone": "main",
                                "min_count": 3,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_rakdos_through_the_breach(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "rakdos-through-the-breach" for item in archetypes):
        raise ValueError("rakdos-through-the-breach already exists in production")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "eldrazi-ramp-chant"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one Eldrazi Ramp Chant insertion anchor")
    archetypes.insert(
        anchors[0] + 1,
        {
            "id": "rakdos-through-the-breach",
            "name": "Rakdos Through the Breach",
            "priority": 646700,
            "rules": [
                {
                    "id": "rakdos-through-the-breach-primary",
                    "priority": 646700,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Through the Breach",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Emrakul, the Aeons Torn",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Ugin's Labyrinth",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {"card": "Eldrazi Temple", "zone": "main", "min_count": 3},
                            {
                                "card": "Devourer of Destiny",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Goryo's Vengeance",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Faithless Looting",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Talisman of Indulgence",
                                "zone": "main",
                                "min_count": 3,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_cosmogoyf_necrodominance_subtype(document: dict[str, Any]) -> None:
    archetypes = [
        item for item in document["archetypes"] if item.get("id") == "necrodominance"
    ]
    if len(archetypes) != 1:
        raise ValueError("expected exactly one Necrodominance parent")
    archetype = archetypes[0]
    if archetype.get("priority") != 636000:
        raise ValueError("Necrodominance parent priority changed")
    if any(item.get("id") == "cosmogoyf" for item in archetype["subtypes"]):
        raise ValueError("Cosmogoyf Necrodominance subtype already exists")
    archetype["priority"] = 636100
    archetype["subtypes"].append(
        {"id": "cosmogoyf", "name": "Cosmogoyf Necrodominance"}
    )
    archetype["rules"].append(
        {
            "id": "necrodominance-cosmogoyf",
            "priority": 636100,
            "subtype_id": "cosmogoyf",
            "conditions": {
                "all": [
                    {"card": "Necrodominance", "zone": "main", "min_count": 3},
                    {"card": "Cosmogoyf", "zone": "main", "min_count": 3},
                    {"card": "Thud", "zone": "main", "exact_count": 0},
                    {"card": "Fling", "zone": "main", "exact_count": 0},
                ]
            },
        }
    )


def _add_badgermole_and_devoted_subtypes(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    devoted_matches = [
        (index, item)
        for index, item in enumerate(archetypes)
        if item.get("id") == "devoted-druid-combo"
    ]
    if len(devoted_matches) != 1:
        raise ValueError("expected exactly one Devoted Druid Combo parent")
    devoted_index, devoted = devoted_matches[0]
    if devoted.get("priority") != 625000 or devoted.get("subtypes") is not None:
        raise ValueError("Devoted Druid Combo parent baseline changed")
    primary = devoted.get("rules")
    expected_primary = [
        {
            "id": "devoted-druid-combo-primary",
            "priority": 625000,
            "subtype_id": None,
            "conditions": {
                "all": [
                    {"card": "Devoted Druid", "zone": "main", "min_count": 3},
                    {
                        "card": "Vizier of Remedies",
                        "zone": "main",
                        "min_count": 1,
                    },
                    {"card": "Nature's Rhythm", "zone": "main", "min_count": 3},
                ]
            },
        }
    ]
    if primary != expected_primary:
        raise ValueError("Devoted Druid Combo primary rule baseline changed")

    common = deepcopy(primary[0]["conditions"]["all"])
    devoted["subtypes"] = [
        {"id": "abzan", "name": "Abzan"},
        {"id": "selesnya", "name": "Selesnya"},
    ]
    devoted["rules"] = [
        {
            "id": "devoted-druid-combo-primary",
            "priority": 625000,
            "subtype_id": "abzan",
            "conditions": {
                "all": common
                + [
                    {
                        "card": "__classifier-semantic-main-white-source__",
                        "zone": "main",
                        "min_count": 1,
                    },
                    {
                        "card": "__classifier-semantic-main-black-source__",
                        "zone": "main",
                        "min_count": 1,
                    },
                    {
                        "card": "__classifier-semantic-main-red-source__",
                        "zone": "main",
                        "exact_count": 0,
                    },
                ]
            },
        },
        {
            "id": "devoted-druid-combo-selesnya",
            "priority": 624900,
            "subtype_id": "selesnya",
            "conditions": {
                "all": common
                + [
                    {
                        "card": "__classifier-semantic-main-white-source__",
                        "zone": "main",
                        "min_count": 1,
                    },
                    {
                        "card": "__classifier-semantic-main-blue-source__",
                        "zone": "main",
                        "exact_count": 0,
                    },
                    {
                        "card": "__classifier-semantic-main-black-source__",
                        "zone": "main",
                        "exact_count": 0,
                    },
                    {
                        "card": "__classifier-semantic-main-red-source__",
                        "zone": "main",
                        "exact_count": 0,
                    },
                ]
            },
        },
    ]

    if any(item.get("id") == "badgermole-combo" for item in archetypes):
        raise ValueError("Badgermole Combo already exists in production")
    badgermole_common = [
        {"card": "Badgermole Cub", "zone": "main", "min_count": 3},
        {"card": "Leyline of Abundance", "zone": "main", "min_count": 3},
        {"card": "Green Sun's Zenith", "zone": "main", "min_count": 3},
        {"card": "Quirion Ranger", "zone": "main", "min_count": 3},
        {"card": "Vizier of Remedies", "zone": "main", "exact_count": 0},
    ]
    no_non_green_sources = [
        {
            "card": f"__classifier-semantic-main-{color}-source__",
            "zone": "main",
            "exact_count": 0,
        }
        for color in ("white", "blue", "red")
    ]
    archetypes.insert(
        devoted_index + 1,
        {
            "id": "badgermole-combo",
            "name": "Badgermole Combo",
            "priority": 624800,
            "subtypes": [
                {"id": "golgari", "name": "Golgari"},
                {"id": "mono-green", "name": "Mono-Green"},
            ],
            "rules": [
                {
                    "id": "badgermole-combo-golgari",
                    "priority": 624800,
                    "subtype_id": "golgari",
                    "conditions": {
                        "all": badgermole_common
                        + no_non_green_sources
                        + [
                            {
                                "card": "__classifier-semantic-main-black-source__",
                                "zone": "main",
                                "min_count": 1,
                            }
                        ]
                    },
                },
                {
                    "id": "badgermole-combo-mono-green",
                    "priority": 624700,
                    "subtype_id": "mono-green",
                    "conditions": {
                        "all": badgermole_common
                        + no_non_green_sources
                        + [
                            {
                                "card": "__classifier-semantic-main-black-source__",
                                "zone": "main",
                                "exact_count": 0,
                            }
                        ]
                    },
                },
            ],
        },
    )


def _add_badgermole_landfall_subtype(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    matches = [item for item in archetypes if item.get("id") == "badgermole-combo"]
    if len(matches) != 1:
        raise ValueError("expected exactly one reviewed Badgermole Combo parent")
    badgermole = matches[0]
    if badgermole.get("priority") != 624800:
        raise ValueError("Badgermole Combo parent priority changed")
    expected_subtypes = [
        {"id": "golgari", "name": "Golgari"},
        {"id": "mono-green", "name": "Mono-Green"},
    ]
    if badgermole.get("subtypes") != expected_subtypes:
        raise ValueError("Badgermole Combo subtype baseline changed")
    rules = badgermole.get("rules")
    if not isinstance(rules, list) or any(
        item.get("id") == "badgermole-combo-landfall" for item in rules
    ):
        raise ValueError("Badgermole Combo Landfall rule already exists")

    badgermole["subtypes"].append({"id": "landfall", "name": "Landfall"})
    rules.append(
        {
            "id": "badgermole-combo-landfall",
            "priority": 624600,
            "subtype_id": "landfall",
            "conditions": {
                "all": [
                    {"card": "Badgermole Cub", "zone": "main", "min_count": 3},
                    {
                        "card": "Green Sun's Zenith",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {"card": "Quirion Ranger", "zone": "main", "min_count": 2},
                    {
                        "card": "Springheart Nantuko",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {
                        "card": "Ashaya, Soul of the Wild",
                        "zone": "main",
                        "min_count": 1,
                    },
                    {"card": "Icetill Explorer", "zone": "main", "min_count": 3},
                    {
                        "card": "Leyline of Abundance",
                        "zone": "main",
                        "exact_count": 0,
                    },
                    {
                        "card": "Vizier of Remedies",
                        "zone": "main",
                        "exact_count": 0,
                    },
                ]
            },
        }
    )


def _add_coffers_dimir(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "coffers" for item in archetypes):
        raise ValueError("Coffers already exists in production")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "necrodominance"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one Necrodominance insertion anchor")
    archetypes.insert(
        anchors[0] + 1,
        {
            "id": "coffers",
            "name": "Coffers",
            "priority": 636400,
            "subtypes": [{"id": "dimir", "name": "Dimir"}],
            "rules": [
                {
                    "id": "coffers-dimir",
                    "priority": 636400,
                    "subtype_id": "dimir",
                    "conditions": {
                        "all": [
                            {
                                "card": "Cabal Coffers",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Watery Grave",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Consult the Star Charts",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Necrodominance",
                                "zone": "main",
                                "exact_count": 0,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_dark_maestro_and_umori(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    coffers_matches = [
        (index, item)
        for index, item in enumerate(archetypes)
        if item.get("id") == "coffers"
    ]
    if len(coffers_matches) != 1:
        raise ValueError("expected exactly one accepted Coffers parent")
    coffers_index, coffers = coffers_matches[0]
    if coffers.get("subtypes") != [{"id": "dimir", "name": "Dimir"}]:
        raise ValueError("Coffers subtype baseline changed before Umori")
    coffers["subtypes"].append({"id": "umori", "name": "Umori"})
    coffers["rules"].append(
        {
            "id": "coffers-umori",
            "priority": 636200,
            "subtype_id": "umori",
            "conditions": {
                "all": [
                    {"card": "Cabal Coffers", "zone": "main", "min_count": 3},
                    {"card": "Dark Petition", "zone": "main", "min_count": 3},
                    {"card": "Profane Tutor", "zone": "main", "min_count": 3},
                    {"card": "Sylvan Scrying", "zone": "main", "min_count": 3},
                    {
                        "card": "Bloodchief's Thirst",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {
                        "card": "Molten-Core Maestro",
                        "zone": "main",
                        "exact_count": 0,
                    },
                    {
                        "card": "Necrodominance",
                        "zone": "main",
                        "exact_count": 0,
                    },
                ]
            },
        }
    )

    if any(item.get("id") == "dark-maestro" for item in archetypes):
        raise ValueError("Dark Maestro already exists in production")
    archetypes.insert(
        coffers_index + 1,
        {
            "id": "dark-maestro",
            "name": "Dark Maestro",
            "priority": 636500,
            "rules": [
                {
                    "id": "dark-maestro-primary",
                    "priority": 636500,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Cabal Coffers",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Dark Petition",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Profane Tutor",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Molten-Core Maestro",
                                "zone": "main",
                                "min_count": 2,
                            },
                            {
                                "card": "Necrodominance",
                                "zone": "main",
                                "exact_count": 0,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_coffers_golgari(document: dict[str, Any]) -> None:
    archetypes = [
        item for item in document["archetypes"] if item.get("id") == "coffers"
    ]
    if len(archetypes) != 1:
        raise ValueError("expected exactly one accepted Coffers parent")
    coffers = archetypes[0]
    if coffers.get("subtypes") != [
        {"id": "dimir", "name": "Dimir"},
        {"id": "umori", "name": "Umori"},
    ]:
        raise ValueError("Coffers subtype baseline changed before Golgari")
    coffers["subtypes"].insert(1, {"id": "golgari", "name": "Golgari"})
    coffers["rules"].insert(
        1,
        {
            "id": "coffers-golgari",
            "priority": 636300,
            "subtype_id": "golgari",
            "conditions": {
                "all": [
                    {"card": "Cabal Coffers", "zone": "main", "min_count": 3},
                    {
                        "card": "Karn, the Great Creator",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {
                        "card": "Underground Mortuary",
                        "zone": "main",
                        "min_count": 2,
                    },
                    {
                        "card": "Necrodominance",
                        "zone": "main",
                        "exact_count": 0,
                    },
                ]
            },
        },
    )


def _add_eight_rack(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "eight-rack" for item in archetypes):
        raise ValueError("eight-rack already exists in the production baseline")
    anchors = [
        index for index, item in enumerate(archetypes) if item.get("id") == "coffers"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one Coffers insertion anchor")
    archetypes.insert(
        anchors[0] + 1,
        {
            "id": "eight-rack",
            "name": "8-Rack",
            "priority": 636600,
            "rules": [
                {
                    "id": "eight-rack-primary",
                    "priority": 636600,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {"card": "The Rack", "zone": "main", "min_count": 3},
                            {
                                "card": "Raven's Crime",
                                "zone": "main",
                                "min_count": 2,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_leyline_fling(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "leyline-fling" for item in archetypes):
        raise ValueError("leyline-fling already exists in the production baseline")
    anchors = [
        index for index, item in enumerate(archetypes) if item.get("id") == "prowess"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one Prowess insertion anchor")
    archetypes.insert(
        anchors[0] + 1,
        {
            "id": "leyline-fling",
            "name": "Leyline Fling",
            "priority": 673000,
            "rules": [
                {
                    "id": "leyline-fling-primary",
                    "priority": 673000,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Leyline of Resonance",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Heartfire Hero",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Callous Sell-Sword",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Monastery Swiftspear",
                                "zone": "main",
                                "min_count": 3,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_orzhov_blink_splash(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    matches = [item for item in archetypes if item.get("id") == "orzhov-blink"]
    if len(matches) != 1:
        raise ValueError("expected exactly one Orzhov Blink parent")
    orzhov_blink = matches[0]
    expected_primary = {
        "id": "orzhov-blink-primary",
        "priority": 632300,
        "subtype_id": None,
        "conditions": {
            "all": [
                {
                    "card": "Phelia, Exuberant Shepherd",
                    "zone": "main",
                    "min_count": 3,
                },
                {
                    "card": "Overlord of the Balemurk",
                    "zone": "main",
                    "min_count": 3,
                },
                {"card": "Ephemerate", "zone": "main", "min_count": 2},
                {
                    "card": "__classifier-semantic-main-blue-source__",
                    "zone": "main",
                    "exact_count": 0,
                },
                {
                    "card": "__classifier-semantic-main-red-source__",
                    "zone": "main",
                    "exact_count": 0,
                },
                {
                    "card": "__classifier-semantic-main-green-source__",
                    "zone": "main",
                    "exact_count": 0,
                },
                {
                    "card": "Goryo's Vengeance",
                    "zone": "main",
                    "exact_count": 0,
                },
            ]
        },
    }
    if orzhov_blink.get("rules") != [expected_primary]:
        raise ValueError("Orzhov Blink production rules changed from the reviewed base")
    orzhov_blink["rules"].append(
        {
            "id": "orzhov-blink-splash",
            "priority": 632250,
            "subtype_id": None,
            "conditions": {
                "all": [
                    {
                        "card": "Phelia, Exuberant Shepherd",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {
                        "card": "Overlord of the Balemurk",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {"card": "Ephemerate", "zone": "main", "min_count": 2},
                    {
                        "card": "Emperor of Bones",
                        "zone": "main",
                        "min_count": 2,
                    },
                    {"card": "Flickerwisp", "zone": "main", "min_count": 2},
                    {"card": "Solitude", "zone": "main", "min_count": 3},
                    {"card": "Thoughtseize", "zone": "main", "min_count": 3},
                    {
                        "card": "Psychic Frog",
                        "zone": "main",
                        "exact_count": 0,
                    },
                    {
                        "card": "Quantum Riddler",
                        "zone": "main",
                        "exact_count": 0,
                    },
                    {
                        "card": "Detective's Phoenix",
                        "zone": "main",
                        "exact_count": 0,
                    },
                    {
                        "card": "Phlage, Titan of Fire's Fury",
                        "zone": "main",
                        "exact_count": 0,
                    },
                    {
                        "card": "Goryo's Vengeance",
                        "zone": "main",
                        "exact_count": 0,
                    },
                ]
            },
        }
    )


def _repair_eldrazi_aggro_primary(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    matches = [item for item in archetypes if item.get("id") == "eldrazi-aggro"]
    if len(matches) != 1:
        raise ValueError("expected exactly one Eldrazi Aggro parent")
    eldrazi_aggro = matches[0]
    expected_primary = {
        "id": "eldrazi-aggro-primary",
        "priority": 640000,
        "subtype_id": None,
        "conditions": {
            "all": [
                {
                    "card": "Eldrazi Linebreaker",
                    "zone": "main",
                    "min_count": 3,
                },
                {
                    "card": "It That Heralds the End",
                    "zone": "main",
                    "min_count": 3,
                },
            ]
        },
    }
    if eldrazi_aggro.get("rules") != [expected_primary]:
        raise ValueError(
            "Eldrazi Aggro production rules changed from the reviewed base"
        )
    eldrazi_aggro["rules"][0]["conditions"]["all"] = [
        {
            "card": "Eldrazi Linebreaker",
            "zone": "main",
            "min_count": 3,
        },
        {
            "card": "Basking Broodscale",
            "zone": "main",
            "exact_count": 0,
        },
    ]


def _add_mono_green_stompy(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    expected = {
        "id": "mono-green-stompy",
        "name": "Mono-Green Stompy",
        "priority": 638500,
        "rules": [
            {
                "id": "mono-green-stompy-primary",
                "priority": 638500,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {
                            "card": "Aspect of Hydra",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {
                            "card": "Old-Growth Troll",
                            "zone": "main",
                            "min_count": 3,
                        },
                    ]
                },
            }
        ],
    }
    matches = [item for item in archetypes if item.get("id") == "mono-green-stompy"]
    if matches:
        if matches == [expected]:
            return
        raise ValueError("mono-green-stompy already exists with an unexpected shape")
    anchors = [
        index
        for index, item in enumerate(archetypes)
        if item.get("id") == "eldrazi-aggro"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one Eldrazi Aggro insertion anchor")
    archetypes.insert(anchors[0] + 1, expected)


def _repair_dredge_primary(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    matches = [item for item in archetypes if item.get("id") == "dredge"]
    if len(matches) != 1:
        raise ValueError("expected exactly one Dredge parent")
    dredge = matches[0]
    expected_primary = {
        "id": "dredge-primary",
        "priority": 207000,
        "subtype_id": None,
        "conditions": {
            "all": [
                {
                    "card": "Arclight Phoenix",
                    "zone": "main",
                    "min_count": 3,
                },
                {
                    "card": "Creeping Chill",
                    "zone": "main",
                    "min_count": 3,
                },
                {
                    "card": "Life from the Loam",
                    "zone": "main",
                    "min_count": 3,
                },
                {
                    "card": "Burning Inquiry",
                    "zone": "main",
                    "min_count": 3,
                },
            ]
        },
    }
    if dredge.get("rules") != [expected_primary]:
        raise ValueError("Dredge production rules changed from the reviewed base")
    dredge["rules"][0]["conditions"]["all"] = expected_primary["conditions"]["all"][:3]


def _repair_izzet_wizards_primary(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    matches = [item for item in archetypes if item.get("id") == "izzet-wizards"]
    if len(matches) != 1:
        raise ValueError("expected exactly one Izzet Wizards parent")
    izzet_wizards = matches[0]
    expected_primary = {
        "id": "izzet-wizards-primary",
        "priority": 622000,
        "subtype_id": None,
        "conditions": {
            "all": [
                {
                    "card": "Snapcaster Mage",
                    "zone": "main",
                    "min_count": 2,
                },
                {
                    "card": "Flame of Anor",
                    "zone": "main",
                    "min_count": 3,
                },
                {
                    "card": "Lightning Bolt",
                    "zone": "main",
                    "min_count": 2,
                },
            ]
        },
    }
    if izzet_wizards.get("rules") != [expected_primary]:
        raise ValueError(
            "Izzet Wizards production rules changed from the reviewed base"
        )
    izzet_wizards["rules"][0]["conditions"]["all"] = [
        *expected_primary["conditions"]["all"][:2],
        *(
            {"card": card, "zone": "any", "exact_count": 0}
            for card in IZZET_WIZARDS_REVIEWED_WHITE_SPELLS
        ),
    ]


def _repair_izzet_prowess_rule(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    matches = [item for item in archetypes if item.get("id") == "prowess"]
    if len(matches) != 1:
        raise ValueError("expected exactly one Prowess parent")
    rules = [
        item
        for item in matches[0].get("rules", [])
        if item.get("id") == "prowess-izzet"
    ]
    expected_rule = {
        "id": "prowess-izzet",
        "priority": 672200,
        "subtype_id": "izzet",
        "conditions": {
            "all": [
                {"card": "Cori-Steel Cutter", "zone": "main", "min_count": 3},
                {"card": "Lava Dart", "zone": "main", "min_count": 3},
                {
                    "card": "Dragon's Rage Channeler",
                    "zone": "main",
                    "min_count": 3,
                },
                {
                    "card": "Monastery Swiftspear",
                    "zone": "main",
                    "min_count": 3,
                },
                {"card": "Preordain", "zone": "main", "min_count": 2},
                {
                    "card": "__classifier-semantic-any-white-spell__",
                    "zone": "any",
                    "exact_count": 0,
                },
                {
                    "card": "__classifier-semantic-any-black-spell__",
                    "zone": "any",
                    "exact_count": 0,
                },
                {
                    "card": "__classifier-semantic-any-green-spell__",
                    "zone": "any",
                    "exact_count": 0,
                },
            ]
        },
    }
    if rules != [expected_rule]:
        raise ValueError("Izzet Prowess production rule changed from the reviewed base")
    rules[0]["conditions"]["all"] = [
        *expected_rule["conditions"]["all"][:2],
        {
            "card": "Monastery Swiftspear",
            "zone": "main",
            "min_count": 2,
        },
        *expected_rule["conditions"]["all"][4:],
    ]


def _repair_jeskai_blink_primary(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    matches = [item for item in archetypes if item.get("id") == "jeskai-blink"]
    if len(matches) != 1:
        raise ValueError("expected exactly one Jeskai Blink parent")
    jeskai_blink = matches[0]
    expected_primary = {
        "id": "jeskai-blink-primary",
        "priority": 632500,
        "subtype_id": None,
        "conditions": {
            "all": [
                {
                    "card": "Phelia, Exuberant Shepherd",
                    "zone": "main",
                    "min_count": 3,
                },
                {"card": "Quantum Riddler", "zone": "main", "min_count": 3},
                {"card": "Solitude", "zone": "main", "min_count": 3},
                {
                    "card": "Stoneforge Mystic",
                    "zone": "main",
                    "max_count": 2,
                },
                {
                    "card": "__classifier-semantic-main-red-source__",
                    "zone": "main",
                    "min_count": 1,
                },
                {
                    "card": "__classifier-semantic-main-black-source__",
                    "zone": "main",
                    "exact_count": 0,
                },
                {
                    "card": "__classifier-semantic-main-green-source__",
                    "zone": "main",
                    "exact_count": 0,
                },
                {
                    "card": "Goryo's Vengeance",
                    "zone": "main",
                    "exact_count": 0,
                },
            ]
        },
    }
    if jeskai_blink.get("rules") != [expected_primary]:
        raise ValueError("Jeskai Blink production rules changed from the reviewed base")
    jeskai_blink["rules"][0]["conditions"]["all"][0]["min_count"] = 2


def _repair_jeskai_energy_primary(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    matches = [item for item in archetypes if item.get("id") == "jeskai-energy"]
    if len(matches) != 1:
        raise ValueError("expected exactly one Jeskai Energy parent")
    jeskai_energy = matches[0]
    expected_primary = {
        "id": "jeskai-energy-primary",
        "priority": 686000,
        "subtype_id": None,
        "conditions": {
            "all": [
                {
                    "card": "Ajani, Nacatl Pariah",
                    "zone": "main",
                    "min_count": 3,
                },
                {"card": "Guide of Souls", "zone": "main", "min_count": 3},
                {"card": "Quantum Riddler", "zone": "main", "min_count": 3},
            ]
        },
    }
    if jeskai_energy.get("rules") != [expected_primary]:
        raise ValueError(
            "Jeskai Energy production rules changed from the reviewed base"
        )
    jeskai_energy["rules"][0]["conditions"]["all"] = [
        *expected_primary["conditions"]["all"][:2],
        {"card": "Ocelot Pride", "zone": "main", "min_count": 3},
        {"card": "Quantum Riddler", "zone": "main", "min_count": 1},
        {
            "card": "__classifier-semantic-main-red-source__",
            "zone": "main",
            "min_count": 1,
        },
    ]


def _add_golgari_yawgmoth_young_wolf_path(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    matches = [item for item in archetypes if item.get("id") == "golgari-yawgmoth"]
    if len(matches) != 1:
        raise ValueError("expected exactly one Golgari Yawgmoth parent")
    golgari_yawgmoth = matches[0]
    expected_primary = {
        "id": "golgari-yawgmoth-primary",
        "priority": 221000,
        "subtype_id": None,
        "conditions": {
            "all": [
                {
                    "card": "Yawgmoth, Thran Physician",
                    "zone": "main",
                    "min_count": 3,
                },
                {
                    "card": "Grist, the Hunger Tide",
                    "zone": "main",
                    "min_count": 1,
                },
            ]
        },
    }
    if golgari_yawgmoth.get("rules") != [expected_primary]:
        raise ValueError(
            "Golgari Yawgmoth production rules changed from the reviewed base"
        )
    golgari_yawgmoth["rules"].append(
        {
            "id": "golgari-yawgmoth-young-wolf",
            "priority": 220900,
            "subtype_id": None,
            "conditions": {
                "all": [
                    {
                        "card": "Yawgmoth, Thran Physician",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {
                        "card": "Young Wolf",
                        "zone": "main",
                        "min_count": 2,
                    },
                ]
            },
        }
    )


def _add_hardened_scales(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    if any(item.get("id") == "hardened-scales" for item in archetypes):
        raise ValueError("hardened-scales already exists in the production baseline")
    anchors = [
        index for index, item in enumerate(archetypes) if item.get("id") == "affinity"
    ]
    if len(anchors) != 1:
        raise ValueError("expected exactly one Affinity insertion anchor")
    archetypes.insert(
        anchors[0],
        {
            "id": "hardened-scales",
            "name": "Hardened Scales",
            "priority": 648500,
            "rules": [
                {
                    "id": "hardened-scales-primary",
                    "priority": 648500,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Hardened Scales",
                                "zone": "main",
                                "min_count": 3,
                            }
                        ]
                    },
                }
            ],
        },
    )


def _repair_hammer_time(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    matches = [item for item in archetypes if item.get("id") == "hammer-time"]
    if len(matches) != 1:
        raise ValueError("expected exactly one Hammer Time parent")
    hammer = matches[0]
    expected_primary = {
        "id": "hammer-time",
        "name": "Hammer Time",
        "priority": 626000,
        "subtypes": [
            {"id": "azorius", "name": "Azorius"},
            {"id": "mono-white", "name": "Mono-White"},
        ],
        "rules": [
            {
                "id": "hammer-time-azorius",
                "priority": 626000,
                "subtype_id": "azorius",
                "conditions": {
                    "all": [
                        {"card": "Colossus Hammer", "zone": "main", "min_count": 3},
                        {"card": "Puresteel Paladin", "zone": "main", "min_count": 3},
                        {"card": "Metallic Rebuke", "zone": "main", "min_count": 2},
                    ]
                },
            },
            {
                "id": "hammer-time-mono-white",
                "priority": 625900,
                "subtype_id": "mono-white",
                "conditions": {
                    "all": [
                        {"card": "Colossus Hammer", "zone": "main", "min_count": 3},
                        {"card": "Puresteel Paladin", "zone": "main", "min_count": 3},
                        {"card": "Stoneforge Mystic", "zone": "main", "min_count": 3},
                        {"card": "Hallowed Fountain", "zone": "main", "exact_count": 0},
                    ]
                },
            },
        ],
    }

    traditional_core = [
        {"card": "Colossus Hammer", "zone": "main", "min_count": 3},
        {"card": "Puresteel Paladin", "zone": "main", "min_count": 3},
    ]
    no_black_or_green = [
        {
            "card": "__classifier-semantic-main-black-source__",
            "zone": "main",
            "exact_count": 0,
        },
        {
            "card": "__classifier-semantic-main-green-source__",
            "zone": "main",
            "exact_count": 0,
        },
        {
            "card": "__classifier-semantic-any-black-spell__",
            "zone": "any",
            "exact_count": 0,
        },
        {
            "card": "__classifier-semantic-any-green-spell__",
            "zone": "any",
            "exact_count": 0,
        },
    ]
    candidate = {
        "id": "hammer-time",
        "name": "Hammer Time",
        "priority": 626030,
        "subtypes": [
            {"id": "azorius", "name": "Azorius"},
            {"id": "boros", "name": "Boros"},
            {"id": "jeskai", "name": "Jeskai"},
            {"id": "mono-white", "name": "Mono-White"},
        ],
        "rules": [
            {
                "id": "hammer-time-jeskai-kellan",
                "priority": 626030,
                "subtype_id": "jeskai",
                "conditions": {
                    "all": [
                        {"card": "Colossus Hammer", "zone": "main", "min_count": 3},
                        {
                            "card": "Kellan, the Fae-Blooded",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {
                            "card": "Super-Soldier Serum",
                            "zone": "main",
                            "min_count": 2,
                        },
                        {
                            "card": "Puresteel Paladin",
                            "zone": "main",
                            "max_count": 2,
                        },
                        {
                            "card": "__classifier-semantic-main-white-source__",
                            "zone": "main",
                            "min_count": 1,
                        },
                        {
                            "card": "__classifier-semantic-main-blue-source__",
                            "zone": "main",
                            "min_count": 1,
                        },
                        {
                            "card": "__classifier-semantic-main-red-source__",
                            "zone": "main",
                            "min_count": 1,
                        },
                        *deepcopy(no_black_or_green),
                    ]
                },
            },
            {
                "id": "hammer-time-jeskai-red-source",
                "priority": 626020,
                "subtype_id": "jeskai",
                "conditions": {
                    "all": [
                        *deepcopy(traditional_core),
                        {
                            "card": "__classifier-semantic-main-white-source__",
                            "zone": "main",
                            "min_count": 1,
                        },
                        {
                            "card": "__classifier-semantic-main-blue-source__",
                            "zone": "main",
                            "min_count": 1,
                        },
                        {
                            "card": "__classifier-semantic-main-red-source__",
                            "zone": "main",
                            "min_count": 1,
                        },
                        *deepcopy(no_black_or_green),
                    ]
                },
            },
            {
                "id": "hammer-time-jeskai-red-spell",
                "priority": 626010,
                "subtype_id": "jeskai",
                "conditions": {
                    "all": [
                        *deepcopy(traditional_core),
                        {
                            "card": "__classifier-semantic-main-white-source__",
                            "zone": "main",
                            "min_count": 1,
                        },
                        {
                            "card": "__classifier-semantic-main-blue-source__",
                            "zone": "main",
                            "min_count": 1,
                        },
                        {
                            "card": "__classifier-semantic-main-red-source__",
                            "zone": "main",
                            "exact_count": 0,
                        },
                        {
                            "card": "__classifier-semantic-any-red-spell__",
                            "zone": "any",
                            "min_count": 1,
                        },
                        *deepcopy(no_black_or_green),
                    ]
                },
            },
            {
                "id": "hammer-time-azorius",
                "priority": 626000,
                "subtype_id": "azorius",
                "conditions": {
                    "all": [
                        *deepcopy(traditional_core),
                        {
                            "card": "__classifier-semantic-main-white-source__",
                            "zone": "main",
                            "min_count": 1,
                        },
                        {
                            "card": "__classifier-semantic-main-blue-source__",
                            "zone": "main",
                            "min_count": 1,
                        },
                        {
                            "card": "__classifier-semantic-main-red-source__",
                            "zone": "main",
                            "exact_count": 0,
                        },
                        {
                            "card": "__classifier-semantic-any-red-spell__",
                            "zone": "any",
                            "exact_count": 0,
                        },
                        *deepcopy(no_black_or_green),
                    ]
                },
            },
            {
                "id": "hammer-time-boros",
                "priority": 625950,
                "subtype_id": "boros",
                "conditions": {
                    "all": [
                        *deepcopy(traditional_core),
                        {
                            "card": "__classifier-semantic-main-white-source__",
                            "zone": "main",
                            "min_count": 1,
                        },
                        {
                            "card": "__classifier-semantic-main-red-source__",
                            "zone": "main",
                            "min_count": 1,
                        },
                        {
                            "card": "__classifier-semantic-main-blue-source__",
                            "zone": "main",
                            "exact_count": 0,
                        },
                        {
                            "card": "__classifier-semantic-any-blue-spell__",
                            "zone": "any",
                            "exact_count": 0,
                        },
                        *deepcopy(no_black_or_green),
                    ]
                },
            },
            {
                "id": "hammer-time-mono-white",
                "priority": 625900,
                "subtype_id": "mono-white",
                "conditions": {
                    "all": [
                        *deepcopy(traditional_core),
                        {
                            "card": "__classifier-semantic-main-white-source__",
                            "zone": "main",
                            "min_count": 1,
                        },
                        {
                            "card": "__classifier-semantic-main-blue-source__",
                            "zone": "main",
                            "exact_count": 0,
                        },
                        {
                            "card": "__classifier-semantic-main-red-source__",
                            "zone": "main",
                            "exact_count": 0,
                        },
                        {
                            "card": "__classifier-semantic-any-blue-spell__",
                            "zone": "any",
                            "exact_count": 0,
                        },
                        {
                            "card": "__classifier-semantic-any-red-spell__",
                            "zone": "any",
                            "exact_count": 0,
                        },
                        *deepcopy(no_black_or_green),
                    ]
                },
            },
        ],
    }
    if hammer == candidate:
        return
    if hammer != expected_primary:
        raise ValueError("Hammer Time production rules changed from the reviewed base")
    hammer.clear()
    hammer.update(candidate)


def _insert_rule(
    document: dict[str, Any], archetype_id: str, rule: dict[str, Any]
) -> dict[str, Any]:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    matches = [item for item in archetypes if item.get("id") == archetype_id]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {archetype_id} parent")
    parent = matches[0]
    rules = parent.get("rules")
    if not isinstance(rules, list):
        raise ValueError(f"{archetype_id} has no rule list")
    if any(item.get("id") == rule["id"] for item in rules):
        raise ValueError(f"{rule['id']} already exists")
    rules.append(rule)
    rules.sort(key=lambda item: int(item["priority"]), reverse=True)
    return parent


def _add_grixis_deaths_shadow_frog_path(document: dict[str, Any]) -> None:
    _insert_rule(
        document,
        "deaths-shadow",
        {
            "id": "deaths-shadow-grixis-frog",
            "priority": 620025,
            "subtype_id": "grixis",
            "conditions": {
                "all": [
                    {"card": "Death's Shadow", "zone": "main", "min_count": 3},
                    {"card": "Thoughtseize", "zone": "main", "min_count": 3},
                    {"card": "Street Wraith", "zone": "main", "min_count": 3},
                    {"card": "Psychic Frog", "zone": "main", "min_count": 3},
                    {"card": "Blood Crypt", "zone": "main", "min_count": 1},
                    {"card": "Watery Grave", "zone": "main", "min_count": 1},
                    {"card": "Steam Vents", "zone": "main", "min_count": 1},
                    {"card": "Stubborn Denial", "zone": "main", "max_count": 1},
                    {"card": "Goryo's Vengeance", "zone": "main", "exact_count": 0},
                    {"card": "Persist", "zone": "main", "exact_count": 0},
                ]
            },
        },
    )


def _add_four_color_ritual_path(document: dict[str, Any]) -> None:
    parent = _insert_rule(
        document,
        "five-color-ritual",
        {
            "id": "five-color-ritual-omnath",
            "priority": 324100,
            "subtype_id": None,
            "conditions": {
                "all": [
                    {"card": "Birthing Ritual", "zone": "main", "min_count": 3},
                    {"card": "Shardless Agent", "zone": "main", "min_count": 3},
                    {
                        "card": "Omnath, Locus of Creation",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {
                        "card": "Elesh Norn, Mother of Machines",
                        "zone": "main",
                        "min_count": 1,
                    },
                    {"card": "Magmatic Hellkite", "zone": "main", "max_count": 2},
                ]
            },
        },
    )
    parent["priority"] = 324100


def _add_boros_ponza_wildfire_path(document: dict[str, Any]) -> None:
    _insert_rule(
        document,
        "boros-land-destruction",
        {
            "id": "boros-land-destruction-boom-wildfire",
            "priority": 660990,
            "subtype_id": None,
            "conditions": {
                "all": [
                    {"card": "Boom/Bust", "zone": "main", "min_count": 3},
                    {
                        "card": "Flagstones of Trokair",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {"card": "Cleansing Wildfire", "zone": "main", "min_count": 3},
                    {"card": "Price of Freedom", "zone": "main", "min_count": 3},
                ]
            },
        },
    )


def _add_boros_ponza_classic_path(document: dict[str, Any]) -> None:
    _insert_rule(
        document,
        "boros-land-destruction",
        {
            "id": "boros-land-destruction-boom-classic",
            "priority": 660980,
            "subtype_id": None,
            "conditions": {
                "all": [
                    {"card": "Boom/Bust", "zone": "main", "min_count": 3},
                    {
                        "card": "Flagstones of Trokair",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {"card": "Pillage", "zone": "main", "min_count": 3},
                    {"card": "Stone Rain", "zone": "main", "min_count": 3},
                ]
            },
        },
    )


def _add_grixis_persist_wizards_path(document: dict[str, Any]) -> None:
    _insert_rule(
        document,
        "grixis-persist",
        {
            "id": "grixis-persist-wizards",
            "priority": 639890,
            "subtype_id": None,
            "conditions": {
                "all": [
                    {"card": "Persist", "zone": "main", "min_count": 3},
                    {"card": "Thundertrap Trainer", "zone": "main", "min_count": 3},
                    {"card": "Traumatic Critique", "zone": "main", "min_count": 3},
                    {
                        "card": "Tamiyo, Inquisitive Student",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {"card": "Watery Grave", "zone": "main", "min_count": 1},
                    {"card": "Steam Vents", "zone": "main", "min_count": 1},
                    {"card": "Goryo's Vengeance", "zone": "main", "exact_count": 0},
                ]
            },
        },
    )


def _grixis_tempo_exclusions() -> list[dict[str, Any]]:
    return [
        {"card": "Goryo's Vengeance", "zone": "main", "exact_count": 0},
        {"card": "Persist", "zone": "main", "exact_count": 0},
        {"card": "Death's Shadow", "zone": "main", "exact_count": 0},
        {
            "card": "__classifier-semantic-main-white-source__",
            "zone": "main",
            "exact_count": 0,
        },
        {
            "card": "__classifier-semantic-main-green-source__",
            "zone": "main",
            "exact_count": 0,
        },
    ]


def _add_grixis_tempo_bowmasters_path(document: dict[str, Any]) -> None:
    _insert_rule(
        document,
        "grixis-tempo",
        {
            "id": "grixis-tempo-bowmasters",
            "priority": 638070,
            "subtype_id": None,
            "conditions": {
                "all": [
                    {
                        "card": "Dragon's Rage Channeler",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {"card": "Expressive Iteration", "zone": "main", "min_count": 3},
                    {"card": "Orcish Bowmasters", "zone": "main", "min_count": 2},
                    {"card": "Thoughtseize", "zone": "main", "min_count": 3},
                    {"card": "Psychic Frog", "zone": "main", "max_count": 2},
                    {"card": "Watery Grave", "zone": "main", "min_count": 1},
                    {"card": "Steam Vents", "zone": "main", "min_count": 1},
                    *_grixis_tempo_exclusions(),
                ]
            },
        },
    )


def _add_grixis_tempo_counterspell_path(document: dict[str, Any]) -> None:
    _insert_rule(
        document,
        "grixis-tempo",
        {
            "id": "grixis-tempo-counterspell",
            "priority": 638090,
            "subtype_id": None,
            "conditions": {
                "all": [
                    {"card": "Psychic Frog", "zone": "main", "min_count": 3},
                    {
                        "card": "Ragavan, Nimble Pilferer",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {"card": "Counterspell", "zone": "main", "min_count": 3},
                    {"card": "Fatal Push", "zone": "main", "max_count": 2},
                    {"card": "Watery Grave", "zone": "main", "min_count": 1},
                    {"card": "Steam Vents", "zone": "main", "min_count": 1},
                    *_grixis_tempo_exclusions(),
                ]
            },
        },
    )


def _add_grixis_tempo_drc_frog_path(document: dict[str, Any]) -> None:
    _insert_rule(
        document,
        "grixis-tempo",
        {
            "id": "grixis-tempo-drc-frog",
            "priority": 638080,
            "subtype_id": None,
            "conditions": {
                "all": [
                    {"card": "Psychic Frog", "zone": "main", "min_count": 3},
                    {
                        "card": "Dragon's Rage Channeler",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {"card": "Fatal Push", "zone": "main", "min_count": 3},
                    {
                        "card": "Ragavan, Nimble Pilferer",
                        "zone": "main",
                        "max_count": 2,
                    },
                    {"card": "Watery Grave", "zone": "main", "min_count": 1},
                    {"card": "Steam Vents", "zone": "main", "min_count": 1},
                    *_grixis_tempo_exclusions(),
                ]
            },
        },
    )


def _add_rakdos_prowess_path(document: dict[str, Any]) -> None:
    parent = _insert_rule(
        document,
        "prowess",
        {
            "id": "prowess-rakdos",
            "priority": 672750,
            "subtype_id": "rakdos",
            "conditions": {
                "all": [
                    {"card": "Cori-Steel Cutter", "zone": "main", "min_count": 3},
                    {"card": "Lava Dart", "zone": "main", "min_count": 3},
                    {
                        "card": "Dragon's Rage Channeler",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {
                        "card": "Monastery Swiftspear",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {"card": "Blood Crypt", "zone": "main", "min_count": 1},
                    {
                        "card": "__classifier-semantic-any-black-spell__",
                        "zone": "any",
                        "min_count": 1,
                    },
                    {
                        "card": "__classifier-semantic-any-white-spell__",
                        "zone": "any",
                        "exact_count": 0,
                    },
                    {
                        "card": "__classifier-semantic-any-blue-spell__",
                        "zone": "any",
                        "exact_count": 0,
                    },
                    {
                        "card": "__classifier-semantic-any-green-spell__",
                        "zone": "any",
                        "exact_count": 0,
                    },
                    {"card": "Nethergoyf", "zone": "main", "exact_count": 0},
                ]
            },
        },
    )
    subtypes = parent.get("subtypes")
    if not isinstance(subtypes, list) or any(
        item.get("id") == "rakdos" for item in subtypes
    ):
        raise ValueError("Prowess Rakdos subtype is missing or already exists")
    subtypes.append({"id": "rakdos", "name": "Rakdos"})


OWNER_BULK_BATCH2_PARENTS: dict[str, dict[str, Any]] = {
    IZZET_EXTRA_TURNS_FAMILY: {
        "id": "izzet-extra-turns",
        "name": "Izzet Extra Turns",
        "priority": 622150,
        "rules": [
            {
                "id": "izzet-extra-turns-primary",
                "priority": 622150,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {
                            "card": "Tablet of Discovery",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {"card": "Time Warp", "zone": "main", "min_count": 3},
                        {
                            "card": "Temporal Mastery",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {
                            "card": "__classifier-semantic-main-blue-source__",
                            "zone": "main",
                            "min_count": 1,
                        },
                        {
                            "card": "__classifier-semantic-main-red-source__",
                            "zone": "main",
                            "min_count": 1,
                        },
                        *(
                            {
                                "card": f"__classifier-semantic-main-{color}-source__",
                                "zone": "main",
                                "exact_count": 0,
                            }
                            for color in ("white", "black", "green")
                        ),
                        *(
                            {
                                "card": f"__classifier-semantic-any-{color}-spell__",
                                "zone": "any",
                                "exact_count": 0,
                            }
                            for color in ("white", "black", "green")
                        ),
                    ]
                },
            }
        ],
    },
    JUND_GOBLINS_FAMILY: {
        "id": "jund-goblins",
        "name": "Jund Goblins",
        "priority": 625500,
        "rules": [
            {
                "id": "jund-goblins-primary",
                "priority": 625500,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {
                            "card": "Birthing Ritual",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {
                            "card": "Ignoble Hierarch",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {
                            "card": "Conspicuous Snoop",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {"card": "Blood Crypt", "zone": "main", "min_count": 1},
                        {
                            "card": "Stomping Ground",
                            "zone": "main",
                            "min_count": 1,
                        },
                    ]
                },
            }
        ],
    },
    THOPTER_SWORD_BANT_FAMILY: {
        "id": "thopter-sword",
        "name": "Thopter Sword",
        "priority": 648800,
        "subtypes": [{"id": "bant", "name": "Bant"}],
        "rules": [
            {
                "id": "thopter-sword-bant",
                "priority": 648800,
                "subtype_id": "bant",
                "conditions": {
                    "all": [
                        {
                            "card": "Thopter Foundry",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {
                            "card": "Sword of the Meek",
                            "zone": "main",
                            "min_count": 2,
                        },
                        {
                            "card": "Malevolent Rumble",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {
                            "card": "Breeding Pool",
                            "zone": "main",
                            "min_count": 1,
                        },
                        {
                            "card": "Hallowed Fountain",
                            "zone": "main",
                            "min_count": 1,
                        },
                    ]
                },
            }
        ],
    },
    RAKDOS_AGGRO_FAMILY: {
        "id": "rakdos-aggro",
        "name": "Rakdos Aggro",
        "priority": 620050,
        "rules": [
            {
                "id": "rakdos-aggro-primary",
                "priority": 620050,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {
                            "card": "Super Shredder",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {"card": "Moonshadow", "zone": "main", "min_count": 3},
                        {
                            "card": "Ragavan, Nimble Pilferer",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {"card": "Blood Crypt", "zone": "main", "min_count": 1},
                    ]
                },
            }
        ],
    },
    PRIMAL_PRAYERS_RECRUITER_FAMILY: {
        "id": "primal-prayers-combo",
        "name": "Primal Prayers Combo",
        "priority": 688500,
        "rules": [
            {
                "id": "primal-prayers-combo-primary",
                "priority": 688500,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {
                            "card": "Primal Prayers",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {
                            "card": "Guide of Souls",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {"card": "Ocelot Pride", "zone": "main", "min_count": 3},
                    ]
                },
            }
        ],
    },
    PRIMAL_PRAYERS_ZENITH_FAMILY: {
        "id": "primal-prayers-combo",
        "name": "Primal Prayers Combo",
        "priority": 688500,
        "rules": [
            {
                "id": "primal-prayers-combo-primary",
                "priority": 688500,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {
                            "card": "Primal Prayers",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {
                            "card": "Guide of Souls",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {"card": "Ocelot Pride", "zone": "main", "min_count": 3},
                    ]
                },
            }
        ],
    },
    NAYA_MIDRANGE_FAMILY: {
        "id": "naya-midrange",
        "name": "Naya Midrange",
        "priority": 623850,
        "rules": [
            {
                "id": "naya-midrange-primary",
                "priority": 623850,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {
                            "card": "Ragavan, Nimble Pilferer",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {
                            "card": "Phlage, Titan of Fire's Fury",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {"card": "Wrenn and Six", "zone": "main", "min_count": 2},
                        *(
                            {
                                "card": f"__classifier-semantic-main-{color}-source__",
                                "zone": "main",
                                "min_count": 1,
                            }
                            for color in ("white", "red", "green")
                        ),
                    ]
                },
            }
        ],
    },
    FIVE_COLOR_ELEMENTALS_FAMILY: {
        "id": "five-color-elementals",
        "name": "Five-Color Elementals",
        "priority": 324200,
        "rules": [
            {
                "id": "five-color-elementals-primary",
                "priority": 324200,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {
                            "card": "Birthing Ritual",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {
                            "card": "Omnath, Locus of Creation",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {"card": "Risen Reef", "zone": "main", "min_count": 3},
                        {
                            "card": "Shardless Agent",
                            "zone": "main",
                            "exact_count": 0,
                        },
                    ]
                },
            }
        ],
    },
    CHEERIOS_FAMILY: {
        "id": "cheerios",
        "name": "Cheerios",
        "priority": 683400,
        "rules": [
            {
                "id": "cheerios-primary",
                "priority": 683400,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {
                            "card": "Sram, Senior Edificer",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {"card": "Bone Saw", "zone": "main", "min_count": 3},
                        {"card": "Kite Shield", "zone": "main", "min_count": 3},
                    ]
                },
            }
        ],
    },
    SHAPE_ANEW_FAMILY: {
        "id": "shape-anew",
        "name": "Shape Anew",
        "priority": 667500,
        "rules": [
            {
                "id": "shape-anew-primary",
                "priority": 667500,
                "subtype_id": None,
                "conditions": {
                    "all": [{"card": "Shape Anew", "zone": "main", "min_count": 3}]
                },
            }
        ],
    },
    GLIMPSE_OF_TOMORROW_FAMILY: {
        "id": "glimpse-of-tomorrow",
        "name": "Glimpse of Tomorrow",
        "priority": 624500,
        "rules": [
            {
                "id": "glimpse-of-tomorrow-primary",
                "priority": 624500,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {
                            "card": "Glimpse of Tomorrow",
                            "zone": "main",
                            "min_count": 3,
                        }
                    ]
                },
            }
        ],
    },
    IZZET_CAULDRON_FAMILY: {
        "id": "izzet-cauldron",
        "name": "Izzet Cauldron",
        "priority": 622050,
        "rules": [
            {
                "id": "izzet-cauldron-primary",
                "priority": 622050,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {"card": "Vivi Ornitier", "zone": "main", "min_count": 3},
                        {
                            "card": "Agatha's Soul Cauldron",
                            "zone": "main",
                            "min_count": 3,
                        },
                    ]
                },
            }
        ],
    },
}


OWNER_BULK_BATCH3_PARENTS: dict[str, dict[str, Any]] = {
    DOMAIN_PERSIST_FAMILY: {
        "id": "domain-persist",
        "name": "Domain Persist",
        "priority": 640100,
        "rules": [
            {
                "id": "domain-persist-primary",
                "priority": 640100,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {"card": "Persist", "zone": "main", "min_count": 3},
                        {"card": "Archon of Cruelty", "zone": "main", "min_count": 3},
                        {
                            "card": "Leyline of the Guildpact",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {"card": "Scion of Draco", "zone": "main", "min_count": 3},
                    ]
                },
            }
        ],
    },
    DIMIR_PERSIST_FAMILY: {
        "id": "dimir-persist",
        "name": "Dimir Persist",
        "priority": 639550,
        "rules": [
            {
                "id": "dimir-persist-primary",
                "priority": 639550,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {"card": "Persist", "zone": "main", "min_count": 3},
                        {"card": "Archon of Cruelty", "zone": "main", "min_count": 3},
                        {"card": "Psychic Frog", "zone": "main", "min_count": 3},
                        {"card": "Watery Grave", "zone": "main", "min_count": 1},
                        *(
                            {
                                "card": f"__classifier-semantic-main-{color}-source__",
                                "zone": "main",
                                "exact_count": 0,
                            }
                            for color in ("white", "red", "green")
                        ),
                        *(
                            {
                                "card": f"__classifier-semantic-any-{color}-spell__",
                                "zone": "any",
                                "exact_count": 0,
                            }
                            for color in ("white", "red", "green")
                        ),
                    ]
                },
            }
        ],
    },
    AZORIUS_MIRACLES_FAMILY: {
        "id": "azorius-miracles",
        "name": "Azorius Miracles",
        "priority": 642900,
        "rules": [
            {
                "id": "azorius-miracles-primary",
                "priority": 642900,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {"card": "Brainsurge", "zone": "main", "min_count": 3},
                        {"card": "Terminus", "zone": "main", "min_count": 3},
                        {"card": "Hallowed Fountain", "zone": "main", "min_count": 1},
                    ]
                },
            }
        ],
    },
    SULTAI_FLICKER_FAMILY: {
        "id": "sultai-flicker",
        "name": "Sultai Flicker",
        "priority": 633500,
        "rules": [
            {
                "id": "sultai-flicker-primary",
                "priority": 633500,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {"card": "Ghostly Flicker", "zone": "main", "min_count": 3},
                        {"card": "Drowner of Truth", "zone": "main", "min_count": 3},
                        {"card": "Psychic Frog", "zone": "main", "min_count": 3},
                        {"card": "Breeding Pool", "zone": "main", "min_count": 1},
                        {"card": "Watery Grave", "zone": "main", "min_count": 1},
                        *(
                            {
                                "card": f"__classifier-semantic-main-{color}-source__",
                                "zone": "main",
                                "exact_count": 0,
                            }
                            for color in ("white", "red")
                        ),
                        *(
                            {
                                "card": f"__classifier-semantic-any-{color}-spell__",
                                "zone": "any",
                                "exact_count": 0,
                            }
                            for color in ("white", "red")
                        ),
                    ]
                },
            }
        ],
    },
    DOMAIN_BLINK_FAMILY: {
        "id": "domain-blink",
        "name": "Domain Blink",
        "priority": 632450,
        "rules": [
            {
                "id": "domain-blink-primary",
                "priority": 632450,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {
                            "card": "Phelia, Exuberant Shepherd",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {"card": "Leyline Binding", "zone": "main", "min_count": 3},
                        {
                            "card": "Overlord of the Balemurk",
                            "zone": "main",
                            "min_count": 3,
                        },
                    ]
                },
            }
        ],
    },
    RAKDOS_DELIRIUM_PHOENIX_FAMILY: {
        "id": "rakdos-delirium",
        "name": "Rakdos Delirium",
        "priority": 620070,
        "rules": [
            {
                "id": "rakdos-delirium-primary",
                "priority": 620070,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {"card": "Nethergoyf", "zone": "main", "min_count": 3},
                        {
                            "card": "Dragon's Rage Channeler",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {"card": "Fear of Missing Out", "zone": "main", "min_count": 3},
                        {"card": "Moonshadow", "zone": "main", "min_count": 3},
                        {"card": "Detective's Phoenix", "zone": "main", "min_count": 2},
                        {"card": "Mishra's Bauble", "zone": "main", "min_count": 3},
                        {"card": "Blood Crypt", "zone": "main", "min_count": 1},
                        {"card": "Hollow One", "zone": "main", "exact_count": 0},
                        {"card": "Cori-Steel Cutter", "zone": "main", "exact_count": 0},
                        {"card": "Death's Shadow", "zone": "main", "exact_count": 0},
                    ]
                },
            }
        ],
    },
    FIVE_COLOR_HUMANS_FAMILY: {
        "id": "five-color-humans",
        "name": "Five-Color Humans",
        "priority": 683450,
        "rules": [
            {
                "id": "five-color-humans-primary",
                "priority": 683450,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {"card": "Aether Vial", "zone": "main", "min_count": 3},
                        {
                            "card": "Champion of the Parish",
                            "zone": "main",
                            "min_count": 3,
                        },
                        {"card": "Thalia's Lieutenant", "zone": "main", "min_count": 3},
                        {"card": "Cavern of Souls", "zone": "main", "min_count": 3},
                        {"card": "Secluded Courtyard", "zone": "main", "min_count": 3},
                        {"card": "Meddling Mage", "zone": "main", "min_count": 3},
                    ]
                },
            }
        ],
    },
}
OWNER_BULK_BATCH3_PARENTS[RAKDOS_DELIRIUM_CASEY_FAMILY] = OWNER_BULK_BATCH3_PARENTS[
    RAKDOS_DELIRIUM_PHOENIX_FAMILY
]


OWNER_BULK_BATCH4_PARENTS: dict[str, dict[str, Any]] = {
    DIMIR_UNEARTH_WHITE_SPLASH_FAMILY: {
        "id": "dimir-unearth",
        "name": "Dimir Unearth",
        "priority": 659500,
        "rules": [
            {
                "id": "dimir-unearth-primary",
                "priority": 659500,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {"card": "Abhorrent Oculus", "zone": "main", "min_count": 3},
                        {"card": "Unearth", "zone": "main", "min_count": 3},
                        {"card": "Thought Scour", "zone": "main", "min_count": 3},
                        {"card": "Psychic Frog", "zone": "main", "min_count": 3},
                        {"card": "Watery Grave", "zone": "main", "min_count": 1},
                        {"card": "Birthing Ritual", "zone": "main", "exact_count": 0},
                        {"card": "Goryo's Vengeance", "zone": "main", "exact_count": 0},
                        {"card": "Persist", "zone": "main", "exact_count": 0},
                    ]
                },
            }
        ],
    },
    DIMIR_GORYOS_FAMILY: {
        "id": "dimir-goryos",
        "name": "Dimir Goryo's",
        "priority": 641175,
        "rules": [
            {
                "id": "dimir-goryos-primary",
                "priority": 641175,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {"card": "Goryo's Vengeance", "zone": "main", "min_count": 3},
                        {"card": "Atraxa, Grand Unifier", "zone": "main", "min_count": 3},
                        {"card": "Psychic Frog", "zone": "main", "min_count": 3},
                        {"card": "Watery Grave", "zone": "main", "min_count": 1},
                        *(
                            {
                                "card": f"__classifier-semantic-main-{color}-source__",
                                "zone": "main",
                                "exact_count": 0,
                            }
                            for color in ("white", "red", "green")
                        ),
                    ]
                },
            }
        ],
    },
    IZZET_TEMPO_FAMILY: {
        "id": "izzet-tempo",
        "name": "Izzet Tempo",
        "priority": 638075,
        "rules": [
            {
                "id": "izzet-tempo-primary",
                "priority": 638075,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {"card": "Ragavan, Nimble Pilferer", "zone": "main", "min_count": 3},
                        {"card": "Counterspell", "zone": "main", "min_count": 3},
                        {"card": "Tamiyo, Inquisitive Student", "zone": "main", "min_count": 3},
                        {"card": "Steam Vents", "zone": "main", "min_count": 1},
                        {"card": "Psychic Frog", "zone": "main", "exact_count": 0},
                        *(
                            {
                                "card": f"__classifier-semantic-main-{color}-source__",
                                "zone": "main",
                                "exact_count": 0,
                            }
                            for color in ("white", "black", "green")
                        ),
                        *(
                            {
                                "card": f"__classifier-semantic-any-{color}-spell__",
                                "zone": "any",
                                "exact_count": 0,
                            }
                            for color in ("white", "black", "green")
                        ),
                    ]
                },
            }
        ],
    },
    RAKDOS_MIDRANGE_FAMILY: {
        "id": "rakdos-midrange",
        "name": "Rakdos Midrange",
        "priority": 620060,
        "rules": [
            {
                "id": "rakdos-midrange-primary",
                "priority": 620060,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {"card": "Ragavan, Nimble Pilferer", "zone": "main", "min_count": 3},
                        {"card": "Dauthi Voidwalker", "zone": "main", "min_count": 3},
                        {"card": "Orcish Bowmasters", "zone": "main", "min_count": 3},
                        {"card": "Seasoned Pyromancer", "zone": "main", "min_count": 3},
                        {"card": "Thoughtseize", "zone": "main", "min_count": 3},
                        {"card": "Blood Crypt", "zone": "main", "min_count": 1},
                    ]
                },
            }
        ],
    },
    YAWGMOTH_ENERGY_FAMILY: {
        "id": "yawgmoth-energy",
        "name": "Yawgmoth Energy",
        "priority": 687050,
        "rules": [
            {
                "id": "yawgmoth-energy-primary",
                "priority": 687050,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {"card": "Yawgmoth, Thran Physician", "zone": "main", "min_count": 2},
                        {"card": "Guide of Souls", "zone": "main", "min_count": 3},
                        {"card": "Ocelot Pride", "zone": "main", "min_count": 3},
                        {"card": "Young Wolf", "zone": "main", "min_count": 3},
                        {"card": "Birthing Ritual", "zone": "main", "min_count": 3},
                    ]
                },
            }
        ],
    },
    SULTAI_TEMPO_FAMILY: {
        "id": "sultai-tempo",
        "name": "Sultai Tempo",
        "priority": 638025,
        "rules": [
            {
                "id": "sultai-tempo-primary",
                "priority": 638025,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {"card": "Ice-Fang Coatl", "zone": "main", "min_count": 3},
                        {"card": "Counterspell", "zone": "main", "min_count": 3},
                        {"card": "Fatal Push", "zone": "main", "min_count": 3},
                        {"card": "Breeding Pool", "zone": "main", "min_count": 1},
                        {"card": "Watery Grave", "zone": "main", "min_count": 1},
                        {"card": "Abhorrent Oculus", "zone": "main", "exact_count": 0},
                        {"card": "Birthing Ritual", "zone": "main", "exact_count": 0},
                        *(
                            {
                                "card": f"__classifier-semantic-main-{color}-source__",
                                "zone": "main",
                                "exact_count": 0,
                            }
                            for color in ("white", "red")
                        ),
                        *(
                            {
                                "card": f"__classifier-semantic-any-{color}-spell__",
                                "zone": "any",
                                "exact_count": 0,
                            }
                            for color in ("white", "red")
                        ),
                    ]
                },
            }
        ],
    },
    SOLEMNITY_BLINK_FAMILY: {
        "id": "solemnity-blink",
        "name": "Solemnity Blink",
        "priority": 673650,
        "rules": [
            {
                "id": "solemnity-blink-primary",
                "priority": 673650,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {"card": "Solemnity", "zone": "main", "min_count": 3},
                        {"card": "Overlord of the Balemurk", "zone": "main", "min_count": 3},
                        {"card": "Phelia, Exuberant Shepherd", "zone": "main", "min_count": 2},
                        {"card": "Solitude", "zone": "main", "min_count": 3},
                        {"card": "Nine Lives", "zone": "main", "exact_count": 0},
                        {"card": "Phyrexian Unlife", "zone": "main", "exact_count": 0},
                    ]
                },
            }
        ],
    },
    MONO_BLACK_SAGA_FAMILY: {
        "id": "mono-black-saga",
        "name": "Mono-Black Saga",
        "priority": 100000,
        "rules": [
            {
                "id": "mono-black-saga-primary",
                "priority": 100000,
                "subtype_id": None,
                "conditions": {
                    "all": [
                        {"card": "Urza's Saga", "zone": "main", "min_count": 3},
                        {"card": "Nethergoyf", "zone": "main", "min_count": 3},
                        {"card": "Mishra's Bauble", "zone": "main", "min_count": 3},
                        {"card": "Thoughtseize", "zone": "main", "min_count": 3},
                        {"card": "Swamp", "zone": "main", "min_count": 4},
                        *(
                            {"card": card, "zone": "main", "exact_count": 0}
                            for card in (
                                "Death's Shadow",
                                "Dragon's Rage Channeler",
                                "Fear of Missing Out",
                                "Moonshadow",
                                "Cori-Steel Cutter",
                                "Necrodominance",
                            )
                        ),
                        *(
                            {
                                "card": f"__classifier-semantic-any-{color}-spell__",
                                "zone": "any",
                                "exact_count": 0,
                            }
                            for color in ("white", "blue", "red", "green")
                        ),
                    ]
                },
            }
        ],
    },
}
OWNER_BULK_BATCH4_PARENTS[DIMIR_UNEARTH_DIMIR_FAMILY] = OWNER_BULK_BATCH4_PARENTS[
    DIMIR_UNEARTH_WHITE_SPLASH_FAMILY
]


def _add_owner_bulk_batch2_parent(document: dict[str, Any], *, family_id: str) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    candidate = deepcopy(OWNER_BULK_BATCH2_PARENTS[family_id])
    existing = [item for item in archetypes if item.get("id") == candidate["id"]]
    if existing:
        if existing == [candidate]:
            return
        raise ValueError(f"{candidate['id']} already exists with another definition")
    priority = int(candidate["priority"])
    insertion = next(
        (
            index
            for index, item in enumerate(archetypes)
            if int(item["priority"]) < priority
        ),
        len(archetypes),
    )
    archetypes.insert(insertion, candidate)


def _add_owner_bulk_batch3_parent(document: dict[str, Any], *, family_id: str) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    candidate = deepcopy(OWNER_BULK_BATCH3_PARENTS[family_id])
    existing = [item for item in archetypes if item.get("id") == candidate["id"]]
    if existing:
        if existing == [candidate]:
            return
        raise ValueError(f"{candidate['id']} already exists with another definition")
    priority = int(candidate["priority"])
    insertion = next(
        (
            index
            for index, item in enumerate(archetypes)
            if int(item["priority"]) < priority
        ),
        len(archetypes),
    )
    archetypes.insert(insertion, candidate)


def _add_owner_bulk_batch4_parent(document: dict[str, Any], *, family_id: str) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Modern production rules have no archetype list")
    candidate = deepcopy(OWNER_BULK_BATCH4_PARENTS[family_id])
    existing = [item for item in archetypes if item.get("id") == candidate["id"]]
    if existing:
        if existing == [candidate]:
            return
        raise ValueError(f"{candidate['id']} already exists with another definition")
    priority = int(candidate["priority"])
    insertion = next(
        (
            index
            for index, item in enumerate(archetypes)
            if int(item["priority"]) < priority
        ),
        len(archetypes),
    )
    archetypes.insert(insertion, candidate)


PROPOSAL_HANDLERS: dict[str, Callable[[dict[str, Any]], None]] = {
    AGADEEM_PERSIST_REDUCED_CRYPT_FAMILY: (_add_agadeem_persist_reduced_crypt_path),
    AMULET_SCAPESHIFT_FAMILY: _add_amulet_scapeshift_path,
    ASMO_PERSIST_FAMILY: _add_asmo_persist,
    AZORIUS_MIRACLES_FAMILY: partial(
        _add_owner_bulk_batch3_parent, family_id=AZORIUS_MIRACLES_FAMILY
    ),
    BADGERMOLE_FAMILY: _add_badgermole_and_devoted_subtypes,
    BADGERMOLE_LANDFALL_FAMILY: _add_badgermole_landfall_subtype,
    BOGLES_FAMILY: _add_bogles,
    CHEERIOS_FAMILY: partial(_add_owner_bulk_batch2_parent, family_id=CHEERIOS_FAMILY),
    COFFERS_DIMIR_FAMILY: _add_coffers_dimir,
    COFFERS_GOLGARI_FAMILY: _add_coffers_golgari,
    COSMOGOYF_NECRO_FAMILY: _add_cosmogoyf_necrodominance_subtype,
    DARK_MAESTRO_UMORI_FAMILY: _add_dark_maestro_and_umori,
    DIMIR_PERSIST_FAMILY: partial(
        _add_owner_bulk_batch3_parent, family_id=DIMIR_PERSIST_FAMILY
    ),
    DIMIR_UNEARTH_DIMIR_FAMILY: partial(
        _add_owner_bulk_batch4_parent, family_id=DIMIR_UNEARTH_DIMIR_FAMILY
    ),
    DIMIR_UNEARTH_WHITE_SPLASH_FAMILY: partial(
        _add_owner_bulk_batch4_parent, family_id=DIMIR_UNEARTH_WHITE_SPLASH_FAMILY
    ),
    DIMIR_GORYOS_FAMILY: partial(
        _add_owner_bulk_batch4_parent, family_id=DIMIR_GORYOS_FAMILY
    ),
    DOMAIN_BLINK_FAMILY: partial(
        _add_owner_bulk_batch3_parent, family_id=DOMAIN_BLINK_FAMILY
    ),
    DOMAIN_PERSIST_FAMILY: partial(
        _add_owner_bulk_batch3_parent, family_id=DOMAIN_PERSIST_FAMILY
    ),
    DREDGE_FAMILY: _repair_dredge_primary,
    EIGHT_RACK_FAMILY: _add_eight_rack,
    ELDRAZI_AGGRO_FAMILY: _repair_eldrazi_aggro_primary,
    ELDRAZI_OUROBOROID_FAMILY: _add_eldrazi_ouroboroid,
    ESPER_VALUE_FAMILY: _add_esper_value_paths,
    FIVE_COLOR_ELEMENTALS_FAMILY: partial(
        _add_owner_bulk_batch2_parent, family_id=FIVE_COLOR_ELEMENTALS_FAMILY
    ),
    FIVE_COLOR_HUMANS_FAMILY: partial(
        _add_owner_bulk_batch3_parent, family_id=FIVE_COLOR_HUMANS_FAMILY
    ),
    GLIMPSE_OF_TOMORROW_FAMILY: partial(
        _add_owner_bulk_batch2_parent, family_id=GLIMPSE_OF_TOMORROW_FAMILY
    ),
    GRUUL_BROODSCALE_FAMILY: _relax_gruul_broodscale_blade,
    GRUUL_CRAGGANWICK_FAMILY: _add_gruul_cragganwick,
    HAMMER_KELLAN_FAMILY: _repair_hammer_time,
    HAMMER_TRADITIONAL_FAMILY: _repair_hammer_time,
    GRUUL_MIDRANGE_FAMILY: _add_gruul_midrange,
    GRUUL_VALAKUT_FAMILY: _add_gruul_valakut,
    GRIXIS_DRESS_DOWN_FAMILY: _add_grixis_dress_down,
    GRIXIS_GORYOS_EMPEROR_FAMILY: _add_grixis_goryos_emperor_path,
    GRIXIS_DEATHS_SHADOW_FAMILY: _add_grixis_deaths_shadow_frog_path,
    FOUR_COLOR_RITUAL_FAMILY: _add_four_color_ritual_path,
    BOROS_PONZA_WILDFIRE_FAMILY: _add_boros_ponza_wildfire_path,
    BOROS_PONZA_CLASSIC_FAMILY: _add_boros_ponza_classic_path,
    GRIXIS_PERSIST_WIZARDS_FAMILY: _add_grixis_persist_wizards_path,
    GRIXIS_TEMPO_BOWMASTERS_FAMILY: _add_grixis_tempo_bowmasters_path,
    GRIXIS_TEMPO_COUNTERSPELL_FAMILY: _add_grixis_tempo_counterspell_path,
    GRIXIS_TEMPO_DRC_FROG_FAMILY: _add_grixis_tempo_drc_frog_path,
    GRIXIS_TEMPO_FAMILY: _add_grixis_tempo,
    GOLGARI_GORYOS_FAMILY: _add_golgari_goryos,
    GOLGARI_YAWGMOTH_FAMILY: _add_golgari_yawgmoth_young_wolf_path,
    GOLGARI_DELIRIUM_FAMILY: _add_golgari_delirium,
    HARDENED_SCALES_FAMILY: _add_hardened_scales,
    IZZET_PROWESS_FAMILY: _repair_izzet_prowess_rule,
    IZZET_CAULDRON_FAMILY: partial(
        _add_owner_bulk_batch2_parent, family_id=IZZET_CAULDRON_FAMILY
    ),
    IZZET_EXTRA_TURNS_FAMILY: partial(
        _add_owner_bulk_batch2_parent, family_id=IZZET_EXTRA_TURNS_FAMILY
    ),
    IZZET_TWIN_FAMILY: _add_izzet_twin,
    IZZET_TEMPO_FAMILY: partial(
        _add_owner_bulk_batch4_parent, family_id=IZZET_TEMPO_FAMILY
    ),
    IZZET_WIZARDS_FAMILY: _repair_izzet_wizards_primary,
    IZZET_THROUGH_THE_BREACH_FAMILY: _add_izzet_through_the_breach,
    IZZET_STORM_FAMILY: _add_izzet_storm,
    JESKAI_BLINK_FAMILY: _repair_jeskai_blink_primary,
    JESKAI_ENERGY_LOW_RIDDLER_FAMILY: _repair_jeskai_energy_primary,
    JUND_GOBLINS_FAMILY: partial(
        _add_owner_bulk_batch2_parent, family_id=JUND_GOBLINS_FAMILY
    ),
    LEYLINE_FLING_FAMILY: _add_leyline_fling,
    MARDU_VIAL_FAMILY: _add_mardu_vial,
    NAYA_MIDRANGE_FAMILY: partial(
        _add_owner_bulk_batch2_parent, family_id=NAYA_MIDRANGE_FAMILY
    ),
    MONO_GREEN_TRUDGE_FAMILY: _add_mono_green_trudge,
    MONO_GREEN_STOMPY_COMPANION_FAMILY: _add_mono_green_stompy,
    MONO_GREEN_STOMPY_FAMILY: _add_mono_green_stompy,
    MONO_BLUE_NAMOR_FAMILY: _add_mono_blue_namor,
    MONO_BLACK_SAGA_FAMILY: partial(
        _add_owner_bulk_batch4_parent, family_id=MONO_BLACK_SAGA_FAMILY
    ),
    MONO_WHITE_HUMANS_FAMILY: _add_mono_white_humans,
    ORZHOV_BLINK_SPLASH_FAMILY: _add_orzhov_blink_splash,
    ORZHOV_SOULTRADER_FAMILY: _add_orzhov_soultrader_subtype,
    RECLAMATION_FAMILY: _add_reclamation_parents,
    RAKDOS_PERSIST_FAMILY: _add_rakdos_persist,
    RAKDOS_DELIRIUM_CASEY_FAMILY: partial(
        _add_owner_bulk_batch3_parent,
        family_id=RAKDOS_DELIRIUM_CASEY_FAMILY,
    ),
    RAKDOS_DELIRIUM_PHOENIX_FAMILY: partial(
        _add_owner_bulk_batch3_parent,
        family_id=RAKDOS_DELIRIUM_PHOENIX_FAMILY,
    ),
    RAKDOS_AGGRO_FAMILY: partial(
        _add_owner_bulk_batch2_parent, family_id=RAKDOS_AGGRO_FAMILY
    ),
    RAKDOS_MIDRANGE_FAMILY: partial(
        _add_owner_bulk_batch4_parent, family_id=RAKDOS_MIDRANGE_FAMILY
    ),
    RAKDOS_PROWESS_FAMILY: _add_rakdos_prowess_path,
    RAKDOS_THROUGH_THE_BREACH_FAMILY: _add_rakdos_through_the_breach,
    SCAPESHIFT_FAMILY: _add_scapeshift,
    SHAPE_ANEW_FAMILY: partial(
        _add_owner_bulk_batch2_parent, family_id=SHAPE_ANEW_FAMILY
    ),
    SOLEMNITY_PRISON_FAMILY: _add_solemnity_prison,
    SOLEMNITY_BLINK_FAMILY: partial(
        _add_owner_bulk_batch4_parent, family_id=SOLEMNITY_BLINK_FAMILY
    ),
    SULTAI_TEMPO_FAMILY: partial(
        _add_owner_bulk_batch4_parent, family_id=SULTAI_TEMPO_FAMILY
    ),
    SULTAI_PERSIST_FAMILY: _add_sultai_persist,
    SULTAI_FLICKER_FAMILY: partial(
        _add_owner_bulk_batch3_parent, family_id=SULTAI_FLICKER_FAMILY
    ),
    THOPTER_SWORD_BANT_FAMILY: partial(
        _add_owner_bulk_batch2_parent, family_id=THOPTER_SWORD_BANT_FAMILY
    ),
    PRIMAL_PRAYERS_RECRUITER_FAMILY: partial(
        _add_owner_bulk_batch2_parent,
        family_id=PRIMAL_PRAYERS_RECRUITER_FAMILY,
    ),
    PRIMAL_PRAYERS_ZENITH_FAMILY: partial(
        _add_owner_bulk_batch2_parent, family_id=PRIMAL_PRAYERS_ZENITH_FAMILY
    ),
    YAWGMOTH_ENERGY_FAMILY: partial(
        _add_owner_bulk_batch4_parent, family_id=YAWGMOTH_ENERGY_FAMILY
    ),
}


def build_shadow_rules(root: Path = ROOT) -> dict[str, Any]:
    production_path = root / "my_archetypes" / "modern.yaml"
    if _sha256(production_path) != PRODUCTION_MODERN_SHA256:
        raise ValueError("Modern production rules changed from the accepted R3 base")
    production = _read_mapping(production_path)
    if (
        production.get("schema_version") != "1.1.0"
        or production.get("format") != "modern"
    ):
        raise ValueError("Modern production rules have an unexpected identity")

    accepted = _accepted_shadow_families(root)
    unsupported = sorted(set(accepted) - set(PROPOSAL_HANDLERS))
    if unsupported:
        raise ValueError(
            f"accepted shadow dispositions have no reviewed proposal: {unsupported}"
        )
    rakdos = accepted.get(RAKDOS_PERSIST_FAMILY)
    if rakdos != {
        "family_id": RAKDOS_PERSIST_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "rakdos-persist",
        "rationale": (
            "Owner accepted a separate Rakdos Persist parent for the recurring "
            "Archon/Bloodghast sacrifice-reanimation family; Abhorrent Oculus "
            "remains required for Grixis Persist, and lists with three or more "
            "main-deck Living End remain Living End."
        ),
        "owner_accepted": True,
    }:
        raise ValueError(
            "Rakdos Persist disposition is not the exact owner-accepted decision"
        )
    asmo_persist = accepted.get(ASMO_PERSIST_FAMILY)
    if asmo_persist != {
        "family_id": ASMO_PERSIST_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "asmo-persist",
        "rationale": (
            "Owner accepted Asmo Persist as a separate parent rather than a "
            "Rakdos Persist subtype because its Asmoranomardicadaistinaculdacar, "
            "Underworld Cookbook, and Ovalchase Daredevil engine is materially "
            "different from the traditional Bloodghast build. Ovalchase "
            "Daredevil is an absolute required core; Monument to Endurance, "
            "Mox Opal, Emperor of Bones, and Urza's Saga remain construction "
            "choices."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Asmo Persist disposition is not the accepted decision")
    izzet_storm = accepted.get(IZZET_STORM_FAMILY)
    if izzet_storm != {
        "family_id": IZZET_STORM_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "izzet-storm",
        "rationale": (
            "Owner accepted Izzet Storm as a separate parent rather than a "
            "Ruby Storm subtype or supplemental path. The reviewed rule uses "
            "Ral, Stormcatch Mentor, and Past in Flames as the stable Izzet "
            "engine and excludes Ruby Medallion; Flow State, the ritual mix, "
            "Manamorphose, Grapeshot, and blue card selection remain "
            "construction choices."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Izzet Storm disposition is not the accepted decision")
    eldrazi_ouroboroid = accepted.get(ELDRAZI_OUROBOROID_FAMILY)
    if eldrazi_ouroboroid != {
        "family_id": ELDRAZI_OUROBOROID_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "eldrazi-ouroboroid",
        "rationale": (
            "Owner accepted Eldrazi Ouroboroid as a separate parent rather than "
            "an Eldrazi Aggro path, an Eldrazi Ramp subtype, or Badgermole Combo. "
            "The reviewed mainboard rule requires at least three each of "
            "Ouroboroid, Badgermole Cub, Eldrazi Temple, and Sowing Mycospawn. "
            "Existing Eldrazi, Broodscale Combo, and Badgermole Combo rules retain "
            "precedence when a future list satisfies both identities; Thought-Knot "
            "Seer, Green Sun's Zenith, Springheart Nantuko, Kozilek's Command, and "
            "the tutor package remain construction choices."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Eldrazi Ouroboroid disposition is not the accepted decision")
    sultai_persist = accepted.get(SULTAI_PERSIST_FAMILY)
    if sultai_persist != {
        "family_id": SULTAI_PERSIST_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "sultai-persist",
        "rationale": (
            "Owner accepted Sultai Persist as a separate parent rather than a "
            "Grixis, Agadeem, Esper, Rakdos, or Asmo Persist path. The reviewed "
            "mainboard rule requires at least three each of Persist, Archon of "
            "Cruelty, Psychic Frog, and Malevolent Rumble. Existing Persist "
            "identities retain precedence if a future list satisfies both rules; "
            "Eyetwitch, Stitcher's Supplier, Witherbloom Charm, Flare of Malice, "
            "Abhorrent Oculus, Emperor of Bones, and the remaining sacrifice/"
            "self-mill package remain construction choices."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Sultai Persist disposition is not the accepted decision")
    golgari_delirium = accepted.get(GOLGARI_DELIRIUM_FAMILY)
    if golgari_delirium != {
        "family_id": GOLGARI_DELIRIUM_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "golgari-delirium",
        "rationale": (
            "Owner accepted Golgari Delirium as a separate parent with no subtype "
            "because the reviewed Saga and Moonshadow builds share 53 of 60 "
            "main-deck cards and the complete sideboard; Urza's Saga and its "
            "toolbox artifacts plus Moonshadow and Street Wraith remain "
            "construction choices. The reviewed mainboard rule requires at least "
            "three each of Nethergoyf, Omnivorous Flytrap, and Mishra's Bauble, "
            "at least two Witherbloom Command, reviewed black and green mana "
            "sources, and no reviewed white, blue, or red main-deck mana source. "
            "Existing explicit identities retain precedence."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Golgari Delirium disposition is not the accepted decision")
    bogles = accepted.get(BOGLES_FAMILY)
    if bogles != {
        "family_id": BOGLES_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "bogles",
        "rationale": (
            "Owner accepted Bogles as a separate color-agnostic parent with no "
            "subtype. The reviewed mainboard rule requires at least three each "
            "of Slippery Bogle, Gladecover Scout, and Ethereal Armor; these two "
            "hexproof creatures and the defining Aura payoff are sufficient to "
            "identify the archetype. Daybreak Coronet, Kor Spiritdancer, "
            "Light-Paws, Rancor, the Umbra mix, Sheltered by Ghosts, Spirit "
            "Mantle, Reprieve, and the remaining Aura package are construction "
            "choices."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Bogles disposition is not the accepted decision")
    reclamation = accepted.get(RECLAMATION_FAMILY)
    if reclamation != {
        "family_id": RECLAMATION_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "temur-reclamation|bant-reclamation",
        "rationale": (
            "Owner accepted two separate color-bounded parents with no "
            "subtypes, Temur Reclamation and Bant Reclamation. Each reviewed "
            "rule requires at least three main-deck Wilderness Reclamation, "
            "reviewed main-deck mana sources for all three named colors, no "
            "reviewed main-deck off-color source, and no reviewed actual "
            "off-color spell in either main deck or sideboard. Growth Spiral, "
            "Galvanic Discharge, Traumatic Critique, Counterspell, Consult the "
            "Star Charts, Orim's Chant, Planar Genesis, Teferi, sweepers, and "
            "other interaction or payoff packages remain construction choices. "
            "The Reclamation parents outrank Izzet Wizards, Chant Control, and "
            "generic control; complete combo identities and Omnath Midrange "
            "retain precedence. Unsupported four-color or other color groups "
            "remain Unknown unless an existing explicit identity applies."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Reclamation disposition is not the accepted decision")
    broodscale = accepted.get(GRUUL_BROODSCALE_FAMILY)
    if broodscale != {
        "family_id": GRUUL_BROODSCALE_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "map_existing",
        "target_identity": "broodscale-combo/gruul",
        "rationale": (
            "Owner accepted the recurring Eldrazi-heavy Broodscale family as "
            "Gruul Broodscale Combo by lowering only the main-deck Blade of the "
            "Bloodchief threshold from three to two; Basking Broodscale and "
            "Stomping Ground requirements remain unchanged."
        ),
        "owner_accepted": True,
    }:
        raise ValueError(
            "Gruul Broodscale disposition is not the exact owner-accepted decision"
        )
    esper_value = accepted.get(ESPER_VALUE_FAMILY)
    if esper_value != {
        "family_id": ESPER_VALUE_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "map_existing",
        "target_identity": "esper-ketramose|esper-blink",
        "rationale": (
            "Owner accepted a deterministic split of this transitive candidate "
            "family; low-count Relic/Ketramose lists with at most two Phelia map "
            "to Esper Ketramose, while the remaining Ephemerate/Frog/Solitude "
            "lists map to Esper Blink with a sweeper-heavy control exclusion."
        ),
        "owner_accepted": True,
        "partition": [
            {
                "target_identity": "esper-ketramose",
                "record_ids": [
                    "154989c4ea5400776303",
                    "2a91848de862a805e5bf",
                    "38ea22f638a19f3946ed",
                    "ed40c4fe85260354a346",
                ],
            },
            {
                "target_identity": "esper-blink",
                "record_ids": [
                    "1c47530b320c2abb88b0",
                    "626720cad88d9b967b5e",
                    "96477803963b8d74298d",
                ],
            },
        ],
    }:
        raise ValueError(
            "Esper value-family disposition is not the exact owner-accepted decision"
        )
    scapeshift = accepted.get(SCAPESHIFT_FAMILY)
    if scapeshift != {
        "family_id": SCAPESHIFT_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "scapeshift/naya|scapeshift/four-color",
        "rationale": (
            "Owner accepted Scapeshift as a new parent with Naya and Four-Color "
            "subtypes; Bring to Light and reviewed mana sources distinguish the "
            "Four-Color record, while Amulet of Vigor is excluded."
        ),
        "owner_accepted": True,
        "partition": [
            {
                "target_identity": "scapeshift/naya",
                "record_ids": [
                    "54b72fc579d904e66b0c",
                    "8c2d5ce7408bf07f4ac9",
                    "b52fb8112fbbbfe12cca",
                    "c50cf6faf9a08ccbd515",
                    "d61a34363d9282c91c8d",
                    "f6ae34fac2f7ac134d6b",
                ],
            },
            {
                "target_identity": "scapeshift/four-color",
                "record_ids": ["1226de5394fb836abbe4"],
            },
        ],
    }:
        raise ValueError(
            "Scapeshift disposition is not the exact owner-accepted decision"
        )
    gruul_valakut = accepted.get(GRUUL_VALAKUT_FAMILY)
    if gruul_valakut != {
        "family_id": GRUUL_VALAKUT_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "gruul-valakut",
        "rationale": (
            "Owner accepted the recurring white-free Valakut/Dryad/Icetill "
            "family as a separate Gruul Valakut parent because its Vibrance "
            "and Wrenn engine contains no Scapeshift."
        ),
        "owner_accepted": True,
    }:
        raise ValueError(
            "Gruul Valakut disposition is not the exact owner-accepted decision"
        )
    gruul_midrange = accepted.get(GRUUL_MIDRANGE_FAMILY)
    if gruul_midrange != {
        "family_id": GRUUL_MIDRANGE_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "gruul-midrange",
        "rationale": (
            "Owner accepted the recurring Karn/Blood Moon/Utopia Sprawl lists "
            "as a separate Gruul Midrange parent rather than Mono-Green Stompy "
            "or Gruul Ponza. The reviewed mainboard rule requires at least three "
            "each of Karn, the Great Creator, Blood Moon, and Utopia Sprawl. "
            "Fanatic of Rhonas, Malevolent Rumble, Endurance, Arbor Elf, "
            "Vibrance, Fable of the Mirror-Breaker, Pillage, removal, and the "
            "Karn wishboard remain construction choices; no subtype is added."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Gruul Midrange disposition is not the accepted decision")
    mono_blue_namor = accepted.get(MONO_BLUE_NAMOR_FAMILY)
    if mono_blue_namor != {
        "family_id": MONO_BLUE_NAMOR_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "mono-blue-namor",
        "rationale": (
            "Owner accepted the recurring Namor and Archmage's Charm counterspell "
            "shells as a separate Mono-Blue Namor parent rather than traditional "
            "Mono-Blue Merfolk or a generic Mono-Blue Control parent. The reviewed "
            "rule requires at least three main-deck Namor and Archmage's Charm, "
            "excludes Lord of Atlantis, Goblin Charbelcher, reviewed off-color "
            "main-deck mana sources, and reviewed off-color spells in either zone. "
            "Disrupting Shoal, Force of Negation, Vodalian Hexcatcher, Svyelun, "
            "Spreading Seas, and Harbinger of the Seas remain construction choices; "
            "Phyrexian-neutral cards do not create a color splash, and no subtype is "
            "added."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Mono-Blue Namor disposition is not the accepted decision")
    golgari_goryos = accepted.get(GOLGARI_GORYOS_FAMILY)
    if golgari_goryos != {
        "family_id": GOLGARI_GORYOS_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "golgari-goryos",
        "rationale": (
            "Owner accepted the recurring Dina's Guidance and Formidable Speaker "
            "lists as a separate Golgari Goryo's parent rather than Esper Persist, "
            "Golgari Persist, or a generic Golgari Reanimator identity. The reviewed "
            "rule requires at least three main-deck Goryo's Vengeance, Dina's "
            "Guidance, and Formidable Speaker, requires reviewed black and green "
            "main-deck mana sources, and excludes reviewed white, blue, and red "
            "main-deck mana sources. Persist, Unmarked Grave, Shifting Woodland, "
            "Archon of Cruelty, and individual legendary reanimation targets remain "
            "construction choices; no subtype is added."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Golgari Goryo's disposition is not the accepted decision")
    izzet_prowess = accepted.get(IZZET_PROWESS_FAMILY)
    if izzet_prowess != {
        "family_id": IZZET_PROWESS_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "map_existing",
        "target_identity": "prowess/izzet",
        "rationale": (
            "Owner mapped the two recurring cross-source Cutter and Lava Dart "
            "records to existing Prowess/Izzet and accepted repairing the existing "
            "prowess-izzet rule rather than adding an identity. The rule keeps its "
            "stable ID and priority, continues to require at least three main-deck "
            "Cori-Steel Cutter and Lava Dart plus two Preordain, reduces Monastery "
            "Swiftspear from three to two, removes the Dragon's Rage Channeler "
            "requirement, and retains the reviewed white, black, and green spell "
            "exclusions in either zone. Dragon's Rage Channeler, Soul-Scar Mage, "
            "Slickshot Show-Off, Stormchaser's Talent, Boomerang Basics, Expressive "
            "Iteration, and Experimental Synthesizer remain construction choices. "
            "Prowess/Lessons retains higher priority, and the separate Emry-based "
            "Izzet Steel-Cutter rule remains unchanged."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Izzet Prowess disposition is not the accepted decision")
    solemnity_prison = accepted.get(SOLEMNITY_PRISON_FAMILY)
    if solemnity_prison != {
        "family_id": SOLEMNITY_PRISON_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "solemnity-prison",
        "rationale": (
            "Owner accepted the recurring Solemnity lock lists as a separate "
            "Solemnity Prison parent with no subtype. Two mutually exclusive "
            "mainboard paths require at least three Solemnity plus either three "
            "Nine Lives, or three Phyrexian Unlife with at most two Nine Lives. "
            "United Battlefront, Greater Auramancy, Sterling Grove, Solitary "
            "Confinement, and color sources remain construction choices; no "
            "speculative Broodmoth or Enduring Ideal exclusion is added."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Solemnity Prison disposition is not the accepted decision")
    mono_green_trudge = accepted.get(MONO_GREEN_TRUDGE_FAMILY)
    if mono_green_trudge != {
        "family_id": MONO_GREEN_TRUDGE_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "mono-green-trudge",
        "rationale": (
            "Owner accepted the recurring Trudge and Henge lists as a separate "
            "Mono-Green Trudge parent with no subtype rather than Fight Rigging "
            "or Badgermole Combo. The reviewed mainboard rule requires at least "
            "three Slumbering Trudge and The Great Henge, permits at most two "
            "Fight Rigging, and excludes reviewed white, blue, black, and red "
            "main-deck mana sources. Badgermole Cub, Fanatic of Rhonas, Life's "
            "Legacy, Ouroboroid, Green Sun's Zenith, Ashaya, Quirion Ranger, "
            "Springheart Nantuko, Summoner's Pact, and Craterhoof Behemoth remain "
            "construction choices. Existing Fight Rigging retains builds with "
            "at least three Fight Rigging, and future true splashes remain Unknown "
            "pending review."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Mono-Green Trudge disposition is not accepted")
    grixis_tempo = accepted.get(GRIXIS_TEMPO_FAMILY)
    if grixis_tempo != {
        "family_id": GRIXIS_TEMPO_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "grixis-tempo",
        "rationale": (
            "Owner accepted a separate Grixis Tempo parent for the Ragavan-based "
            "proactive tempo shell rather than retaining it under Dimir Tempo's "
            "red-splash subtype. The reviewed rule requires at least three "
            "main-deck Fatal Push, Psychic Frog, and Ragavan, at least one Watery "
            "Grave and Steam Vents, excludes Goryo's Vengeance, Persist, Death's "
            "Shadow, and reviewed white and green main-deck mana sources, and "
            "does not constrain Counterspell. The stable dimir-tempo-grixis rule "
            "and internal subtype IDs remain, its visible subtype names become "
            "Dimir Red Splash and Dimir White Splash, and its red-splash path "
            "permits at most two Ragavan so the identities remain mutually "
            "exclusive."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Grixis Tempo disposition is not accepted")
    orzhov_soultrader = accepted.get(ORZHOV_SOULTRADER_FAMILY)
    if orzhov_soultrader != {
        "family_id": ORZHOV_SOULTRADER_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "map_existing",
        "target_identity": "soultrader/orzhov",
        "rationale": (
            "Owner mapped the established Orzhov Soultrader combo shell to "
            "existing Soultrader with a new Orzhov subtype rather than Mardu "
            "Energy or a new parent. The reviewed rule requires at least three "
            "main-deck Warren Soultrader, Gravecrawler, and Marionette Apprentice "
            "plus one Godless Shrine; it excludes reviewed blue, green, and red "
            "main-deck mana sources and reviewed off-color spells in either zone. "
            "The Orzhov rule has higher priority than Mardu Energy so the complete "
            "combo core wins even when Ajani or other Energy cards are present. "
            "Guide of Souls, Ocelot Pride, Ajani, Knight-Errant of Eos, Chthonian "
            "Nightmare, Orcish Bowmasters, Sephiroth, and Overlord remain "
            "construction choices."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Orzhov Soultrader disposition is not accepted")
    grixis_dress_down = accepted.get(GRIXIS_DRESS_DOWN_FAMILY)
    if grixis_dress_down != {
        "family_id": GRIXIS_DRESS_DOWN_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "grixis-dress-down",
        "rationale": (
            "Owner accepted Grixis Dress Down as a separate parent rather than "
            "broad Grixis Control or Dimir Tempo's red-splash subtype. The "
            "reviewed mainboard rule requires at least three Dress Down, "
            "Nulldrifter, and Kroxa, Titan of Death's Hunger plus one Steam "
            "Vents and Watery Grave; it excludes Goryo's Vengeance, Persist, "
            "Death's Shadow, reviewed white and green main-deck mana sources, "
            "and reviewed white and green spells in either zone. The priority "
            "sits below Grixis Tempo and above Dimir Tempo's red splash. Fatal "
            "Push, Consign to Memory, Traumatic Critique, Force of Negation, "
            "and Consult the Star Charts remain construction choices. "
            "Four-color Dress Down remains Unknown pending separate evidence."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Grixis Dress Down disposition is not accepted")
    grixis_goryos_emperor = accepted.get(GRIXIS_GORYOS_EMPEROR_FAMILY)
    if grixis_goryos_emperor != {
        "family_id": GRIXIS_GORYOS_EMPEROR_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "map_existing",
        "target_identity": "grixis-goryos",
        "rationale": (
            "Owner mapped the singleton low-Goryo's Emperor build to existing "
            "Grixis Goryo's rather than adding a parent or subtype. The supplemental "
            "mainboard path requires one or two Goryo's Vengeance, at least three "
            "each of Emperor of Bones, Atraxa, Grand Unifier, Faithless Looting, "
            "and Psychic Frog, and excludes Ephemerate and Persist. The original "
            "Grixis Goryo's primary remains unchanged and mutually exclusive. "
            "Griselbrand, Sin, Spira's Punishment, Thoughtseize, Force of Negation, "
            "Consign to Memory, and discard outlets remain construction choices; "
            "zero-Goryo's Emperor builds remain Unknown pending separate evidence."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Grixis Goryo's Emperor disposition is not accepted")
    mono_white_humans = accepted.get(MONO_WHITE_HUMANS_FAMILY)
    if mono_white_humans != {
        "family_id": MONO_WHITE_HUMANS_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "mono-white-humans",
        "rationale": (
            "Owner accepted the singleton as a new Mono-White Humans parent "
            "with no subtype, explicitly separate from the later Five-Color "
            "Humans family. The reviewed mainboard rule requires at least three "
            "Aether Vial, Champion of the Parish, Thalia's Lieutenant, and "
            "Coppercoat Vanguard plus at least five Plains; it excludes Ocelot "
            "Pride, reviewed blue, black, red, and green main-deck mana sources, "
            "and reviewed off-color spells in either zone. Adeline, Resplendent "
            "Cathar, Guide of Souls, Esper Sentinel, Ranger-Captain of Eos, Voice "
            "of Victory, and Witch Enchanter remain construction choices. The "
            "observed Five-Color Humans list has no Coppercoat Vanguard and only "
            "two Plains, remains Unknown, and will receive separate parent-level "
            "review at its own queue position."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Mono-White Humans disposition is not accepted")
    gruul_cragganwick = accepted.get(GRUUL_CRAGGANWICK_FAMILY)
    if gruul_cragganwick != {
        "family_id": GRUUL_CRAGGANWICK_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "gruul-cragganwick",
        "rationale": (
            "Owner accepted the singleton as a new Gruul Cragganwick parent "
            "with no subtype, separate from Cremator Goryo's and Gruul "
            "Midrange. The reviewed mainboard rule requires at least three "
            "Cragganwick Cremator, Yargle and Multani, Badgermole Cub, and "
            "Blood Moon plus reviewed red and green mana sources; it excludes "
            "reviewed white, blue, and black main-deck mana sources, Goryo's "
            "Vengeance, and Emrakul, the Aeons Torn. Formidable Speaker, "
            "Monstrous Emergence, Screaming Nemesis, The Underworld Cookbook, "
            "and Urza's Saga remain construction choices. No generic black-spell "
            "exclusion is added because Yargle is the combo payload despite its "
            "black mana symbol."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Gruul Cragganwick disposition is not accepted")
    amulet_scapeshift = accepted.get(AMULET_SCAPESHIFT_FAMILY)
    if amulet_scapeshift != {
        "family_id": AMULET_SCAPESHIFT_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "map_existing",
        "target_identity": "amulet-titan",
        "rationale": (
            "Owner accepted the singleton Scapeshift list as Amulet Titan due "
            "to four Amulet of Vigor, the bounce-land/Saga engine, Cultivator "
            "Colossus, and Primeval Titan; it must not map to Scapeshift."
        ),
        "owner_accepted": True,
    }:
        raise ValueError(
            "Amulet Scapeshift disposition is not the exact owner-accepted decision"
        )
    izzet_breach = accepted.get(IZZET_THROUGH_THE_BREACH_FAMILY)
    if izzet_breach != {
        "family_id": IZZET_THROUGH_THE_BREACH_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "izzet-through-the-breach",
        "rationale": (
            "Owner accepted Izzet Through the Breach as a separate parent with "
            "no subtype; the reviewed Through the Breach, Emrakul, Ugin's "
            "Labyrinth, Eldrazi Temple, Devourer, Kozilek's Command, and Talisman "
            "of Creativity core distinguishes it from Rakdos and historical Gruul "
            "builds."
        ),
        "owner_accepted": True,
    }:
        raise ValueError(
            "Izzet Through the Breach disposition is not the accepted decision"
        )
    rakdos_breach = accepted.get(RAKDOS_THROUGH_THE_BREACH_FAMILY)
    if rakdos_breach != {
        "family_id": RAKDOS_THROUGH_THE_BREACH_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "rakdos-through-the-breach",
        "rationale": (
            "Owner accepted the classic Rakdos Through the Breach list as a "
            "separate parent with no subtype; its reviewed Goryo's Vengeance, "
            "Faithless Looting, and Talisman of Indulgence engine distinguishes "
            "the graveyard-oriented build from Izzet Through the Breach."
        ),
        "owner_accepted": True,
    }:
        raise ValueError(
            "Rakdos Through the Breach disposition is not the accepted decision"
        )
    cosmogoyf_necro = accepted.get(COSMOGOYF_NECRO_FAMILY)
    if cosmogoyf_necro != {
        "family_id": COSMOGOYF_NECRO_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "map_existing",
        "target_identity": "necrodominance/cosmogoyf",
        "rationale": (
            "Owner accepted Cosmogoyf Necrodominance as a subtype of the "
            "existing Necrodominance parent because Necrodominance, Soul Spike, "
            "and black interaction define the deck while Cosmogoyf is its "
            "finisher; Thud and Fling remain explicit exclusions so the subtype "
            "cannot absorb Fling Goyf."
        ),
        "owner_accepted": True,
    }:
        raise ValueError(
            "Cosmogoyf Necrodominance disposition is not the accepted decision"
        )
    badgermole = accepted.get(BADGERMOLE_FAMILY)
    if badgermole != {
        "family_id": BADGERMOLE_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": ("badgermole-combo/golgari|badgermole-combo/mono-green"),
        "rationale": (
            "Owner accepted Badgermole Combo as a separate parent with Golgari "
            "and Mono-Green subtypes. Devoted Combo requires both Devoted Druid "
            "and Vizier of Remedies; the mono-green Druid/Quillspike record has no "
            "Vizier or white source and remains Badgermole. Existing Devoted Combo "
            "gains Abzan and Selesnya subtypes; blue sideboard or main-deck splash "
            "does not disqualify an otherwise Abzan build."
        ),
        "owner_accepted": True,
        "partition": [
            {
                "target_identity": "badgermole-combo/golgari",
                "record_ids": [
                    "03dfaac2fac24535b3de",
                    "5fe2ea0a481a3fae9fc0",
                    "c911c95f1984590a3537",
                ],
            },
            {
                "target_identity": "badgermole-combo/mono-green",
                "record_ids": [
                    "59770edbd1b9ac5b1213",
                    "f30d57c6bc480152cf4f",
                ],
            },
        ],
    }:
        raise ValueError("Badgermole disposition is not the accepted decision")

    badgermole_landfall = accepted.get(BADGERMOLE_LANDFALL_FAMILY)
    if badgermole_landfall != {
        "family_id": BADGERMOLE_LANDFALL_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "map_existing",
        "target_identity": "badgermole-combo/landfall",
        "rationale": (
            "Owner accepted this recurring landfall construction as the Landfall "
            "subtype of Badgermole Combo because it retains the reviewed "
            "Badgermole Cub, Green Sun's Zenith, Quirion Ranger, Springheart "
            "Nantuko, and Ashaya combo core while replacing the Leyline support "
            "package with Icetill Explorer and landfall support. The reviewed "
            "mainboard rule requires at least three Badgermole Cub, three Green "
            "Sun's Zenith, two Quirion Ranger, three Springheart Nantuko, one "
            "Ashaya, and three Icetill Explorer, and excludes Leyline of Abundance "
            "and Vizier of Remedies. Earthbender Ascension, Nature's Rhythm, color "
            "splash, and other toolbox cards remain construction choices."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Badgermole Landfall disposition is not the accepted decision")

    jeskai_blink = accepted.get(JESKAI_BLINK_FAMILY)
    if jeskai_blink != {
        "family_id": JESKAI_BLINK_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "map_existing",
        "target_identity": "jeskai-blink",
        "rationale": (
            "Owner mapped the two recurring low-Phelia records to existing "
            "Jeskai Blink and accepted repairing the existing "
            "jeskai-blink-primary rule rather than adding a construction-specific "
            "rule. The Phelia, Exuberant Shepherd mainboard threshold changes "
            "from three to two while Quantum Riddler and Solitude remain at "
            "three, the existing red-source, Stoneforge Mystic, black-source, "
            "green-source, and Goryo's Vengeance boundaries remain unchanged, "
            "and Fable of the Mirror-Breaker, Ephemerate, Phlage, Ragavan, "
            "Galvanic Discharge, Counterspell, and other value or interaction "
            "packages remain construction choices."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Jeskai Blink disposition is not the accepted decision")

    mardu_vial = accepted.get(MARDU_VIAL_FAMILY)
    if mardu_vial != {
        "family_id": MARDU_VIAL_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "mardu-vial",
        "rationale": (
            "Owner accepted the recurring Aether Vial and Imperial Recruiter "
            "toolbox as a separate Mardu Vial parent rather than Mardu Energy "
            "because the reviewed lists omit Ocelot Pride and do not use Energy "
            "as a shared resource engine. The reviewed mainboard rule requires "
            "at least three Aether Vial, three Imperial Recruiter, two Chthonian "
            "Nightmare, and three Solitude. Guide of Souls, Ajani, Galvanic "
            "Discharge, Emperor of Bones, Phyrexian Tower, Seasoned Pyromancer, "
            "and other toolbox cards remain construction choices, and no subtype "
            "is added. Both existing Mardu Energy rules retain higher priority "
            "for a future hybrid that satisfies their complete Energy signatures."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Mardu Vial disposition is not the accepted decision")

    agadeem_persist = accepted.get(AGADEEM_PERSIST_REDUCED_CRYPT_FAMILY)
    if agadeem_persist != {
        "family_id": AGADEEM_PERSIST_REDUCED_CRYPT_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "map_existing",
        "target_identity": "agadeem-persist",
        "rationale": (
            "Owner mapped the two recurring reduced-Crypt records to existing "
            "Agadeem Persist rather than creating a BG Persist or Black Lessons "
            "parent because they retain the Eyetwitch, Stitcher's Supplier, "
            "Phyrexian Tower, Persist, and Archon of Cruelty game plan of "
            "existing Agadeem lists. The existing agadeem-persist-primary rule "
            "continues to require at least three main-deck Crypt of Agadeem. A "
            "mutually exclusive supplemental path requires at least three "
            "main-deck Persist, Archon of Cruelty, Eyetwitch, Stitcher's "
            "Supplier, and Phyrexian Tower plus one or two Crypt of Agadeem. "
            "Emperor of Bones, Overlord of the Balemurk, Street Wraith, "
            "interaction, and the green splash remain construction choices. "
            "Existing Grixis, Esper, Asmo, Rakdos, and Sultai Persist rules "
            "retain higher priority over the supplemental path for future "
            "hybrids."
        ),
        "owner_accepted": True,
    }:
        raise ValueError(
            "Agadeem Persist reduced-Crypt disposition is not the accepted decision"
        )

    jeskai_energy = accepted.get(JESKAI_ENERGY_LOW_RIDDLER_FAMILY)
    if jeskai_energy != {
        "family_id": JESKAI_ENERGY_LOW_RIDDLER_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "map_existing",
        "target_identity": "jeskai-energy",
        "rationale": (
            "Owner mapped the two recurring low-Riddler records to existing "
            "Jeskai Energy rather than Boros Energy, Jeskai Blink, or a new "
            "identity. The existing jeskai-energy-primary rule ID and priority "
            "remain unchanged. Its mainboard requirements retain at least three "
            "Ajani, Nacatl Pariah and three Guide of Souls, add at least three "
            "Ocelot Pride and one reviewed red mana source, and reduce Quantum "
            "Riddler from three copies to one. Ocelot Pride preserves the "
            "accepted Guide-plus-Ocelot Energy identity, while the red source "
            "and main-deck Quantum Riddler establish Jeskai rather than Azorius "
            "or Boros. Galvanic Discharge, Ragavan, Goblin Bombardment, Phlage, "
            "Fable, Mockingbird, Ranger-Captain, Solitude, Phelia, and other "
            "value or interaction cards remain construction choices."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Jeskai Energy disposition is not the accepted decision")

    dimir_coffers = accepted.get(COFFERS_DIMIR_FAMILY)
    if dimir_coffers != {
        "family_id": COFFERS_DIMIR_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "coffers/dimir",
        "rationale": (
            "Owner accepted the singleton blue-black Coffers control list as "
            "the Dimir subtype of the new Coffers parent. Its reviewed Coffers, "
            "Watery Grave, and Consult the Star Charts core distinguishes it "
            "from Golgari, Umori, Dark Maestro, and Necrodominance builds."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Dimir Coffers disposition is not the accepted decision")

    maestro_umori = accepted.get(DARK_MAESTRO_UMORI_FAMILY)
    if maestro_umori != {
        "family_id": DARK_MAESTRO_UMORI_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "dark-maestro|coffers/umori",
        "rationale": (
            "Owner accepted Dark Maestro as a separate parent for the three "
            "Molten-Core Maestro Coffers spell-chain lists. The two remaining "
            "all-sorcery tutor lists map to the Umori subtype of a new Coffers "
            "parent; the mainboard-only classifier uses their reviewed Petition, "
            "Tutor, Scrying, and sorcery-removal signature rather than the "
            "sideboard companion card."
        ),
        "owner_accepted": True,
        "partition": [
            {
                "target_identity": "dark-maestro",
                "record_ids": [
                    "41d266c0941adad60d76",
                    "4a2d4c2fc7485aaf48c5",
                    "4d3826e2a4d851b4e968",
                ],
            },
            {
                "target_identity": "coffers/umori",
                "record_ids": [
                    "377839bc726f18cdc258",
                    "d7eae7ab1911770dd0fa",
                ],
            },
        ],
    }:
        raise ValueError("Dark Maestro/Umori disposition is not accepted")

    golgari_coffers = accepted.get(COFFERS_GOLGARI_FAMILY)
    if golgari_coffers != {
        "family_id": COFFERS_GOLGARI_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "coffers/golgari",
        "rationale": (
            "Owner accepted the singleton Karn-based list as the traditional "
            "Golgari subtype of the new Coffers parent. Its reviewed Coffers, "
            "Karn, and Underground Mortuary core distinguishes it from Dimir, "
            "Umori, Dark Maestro, and Necrodominance builds; no empty Mono-Black "
            "subtype is added without a current sample."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Golgari Coffers disposition is not the accepted decision")

    eight_rack = accepted.get(EIGHT_RACK_FAMILY)
    if eight_rack != {
        "family_id": EIGHT_RACK_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "eight-rack",
        "rationale": (
            "Owner accepted the recurring mono-black Rack discard family as a "
            "separate 8-Rack parent. The reviewed mainboard rule requires at "
            "least three The Rack and two Raven's Crime; Smallpox, Bandit's "
            "Talent, Dauthi Voidwalker, and Urza's Saga remain construction "
            "choices rather than identity requirements, and no subtype is added."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("8-Rack disposition is not the accepted decision")

    leyline_fling = accepted.get(LEYLINE_FLING_FAMILY)
    if leyline_fling != {
        "family_id": LEYLINE_FLING_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "leyline-fling",
        "rationale": (
            "Owner accepted the recurring Leyline of Resonance and Callous "
            "Sell-Sword pump-and-sacrifice family as a separate Leyline Fling "
            "parent rather than a Prowess subtype. The reviewed mainboard "
            "signature requires at least three each of Leyline of Resonance, "
            "Heartfire Hero, Callous Sell-Sword, and Monastery Swiftspear; "
            "color sources and individual pump spells are not identity "
            "requirements, and no subtype is added."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Leyline Fling disposition is not the accepted decision")

    orzhov_blink_splash = accepted.get(ORZHOV_BLINK_SPLASH_FAMILY)
    if orzhov_blink_splash != {
        "family_id": ORZHOV_BLINK_SPLASH_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "map_existing",
        "target_identity": "orzhov-blink",
        "rationale": (
            "Owner accepted all four recurring utility-splash lists as Orzhov "
            "Blink because they retain the reviewed Phelia, Balemurk, "
            "Ephemerate, Emperor, Flickerwisp, Solitude, and Thoughtseize "
            "engine. A separate splash rule keeps the strict primary path "
            "unchanged, excludes reviewed Esper, Mardu, and Goryo engines, and "
            "treats off-color utility lands without those engines as "
            "construction choices rather than new identities."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Orzhov Blink splash disposition is not accepted")

    eldrazi_aggro = accepted.get(ELDRAZI_AGGRO_FAMILY)
    if eldrazi_aggro != {
        "family_id": ELDRAZI_AGGRO_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "map_existing",
        "target_identity": "eldrazi-aggro",
        "rationale": (
            "Owner confirmed that Eldrazi Linebreaker is the only required "
            "Eldrazi Aggro core and that the existing It That Heralds the End "
            "requirement is incorrect. The accepted shadow repair keeps the "
            "existing primary rule ID, requires at least three Linebreaker, "
            "excludes Basking Broodscale to preserve the combo boundary, leaves "
            "Glaring Fleshraker and Thought-Knot Seer as common construction "
            "choices, and adds no rule path or subtype."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Eldrazi Aggro disposition is not the accepted decision")

    mono_green_stompy = accepted.get(MONO_GREEN_STOMPY_FAMILY)
    if mono_green_stompy != {
        "family_id": MONO_GREEN_STOMPY_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "mono-green-stompy",
        "rationale": (
            "Owner accepted the recurring Aspect of Hydra and Old-Growth Troll "
            "family as a new Mono-Green Stompy parent with no subtype. The rule "
            "uses only those two stable aggressive devotion payoffs, while Steel "
            "Leaf Champion, Frenzied Baloth, Green Sun's Zenith, mana creatures, "
            "and minor black utility lands remain construction choices. The same "
            "rule intentionally includes the separately reviewed Badgermole and "
            "Endurance singleton family."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Mono-Green Stompy disposition is not accepted")

    mono_green_stompy_companion = accepted.get(MONO_GREEN_STOMPY_COMPANION_FAMILY)
    if mono_green_stompy_companion != {
        "family_id": MONO_GREEN_STOMPY_COMPANION_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "mono-green-stompy",
        "rationale": (
            "Owner jointly accepted this singleton Badgermole and Endurance "
            "construction as Mono-Green Stompy because it shares the reviewed "
            "Aspect of Hydra and Old-Growth Troll core with the recurring family. "
            "Its creature package is a construction variation, not a separate "
            "identity or subtype."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Mono-Green Stompy companion disposition is not accepted")

    dredge = accepted.get(DREDGE_FAMILY)
    if dredge != {
        "family_id": DREDGE_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "map_existing",
        "target_identity": "dredge",
        "rationale": (
            "Owner accepted the three recurring Phoenix and dredge-engine lists "
            "as Dredge and confirmed that Burning Inquiry is a construction "
            "choice rather than a required core. The existing primary rule "
            "keeps Arclight Phoenix, Creeping Chill, and Life from the Loam as "
            "its three positive requirements, removes the Burning Inquiry "
            "threshold, and adds no rule path, parent, or subtype."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Dredge disposition is not the accepted decision")

    hardened_scales = accepted.get(HARDENED_SCALES_FAMILY)
    if hardened_scales != {
        "family_id": HARDENED_SCALES_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "hardened-scales",
        "rationale": (
            "Owner accepted the three recurring counter-artifact lists as a "
            "separate Hardened Scales parent rather than Affinity or Broodscale "
            "Combo. Hardened Scales itself is the only required core; Arcbound "
            "Ravager, Walking Ballista, Zabaz, Agatha's Soul Cauldron, Mox Opal, "
            "and Urza's Saga remain construction choices, and no subtype is added."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Hardened Scales disposition is not accepted")

    izzet_wizards = accepted.get(IZZET_WIZARDS_FAMILY)
    if izzet_wizards != {
        "family_id": IZZET_WIZARDS_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "map_existing",
        "target_identity": "izzet-wizards",
        "rationale": (
            "Owner accepted repairing the existing Izzet Wizards primary rather "
            "than adding an identity. The rule keeps Snapcaster Mage and Flame of "
            "Anor as the core, removes the Lightning Bolt threshold, and directly "
            "excludes the reviewed white spells in either mainboard or sideboard. "
            "White-producing lands alone do not make the deck Jeskai, Apostle's "
            "Blessing remains color-neutral because of Phyrexian mana, and a future "
            "unlisted white spell may temporarily fall to Izzet until the inline "
            "exclusions are updated."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Izzet Wizards disposition is not the accepted decision")

    golgari_yawgmoth = accepted.get(GOLGARI_YAWGMOTH_FAMILY)
    if golgari_yawgmoth != {
        "family_id": GOLGARI_YAWGMOTH_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "map_existing",
        "target_identity": "golgari-yawgmoth",
        "rationale": (
            "Owner mapped the three recurring Birthing Ritual lists to existing "
            "Golgari Yawgmoth. The original Yawgmoth plus Grist path remains "
            "intact, and a supplemental path requires at least three Yawgmoth "
            "and at least two Young Wolf in the mainboard. Young Wolf is treated "
            "as the long-standing sacrifice core; Badgermole Cub, Birthing "
            "Ritual, Chord of Calling, Marionette Apprentice, and Grist remain "
            "construction choices for this path. A future Yawgmoth build that "
            "abandons Young Wolf requires explicit rule review."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Golgari Yawgmoth disposition is not the accepted decision")

    hammer_kellan = accepted.get(HAMMER_KELLAN_FAMILY)
    if hammer_kellan != {
        "family_id": HAMMER_KELLAN_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "map_existing",
        "target_identity": "hammer-time/jeskai",
        "rationale": (
            "Owner expanded the Kellan singleton review into an immediate full "
            "Hammer Time shadow refactor. The existing parent retains Azorius "
            "and Mono-White and gains Boros and Jeskai subtypes. Traditional "
            "paths require at least three main-deck Colossus Hammer and "
            "Puresteel Paladin, while the mutually exclusive Kellan path "
            "requires at least three Kellan, two Super-Soldier Serum, and at "
            "most two Puresteel Paladin. Reviewed main-deck mana sources and "
            "any-zone colored spells determine the subtype. Metallic Rebuke, "
            "Stoneforge Mystic, Sigarda's Aid, Leyline Axe, and Battlefield "
            "Improvisation remain construction choices."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Kellan Hammer disposition is not the accepted decision")

    hammer_traditional = accepted.get(HAMMER_TRADITIONAL_FAMILY)
    if hammer_traditional != {
        "family_id": HAMMER_TRADITIONAL_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "map_existing",
        "target_identity": "hammer-time/jeskai",
        "rationale": (
            "Owner jointly accepted this later traditional Hammer singleton "
            "during the immediate full-parent refactor. Its Colossus Hammer "
            "and Puresteel Paladin core maps to Hammer Time, while Hallowed "
            "Fountain plus sideboard Wear/Tear makes it Jeskai under the "
            "existing main-and-sideboard splash policy. The mutually exclusive "
            "red-source and red-spell Jeskai paths avoid requiring Metallic "
            "Rebuke and preserve one Hammer subtype match per reviewed list."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Traditional Hammer disposition is not the accepted decision")

    izzet_twin = accepted.get(IZZET_TWIN_FAMILY)
    if izzet_twin != {
        "family_id": IZZET_TWIN_FAMILY,
        "review_status": "owner_accepted",
        "disposition": "new_identity",
        "target_identity": "izzet-twin",
        "rationale": (
            "Owner accepted the singleton as a new Izzet Twin parent with no "
            "subtype. The reviewed rule requires at least two main-deck "
            "Splinter Twin and three Fear of Missing Out, plus reviewed blue "
            "and red main-deck mana sources; it excludes reviewed white, "
            "black, and green main-deck mana sources and any-zone spells. "
            "Flow State, Mishra's Bauble, Tamiyo, Inquisitive Student, "
            "Expressive Iteration, Force of Negation, and the remaining "
            "interaction package are construction choices. Traditional "
            "Deceiver Exarch and Pestermite paths remain unimplemented "
            "pending real samples."
        ),
        "owner_accepted": True,
    }:
        raise ValueError("Izzet Twin disposition is not the accepted decision")

    batch1_expected = {
        GRIXIS_DEATHS_SHADOW_FAMILY: (
            "deaths-shadow/grixis",
            "Owner mapped the reviewed tabletop singleton to existing Grixis "
            "Death's Shadow. The supplemental path requires at least three "
            "main-deck Death's Shadow, Thoughtseize, Street Wraith, and Psychic "
            "Frog plus Blood Crypt, Watery Grave, and Steam Vents; it permits at "
            "most one Stubborn Denial and excludes Goryo's Vengeance and Persist "
            "so the established Stubborn Denial path and reanimation identities "
            "remain separate.",
        ),
        FOUR_COLOR_RITUAL_FAMILY: (
            "five-color-ritual",
            "Owner mapped the reviewed Four-Color Ritual value build to the "
            "existing Five-Color Ritual parent rather than creating a color-count "
            "identity. The supplemental path requires at least three main-deck "
            "Birthing Ritual, Shardless Agent, and Omnath, Locus of Creation plus "
            "one Elesh Norn, Mother of Machines, while permitting at most two "
            "Magmatic Hellkite so it remains mutually exclusive with the "
            "established Hellkite path.",
        ),
        BOROS_PONZA_WILDFIRE_FAMILY: (
            "boros-land-destruction",
            "Owner mapped the reviewed Boom/Bust Wildfire singleton to existing "
            "Boros Ponza. The supplemental path requires at least three main-deck "
            "Boom/Bust, Flagstones of Trokair, Cleansing Wildfire, and Price of "
            "Freedom; Field of Ruin, Erode, Wrath of the Skies, and the remaining "
            "land-destruction package remain construction choices.",
        ),
        GRIXIS_PERSIST_WIZARDS_FAMILY: (
            "grixis-persist",
            "Owner mapped the reviewed high-deviation Wizards reanimation "
            "singleton to existing Grixis Persist. The supplemental path requires "
            "at least three main-deck Persist, Thundertrap Trainer, Traumatic "
            "Critique, and Tamiyo, Inquisitive Student plus Watery Grave and Steam "
            "Vents, and excludes Goryo's Vengeance; Archon of Cruelty, Faithless "
            "Looting, and Abhorrent Oculus remain construction choices on this "
            "path.",
        ),
        GRIXIS_TEMPO_BOWMASTERS_FAMILY: (
            "grixis-tempo",
            "Owner mapped the reviewed Bowmasters and Expressive Iteration "
            "singleton to existing Grixis Tempo. The supplemental path requires "
            "at least three main-deck Dragon's Rage Channeler, Expressive "
            "Iteration, and Thoughtseize, at least two Orcish Bowmasters, Watery "
            "Grave, and Steam Vents, permits at most two Psychic Frog, and excludes "
            "Goryo's Vengeance, Persist, Death's Shadow, and reviewed white and "
            "green main-deck mana sources.",
        ),
        RAKDOS_PROWESS_FAMILY: (
            "prowess/rakdos",
            "Owner mapped the reviewed Rakdos Cutter singleton to existing Prowess "
            "with a new Rakdos subtype rather than Rakdos Steel-Cutter. The rule "
            "requires at least three main-deck Cori-Steel Cutter, Lava Dart, "
            "Dragon's Rage Channeler, and Monastery Swiftspear plus Blood Crypt "
            "and a black spell in either zone; it excludes white, blue, and green "
            "spells in either zone and Nethergoyf so Mardu, Grixis, and Rakdos "
            "Steel-Cutter remain separate.",
        ),
        BOROS_PONZA_CLASSIC_FAMILY: (
            "boros-land-destruction",
            "Owner mapped the reviewed classic Boom/Bust singleton to existing "
            "Boros Ponza. The supplemental path requires at least three main-deck "
            "Boom/Bust, Flagstones of Trokair, Pillage, and Stone Rain; Molten Rain "
            "and the remaining land-destruction package remain construction "
            "choices.",
        ),
        GRIXIS_TEMPO_COUNTERSPELL_FAMILY: (
            "grixis-tempo",
            "Owner mapped the reviewed Counterspell and Ragavan singleton to "
            "existing Grixis Tempo. The supplemental path requires at least three "
            "main-deck Psychic Frog, Ragavan, Nimble Pilferer, and Counterspell plus "
            "Watery Grave and Steam Vents, permits at most two Fatal Push, and "
            "excludes Goryo's Vengeance, Persist, Death's Shadow, and reviewed white "
            "and green main-deck mana sources.",
        ),
        GRIXIS_TEMPO_DRC_FROG_FAMILY: (
            "grixis-tempo",
            "Owner mapped the reviewed Dragon's Rage Channeler and Psychic Frog "
            "singleton to existing Grixis Tempo. The supplemental path requires at "
            "least three main-deck Psychic Frog, Dragon's Rage Channeler, and Fatal "
            "Push plus Watery Grave and Steam Vents, permits at most two Ragavan, "
            "and excludes Goryo's Vengeance, Persist, Death's Shadow, and reviewed "
            "white and green main-deck mana sources.",
        ),
    }
    for family_id, (target_identity, rationale) in batch1_expected.items():
        expected = {
            "family_id": family_id,
            "review_status": "owner_accepted",
            "disposition": "map_existing",
            "target_identity": target_identity,
            "rationale": rationale,
            "owner_accepted": True,
        }
        if accepted.get(family_id) != expected:
            raise ValueError(f"{family_id} disposition is not the accepted decision")

    batch2_expected = {
        IZZET_EXTRA_TURNS_FAMILY: (
            "izzet-extra-turns",
            "Owner identified the singleton as Izzet Extra Turns. The reviewed "
            "mainboard rule requires at least three Tablet of Discovery, Time "
            "Warp, and Temporal Mastery plus reviewed blue and red mana sources; "
            "reviewed white, black, and green main-deck sources and any-zone "
            "spells are excluded so future off-color builds return to Unknown for "
            "explicit review.",
        ),
        JUND_GOBLINS_FAMILY: (
            "jund-goblins",
            "Owner identified the singleton as Jund Goblins. The reviewed "
            "mainboard rule requires at least three Birthing Ritual, Ignoble "
            "Hierarch, and Conspicuous Snoop plus Blood Crypt and Stomping Ground; "
            "the remaining Goblin combo, tutor, and interaction package remains a "
            "construction choice.",
        ),
        THOPTER_SWORD_BANT_FAMILY: (
            "thopter-sword/bant",
            "Owner identified the singleton as Bant Thopter Sword. The new Thopter "
            "Sword parent has a Bant subtype whose reviewed mainboard rule requires "
            "at least three Thopter Foundry and Malevolent Rumble, two Sword of the "
            "Meek, and one Breeding Pool and Hallowed Fountain; Urza, Emry, Mox "
            "Opal, Whir of Invention, and the remaining artifact package remain "
            "construction choices.",
        ),
        RAKDOS_AGGRO_FAMILY: (
            "rakdos-aggro",
            "Owner identified the singleton as Rakdos Aggro rather than Death's "
            "Shadow or Rakdos Delirium. The reviewed mainboard rule requires at "
            "least three Super Shredder, Moonshadow, and Ragavan, Nimble Pilferer "
            "plus Blood Crypt; Dragon's Rage Channeler, Street Wraith, Stalactite "
            "Stalker, and the interaction package remain construction choices.",
        ),
        PRIMAL_PRAYERS_RECRUITER_FAMILY: (
            "primal-prayers-combo",
            "Owner identified the singleton as Primal Prayers Combo. The shared "
            "reviewed mainboard rule requires at least three Primal Prayers, Guide "
            "of Souls, and Ocelot Pride, giving the combo identity priority over "
            "Energy; Acererak, Greenbelt Rampager, Formidable Speaker, tutor "
            "packages, and the remaining payoff cards remain construction choices.",
        ),
        NAYA_MIDRANGE_FAMILY: (
            "naya-midrange",
            "Owner identified the singleton as Naya Midrange. The reviewed "
            "mainboard rule requires at least three Ragavan, Nimble Pilferer and "
            "Phlage, Titan of Fire's Fury, at least two Wrenn and Six, and reviewed "
            "white, red, and green mana sources; Solitude, Malevolent Rumble, The "
            "Legend of Roku, and the interaction package remain construction "
            "choices.",
        ),
        FIVE_COLOR_ELEMENTALS_FAMILY: (
            "five-color-elementals",
            "Owner identified the singleton as Five-Color Elementals rather than "
            "Five-Color Ritual. The reviewed mainboard rule requires at least three "
            "Birthing Ritual, Omnath, Locus of Creation, and Risen Reef and excludes "
            "Shardless Agent; Voice of Resurgence, Solitude, Psychic Frog, "
            "Ephemerate, and the remaining Elemental package remain construction "
            "choices.",
        ),
        CHEERIOS_FAMILY: (
            "cheerios",
            "Owner identified the singleton as Cheerios. The reviewed mainboard "
            "rule requires at least three Sram, Senior Edificer, Bone Saw, and Kite "
            "Shield; Puresteel Paladin, Retract, Mox Opal, the remaining zero-cost "
            "equipment, and the single Colossus Hammer remain construction choices.",
        ),
        SHAPE_ANEW_FAMILY: (
            "shape-anew",
            "Owner directed all reviewed Shape Anew builds into one parent for now. "
            "The minimal mainboard rule therefore requires at least three Shape "
            "Anew and does not constrain the artifact payoff, color combination, "
            "or surrounding control and value shell.",
        ),
        GLIMPSE_OF_TOMORROW_FAMILY: (
            "glimpse-of-tomorrow",
            "Owner identified the singleton as Glimpse of Tomorrow. The minimal "
            "mainboard rule requires at least three Glimpse of Tomorrow and does "
            "not constrain the cascade enablers, colors, Elemental package, or "
            "payoff configuration.",
        ),
        PRIMAL_PRAYERS_ZENITH_FAMILY: (
            "primal-prayers-combo",
            "Owner identified the singleton as Primal Prayers Combo. The shared "
            "reviewed mainboard rule requires at least three Primal Prayers, Guide "
            "of Souls, and Ocelot Pride, giving the combo identity priority over "
            "Energy; Acererak, Greenbelt Rampager, Formidable Speaker, tutor "
            "packages, and the remaining payoff cards remain construction choices.",
        ),
        IZZET_CAULDRON_FAMILY: (
            "izzet-cauldron",
            "Owner identified the singleton as Izzet Cauldron. The reviewed "
            "mainboard rule requires at least three Vivi Ornitier and Agatha's Soul "
            "Cauldron; Fear of Missing Out, Marauding Mako, Walking Ballista, "
            "Proft's Eidetic Memory, and the remaining Izzet shell remain "
            "construction choices.",
        ),
    }
    for family_id, (target_identity, rationale) in batch2_expected.items():
        expected = {
            "family_id": family_id,
            "review_status": "owner_accepted",
            "disposition": "new_identity",
            "target_identity": target_identity,
            "rationale": rationale,
            "owner_accepted": True,
        }
        if accepted.get(family_id) != expected:
            raise ValueError(f"{family_id} disposition is not the accepted decision")

    rakdos_delirium_rationale = (
        "Owner identified both reviewed singletons as Rakdos Delirium rather "
        "than Hollow One, Rakdos Steel-Cutter, or Death's Shadow. The shared "
        "reviewed mainboard rule requires at least three Nethergoyf, Dragon's "
        "Rage Channeler, Fear of Missing Out, Moonshadow, and Mishra's Bauble, "
        "at least two Detective's Phoenix, and Blood Crypt; Hollow One, "
        "Cori-Steel Cutter, and Death's Shadow are excluded to preserve those "
        "established identities."
    )
    batch3_expected = {
        DIMIR_PERSIST_FAMILY: (
            "dimir-persist",
            "Owner identified the singleton as Dimir Persist and accepted a "
            "color-bounded parent separate from Grixis, Esper, Rakdos, Sultai, "
            "Agadeem, and Domain Persist. The reviewed mainboard rule requires "
            "at least three Persist, Archon of Cruelty, and Psychic Frog plus "
            "Watery Grave, while reviewed white, red, and green main-deck "
            "sources and any-zone spells are excluded.",
        ),
        DOMAIN_PERSIST_FAMILY: (
            "domain-persist",
            "Owner identified the singleton and two structurally equivalent "
            "lists previously selected as Domain Zoo as Domain Persist. The "
            "reviewed mainboard rule requires at least three Persist, Archon of "
            "Cruelty, Leyline of the Guildpact, and Scion of Draco and has "
            "priority over Domain Zoo; the reanimation identity therefore wins "
            "when both rules match.",
        ),
        SULTAI_FLICKER_FAMILY: (
            "sultai-flicker",
            "Owner identified the singleton as Sultai Flicker. The reviewed "
            "mainboard rule requires at least three Ghostly Flicker, Drowner of "
            "Truth, and Psychic Frog plus Breeding Pool and Watery Grave; "
            "reviewed white and red main-deck sources and any-zone spells are "
            "excluded so future off-color builds return to Unknown for explicit "
            "review.",
        ),
        AZORIUS_MIRACLES_FAMILY: (
            "azorius-miracles",
            "Owner identified Brainsurge and Terminus as the higher-priority "
            "identity even when a list also carries the Orim's Chant and "
            "Isochron Scepter package. The reviewed mainboard rule requires at "
            "least three Brainsurge and Terminus plus Hallowed Fountain and "
            "therefore moves seven structurally matching Chant Control lists "
            "into Azorius Miracles along with the reviewed Unknown.",
        ),
        DOMAIN_BLINK_FAMILY: (
            "domain-blink",
            "Owner identified the singleton as Domain Blink. The reviewed "
            "mainboard rule requires at least three Phelia, Exuberant Shepherd, "
            "Leyline Binding, and Overlord of the Balemurk; Phlage, Quantum "
            "Riddler, Ragavan, Emperor of Bones, and the surrounding removal and "
            "value package remain construction choices.",
        ),
        RAKDOS_DELIRIUM_PHOENIX_FAMILY: (
            "rakdos-delirium",
            rakdos_delirium_rationale,
        ),
        FIVE_COLOR_HUMANS_FAMILY: (
            "five-color-humans",
            "Owner identified the singleton as Five-Color Humans, separate from "
            "Mono-White Humans. The reviewed mainboard rule requires at least "
            "three Aether Vial, Champion of the Parish, Thalia's Lieutenant, "
            "Cavern of Souls, Secluded Courtyard, and Meddling Mage; the "
            "remaining multicolor Human package remains a construction choice.",
        ),
        RAKDOS_DELIRIUM_CASEY_FAMILY: (
            "rakdos-delirium",
            rakdos_delirium_rationale,
        ),
    }
    for family_id, (target_identity, rationale) in batch3_expected.items():
        expected = {
            "family_id": family_id,
            "review_status": "owner_accepted",
            "disposition": "new_identity",
            "target_identity": target_identity,
            "rationale": rationale,
            "owner_accepted": True,
        }
        if accepted.get(family_id) != expected:
            raise ValueError(f"{family_id} disposition is not the accepted decision")

    dimir_unearth_rationale = (
        "Owner identified both reviewed singletons and the structurally matching "
        "Dimir Tempo records as Dimir Unearth. The shared reviewed mainboard rule "
        "requires at least three Abhorrent Oculus, Unearth, Thought Scour, and "
        "Psychic Frog plus Watery Grave; Birthing Ritual, Goryo's Vengeance, and "
        "Persist are excluded. White splash cards remain permitted because the "
        "reanimation engine defines the parent."
    )
    batch4_expected = {
        DIMIR_UNEARTH_WHITE_SPLASH_FAMILY: (
            "dimir-unearth",
            dimir_unearth_rationale,
        ),
        DIMIR_UNEARTH_DIMIR_FAMILY: (
            "dimir-unearth",
            dimir_unearth_rationale,
        ),
        DIMIR_GORYOS_FAMILY: (
            "dimir-goryos",
            "Owner identified the singleton as Dimir Goryo's, separate from "
            "Esper, Grixis, Golgari, and Cremator Goryo's. The reviewed mainboard "
            "rule requires at least three Goryo's Vengeance, Atraxa, Grand "
            "Unifier, and Psychic Frog plus Watery Grave and no reviewed white, "
            "red, or green main-deck mana source. Atraxa prevents a general "
            "off-color spell exclusion; Griselbrand, Tainted Indulgence, Quantum "
            "Riddler, and the remaining interaction package remain construction "
            "choices.",
        ),
        IZZET_TEMPO_FAMILY: (
            "izzet-tempo",
            "Owner identified the singleton as Izzet Tempo, separate from the "
            "existing Grixis Tempo parent. The reviewed mainboard rule requires "
            "at least three Ragavan, Nimble Pilferer, Counterspell, and Tamiyo, "
            "Inquisitive Student plus Steam Vents, excludes Psychic Frog, and "
            "excludes reviewed white, black, and green main-deck sources and "
            "any-zone spells. Murktide Regent, Fable of the Mirror-Breaker, Flow "
            "State, Quantum Riddler, and the remaining interaction package remain "
            "construction choices.",
        ),
        RAKDOS_MIDRANGE_FAMILY: (
            "rakdos-midrange",
            "Owner identified the singleton as Rakdos Midrange, separate from "
            "Rakdos Aggro, Rakdos Delirium, and Death's Shadow. The reviewed "
            "mainboard rule requires at least three Ragavan, Nimble Pilferer, "
            "Dauthi Voidwalker, Orcish Bowmasters, Seasoned Pyromancer, and "
            "Thoughtseize plus Blood Crypt. Fable of the Mirror-Breaker, Kroxa, "
            "The Legend of Roku, and the removal mix remain construction choices.",
        ),
        YAWGMOTH_ENERGY_FAMILY: (
            "yawgmoth-energy",
            "Owner identified the singleton as Yawgmoth Energy, separate from "
            "traditional Golgari Yawgmoth and Selesnya Energy. The reviewed "
            "mainboard rule requires at least two Yawgmoth, Thran Physician and "
            "at least three Guide of Souls, Ocelot Pride, Young Wolf, and Birthing "
            "Ritual. Chord of Calling, Badgermole Cub, the tutor targets, and the "
            "remaining Energy package remain construction choices; the existing "
            "three-Yawgmoth rules remain unchanged.",
        ),
        SULTAI_TEMPO_FAMILY: (
            "sultai-tempo",
            "Owner identified the singleton as Sultai Tempo. The reviewed "
            "mainboard rule requires at least three Ice-Fang Coatl, Counterspell, "
            "and Fatal Push plus Breeding Pool and Watery Grave, excludes "
            "Abhorrent Oculus and Birthing Ritual, and excludes reviewed white "
            "and red main-deck sources and any-zone spells. Orcish Bowmasters, "
            "Grist, Witherbloom Charm, Psychic Frog, and the remaining interaction "
            "package remain construction choices.",
        ),
        SOLEMNITY_BLINK_FAMILY: (
            "solemnity-blink",
            "Owner identified the singleton as Solemnity Blink, separate from "
            "Solemnity Prison and Mardu Blink. The reviewed mainboard rule "
            "requires at least three Solemnity, Overlord of the Balemurk, and "
            "Solitude plus at least two Phelia, Exuberant Shepherd, and excludes "
            "Nine Lives and Phyrexian Unlife. Luminous Broodmoth, Persist, Emperor "
            "of Bones, Ketramose, and the remaining Mardu value package remain "
            "construction choices.",
        ),
        MONO_BLACK_SAGA_FAMILY: (
            "mono-black-saga",
            "Owner identified the singleton as Mono-Black Saga and accepted a "
            "lowest-priority fallback parent. The reviewed mainboard rule requires "
            "at least three Urza's Saga, Nethergoyf, Mishra's Bauble, and "
            "Thoughtseize plus at least four Swamp; Death's Shadow, Dragon's Rage "
            "Channeler, Fear of Missing Out, Moonshadow, Cori-Steel Cutter, "
            "Necrodominance, and reviewed nonblack spells are excluded. "
            "Black-producing fetch targets remain permitted, and every established "
            "identity retains precedence.",
        ),
    }
    for family_id, (target_identity, rationale) in batch4_expected.items():
        expected = {
            "family_id": family_id,
            "review_status": "owner_accepted",
            "disposition": "new_identity",
            "target_identity": target_identity,
            "rationale": rationale,
            "owner_accepted": True,
        }
        if accepted.get(family_id) != expected:
            raise ValueError(f"{family_id} disposition is not the accepted decision")

    shadow = deepcopy(production)
    proposal_order = sorted(accepted)
    proposal_order.remove(BADGERMOLE_LANDFALL_FAMILY)
    badgermole_index = proposal_order.index(BADGERMOLE_FAMILY)
    proposal_order.insert(badgermole_index + 1, BADGERMOLE_LANDFALL_FAMILY)
    grixis_expansion_families = [
        GRIXIS_TEMPO_BOWMASTERS_FAMILY,
        GRIXIS_TEMPO_COUNTERSPELL_FAMILY,
        GRIXIS_TEMPO_DRC_FROG_FAMILY,
    ]
    for family_id in grixis_expansion_families:
        proposal_order.remove(family_id)
    grixis_tempo_index = proposal_order.index(GRIXIS_TEMPO_FAMILY)
    for offset, family_id in enumerate(grixis_expansion_families, start=1):
        proposal_order.insert(grixis_tempo_index + offset, family_id)
    for family_id in proposal_order:
        PROPOSAL_HANDLERS[family_id](shadow)
    return shadow


def render_shadow_rules(root: Path = ROOT) -> str:
    production_path = root / "my_archetypes" / "modern.yaml"
    production_text = production_path.read_text(encoding="utf-8")
    yaml_start = production_text.index("schema_version:")
    header = production_text[:yaml_start]
    return header + yaml.safe_dump(
        build_shadow_rules(root),
        allow_unicode=True,
        sort_keys=False,
        width=1000,
    )


def write_shadow_rules(root: Path = ROOT) -> Path:
    destination = (
        root / "docs" / "audits" / "classifier-r4" / "shadow_rules" / "modern.yaml"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        render_shadow_rules(root),
        encoding="utf-8",
        newline="\n",
    )
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.write:
        print(write_shadow_rules(ROOT).relative_to(ROOT).as_posix())
    else:
        print(yaml.safe_dump(build_shadow_rules(ROOT), sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
