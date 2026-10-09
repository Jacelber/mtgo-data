"""Feature selections survive taxonomy changes through exact deck references."""
from copy import deepcopy

import pytest

from mtgmeta.mtgo import landing_editorial as editorial


@pytest.fixture
def selection():
    token = "deck:" + "a" * 20
    deck = {"token": token, "event_id": "123", "deck_id": "a" * 20,
            "deck_fingerprint_sha256": "b" * 64, "final_rank": 1,
            "player": "Player", "player_count": 32, "starttime": "2026-08-16",
            "parent_id": "retired", "subtype_id": None,
            "main_deck": [{"name": "Card A", "qty": 60}], "side_deck": []}
    document = {"format": "standard", "week": {"id": "2026-W33"}, "all_top8": [deck],
        "review": {"top_copy": {"items": [{"order": 1, "text": {"zh": token, "en": token}}]},
                   "features": {"items": [{"destination_id": token, "category": "new_technology",
                       "source_order": 1, "positioning": {"zh": "原文", "en": "Original copy"},
                       "featured_cards": ["Card A"], "supporting_facts": []}]}}}
    current = deepcopy(deck)
    current.update(parent_id="lifegain", subtype_id="orzhov")
    return document, {token: current}


def test_references_use_current_classification_and_keep_owner_content(selection, monkeypatch, tmp_path):
    document, catalog = selection
    before = deepcopy(document)
    monkeypatch.setattr(editorial, "build_top8_subject", lambda *args: pytest.fail("Reclassified a retained catalog"))
    decks = editorial.resolve_review_decks(tmp_path, document, mtgo_catalog=catalog)
    names = {("standard", "lifegain", "orzhov"): {"zh": "黑白回血", "en": "Orzhov Lifegain"}}
    material = editorial.materialize_review(document, names, decks=decks)
    feature = material["features"][0]
    assert (feature["archetype_id"], feature["subtype_id"]) == ("lifegain", "orzhov")
    assert feature["title"] == names[("standard", "lifegain", "orzhov")]
    assert feature["destination_id"] == document["all_top8"][0]["token"]
    assert feature["positioning"] == {"zh": "原文", "en": "Original copy"}
    assert feature["featured_cards"] == [{"name": "Card A"}]
    link = material["weekly_summary"][0]["deck_links"][0]
    assert link["deck"]["archetype_id"] == "lifegain"
    assert link["label"]["en"] == "Orzhov Lifegain · Player · Rank 1"
    assert document == before


@pytest.mark.parametrize("change", ["missing", "fingerprint", "rank", "source", "unknown"])
def test_reference_rejects_wrong_or_unclassified_deck(selection, tmp_path, change):
    document, catalog = selection
    deck = next(iter(catalog.values()))
    if change == "missing":
        catalog.clear()
    elif change == "fingerprint":
        deck["deck_fingerprint_sha256"] = "c" * 64
    elif change == "rank":
        deck["final_rank"] = 2
    elif change == "source":
        deck["source"] = "melee"
    else:
        deck["parent_id"] = "unknown"
    with pytest.raises(editorial.MTGOLandingEditorialError):
        editorial.resolve_review_decks(tmp_path, document, mtgo_catalog=catalog)


def test_legacy_feature_identity_is_not_used(selection, tmp_path):
    document, catalog = selection
    document["review"]["features"]["items"][0].update(parent_id="retired", subtype_id=None)
    decks = editorial.resolve_review_decks(tmp_path, document, mtgo_catalog=catalog)
    material = editorial.materialize_review(document,
        {("standard", "lifegain", "orzhov"): {"zh": "黑白回血", "en": "Orzhov Lifegain"}}, decks=decks)
    assert material["features"][0]["archetype_id"] == "lifegain"
