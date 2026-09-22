"""Format- and source-independent deck normalization helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .card_names import equivalent_basic_land_names, normalize_card_name


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
    """Count a card in main, side, or both zones, merging basic-land printings."""

    equivalent_names = equivalent_basic_land_names(card_name)
    if zone == "main":
        return sum(main_counts.get(name, 0) for name in equivalent_names)
    if zone == "side":
        return sum(side_counts.get(name, 0) for name in equivalent_names)
    return sum(
        main_counts.get(name, 0) + side_counts.get(name, 0)
        for name in equivalent_names
    )
