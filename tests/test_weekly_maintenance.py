from copy import deepcopy
import json
from pathlib import Path

import pytest

from tools import weekly_maintenance as workflow
from mtgmeta.mtgo import review_submission as submissions


@pytest.fixture
def inputs(tmp_path):
    deck = {"token": "deck:00000000000000000001", "event_id": "1", "final_rank": 1,
            "deck_fingerprint_sha256": "a" * 64, "parent_id": "test", "subtype_id": None,
            "main_deck": [{"name": name, "qty": 4} for name in ("A", "B", "C", "D", "E")], "side_deck": []}
    source = {"format": "pioneer", "week": {"id": "2026-W39"}, "bindings": {"classifier_digest": "fixed"},
              "all_top8": [deck], "review": {"features": {"explicit_empty": True, "items": []},
              "top_copy": {"items": [{"order": 1, "text": {"zh": "用户原文", "en": "Owner text"}}]}}}
    page = {"format": "pioneer", "week": {"id": "2026-W39"}, "classifier": {"digest": "fixed"},
            "environment": {"rows": [{"archetype_id": "test", "display_name": "Test",
                                      "key_cards": [{"name": "A"}, {"name": "B"}]}]}}
    workflow.write(tmp_path / "stats/pioneer/mtgo/landing/current.json", page)
    return tmp_path, source, page


def test_displayed_default_requires_actual_page_not_configuration(inputs):
    root, source, page = inputs
    state = workflow.inventory(root, source, page)
    assert state["required_user"] == []
    assert workflow.inventory(root, source)["new_types"] == ["test"]
    changed = deepcopy(page)
    changed["environment"]["rows"][0]["key_cards"][0]["name"] = "C"
    assert workflow.inventory(root, source, changed)["environment"][0]["status"] == "changed"


def test_no_feature_does_not_waive_chinese(inputs):
    root, source, page = inputs
    source["review"]["top_copy"]["items"] = []
    assert workflow.inventory(root, source, page)["required_user"] == ["Landing 中文正文"]
    source["review"]["features"].pop("explicit_empty")
    assert "Feature 有无及选择" in workflow.inventory(root, source, page)["required_user"]


def test_feature_membership_and_missing_copy_are_independent(inputs):
    root, source, page = inputs
    source["review"]["features"] = {"items": [{"destination_id": source["all_top8"][0]["token"],
        "parent_id": "test", "subtype_id": None, "category": "new_deck",
        "featured_cards": ["A", "B", "C", "NOT IN DECK"], "positioning": {}}]}
    state = workflow.inventory(root, source, page)
    assert len(state["errors"]) == 1 and "第4张" in state["errors"][0]
    assert "F1: Feature 中文说明" in state["required_user"]
    assert "F1: Feature 英文草稿" in state["machine_pending"]
    assert source["review"]["features"]["items"][0]["featured_cards"][-1] == "NOT IN DECK"


def test_aliases_survive_removal_without_rebinding(inputs):
    root, source, page = inputs
    first = workflow.inventory(root, source, page)
    source["all_top8"][0]["deck_fingerprint_sha256"] = "b" * 64
    revised = workflow.inventory(root, source, page, first)
    assert list(revised["active_aliases"].values()) == ["F2"]
    assert revised["aliases"]["F1"] == first["aliases"]["F1"]
    assert workflow.inventory(root, source, page, revised)["aliases"] == revised["aliases"]


def test_changed_candidate_facts_get_new_reference(inputs):
    root, source, page = inputs
    first = workflow.inventory(root, source, page)
    source["candidate_evidence"] = [{"token": source["all_top8"][0]["token"],
                                     "reasons": [{"type": "share_increase", "delta_pp": 8}]}]
    revised = workflow.inventory(root, source, page, first)
    assert list(revised["active_aliases"].values()) == ["F2"]
    assert revised["aliases"]["F1"] == first["aliases"]["F1"]


def test_scope_mismatch_rejected(inputs):
    root, source, page = inputs
    page["format"] = "modern"
    with pytest.raises(ValueError, match="another format"):
        workflow.inventory(root, source, page)
    source["bindings"]["classifier_digest"] = "changed"
    with pytest.raises(ValueError, match="binding"):
        workflow.inventory(root, source)


