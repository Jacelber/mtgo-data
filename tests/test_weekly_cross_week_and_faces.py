"""PR 459 second review: real readers with isolated data and finite card responses."""
from copy import deepcopy
import shutil

import pytest

from tools import weekly_maintenance as flow, weekly_resources
from mtgmeta.mtgo import publication, review_submission as review, landing_editorial as editorial


@pytest.fixture
def retained_content(tmp_path):
    # Only this format's necessary retained input/configuration; no archived
    # review outputs, browser cache, publication or mutable production files.
    root = tmp_path / "repository"
    for folder in ("configs", "schemas"):
        shutil.copytree(flow.ROOT / folder, root / folder)
    for pattern in ("data/pauper/*.json", "my_archetypes/pauper.yaml",
                    "stats/pauper/mtgo/meta.json", "stats/pauper/mtgo/decks_1w.json",
                    "stats/pauper/mtgo/landing/current.json",
                    "stats/pauper/mtgo/landing/review/known_archetypes.json",
                    "assets/js/phase8/archetype-visuals.js"):
        for path in flow.ROOT.glob(pattern):
            target = root / path.relative_to(flow.ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    registry_path = root / publication.ADMISSION_PATH
    registry = flow.read(registry_path)
    registry["records"] = []  # This fixture exercises content, not archive health.
    admission = registry["data_admissions"]["formats"]["pauper"]
    admission["weekly_acceptances"] = [r for r in admission["weekly_acceptances"] if r["week"] <= "2026-W39"]
    flow.write(registry_path, registry)
    admitted, events = publication._resolve_scope(root, "pauper")
    for relative, event in events:
        if str(event["event_id"]) in admitted.pending_event_ids:
            event["starttime"] = "2026-09-26T12:00:00Z"  # Unadmitted late W39 input.
            flow.write(root / relative, event)
    facts_dir = tmp_path / "facts"
    facts_dir.mkdir()
    # Live repository metadata advances; this fixture starts from W39 delivery.
    admitted, _ = publication._resolve_scope(root, "pauper")
    metadata = flow.read(root / "stats/pauper/mtgo/meta.json")
    metadata["publication"].update(week="2026-W39", scope_digest=admitted.subject_digest)
    flow.write(root / "stats/pauper/mtgo/meta.json", metadata)
    flow.prepare_facts(root, "pauper", "2026-W39", facts_dir)
    source, facts = flow.read(facts_dir / "source.json"), flow.read(facts_dir / "facts.json")
    source["review"] = deepcopy(flow.read(flow.ROOT / "stats/pauper/mtgo/landing/review/2026-W39.yaml")["review"])
    packet = review.make_content_packet(root, "pauper", "2026-W39", source["review"], facts["page"]["environment"],
        editorial.load_name_catalog_document(root / editorial.DEFAULT_NAME_CATALOG),
        bindings=source["bindings"], facts=facts["review_facts"])
    receipt = review.record_decision(packet, None, list(packet["dimensions"]),
        evidence="SYNTHETIC isolated accepted content", accepted_on="2026-09-30", entrypoint="private://synthetic")
    receipt["admitted_scope"] = facts["admitted_scope"]
    source["acceptance"] = {"submission": packet, "decisions": receipt}
    from tools.import_landing_conversation import import_content
    path = import_content(root, source)
    return root, path, facts


def test_new_week_delivery_keeps_old_content_readable_and_detects_real_changes(retained_content, monkeypatch):
    from datetime import date
    from mtgmeta.weekly_review import build_mtgo_weekly_review
    root, path, facts = retained_content
    source = editorial.load_review_document(path, root / editorial.DEFAULT_REVIEW_SCHEMA)
    original_source = path.read_bytes()
    before = review.content_packet(root, source)
    assert review.resume_summary(root, "pauper", "2026-W39")["content"] == "accepted_recorded"

    # A real new weekly admission (synthetic event/decision), not a mocked helper.
    event = flow.read(next((root / "data/pauper").glob("*.json")))
    event.update(event_id="90000000", starttime="2026-09-29T12:00:00Z")
    deck = source["all_top8"][0]
    event["players"] = [{"player": "Synthetic W40 player", "loginid": "1", "final_rank": 1,
                         "swiss_score": 9, "main_deck": deck["main_deck"], "sideboard": deck["side_deck"]}]
    flow.write(root / "data/pauper/90000000.json", event)
    material = build_mtgo_weekly_review(root, "pauper", "2026-W40")
    for row in material["records"]:
        relative, pointer = row["source_locator"].split("#", 1)
        player = flow.read(root / relative)["players"][int(pointer.split("/")[-1])]
        row.update(main_deck=player["main_deck"], sideboard=player["sideboard"],
                   reference=f"mtgo:{row['event_id']}:{row['rank']}")
    packet = review.full_classification_packet(material)
    receipt = review.record_decision(packet, None, list(packet["dimensions"]),
        evidence="SYNTHETIC W40 data admission", accepted_on="2026-10-06", entrypoint="private://synthetic")
    class TestDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 10, 6)
    monkeypatch.setattr(publication, "date", TestDate)
    admission = publication.acceptance_record(root, "pauper", "2026-W40", accepted_on="2026-10-06",
        expected_review_digest=material["classification_review_digest"], evidence="SYNTHETIC W40 data admission")
    admission["classification_acceptance"] = {"submission": packet, "decisions": receipt}
    registry = flow.read(root / publication.ADMISSION_PATH)
    registry["data_admissions"]["formats"]["pauper"]["weekly_acceptances"].append(admission)
    flow.write(root / publication.ADMISSION_PATH, registry)
    meta = flow.read(root / "stats/pauper/mtgo/meta.json")
    meta["publication"] = publication.publication_binding(root, "pauper")
    flow.write(root / "stats/pauper/mtgo/meta.json", meta)
    assert publication.resolve_scope(root, "pauper").week.strftime("%G-W%V") == "2026-W40"

    after = review.content_packet(root, source)
    assert review.packet_validity(before, after)["state"] in {"current", "equivalent"}
    status = review.resume_summary(root, "pauper", "2026-W39")
    assert status["content"] == "accepted_recorded" and "content_problem" not in status
    assert path.read_bytes() == original_source
    assert facts["pending_event_ids"]  # Retained late W39 event never inherited admission.
    assert set(facts["pending_event_ids"]).isdisjoint(publication.resolve_scope(root, "pauper").event_ids)
    assert set(after["bindings"]["source_event_ids"]).isdisjoint(facts["pending_event_ids"] + ["90000000"])
    for binding in ({**facts["admitted_scope"], "week": "2026-W40"},
                    {**facts["admitted_scope"], "scope_digest": "0" * 64}):
        altered = deepcopy(source)
        altered["acceptance"]["decisions"]["admitted_scope"] = binding
        with pytest.raises(editorial.MTGOLandingEditorialError, match="admission"):
            review.content_packet(root, altered)
    with pytest.raises(editorial.MTGOLandingEditorialError, match="delivered admission"):
        editorial.build_admitted_content_facts(root, "pauper", "2026-W39", require_delivered_classifier=True)

    changed = deepcopy(source)
    changed["review"]["top_copy"]["items"][0]["text"]["zh"] += "实际修改"
    with pytest.raises(ValueError):
        review.content_packet(root, changed)
    prior_event = root / next(relative for relative, event in publication.retained_events(root, "pauper")
                             if str(event["event_id"]) == source["bindings"]["source_event_ids"][0])
    value = flow.read(prior_event)
    value["players"][0]["main_deck"][0]["qty"] += 1
    flow.write(prior_event, value)
    with pytest.raises(ValueError, match="source binding"):
        review.content_packet(root, source)
    assert review.resume_summary(root, "pauper", "2026-W39")["content"] == "needs_repair"


