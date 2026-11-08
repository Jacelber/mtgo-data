"""Structural branch resolution before the accepted family/color policy."""

import json
from pathlib import Path
from dataclasses import replace
from mtgmeta.classifier import _classify_counts as classify_counts
from .nexus_colors import audit_color
from .shadow import resolve_shadow_shortcut
from .branch_colors import apply as apply_tail_color
from .hogaak_colors import (
    applies as hogaak_color_applies,
    audit_color as audit_hogaak_color,
)

COLOR_PATH = Path(__file__).with_name("R02-color-paths.json")
COLOR_DECISIONS = json.loads(COLOR_PATH.read_text(encoding="utf8"))


def classify_branches(rules, main, side):
    result = classify_counts(rules, main, side)
    result = resolve_shadow_shortcut(rules, main, side, result)
    if result.status != "classified":
        return result
    if hogaak_color_applies(result):
        color = audit_hogaak_color(rules, main, side)
        return replace(
            result, subtype_id=color["subtype"], subtype_name=color["subtypeName"]
        )
    if result.archetype_id in {
        "mono-blue-tron",
        "blue-post",
        "green-post",
        "colorless-tron",
    }:
        color = audit_color(rules, result.archetype_id, main, side)
        # An unresolved role remains null; it is reported separately, never guessed.
        return replace(
            result, subtype_id=color["subtype"], subtype_name=color["subtypeName"]
        )
    decisions = [
        COLOR_DECISIONS[m.rule_id]
        for m in result.top_priority_matches
        if m.rule_id in COLOR_DECISIONS
        and COLOR_DECISIONS[m.rule_id]["parent"] == result.archetype_id
    ]
    if not decisions:
        return apply_tail_color(result, main, side)
    assert all(x == decisions[0] for x in decisions), "private color conflict"
    d = decisions[0]
    return replace(result, subtype_id=d["subtype"], subtype_name=d["subtypeName"])
