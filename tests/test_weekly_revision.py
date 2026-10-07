"""Counterexamples for PR 459; synthetic inputs, no network or publication."""
from copy import deepcopy
import json
import shutil

import pytest

from mtgmeta.mtgo import review_submission as review
from tools import weekly_maintenance as workflow
from test_landing_bundle import site


@pytest.fixture
def image_site(site):
    root, base, docs = site
    page = docs["current.json"]
    page["environment"] = {"rows": []}
    page["features"]["items"] = [
        {"destination_id": "deck:F1", "archetype_id": "a", "featured_cards": [{"name": x} for x in "ABCD"]},
        {"destination_id": "deck:F2", "archetype_id": "a", "featured_cards": [{"name": "X"}]}]
    workflow.write(base / "current.json", page)
    docs["features/2026-W38.json"]["features"] = page["features"]
    workflow.write(base / "features/2026-W38.json", docs["features/2026-W38.json"])
    docs["features/index.json"]["weeks"][0]["feature_count"] = 2
    workflow.write(base / "features/index.json", docs["features/index.json"])
    workflow.write(root / "stats/standard/archetype_names.json", {"names": [{"identity_id": "a", "display": {"en": "A", "zh": "甲"}}]})
    assets = root / "assets/js/phase8"
    assets.mkdir(parents=True)
    (assets / "archetype-visuals.js").write_text('const manaIdentities = Object.freeze({\n  standard: Object.freeze({\n    "a": Object.freeze(["u"]),\n  }),\n});')
    (root / "index.html").write_text('<script src="assets/js/phase8/fixture.js"></script>')
    (assets / "fixture.js").write_text("/* synthetic renderer */")
    manifest = {"cards": []}
    for name in "ABCDEX":
        relative = f"assets/card-cache/v1/{name}.jpg"
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(name.encode())
        manifest["cards"].append({"name": name, "local_path": relative,
                                  "uses": [{"format": "standard", "weeks": ["2026-W38"]}]})
    workflow.write(root / "assets/card-cache/v1/manifest.json", manifest)
    relative = "assets/card-localization/images/" + "a" * 64 + ".webp"
    (root / relative).parent.mkdir(parents=True)
    (root / relative).write_bytes(b"original Chinese X")
    workflow.write(root / "assets/card-localization/cards.json", {"X": {"zh_name": "叉", "local_image": relative}})
    return root


def change_f1(root):
    base = root / "stats/standard/mtgo/landing"
    for relative in ("current.json", "features/2026-W38.json"):
        doc = workflow.read(base / relative)
        doc["features"]["items"][0]["featured_cards"][-1]["name"] = "E"
        workflow.write(base / relative, doc)


@pytest.mark.parametrize("other_change", ["path", "chinese", "relocated", "none"])
def test_region_reuse_binds_every_unchanged_language_and_resource(image_site, tmp_path, other_change):
    before = image_site
    after = tmp_path.parent / (tmp_path.name + "-after")
    shutil.copytree(before, after)
    change_f1(after)
    if other_change in {"path", "relocated"}:
        manifest = workflow.read(after / "assets/card-cache/v1/manifest.json")
        manifest["cards"][-1]["local_path"] = "assets/card-cache/v1/other-X.jpg"
        (after / "assets/card-cache/v1/other-X.jpg").write_bytes(b"different art" if other_change == "path" else b"X")
        workflow.write(after / "assets/card-cache/v1/manifest.json", manifest)
    if other_change == "chinese":
        entry = workflow.read(after / "assets/card-localization/cards.json")["X"]
        (after / entry["local_image"]).write_bytes(b"new Chinese art")
    delta = workflow.page_delta(before, after, "standard")
    assert delta["state"] == ("feature_cards_only" if other_change in {"none", "relocated"} else "wider_change")
    assert delta["changed_features"] == ["deck:F1"]
    if other_change == "chinese":
        page = workflow.read(before / "stats/standard/mtgo/landing/current.json")
        assert review.preview_images(before, "standard", page) != review.preview_images(after, "standard", page)


