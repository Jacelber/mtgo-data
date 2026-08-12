"""Build non-production Standard R4 rules for Owner-accepted dispositions."""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "CLASSIFIER-R4-RESIDUAL-UNKNOWN-REVIEW"
R3_BASE_COMMIT = "7bf804684ac22dcf71560bacae4d3bc49c56f08f"
PRODUCTION_STANDARD_SHA256 = (
    "d88c3342826343f07442c37d4652b4caac5be7f690d21122fc31884b63eb37f5"
)

ORZHOV_LIFEGAIN_FAMILY = "standard-unknown-f6886bc730fa"
FIVE_COLOR_HUMANS_FAMILY = "standard-unknown-c43b77e5471b"
MONO_GREEN_MIGHTIEST_FAMILY = "standard-unknown-d85fc6cf3b8c"
SULTAI_CONTROL_FAMILY = "standard-unknown-e37c34297664"
AZORIUS_ESPER_CONTROL_FAMILY = "standard-unknown-1f3d3090fe62"
GOLGARI_REANIMATOR_FAMILY = "standard-unknown-26e1af626a7c"
AZORIUS_PROWESS_FAMILY = "standard-unknown-d2042f54ff9c"
ESPER_PIXIE_FAMILY = "standard-unknown-0b41ac5d43e0"
SULTAI_MIDRANGE_FAMILY = "standard-unknown-399088e97304"
MONO_WHITE_TRIUMPH_FAMILY = "standard-unknown-3e29fa6db392"
IZZET_BURN_FAMILY = "standard-unknown-41c8778fbc1e"
SIMIC_RHYTHM_SQUIRREL_FAMILY = "standard-unknown-5275c620d655"
MONO_GREEN_SQUIRREL_FAMILY = "standard-unknown-8d99d7fdb83d"
TEMUR_HULK_RAMP_FAMILY = "standard-unknown-b847e758d50c"
AZORIUS_AURAS_FAMILY = "standard-unknown-bd5d86377a0e"
BANT_AIRBENDING_FAMILY = "standard-unknown-d7f0c982b6a7"

SINGLETON_DECISIONS = {
    "standard-unknown-0857720282a4": ("new_identity", "selesnya-ramp"),
    "standard-unknown-0cbae9644068": ("map_existing", "boros-burn"),
    "standard-unknown-115a1eb783c9": ("new_identity", "azorius-cage"),
    "standard-unknown-115bb2d40b87": ("new_identity", "white-weenie"),
    "standard-unknown-14e962276abd": ("map_existing", "boros-token"),
    "standard-unknown-18e903160e16": ("new_identity", "golgari-sacrifice"),
    "standard-unknown-242b3816824a": ("new_identity", "mono-blue-namor"),
    "standard-unknown-42ba8896c962": ("map_existing", "boros-token"),
    "standard-unknown-465ced1c0787": ("new_identity", "dimir-oculus"),
    "standard-unknown-546deaf24038": ("new_identity", "sultai-oculus"),
    "standard-unknown-5488cd49501c": ("map_existing", "temur-otters"),
    "standard-unknown-54989a313da5": ("new_identity", "azorius-token-control"),
    "standard-unknown-568d48ce3fef": ("intentional_unknown", "unknown"),
    "standard-unknown-5cb23228136a": ("map_existing", "mono-black-aggro"),
    "standard-unknown-6b0bfc1c3537": ("map_existing", "izzet-lessons"),
    "standard-unknown-71c89735d78a": ("map_existing", "mono-black-demons"),
    "standard-unknown-79d9648ddef1": ("new_identity", "gruul-monsters"),
    "standard-unknown-7aed5a7501d9": ("new_identity", "izzet-iron-man"),
    "standard-unknown-7e295c544d07": ("new_identity", "rakdos-ponza"),
    "standard-unknown-7f6bed1d356c": ("map_existing", "golgari-midrange"),
    "standard-unknown-830e01106c19": ("map_existing", "orzhov-control"),
    "standard-unknown-8524a65d8f73": ("map_existing", "mono-black-demons"),
    "standard-unknown-867164f5dbc4": ("map_existing", "sultai-midrange"),
    "standard-unknown-8784b67a44bd": ("new_identity", "dimir-flash"),
    "standard-unknown-8d24e522f051": ("map_existing", "orzhov-control"),
    "standard-unknown-9505d82a2ea3": ("new_identity", "gruul-ramp"),
    "standard-unknown-96321e1721cb": ("new_identity", "dimir-oculus"),
    "standard-unknown-9c3d83efcf2a": ("map_existing", "azorius-momo"),
    "standard-unknown-9efdb7d63014": ("new_identity", "orzhov-demon"),
    "standard-unknown-ae068aea323a": ("map_existing", "boros-token"),
    "standard-unknown-b05defd59bf9": ("new_identity", "gruul-dinosaur"),
    "standard-unknown-b2752e143f9b": ("map_existing", "temur-elementals"),
    "standard-unknown-b322d579e883": ("map_existing", "golgari-crime"),
    "standard-unknown-b4dd6c01de05": ("new_identity", "mono-white-auras"),
    "standard-unknown-be4503b245f3": ("new_identity", "jeskai-equipment"),
    "standard-unknown-cb47b3fd754a": ("map_existing", "white-sultai-control"),
    "standard-unknown-ce41fdb9a299": ("new_identity", "orzhov-momo"),
    "standard-unknown-d35bb31f0714": ("map_existing", "rakdos-discard"),
    "standard-unknown-dae51c5571ba": ("map_existing", "golgari-crime"),
    "standard-unknown-ddce99be6026": ("new_identity", "gruul-ramp"),
    "standard-unknown-f283503ba493": ("new_identity", "break-out-aggro"),
    "standard-unknown-f68bfee8c56f": ("map_existing", "jeskai-control"),
    "standard-unknown-fa7d763a076f": ("new_identity", "mono-red-burn"),
}