def test_owner_input_is_not_later_page_or_english_acceptance():
    packet = submissions.make_packet("content", "pauper", "2026-W39",
        {"copy.zh": [{"order": 1, "text": "原文"}], "copy.en": [], "visual.feature.a": {}}, bindings={})
    values = {"copy.zh": packet["dimensions"]["copy.zh"]}
    envelope = workflow.record_input(packet, values, evidence="user-message:1", accepted_on="2026-09-30")
    assert submissions.decision_state(packet, envelope["decisions"])["accepted"] == ["copy.zh"]
    assert envelope["decisions"]["owner_input"]["values"] == values
    with pytest.raises(ValueError, match="Chinese only"):
        workflow.record_input(packet, {"copy.en": []}, evidence="user-message:1", accepted_on="2026-09-30")
    with pytest.raises(ValueError, match="differs"):
        workflow.record_input(packet, {"copy.zh": []}, evidence="user-message:1", accepted_on="2026-09-30")


def test_copy_on_write_preserves_base(tmp_path):
    base, candidate = tmp_path / "base.json", tmp_path / "candidate.json"
    workflow.write(base, {"value": 1})
    workflow.link_or_copy(base, candidate)
    workflow.write(candidate, {"value": 2})
    assert workflow.read(base) == {"value": 1}
    assert workflow.read(candidate) == {"value": 2}


def test_submitted_directory_never_overwritten(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, "require_private_output", lambda root, path: None)
    with pytest.raises(ValueError, match="Snapshot exists"):
        workflow.new_output(tmp_path, tmp_path)


def test_fixed_facts_work_while_old_landing_is_preserved(inputs):
    root, source, page = inputs
    old = deepcopy(page)
    old["week"]["id"] = "2026-W38"
    workflow.write(root / "stats/pioneer/mtgo/landing/current.json", old)
    facts = {"page": page, "bindings": source["bindings"], "environment_decks": source["all_top8"]}
    assert workflow.inventory(root, source, old, facts=facts)["required_user"] == []
    assert workflow.read(root / "stats/pioneer/mtgo/landing/current.json")["week"]["id"] == "2026-W38"
    facts["bindings"] = {"classifier_digest": "another"}
    with pytest.raises(ValueError, match="scope differs"):
        workflow.inventory(root, source, old, facts=facts)


def test_environment_web_includes_non_top8_full_decks(inputs):
    root, source, page = inputs
    ninth = deepcopy(source["all_top8"][0])
    ninth["final_rank"] = 9
    ninth["main_deck"] = [{"name": "Only in high-score deck", "qty": 2}]
    facts = {"page": page, "bindings": source["bindings"], "environment_decks": [ninth]}
    text = workflow.render_inventory(workflow.inventory(root, source, facts=facts))
    assert "第9名完整主备牌" in text and "2 Only in high-score deck" in text


def test_regional_acceptance_cannot_cover_a_different_or_unaccepted_page():
    before = submissions.make_packet("preview", "pauper", "2026-W39", {"final_page": {"value": 1}}, bindings={})
    after = submissions.make_packet("preview", "pauper", "2026-W39", {"final_page": {"value": 2}}, bindings={})
    receipt = submissions.record_decision(before, None, ["final_page"], evidence="test-owner-before",
        accepted_on="2026-09-30", entrypoint="http://localhost/before")
    old = {"submission": before, "decisions": receipt}
    check = {"state": "passed", "preview_digest": after["digest"], "only_feature": "deck:one"}
    delta = {"before": before, "after": after, "state": "feature_cards_only", "changed_features": ["deck:one"]}
    kw = {"evidence": "test-owner-region", "accepted_on": "2026-09-30", "entrypoint": "http://localhost/after"}
    accepted = workflow.accept_page(after, check, previous=old, delta=delta, **kw)
    assert submissions.decision_state(after, accepted["decisions"])["pending"] == []
    assert accepted["decisions"]["scoped_page_continuation"]["previous"] == old
    with pytest.raises(ValueError, match="prior accepted"):
        workflow.accept_page(after, check, **kw)
    with pytest.raises(ValueError, match="does not bind"):
        workflow.accept_page(before, check, **kw)
    delta["state"] = "wider_change"
    with pytest.raises(ValueError, match="prior accepted"):
        workflow.accept_page(after, check, previous=old, delta=delta, **kw)


def test_owner_input_keeps_unchanged_english_decision():
    packet = submissions.make_packet("content", "pauper", "2026-W39",
        {"copy.zh": "原文", "copy.en": "Translation"}, bindings={})
    prior = submissions.record_decision(packet, None, ["copy.en"], evidence="owner-english",
        accepted_on="2026-09-30", entrypoint="http://localhost/accepted")
    result = workflow.record_input(packet, {"copy.zh": "原文"}, previous=prior,
        evidence="owner-original", accepted_on="2026-09-30")
    assert submissions.decision_state(packet, result["decisions"])["pending"] == []
    assert result["decisions"]["decisions"]["copy.en"] == prior["decisions"]["copy.en"]


