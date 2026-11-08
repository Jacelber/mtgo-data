"""Role-based colors for the reviewed Hogaak branch, never a pure-UB default."""

from .branch_colors import GREEN, RED, WHITE
from .card_data import printed_spell_colors, known_neutral_payment

BRANCH = "w44-dimir-hogaak"


def applies(result):
    return (
        result.status == "classified"
        and result.archetype_id == "dimir-tempo"
        and any(m.rule_id == BRANCH for m in result.top_priority_matches)
    )


def audit_color(rules, main, side):
    # Preserve the reviewed sideboard use, rather than globally making Silence
    # neutral. A different zone or unsupported Forest plan gets no exception.
    free_silence = (
        not main.get("Reverent Silence", 0)
        and 0 < side.get("Reverent Silence", 0) <= 2
        and main.get("Bayou", 0) >= 1
        and main.get("Dryad Arbor", 0) >= 1
        and main.get("Misty Rainforest", 0) + main.get("Verdant Catacombs", 0) >= 8
    )
    colors = {"blue", "black"}
    evidence, issues = {}, []
    for card in sorted(
        c for c in set(main) | set(side) if main.get(c, 0) + side.get(c, 0) > 0
    ):
        if card == "Reverent Silence":
            cs = set() if free_silence else {"green"}
        elif card == "Hogaak, Arisen Necropolis":
            cs = {"black"}  # Accepted convoke/delve use, never mandatory green.
        elif card in {
            "Faerie Macabre",
            "Surgical Extraction",
            "Nihil Spellbomb",
            "Dismember",
        }:
            cs = set()  # Preserve existing reviewed non-color tool roles.
        else:
            # Existing paid-tool markers include abilities such as Boseiju and
            # activated abilities; do not rely solely on printed spell colors.
            cs = {
                color
                for color, names in [("green", GREEN), ("red", RED), ("white", WHITE)]
                if card in names
            }
            printed = printed_spell_colors(card)
            if printed is not None:
                cs.update({"W": "white", "U": "blue", "B": "black", "R": "red", "G": "green"}[c] for c in printed)
            if not cs and not known_neutral_payment(card):
                issues.append(card + ": unreviewed payment role")
        colors.update(cs)
        evidence[card] = sorted(cs)
    extra = colors - {"blue", "black"}
    if issues:
        subtype, label = None, None
    elif not extra:
        subtype, label = "dimir", "纯蓝黑"
    elif len(extra) == 1:
        subtype, label = {
            "green": ("sultai", "混绿"),
            "red": ("grixis", "混红"),
            "white": ("esper", "混白"),
        }[next(iter(extra))]
    else:
        subtype, label = "multicolor", "多色"
    return {
        "subtype": subtype,
        "subtypeName": label,
        "colors": sorted(colors),
        "evidence": evidence,
        "issues": issues,
        "reverentSilenceFreeRole": free_silence,
    }
