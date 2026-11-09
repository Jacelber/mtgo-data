"""Two accepted Tron output families; recognition and payment colors stay intact."""

COLORS = frozenset(
    {
        "colorless",
        "mono-blue",
        "mono-white",
        "mono-green",
        "mono-red",
        "dimir",
        "izzet",
        "temur",
        "sultai",
        "azorius",
        "boros",
        "esper",
        "selesnya",
        "grixis",
        "rakdos",
        "simic",
        "non-black",
        "non-white",
        "non-green",
        "non-red",
        "non-blue",
    }
)


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
        and sum(
            main.get(c, 0)
            for c in (
                "Stock Up",
                "Thundertrap Trainer",
                "Brainstorm",
                "Ponder",
                "Portent of Calamity",
                "Sink into Stupor",
            )
        )
        >= 3
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


# Only these source-supported one/two-color identities remain separate.
COLOR_IDS = {
    "W": "mono-white",
    "U": "mono-blue",
    "B": "mono-black",
    "R": "mono-red",
    "G": "mono-green",
    "WU": "azorius",
    "WB": "orzhov",
    "WR": "boros",
    "WG": "selesnya",
    "UB": "dimir",
    "UR": "izzet",
    "UG": "simic",
    "BR": "rakdos",
    "BG": "golgari",
    "RG": "gruul",
}


def audit_subtype(rules, parent, main, side):
    """Tron's explicit rainbow exception, preserving reviewed noncasting roles."""
    from ..classifier_cards import _mana_support
    from . import policy_counts
    from .card_data import shared_card
    from .colors import FREE, ABILITIES, spellreq
    from .nexus_colors import audit_color, DIRECT_TARGETS

    ORDER = "WUBRG"

    main, side = policy_counts(main), policy_counts(side)
    cards = set(main) | set(side)
    fixed = {c: [] for c in ORDER}
    capacity = set()
    missing = []
    for n in sorted(cards):
        f = shared_card(n)
        if not f:
            missing.append(n)
            continue
        for color in _mana_support([(f, main.get(n, 0) + side.get(n, 0))]) & set(ORDER):
            fixed[color].append(n)
        capacity.update(set(f.produced_mana) & set(ORDER))
        if n in {
            "Lotus Petal",
            "Mox Opal",
            "Giant's Boulder",
            "Mox Diamond",
            "Chromatic Star",
            "Chromatic Sphere",
        }:
            capacity.update(ORDER)
    # Keep already reviewed free/target/tool roles; these are not new color decisions.
    original = "mono-blue-tron" if parent == "blue-tron" else "colorless-tron"
    role_main, role_side = main, side
    if "Boseiju, Who Endures" in cards and not any(
        s != "Boseiju, Who Endures" for s in fixed["G"]
    ):
        # Its newly confirmed neutral role must also hold while recognizing
        # the existing artifact-tool shell, not only in the final color sum.
        role_main = {n: q for n, q in main.items() if n != "Boseiju, Who Endures"}
        role_side = {n: q for n, q in side.items() if n != "Boseiju, Who Endures"}
    excluded = {
        n: "existing reviewed non-color role"
        for n in audit_color(rules, original, role_main, role_side)["excluded"]
    }
    excluded.update({n: "existing free/noncasting role" for n in cards & set(FREE)})
    excluded.update(
        {n: "existing direct-entry target role" for n in cards & DIRECT_TARGETS}
    )
    # User-confirmed pregame/trap roles, and Firespout does not expand Blue Tron.
    for n in cards & {
        "Leyline of the Void",
        "Mindbreak Trap",
        "Ravenous Trap",
        "Archive Trap",
    }:
        excluded[n] = "reviewed free/pregame tool"
    if parent == "blue-tron" and "Firespout" in cards:
        excluded["Firespout"] = (
            "Owner: Blue Tron board wipe alone does not expand colors"
        )
    planned = set()
    evidence = []
    issues = list(missing)
    pending_hybrids = []
    for zone, counts in [("main", main), ("side", side)]:
        for n, qty in counts.items():
            if n in excluded:
                continue
            colors, hybrid = spellreq(n)
            if n in ABILITIES:
                ac, _ = ABILITIES[n]
                if n != "Boseiju, Who Endures" or any(
                    s != "Boseiju, Who Endures" for s in fixed["G"]
                ):
                    colors.update(ac)
                else:
                    excluded[n] = (
                        "Owner: no other non-rainbow green source for Boseiju channel"
                    )
            for color in colors:
                if color in capacity:
                    planned.add(color)
                    evidence.append(
                        dict(
                            card=n,
                            zone=zone,
                            color=color,
                            quantity=qty,
                            fixed_support=fixed[color],
                        )
                    )
                else:
                    issues.append(n + ": no retained payment capability for " + color)
            for options in hybrid:
                pending_hybrids.append((n, zone, qty, options))
    # A hybrid cost uses an already established color before considering a new
    # color. Evaluate after fixed costs so input card order cannot affect this.
    for n, zone, qty, options in pending_hybrids:
        existing = options & planned
        available = options & {c for c in ORDER if fixed[c]}
        if existing or len(available) == 1:
            choices = existing or available
            color = next(c for c in ORDER if c in choices)
            planned.add(color)
            evidence.append(
                dict(
                    card=n,
                    zone=zone,
                    color=color,
                    quantity=qty,
                    fixed_support=fixed[color],
                )
            )
        else:
            issues.append(n + ": hybrid payment role needs review")
    colors = "".join(c for c in ORDER if c in planned)
    supported = {c for c in planned if fixed[c]}
    if not planned:
        subtype = "colorless" if parent == "tron" else "mono-blue"
    elif parent == "blue-tron" and planned <= {"U"}:
        subtype = "mono-blue"
    elif len(planned) <= 2 and supported == planned:
        subtype = COLOR_IDS[colors]
    else:
        subtype = "multicolor"
    return {
        "subtype": subtype,
        "paid_colors": colors,
        "dedicated_support": fixed,
        "evidence": evidence,
        "excluded": excluded,
        "issues": sorted(set(issues)),
    }


def route_identity(rules, parent, subtype, main, side):
    """Resolve engine first, then source-supported colors for any Tron recognition."""
    if parent in {"tron", "blue-tron"}:
        target = parent
    else:
        # A recognized shell may have held its old color audit unresolved. The
        # new source-aware audit supplies that evidence before registry lookup.
        old_subtype = "colorless" if parent == "colorless-tron" else subtype
        target, _ = output_identity(parent, old_subtype, main)
        if target not in {"tron", "blue-tron"}:
            return parent, subtype, {}
    info = audit_subtype(rules, target, main, side)
    return target, info["subtype"], info