def test_consumer_report_must_match_bound_regions(image_site):
    packet = review.preview_packet(image_site, "standard")
    rows = []
    for region, languages in packet["dimensions"]["final_page"]["image_subjects"].items():
        for language, cards in languages.items():
            rows.extend({"region": region, "language": language, "name": c["name"], "selected": c["image"],
                         "sha256": c["sha256"], "display_name": c["display_name"], "link": c["link"]} for c in cards)
    assert workflow.resource_selection_matches(packet, rows)
    rows[0]["sha256"] = "changed"
    assert not workflow.resource_selection_matches(packet, rows)


def test_missing_old_cache_uses_fixed_evidence_without_guessing(image_site, tmp_path):
    packet = review.preview_packet(image_site, "standard")
    after = tmp_path.parent / (tmp_path.name + "-revised")
    shutil.copytree(image_site, after)
    change_f1(after)
    (image_site / "assets/card-cache/v1/X.jpg").unlink()
    assert workflow.page_delta(image_site, after, "standard")["state"] == "evidence_required"
    assert workflow.page_delta(image_site, after, "standard", packet)["state"] == "feature_cards_only"
    change_f1(image_site)
    with pytest.raises(ValueError, match="original page"):
        workflow.page_delta(image_site, after, "standard", packet)


def test_old_preview_without_bilingual_evidence_is_unknown_not_accepted(image_site):
    current = review.preview_packet(image_site, "standard")
    old = deepcopy(current)
    del old["dimensions"]["final_page"]["image_subjects"]
    old["digest"] = workflow.digest({k: v for k, v in old.items() if k != "digest"})
    assert review.preview_validity(old, current)["state"] == "evidence_required"


def test_identical_selected_bytes_can_relocate_without_new_page_acceptance(image_site):
    before = review.preview_packet(image_site, "standard")
    path = image_site / "assets/card-cache/v1/manifest.json"
    manifest = workflow.read(path)
    manifest["cards"][-1]["local_path"] = "assets/card-cache/v1/moved-X.jpg"
    (image_site / "assets/card-cache/v1/moved-X.jpg").write_bytes(b"X")
    workflow.write(path, manifest)
    after = review.preview_packet(image_site, "standard")
    assert review.preview_validity(before, after)["state"] == "equivalent"


def test_admitted_facts_exclude_late_event_without_rechecking_products(tmp_path, monkeypatch):
    from test_mtgo_reviewed_publication import _repository
    from mtgmeta.mtgo import publication, landing, landing_editorial
    _repository(tmp_path)
    accepted = publication.resolve_scope(tmp_path, "standard")
    week = accepted.week.strftime("%G-W%V")
    workflow.write(tmp_path / "stats/standard/mtgo/meta.json", {"publication": {
        "week": week, "scope_digest": accepted.subject_digest}})
    observed = []
    def page(*args, **kwargs):
        observed.extend(str(e["event_id"]) for _, e in kwargs["_prepared_inputs"][0])
        kwargs["_review_facts"].update({"synthetic": "actual builder input scope"})
        return "ready", {}
    monkeypatch.setattr(landing, "build_document", page)
    monkeypatch.setattr(publication, "inspect_publication", lambda *_: pytest.fail("must not repeat full publication check"))
    facts = landing_editorial.build_admitted_content_facts(tmp_path, "standard", week)
    assert set(observed) == accepted.event_ids
    assert set(facts["pending_event_ids"]) == accepted.pending_event_ids
    assert accepted.pending_event_ids and not set(observed) & accepted.pending_event_ids
    workflow.write(tmp_path / "stats/standard/mtgo/decks_1w.json", {"classifier_digest": "different"})
    with pytest.raises(landing_editorial.MTGOLandingEditorialError, match="delivered statistics"):
        landing_editorial.build_admitted_content_facts(tmp_path, "standard", week, require_delivered_classifier=True)