def _read_mapping(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a mapping")
    return value


def _accepted_families(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "docs" / "audits" / "classifier-r4" / "standard_dispositions.yaml"
    document = _read_mapping(path)
    if (
        document.get("task_id") != TASK_ID
        or document.get("format") != "standard"
        or document.get("scope") != "non_production_shadow"
        or document.get("base_commit") != R3_BASE_COMMIT
    ):
        raise ValueError(f"{path}: unexpected Standard R4 disposition identity")
    families = document.get("families")
    if not isinstance(families, list):
        raise ValueError(f"{path}: families must be a list")
    accepted = {
        item["family_id"]: item
        for item in families
        if isinstance(item, dict)
        and item.get("review_status") == "owner_accepted"
        and item.get("owner_accepted") is True
        and item.get("disposition")
        in {"map_existing", "new_identity", "intentional_unknown"}
    }
    expected = {
        ORZHOV_LIFEGAIN_FAMILY: ("new_identity", "orzhov-lifegain"),
        FIVE_COLOR_HUMANS_FAMILY: ("new_identity", "five-color-humans"),
        MONO_GREEN_MIGHTIEST_FAMILY: ("new_identity", "mono-green-mightiest"),
        SULTAI_CONTROL_FAMILY: ("map_existing", "sultai-control"),
        AZORIUS_ESPER_CONTROL_FAMILY: (
            "new_identity",
            "azorius-control|esper-control",
        ),
        GOLGARI_REANIMATOR_FAMILY: ("map_existing", "golgari-reanimator"),
        AZORIUS_PROWESS_FAMILY: ("new_identity", "azorius-prowess"),
        ESPER_PIXIE_FAMILY: ("map_existing", "esper-pixie"),
        SULTAI_MIDRANGE_FAMILY: ("new_identity", "sultai-midrange"),
        MONO_WHITE_TRIUMPH_FAMILY: ("new_identity", "mono-white-triumph"),
        IZZET_BURN_FAMILY: ("new_identity", "izzet-burn"),
        SIMIC_RHYTHM_SQUIRREL_FAMILY: ("map_existing", "simic-rhythm"),
        MONO_GREEN_SQUIRREL_FAMILY: (
            "new_identity",
            "mono-green-squirrel-combo",
        ),
        TEMUR_HULK_RAMP_FAMILY: ("new_identity", "temur-hulk-ramp"),
        AZORIUS_AURAS_FAMILY: ("new_identity", "azorius-auras"),
        BANT_AIRBENDING_FAMILY: ("map_existing", "bant-airbending"),
        **SINGLETON_DECISIONS,
    }
    observed = {
        family_id: (item.get("disposition"), item.get("target_identity"))
        for family_id, item in accepted.items()
    }
    if observed != expected:
        raise ValueError("Standard R4 dispositions are not the accepted decisions")
    return accepted


def _insert_parent(document: dict[str, Any], parent: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Standard production rules have no archetype list")
    if any(item.get("id") == parent["id"] for item in archetypes):
        raise ValueError(f"{parent['id']} already exists")
    archetypes.append(parent)


def _add_orzhov_lifegain(document: dict[str, Any]) -> None:
    _insert_parent(
        document,
        {
            "id": "orzhov-lifegain",
            "name": "Orzhov Lifegain",
            "priority": 77000,
            "rules": [
                {
                    "id": "orzhov-lifegain-primary",
                    "priority": 77000,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Amalia Benavides Aguirre",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Case of the Uneaten Feast",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Hinterland Sanctifier",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Lunar Convocation",
                                "zone": "main",
                                "min_count": 2,
                            },
                            {"card": "Godless Shrine", "zone": "main", "min_count": 2},
                        ]
                    },
                }
            ],
        },
    )


