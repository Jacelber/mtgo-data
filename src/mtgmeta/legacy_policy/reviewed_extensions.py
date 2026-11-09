"""Accepted structural extensions for previously unresolved Legacy builds.

Existing classifications have precedence. These rules inspect card counts only,
not review row IDs, players, dates, or complete-deck fingerprints. A conflict is
resolved only by its explicitly reviewed competing families and core signature.
"""

from dataclasses import replace
from functools import lru_cache
import json
from pathlib import Path

from .colors import audit


@lru_cache(maxsize=1)
def definitions():
    return json.loads(Path(__file__).with_suffix(".json").read_text(encoding="utf8"))


def resolve_unclassified(main, side, result, rules=None):
    from mtgmeta.classifier import ConditionEvidence, RuleMatch
    from mtgmeta.classifier_cards import classifier_card_name
    from . import identities

    if result.status not in {"unknown", "conflict"}:
        return result
    matches = []
    for rule in definitions():
        if result.status == "conflict":
            parents = {m.archetype_id for m in result.top_priority_matches}
            if parents != set(rule.get("resolves_conflict", [])):
                continue
        evidence = []
        valid = True
        for field in ["main_min", "main_max", "side_min", "side_max"]:
            zone, limit = field.split("_")
            counts = main if zone == "main" else side
            for card, bound in rule.get(field, {}).items():
                card = classifier_card_name(card)
                count = counts.get(card, 0)
                evidence.append(
                    ConditionEvidence(
                        card,
                        zone,
                        count,
                        bound if limit == "min" else None,
                        bound if limit == "max" else None,
                        None,
                    )
                )
                if (limit == "min" and count < bound) or (
                    limit == "max" and count > bound
                ):
                    valid = False
        if not valid:
            continue
        if rule.get("colors") and not rule["parent"].endswith("-tron"):
            color = audit(
                {"main": main, "side": side, "candidate": {"parent": rule["parent"]}}
            )
            cs = set(color["colors"])
            # Firespout needs red to clear ground creatures, not just to pay
            # its hybrid cost. This branch explicitly accepts both uses.
            if (
                rule.get("firespout_ground_use")
                and side.get("Firespout")
                and color["sources"]["R"]
            ):
                cs.add("R")
            if color["issues"] or cs != set(rule["colors"]):
                continue
        from .tron import route_identity

        parent, subtype, tron_info = route_identity(
            rules, rule["parent"], rule.get("subtype"), main, side
        )
        if tron_info.get("issues"):
            continue
        identity = identities().get((parent, subtype))
        if identity is None:
            continue
        matches.append(
            RuleMatch(
                parent,
                identity["parent_name"],
                subtype,
                identity["english"] if subtype else None,
                rule["id"],
                0,
                tuple(evidence),
            )
        )
    if not matches:
        return result
    targets = {(m.archetype_id, m.subtype_id) for m in matches}
    if len(targets) != 1:
        # Overlapping new mechanisms must remain visible, never first-match wins.
        return replace(
            result,
            status="conflict",
            archetype_id=None,
            archetype_name=None,
            subtype_id=None,
            subtype_name=None,
            selected_rule_id=None,
            selected_priority=None,
            matched_rules=result.matched_rules + tuple(matches),
            top_priority_matches=tuple(matches),
            conflict_matches=tuple(matches),
            conflict_kind="parent_archetype",
            priority_tie=True,
            errors=(),
        )
    matches = tuple(sorted(matches, key=lambda m: m.rule_id))
    first = matches[0]
    return replace(
        result,
        status="classified",
        archetype_id=first.archetype_id,
        archetype_name=first.archetype_name,
        subtype_id=first.subtype_id,
        subtype_name=first.subtype_name,
        selected_rule_id=first.rule_id,
        selected_priority=first.priority,
        matched_rules=matches,
        top_priority_matches=matches,
        overridden_matches=result.matched_rules,
        conflict_matches=(),
        conflict_kind=None,
        priority_tie=False,
        errors=(),
    )
