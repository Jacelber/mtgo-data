"""Suppress only the obsolete two-card Reanimator shortcut on guarded Shadow hits."""

from dataclasses import replace

SHADOW_RULE = "e23-shadow-life-resource"
REANIMATOR_SHORTCUT = "dimir-reanimator-builtin"
SHADOW_ABSENT = [
    "Entomb",
    "Careful Study",
    "Buried Alive",
    "Animate Dead",
    "Exhume",
    "Shallow Grave",
    "Persist",
    "Unearth",
    "Archon of Cruelty",
    "Atraxa, Grand Unifier",
    "Griselbrand",
    "Valgavoth, Terror Eater",
    "Abhorrent Oculus",
    "Troll of Khazad-dum",
]


def resolve_shadow_shortcut(rules, main, side, result):
    from mtgmeta.classifier import _classify_counts as classify_counts

    hits = {m.rule_id for m in result.matched_rules}
    if not {SHADOW_RULE, REANIMATOR_SHORTCUT} <= hits:
        return result
    # Never choose a parent by fiat or hide unrelated matches. Re-evaluate the
    # normal engine after suppressing only the overly broad legacy shortcut.
    filtered = replace(
        rules,
        archetypes=tuple(
            replace(f, rules=tuple(r for r in f.rules if r.id != REANIMATOR_SHORTCUT))
            if f.id == "dimir-reanimator"
            else f
            for f in rules.archetypes
        ),
    )
    return classify_counts(filtered, main, side)
