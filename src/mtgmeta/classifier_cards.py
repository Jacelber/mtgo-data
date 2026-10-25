"""Offline card identities and casting facts, separate from deck naming policy."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any

from .card_names import normalize_card_name

FACTS_PATH = Path(__file__).with_name("data") / "classifier_card_facts.json"
IDENTITY_CONTRACT_VERSION = "1.1.0"
COLOR_NAMES = {"W": "white", "U": "blue", "B": "black", "R": "red", "G": "green"}
_FACE_SEPARATOR = re.compile(r"(?<!/)/{1,2}(?!/)")


@dataclass(frozen=True)
class CardFace:
    name: str
    mana_cost: str
    type_line: str
    oracle_text: str
    colors: frozenset[str]


@dataclass(frozen=True)
class CardFact:
    key: str
    oracle_id: str
    name: str
    layout: str
    faces: tuple[CardFace, ...]
    produced_mana: frozenset[str]

    @property
    def castable_faces(self) -> tuple[CardFace, ...]:
        # A transform/flip back is not an independently castable spell.
        faces = (
            self.faces
            if self.layout in {"split", "adventure", "modal_dfc"}
            else self.faces[:1]
        )
        return tuple(f for f in faces if "Land" not in f.type_line)


@dataclass(frozen=True)
class CardFacts:
    cards: Mapping[str, CardFact]
    names: Mapping[str, str]
    digest: str
    face_pairs: Mapping[tuple[str, str], frozenset[str]]


def read_card_facts(path: Path) -> CardFacts:
    payload = path.read_bytes()
    value: Any = json.loads(payload)
    if value.get("schema_version") != "1.0.0" or not isinstance(
        value.get("cards"), list
    ):
        raise ValueError("unsupported classifier card facts")
    cards: dict[str, CardFact] = {}
    names: dict[str, str] = {}
    face_pairs: dict[tuple[str, str], set[str]] = {}
    oracle_ids = set()
    for raw in value["cards"]:
        if not raw["faces"] or raw["key"] in cards or raw["oracle_id"] in oracle_ids:
            raise ValueError("duplicate or incomplete classifier card identity")
        faces = tuple(
            CardFace(
                f["name"],
                f["mana_cost"],
                f["type_line"],
                f["oracle_text"],
                frozenset(f["colors"]),
            )
            for f in raw["faces"]
        )
        if any(
            not f.name or not f.type_line or f.colors - COLOR_NAMES.keys()
            for f in faces
        ):
            raise ValueError("incomplete classifier face facts")
        card = CardFact(
            raw["key"],
            raw["oracle_id"],
            raw["name"],
            raw["layout"],
            faces,
            frozenset(raw["produced_mana"]) & COLOR_NAMES.keys(),
        )
        cards[card.key] = card
        oracle_ids.add(card.oracle_id)
        if len(faces) == 2:
            pair = (normalize_card_name(faces[0].name), normalize_card_name(faces[1].name))
            face_pairs.setdefault(pair, set()).add(card.key)
        for name in raw["names"]:
            if name in names and names[name] != card.key:
                raise ValueError(f"ambiguous classifier card spelling: {name}")
            names[name] = card.key
    return CardFacts(
        MappingProxyType(cards), MappingProxyType(names), sha256(payload).hexdigest(),
        MappingProxyType({pair: frozenset(keys) for pair, keys in face_pairs.items()}),
    )


@lru_cache(maxsize=1)
def card_facts() -> CardFacts:
    return read_card_facts(FACTS_PATH)


@lru_cache(maxsize=32768)
def classifier_card_name(name: str) -> str:
    return resolve_card_name(name, card_facts())


def resolve_card_name(name: str, facts: CardFacts) -> str:
    """Resolve exact names first, then unambiguous complete two-face spellings.

    Only the separator between registered faces is flexible. Slashes inside a
    face name remain literal; unknown pairs, reversed faces and ambiguous pairs
    are retained rather than guessed from one recognized half.
    """
    normalized = normalize_card_name(name)
    if normalized in facts.names:
        return facts.names[normalized]
    candidates = matching_face_entities(normalized, facts.face_pairs)
    return next(iter(candidates)) if len(candidates) == 1 else normalized


def matching_face_entities(
    name: str, face_pairs: Mapping[tuple[str, str], frozenset[str]],
) -> set[str]:
    """Match registered complete pairs for runtime and offline fact selection."""
    candidates: set[str] = set()
    for separator in _FACE_SEPARATOR.finditer(name):
        pair = (
            normalize_card_name(name[:separator.start()]),
            normalize_card_name(name[separator.end():]),
        )
        candidates.update(face_pairs.get(pair, ()))
    return candidates


def normalize_counts(counts: Mapping[str, int]) -> dict[str, int]:
    result: dict[str, int] = {}
    for name, qty in counts.items():
        key = classifier_card_name(name)
        result[key] = result.get(key, 0) + qty
    return result


@dataclass(frozen=True)
class ColorContribution:
    card: str
    zone: str
    quantity: int
    colors: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class DeckColors:
    colors: frozenset[str]
    contributions: tuple[ColorContribution, ...]
    missing: tuple[str, ...]
    mana_support: frozenset[str]
    basic_land_types: frozenset[str]

    @property
    def unresolved_uses(self) -> tuple[str, ...]:
        """Only undecided uses that can change the deck's actual color group."""
        unresolved = set()
        for contribution in self.contributions:
            if not contribution.reason.startswith("fling-secondary:unreviewed-source-count:"):
                continue
            color = COLOR_NAMES[FLING_SECONDARY_FACES[contribution.card][0]]
            if color in contribution.colors and not any(
                other.card != contribution.card and color in other.colors
                for other in self.contributions
            ):
                unresolved.add(contribution.card)
        return tuple(sorted(unresolved))


