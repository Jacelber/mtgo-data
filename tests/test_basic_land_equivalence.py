from mtgmeta.card_names import (
    BASIC_LAND_PRINTING_PAIRS,
    canonical_basic_land_name,
    equivalent_basic_land_names,
)
from mtgmeta.classifier_features import (
    CardFeatures,
    SemanticFeatureManifest,
    augment_semantic_counts,
    mana_source_marker,
)
from mtgmeta.deck import count_card, deck_to_counts
from mtgmeta.mtgo import landing_screening, stats


def _card(name: str, qty: int) -> dict[str, object]:
    return {"name": name, "qty": qty}


def test_all_basic_land_printing_pairs_share_one_canonical_name():
    assert len(BASIC_LAND_PRINTING_PAIRS) == 6
    for canonical, snow_covered in BASIC_LAND_PRINTING_PAIRS:
        assert canonical_basic_land_name(canonical) == canonical
        assert canonical_basic_land_name(snow_covered) == canonical
        assert equivalent_basic_land_names(canonical) == (canonical, snow_covered)
        assert equivalent_basic_land_names(snow_covered) == (canonical, snow_covered)


def test_basic_land_canonicalization_does_not_apply_unrelated_card_aliases():
    assert canonical_basic_land_name("Nia, Skysail Storyteller") == (
        "Nia, Skysail Storyteller"
    )


def test_classifier_card_counts_merge_ordinary_and_snow_covered_printings():
    main, side = deck_to_counts(
        {
            "main_deck": [_card("Island", 1), _card("Snow-Covered Island", 2)],
            "sideboard": [_card("Snow-Covered Island", 1)],
        }
    )

    assert count_card("Island", "main", main, side) == 3
    assert count_card("Snow-Covered Island", "main", main, side) == 3
    assert count_card("Island", "any", main, side) == 4


def test_snow_covered_basic_land_inherits_ordinary_mana_source_feature():
    empty = CardFeatures(frozenset(), frozenset(), False, False)
    manifest = SemanticFeatureManifest(
        schema_version="1.0.0",
        cards={
            "Island": CardFeatures(frozenset({"blue"}), frozenset(), False, False),
            "Unrelated": empty,
        },
    )

    main, side = augment_semantic_counts(
        {"Snow-Covered Island": 2},
        {},
        manifest,
    )

    assert main[mana_source_marker("blue")] == 2
    assert side == {}


def test_construction_vectors_merge_basic_land_printings_but_fingerprints_do_not():
    ordinary = {"main_deck": [_card("Island", 3)], "side_deck": []}
    snow_covered = {
        "main_deck": [_card("Snow-Covered Island", 3)],
        "side_deck": [],
    }
    mixed = {
        "main_deck": [_card("Island", 1), _card("Snow-Covered Island", 2)],
        "side_deck": [],
    }

    assert stats.deck_vector(ordinary) == {"Island": 3}
    assert stats.deck_vector(snow_covered) == {"Island": 3}
    assert stats.deck_vector(mixed) == {"Island": 3}
    assert stats.deck_diff(stats.deck_vector(snow_covered), {"Island": 3}) == {
        "fewer": [],
        "more": [],
    }
    assert landing_screening.deck_fingerprint(ordinary) != landing_screening.deck_fingerprint(
        snow_covered
    )
