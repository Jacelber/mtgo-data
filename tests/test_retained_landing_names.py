"""Retired display names reuse decisions, without reviving old classifications."""
import json

import pytest
import yaml

from mtgmeta.mtgo import landing_editorial as names, review_submission as review


@pytest.fixture
def retained(tmp_path, monkeypatch):
    page = {"week": {"id": "2026-W40"}, "environment": {"rows": [{"archetype_id": "retired"}]}}
    path = tmp_path / "stats/modern/mtgo/landing/current.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(page))
    bundle = {"week": "2026-W40", "documents": {"landing": page, "environment_decks": {}}}
    catalog = {"schema_version": "1.0.0", "names": [{"format": "modern", "parent_id": "active",
        "subtype_id": None, "english": "Active", "chinese": "当前", "review_status": "approved",
        "identity_key": "modern|active|none"}]}
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/mtgo_archetype_names.yaml").write_text(yaml.safe_dump(catalog), encoding="utf-8")
    monkeypatch.setattr(names, "validate_name_catalog", lambda *a, **kw: {})
    monkeypatch.setattr(names, "_taxonomy_rows", lambda *a: catalog["names"])
    packet = review.make_packet("preview", "modern", "2026-W40", {"final_page": {"names": {
        "retired": {"en": "Retired", "zh": "旧名称"}, "unused": {"en": "Unused", "zh": "未使用"}}}}, bindings={})
    receipt = review.record_decision(packet, None, ["final_page"], evidence="synthetic-only",
                                    accepted_on="2026-10-07", entrypoint="fixture://preview")
    ledger = {"records": [{"week": "2026-W40", "formats": {"modern": {
        "preview_acceptance": {"submission": packet, "decisions": receipt}}}}]}
    return tmp_path, bundle, ledger


def build(fixture):
    root, bundle, ledger = fixture
    (root / "stats/modern/mtgo/landing/current.json").write_text(json.dumps(bundle["documents"]["landing"]))
    (root / "configs/mtgo_weekly_review_completions.yaml").write_text(yaml.safe_dump(ledger), encoding="utf-8")
    return names.build_public_name_contract(root, "modern")


def test_only_needed_approved_names_retained_and_removed_when_page_changes(retained):
    old = build(retained)
    assert {x["identity_id"] for x in old["names"]} == {"active", "retired"}
    assert next(x for x in old["names"] if x["identity_id"] == "retired")["display"]["zh"] == "旧名称"
    retained[1]["documents"]["landing"]["environment"]["rows"] = [{"archetype_id": "active"}]
    new = build(retained)
    assert [x["identity_id"] for x in new["names"]] == ["active"]
    assert old["provenance"]["classifier_identity_digest"] == new["provenance"]["classifier_identity_digest"]
    assert old["provenance"]["name_catalog_digest"] == new["provenance"]["name_catalog_digest"]
    assert old["provenance"]["projection_subject_digest"] != new["provenance"]["projection_subject_digest"]


@pytest.mark.parametrize("damage", ["decision", "week", "format", "name", "tampered"])
def test_unaccepted_or_wrong_scope_cannot_supply_names(retained, damage):
    record = retained[2]["records"][0]
    accepted = record["formats"]["modern"]["preview_acceptance"]
    if damage == "decision": accepted["decisions"] = {}
    elif damage == "week": record["week"] = "2026-W39"
    elif damage == "format": record["formats"] = {"standard": record["formats"]["modern"]}
    elif damage == "name": retained[1]["documents"]["landing"]["environment"]["rows"][0]["archetype_id"] = "not-approved"
    else: accepted["submission"]["dimensions"]["final_page"]["names"]["retired"]["zh"] = "Changed"
    with pytest.raises((ValueError, names.MTGOLandingEditorialError)):
        build(retained)


def test_expanded_deck_and_feature_require_subtype_names():
    page = {"environment": {"rows": [{"archetype_id": "a"}]},
            "features": {"items": [{"archetype_id": "b", "subtype_id": "feature"}]}}
    decks = {"decks": {"A": {"archetype_id": "a", "subtypes": [{"id": "detail"}]}}}
    assert names.landing_name_identities(page, decks) == {"a", "a/detail", "b", "b/feature"}


def test_empty_subtype_best_deck_is_not_the_expanded_title():
    page = {"environment": {"rows": [{"archetype_id": "a"}]}}
    best = {"player": "winner", "event_id": "123", "final_rank": 1}
    decks = {"decks": {"A": {"archetype_id": "a", "best_deck": best, "subtypes": [
        {"id": "empty", "best_deck": None}, {"id": "winner", "best_deck": best}]}}}
    assert names.landing_name_identities(page, decks) == {"a", "a/winner"}