def _add_five_color_humans(document: dict[str, Any]) -> None:
    _insert_parent(
        document,
        {
            "id": "five-color-humans",
            "name": "Five-Color Humans",
            "priority": 25990,
            "rules": [
                {
                    "id": "five-color-humans-primary",
                    "priority": 25990,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {"card": "Cavern of Souls", "zone": "main", "min_count": 4},
                            {
                                "card": "Secluded Courtyard",
                                "zone": "main",
                                "min_count": 4,
                            },
                            {
                                "card": "Celestial Reunion",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Cecil, Dark Knight",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Spectacular Spider-Man",
                                "zone": "main",
                                "min_count": 2,
                            },
                            {
                                "card": "Arachne, Psionic Weaver",
                                "zone": "main",
                                "min_count": 2,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_mono_green_mightiest(document: dict[str, Any]) -> None:
    _insert_parent(
        document,
        {
            "id": "mono-green-mightiest",
            "name": "Mono-Green Mightiest",
            "priority": 76900,
            "rules": [
                {
                    "id": "mono-green-mightiest-primary",
                    "priority": 76900,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Earth's Mightiest Heroes",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Craterhoof Behemoth",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {"card": "Ouroboroid", "zone": "main", "min_count": 3},
                            {
                                "card": "Spider Manifestation",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {"card": "Forest", "zone": "main", "min_count": 12},
                            {"card": "Nature's Rhythm", "zone": "main", "max_count": 1},
                        ]
                    },
                }
            ],
        },
    )


def _add_sultai_control_path(document: dict[str, Any]) -> None:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Standard production rules have no archetype list")
    matches = [item for item in archetypes if item.get("id") == "sultai-control"]
    if len(matches) != 1:
        raise ValueError("expected exactly one Sultai Control parent")
    parent = matches[0]
    rules = parent.get("rules")
    if not isinstance(rules, list) or any(
        rule.get("id") == "sultai-control-consult" for rule in rules
    ):
        raise ValueError("Sultai Control rules have an unexpected shape")
    parent["priority"] = 40010
    rules.append(
        {
            "id": "sultai-control-consult",
            "priority": 40010,
            "subtype_id": None,
            "conditions": {
                "all": [
                    {"card": "Consult the Star Charts", "zone": "main", "min_count": 3},
                    {"card": "Deadly Cover-Up", "zone": "main", "min_count": 3},
                    {"card": "Professor Dellian Fel", "zone": "main", "min_count": 2},
                    {"card": "Breeding Pool", "zone": "main", "min_count": 2},
                    {"card": "Watery Grave", "zone": "main", "min_count": 2},
                    {"card": "Overgrown Tomb", "zone": "main", "min_count": 1},
                    {
                        "card": "Unholy Annex // Ritual Chamber",
                        "zone": "main",
                        "max_count": 2,
                    },
                ]
            },
        }
    )


def _find_parent(document: dict[str, Any], parent_id: str) -> dict[str, Any]:
    archetypes = document.get("archetypes")
    if not isinstance(archetypes, list):
        raise ValueError("Standard production rules have no archetype list")
    matches = [item for item in archetypes if item.get("id") == parent_id]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {parent_id} parent")
    return matches[0]


def _add_control_paths(document: dict[str, Any]) -> None:
    azorius = _find_parent(document, "azorius-control")
    rules = azorius.get("rules")
    if not isinstance(rules, list) or any(
        rule.get("id") == "azorius-control-consult" for rule in rules
    ):
        raise ValueError("Azorius Control rules have an unexpected shape")
    rules.append(
        {
            "id": "azorius-control-consult",
            "priority": 38990,
            "subtype_id": None,
            "conditions": {
                "all": [
                    {"card": "Consult the Star Charts", "zone": "main", "min_count": 2},
                    {"card": "Day of Judgment", "zone": "main", "min_count": 3},
                    {"card": "Stock Up", "zone": "main", "min_count": 3},
                    {"card": "No More Lies", "zone": "main", "min_count": 2},
                    {"card": "Hallowed Fountain", "zone": "main", "min_count": 2},
                    {"card": "Jeskai Revelation", "zone": "any", "exact_count": 0},
                    {"card": "Ancient Vendetta", "zone": "any", "exact_count": 0},
                    {"card": "Swamp", "zone": "any", "exact_count": 0},
                ]
            },
        }
    )
    _insert_parent(
        document,
        {
            "id": "esper-control",
            "name": "Esper Control",
            "priority": 39010,
            "rules": [
                {
                    "id": "esper-control-consult",
                    "priority": 39010,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Consult the Star Charts",
                                "zone": "main",
                                "min_count": 2,
                            },
                            {"card": "Day of Judgment", "zone": "main", "min_count": 3},
                            {"card": "Stock Up", "zone": "main", "min_count": 3},
                            {"card": "No More Lies", "zone": "main", "min_count": 2},
                            {
                                "card": "Hallowed Fountain",
                                "zone": "main",
                                "min_count": 2,
                            },
                            {"card": "Ancient Vendetta", "zone": "any", "min_count": 1},
                            {"card": "Swamp", "zone": "main", "min_count": 1},
                            {
                                "card": "Jeskai Revelation",
                                "zone": "any",
                                "exact_count": 0,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_golgari_reanimator_path(document: dict[str, Any]) -> None:
    parent = _find_parent(document, "golgari-reanimator")
    rules = parent.get("rules")
    if not isinstance(rules, list) or any(
        rule.get("id") == "golgari-reanimator-faithful" for rule in rules
    ):
        raise ValueError("Golgari Reanimator rules have an unexpected shape")
    rules.append(
        {
            "id": "golgari-reanimator-faithful",
            "priority": 13990,
            "subtype_id": None,
            "conditions": {
                "all": [
                    {"card": "Valgavoth's Faithful", "zone": "main", "min_count": 3},
                    {"card": "Broodheart Engine", "zone": "main", "min_count": 3},
                    {"card": "Broodspinner", "zone": "main", "min_count": 3},
                ]
            },
        }
    )


def _add_azorius_prowess(document: dict[str, Any]) -> None:
    _insert_parent(
        document,
        {
            "id": "azorius-prowess",
            "name": "Azorius Prowess",
            "priority": 50990,
            "rules": [
                {
                    "id": "azorius-prowess-primary",
                    "priority": 50990,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {"card": "Elusive Otter", "zone": "main", "min_count": 3},
                            {
                                "card": "Stormchaser's Talent",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Practiced Offense",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Hallowed Fountain",
                                "zone": "main",
                                "min_count": 2,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _repair_esper_pixie(document: dict[str, Any]) -> None:
    parent = _find_parent(document, "esper-pixie")
    rules = parent.get("rules")
    if not isinstance(rules, list) or len(rules) != 1:
        raise ValueError("Esper Pixie rules have an unexpected shape")
    rule = rules[0]
    if rule.get("id") != "esper-pixie-primary":
        raise ValueError("Esper Pixie primary rule is missing")
    rule["conditions"] = {
        "all": [
            {"card": "Nurturing Pixie", "zone": "main", "min_count": 3},
            {"card": "Stormchaser's Talent", "zone": "main", "min_count": 3},
            {"card": "Hallowed Fountain", "zone": "main", "min_count": 2},
            {"card": "Watery Grave", "zone": "main", "min_count": 2},
        ]
    }


def _add_sultai_midrange(document: dict[str, Any]) -> None:
    _insert_parent(
        document,
        {
            "id": "sultai-midrange",
            "name": "Sultai Midrange",
            "priority": 65990,
            "rules": [
                {
                    "id": "sultai-midrange-primary",
                    "priority": 65990,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {"card": "Badgermole Cub", "zone": "main", "min_count": 3},
                            {
                                "card": "Icetill Explorer",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Overlord of the Balemurk",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {"card": "Esper Origins", "zone": "main", "min_count": 2},
                            {
                                "card": "Superior Spider-Man",
                                "zone": "main",
                                "min_count": 2,
                            },
                            {"card": "Breeding Pool", "zone": "main", "min_count": 2},
                        ]
                    },
                }
            ],
        },
    )


def _add_mono_white_triumph(document: dict[str, Any]) -> None:
    _insert_parent(
        document,
        {
            "id": "mono-white-triumph",
            "name": "Mono-White Triumph",
            "priority": 76920,
            "rules": [
                {
                    "id": "mono-white-triumph-primary",
                    "priority": 76920,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Political Triumph",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Cosmogrand Zenith",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Enduring Innocence",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Invasion Reinforcements",
                                "zone": "main",
                                "min_count": 3,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_izzet_burn(document: dict[str, Any]) -> None:
    _insert_parent(
        document,
        {
            "id": "izzet-burn",
            "name": "Izzet Burn",
            "priority": 63990,
            "rules": [
                {
                    "id": "izzet-burn-primary",
                    "priority": 63990,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {
                                "card": "Death to Our Enemies",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {"card": "Plasma Bolt", "zone": "main", "min_count": 3},
                            {"card": "Boltwave", "zone": "main", "min_count": 3},
                            {"card": "Steam Vents", "zone": "main", "min_count": 2},
                        ]
                    },
                }
            ],
        },
    )


def _repair_simic_rhythm(document: dict[str, Any]) -> None:
    parent = _find_parent(document, "simic-rhythm")
    rules = parent.get("rules")
    if not isinstance(rules, list) or len(rules) != 1:
        raise ValueError("Simic Rhythm rules have an unexpected shape")
    primary = rules[0]
    if primary.get("id") != "simic-rhythm-primary":
        raise ValueError("Simic Rhythm primary rule is missing")
    conditions = primary.get("conditions", {}).get("all")
    if not isinstance(conditions, list) or any(
        item.get("card") == "Breeding Pool" for item in conditions
    ):
        raise ValueError("Simic Rhythm primary conditions are unexpected")
    conditions.append({"card": "Breeding Pool", "zone": "main", "min_count": 2})
    parent["priority"] = 68010
    rules.append(
        {
            "id": "simic-rhythm-squirrel",
            "priority": 68010,
            "subtype_id": None,
            "conditions": {
                "all": [
                    {"card": "Badgermole Cub", "zone": "main", "min_count": 3},
                    {"card": "Nature's Rhythm", "zone": "main", "min_count": 2},
                    {"card": "Enduring Vitality", "zone": "main", "min_count": 3},
                    {
                        "card": "The Unbeatable Squirrel Girl",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {
                        "card": "Shang-Chi, Master of Kung Fu",
                        "zone": "main",
                        "min_count": 3,
                    },
                    {"card": "Breeding Pool", "zone": "main", "min_count": 2},
                ]
            },
        }
    )


def _add_mono_green_squirrel_combo(document: dict[str, Any]) -> None:
    _insert_parent(
        document,
        {
            "id": "mono-green-squirrel-combo",
            "name": "Mono-Green Squirrel Combo",
            "priority": 68020,
            "rules": [
                {
                    "id": "mono-green-squirrel-combo-primary",
                    "priority": 68020,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {"card": "Badgermole Cub", "zone": "main", "min_count": 3},
                            {"card": "Nature's Rhythm", "zone": "main", "min_count": 3},
                            {
                                "card": "Enduring Vitality",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "The Unbeatable Squirrel Girl",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {
                                "card": "Shang-Chi, Master of Kung Fu",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {"card": "Forest", "zone": "main", "min_count": 12},
                            {"card": "Breeding Pool", "zone": "main", "exact_count": 0},
                            {
                                "card": "Stomping Ground",
                                "zone": "main",
                                "exact_count": 0,
                            },
                            {"card": "Temple Garden", "zone": "main", "exact_count": 0},
                            {
                                "card": "Overgrown Tomb",
                                "zone": "main",
                                "exact_count": 0,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _add_temur_hulk_ramp(document: dict[str, Any]) -> None:
    _insert_parent(
        document,
        {
            "id": "temur-hulk-ramp",
            "name": "Temur Hulk Ramp",
            "priority": 67990,
            "rules": [
                {
                    "id": "temur-hulk-ramp-primary",
                    "priority": 67990,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {"card": "World War Hulk", "zone": "main", "min_count": 3},
                            {"card": "Shared Roots", "zone": "main", "min_count": 3},
                            {
                                "card": "Terror of the Peaks",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {"card": "Stomping Ground", "zone": "main", "min_count": 3},
                            {"card": "Island", "zone": "main", "min_count": 1},
                        ]
                    },
                }
            ],
        },
    )


def _add_azorius_auras(document: dict[str, Any]) -> None:
    _insert_parent(
        document,
        {
            "id": "azorius-auras",
            "name": "Azorius Auras",
            "priority": 67980,
            "rules": [
                {
                    "id": "azorius-auras-primary",
                    "priority": 67980,
                    "subtype_id": None,
                    "conditions": {
                        "all": [
                            {"card": "Ethereal Armor", "zone": "main", "min_count": 3},
                            {
                                "card": "Super Intelligence",
                                "zone": "main",
                                "min_count": 3,
                            },
                            {"card": "Skyward Spider", "zone": "main", "min_count": 3},
                            {
                                "card": "Hallowed Fountain",
                                "zone": "main",
                                "min_count": 2,
                            },
                        ]
                    },
                }
            ],
        },
    )


def _repair_bant_airbending(document: dict[str, Any]) -> None:
    parent = _find_parent(document, "bant-airbending")
    rules = parent.get("rules")
    if not isinstance(rules, list) or len(rules) != 1:
        raise ValueError("Bant Airbending rules have an unexpected shape")
    rule = rules[0]
    if rule.get("id") != "bant-airbending-primary":
        raise ValueError("Bant Airbending primary rule is missing")
    rule["conditions"] = {
        "all": [
            {"card": "Aang, Swift Savior", "zone": "main", "min_count": 3},
            {"card": "Appa, Steadfast Guardian", "zone": "main", "min_count": 3},
            {"card": "Doc Aurlock, Grizzled Genius", "zone": "main", "min_count": 3},
        ]
    }


def _card(
    name: str,
    *,
    zone: str = "main",
    minimum: int | None = None,
    maximum: int | None = None,
    exact: int | None = None,
) -> dict[str, Any]:
    condition: dict[str, Any] = {"card": name, "zone": zone}
    if minimum is not None:
        condition["min_count"] = minimum
    if maximum is not None:
        condition["max_count"] = maximum
    if exact is not None:
        condition["exact_count"] = exact
    return condition


def _rule(
    rule_id: str,
    priority: int,
    conditions: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": rule_id,
        "priority": priority,
        "subtype_id": None,
        "conditions": {"all": conditions},
    }


def _new_parent(
    document: dict[str, Any],
    parent_id: str,
    name: str,
    priority: int,
    rules: list[dict[str, Any]],
) -> None:
    _insert_parent(
        document,
        {"id": parent_id, "name": name, "priority": priority, "rules": rules},
    )


def _find_rule(parent: dict[str, Any], rule_id: str) -> dict[str, Any]:
    rules = parent.get("rules")
    if not isinstance(rules, list):
        raise ValueError(f"{parent.get('id')}: rules must be a list")
    for rule in rules:
        if rule.get("id") == rule_id:
            return rule
    raise ValueError(f"{parent.get('id')}: missing rule {rule_id}")


def _append_rule(parent: dict[str, Any], rule: dict[str, Any]) -> None:
    rules = parent.get("rules")
    if not isinstance(rules, list):
        raise ValueError(f"{parent.get('id')}: rules must be a list")
    if any(item.get("id") == rule["id"] for item in rules):
        raise ValueError(f"{rule['id']} already exists")
    rules.append(rule)


def _replace_conditions(
    document: dict[str, Any],
    parent_id: str,
    rule_id: str,
    conditions: list[dict[str, Any]],
) -> None:
    _find_rule(_find_parent(document, parent_id), rule_id)["conditions"] = {
        "all": conditions
    }


def _apply_standard_singleton_decisions(document: dict[str, Any]) -> None:
    # Direct Owner preclassifications.
    _new_parent(
        document,
        "selesnya-ramp",
        "Selesnya Ramp",
        76890,
        [_rule("selesnya-ramp-primary", 76890, [
            _card("Shared Roots", minimum=3),
            _card("Day of Judgment", minimum=3),
            _card("__classifier-semantic-main-blue-source__", exact=0),
            _card("__classifier-semantic-main-red-source__", exact=0),
            _card("__classifier-semantic-main-black-source__", exact=0),
        ])],
    )
    _append_rule(
        _find_parent(document, "boros-burn"),
        _rule("boros-burn-boltwave", 31990, [
            _card("Boltwave", minimum=3),
            _card("Boros Charm", minimum=3),
        ]),
    )
    _new_parent(document, "azorius-cage", "Azorius Cage", 76880, [
        _rule("azorius-cage-primary", 76880, [
            _card("Collector's Cage", minimum=3),
            _card("Hallowed Fountain", minimum=1),
            _card("Pawpatch Recruit", zone="any", exact=0),
        ])
    ])
    _new_parent(document, "white-weenie", "White Weenie", 76870, [
        _rule("white-weenie-primary", 76870, [
            _card("Lightstall Inquisitor", minimum=3),
            _card("Figure of Fable", minimum=3),
            _card("Suki, Courageous Rescuer", minimum=3),
        ])
    ])
    _new_parent(document, "golgari-sacrifice", "Golgari Sacrifice", 76860, [
        _rule("golgari-sacrifice-primary", 76860, [
            _card("Nezumi Linkbreaker", minimum=3),
            _card("Rottenmouth Viper", minimum=3),
        ])
    ])
    _new_parent(document, "mono-blue-namor", "Mono-Blue Namor", 76850, [
        _rule("mono-blue-namor-primary", 76850, [
            _card("Namor the Sub-Mariner", minimum=3),
            _card("Eluge, the Shoreless Sea", minimum=3),
        ])
    ])
    _new_parent(document, "dimir-oculus", "Dimir Oculus", 76840, [
        _rule("dimir-oculus-primary", 76840, [
            _card("Abhorrent Oculus", minimum=3),
            _card("Ral Zarek, Guest Lecturer", minimum=3),
            _card("Oblivious Bookworm", zone="any", exact=0),
        ])
    ])
    _new_parent(document, "sultai-oculus", "Sultai Oculus", 76830, [
        _rule("sultai-oculus-primary", 76830, [
            _card("Abhorrent Oculus", minimum=3),
            _card("Oblivious Bookworm", minimum=3),
            _card("Ral Zarek, Guest Lecturer", minimum=3),
        ])
    ])
    _append_rule(
        _find_parent(document, "temur-otters"),
        _rule("temur-otters-vitality-floodcaller", 24990, [
            _card("Enduring Vitality", minimum=3),
            _card("Valley Floodcaller", zone="any", minimum=3),
            _card("Song of Totentanz", zone="any", minimum=2),
        ]),
    )
    _new_parent(
        document,
        "azorius-token-control",
        "Azorius Token Control",
        76820,
        [_rule("azorius-token-control-primary", 76820, [
            _card("Caretaker's Talent", minimum=3),
            _card("Hallowed Fountain", minimum=2),
        ])],
    )
    _new_parent(document, "gruul-monsters", "Gruul Monsters", 76810, [
        _rule("gruul-monsters-primary", 76810, [
            _card("Axebane Ferox", minimum=3),
            _card("Nova Hellkite", minimum=3),
        ])
    ])
    _new_parent(document, "izzet-iron-man", "Izzet Iron Man", 76800, [
        _rule("izzet-iron-man-primary", 76800, [
            _card("Tony Stark", minimum=3),
            _card("Jace Reawakened", minimum=3),
        ])
    ])
    _new_parent(document, "rakdos-ponza", "Rakdos Ponza", 76790, [
        _rule("rakdos-ponza-primary", 76790, [
            _card("The Soul Stone", minimum=3),
            _card("Magmatic Hellkite", minimum=3),
        ])
    ])
    _new_parent(document, "dimir-flash", "Dimir Flash", 76780, [
        _rule("dimir-flash-primary", 76780, [
            _card("Brineborn Cutthroat", minimum=3),
            _card("Enduring Curiosity", minimum=3),
        ])
    ])
    _new_parent(document, "orzhov-demon", "Orzhov Demon", 76770, [
        _rule("orzhov-demon-primary", 76770, [
            _card("Unholy Annex // Ritual Chamber", minimum=3),
            _card("Godless Shrine", minimum=3),
        ])
    ])
    _new_parent(document, "gruul-dinosaur", "Gruul Dinosaur", 76760, [
        _rule("gruul-dinosaur-primary", 76760, [
            _card("Regal Imperiosaur", minimum=3),
            _card("Belligerent Yearling", minimum=3),
        ])
    ])

    # Owner-confirmed repairs and supplemental paths.
    _replace_conditions(document, "boros-token", "boros-token-primary", [
        _card("Voice of Victory", minimum=3),
        _card("Warleader's Call", minimum=3),
    ])
    _append_rule(
        _find_parent(document, "mono-black-aggro"),
        _rule("mono-black-aggro-corpses-banner", 9990, [
            _card("Swamp", minimum=14),
            _card("Forsaken Miner", minimum=3),
            _card("Corpses of the Lost", minimum=3),
            _card("Heraldic Banner", minimum=3),
        ]),
    )
    lessons = _find_rule(_find_parent(document, "izzet-lessons"), "izzet-lessons-primary")
    lesson_conditions = lessons["conditions"]["all"]
    next(item for item in lesson_conditions if item["card"] == "Firebending Lesson")["min_count"] = 3
    _replace_conditions(document, "mono-black-demons", "mono-black-demons-primary", [
        _card("Unholy Annex // Ritual Chamber", minimum=3),
        _card("Swamp", minimum=13),
    ])
    _append_rule(_find_parent(document, "golgari-midrange"), _rule(
        "golgari-midrange-badgermole-sentinel", 1990, [
            _card("Overgrown Tomb", minimum=2),
            _card("Blooming Marsh", minimum=2),
            _card("Badgermole Cub", minimum=3),
            _card("Sentinel of the Nameless City", minimum=3),
            _card("Nature's Rhythm", zone="any", exact=0),
            _card("Flow State", zone="any", exact=0),
            _card("Unholy Annex // Ritual Chamber", zone="any", maximum=1),
        ]
    ))
    orzhov_control = _find_parent(document, "orzhov-control")
    common_control = [
        _card("Ketramose, the New Dawn", zone="any", minimum=3),
        _card("Ghost Vacuum", zone="any", minimum=1),
    ]
    _append_rule(orzhov_control, _rule(
        "orzhov-control-day-of-judgment", 6995,
        [*common_control, _card("Day of Judgment", zone="any", minimum=3)],
    ))
    _append_rule(orzhov_control, _rule(
        "orzhov-control-deadly-cover-up", 6990,
        [*common_control, _card("Deadly Cover-Up", zone="any", minimum=2)],
    ))
    _append_rule(_find_parent(document, "sultai-midrange"), _rule(
        "sultai-midrange-hauntwoods-value", 12980, [
            _card("Llanowar Elves", minimum=3),
            _card("Overlord of the Hauntwoods", minimum=3),
            _card("Rakshasa's Bargain", minimum=3),
            _card("Breeding Pool", minimum=2),
            _card("Overgrown Tomb", minimum=2),
        ]
    ))
    momo_rule = _find_rule(_find_parent(document, "azorius-momo"), "azorius-momo-primary")
    next(item for item in momo_rule["conditions"]["all"] if item["card"] == "Springleaf Drum")["min_count"] = 2

    elementals = _find_parent(document, "temur-elementals")
    elementals["name"] = "Ramp Elementals"
    _replace_conditions(document, "temur-elementals", "temur-elementals-primary", [
        _card("Ashling, Rekindled", minimum=4),
        _card("Sunderflock", minimum=2),
        _card("Vibrance", minimum=2),
        _card("Flamebraider", minimum=2),
    ])
    archetypes = document["archetypes"]
    document["archetypes"] = [item for item in archetypes if item.get("id") != "grixis-elementals"]
    _replace_conditions(document, "golgari-crime", "golgari-crime-primary", [
        _card("Freestrider Lookout", minimum=4),
        _card("Ghost Vacuum", minimum=2),
    ])

    _new_parent(document, "mono-white-auras", "Mono-White Auras", 67970, [
        _rule("mono-white-auras-primary", 67970, [
            _card("Plains", minimum=13),
            _card("Ethereal Armor", minimum=3),
            _card("Optimistic Scavenger", minimum=3),
        ])
    ])
    _new_parent(document, "jeskai-equipment", "Jeskai Equipment", 67960, [
        _rule("jeskai-equipment-primary", 67960, [
            _card("The Mighty Thor, Jane Foster", minimum=3),
            _card("Cloud, Midgar Mercenary", minimum=1),
            _card("Mjölnir, Hammer of Thor", minimum=3),
        ])
    ])
    _append_rule(_find_parent(document, "white-sultai-control"), _rule(
        "white-sultai-control-hauntwoods", 13005, [
            _card("Consult the Star Charts", minimum=3),
            _card("Emeritus of Abundance", minimum=3),
            _card("Overlord of the Hauntwoods", minimum=3),
            _card("Watery Grave", minimum=2),
            _card("Overgrown Tomb", minimum=2),
            _card("Hallowed Fountain", minimum=1),
            _card("Get Lost", minimum=1),
        ]
    ))
    _new_parent(document, "orzhov-momo", "Orzhov Momo", 38010, [
        _rule("orzhov-momo-primary", 38010, [
            _card("Momo, Friendly Flier", minimum=3),
            _card("Sage of the Skies", minimum=2),
            _card("Godless Shrine", minimum=1),
        ])
    ])
    _replace_conditions(document, "rakdos-discard", "rakdos-discard-primary", [
        _card("Moonshadow", minimum=3),
        _card("Marauding Mako", minimum=3),
        _card("Quantum Riddler", zone="any", exact=0),
    ])
    _new_parent(document, "gruul-ramp", "Gruul Ramp", 67880, [
        _rule("gruul-ramp-tablet", 67880, [
            _card("Shared Roots", minimum=3),
            _card("Tablet of Discovery", minimum=3),
            _card("Stomping Ground", minimum=3),
            _card("__classifier-semantic-main-blue-source__", exact=0),
            _card("__classifier-semantic-main-white-source__", exact=0),
            _card("__classifier-semantic-main-black-source__", exact=0),
        ]),
        _rule("gruul-ramp-weather-maker", 67870, [
            _card("Shared Roots", minimum=3),
            _card("Weather Maker", minimum=3),
            _card("Stomping Ground", minimum=3),
            _card("__classifier-semantic-main-blue-source__", exact=0),
            _card("__classifier-semantic-main-white-source__", exact=0),
            _card("__classifier-semantic-main-black-source__", exact=0),
        ]),
    ])
    _new_parent(document, "break-out-aggro", "Break Out Aggro", 67950, [
        _rule("break-out-aggro-primary", 67950, [
            _card("Break Out", minimum=3),
            _card("Spider-Man 2099", minimum=3),
        ])
    ])
    _append_rule(_find_parent(document, "jeskai-control"), _rule(
        "jeskai-control-consult-helix", 56990, [
            _card("Consult the Star Charts", minimum=3),
            _card("No More Lies", minimum=2),
            _card("Lightning Helix", minimum=3),
            _card("Jeskai Revelation", zone="any", exact=0),
            _card("Inevitable Defeat", zone="any", exact=0),
        ]
    ))
    _new_parent(document, "mono-red-burn", "Mono-Red Burn", 67940, [
        _rule("mono-red-burn-primary", 67940, [
            _card("Death to Our Enemies", minimum=3),
            _card("Mountain", minimum=13),
        ])
    ])


def build_standard_shadow_rules(root: Path = ROOT) -> dict[str, Any]:
    _accepted_families(root)
    production_path = root / "my_archetypes" / "standard.yaml"
    if sha256(production_path.read_bytes()).hexdigest() != PRODUCTION_STANDARD_SHA256:
        raise ValueError("Standard production rules changed outside the R4 shadow")
    shadow = deepcopy(_read_mapping(production_path))
    _add_orzhov_lifegain(shadow)
    _add_five_color_humans(shadow)
    _add_mono_green_mightiest(shadow)
    _add_sultai_control_path(shadow)
    _add_control_paths(shadow)
    _add_golgari_reanimator_path(shadow)
    _add_azorius_prowess(shadow)
    _repair_esper_pixie(shadow)
    _add_sultai_midrange(shadow)
    _add_mono_white_triumph(shadow)
    _add_izzet_burn(shadow)
    _repair_simic_rhythm(shadow)
    _add_mono_green_squirrel_combo(shadow)
    _add_temur_hulk_ramp(shadow)
    _add_azorius_auras(shadow)
    _repair_bant_airbending(shadow)
    _apply_standard_singleton_decisions(shadow)
    return shadow


def render_standard_shadow_rules(root: Path = ROOT) -> str:
    return yaml.safe_dump(
        build_standard_shadow_rules(root),
        allow_unicode=True,
        sort_keys=False,
        width=1000,
    )


def write_standard_shadow_rules(root: Path = ROOT) -> Path:
    destination = (
        root / "docs" / "audits" / "classifier-r4" / "shadow_rules" / "standard.yaml"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        render_standard_shadow_rules(root), encoding="utf-8", newline="\n"
    )
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.write:
        print(write_standard_shadow_rules(ROOT).relative_to(ROOT).as_posix())
    else:
        print(yaml.safe_dump(build_standard_shadow_rules(ROOT), sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
