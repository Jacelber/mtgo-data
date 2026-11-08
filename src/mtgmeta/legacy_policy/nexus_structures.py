"""Accepted Nexus structures; no event, player, or exact-deck overrides."""

GUARDS = [
    "Mystic Forge",
    "The Fantasticar",
    "Painter's Servant",
    "Helm of Obedience",
    "Paradoxical Outcome",
    "Show and Tell",
]
PATHS = {
    "artifact-stock": (
        "colorless-tron",
        "Tron",
        {
            "Planar Nexus": 3,
            "Urza's Tower": 3,
            "Urza's Mine": 3,
            "Urza's Power Plant": 3,
            "Karn, the Great Creator": 3,
            "The One Ring": 3,
            "Grim Monolith": 3,
            "Trinisphere": 3,
            "Ugin, Eye of the Storms": 2,
            "Stock Up": 4,
            "Giant's Boulder": 3,
            "Disruptor Flute": 2,
        },
        GUARDS
        + [
            "Cloudpost",
            "Glimmerpost",
            "Transmute Artifact",
            "Force of Will",
            "Force of Negation",
            "Thundertrap Trainer",
            "Sink into Stupor",
            "Portent of Calamity",
        ],
        {},
    ),
    "green-post": (
        "green-post",
        "Green Post",
        {
            "Cloudpost": 4,
            "Glimmerpost": 2,
            "Planar Nexus": 3,
            "Urza's Tower": 3,
            "Crop Rotation": 4,
            "Karn, the Great Creator": 3,
            "The One Ring": 3,
            "Kozilek's Command": 3,
        },
        GUARDS + ["Transmute Artifact", "Force of Will", "Force of Negation"],
        {},
    ),
    "transmute-tron": (
        "mono-blue-tron",
        "Blue Tron",
        {
            "Planar Nexus": 3,
            "Urza's Tower": 3,
            "Urza's Mine": 3,
            "Urza's Power Plant": 3,
            "Transmute Artifact": 3,
            "Coveted Jewel": 2,
            "Relic of Sauron": 3,
            "Paradox Engine": 1,
            "Grim Monolith": 4,
            "Expedition Map": 2,
            "Kozilek's Command": 3,
            "Ugin, Eye of the Storms": 2,
            "Trinisphere": 3,
            "The One Ring": 3,
        },
        GUARDS + ["Cloudpost", "Glimmerpost", "Copy Artifact", "Glaring Fleshraker"],
        {"Coveted Jewel": 2},
    ),
}


def matches(tag, main):
    _, _, minimums, absent, maximums = PATHS[tag]
    return (
        all(main.get(c, 0) >= n for c, n in minimums.items())
        and all(not main.get(c, 0) for c in absent)
        and all(main.get(c, 0) <= n for c, n in maximums.items())
    )