def test_card_localization_uses_only_unambiguous_selected_deck_names(inputs):
    _, source, _ = inputs
    source["review"]["features"] = {"items": [{"destination_id": source["all_top8"][0]["token"],
        "featured_cards": ["甲", "B", "C", "D"]}]}
    revised, changes = workflow.normalize_selected_cards(source, {"A": {"zh_name": "甲"}})
    assert revised["review"]["features"]["items"][0]["featured_cards"] == ["A", "B", "C", "D"]
    assert source["review"]["features"]["items"][0]["featured_cards"][0] == "甲"
    assert changes[0]["input"] == "甲"
    with pytest.raises(ValueError, match="Ambiguous"):
        workflow.normalize_selected_cards(source, {"A": {"zh_name": "甲"}, "B": {"zh_name": "甲"}})


def test_retained_catalog_cannot_drift_behind_same_binding(inputs):
    root, source, page = inputs
    source["bindings"]["link_catalog_digest"] = workflow.editorial.document_digest(source["all_top8"])
    source["all_top8"][0]["main_deck"][0]["qty"] = 3
    with pytest.raises(ValueError, match="catalog changed"):
        workflow.inventory(root, source, page)


def test_displayed_policy_accepts_only_unchanged_visual_and_names(tmp_path, monkeypatch):
    workflow.write(tmp_path / "stats/pioneer/mtgo/landing/current.json", {
        "environment": {"rows": [{"archetype_id": "test", "key_cards": [{"name": "A"}]}]}})
    workflow.write(tmp_path / "stats/pioneer/archetype_names.json", {
        "names": [{"identity_id": "test", "display": {"zh": "测试", "en": "Test"}}]})
    monkeypatch.setattr(submissions, "visual_colors", lambda *_: {"test": ["U"]})
    dimensions = {"visual.environment.test": {"colors": ["U"], "cards": ["A"]},
                  "name.pioneer|test|none.zh": "测试", "name.pioneer|test|none.en": "Test"}
    packet = submissions.make_packet("content", "pioneer", "2026-W39", dimensions, bindings={})
    kw = {"evidence": "standing-owner-policy", "accepted_on": "2026-09-30"}
    result = workflow.adopt_displayed(packet, tmp_path, **kw)
    assert submissions.decision_state(packet, result["decisions"])["accepted"] == ["visual.environment.test"]
    dimensions["visual.environment.test"]["colors"] = ["R"]
    changed = submissions.make_packet("content", "pioneer", "2026-W39", dimensions, bindings={})
    assert workflow.adopt_displayed(changed, tmp_path, **kw)["decisions"]["displayed_environment_policy"]["keys"] == []


def test_data_wrapper_orders_existing_producers_and_binds_resume(tmp_path, monkeypatch):
    from datetime import date
    from types import SimpleNamespace
    from mtgmeta.melee import classification, opportunities, stats, matchup, publish
    from mtgmeta.mtgo import publication
    calls = []
    monkeypatch.setattr(workflow, "require_private_output", lambda *_: None)
    monkeypatch.setattr(publication, "resolve_scope", lambda *_: SimpleNamespace(week=date(2026, 9, 21)))
    for name, module in (("classification", classification), ("opportunities", opportunities), ("stats", stats), ("matchup", matchup), ("publish", publish)):
        monkeypatch.setattr(module, "main", lambda args, name=name: calls.append(name) or 0)
    def stage(root, formats, **kwargs):
        calls.append(("stage", formats, kwargs))
        return {"stage": str(tmp_path / "staged")}
    monkeypatch.setattr(publication, "stage_publications", stage)
    plan = {"week": "2026-W39", "mtgo_formats": ["modern"], "melee": [{
        "format": "modern", "event_id": "405588", "steps": ["publish", "stats", "classification", "matchup", "opportunities"]}]}
    result = workflow.stage_data(tmp_path, plan)
    assert calls[:5] == ["classification", "opportunities", "stats", "matchup", "publish"]
    assert calls[-1][2] == {"include_landing": False, "execute": False, "resume_stage": None}
    calls.clear()
    resumed = workflow.stage_data(tmp_path, plan, tmp_path / "staged", result)
    assert len(calls) == 1 and calls[0][0] == "stage"
    assert resumed["reused_melee"] == result["melee_completed"]
    with pytest.raises(ValueError, match="same plan"):
        workflow.stage_data(tmp_path, {**plan, "melee": []}, tmp_path / "staged", result)
    assert len(calls) == 1
    calls.clear()
    monkeypatch.setattr(classification, "main", lambda args: 1)
    with pytest.raises(ValueError, match="classification failed"):
        workflow.stage_data(tmp_path, plan)
    assert calls == []  # No stats, MTGO stage, or delivery after failure.