# These are use policies, not assertions that the printed cards are colorless.
# A supported normal casting route still contributes its color.
NONCAST_WITHOUT_SUPPORT = frozenset(
    {"Faerie Macabre", "Leyline of the Void", "Leyline of Sanctity"}
)
GORYOS_TARGETS = frozenset(
    {
        "Atraxa, Grand Unifier",
        "Griselbrand",
        "Emrakul, the Aeons Torn",
        "Sin, Spira's Punishment",
        "Ureni, the Song Unending",
        "Koma, World-Eater",
    }
)
CREATIVITY_TARGETS = frozenset(
    {
        "Archon of Cruelty",
        "Atraxa, Grand Unifier",
        "Emrakul, the Aeons Torn",
        "Serra's Emissary",
        "Terastodon",
        "Iona, Shield of Emeria",
    }
)
STANDARD_FLING_CHARM_CORE = (
    ("Callous Sell-Sword", 3),
    ("Slickshot Show-Off", 4),
    ("Wild Ride", 3),
)
STANDARD_FLING_CHARMS = frozenset({"Poison Dart Frog", "Frog Butler", "Quintorius Kand"})
STANDARD_SPIDER_COPY_TARGETS = frozenset({"Absolute Virtue"})
COLOR_PROFILES = frozenset(
    {"default", "modern-goryos", "modern-creativity", "standard-fling", "standard-spider-man", "pauper-packbeast", "pauper-battle-screech"}
)
PACKBEAST_RED_ROUTE = ("Lightning Bolt", "Galvanic Blast", "Holdout Settlement")
PACKBEAST_MARDU_SOURCES = (("Mardu Devotee", 4), ("Springleaf Drum", 4))
PACKBEAST_GREEN_ROUTE = (("Winding Way", 1), ("Springleaf Drum", 4))
BATTLE_SCREECH_GRUDGE_GATES = ("Citadel Gate", "Cliffgate")
CARD_USES = frozenset(
    {"normal_cast", "noncast", "noncast_without_support", "front_only", "adventure_only", "fling_secondary"}
)
# Opt-in family uses, never a global minimum-source rule for normal spells.
FLING_SECONDARY_FACES = {
    "Callous Sell-Sword": ("B", "adventure_only"),
    "Elusive Otter": ("G", "front_only"),
}
BASIC_TYPES = frozenset({"Plains", "Island", "Swamp", "Mountain", "Forest"})


