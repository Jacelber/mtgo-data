"""Two accepted Tron output families; recognition and payment colors stay intact."""

COLORS = frozenset({
    "colorless", "mono-blue", "mono-white", "mono-green", "mono-red",
    "dimir", "izzet", "temur", "sultai", "azorius", "boros", "esper",
    "selesnya", "grixis", "rakdos", "simic", "non-black", "non-white",
    "non-green",
})


def output_identity(parent, subtype, main):
    """Remap only an already recognized Tron, never another Nexus family."""
    color = parent.removesuffix("-tron") if parent else ""
    if color not in COLORS or parent != color + "-tron":
        return parent, subtype
    # The broad colorless recognition without its validated payment subtype
    # was not an accepted output. Leave it unresolved for reviewed extensions.
    if parent == "colorless-tron" and subtype != "colorless":
        return parent, subtype
    interaction = (
        main.get("Force of Will", 0) + main.get("Force of Negation", 0) >= 3
        and sum(main.get(c, 0) for c in (
            "Stock Up", "Thundertrap Trainer", "Brainstorm", "Ponder",
            "Portent of Calamity", "Sink into Stupor",
        )) >= 3
    )
    transmute_engine = (
        main.get("Transmute Artifact", 0) >= 2
        and main.get("Coveted Jewel", 0) >= 1
        and main.get("Relic of Sauron", 0) >= 1
        and main.get("Grim Monolith", 0) >= 2
    )
    return ("blue-tron" if interaction or transmute_engine else "tron"), color


def remap_result(result, main):
    from .families import remap

    if result.status != "classified":
        return result
    pid, sid = output_identity(result.archetype_id, result.subtype_id, main)
    if (pid, sid) == (result.archetype_id, result.subtype_id):
        return result
    return remap(result, pid, "Blue Tron" if pid == "blue-tron" else "Tron", sid)