def test_selected_resources_advance_only_current_format_cache_window(tmp_path):
    site = tmp_path / "site"
    path = site / "assets/card-cache/v1/manifest.json"
    other = {"format": "modern", "selected_weeks": ["2026-W39"]}
    flow.write(path, {"cards": [], "formats": [deepcopy(other), {
        "format": "standard", "selected_weeks": ["2026-W39", "2026-W38", "2026-W37", "2026-W36"]}]})
    page = {"format": "standard", "week": {"id": "2026-W40"},
            "environment": {"rows": []}, "features": {"items": []}}
    assert weekly_resources.ensure(site, page)["downloaded"] == []
    manifest = flow.read(path)
    assert manifest["formats"][0] == other
    assert manifest["formats"][1] == {
        "format": "standard", "selected_weeks": ["2026-W40", "2026-W39", "2026-W38", "2026-W37"],
        "anchor_week": "2026-W40", "window_end": "2026-W40", "window_start": "2026-W37"}
    assert manifest["schema_version"] == "1.1.0"
    before = path.read_bytes()
    weekly_resources.ensure(site, page)
    assert path.read_bytes() == before


@pytest.mark.parametrize("name", ["Front", "Front // Back"])
@pytest.mark.parametrize("failure", [None, "missing_image", "wrong_card"])
def test_selected_feature_uses_existing_face_resolution_and_resumes(tmp_path, name, failure):
    from PIL import Image
    site, responses = tmp_path / "site", tmp_path / "responses"
    responses.mkdir()
    Image.new("RGB", (40, 60), "navy").save(responses / "image.jpg")
    uri = "https://cards.scryfall.io/normal/front/synthetic.jpg"
    card = {"name": "Front // Back", "id": "00000000-0000-0000-0000-000000000001",
            "card_faces": [{"name": "Front", "image_uris": {"normal": uri}}, {"name": "Back"}]}
    fixture = {"cards": {name: deepcopy(card)}, "images": {uri: "image.jpg"}}
    if failure == "missing_image":
        del fixture["cards"][name]["card_faces"][0]["image_uris"]
    if failure == "wrong_card":
        fixture["cards"][name] = {**card, "name": "Other", "card_faces": []}
    flow.write(responses / "fixture.json", fixture)
    cached = site / "assets/card-cache/v1/images/cached.jpg"
    cached.parent.mkdir(parents=True)
    shutil.copyfile(responses / "image.jpg", cached)
    cached_bytes = cached.read_bytes()
    existing = {"name": "Cached", "source_image_uri": uri, "local_path": "assets/card-cache/v1/images/cached.jpg",
                "uses": [{"format": "pauper", "weeks": ["2026-W39"]}]}
    flow.write(site / "assets/card-cache/v1/manifest.json", {"cards": [existing]})
    page = {"format": "pauper", "week": {"id": "2026-W39"}, "environment": {"rows": []},
            "features": {"items": [{"featured_cards": [{"name": "Cached"}, {"name": name}]}]}}
    page_before = deepcopy(page)
    if failure:
        with pytest.raises(ValueError, match="No normal image|another card"):
            weekly_resources.ensure(site, page, fixture=responses / "fixture.json")
        assert cached.read_bytes() == cached_bytes and page == page_before
        fixture["cards"][name] = card
        flow.write(responses / "fixture.json", fixture)
    result = weekly_resources.ensure(site, page, fixture=responses / "fixture.json")
    assert len(result["downloaded"]) == 1 and existing["local_path"] in result["reused"]
    entry = next(c for c in flow.read(site / "assets/card-cache/v1/manifest.json")["cards"] if c["name"] == name)
    assert entry["face_index"] == 0 and entry["source_image_uri"] == uri
    assert page == page_before and cached.read_bytes() == cached_bytes
    assert weekly_resources.ensure(site, page)["downloaded"] == []


