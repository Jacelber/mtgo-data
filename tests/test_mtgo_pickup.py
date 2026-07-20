"""P3-06 regression coverage for Pickup, metadata, and public catalogs."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for candidate in (ROOT, SRC):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import gen_meta
import stats_standard
import stats_matchup
import weekly_pickup
from mtgmeta.config import DisabledFormatError, UnknownFormatError
from mtgmeta.mtgo import matchup as mtgo_matchup
from mtgmeta.mtgo import pickup
from mtgmeta.mtgo import stats as mtgo_stats


REFERENCE_TODAY = date(2026, 7, 19)
PUBLIC = ROOT / "stats" / "standard" / "mtgo"
PICKUP = PUBLIC / "pickup"


def test_fixed_reference_candidates_and_base_are_byte_identical(tmp_path):
    result = pickup.generate_candidates(
        ROOT,
        "standard",
        today=REFERENCE_TODAY,
        output_directory=tmp_path,
    )
    assert result is not None
    assert result["week"] == "2026-W28"
    assert result["candidate_path"].read_bytes() == (
        PICKUP / "candidates_2026-W28.yaml"
    ).read_bytes()
    assert result["base_reference_path"].read_bytes() == (
        PICKUP / "base_reference_2026-W28.yaml"
    ).read_bytes()


def test_candidate_preservation_does_not_overwrite_manual_review(tmp_path):
    first = pickup.generate_candidates(
        ROOT,
        "standard",
        today=REFERENCE_TODAY,
        output_directory=tmp_path,
    )
    candidate = first["candidate_path"]
    reviewed = candidate.read_text(encoding="utf-8") + "# manual review marker\n"
    candidate.write_text(reviewed, encoding="utf-8")

    second = pickup.generate_candidates(
        ROOT,
        "standard",
        today=REFERENCE_TODAY,
        output_directory=tmp_path,
        preserve_existing=True,
    )
    assert second["skipped_existing"] is True
    assert candidate.read_text(encoding="utf-8") == reviewed


def test_unapproved_candidates_do_not_publish_or_update_state(tmp_path):
    candidates = tmp_path / "candidates"
    output = tmp_path / "published"
    pickup.generate_candidates(
        ROOT,
        "standard",
        today=REFERENCE_TODAY,
        output_directory=candidates,
    )
    assert pickup.publish(
        ROOT,
        "standard",
        today=REFERENCE_TODAY,
        candidate_directory=candidates,
        output_directory=output,
    ) is None
    assert not output.exists()


def test_publish_preserves_manual_approval_and_catalog_state(tmp_path):
    candidates = tmp_path / "candidates"
    output = tmp_path / "published"
    generated = pickup.generate_candidates(
        ROOT,
        "standard",
        today=REFERENCE_TODAY,
        output_directory=candidates,
    )
    candidate_path = generated["candidate_path"]
    document = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    selected = document["existing_changes"][0]
    selected["approved"] = True
    selected["comment_zh"] = "  人工确认  "
    candidate_path.write_text(
        yaml.dump(document, allow_unicode=True, sort_keys=False, width=1000),
        encoding="utf-8",
    )

    result = pickup.publish(
        ROOT,
        "standard",
        today=REFERENCE_TODAY,
        candidate_directory=candidates,
        output_directory=output,
    )
    assert result is not None
    assert result["existing_count"] == 1
    assert result["new_count"] == 0

    published = json.loads(result["published_path"].read_text(encoding="utf-8"))
    assert published["format"] == "standard"
    assert published["source"] == "mtgo"
    assert published["existing_changes"][0]["comment_zh"] == "人工确认"
    assert "approved" not in published["existing_changes"][0]

    catalog = json.loads(result["index_path"].read_text(encoding="utf-8"))
    assert [entry["week"] for entry in catalog["weeks"]] == ["2026-W28", "2026-W27"]
    assert catalog["weeks"][0]["existing_count"] == 1
    assert json.loads(result["known_path"].read_text(encoding="utf-8"))["known"] == sorted(
        set(json.loads((PICKUP / "known_archetypes.json").read_text(encoding="utf-8"))["known"])
        | pickup.archetypes_in_window(
            mtgo_stats.load_all_events(ROOT, "standard"),
            stats_standard.load_rules(),
            date(2026, 7, 6),
            1,
        )
    )


def test_fixed_reference_metadata_and_legacy_wrapper_are_byte_identical(
    tmp_path, monkeypatch
):
    expected = json.loads((PUBLIC / "meta.json").read_text(encoding="utf-8"))
    destination = pickup.generate_metadata(
        ROOT,
        "standard",
        rules_updated=expected["rules_updated"],
        data_updated=expected["data_updated"],
        output_directory=tmp_path / "shared",
    )
    wrapped = gen_meta.generate_metadata(
        rules_updated=expected["rules_updated"],
        data_updated=expected["data_updated"],
        output_directory=tmp_path / "legacy",
    )
    assert destination.read_bytes() == (PUBLIC / "meta.json").read_bytes()
    assert wrapped.read_bytes() == destination.read_bytes()
    captured = {}

    def fake_runner(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return type("Result", (), {"stdout": "2026-07-20T05:34:31+09:00\n"})()

    assert pickup.rules_last_commit_iso(
        ROOT,
        ROOT / "my_archetypes" / "standard.yaml",
        runner=fake_runner,
    ) == "2026-07-20T05:34:31+09:00"
    assert captured["command"] == [
        "git",
        "log",
        "-1",
        "--format=%cI",
        "--",
        "my_archetypes/standard.yaml",
    ]
    assert captured["kwargs"] == {
        "cwd": ROOT.resolve(),
        "capture_output": True,
        "text": True,
        "check": True,
    }

    monkeypatch.setattr(
        gen_meta._shared,
        "rules_last_commit_iso",
        lambda root, rules_file: "2026-07-20T05:34:31+09:00",
    )
    assert gen_meta.rules_last_commit_iso() == "2026-07-20T05:34:31+09:00"


@pytest.mark.parametrize(
    "format_id,error",
    [("pauper", DisabledFormatError), ("missing", UnknownFormatError)],
)
def test_unavailable_formats_fail_before_pickup_or_metadata_output(
    tmp_path, format_id, error
):
    pickup_output = tmp_path / "pickup"
    metadata_output = tmp_path / "metadata"
    with pytest.raises(error):
        pickup.generate_candidates(ROOT, format_id, output_directory=pickup_output)
    with pytest.raises(error):
        pickup.generate_metadata(ROOT, format_id, output_directory=metadata_output)
    assert not pickup_output.exists()
    assert not metadata_output.exists()


def test_catalog_capability_gates_every_catalog_before_output(tmp_path):
    registry = yaml.safe_load((ROOT / "configs" / "formats.yaml").read_text(encoding="utf-8"))
    standard = next(item for item in registry["formats"] if item["id"] == "standard")
    standard["mtgo"]["capabilities"].remove("catalog_generation")
    registry_path = tmp_path / "formats.yaml"
    registry_path.write_text(
        yaml.dump(registry, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    destinations = [tmp_path / "stats", tmp_path / "matchups", tmp_path / "pickup"]
    with pytest.raises(DisabledFormatError, match="catalog_generation"):
        mtgo_stats.build_all_stats(
            ROOT,
            "standard",
            registry_path=registry_path,
            output_directory=destinations[0],
        )
    with pytest.raises(DisabledFormatError, match="catalog_generation"):
        mtgo_matchup.build_all_matchups(
            ROOT,
            "standard",
            registry_path=registry_path,
            output_directory=destinations[1],
        )
    with pytest.raises(DisabledFormatError, match="catalog_generation"):
        pickup.publish(
            ROOT,
            "standard",
            registry_path=registry_path,
            output_directory=destinations[2],
        )
    assert not any(destination.exists() for destination in destinations)


def test_legacy_commands_route_to_shared_format_aware_implementation(monkeypatch):
    captured = {}

    def fake_candidates(root, format_id):
        captured["pickup"] = (root, format_id)
        return None

    def fake_metadata(root, format_id, **kwargs):
        captured["metadata"] = (root, format_id, kwargs)
        return Path(kwargs["output_directory"]) / "meta.json"

    monkeypatch.setattr(weekly_pickup._shared, "generate_candidates", fake_candidates)
    monkeypatch.setattr(gen_meta._shared, "generate_metadata", fake_metadata)
    assert weekly_pickup.generate_candidates() is None
    destination = gen_meta.generate_metadata(output_directory="target")
    assert captured["pickup"] == (ROOT, "standard")
    assert captured["metadata"][0:2] == (ROOT, "standard")
    assert destination == Path("target") / "meta.json"


def test_shared_publication_module_has_no_implicit_standard_paths():
    source = (SRC / "mtgmeta" / "mtgo" / "pickup.py").read_text(encoding="utf-8")
    assert '"standard"' not in source
    assert "stats/standard/mtgo" not in source
    workflow = (ROOT / ".github" / "workflows" / "update.yml").read_text(encoding="utf-8")
    assert "python -B weekly_pickup.py" not in workflow
    assert "python -B gen_meta.py" not in workflow
    assert "pickup candidates --if-absent" in workflow
    assert "generate-metadata" in workflow