def test_known_state_uses_maintained_review_path(tmp_path, monkeypatch):
    from datetime import date
    fake = {"rules": {}, "events": [], "processed": {}, "records": [], "all_top8": [],
        "page": {"week": {"id": "2026-W39"}, "source_event_ids": [], "classifier": {"digest": "a"},
                 "review_binding": {"machine_fact_digest": "b"}},
        "review_facts": {"value": 1}, "admitted_scope": {"scope_digest": "c"}, "pending_event_ids": []}
    monkeypatch.setattr(workflow.editorial, "build_admitted_content_facts", lambda *_, **kw: fake)
    monkeypatch.setattr(workflow.screening, "load_screening_policy", lambda *_: {})
    captured = []
    def candidates(events, rules, monday, known, *args, **kwargs):
        captured.append(known)
        return {"existing_changes": [], "new_archetypes": []}, None, None, None
    monkeypatch.setattr(workflow.editorial, "build_candidate_documents", candidates)
    workflow.write(tmp_path / "stats/pioneer/mtgo/landing/review/known_archetypes.json", {"known_ids": ["historically-known"]})
    output = tmp_path / "out"
    workflow.prepare_facts(tmp_path, "pioneer", "2026-W39", output)
    assert captured == [{"historically-known"}]
    assert not workflow.read(output / "facts.json")["known_state"]["initialized"]


def test_material_digest_allows_technical_equivalence_but_rejects_real_change(tmp_path, monkeypatch):
    monkeypatch.setattr(review, "content_dimensions", lambda *_: {"copy.zh": "用户原文"})
    make = lambda bindings, facts: review.make_content_packet(tmp_path, "pauper", "2026-W39", {}, {},
        {"names": []}, bindings=bindings, facts=facts)
    old = make({"classifier_digest": "A", "machine_fact_digest": "one"}, {"actual_count": 31})
    new = make({"classifier_digest": "B", "machine_fact_digest": "two"}, {"actual_count": 31})
    assert review.packet_validity(old, new)["state"] == "equivalent"
    changed = make({"classifier_digest": "B", "machine_fact_digest": "two"}, {"actual_count": 32})
    assert review.packet_validity(old, changed)["state"] == "changed"


def test_selected_new_environment_and_missing_resources_use_existing_contracts(tmp_path):
    from PIL import Image
    from tools import weekly_resources, build_archetype_visuals
    site, responses = tmp_path / "site", tmp_path / "responses"
    responses.mkdir()
    Image.new("RGB", (80, 50), "navy").save(responses / "crop.jpg")
    Image.new("RGB", (50, 80), "green").save(responses / "zh.webp")
    fixture = {"cards": {"Synthetic B": {"name": "Synthetic B", "image_uris": {
        "art_crop": "https://cards.scryfall.io/art_crop/front/synthetic.jpg"}}},
        "images": {"https://cards.scryfall.io/art_crop/front/synthetic.jpg": "crop.jpg",
                   "https://images.mtgch.com/zhs/synthetic.webp": "zh.webp"}}
    workflow.write(responses / "fixture.json", fixture)
    workflow.write(site / "assets/card-cache/v1/manifest.json", {"cards": []})
    workflow.write(site / "assets/card-localization/cards.json", {
        "Synthetic B": {"zh_name": "测试乙", "image_url": "https://images.mtgch.com/zhs/synthetic.webp"}})
    existing = site / "assets/images/representative-cards/pauper/synthetic-a.jpg"
    existing.parent.mkdir(parents=True)
    shutil.copyfile(responses / "crop.jpg", existing)
    untouched = site / "assets/images/representative-cards/pauper/unrelated.jpg"
    untouched.write_bytes(b"untouched")
    page = {"format": "pauper", "week": {"id": "2026-W39"}, "features": {"items": []},
            "environment": {"rows": [{"archetype_id": "new-type", "key_cards": [{"name": "Synthetic A"}, {"name": "Synthetic B"}]}]}}
    source = site / "assets/js/phase8/archetype-visuals.js"
    source.parent.mkdir(parents=True)
    source.write_text('const representativeCards = Object.freeze({\n  pauper: Object.freeze({\n    "old-type": Object.freeze([\n      Object.freeze({"name": "Synthetic A", "image": "../images/representative-cards/pauper/synthetic-a.jpg"}),\n    ]),\n  }),\n});')
    with pytest.raises(ValueError, match="Missing selected card"):
        weekly_resources.ensure(site, page)
    result = weekly_resources.ensure(site, page, fixture=responses / "fixture.json")
    assert len(result["downloaded"]) == 2 and result["resolved_names"] == ["Synthetic B"]
    config = {"formats": {"pauper": {"parents": {"new-type": ["Synthetic A", "Synthetic B"]},
                                      "subtypes": {}, "allow_parent_fallback_for_subtypes": []}}}
    build_archetype_visuals.generate(site, "pauper", identities={"new-type"}, config_override=config)
    assert '"old-type"' in source.read_text() and '"new-type"' in source.read_text()
    subjects = review.preview_image_subjects(site, "pauper", page)
    assert subjects["environment:new-type"]["zh"][1]["display_name"] == "测试乙"
    assert weekly_resources.ensure(site, page, fixture=responses / "fixture.json")["downloaded"] == []
    assert untouched.read_bytes() == b"untouched"


