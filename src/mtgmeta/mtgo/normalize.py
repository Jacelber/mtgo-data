"""MTGO event normalization and format-aware classification dispatch."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..classifier import ClassificationResult, classify_deck
from ..config import FormatConfigError, load_rule_set
from ..rules import RuleSet
from . import load_mtgo_context


def cards_to_simple(card_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "name": card["card_attributes"]["card_name"].strip(),
            "qty": int(card["qty"]),
        }
        for card in card_list
    ]


def normalize_event(data: dict[str, Any], *, include_inplayoffs: bool = True) -> dict[str, Any]:
    standings_by_id = {standing["loginid"]: standing for standing in data.get("standings", [])}
    finalrank_by_id = {ranking["loginid"]: ranking for ranking in data.get("final_rank", [])}
    players = []
    for deck in data["decklists"]:
        login_id = deck["loginid"]
        standing = standings_by_id.get(login_id, {})
        final_rank = finalrank_by_id.get(login_id, {})
        score = standing.get("score")
        players.append(
            {
                "player": deck["player"],
                "loginid": login_id,
                "swiss_rank": standing.get("rank"),
                "swiss_score": score,
                "swiss_wins": int(score) // 3 if score is not None else None,
                "opp_match_win_pct": standing.get("opponentmatchwinpercentage"),
                "game_win_pct": standing.get("gamewinpercentage"),
                "final_rank": final_rank.get("rank"),
                "main_deck": cards_to_simple(deck["main_deck"]),
                "sideboard": cards_to_simple(deck["sideboard_deck"]),
            }
        )
    player_count = data["player_count"]
    normalized = {
        "event_id": data["event_id"],
        "description": data["description"],
        "format": data.get("format"),
        "starttime": data.get("starttime"),
        "player_count": player_count.get("players") if isinstance(player_count, dict) else player_count,
    }
    if include_inplayoffs:
        normalized["inplayoffs"] = data.get("inplayoffs")
    normalized["players"] = players
    return normalized


def load_rules_for_format(
    repository_root: str | Path,
    format_id: str,
    *,
    registry_path: str | Path | None = None,
) -> RuleSet:
    context = load_mtgo_context(
        repository_root,
        format_id,
        "classification",
        registry_path=registry_path,
    )
    rule_set = load_rule_set(context.paths["rules"])
    if rule_set.format != format_id:
        raise FormatConfigError(
            f"classification rules declare {rule_set.format!r}, expected {format_id!r}"
        )
    return rule_set


def classify_event(event: dict[str, Any], rule_set: RuleSet) -> tuple[ClassificationResult, ...]:
    return tuple(classify_deck(rule_set, player) for player in event.get("players", []))


__all__ = ["cards_to_simple", "classify_event", "load_rules_for_format", "normalize_event"]