@pytest.mark.parametrize("name", ["Front", "Front // Back"])
@pytest.mark.parametrize("failure", [None, "missing_crop", "wrong_card"])
def test_environment_face_selection_keeps_art_crop_and_cache(tmp_path, name, failure):
    from PIL import Image
    from tools.build_archetype_visuals import image_slug
    site, responses = tmp_path / "site", tmp_path / "responses"
    responses.mkdir()
    Image.new("RGB", (80, 50), "green").save(responses / "crop.jpg")
    crop = "https://cards.scryfall.io/art_crop/front/synthetic.jpg"
    normal = "https://cards.scryfall.io/normal/front/synthetic.jpg"
    card = {"name": "Front // Back", "id": "00000000-0000-0000-0000-000000000001",
            "card_faces": [{"name": "Front", "image_uris": {"normal": normal, "art_crop": crop}},
                           {"name": "Back", "image_uris": {"normal": normal,
                            "art_crop": "https://cards.scryfall.io/art_crop/back/second.jpg"}}]}
    fixture = {"cards": {name: deepcopy(card)}, "images": {crop: "crop.jpg"}}
    if failure == "missing_crop":
        for face in fixture["cards"][name]["card_faces"]:
            del face["image_uris"]["art_crop"]  # normal exists but must not substitute.
    if failure == "wrong_card":
        fixture["cards"][name] = {**card, "name": "Other", "card_faces": []}
    flow.write(responses / "fixture.json", fixture)
    cached = site / "assets/images/representative-cards/pauper/cached.jpg"
    cached.parent.mkdir(parents=True)
    shutil.copyfile(responses / "crop.jpg", cached)
    before = cached.read_bytes()
    page = {"format": "pauper", "week": {"id": "2026-W39"}, "features": {"items": []},
            "environment": {"rows": [{"archetype_id": "synthetic", "key_cards": [
                {"name": "Cached"}, {"name": name}]}]}}
    original = deepcopy(page)
    if failure:
        with pytest.raises(ValueError, match="No art_crop image|another card"):
            weekly_resources.ensure(site, page, fixture=responses / "fixture.json")
        assert page == original and cached.read_bytes() == before
        fixture["cards"][name] = card
        flow.write(responses / "fixture.json", fixture)
    result = weekly_resources.ensure(site, page, fixture=responses / "fixture.json")
    target = site / f"assets/images/representative-cards/pauper/{image_slug(name)}.jpg"
    assert result["downloaded"] == [target.relative_to(site).as_posix()]
    assert target.read_bytes() == (responses / "crop.jpg").read_bytes()
    assert cached.relative_to(site).as_posix() in result["reused"]
    assert page == original and cached.read_bytes() == before
    assert weekly_resources.ensure(site, page)["downloaded"] == []
