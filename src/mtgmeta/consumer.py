"""Small shared helpers for Phase 8 public consumer fields."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


WILSON_Z = 1.96


def identity_display_name(
    parent_name: str,
    subtype_name: str | None = None,
    *,
    maintained_subtype_names: Iterable[str] = (),
) -> str:
    """Return a self-contained label without repeating a maintained prefix."""

    if subtype_name is None:
        return parent_name
    if parent_name.casefold() in subtype_name.casefold():
        return subtype_name
    parent_folded = parent_name.casefold()
    leading_subtypes = [
        name
        for name in maintained_subtype_names
        if parent_folded == name.casefold()
        or parent_folded.startswith(f"{name.casefold()} ")
    ]
    if leading_subtypes:
        base_name = max(leading_subtypes, key=len)
        parent_suffix = parent_name[len(base_name) :].strip()
        return f"{subtype_name} {parent_suffix}".strip()
    return f"{subtype_name} {parent_name}"


def wilson_interval(
    wins: int,
    total: int,
    z: float = WILSON_Z,
) -> dict[str, float] | None:
    """Return a Wilson interval for literal wins over all valid matches."""

    if total <= 0:
        return None
    proportion = wins / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = (
        z
        * (
            proportion * (1 - proportion) / total
            + z * z / (4 * total * total)
        )
        ** 0.5
        / denominator
    )
    return {
        "lower": round(max(0.0, center - margin), 6),
        "upper": round(min(1.0, center + margin), 6),
    }


def literal_match_record(
    wins: int,
    losses: int,
    draws: int,
) -> dict[str, Any]:
    """Return the frozen Phase 8 literal win-rate record."""

    matches = wins + losses + draws
    return {
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "matches": matches,
        "win_rate": round(wins / matches, 6) if matches else None,
        "win_rate_method": "wins_over_valid_matches",
        "confidence_interval_95": wilson_interval(wins, matches),
    }
