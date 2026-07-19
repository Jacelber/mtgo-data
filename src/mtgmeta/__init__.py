"""Shared utilities for constructed Magic tournament data."""

from .card_names import CARD_ALIASES, normalize_card_name
from .classifier import (
    ClassificationResult, ConditionEvidence, RuleMatch, classify_counts,
    classify_deck, condition_matches, evaluate_matches,
)
from .deck import count_card, deck_to_counts
from .config import RuleConfigError, load_rule_set, parse_rule_text
from .rules import ArchetypeDefinition, CardCondition, ClassificationRule, RuleSet, SubtypeDefinition

__all__ = [
    "ArchetypeDefinition", "CARD_ALIASES", "CardCondition", "ClassificationResult",
    "ClassificationRule", "ConditionEvidence", "RuleConfigError", "RuleMatch", "RuleSet",
    "SubtypeDefinition", "classify_counts", "classify_deck", "condition_matches", "count_card",
    "deck_to_counts", "evaluate_matches", "load_rule_set", "normalize_card_name",
    "parse_rule_text",
]
