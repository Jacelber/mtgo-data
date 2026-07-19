"""Format- and source-independent deck normalization helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .card_names import normalize_card_name


CardCounts = dict[str, int]


def _zone_to_counts(cards: list[Mapping[str, Any]]) -> CardCounts:
    counts: CardCounts = {}
    for card in cards:
        name = normalize_card_name(card["name"])
        counts[name] = counts.get(name, 0) + int(card["qty"])
    return counts


def deck_to_counts(deck: Mapping[str, Any]) -> tuple[CardCounts, CardCounts]:
    """Return normalized main-deck and sideboard card counts."""

    return (
        _zone_to_counts(deck.get("main_deck", [])),
        _zone_to_counts(deck.get("sideboard", [])),
    )


def count_card(
    card_name: str,
    zone: str,
    main_counts: Mapping[str, int],
    side_counts: Mapping[str, int],
) -> int:
    """Count a canonical card name in main, side, or both zones."""

    if zone == "main":
        return main_counts.get(card_name, 0)
    if zone == "side":
        return side_counts.get(card_name, 0)
    return main_counts.get(card_name, 0) + side_counts.get(card_name, 0)