def _cost_colors(
    face: CardFace, support: frozenset[str], established: frozenset[str]
) -> set[str]:
    symbols = re.findall(r"\{([^}]+)\}", face.mana_cost)
    colors: set[str] = set()
    for symbol in symbols:
        options = set(symbol.split("/")) & COLOR_NAMES.keys()
        if "/" in symbol:
            # Phyrexian/generic hybrid costs have a colorless payment route;
            # ordinary hybrid colors follow the deck's supported payment routes.
            options &= support
            if "P" in symbol.split("/") or "2" in symbol.split("/"):
                options &= established
            elif options & established:
                options &= established
            # Mana-spent effects (Firespout) can make the optional color a
            # meaningful use even when another color pays the hybrid cost.
            options |= {
                c for c in support
                if re.search(
                    rf"\bif (?:\{{{c}\}})+ was spent", face.oracle_text, re.IGNORECASE
                )
            }
        colors.update(options)
    if not symbols:  # e.g. a suspend spell with a color indicator
        colors.update(face.colors)
    return colors


def _has_color_payment(face: CardFace, support: set[str]) -> bool:
    """Check colored payments only, without estimating mana quantity or speed."""
    for symbol in re.findall(r"\{([^}]+)\}", face.mana_cost):
        parts = set(symbol.split("/"))
        colors = parts & COLOR_NAMES.keys()
        if colors and not (parts & {"P", "2"}) and not (colors & support):
            return False
    return True


def _additional_casting_colors(face: CardFace, support: frozenset[str]) -> set[str]:
    """Count supported flashback and kicker payments used to cast a spell.

    Read only the mana cost immediately following the keyword, not arbitrary
    oracle symbols (activated abilities do not define the default colors).
    Nonmana flashback costs, such as Battle Screech, contribute no extra color.
    """
    colors: set[str] = set()
    for cost in re.findall(
        r"\b(?:Flashback|Kicker) ((?:\{[^}]+\})+)", face.oracle_text
    ):
        payment = CardFace(face.name, cost, face.type_line, "", frozenset())
        if _has_color_payment(payment, set(support)):
            colors.update(set(re.findall(r"\{([WUBRG])\}", cost)) & support)
    return colors


def _mana_support(cards: list[tuple[CardFact, int]]) -> set[str]:
    """Stable color support, rather than every theoretically payable color.

    Rainbow lands and generic artifact/creature mana do not establish a color.
    Restricted lands, luck-dependent Caverns and a singleton Gardens likewise
    do not establish a splash. Fetch lands use the colors of retained targets.
    """
    support: set[str] = set()
    quantities: dict[str, int] = {}
    for card, qty in cards:
        quantities[card.key] = quantities.get(card.key, 0) + qty
    for card, _ in cards:
        playable_faces = (
            card.faces if card.layout == "modal_dfc" else card.faces[:1]
        )
        if not any("Land" in f.type_line for f in playable_faces):
            continue
        if card.key in {"Gemstone Caverns", "Reflecting Pool"}:
            # Pool cannot introduce a color absent from the other lands.
            continue
        if card.key == "The Mycosynth Gardens" and quantities[card.key] == 1:
            continue
        # Some sources can potentially make all five colors but always have a
        # fixed ordinary ability too (Citadel Gate -> W, Vivid Creek -> U).
        # Keep that fixed part, without inferring the optional chosen color.
        fixed: set[str] = set()
        for face in playable_faces:
            for line in face.oracle_text.splitlines():
                if "Spend this mana only" in line:
                    continue
                for symbols in re.findall(
                    r"\{T\}: Add ((?:\{[WUBRGC]\})+(?: or (?:\{[WUBRGC]\})+)*)", line
                ):
                    fixed.update(set(re.findall(r"\{([WUBRG])\}", symbols)))
        # Printed five-color capability (Lotus Field, Starting Town, etc.)
        # cannot establish a particular color's normal casting plan. A chosen
        # basic type is equivalent even when produced_mana omits that ability.
        if len(card.produced_mana) == 5 or any(
            "choose a basic land type" in f.oracle_text.lower()
            and "is the chosen type" in f.oracle_text.lower()
            for f in playable_faces
        ) or any("Spend this mana only" in f.oracle_text for f in playable_faces):
            support.update(fixed)
            continue
        support.update(card.produced_mana)
    return support


def _used_faces(card: CardFact, use: str | None) -> tuple[CardFace, ...]:
    if use == "front_only":
        return tuple(f for f in card.faces[:1] if "Land" not in f.type_line)
    if use == "adventure_only":
        return tuple(f for f in card.faces[1:] if "Land" not in f.type_line)
    return card.castable_faces