def test_joint_web_shows_source_date_totals_and_existing_names(tmp_path, monkeypatch):
    from mtgmeta import weekly_review
    row = {"event_id": "123", "rank": 1, "player": "Synthetic", "date": "2026-09-21",
           "identity": {"parent_chinese": "测试", "parent_english": "Test"},
           "source_locator": "event.json#/players/0"}
    mtgo = {"records": [row], "event_ids": ["123"], "classifier": {"subject_digest": "fixed"}}
    workflow.write(tmp_path / "event.json", {"players": [{"main_deck": [{"name": "Synthetic Card", "qty": 60}], "sideboard": []}]})
    workflow.write(tmp_path / "data/modern/melee/events/456.json", {
        "metadata": {"date": {"start": "2026-09-20"}, "name": "Synthetic Melee"}, "quality": {},
        "decklists": [{"participant_id": "p1", "status": "submitted", "game_format": "modern", "cards": [
            {"name": "Synthetic Card", "quantity": 60, "section": "main"},
            {"name": "Synthetic Card", "quantity": 15, "section": "sideboard"}]}]})
    melee = {"classifier": {"subject_digest": "fixed"}, "available_records": [
        {"participant_id": "p1", "rank": 2, "identity": row["identity"]}], "unavailable_records": []}
    monkeypatch.setattr(weekly_review, "build_mtgo_weekly_review", lambda *_: deepcopy(mtgo))
    monkeypatch.setattr(weekly_review, "build_melee_review", lambda *_, **kw: deepcopy(melee))
    monkeypatch.setattr(review, "full_classification_packet", lambda *_: {"synthetic": True})
    workflow.write(tmp_path / "lookup.json", {"Synthetic Card": {"zh_name": "测试牌"}})
    output = tmp_path / "web"
    output.mkdir()
    workflow.classification_material(tmp_path, "modern", "2026-W39", ["456"], output, tmp_path / "lookup.json")
    page = (output / "index.html").read_text(encoding="utf-8")
    # The shared carrier stores complete input; cards/totals are rendered when
    # the owner opens a row rather than expanding every deck in the HTML.
    embedded = json.loads(page.split('<script id="review-data" type="application/json">')[1].split('</script>')[0])
    assert embedded["localization"]["Synthetic Card"]["zh_name"] == "测试牌"
    one, two = embedded["material"]["members"]
    assert one["records"][0]["date"] == "2026-09-21"
    assert one["records"][0]["source_locator"] == "event.json#/players/0"
    assert two["records"][0]["reference"] == "melee:456:p1"
    assert two["records"][0]["date"] == "2026-09-20"
    assert two["records"][0]["event_name"] == "Synthetic Melee"
    assert sum(c["qty"] for c in two["records"][0]["main_deck"]) == 60
    assert sum(c["qty"] for c in two["records"][0]["sideboard"]) == 15
