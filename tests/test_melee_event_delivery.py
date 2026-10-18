from copy import deepcopy
import json
from pathlib import Path
import subprocess

import pytest

from build_pages_artifact import measure_artifact, PublicationError
from mtgmeta.mtgo import publication
from tools import melee_event_delivery as workflow


def test_shared_validation_index_tracks_actual_edits_additions_and_deletions(tmp_path):
    root, stage = tmp_path / "source", tmp_path / "stage"
    root.mkdir(); stage.mkdir()
    def git(directory, *args):
        return subprocess.run(["git", "-C", str(directory), *args], check=True, capture_output=True).stdout
    git(root, "init", "-q")
    for name in ("same", "changed", "deleted"):
        (root / name).write_bytes((name * 100).encode())
    git(root, "add", "--all")
    git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "baseline")
    source_index = (root / ".git/index").read_bytes()
    (stage / "same").write_bytes((root / "same").read_bytes())
    (stage / "changed").write_bytes(b"new content")
    (stage / "added").write_bytes(b"new file")
    publication._prepare_validation_index(root, stage)
    publication._index_validation_candidate(stage)
    assert set(git(stage, "ls-files").decode().splitlines()) == {"same", "changed", "added"}
    for name in ("same", "changed", "added"):
        object_id = git(stage, "rev-parse", ":" + name).strip().decode()
        assert git(stage, "cat-file", "blob", object_id) == (stage / name).read_bytes()
    same_id = git(root, "rev-parse", "HEAD:same").strip().decode()
    assert not (stage / ".git/objects" / same_id[:2] / same_id[2:]).exists()
    assert (root / ".git/index").read_bytes() == source_index
    assert git(stage, "remote") == b""
    assert b"\r" not in (stage / ".git/objects/info/alternates").read_bytes()
    # Re-entry indexes actual bytes again; it cannot trust old stat metadata.
    (stage / "changed").write_bytes(b"edited again")
    import os
    # A same-size edit with restored timestamps must still enter the index.
    (stage / "same").write_bytes(b"X" * (root / "same").stat().st_size)
    os.utime(stage / "same", ns=((root / "same").stat().st_atime_ns, (root / "same").stat().st_mtime_ns))
    publication._prepare_validation_index(root, stage)
    publication._index_validation_candidate(stage)
    assert git(stage, "show", ":changed") == b"edited again"
    assert git(stage, "show", ":same") == (stage / "same").read_bytes()


@pytest.mark.parametrize("change_content", [False, "current", "history"])
def test_same_week_restatement_allows_only_technical_changes(tmp_path, monkeypatch, change_content):
    from mtgmeta import classifier_closure, classifier
    from mtgmeta.mtgo import normalize, landing
    root, stage = tmp_path / "source", tmp_path / "stage"
    relative = Path("stats/modern/mtgo/landing/current.json")
    before = {"week": {"id": "2025-W02"}, "classifier": {"digest": "old"},
              "weekly_summary": {"items": ["accepted text"]}, "features": {"items": []},
              "environment": {"rows": []}}
    (root / relative).parent.mkdir(parents=True)
    (root / relative).write_text(json.dumps(before), encoding="utf-8")
    feature = relative.parent / "features/2025-W01.json"
    (root / feature).parent.mkdir(parents=True)
    (root / feature).write_text(json.dumps({"classifier_digest": "old", "items": ["accepted archive"]}))
    original = (root / relative).read_bytes()
    monkeypatch.setattr(normalize, "load_rules_for_format", lambda *a: None)
    monkeypatch.setattr(classifier, "classifier_digest", lambda *a: "new")
    monkeypatch.setattr(classifier_closure, "_inspect_landing", lambda *a: {"state": "STALE_REGENERABLE"})
    def generate(candidate, fmt, *, allow_classifier_restatement):
        assert allow_classifier_restatement is True
        after = deepcopy(before)
        after["classifier"] = {"digest": "new"}
        if change_content == "current":
            after["weekly_summary"]["items"] = ["unapproved rewrite"]
        if change_content == "history":
            (candidate / feature).write_text(json.dumps({"classifier_digest": "new", "items": ["rewritten archive"]}))
        (candidate / relative).write_text(json.dumps(after), encoding="utf-8")
        return {"status": "reviewed"}
    monkeypatch.setattr(landing, "generate", generate)
    if change_content:
        with pytest.raises(publication.PublicationError, match="content changed"):
            publication._restate_retained_landing(root, stage, "modern", "2025-W02")
    else:
        publication._restate_retained_landing(root, stage, "modern", "2025-W02")
        assert json.loads((stage / relative).read_bytes())["weekly_summary"] == before["weekly_summary"]
    assert (root / relative).read_bytes() == original


