"""Role-based colors for the reviewed Hogaak branch, never a pure-UB default."""

import json
from pathlib import Path

from .branch_colors import GREEN, RED, WHITE

EVIDENCE_PATH = Path(__file__).with_name("hogaak-color-evidence.json")
ROLES = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))["roles"]
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
        elif card in ROLES:
            cs = set(ROLES[card])
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
            feature = rules.semantic_features.cards.get(card)
            if feature is not None:
                cs.update(feature.spell_colors)
            if not cs:
                # An unseen card/land or colorless artifact may have a colored
                # ability. Lack of evidence must not silently mean pure UB.
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
