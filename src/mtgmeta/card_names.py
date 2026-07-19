"""Format-independent card-name normalization."""

from __future__ import annotations

import json
from pathlib import Path


_ALIAS_DATA_PATH = Path(__file__).with_name("data") / "om1_spm_aliases.json"


def _load_card_aliases() -> dict[str, str]:
    artifact = json.loads(_ALIAS_DATA_PATH.read_text(encoding="utf-8"))
    mappings = artifact["mappings"]
    aliases = {item["alias"]: item["canonical_name"] for item in mappings}
    if len(mappings) != artifact["mapping_count"] or len(aliases) != len(mappings):
        raise ValueError("Card-alias artifact contains a count mismatch or duplicate alias")
    return aliases


CARD_ALIASES = _load_card_aliases()


def normalize_card_name(name: str) -> str:
    """Strip surrounding whitespace and resolve a known printed-name alias."""

    stripped_name = name.strip()
    return CARD_ALIASES.get(stripped_name, stripped_name)
