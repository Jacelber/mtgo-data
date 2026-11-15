"""Missing private input never authorizes changing already published content."""
from copy import deepcopy
from hashlib import sha256
import json
from types import SimpleNamespace

import pytest

from mtgmeta.mtgo.publication import PublicationError, _restate_published_landing


def fixture(tmp_path, monkeypatch):
    from mtgmeta.mtgo import landing, landing_bundle, landing_editorial, normalize
    from mtgmeta import classifier
    root, stage = tmp_path / "source", tmp_path / "candidate"
    relative = "stats/standard/mtgo/landing"
    before = {key: {"value": key} for key in landing.CLASSIFIER_RESTATEMENT_MATERIAL_FIELDS}
    before.update(format="standard", week={"id": "2026-W45"}, classifier={"digest": "old"},
        review_binding={"classifier_digest": "old", "machine_fact_digest": "old-facts",
                        "pickup_document_digest": "original-private-review", "summary_fact_digest": "original-content"},
        weekly_summary={"items": [{"text": {"zh": "原文", "en": "Original prose"}}]},
        features={"items": [{"archetype_id": "unchanged", "subtype_id": None,
            "headline": {"en": "Same Deck", "zh": "相同构筑"}, "deck": {"main_deck": [], "side_deck": [{"name": "Sideboard card", "qty": 1}]},
            "featured_cards": [{"name": "Original representative"}]}]})
    for base in (root, stage):
        path = base / relative
        (path / "features").mkdir(parents=True)
        (path / "current.json").write_text(json.dumps(before))
        (path / "features/2026-W45.json").write_text(json.dumps({"classifier_digest": "old", "features": before["features"]}))
        (path / "features/2026-W44.json").write_text('retained earlier archive')
    original = root / relative / "current.json"
    (root / "stats/standard/mtgo/meta.json").write_text(json.dumps({"publication": {"artifacts": {
        f"{relative}/current.json": sha256(original.read_bytes()).hexdigest()}}}))
    facts = deepcopy(before)
    facts["classifier"] = {"digest": "new"}
    facts["review_binding"] = {"classifier_digest": "new", "machine_fact_digest": "new-facts"}
    facts["features"] = {"items": []}
    facts["weekly_summary"] = {"items": []}
    monkeypatch.setattr(landing, "build_document", lambda *a, **kw: ("not_applicable", facts))
    monkeypatch.setattr(landing, "generate_week_data", lambda *a: {"range": "fixed-week-range"})
    monkeypatch.setattr(landing, "validate_document", lambda doc: None)
    monkeypatch.setattr(landing_bundle, "inspect_bundle", lambda *a: {})
    monkeypatch.setattr(normalize, "load_rules_for_format", lambda *a: None)
    result = SimpleNamespace(status="classified", archetype_id="unchanged", subtype_id=None)
    def classify(_rules, deck):
        assert deck["sideboard"] == [{"name": "Sideboard card", "qty": 1}]
        return result
    monkeypatch.setattr(classifier, "classify_deck", classify)
    names = {("standard", "unchanged", None): {"en": "Same Deck", "zh": "相同构筑"}}
    monkeypatch.setattr(landing_editorial, "load_name_catalog", lambda *a: names)
    return root, stage, relative, before, facts, result, names


def test_identical_published_content_rebinds_without_inventing_acceptance(tmp_path, monkeypatch):
    root, stage, relative, before, *_ = fixture(tmp_path, monkeypatch)
    source_bytes = (root / relative / "current.json").read_bytes()
    _restate_published_landing(root, stage, "standard", before)
    after = json.loads((stage / relative / "current.json").read_bytes())
    assert after["classifier"]["digest"] == "new"
    assert after["review_binding"]["classifier_digest"] == "new"
    assert after["review_binding"]["pickup_document_digest"] == "original-private-review"
    assert after["review_binding"]["summary_fact_digest"] == "original-content"
    assert after["weekly_summary"] == before["weekly_summary"] and after["features"] == before["features"]
    assert (stage / relative / "features/2026-W44.json").read_text() == 'retained earlier archive'
    assert (root / relative / "current.json").read_bytes() == source_bytes
    assert not (stage / relative / "review").exists()


@pytest.mark.parametrize("field", ["environment", "populations", "source_event_ids"])
def test_changed_published_facts_still_require_review(tmp_path, monkeypatch, field):
    root, stage, _, before, facts, *_ = fixture(tmp_path, monkeypatch)
    facts[field] = {"changed": True}
    with pytest.raises(PublicationError, match="facts changed"):
        _restate_published_landing(root, stage, "standard", before)


def test_changed_selected_identity_or_name_still_requires_review(tmp_path, monkeypatch):
    root, stage, _, before, _, result, names = fixture(tmp_path, monkeypatch)
    result.subtype_id = "new-choice"
    with pytest.raises(PublicationError, match="classification or name changed"):
        _restate_published_landing(root, stage, "standard", before)
    result.subtype_id = None
    names[("standard", "unchanged", None)]["zh"] = "不同名称"
    with pytest.raises(PublicationError, match="classification or name changed"):
        _restate_published_landing(root, stage, "standard", before)


def test_unbound_local_page_is_not_accepted_content(tmp_path, monkeypatch):
    root, stage, relative, before, *_ = fixture(tmp_path, monkeypatch)
    (root / relative / "current.json").write_text('{}')
    with pytest.raises(PublicationError, match="not bound"):
        _restate_published_landing(root, stage, "standard", before)


def test_an_arbitrary_caller_document_is_not_the_published_source(tmp_path, monkeypatch):
    root, stage, _, before, *_ = fixture(tmp_path, monkeypatch)
    before["weekly_summary"]["items"] = [{"text": "unapproved replacement"}]
    with pytest.raises(PublicationError, match="not bound"):
        _restate_published_landing(root, stage, "standard", before)