def _fling_fixed_sources(cards: list[tuple[CardFact, int]], color: str) -> int:
    """Extra fixed lands for the two reviewed Fling uses, not mana reliability.

    Rainbow/chosen-type lands and incidental mana do not defeat this local
    exception. Fetch targets count as fixed lands, not as extra copies for
    every fetch. Other spells still use the unchanged normal support model.
    """
    return sum(
        qty for card, qty in cards
        if color in card.produced_mana
        and color in _mana_support([(card, qty)])
    )


def deck_colors(
    main: Mapping[str, int],
    side: Mapping[str, int],
    *,
    profile: str = "default",
    facts: CardFacts | None = None,
    uses: Mapping[str, str] | None = None,
) -> DeckColors:
    if profile not in COLOR_PROFILES:
        raise ValueError(f"unknown color profile: {profile}")
    facts = facts or card_facts()
    resolved_uses: dict[str, str] = {}
    for name, declared_use in (uses or {}).items():
        key = facts.names.get(normalize_card_name(name), normalize_card_name(name))
        if key in resolved_uses and resolved_uses[key] != declared_use:
            raise ValueError(f"conflicting card use policies for {key}")
        resolved_uses[key] = declared_use
    uses = resolved_uses
    if set(uses.values()) - CARD_USES:
        raise ValueError("unknown per-card use policy")
    for name, declared_use in uses.items():
        if declared_use == "fling_secondary" and name not in FLING_SECONDARY_FACES:
            raise ValueError("fling_secondary requires Sell-Sword or Otter")
        if declared_use in {"front_only", "adventure_only"}:
            card = facts.cards.get(name)
            if card is None or card.layout != "adventure":
                raise ValueError("face selection requires a known adventure card: " + name)
    # Owner-confirmed charm use in the reviewed Standard Fling shell. Reuse
    # its existing structural core, not player identity or a blanket Frog ban.
    # Main-deck copies or multiple charm cards are outside this reviewed use.
    charm_shell = (
        profile == "standard-fling"
        and sum(main.get(name, 0) for name in STANDARD_FLING_CHARMS) == 0
        and sum(side.get(name, 0) for name in STANDARD_FLING_CHARMS) == 1
        and all(main.get(name, 0) >= qty for name, qty in STANDARD_FLING_CHARM_CORE)
    )
    charm_uses = {
        name for name in STANDARD_FLING_CHARMS
        if charm_shell and side.get(name, 0) == 1 and name not in uses
    }
    for name in charm_uses:
        uses[name] = "noncast"
    targets = (
        GORYOS_TARGETS
        if profile == "modern-goryos"
        else CREATIVITY_TARGETS
        if profile == "modern-creativity"
        else STANDARD_SPIDER_COPY_TARGETS
        if profile == "standard-spider-man" and main.get("Superior Spider-Man", 0) > 0
        else frozenset()
    )
    rows = [
        (zone, name, qty, facts.cards.get(facts.names.get(name, name)))
        for zone, counts in [("main", main), ("side", side)]
        for name, qty in sorted(counts.items())
        if qty and not name.startswith("__classifier-semantic-")
    ]
    missing = tuple(sorted({name for _, name, _, card in rows if card is None}))
    optional_reasons: dict[str, str] = {}
    for name, (color, selected_use) in FLING_SECONDARY_FACES.items():
        if uses.get(name) != "fling_secondary":
            continue
        # The family opts into the card's use in either zone. Unknown card
        # facts must not be silently treated as evidence of zero extra lands.
        if missing:
            continue
        count = _fling_fixed_sources(
            [(card, qty) for _, _, qty, card in rows if card is not None], color
        )
        if count <= 2:
            uses[name] = selected_use
            outcome = "optional-face"
        else:
            # Preserve default behavior outside the approved exception. Three
            # sources remain review evidence, NOT an approved threshold.
            outcome = "unreviewed-source-count" if count == 3 else "both-faces"
        optional_reasons[name] = f"fling-secondary:{outcome}:fixed-sources={count}"
    support = _mana_support(
        [(card, qty) for _, _, qty, card in rows if card is not None]
    )
    ordinary_support = set(support)
    # Reviewed Battle Screech route: chosen Gate colors support Grudge's
    # green flashback only. Do not grant green to unrelated spells or families.
    gates_grudge = (
        profile == "pauper-battle-screech"
        and all(main.get(name, 0) > 0 for name in BATTLE_SCREECH_GRUDGE_GATES)
    )
    # A sideboard-only Lesson can be a learn target without a normal casting
    # plan. Family mana exceptions must not silently establish its extra color.
    has_learn = any(
        zone == "main" and card is not None and uses.get(card.key) != "noncast"
        and any(re.search(r"\blearn\.", face.oracle_text, re.IGNORECASE)
                for face in _used_faces(card, uses.get(card.key)))
        for zone, _, _, card in rows
    )
    lesson_targets = {
        card.key for zone, _, _, card in rows
        if has_learn and zone == "side" and card is not None
        and not main.get(card.key, 0)
        and any("Lesson" in face.type_line.split() for face in card.castable_faces)
    }
    # Owner-approved main-deck burn route. The caller already enforces the
    # Packbeast parent core. This grants only red support from Holdout, never
    # all five colors or a general exception for Drum/sideboard splashes.
    packbeast_red = (
        profile == "pauper-packbeast"
        and all(main.get(name, 0) > 0 for name in PACKBEAST_RED_ROUTE)
    )
    if packbeast_red:
        support.add("R")
    # The separately reviewed full Devotee + Drum package establishes B/R
    # in Packbeast. Encampment and a particular payoff are not prerequisites.
    # Four of each is the reviewed configuration, not a global source cutoff.
    packbeast_mardu = (
        profile == "pauper-packbeast"
        and all(main.get(name, 0) >= qty for name, qty in PACKBEAST_MARDU_SOURCES)
    )
    if packbeast_mardu:
        support.update({"B", "R"})
    packbeast_green = (
        profile == "pauper-packbeast"
        and all(main.get(name, 0) >= qty for name, qty in PACKBEAST_GREEN_ROUTE)
    )
    if packbeast_green:
        support.add("G")
    land_types: set[str] = set()
    for zone, _, _, card in rows:
        if card is None:
            continue
        for face in card.faces:
            if zone == "main" and "Land" in face.type_line:
                land_types.update(set(face.type_line.split()) & BASIC_TYPES)
    # Establish mandatory spell colors first. Optional life/hybrid payments
    # do not turn rainbow artifact mana or one incidental land into a splash.
    # This still records those cards' colored payment in an established color.
    established: set[str] = set()
    for zone, _, _, card in rows:
        if (
            card is None
            or card.layout == "modal_dfc"
            or uses.get(card.key) == "noncast"
            or (
                card.key in (targets | NONCAST_WITHOUT_SUPPORT)
                and uses.get(card.key) != "normal_cast"
            )
        ):
            continue
        for face in _used_faces(card, uses.get(card.key)):
            payment_support = ordinary_support if card.key in lesson_targets else support
            if (
                uses.get(card.key) != "normal_cast"
                and not _has_color_payment(face, payment_support)
            ):
                continue
            established.update(re.findall(r"\{([WUBRG])\}", face.mana_cost))
    evidence = []
    combined: set[str] = set()
    for zone, name, qty, card in rows:
        if card is None:
            continue
        colors: set[str] = set()
        reason = "castable-spell-faces"
        use = uses.get(card.key)
        if use == "noncast" or (card.key in targets and use != "normal_cast"):
            reason = (
                "explicit-noncast-use"
                if use == "noncast"
                else profile + ":noncast-target"
            )
        else:
            unsupported = False
            payment_support = ordinary_support if card.key in lesson_targets else support
            grudge_support = gates_grudge and card.key == "Ancient Grudge"
            if grudge_support:
                payment_support = payment_support | {"G"}
            payment_frozen = frozenset(payment_support)
            for face in _used_faces(card, use):
                if (
                    use != "normal_cast"
                    and not _has_color_payment(face, payment_support)
                ):
                    unsupported = True
                    continue
                contribution = _cost_colors(
                    face, payment_frozen, frozenset(established)
                )
                contribution.update(_additional_casting_colors(face, payment_frozen))
                if use == "normal_cast":
                    contribution = set(re.findall(r"[WUBRG]", face.mana_cost)) or set(
                        face.colors
                    )
                    reason = "explicit-normal-cast-use"
                # Main and side use the same support requirement, including
                # color indicators and alternate faces. Explicit normal-use
                # exceptions remain available for reviewed casting plans.
                if use != "normal_cast":
                    contribution &= payment_frozen
                colors.update(contribution)
            if grudge_support and use != "normal_cast" and "G" in colors:
                reason = "pauper-battle-screech:gates-grudge-flashback-support"
            if use in {"front_only", "adventure_only"}:
                reason = "explicit-" + use.replace("_", "-") + "-use"
            if unsupported and not colors:
                reason = (
                    "learn:sideboard-lesson-without-ordinary-land-support"
                    if card.key in lesson_targets
                    else "scoped-noncast-without-land-color-support"
                    if use == "noncast_without_support"
                    else "sideboard-without-land-color-support"
                    if zone == "side"
                    else "main-without-land-color-support"
                )
            if (
                use != "normal_cast"
                and card.key in NONCAST_WITHOUT_SUPPORT
                and not colors <= (support & established)
            ):
                colors.clear()
                reason = "noncast-without-established-supported-color"
        named = tuple(COLOR_NAMES[c] for c in COLOR_NAMES if c in colors)
        if card.key in charm_uses:
            reason = "standard-fling:sideboard-charm"
        if card.key in optional_reasons:
            reason = optional_reasons[card.key]
        if packbeast_red and card.key == "Holdout Settlement" and zone == "main":
            reason = "pauper-packbeast:main-burn-red-support"
        if packbeast_mardu and card.key in {name for name, _ in PACKBEAST_MARDU_SOURCES} and zone == "main":
            reason = "pauper-packbeast:devotee-drum-black-red-support"
        if packbeast_green and card.key == "Winding Way" and zone == "main":
            reason = "pauper-packbeast:main-winding-way-green-support"
        combined.update(named)
        evidence.append(ColorContribution(card.key, zone, qty, named, reason))
    return DeckColors(
        frozenset(combined),
        tuple(evidence),
        missing,
        frozenset(COLOR_NAMES[c] for c in support),
        frozenset(land_types),
    )


