"""Adapt the shared immutable card snapshot; never store Legacy card facts."""

import re

from ..classifier_cards import CardFact, card_facts, resolve_card_name


def shared_card(name: str) -> CardFact | None:
    snapshot = card_facts()
    return snapshot.cards.get(resolve_card_name(name, snapshot))


def _legacy_shape(card: CardFact) -> dict:
    faces = [
        dict(
            name=f.name,
            mana_cost=f.mana_cost,
            type_line=f.type_line,
            oracle_text=f.oracle_text,
            colors=sorted(f.colors),
        )
        for f in card.faces
    ]
    result = {**faces[0], "produced_mana": sorted(card.produced_mana)}
    if card.layout == "split":
        result["mana_cost"] = " ".join(f["mana_cost"] for f in faces)
    if len(faces) > 1:
        result["card_faces"] = faces
    return result


def shared_fact(name: str) -> dict:
    card = shared_card(name)
    return _legacy_shape(card) if card else {}


def known_neutral_payment(name: str) -> bool:
    """Prove a neutral payment role; lack of a fact never proves neutrality.

    Basic lands produce colors but do not require them. Other cards only pass
    when every face has no colored symbol in its cost or rules text. This keeps
    colored activations/flashback and unfamiliar roles outside the fallback.
    """
    card = shared_card(name)
    if not card:
        return False
    if len(card.faces) == 1 and {"Basic", "Land"} <= set(card.faces[0].type_line.split()):
        return True
    if len(card.faces) == 1 and "Land" in card.faces[0].type_line:
        # Ignore mana OUTPUT symbols, not activation/channel payments.
        text = "\n".join(
            line.split(":", 1)[0] if ":" in line and "Add " in line else line
            for line in card.faces[0].oracle_text.splitlines()
        )
        return not re.search(r"\{[^}]*[WUBRG][^}]*\}", text)
    return not any(
        re.search(r"\{[^}]*[WUBRG][^}]*\}", f.mana_cost + "\n" + f.oracle_text)
        for f in card.faces
    )


def printed_spell_colors(name: str) -> set[str] | None:
    """Fixed casting colors, leaving ambiguous payment routes unresolved."""
    card = shared_card(name)
    if not card:
        return None
    face = card.faces[0]
    if "Land" in face.type_line:
        return set()
    cost = " ".join(f.mana_cost for f in card.faces) if card.layout == "split" else face.mana_cost
    tokens = re.findall(r"\{([^}]+)\}", cost)
    if any("/" in t for t in tokens):
        return None
    return set(tokens) & set("WUBRG")
