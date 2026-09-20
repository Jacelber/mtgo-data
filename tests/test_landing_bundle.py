from copy import deepcopy
import json

import pytest

from mtgmeta.mtgo.landing_bundle import inspect_bundle


@pytest.fixture
def site(tmp_path):
    base = tmp_path / "stats/standard/mtgo/landing"
    week = {"id": "2026-W38", "start": "2026-09-14", "end": "2026-09-20"}
    files = {key: f"weeks/{week['id']}/{key}.json" for key in
             ("range", "completeness", "environment_decks", "feature_decks")}
    documents = {"current.json": {"week": week, "format": "standard", "classifier": {"digest": "old-rules"},
                                  "data_files": files, "features": {"items": []}},
                 "features/2026-W38.json": {"week": week, "format": "standard", "features": {"items": []}},
                 "features/index.json": {"format": "standard", "weeks": [{"week": week["id"],
                                              "file": "2026-W38.json", "feature_count": 0}]}}
    for key, path in files.items():
        period = {"start": "2026-08-24" if key == "feature_decks" else week["start"], "end": week["end"]}
        documents[path] = {"format": "standard", "period": period, "classifier_digest": "old-rules"}
    for path, value in documents.items():
        target = base / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value))
    return tmp_path, base, documents


def test_retained_week_ignores_new_rolling_data_and_accepts_four_week_feature_window(site):
    root, base, _ = site
    before = inspect_bundle(root, "standard")["digest"]
    (base.parent / "range_1w.json").write_text('{"classifier_digest":"new-rules","period":{"end":"2099-01-01"}}')
    assert inspect_bundle(root, "standard")["digest"] == before


@pytest.mark.parametrize("change", ["missing", "classifier", "period", "format", "path", "archive"])
def test_broken_product_combinations_are_rejected(site, change):
    root, base, documents = site
    path = "weeks/2026-W38/environment_decks.json"
    document = deepcopy(documents[path])
    if change == "missing":
        (base / path).unlink()
    else:
        if change == "classifier":
            document["classifier_digest"] = "new-rules"
        elif change == "period":
            document["period"]["end"] = "2026-09-27"
        elif change == "format":
            document["format"] = "modern"
        elif change == "path":
            path, document = "current.json", deepcopy(documents["current.json"])
            document["data_files"]["range"] = "../../other.json"
        else:
            path, document = "features/2026-W38.json", deepcopy(documents["features/2026-W38.json"])
            document["features"]["items"] = [{"hidden": "feature"}]
        (base / path).write_text(json.dumps(document))
    with pytest.raises((OSError, ValueError)):
        inspect_bundle(root, "standard")


def test_legacy_unpinned_page_may_only_reuse_matching_rolling_files(site):
    root, base, documents = site
    page = deepcopy(documents["current.json"])
    page.pop("data_files")
    (base / "current.json").write_text(json.dumps(page))
    paths = {"range": "range_1w.json", "completeness": "completeness/1w.json",
             "environment_decks": "decks_1w.json", "feature_decks": "decks_4w.json"}
    for key, path in paths.items():
        target = base.parent / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(documents[f"weeks/2026-W38/{key}.json"]))
    assert inspect_bundle(root, "standard")["pinned"] is False
    value = documents["weeks/2026-W38/range.json"]
    value["period"]["end"] = "2026-09-27"
    (base.parent / "range_1w.json").write_text(json.dumps(value))
    with pytest.raises(ValueError, match="period mismatch"):
        inspect_bundle(root, "standard")


def test_completion_requires_the_accepted_preview_in_the_confirmed_archive(site, monkeypatch, tmp_path):
    import sys
    from mtgmeta.mtgo import review_submission as review
    from tools import review_submission as cli
    from tools.delivery import packages
    root, base, documents = site
    page = documents["current.json"]
    page["environment"] = {"rows": []}
    (base / "current.json").write_text(json.dumps(page))
    assets = root / "assets/js/phase8"
    assets.mkdir(parents=True)
    (assets / "app.js").write_text("/* fixture renderer */")
    (assets / "archetype-visuals.js").write_text('const manaIdentities = Object.freeze({\n  standard: Object.freeze({\n  }),\n});')
    for relative, text in {"index.html": "<html>synthetic page</html>", "melee/index.html": "synthetic",
                           "stats/catalog.json": "{}", "stats/standard/archetype_names.json": '{"names":[]}'}.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    packet = review.preview_packet(root, "standard")
    decisions = review.record_decision(packet, None, ["final_page"], evidence="Synthetic explicit acceptance",
                                        accepted_on="2026-09-21", entrypoint="https://example.invalid/fixture")
    acceptance = tmp_path.parent / (tmp_path.name + "-acceptance.json")
    acceptance.write_text(json.dumps({"submission": packet, "decisions": decisions}))
    candidate = tmp_path.parent / (tmp_path.name + "-package")
    manifest = packages.prepare(root, candidate, target="Jacelber/mtgo-data", source="synthetic")
    state_path = tmp_path.parent / (tmp_path.name + "-state.json")
    output = tmp_path.parent / (tmp_path.name + "-completion.json")
    state = {"pending": None, "current": {"health": "unknown", "operation": "synthetic", "package": manifest["id"]}}
    args = ["review_submission", "--root", str(root), "completion", "--acceptance", str(acceptance),
            "--candidate", str(candidate), "--publication-state", str(state_path), "--output", str(output)]
    monkeypatch.setattr(sys, "argv", args)
    state_path.write_text(json.dumps(state))
    with pytest.raises(ValueError, match="not confirmed"):
        cli.main()
    assert not output.exists()
    state["current"]["health"] = "passed"
    state_path.write_text(json.dumps(state))
    cli.main()
    envelope = json.loads(output.read_text())
    review.validate_completion(root, "standard", "2026-W38", {"preview_acceptance": envelope})
    from tools.export_weekly_classification_review import attach_preview_acceptances
    record = {"week": "2026-W38", "formats": {"standard": {}}}
    with pytest.raises(ValueError, match="requires confirmed"):
        attach_preview_acceptances(root, record, None)
    receipt_file = tmp_path.parent / (tmp_path.name + "-format-receipts.json")
    receipt_file.write_text(json.dumps({"standard": envelope}))
    attach_preview_acceptances(root, record, receipt_file)
    assert record["formats"]["standard"]["preview_acceptance"] == envelope
    (assets / "app.js").write_text("/* changed display after acceptance */")
    with pytest.raises(ValueError, match="differs"):
        review.validate_completion(root, "standard", "2026-W38", {"preview_acceptance": envelope})
