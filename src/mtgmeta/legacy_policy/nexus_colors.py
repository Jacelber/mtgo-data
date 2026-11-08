"""Private, role-aware color audit. Unresolved uses retain a null subtype."""

import json
from pathlib import Path
from .nexus_structures import matches

LOCAL = json.loads(
    Path(__file__)
    .with_name("nexus-local-card-evidence.json")
    .read_text(encoding="utf8")
)
ORDER = ["white", "blue", "black", "red", "green"]
LETTERS = dict(zip("WUBRG", ORDER))
# Basic mana-cost facts supplement the existing manifest; detailed uncertain
# MDFC/free-cast uses below are intentionally not guessed from color identity.
EXTRA = {
    "blue": "Agent of Treachery|Archive Trap|Cyclonic Rift|Hydroelectric Specimen|Impulse|Invasion Submersible|Marang River Regent|Moonsnare Prototype|Omniscience|Portent of Calamity|Repeal|Sea Gate Restoration|Shark Typhoon|Show and Tell|Sphinx of the Final Word|Transmute Artifact",
    "white": "Ethersworn Canonist|Perilous Snare|Seasoned Dungeoneer",
    "green": "Crop Rotation|Once Upon a Time|Primeval Titan",
}
NEUTRAL = set(
    (
        "All Is Dust|Ancient Tomb|Argentum Masticore|Basalt Monolith|Blast Zone|Bojuka Bog|Candelabra of Tawnos|Canoptek Scarab Swarm|Chalice of the Void|Chrome Mox|City of Traitors|Cityscape Leveler|Cloudpost|Coveted Jewel|Crucible of Worlds|Cursed Totem|Defense Grid|Disruptor Flute|Eldrazi Confluence|Emrakul, the Aeons Torn|Engineered Explosives|Ensnaring Bridge|Expedition Map|Extinguisher Battleship|Eye of Ugin|Forest|Ghost Quarter|Glimmerpost|Grafdigger's Cage|Grim Monolith|Grindstone|Helm of Obedience|Inventors' Fair|Island|Karakas|Karn's Sylex|Liquimetal Coating|Lotus Petal|Manifold Key|Meekstone|Meteor Golem|Mishra's Bauble|Mishra's Research Desk|Mistrise Village|Mox Diamond|Mox Opal|Mycosynth Lattice|Mystic Forge|Otawara, Soaring City|Painter's Servant|Paradox Engine|Petrified Hamlet|Plains|Planar Nexus|Powder Keg|Ratchet Bomb|Relic of Progenitus|Relic of Sauron|Skysovereign, Consul Flagship|Sorcerous Spyglass|Soul-Guide Lantern|Spatial Contortion|Sphere of Resistance|Summon: Bahamut|Sundering Titan|Swamp|Syr Ginger, the Meal Ender|Talon Gates of Madara|The Fantasticar|The Filigree Sylex|The One Ring|The Stone Brain|The Tabernacle at Pendrell Vale|The Ten Rings|Thorn of Amethyst|Tormod's Crypt|Torpor Orb|Ugin, Eye of the Storms|Ugin, the Spirit Dragon|Ulamog, the Ceaseless Hunger|Underground Sea|Urza's Mine|Urza's Power Plant|Urza's Saga|Urza's Workshop|Volcanic Island|Voltaic Key|Wasteland"
    ).split("|")
)
IGNORED = {
    "Faerie Macabre",
    "Surgical Extraction",
    "Nihil Spellbomb",
    "Dismember",
    "Haywire Mite",
}
CONDITIONAL = {
    "Leyline of the Void": {"black"},
    "Ravenous Trap": {"black"},
    "Mindbreak Trap": {"blue"},
    "Archive Trap": {"blue"},
    "Force of Vigor": {"green"},
    "Once Upon a Time": {"green"},
    "Elvish Spirit Guide": {"green"},
    "Simian Spirit Guide": {"red"},
    "Phyrexian Metamorph": {"blue"},
    "Waterlogged Teachings": {"blue", "black"},
}


