"""Accepted Legacy family/color policy, explicitly enabled by the rule file.

Recognition branches remain separate from output identities: branch names and
retired splash children must not leak into statistics or the weekly catalog.
Only card counts enter classification. Private review rows are not runtime data.
"""

from dataclasses import replace
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from typing import TYPE_CHECKING
from collections.abc import Mapping

from ..rules import ArchetypeDefinition, SubtypeDefinition, RuleSet

if TYPE_CHECKING:
    from ..classifier import ClassificationResult

ROOT = Path(__file__).parent


@lru_cache(maxsize=1)
def identities():
    rows = json.loads((ROOT / "identities.json").read_text(encoding="utf8"))
    result = {(r["parent_id"], r["subtype_id"]): r for r in rows}
    if len(result) != len(rows):
        raise ValueError("duplicate Legacy output identity")
    return result


@lru_cache(maxsize=1)
def _full_subtype_names():
    return frozenset(
        (r["parent_name"], r["english"])
        for r in identities().values()
        if r["subtype_id"] is not None
    )


def is_full_subtype_name(parent: str, subtype: str) -> bool:
    """Explicit accepted complete labels, without guessing from color words."""
    return (parent, subtype) in _full_subtype_names()


def register_outputs(rules: RuleSet) -> RuleSet:
    groups = {}
    for row in identities().values():
        groups.setdefault(row["parent_id"], []).append(row)
    outputs = tuple(
        ArchetypeDefinition(
            pid,
            rows[0]["parent_name"],
            0,
            tuple(
                SubtypeDefinition(r["subtype_id"], r["english"], pid)
                for r in rows
                if r["subtype_id"] is not None
            ),
            (),
        )
        for pid, rows in sorted(groups.items())
    )
    return replace(rules, archetypes=outputs, recognition_archetypes=rules.archetypes)


def structural_rules(rules):
    return replace(
        rules,
        archetypes=rules.recognition_archetypes or rules.archetypes,
        recognition_archetypes=None,
        identity_policy=None,
    )


def policy_subject() -> dict[str, str]:
    # Both executable policy and public facts are versioned classifier inputs.
    subject = {}
    for path in sorted(ROOT.iterdir()):
        if path.suffix not in {".py", ".json"}:
            continue
        # Windows checkout line endings and JSON indentation do not alter
        # classification. Hash canonical text/data so the digest is portable.
        text = path.read_text(encoding="utf8")
        if path.suffix == ".json":
            text = json.dumps(
                json.loads(text),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        subject[path.name] = sha256(text.encode("utf8")).hexdigest()
    return subject


def classify(
    rules: RuleSet, main: Mapping[str, int], side: Mapping[str, int]
) -> "ClassificationResult":
    from .reviewed_extensions import resolve_unclassified

    main, side = policy_counts(main), policy_counts(side)
    result = _classify_registered(rules, main, side)
    result = resolve_unclassified(main, side, result, rules)
    if result.status == "classified" and result.archetype_id in {
        "mystic-forge-combo",
        "goblins",
    }:
        from .colors import audit
        from .families import remap

        color = audit(
            {"main": main, "side": side, "candidate": {"parent": result.archetype_id}}
        )
        if result.archetype_id == "mystic-forge-combo":
            sid = {
                "": "colorless",
                "U": "mono-blue",
                "R": "mono-red",
                "W": "mono-white",
            }.get(color["colors"], "multicolor")
        else:
            sid = {"R": "mono-red", "BR": "rakdos", "RG": "gruul"}.get(color["colors"])
        identity = identities().get((result.archetype_id, sid)) if sid else None
        if color["issues"] or identity is None:
            return replace(
                result,
                status="unknown",
                archetype_id=None,
                archetype_name=None,
                subtype_id=None,
                subtype_name=None,
                selected_rule_id=None,
                selected_priority=None,
                errors=tuple(color["issues"])
                or ("legacy_identity: maintained subtype requires review",),
            )
        result = remap(
            result,
            result.archetype_id,
            identity["parent_name"],
            sid,
            identity["english"],
        )
    return result


def _classify_registered(rules, main, side):
    from .families import classify_with_review

    main, side = policy_counts(main), policy_counts(side)
    result, info = classify_with_review(structural_rules(rules), main, side)
    if result.status != "classified":
        return result
    # Owner-confirmed integration cleanup: these nulls were duplicate pure
    # identities, not unreviewed colors or a distinct construction subtype.
    default_subtypes = {"azorius-control": "azorius", "mono-blue-tron": "mono-blue"}
    if result.subtype_id is None and result.archetype_id in default_subtypes:
        color_audit = info.get("colorAudit", {})
        required = {"azorius-control": "WU", "mono-blue-tron": "U"}[result.archetype_id]
        if color_audit.get("issues") or color_audit.get("colors") != required:
            return replace(
                result,
                status="unknown",
                archetype_id=None,
                archetype_name=None,
                subtype_id=None,
                subtype_name=None,
                selected_rule_id=None,
                selected_priority=None,
                top_priority_matches=(),
                overridden_matches=(),
                errors=(
                    "legacy_identity: pure subtype requires resolved payment evidence",
                ),
            )
        sid = default_subtypes[result.archetype_id]

        def fill(m):
            return (
                replace(m, subtype_id=sid)
                if m.archetype_id == result.archetype_id
                else m
            )

        result = replace(
            result,
            subtype_id=sid,
            matched_rules=tuple(fill(m) for m in result.matched_rules),
            top_priority_matches=tuple(fill(m) for m in result.top_priority_matches),
            overridden_matches=tuple(fill(m) for m in result.overridden_matches),
        )
    from .tron import remap_result

    result = remap_result(result, main)
    identity = identities().get((result.archetype_id, result.subtype_id))
    issues = info.get("issues", [])
    if identity is None or issues:
        # New evidence is reviewable Unknown, never an unregistered guessed color.
        return replace(
            result,
            status="unknown",
            archetype_id=None,
            archetype_name=None,
            subtype_id=None,
            subtype_name=None,
            selected_rule_id=None,
            selected_priority=None,
            top_priority_matches=(),
            overridden_matches=(),
            errors=tuple("legacy_identity: " + str(x) for x in issues)
            or ("legacy_identity: output requires review",),
        )

    def match(m):
        known = identities().get((m.archetype_id, m.subtype_id))
        if known is None:
            return m
        return replace(
            m,
            archetype_name=known["parent_name"],
            subtype_name=known["english"] if m.subtype_id else None,
        )

    return replace(
        result,
        archetype_name=identity["parent_name"],
        subtype_name=identity["english"] if result.subtype_id else None,
        matched_rules=tuple(match(m) for m in result.matched_rules),
        top_priority_matches=tuple(match(m) for m in result.top_priority_matches),
        overridden_matches=tuple(match(m) for m in result.overridden_matches),
    )


def policy_counts(counts):
    """Use the shared identity vocabulary, including aliases and split faces."""
    from ..classifier_cards import normalize_counts

    return normalize_counts({n: q for n, q in counts.items() if q})
