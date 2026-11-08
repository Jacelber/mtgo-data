"""Role-based color additions for the final manual reconciliation.

No player, date, source cell or deck hash participates. Large reanimation
targets and free graveyard tools do not establish a casting color. Existing
explicit color paths remain authoritative in private_candidate.
"""

from dataclasses import replace

GREEN = {
    "Questing Druid",
    "Once Upon a Time",
    "Gaddock Teeg",
    "Veil of Summer",
    "Nature's Claim",
    "Reverent Silence",
    "Witherbloom Apprentice",
    "Assassin's Trophy",
    "Abrupt Decay",
    "Boseiju, Who Endures",
    "Undermountain Adventurer",
    "Collector Ouphe",
    "Wear Down",
    "Force of Vigor",
}
RED = {
    "Pyroblast",
    "Red Elemental Blast",
    "Meltdown",
    "Fire Magic",
    "Ruination",
    "Forth Eorlingas!",
    "Magus of the Moon",
    "Blood Moon",
    "Faithless Looting",
    "Lightning Bolt",
    "Cori-Steel Cutter",
    "Flame of Anor",
    "Dreadhorde Arcanist",
    "Abrade",
    "Sudden Demise",
    "Burning Wish",
    "Shenanigans",
}
WHITE = {
    "Portable Hole",
    "Containment Priest",
    "Rip Apart",
    "Swords to Plowshares",
    "Prismatic Ending",
    "Rest in Peace",
    "Deafening Silence",
    "Lavinia, Azorius Renegade",
    "Wrath of the Skies",
    "Dispatch",
    "March of Otherworldly Light",
}
BLUE = {
    "Show and Tell",
    "Daze",
    "Brainstorm",
    "Ponder",
    "Flusterstorm",
    "Consign to Memory",
    "Force of Will",
    "Force of Negation",
    "Spell Pierce",
    "Stifle",
}
BLACK = {
    "Toxic Deluge",
    "Thoughtseize",
    "Orcish Bowmasters",
    "Cabal Therapy",
    "Fatal Push",
    "Snuff Out",
    "Molten Collapse",
    "Baleful Strix",
}
BASE = {
    "gwx-depths": set("WG"),
    "rakdos-reanimator": set("BR"),
    "mono-black-reanimator": set("B"),
    "bant-beanstalk": set("WUG"),
    "blue-artifacts": set("UR"),
    "boros-energy": set("WR"),
    "boros-initiative": set("WR"),
    "mono-black-midrange": set("B"),
    "azorius-control": set("WU"),
    "azorius-stoneblade": set("WU"),
    "death-and-taxes-yorion-mono-white": set("W"),
    "death-and-taxes-yorion-black-white": set("WB"),
    "dimir-tempo": set("UB"),
    "azorius-tempo": set("WU"),
}
LABEL = {"W": "白", "U": "蓝", "B": "黑", "R": "红", "G": "绿"}
GUILD = {
    "URG": "temur",
    "BG": "golgari",
    "BR": "rakdos",
    "WR": "boros",
    "WG": "selesnya",
    "UG": "simic",
    "WB": "orzhov",
    "WU": "azorius",
    "UB": "dimir",
    "UR": "izzet",
    "WUR": "jeskai",
    "UBR": "grixis",
    "BRG": "jund",
    "WUG": "bant",
    "WBR": "mardu",
    "WRG": "naya",
    "WUB": "esper",
    "WBG": "abzan",
    "UBG": "sultai",
}


def infer(parent, main, side):
    if parent not in BASE:
        return None
    cards = {c for c, n in main.items() if n} | {c for c, n in side.items() if n}
    extra = set()
    for color, names in [
        ("W", WHITE),
        ("U", BLUE),
        ("B", BLACK),
        ("R", RED),
        ("G", GREEN),
    ]:
        if color not in BASE[parent] and cards & names:
            extra.add(color)
    if not extra:
        return (
            {"subtype": "selesnya", "subtypeName": "纯绿白", "evidence": []}
            if parent == "gwx-depths"
            else None
        )
    order = "WUBRG"
    allcolors = "".join(c for c in order if c in BASE[parent] | extra)
    return {
        "subtype": GUILD.get(allcolors, "multicolor"),
        "subtypeName": (
            "多色"
            if len(allcolors) >= 4
            else "混" + "".join(LABEL[c] for c in order if c in extra)
        ),
        "evidence": sorted(
            cards
            & set().union(
                *(
                    names
                    for col, names in [
                        ("W", WHITE),
                        ("U", BLUE),
                        ("B", BLACK),
                        ("R", RED),
                        ("G", GREEN),
                    ]
                    if col in extra
                )
            )
        ),
    }


def apply(result, main, side):
    if result.subtype_id is not None:
        return result
    color = infer(result.archetype_id, main, side)
    return (
        replace(result, subtype_id=color["subtype"], subtype_name=color["subtypeName"])
        if color
        else result
    )