def test_byte_measurement_labels_lower_bound_and_rejects_combined_overflow(tmp_path):
    root, overlay = tmp_path / "root", tmp_path / "overlay"
    root.mkdir(); overlay.mkdir()
    (root / "index.html").write_bytes(b"123456")
    (overlay / "image").write_bytes(b"12345")
    config = {"maximum_artifact_bytes": 10,
              "generated_overlays": [{"id": "images", "maximum_bytes": 20}]}
    result = measure_artifact(root, config, selected={"index.html"})
    assert result["bytes"] == 6 and result["complete"] is False
    with pytest.raises(PublicationError, match="maximum_artifact_bytes: 11"):
        measure_artifact(root, config, selected={"index.html"}, overlays={"images": overlay})
    config["maximum_artifact_bytes"] = 11
    assert measure_artifact(root, config, selected={"index.html"}, overlays={"images": overlay})["complete"] is True
    with pytest.raises(PublicationError, match="maximum_artifact_bytes: 11"):
        measure_artifact(root, config, selected={"index.html"}, overlays={"images": overlay}, maximum_bytes=10)


def test_offline_preview_cannot_query_missing_resources(tmp_path, monkeypatch):
    root = tmp_path / "source"
    record = {"schema": 1, "identity": {"kind": "reviewed_data", "root": str(root),
              "scope": {}, "material": {"fixed": True}}, "operation": "unused"}
    path = tmp_path / "fixed.delivery.json"
    path.write_text(json.dumps(record))
    monkeypatch.setattr(workflow, "material_snapshot", lambda *a: {"fixed": True})
    def forbidden(*a):
        pytest.fail("Offline preview reached a resource query/build")
    monkeypatch.setattr(workflow.resources, "prepare_site", forbidden)
    with pytest.raises((ValueError, OSError)):
        workflow.preview(path, offline=True)


def test_preview_rejects_missing_comparison_deck_dependency(tmp_path, monkeypatch):
    root, site = tmp_path / "source", tmp_path / "site"
    record = {"schema": 1, "identity": {"kind": "reviewed_data", "root": str(root),
              "scope": {"melee": [{"format": "modern", "event_id": "123"}]}, "material": {}}, "operation": "unused"}
    path = tmp_path / "fixed.delivery.json"
    path.write_text(json.dumps(record))
    for relative, data in {"stats/catalog.json": {}, "stats/modern/archetype_names.json": {},
        "stats/modern/melee/index.json": {"events": [{"event_id": "123", **{key: f"events/123/{key}.json"
         for key in ("meta", "overview", "quality", "decks", "matchup")}}]}}.items():
        destination = site / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(data))
    monkeypatch.setattr(workflow, "material_snapshot", lambda *a: {})
    monkeypatch.setattr(workflow.resources, "prepare_site", lambda *a: site)
    with pytest.raises(ValueError, match="consumer dependencies"):
        workflow.preview(path)


def test_audit_separates_unknown_missing_and_rejects_changed_raw_input(tmp_path, monkeypatch):
    import hashlib
    from mtgmeta import classifier
    from mtgmeta.mtgo import normalize
    monkeypatch.setattr(normalize, "load_rules_for_format", lambda *a: None)
    monkeypatch.setattr(classifier, "classifier_digest", lambda *a: "current")
    raw = tmp_path / "raw.json"
    raw.write_bytes(b"retained source")
    event = {"metadata": {"event_id": "123", "constructed_format": "modern"},
        "participants": [{"id": i, "display_name": i, "status": "active"} for i in ("A", "B")],
        "standings": [{"participant_id": i, "rank": rank} for rank, i in enumerate(("A", "B"), 1)],
        "decklists": [{"participant_id": "A", "status": "submitted", "cards": [{"name": "Card", "quantity": 60}]},
                      {"participant_id": "B", "status": "missing", "cards": []}],
        "provenance": {"raw_artifacts": [{"path": "raw.json", "sha256": hashlib.sha256(raw.read_bytes()).hexdigest()}]},
        "quality": {"status": "warning"}}
    path = tmp_path / "data/modern/melee/events/123.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(event))
    overlay = {"event_id": "123", "format": "modern", "classifier": {"digest": "current"},
        "input": {"event_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}, "summary": {"unknown": 1},
        "records": [{"participant_id": "A", "classification_status": "unknown"}], "quality": {}}
    path = tmp_path / "data/modern/melee/classifications/123.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(overlay))
    result = workflow.audit(tmp_path, "modern", "123")
    assert result["participants"] == 2 and result["participant_coverage_equal"] is True
    assert [row["name"] for row in result["unknown"]] == ["A"]
    assert result["unknown"][0]["decklist"]["cards"][0]["quantity"] == 60
    assert [row["name"] for row in result["unavailable"]] == ["B"]
    raw.write_bytes(b"changed source")
    with pytest.raises(ValueError, match="raw artifact hash"):
        workflow.audit(tmp_path, "modern", "123")