def audit_color(rules, parent, main, side):
    cards = set(main) | set(side)
    colors = set()
    evidence = {}
    issues = []
    excluded = {}
    transmute_tron = parent == "mono-blue-tron" and matches("transmute-tron", main)
    green_post = parent == "green-post" and matches("green-post", main)
    # Owner-approved roles in the reviewed Nexus/Tower/Karn shells only.
    # Basic Swamp/Island support for fallback payment does not revoke these
    # decisions. Main-deck Trap/Leyline plans remain outside this exception.
    nexus_tools = (
        main.get("Planar Nexus", 0) >= 3
        and main.get("Urza's Tower", 0) >= 3
        and main.get("Karn, the Great Creator", 0) >= 3
    )
    free_tools = set()
    if nexus_tools or transmute_tron:
        free_tools = {
            card
            for card in [
                "Leyline of the Void",
                "Mindbreak Trap",
                "Archive Trap",
                "Ravenous Trap",
                "Phyrexian Metamorph",
            ]
            if side.get(card, 0) and not main.get(card, 0)
        }
        if parent == "colorless-tron" and (
            main.get("Trinisphere", 0) + main.get("Sphere of Resistance", 0) >= 3
        ):
            free_tools.update({"Elvish Spirit Guide", "Simian Spirit Guide"} & cards)
    if transmute_tron and main.get("Phyrexian Metamorph", 0):
        free_tools.add("Phyrexian Metamorph")
    if green_post:
        free_tools.update({"Elvish Spirit Guide"} & cards)
    once_regular = nexus_tools and all(
        main.get(card, 0) >= n
        for card, n in [
            ("Once Upon a Time", 3),
            ("Thundertrap Trainer", 3),
            ("Stock Up", 3),
            ("Force of Will", 3),
            ("Giant's Boulder", 2),
        ]
    )
    once_regular = once_regular or (green_post and main.get("Once Upon a Time", 0) >= 3)
    combo = main.get("Show and Tell", 0) >= 3 or main.get("Portent of Calamity", 0) >= 3
    # W44 reviewed Emry/Foundry Nexus shell: printed blue creatures and
    # activated blue/green tools, not the artifacts' printed color identity.
    emry_nexus = parent == "mono-blue-tron" and all(
        main.get(c, 0) >= 3
        for c in [
            "Planar Nexus",
            "Urza's Tower",
            "Emry, Lurker of the Loch",
            "Retrofitter Foundry",
            "Force of Will",
        ]
    )
    tool_colors = (
        {
            "Aether Spellbomb": {"blue"},
            "Emry, Lurker of the Loch": {"blue"},
            "Plagon, Lord of the Beach": {"blue"},
            "Shadowspear": set(),
        }
        if emry_nexus
        else {}
    )
    for card in sorted(cards):
        if card in free_tools:
            excluded[card] = (
                "Owner-approved free/alternative tool role; fallback hardcast support is not a color commitment"
            )
            continue
        if card in IGNORED:
            excluded[card] = "confirmed non-color tool use"
            continue
        if card == "Atraxa, Grand Unifier" and combo:
            excluded[card] = (
                "combo target; incidental hardcast is not an extra color commitment"
            )
            continue
        if card in CONDITIONAL and not (card == "Once Upon a Time" and once_regular):
            continue
        if card == "Boseiju, Who Endures":
            cs = {"green"}  # Reviewed channel role, not its mana-production line.
        elif card == "Chaos Defiler":
            cs = {"black", "red"}
        elif transmute_tron and card == "Mishra's Research Desk":
            cs = {"red"}  # Accepted recurring resource use, not printed cost.
        elif transmute_tron and card == "Otawara, Soaring City":
            cs = {"blue"}
        elif card in tool_colors:
            cs = tool_colors[card]
        elif card in LOCAL:
            cs = {LETTERS[c] for c in LOCAL[card].get("colors", [])}
        elif card in NEUTRAL:
            cs = set()
        else:
            cs = {color for color, names in EXTRA.items() if card in names.split("|")}
            feature = rules.semantic_features.cards.get(card)
            if not cs and feature is not None:
                cs = set(feature.spell_colors)
            elif not cs:
                issues.append(card + ": missing local color/use evidence")
        if cs:
            evidence[card] = sorted(cs)
            colors.update(cs)
    for card, cs in CONDITIONAL.items():
        if card in free_tools or (card == "Once Upon a Time" and once_regular):
            continue
        if card in cards and not cs <= colors:
            issues.append(
                card + ": conditional free use versus hardcast needs confirmation"
            )
    if (
        parent == "mono-blue-tron"
        and main.get("Force of Will", 0) < 3
        and not transmute_tron
    ):
        issues.append(
            "blue core versus artifact core needs confirmation; Stock Up alone is insufficient"
        )
    if issues:
        return {
            "subtype": None,
            "subtypeName": None,
            "colors": sorted(colors),
            "evidence": evidence,
            "excluded": excluded,
            "issues": issues,
        }
    base_blue = parent in {"mono-blue-tron", "blue-post"}
    if parent == "green-post":
        extras = colors - {"green"}
        if not extras:
            subtype, label = "mono-green", "纯绿"
        elif len(extras) >= 2:
            subtype, label = "multicolor", "多色"
        else:
            return {
                "subtype": None,
                "subtypeName": None,
                "colors": sorted(colors),
                "evidence": evidence,
                "excluded": excluded,
                "issues": ["green Post single-splash naming remains unreviewed"],
            }
        return {
            "subtype": subtype,
            "subtypeName": label,
            "colors": sorted(colors),
            "evidence": evidence,
            "excluded": excluded,
            "issues": [],
        }
    extras = colors - {"blue"} if base_blue else colors
    if not extras:
        subtype, label = ("mono-blue", "纯蓝") if base_blue else ("colorless", "无色")
    elif base_blue and len(extras) == 1:
        color = next(iter(extras))
        subtype, label = {
            "black": ("dimir", "混黑"),
            "red": ("izzet", "混红"),
            "white": ("azorius", "混白"),
            "green": ("simic", "混绿"),
        }[color]
    elif not base_blue and colors == {"white"}:
        subtype, label = "white", "混白"
    elif (
        parent == "colorless-tron"
        and colors == {"blue"}
        and matches("artifact-stock", main)
    ):
        subtype, label = "blue", "混蓝"
    elif len(colors) >= 2:
        subtype, label = "multicolor", "多色"
    else:
        # No newly invented fine color subtype for the original colorless family.
        return {
            "subtype": None,
            "subtypeName": None,
            "colors": sorted(colors),
            "evidence": evidence,
            "excluded": excluded,
            "issues": ["artifact-core one/two-color naming needs confirmation"],
        }
    return {
        "subtype": subtype,
        "subtypeName": label,
        "colors": sorted(colors),
        "evidence": evidence,
        "excluded": excluded,
        "issues": [],
    }