def color_policy_subject() -> dict[str, object]:
    """Include maintained per-card policies independently of an engine bump."""
    return {
        "spell_payment": "main-and-side-non-rainbow-land-support-v2",
        "rainbow_sources": "capability-does-not-establish-color-v1",
        "learn_targets": "sideboard-only-lesson-needs-ordinary-land-support-v1",
        "fixed_mana_ability": "preserve-unrestricted-fixed-tap-color-v1",
        "incidental_land_sources": ["Gemstone Caverns", "singleton The Mycosynth Gardens"],
        "optional_cost_payment": "established-spell-colors-v1",
        "additional_casting_payment": "supported-flashback-kicker-v1",
        "mana_spent_effects": "supported-repeated-color-symbols-v1",
        "chosen_basic_land_type": "rainbow-capability-not-stable-color-support-v2",
        "card_use_modes": sorted(CARD_USES),
        "fling_secondary": {
            "cards": FLING_SECONDARY_FACES,
            "optional_fixed_source_counts": [0, 1, 2],
            "source_policy": "fixed-normal-lands-excluding-rainbow-v1",
            "zones": "main-and-side",
            "outside_exception": "default-faces; three-sources-unreviewed",
            "unresolved_use": "block-color-selection-when-sole-contribution-v1",
        },
        "noncast_without_established_support": sorted(NONCAST_WITHOUT_SUPPORT),
        "modern-goryos": sorted(GORYOS_TARGETS),
        "modern-creativity": sorted(CREATIVITY_TARGETS),
        "standard-spider-man": {
            "copy_source": "Superior Spider-Man",
            "source_zone": "main",
            "targets": sorted(STANDARD_SPIDER_COPY_TARGETS),
        },
        "pauper-packbeast": {
            "scope": "inherited-parent-core",
            "burn_route": {"main_cards": list(PACKBEAST_RED_ROUTE), "support": ["R"]},
            "mardu_route": {"main_sources": list(PACKBEAST_MARDU_SOURCES), "support": ["B", "R"]},
            "green_route": {"main_cards": list(PACKBEAST_GREEN_ROUTE), "support": ["G"]},
        },
        "pauper-battle-screech": {
            "main_gates": list(BATTLE_SCREECH_GRUDGE_GATES),
            "minimum_each": 1,
            "card": "Ancient Grudge",
            "support": ["G"],
            "scope": "card-only-flashback-main-and-side",
        },
        "standard-fling": {
            "core": list(STANDARD_FLING_CHARM_CORE),
            "cards": sorted(STANDARD_FLING_CHARMS),
            "count_scope": "total-across-approved-charm-cards",
            "main_count": 0,
            "side_count": 1,
            "use": "noncast",
        },
        "binding_domain_convention": "binding-positive-five-basic-types",
    }
