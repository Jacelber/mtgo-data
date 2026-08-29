from mtgmeta.card_names import (
    card_name_lookup_candidates,
    front_face_card_name,
)


def test_front_face_card_name_preserves_existing_classification_behavior():
    assert front_face_card_name(" Front Face // Back Face ") == "Front Face"
    assert front_face_card_name("Single Face") == "Single Face"


def test_lookup_candidates_use_maintained_alias_and_front_face():
    assert card_name_lookup_candidates("Nia, Skysail Storyteller") == (
        "Gwen Stacy // Ghost-Spider",
        "Gwen Stacy",
    )


def test_lookup_candidates_expand_one_legacy_slash_without_touching_card_text_slashes():
    assert card_name_lookup_candidates("Fire/Ice") == (
        "Fire/Ice",
        "Fire // Ice",
        "Fire",
    )
    assert card_name_lookup_candidates("SP//dr, Piloted by Peni") == (
        "SP//dr, Piloted by Peni",
    )
