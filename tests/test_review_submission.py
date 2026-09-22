"""Independent scenarios for the Owner's review boundary, not wording tests."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
import yaml

from mtgmeta.mtgo import review_submission as review
from mtgmeta.mtgo import landing_editorial as editorial
from tools import import_landing_conversation as importer


def packet(**overrides):
    return review.make_packet("content", overrides.get("format", "standard"), "2026-W38",
                              overrides.get("dimensions", {"name.zh": "蓝白", "name.en": "Azorius"}),
                              bindings={"classifier": "unchanged"})


def accept(subject, keys=None):
    return review.record_decision(subject, None, keys or list(subject["dimensions"]),
                                  evidence="Synthetic scenario: Owner explicitly accepted these fields",
                                  accepted_on="2026-09-28", entrypoint="private://synthetic/index.html")


def test_chinese_decision_never_accepts_english_or_another_format():
    subject = packet()
    receipt = accept(subject, ["name.zh"])
    assert review.decision_state(subject, receipt) == {"accepted": ["name.zh"], "pending": ["name.en"]}
    assert review.decision_state(packet(format="modern"), receipt)["accepted"] == []
    with pytest.raises(ValueError, match="unsubmitted"):
        review.record_decision(subject, None, ["hidden"], evidence="actual decision",
                               accepted_on="2026-09-28", entrypoint="private://material")


def test_only_changed_dimension_loses_acceptance_and_current_cannot_be_rebound():
    original = packet()
    receipt = accept(original)
    changed = packet(dimensions={"name.zh": "新中文", "name.en": "Azorius"})
    assert review.decision_state(changed, receipt) == {"accepted": ["name.en"], "pending": ["name.zh"]}
    with pytest.raises(ValueError, match="no longer matches"):
        review.require_accepted(original, receipt, current=changed)
    tampered = deepcopy(original)
    tampered["dimensions"]["name.en"] = "Hidden replacement"
    with pytest.raises(ValueError, match="material changed"):
        review.require_accepted(tampered, receipt)


def test_group_material_requires_every_requested_deck_and_complete_zones():
    rows = [{"reference": str(i), "main_deck": [{"name": "Island", "qty": 60}],
             "sideboard": [], "rank": i} for i in (1, 2, 3, 4)]
    materials = {"classification": {"format": "standard", "week": "2026-W38", "event_ids": ["1"],
                 "classifier": {"subject_digest": "rules"}, "classification_review_digest": "all",
                 "records": rows}}
    requests = [{"id": "S1", "members": ["1", "2", "3", "4"], "proposed": "blue", "reason": "test evidence"}]
    subject = review.classification_packet(materials, requests)
    assert len(subject["dimensions"]["S1"]["members"]) == 4
    assert subject["dimensions"]["S1"]["members"][0]["main_deck_total"] == 60
    del rows[-1]["sideboard"]
    with pytest.raises(ValueError, match="sideboard"):
        review.classification_packet(materials, requests)
    materials["classification"]["records"].pop()
    with pytest.raises(ValueError, match="Missing"):
        review.classification_packet(materials, requests)


def test_new_full_acceptance_is_not_an_individual_proposal_and_legacy_is_unchanged():
    review.validate_classification_acceptance({"week": "2026-W37"})
    record = {"week": "2026-W38", "event_ids": ["1"], "accepted_classifier_subject": "rules",
              "classification_review_digest": "all"}
    with pytest.raises(ValueError, match="submitted full-table"):
        review.validate_classification_acceptance(record)
    subject = packet()
    record["classification_acceptance"] = {"submission": subject, "decisions": accept(subject)}
    with pytest.raises(ValueError, match="Individual"):
        review.validate_classification_acceptance(record)
    subject = review.full_classification_packet({"format": "standard", "week": "2026-W38", "event_ids": ["1"],
        "classifier": {"subject_digest": "rules"}, "classification_review_digest": "all",
        "records": [{"reference": "one", "main_deck": [{"name": "Island", "qty": 60}], "sideboard": []}]})
    record["classification_acceptance"] = {"submission": subject, "decisions": accept(subject)}
    review.validate_classification_acceptance(record, "standard")
    with pytest.raises(ValueError, match="other-scope"):
        review.validate_classification_acceptance(record, "modern")


def test_visuals_colorless_requires_c_and_scope_is_minimal(tmp_path):
    source = tmp_path / "assets/js/phase8/archetype-visuals.js"
    source.parent.mkdir(parents=True)
    source.write_text('const manaIdentities = Object.freeze({\n  standard: Object.freeze({\n'
                      '    "artifacts": Object.freeze(["c"]),\n    "unrelated": Object.freeze(["r"]),\n  }),\n});')
    content = {"top_copy": {"items": []}, "features": {"explicit_empty": True, "items": []}}
    environment = {"rows": [{"archetype_id": "artifacts", "key_cards": [{"name": "A"}, {"name": "B"}]}]}
    names = {"names": [{"identity_key": "standard|artifacts|none", "english": "Artifacts", "chinese": "神器"}]}
    before = review.content_dimensions(tmp_path, "standard", content, environment, names)
    source.write_text(source.read_text().replace('["r"]', '["g"]'))
    assert review.content_dimensions(tmp_path, "standard", content, environment, names) == before
    assert before["visual.environment.artifacts"]["colors"] == ["c"]
    assert before["features"] == before["copy.zh"] == []
    source.write_text(source.read_text().replace('"artifacts": Object.freeze(["c"])', '"artifacts": Object.freeze([])'))
    with pytest.raises(ValueError, match="at least one indicator"):
        review.content_dimensions(tmp_path, "standard", content, environment, names)
    source.write_text(source.read_text().replace('    "artifacts": Object.freeze([]),\n', ''))
    with pytest.raises(ValueError, match="Incomplete visual"):
        review.content_dimensions(tmp_path, "standard", content, environment, names)


def test_import_requires_submission_before_writing_and_never_auto_binds(tmp_path, monkeypatch):
    (tmp_path / "configs").mkdir()
    (tmp_path / editorial.DEFAULT_NAME_CATALOG).write_text("names: []\n")
    week = {"id": "2026-W38", "start": "2026-09-14", "end": "2026-09-20"}
    subject = {"week": week, "source_event_ids": ["1"], "classifier_digest": "a",
               "selection_policy_digest": "b", "machine_fact_digest": "c", "link_catalog_digest": "d"}
    source = {"format": "standard", "week": week, "bindings": dict(subject),
              "review": {"top_copy": {"reviewed": True}, "features": {"reviewed": True}}}
    monkeypatch.setattr(editorial, "build_top8_subject", lambda *args: subject)
    with pytest.raises(ValueError, match="actually submitted"):
        importer.import_content(tmp_path, source)
    original = packet()
    source["acceptance"] = {"submission": original, "decisions": accept(original)}
    monkeypatch.setattr(review, "content_packet", lambda *args: packet(dimensions={"name.zh": "changed"}))
    with pytest.raises(ValueError, match="no longer matches"):
        importer.import_content(tmp_path, source)
    assert not (tmp_path / "stats").exists()


def test_existing_w37_review_and_name_catalog_remain_valid():
    root = Path(__file__).resolve().parents[1]
    for format_id in ("standard", "modern", "pauper"):
        document = editorial.load_review_document(root / f"stats/{format_id}/mtgo/landing/review/2026-W37.yaml",
                                                   root / editorial.DEFAULT_REVIEW_SCHEMA)
        assert document["schema_version"] == "1.2.0"
    catalog = yaml.safe_load((root / editorial.DEFAULT_NAME_CATALOG).read_text(encoding="utf-8"))
    editorial._validate_schema(catalog, root / editorial.DEFAULT_NAME_SCHEMA, "legacy names")
    assert review.names_approved("approved")
    assert not review.names_approved({"english": "pending_owner_review", "chinese": "approved"})


def test_snapshot_is_portable_and_never_overwrites_submitted_material(tmp_path):
    subject = packet()
    review.write_materials(subject, tmp_path / "one", accept(subject, ["name.zh"]))
    copied = json.loads((tmp_path / "one/submission.json").read_text(encoding="utf-8"))
    receipt = json.loads((tmp_path / "one/decisions.json").read_text(encoding="utf-8"))["decisions"]
    assert review.decision_state(copied, receipt)["pending"] == ["name.en"]
    with pytest.raises(ValueError, match="new snapshot"):
        review.write_materials(subject, tmp_path / "one")


def test_final_preview_material_renders_archetype_color_mapping(tmp_path):
    subject = review.make_packet("preview", "standard", "2026-W38", {
        "final_page": {
            "colors": {"4-color-demons": ["w", "u", "b", "r"]},
            "selected_local_images": {},
        },
    }, bindings={})
    output = tmp_path / "preview"
    review.write_materials(subject, output, preview_entrypoint="http://127.0.0.1:8773/index.html")
    assert (output / "index.html").is_file()


def test_only_stable_choices_can_be_reused_across_weeks():
    dimensions = {"visual.environment.a": {"colors": ["c"], "cards": ["A", "B"]}, "copy.zh": "same"}
    old = review.make_packet("content", "modern", "2026-W38", dimensions, bindings={})
    new = review.make_packet("content", "modern", "2026-W39", dimensions, bindings={})
    receipt = review.reuse_decisions(new, {"submission": old, "decisions": accept(old)})
    assert review.decision_state(new, receipt) == {"accepted": ["visual.environment.a"], "pending": ["copy.zh"]}
    with pytest.raises(ValueError, match="another format"):
        review.reuse_decisions(packet(format="standard"), {"submission": old, "decisions": accept(old)})


def test_existing_approved_language_is_reused_but_pending_language_is_not(tmp_path):
    path = tmp_path / "assets/js/phase8/archetype-visuals.js"
    path.parent.mkdir(parents=True)
    path.write_text('const manaIdentities = Object.freeze({\n  standard: Object.freeze({\n    "a": Object.freeze(["c"]),\n  }),\n});')
    names = {"names": [{"identity_key": "standard|a|none", "chinese": "已确认", "english": "Pending",
                        "review_status": {"chinese": "approved", "english": "pending_owner_review"}}]}
    packet = review.make_content_packet(tmp_path, "standard", "2026-W38",
        {"top_copy": {"items": []}, "features": {"items": [], "explicit_empty": True}},
        {"rows": [{"archetype_id": "a", "key_cards": [{"name": "A"}, {"name": "B"}]}]}, names, bindings={})
    state = review.decision_state(packet, None)
    assert state["accepted"] == ["name.standard|a|none.zh"]
    assert "name.standard|a|none.en" in state["pending"]


def test_accepted_new_content_imports_and_loads_without_relaxing_schema(tmp_path, monkeypatch):
    import shutil
    root = Path(__file__).resolve().parents[1]
    source = yaml.safe_load((root / "stats/modern/mtgo/landing/review/2026-W37.yaml").read_text(encoding="utf-8"))
    source["week"] = {"id": "2026-W38", "start": "2026-09-14", "end": "2026-09-20"}
    (tmp_path / "configs").mkdir()
    (tmp_path / editorial.DEFAULT_NAME_CATALOG).write_text("names: []\n")
    (tmp_path / "schemas").mkdir()
    shutil.copyfile(root / editorial.DEFAULT_REVIEW_SCHEMA, tmp_path / editorial.DEFAULT_REVIEW_SCHEMA)
    subject = {**source, **source["bindings"]}
    monkeypatch.setattr(editorial, "build_top8_subject", lambda *args: subject)
    dims = {f"copy.{language}": [{"order": item["order"], "text": item["text"][language]}
                               for item in source["review"]["top_copy"]["items"]] for language in ("zh", "en")}
    dims["features"] = []
    packet = review.make_packet("content", "modern", "2026-W38", dims,
        bindings={key: source["bindings"][key] for key in ("source_event_ids", "classifier_digest", "selection_policy_digest", "machine_fact_digest", "link_catalog_digest")})
    monkeypatch.setattr(review, "content_packet", lambda *args: packet)
    source["acceptance"] = {"submission": packet, "decisions": accept(packet)}
    destination = importer.import_content(tmp_path, source)
    actual = editorial.load_review_document(destination, tmp_path / editorial.DEFAULT_REVIEW_SCHEMA)
    assert actual["schema_version"] == "1.3.0"
    assert actual["acceptance"] == source["acceptance"]
    actual["review"]["top_copy"]["items"][0]["text"]["en"] = "unseen replacement"
    with pytest.raises((ValueError, editorial.MTGOLandingEditorialError)):
        editorial.validate_review_document(actual, tmp_path / editorial.DEFAULT_REVIEW_SCHEMA)

    # Workbook parsing is unchanged; verify its import boundary uses the same receipt.
    proposed = deepcopy(source)
    proposed.pop("acceptance")
    proposed["bindings"]["workbook_sha256"] = "0" * 64
    workbook = tmp_path / "review.xlsx"
    validated = {"reviews": {("modern", "2026-W38"): proposed}, "workbook_sha256": "0" * 64,
                 "name_count": 0, "review_count": 1, "feature_count": 0, "copy_count": 2}
    monkeypatch.setattr(editorial, "_validated_workbook_subject", lambda *args, **kwargs: deepcopy(validated))
    monkeypatch.setattr(editorial, "_known_ids", lambda *args: set())
    output = tmp_path / "workbook-output"
    with pytest.raises(FileNotFoundError):
        editorial.import_review_workbook(tmp_path, workbook, output_root=output)
    assert not output.exists()
    workbook.with_suffix(".submissions.json").write_text(json.dumps({"modern/2026-W38": source["acceptance"]}))
    editorial.import_review_workbook(tmp_path, workbook, output_root=output)
    result = editorial.load_review_document(output / "stats/modern/mtgo/landing/review/2026-W38.yaml",
                                              tmp_path / editorial.DEFAULT_REVIEW_SCHEMA)
    assert result["schema_version"] == "1.3.0"
    assert "workbook_sha256" not in result["bindings"]


def test_resume_does_not_reopen_a_legacy_completed_week(tmp_path):
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/mtgo_weekly_review_completions.yaml").write_text(
        "records:\n  - week: 2026-W37\n    formats:\n      modern: {}\n", encoding="utf-8")
    result = review.resume_summary(tmp_path, "modern", "2026-W37")
    assert result["completion"] == "legacy_recorded"
    assert result["data_publication"] == "unknown"
    assert result["preview"] == "not_separately_recorded_legacy"
    assert result["next_actions"][0].startswith("保留本周完成结果，不重开验收")
