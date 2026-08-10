"""Build the accepted R2 shadow rule sets without editing production rules."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "docs" / "audits" / "classifier-r2" / "shadow_rules"
FEATURE_PREFIX = "__classifier-r2-"


def source(color: str) -> str:
    return f"{FEATURE_PREFIX}main-{color}-source__"


def spell(color: str) -> str:
    return f"{FEATURE_PREFIX}any-{color}-spell__"


EQUIPMENT = f"{FEATURE_PREFIX}main-equipment__"


def condition(
    card: str,
    *,
    zone: str = "main",
    min_count: int | None = None,
    max_count: int | None = None,
    exact_count: int | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {"card": card, "zone": zone}
    if min_count is not None:
        item["min_count"] = min_count
    if max_count is not None:
        item["max_count"] = max_count
    if exact_count is not None:
        item["exact_count"] = exact_count
    return item


def rule(
    rule_id: str,
    priority: int,
    conditions: list[dict[str, Any]],
    *,
    subtype_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": rule_id,
        "priority": priority,
        "subtype_id": subtype_id,
        "conditions": {"all": conditions},
    }


def parent(
    parent_id: str,
    name: str,
    rules: list[dict[str, Any]],
    *,
    subtypes: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": parent_id,
        "name": name,
        "priority": max(item["priority"] for item in rules),
    }
    if subtypes:
        result["subtypes"] = [
            {"id": subtype_id, "name": subtype_name}
            for subtype_id, subtype_name in subtypes
        ]
    result["rules"] = rules
    return result


def _load(format_id: str) -> dict[str, Any]:
    path = ROOT / "my_archetypes" / f"{format_id}.yaml"
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    for archetype in value["archetypes"]:
        for item in archetype["rules"]:
            item["priority"] *= 100
        archetype["priority"] = max(item["priority"] for item in archetype["rules"])
    return value


def _remove(data: dict[str, Any], *parent_ids: str) -> dict[str, dict[str, Any]]:
    removed = {
        item["id"]: item
        for item in data["archetypes"]
        if item["id"] in parent_ids
    }
    assert set(removed) == set(parent_ids)
    data["archetypes"] = [
        item for item in data["archetypes"] if item["id"] not in parent_ids
    ]
    return removed


def _replace(data: dict[str, Any], replacement: dict[str, Any]) -> None:
    for index, item in enumerate(data["archetypes"]):
        if item["id"] == replacement["id"]:
            data["archetypes"][index] = replacement
            return
    raise AssertionError(f"missing parent {replacement['id']}")


def _set_rule_priorities(
    data: dict[str, Any], parent_id: str, priorities: dict[str, int]
) -> None:
    archetype = next(item for item in data["archetypes"] if item["id"] == parent_id)
    rules = {item["id"]: item for item in archetype["rules"]}
    if set(priorities) != set(rules):
        raise AssertionError(f"unexpected rules while reprioritizing {parent_id}")
    for rule_id, priority in priorities.items():
        rules[rule_id]["priority"] = priority
    archetype["priority"] = max(priorities.values())


def _strict_sources(*allowed: str) -> list[dict[str, Any]]:
    return [
        condition(source(color), exact_count=0)
        for color in ("white", "blue", "black", "red", "green")
        if color not in allowed
    ]


def _modern() -> dict[str, Any]:
    data = _load("modern")

    # The accepted precedence places complete combo parents above the broad
    # Chant parent core, even when their historical numeric priorities were
    # lower. These are the only observed complete-combo overlaps in the frozen
    # corpus; their internal ordering is preserved.
    _set_rule_priorities(
        data,
        "mono-blue-belcher",
        {"mono-blue-belcher-primary": 306_300},
    )
    _set_rule_priorities(
        data,
        "boros-belcher",
        {
            "boros-belcher-primary": 306_100,
            "boros-belcher-ritual": 306_200,
        },
    )

    _remove(data, "persist-reanimator")
    data["archetypes"].extend(
        [
            parent(
                "grixis-persist",
                "Grixis Persist",
                [
                    rule(
                        "grixis-persist-primary",
                        639_900,
                        [
                            condition("Persist", min_count=3),
                            condition("Archon of Cruelty", min_count=3),
                            condition("Faithless Looting", min_count=3),
                            condition("Abhorrent Oculus", min_count=3),
                        ],
                    )
                ],
            ),
            parent(
                "agadeem-persist",
                "Agadeem Persist",
                [
                    rule(
                        "agadeem-persist-primary",
                        639_800,
                        [
                            condition("Persist", min_count=3),
                            condition("Crypt of Agadeem", min_count=3),
                        ],
                    )
                ],
            ),
            parent(
                "esper-persist",
                "Esper Persist",
                [
                    rule(
                        "esper-persist-primary",
                        639_700,
                        [
                            condition("Persist", min_count=3),
                            condition("Archon of Cruelty", min_count=3),
                            condition("Faithful Mending", min_count=2),
                        ],
                    )
                ],
            ),
        ]
    )

    _remove(data, "goryos-reanimator")
    data["archetypes"].extend(
        [
            parent(
                "cremator-goryos",
                "Cremator Goryo's",
                [
                    rule(
                        "cremator-goryos-primary",
                        641_300,
                        [
                            condition("Goryo's Vengeance", min_count=3),
                            condition("Cragganwick Cremator", min_count=3),
                            condition("Emrakul, the Aeons Torn", min_count=3),
                        ],
                    )
                ],
            ),
            parent(
                "esper-goryos",
                "Esper Goryo's",
                [
                    rule(
                        "esper-goryos-primary",
                        641_200,
                        [
                            condition("Goryo's Vengeance", min_count=3),
                            condition("Atraxa, Grand Unifier", min_count=3),
                            condition("Psychic Frog", min_count=3),
                            condition("Ephemerate", min_count=3),
                        ],
                    )
                ],
            ),
            parent(
                "grixis-goryos",
                "Grixis Goryo's",
                [
                    rule(
                        "grixis-goryos-primary",
                        641_100,
                        [
                            condition("Goryo's Vengeance", min_count=3),
                            condition("Faithless Looting", min_count=3),
                            condition("Psychic Frog", min_count=3),
                            condition("Ephemerate", exact_count=0),
                        ],
                    )
                ],
            ),
        ]
    )

    old_dimir = _remove(data, "blue-black-tempo")["blue-black-tempo"]
    retained = []
    for item in old_dimir["rules"][:2]:
        copied = deepcopy(item)
        copied["id"] = copied["id"].replace("blue-black-tempo", "dimir-tempo")
        retained.append(copied)
    dimir_exclusions = _strict_sources("blue", "black")
    retained.extend(
        [
            rule(
                "dimir-tempo-dimir-frog",
                212_010,
                [
                    condition("Fatal Push", min_count=3),
                    condition("Psychic Frog", min_count=3),
                    condition("Watery Grave", min_count=1),
                    condition("Goryo's Vengeance", exact_count=0),
                    condition("Persist", exact_count=0),
                    *dimir_exclusions,
                ],
                subtype_id="dimir",
            ),
            rule(
                "dimir-tempo-dimir-bowmasters",
                212_000,
                [
                    condition("Psychic Frog", max_count=2),
                    condition("Fatal Push", min_count=3),
                    condition("Orcish Bowmasters", min_count=2),
                    condition("Watery Grave", min_count=1),
                    condition("Goryo's Vengeance", exact_count=0),
                    condition("Persist", exact_count=0),
                    *dimir_exclusions,
                ],
                subtype_id="dimir",
            ),
        ]
    )
    data["archetypes"].append(
        parent(
            "dimir-tempo",
            "Dimir Tempo",
            retained,
            subtypes=[("dimir", "Dimir"), ("grixis", "Grixis"), ("esper", "Esper")],
        )
    )

    _remove(data, "blink")
    blink_common = [
        condition("Goryo's Vengeance", exact_count=0),
    ]
    data["archetypes"].extend(
        [
            parent(
                "esper-ketramose",
                "Esper Ketramose",
                [
                    rule(
                        "esper-ketramose-primary",
                        632_900,
                        [
                            condition("Relic of Progenitus", min_count=3),
                            condition("Ketramose, the New Dawn", min_count=3),
                            condition("Psychic Frog", min_count=3),
                            condition("Solitude", min_count=3),
                            *_strict_sources("white", "blue", "black"),
                            *blink_common,
                        ],
                    )
                ],
            ),
            parent(
                "esper-blink",
                "Esper Blink",
                [
                    rule(
                        "esper-blink-overlord",
                        632_800,
                        [
                            condition("Phelia, Exuberant Shepherd", min_count=3),
                            condition("Overlord of the Balemurk", min_count=3),
                            condition("Quantum Riddler", min_count=3),
                            *_strict_sources("white", "blue", "black"),
                            *blink_common,
                        ],
                    ),
                    rule(
                        "esper-blink-psychic-frog",
                        632_700,
                        [
                            condition("Phelia, Exuberant Shepherd", min_count=3),
                            condition("Quantum Riddler", min_count=3),
                            condition("Solitude", min_count=3),
                            condition("Psychic Frog", min_count=3),
                            condition("Overlord of the Balemurk", max_count=2),
                            *_strict_sources("white", "blue", "black"),
                            *blink_common,
                        ],
                    ),
                ],
            ),
            parent(
                "azorius-blink",
                "Azorius Blink",
                [
                    rule(
                        "azorius-blink-primary",
                        632_200,
                        [
                            condition("Phelia, Exuberant Shepherd", min_count=3),
                            condition("Quantum Riddler", min_count=3),
                            condition("Solitude", min_count=3),
                            condition("Ephemerate", min_count=2),
                            condition("Hallowed Fountain", min_count=1),
                            *_strict_sources("white", "blue"),
                            *blink_common,
                        ],
                    )
                ],
            ),
            parent(
                "jeskai-stoneforge",
                "Jeskai Stoneforge",
                [
                    rule(
                        "jeskai-stoneforge-primary",
                        632_600,
                        [
                            condition("Phelia, Exuberant Shepherd", min_count=3),
                            condition("Quantum Riddler", min_count=3),
                            condition("Solitude", min_count=3),
                            condition("Stoneforge Mystic", min_count=3),
                            condition(EQUIPMENT, min_count=1),
                            condition(source("red"), min_count=1),
                            *_strict_sources("white", "blue", "red"),
                            *blink_common,
                        ],
                    )
                ],
            ),
            parent(
                "jeskai-blink",
                "Jeskai Blink",
                [
                    rule(
                        "jeskai-blink-primary",
                        632_500,
                        [
                            condition("Phelia, Exuberant Shepherd", min_count=3),
                            condition("Quantum Riddler", min_count=3),
                            condition("Solitude", min_count=3),
                            condition("Stoneforge Mystic", max_count=2),
                            condition(source("red"), min_count=1),
                            *_strict_sources("white", "blue", "red"),
                            *blink_common,
                        ],
                    )
                ],
            ),
            parent(
                "mardu-blink",
                "Mardu Blink",
                [
                    rule(
                        "mardu-blink-primary",
                        632_400,
                        [
                            condition("Phelia, Exuberant Shepherd", min_count=3),
                            condition("Overlord of the Balemurk", min_count=3),
                            condition("Detective's Phoenix", min_count=2),
                            condition("Solitude", min_count=3),
                            *_strict_sources("white", "black", "red"),
                            *blink_common,
                        ],
                    )
                ],
            ),
            parent(
                "orzhov-blink",
                "Orzhov Blink",
                [
                    rule(
                        "orzhov-blink-primary",
                        632_300,
                        [
                            condition("Phelia, Exuberant Shepherd", min_count=3),
                            condition("Overlord of the Balemurk", min_count=3),
                            condition("Ephemerate", min_count=2),
                            *_strict_sources("white", "black"),
                            *blink_common,
                        ],
                    )
                ],
            ),
        ]
    )

    broodscale = next(item for item in data["archetypes"] if item["id"] == "broodscale-combo")
    broodscale["subtypes"].append({"id": "simic", "name": "Simic"})
    broodscale["rules"].append(
        rule(
            "broodscale-combo-simic",
            653_000,
            [
                condition("Basking Broodscale", min_count=3),
                condition("Blade of the Bloodchief", min_count=2),
                condition("Breeding Pool", min_count=1),
                condition("Talisman of Curiosity", min_count=2),
            ],
            subtype_id="simic",
        )
    )
    broodscale["priority"] = 653_000

    ponza = next(item for item in data["archetypes"] if item["id"] == "boros-land-destruction")
    ponza["name"] = "Boros Ponza"

    ramp = next(item for item in data["archetypes"] if item["id"] == "eldrazi-ramp")
    ramp["subtypes"] = [item for item in ramp["subtypes"] if item["id"] != "selesnya"]
    ramp["rules"] = [item for item in ramp["rules"] if item["subtype_id"] != "selesnya"]
    ramp["priority"] = max(item["priority"] for item in ramp["rules"])
    data["archetypes"].append(
        parent(
            "eldrazi-ramp-chant",
            "Eldrazi Ramp Chant",
            [
                rule(
                    "eldrazi-ramp-chant-primary",
                    646_850,
                    [
                        condition("Sowing Mycospawn", min_count=3),
                        condition("Ugin's Labyrinth", min_count=3),
                        condition("Eldrazi Temple", min_count=3),
                        condition("Orim's Chant", min_count=3),
                    ],
                )
            ],
        )
    )

    data["archetypes"].append(
        parent(
            "omnath-midrange",
            "Omnath Midrange",
            [
                rule(
                    "omnath-midrange-primary",
                    307_000,
                    [
                        condition("Omnath, Locus of Creation", min_count=2),
                        condition("Wrenn and Six", min_count=2),
                        condition("Teferi, Time Raveler", min_count=2),
                    ],
                )
            ],
        )
    )
    _replace(
        data,
        parent(
            "chant-control",
            "Chant Control",
            [
                rule(
                    "chant-control-jeskai",
                    306_000,
                    [
                        condition("Orim's Chant", min_count=3),
                        condition(spell("red"), min_count=1, zone="any"),
                    ],
                    subtype_id="jeskai",
                ),
                rule(
                    "chant-control-azorius",
                    305_900,
                    [
                        condition("Orim's Chant", min_count=3),
                        condition(spell("red"), exact_count=0, zone="any"),
                    ],
                    subtype_id="azorius",
                ),
            ],
            subtypes=[("azorius", "Azorius"), ("jeskai", "Jeskai")],
        ),
    )
    _replace(
        data,
        parent(
            "azorius-control",
            "Azorius Control",
            [
                rule(
                    "azorius-control-primary",
                    304_000,
                    [
                        condition("Meticulous Archive", min_count=1),
                        condition("Wrath of the Skies", min_count=2),
                        condition("Hallowed Fountain", min_count=1),
                        condition("Counterspell", min_count=2),
                        condition("Orim's Chant", exact_count=0),
                        condition("Isochron Scepter", exact_count=0),
                        condition("Galvanic Discharge", exact_count=0),
                    ],
                )
            ],
        ),
    )
    jeskai_control = next(item for item in data["archetypes"] if item["id"] == "jeskai-control")
    jeskai_control["rules"][0]["conditions"]["all"].append(
        condition("Isochron Scepter", exact_count=0)
    )

    _remove(data, "hollow-one")
    hollow_core = [
        condition("Hollow One", min_count=3),
        condition("Burning Inquiry", min_count=3),
        condition("Detective's Phoenix", min_count=3),
        condition("Vengevine", exact_count=0),
    ]
    data["archetypes"].extend(
        [
            parent(
                "hollowvine",
                "Hollowvine",
                [
                    rule(
                        "hollowvine-primary",
                        628_000,
                        [
                            condition("Hollow One", min_count=3),
                            condition("Vengevine", min_count=3),
                            condition("Blazing Rootwalla", min_count=3),
                        ],
                    )
                ],
            ),
            parent(
                "rakdos-hollow-one",
                "Rakdos Hollow One",
                [
                    rule(
                        "rakdos-hollow-one-mardu-practiced-offense",
                        627_930,
                        [*hollow_core, condition("Practiced Offense", min_count=1)],
                        subtype_id="mardu",
                    ),
                    rule(
                        "rakdos-hollow-one-mardu-hardened-academic",
                        627_920,
                        [*hollow_core, condition("Hardened Academic", min_count=1)],
                        subtype_id="mardu",
                    ),
                    rule(
                        "rakdos-hollow-one-mardu-wear-tear",
                        627_910,
                        [*hollow_core, condition("Wear/Tear", zone="any", min_count=1)],
                        subtype_id="mardu",
                    ),
                    rule(
                        "rakdos-hollow-one-rakdos",
                        627_900,
                        [
                            *hollow_core,
                            condition("Practiced Offense", exact_count=0),
                            condition("Hardened Academic", exact_count=0),
                            condition("Wear/Tear", zone="any", exact_count=0),
                        ],
                        subtype_id="rakdos",
                    ),
                ],
                subtypes=[("rakdos", "Rakdos"), ("mardu", "Mardu")],
            ),
        ]
    )

    living_core = [condition("Living End", min_count=3)]
    _replace(
        data,
        parent(
            "living-end",
            "Living End",
            [
                rule(
                    "living-end-four-color",
                    113_050,
                    [
                        *living_core,
                        condition("Shardless Agent", min_count=3),
                        condition("Violent Outburst", min_count=3),
                        condition("Overlord of the Balemurk", min_count=3),
                    ],
                    subtype_id="four-color",
                ),
                rule(
                    "living-end-temur",
                    113_040,
                    [
                        *living_core,
                        condition("Shardless Agent", min_count=3),
                        condition("Violent Outburst", min_count=3),
                        condition("Overlord of the Balemurk", exact_count=0),
                    ],
                    subtype_id="temur",
                ),
                rule(
                    "living-end-sultai",
                    113_030,
                    [
                        *living_core,
                        condition("Shardless Agent", min_count=3),
                        condition("Overlord of the Balemurk", min_count=3),
                        condition("Violent Outburst", exact_count=0),
                    ],
                    subtype_id="sultai",
                ),
                rule(
                    "living-end-bant",
                    113_020,
                    [
                        *living_core,
                        condition("Shardless Agent", min_count=3),
                        condition("Ardent Plea", min_count=3),
                        condition("Violent Outburst", exact_count=0),
                        condition("Overlord of the Balemurk", exact_count=0),
                    ],
                    subtype_id="bant",
                ),
                rule(
                    "living-end-rakdos",
                    113_010,
                    [
                        *living_core,
                        condition("Electrodominance", min_count=3),
                        condition("Shardless Agent", exact_count=0),
                        condition("Violent Outburst", exact_count=0),
                        condition("Overlord of the Balemurk", exact_count=0),
                    ],
                    subtype_id="rakdos",
                ),
            ],
            subtypes=[
                ("four-color", "Four-Color"),
                ("temur", "Temur"),
                ("sultai", "Sultai"),
                ("bant", "Bant"),
                ("rakdos", "Rakdos"),
            ],
        ),
    )

    steel = next(item for item in data["archetypes"] if item["id"] == "steel-cutter")
    steel["name"] = "Izzet Steel-Cutter"
    steel["subtypes"] = [{"id": "izzet", "name": "Izzet"}]
    steel["rules"] = [steel["rules"][0]]
    steel["priority"] = steel["rules"][0]["priority"]
    data["archetypes"].extend(
        [
            parent(
                "rakdos-steel-cutter",
                "Rakdos Steel-Cutter",
                [
                    rule(
                        "rakdos-steel-cutter-primary",
                        674_500,
                        [
                            condition("Cori-Steel Cutter", min_count=3),
                            condition("Dragon's Rage Channeler", min_count=3),
                            condition("Lava Dart", min_count=3),
                            condition("Nethergoyf", min_count=3),
                            condition("Blood Crypt", min_count=1),
                        ],
                    )
                ],
            ),
            parent(
                "mono-red-artifact",
                "Mono-Red Artifact",
                [
                    rule(
                        "mono-red-artifact-primary",
                        674_000,
                        [
                            condition("Mox Opal", min_count=3),
                            condition("Urza's Saga", min_count=3),
                            condition("Cori-Steel Cutter", min_count=3),
                            condition("Weapons Manufacturing", min_count=3),
                        ],
                    )
                ],
            ),
        ]
    )
    prowess_core = [
        condition("Cori-Steel Cutter", min_count=3),
        condition("Lava Dart", min_count=3),
    ]
    red_core = [
        *prowess_core,
        condition("Dragon's Rage Channeler", min_count=3),
        condition("Monastery Swiftspear", min_count=3),
    ]
    _replace(
        data,
        parent(
            "prowess",
            "Prowess",
            [
                rule(
                    "prowess-lessons",
                    672_900,
                    [
                        *prowess_core,
                        condition("Academic Dispute", min_count=3),
                        condition("Boomerang Basics", zone="any", min_count=3),
                    ],
                    subtype_id="lessons",
                ),
                rule(
                    "prowess-mardu",
                    672_800,
                    [
                        *red_core,
                        condition("Blood Crypt", min_count=1),
                        condition("Sacred Foundry", min_count=1),
                    ],
                    subtype_id="mardu",
                ),
                rule(
                    "prowess-grixis",
                    672_700,
                    [
                        *prowess_core,
                        condition("Preordain", min_count=2),
                        condition(spell("black"), zone="any", min_count=1),
                    ],
                    subtype_id="grixis",
                ),
                rule(
                    "prowess-jeskai",
                    672_600,
                    [
                        *prowess_core,
                        condition("Preordain", min_count=2),
                        condition(spell("white"), zone="any", min_count=1),
                    ],
                    subtype_id="jeskai",
                ),
                rule(
                    "prowess-temur",
                    672_500,
                    [*prowess_core, condition(spell("green"), zone="any", min_count=1)],
                    subtype_id="temur",
                ),
                rule(
                    "prowess-boros",
                    672_400,
                    [
                        *red_core,
                        condition(spell("white"), zone="any", min_count=1),
                        condition("Preordain", exact_count=0),
                        condition("Blood Crypt", exact_count=0),
                        condition("Hallowed Fountain", exact_count=0),
                        condition("Arclight Phoenix", exact_count=0),
                    ],
                    subtype_id="boros",
                ),
                rule(
                    "prowess-mono-red",
                    672_300,
                    [
                        *red_core,
                        condition(spell("white"), zone="any", exact_count=0),
                        condition(spell("blue"), zone="any", exact_count=0),
                        condition(spell("black"), zone="any", exact_count=0),
                        condition(spell("green"), zone="any", exact_count=0),
                        condition("Arclight Phoenix", exact_count=0),
                    ],
                    subtype_id="mono-red",
                ),
                rule(
                    "prowess-izzet",
                    672_200,
                    [
                        *red_core,
                        condition("Preordain", min_count=2),
                        condition(spell("white"), zone="any", exact_count=0),
                        condition(spell("black"), zone="any", exact_count=0),
                        condition(spell("green"), zone="any", exact_count=0),
                    ],
                    subtype_id="izzet",
                ),
            ],
            subtypes=[
                ("izzet", "Izzet"),
                ("temur", "Temur"),
                ("grixis", "Grixis"),
                ("jeskai", "Jeskai"),
                ("lessons", "Lessons"),
                ("boros", "Boros"),
                ("mono-red", "Mono-Red"),
                ("mardu", "Mardu"),
            ],
        ),
    )

    _replace(
        data,
        parent(
            "deaths-shadow",
            "Death's Shadow",
            [
                rule(
                    "deaths-shadow-grixis",
                    620_030,
                    [
                        condition("Death's Shadow", min_count=3),
                        condition("Thoughtseize", min_count=3),
                        condition("Stubborn Denial", min_count=2),
                        condition("Blood Crypt", min_count=1),
                        condition("Watery Grave", min_count=1),
                    ],
                    subtype_id="grixis",
                ),
                rule(
                    "deaths-shadow-dimir",
                    620_020,
                    [
                        condition("Death's Shadow", min_count=3),
                        condition("Thoughtseize", min_count=3),
                        condition("Stubborn Denial", min_count=2),
                        condition("Watery Grave", min_count=1),
                        condition("Blood Crypt", exact_count=0),
                        condition("Steam Vents", exact_count=0),
                    ],
                    subtype_id="dimir",
                ),
                rule(
                    "deaths-shadow-rakdos",
                    620_010,
                    [
                        condition("Death's Shadow", min_count=3),
                        condition("Thoughtseize", min_count=3),
                        condition("Nethergoyf", min_count=3),
                        condition("Moonshadow", min_count=3),
                        condition("Street Wraith", min_count=3),
                        condition("Blood Crypt", min_count=1),
                        condition("Stubborn Denial", exact_count=0),
                        condition("Watery Grave", exact_count=0),
                        condition("Steam Vents", exact_count=0),
                    ],
                    subtype_id="rakdos",
                ),
            ],
            subtypes=[("grixis", "Grixis"), ("dimir", "Dimir"), ("rakdos", "Rakdos")],
        ),
    )

    _remove(data, "blue-eldrazi")
    data["archetypes"].append(
        parent(
            "mono-blue-tron",
            "Mono-Blue Tron",
            [
                rule(
                    "mono-blue-tron-primary",
                    621_000,
                    [
                        condition("Urza's Mine", min_count=4),
                        condition("Urza's Power Plant", min_count=4),
                        condition("Urza's Tower", min_count=4),
                        condition("Expedition Map", min_count=3),
                        condition("Island", min_count=3),
                        *_strict_sources("blue"),
                    ],
                )
            ],
        )
    )
    return data


def _standard() -> dict[str, Any]:
    data = _load("standard")

    _replace(
        data,
        parent(
            "izzet-aggro",
            "Izzet Aggro",
            [
                rule(
                    "izzet-aggro-primary",
                    22_000,
                    [
                        condition("Scalding Viper", min_count=3),
                        condition("Hired Claw", min_count=3),
                        condition("Spirebluff Canal", min_count=1),
                    ],
                )
            ],
        ),
    )

    _remove(data, "azorius-tempo")
    data["archetypes"].append(
        parent(
            "azorius-prison",
            "Azorius Prison",
            [
                rule(
                    "azorius-prison-primary",
                    65_000,
                    [
                        condition("High Noon", min_count=3),
                        condition("Aang, Swift Savior", min_count=2),
                        condition("Aven Interrupter", min_count=3),
                    ],
                )
            ],
        )
    )

    _remove(data, "jeskai-manufacturing")
    manufacturing_core = [
        condition("Weapons Manufacturing", min_count=3),
        condition("United Battlefront", min_count=3),
        condition("Sacred Foundry", min_count=1),
    ]
    _replace(
        data,
        parent(
            "boros-manufacturing",
            "Boros Manufacturing",
            [
                rule(
                    "boros-manufacturing-jeskai",
                    16_000,
                    [*manufacturing_core, condition("Cryogen Relic", min_count=2)],
                    subtype_id="jeskai",
                ),
                rule(
                    "boros-manufacturing-mardu",
                    15_950,
                    [
                        *manufacturing_core,
                        condition("Cryogen Relic", max_count=1),
                        condition("Tithing Blade", min_count=2),
                    ],
                    subtype_id="mardu",
                ),
                rule(
                    "boros-manufacturing-boros",
                    15_900,
                    [
                        *manufacturing_core,
                        condition("Cryogen Relic", max_count=1),
                        condition("Tithing Blade", max_count=1),
                    ],
                    subtype_id="boros",
                ),
            ],
            subtypes=[("jeskai", "Jeskai"), ("mardu", "Mardu"), ("boros", "Boros")],
        ),
    )

    _remove(data, "simic-kona")
    kona_core = [
        condition("Kona, Rescue Beastie", min_count=4),
        condition("Omniscience", min_count=4),
        condition("Uthros, Titanic Godcore", min_count=3),
    ]
    data["archetypes"].append(
        parent(
            "kona-omniscience",
            "Kona Omniscience",
            [
                rule(
                    "kona-omniscience-temur",
                    41_020,
                    [
                        *kona_core,
                        condition("Ashling, Rekindled", min_count=1),
                        condition("Adagia, Windswept Bastion", exact_count=0),
                        condition("Hallowed Fountain", exact_count=0),
                    ],
                    subtype_id="temur",
                ),
                rule(
                    "kona-omniscience-bant-adagia",
                    41_010,
                    [
                        *kona_core,
                        condition("Adagia, Windswept Bastion", min_count=1),
                        condition("Ashling, Rekindled", exact_count=0),
                    ],
                    subtype_id="bant",
                ),
                rule(
                    "kona-omniscience-bant-hallowed-fountain",
                    41_005,
                    [
                        *kona_core,
                        condition("Hallowed Fountain", min_count=1),
                        condition("Ashling, Rekindled", exact_count=0),
                    ],
                    subtype_id="bant",
                ),
                rule(
                    "kona-omniscience-simic",
                    41_000,
                    [
                        *kona_core,
                        condition("Ashling, Rekindled", exact_count=0),
                        condition("Adagia, Windswept Bastion", exact_count=0),
                        condition("Hallowed Fountain", exact_count=0),
                    ],
                    subtype_id="simic",
                ),
            ],
            subtypes=[("temur", "Temur"), ("bant", "Bant"), ("simic", "Simic")],
        )
    )

    _remove(data, "4-color-control")
    data["archetypes"].extend(
        [
            parent(
                "dark-jeskai-control",
                "Dark Jeskai Control",
                [
                    rule(
                        "dark-jeskai-control-primary",
                        56_000,
                        [
                            condition("Inevitable Defeat", min_count=2),
                            condition("Jeskai Revelation", min_count=1),
                            condition("Stock Up", min_count=1),
                            condition("Tablet of Discovery", max_count=1),
                        ],
                    )
                ],
            ),
            parent(
                "white-sultai-control",
                "White Sultai Control",
                [
                    rule(
                        "white-sultai-control-primary",
                        13_010,
                        [
                            condition("Rakshasa's Bargain", zone="any", min_count=2),
                            condition("Aang, Swift Savior", zone="any", min_count=2),
                            condition("Three Steps Ahead", zone="any", min_count=2),
                            condition("Emeritus of Abundance", zone="any", min_count=2),
                            condition("Flow State", zone="any", exact_count=0),
                        ],
                    )
                ],
            ),
        ]
    )
    sultai = next(item for item in data["archetypes"] if item["id"] == "sultai-control")
    sultai["rules"].append(
        rule(
            "sultai-control-bargain",
            12_990,
            [
                condition("Rakshasa's Bargain", zone="any", min_count=2),
                condition("Three Steps Ahead", zone="any", min_count=2),
                condition("Emeritus of Abundance", zone="any", min_count=2),
                condition("Flow State", zone="any", exact_count=0),
                condition("Aang, Swift Savior", zone="any", exact_count=0),
            ],
        )
    )
    sultai["priority"] = max(item["priority"] for item in sultai["rules"])

    allies = next(item for item in data["archetypes"] if item["id"] == "4-color-allies")
    allies["name"] = "Allies Kindred"

    _remove(data, "boros-leyline", "mono-red-leyline")
    leyline_core = [
        condition("Leyline of Resonance", min_count=4),
        condition("Slickshot Show-Off", min_count=4),
    ]
    leyline_rules = []
    supported = ["blue", "green", "white", "black"]
    subtype_names = {
        "blue": ("izzet", "Izzet"),
        "green": ("gruul", "Gruul"),
        "white": ("boros", "Boros"),
        "black": ("rakdos", "Rakdos"),
    }
    for offset, color in enumerate(supported):
        subtype_id, _ = subtype_names[color]
        leyline_rules.append(
            rule(
                f"leyline-aggro-{subtype_id}",
                27_040 - offset * 10,
                [
                    *leyline_core,
                    condition(source(color), min_count=1),
                    *[
                        condition(source(other), exact_count=0)
                        for other in supported
                        if other != color
                    ],
                ],
                subtype_id=subtype_id,
            )
        )
    leyline_rules.append(
        rule(
            "leyline-aggro-mono-red",
            27_000,
            [
                *leyline_core,
                *[condition(source(color), exact_count=0) for color in supported],
            ],
            subtype_id="mono-red",
        )
    )
    _replace(
        data,
        parent(
            "leyline-aggro",
            "Leyline Aggro",
            leyline_rules,
            subtypes=[
                ("izzet", "Izzet"),
                ("gruul", "Gruul"),
                ("boros", "Boros"),
                ("rakdos", "Rakdos"),
                ("mono-red", "Mono-Red"),
            ],
        ),
    )

    deceit = next(item for item in data["archetypes"] if item["id"] == "dimir-deceit")
    for item in deceit["rules"][0]["conditions"]["all"]:
        if item["card"] == "Requiting Hex":
            item["min_count"] = 2
            break
    else:
        raise AssertionError("Dimir Deceit Requiting Hex condition missing")
    return data


def build_shadow_rules(format_id: str) -> dict[str, Any]:
    if format_id == "modern":
        return _modern()
    if format_id == "standard":
        return _standard()
    raise ValueError(f"unsupported shadow format {format_id!r}")


def write_shadow_rules(format_id: str) -> Path:
    path = OUTPUT_ROOT / f"{format_id}.yaml"
    document = build_shadow_rules(format_id)
    text = yaml.safe_dump(document, sort_keys=False, allow_unicode=True, width=100)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def main() -> int:
    for format_id in ("modern", "standard"):
        path = write_shadow_rules(format_id)
        print(path.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
