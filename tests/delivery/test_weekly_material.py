"""Real package/binding checks with a small synthetic public selection."""
from datetime import date
import json
import shutil
from types import SimpleNamespace

import pytest

from tools.delivery import packages, verification, weekly


@pytest.fixture
def material(tmp_path, monkeypatch):
    import build_pages_artifact as builder
    from mtgmeta import classifier_closure
    from mtgmeta.mtgo import publication
    root, site = tmp_path / "root", tmp_path / "site"
    selected = set(packages.PROBES) | {
        "stats/standard/mtgo/landing/current.json",
        "stats/standard/mtgo/landing/features/index.json",
        "stats/standard/mtgo/landing/features/2024-W52.json",
    }
    for relative in selected | {"configs/pages_publication.json", "configs/protection.json", "data/standard/100.json"}:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"weeks": [{"week": "2024-W52", "file": "2024-W52.json"}]}))
    shutil.copytree(root, site)
    shutil.rmtree(site / "configs")
    shutil.rmtree(site / "data")
    config = {"compatibility_manifests": ["configs/protection.json"], "generated_overlays": []}
    # Isolate product registry/platform; snapshot, source hashing, package, scope
    # and existing acceptance comparisons below use their real implementations.
    monkeypatch.setattr(builder, "load_config", lambda *a: config)
    monkeypatch.setattr(builder, "publication_paths", lambda *a: selected)
    monkeypatch.setattr(builder, "validate_compatibility", lambda *a: None)
    monkeypatch.setattr(publication, "resolve_scope", lambda *a: SimpleNamespace(week=date(2025, 1, 6)))
    monkeypatch.setattr(publication, "inspect_publication", lambda *a: [])
    monkeypatch.setattr(classifier_closure, "validate_current_melee", lambda *a: None)
    accepted = tmp_path / "accepted.json"
    accepted.write_text('{}')

    def prepare(kind="reviewed_data"):
        record = weekly.create_record(tmp_path / "handoff.json", kind=kind, root=root, site=site,
            scope={"week": "2025-W02", "mtgo_formats": ["standard"]}, references=[accepted],
            source="a" * 40, target="Jacelber/mtgo-data-governance-verification")
        candidate = tmp_path / "package"
        packages.prepare(site, candidate, target=record["identity"]["target"], source=record["identity"]["source"])
        return record, candidate
    return root, site, accepted, prepare


def test_fixed_data_passes_without_content_acceptance(material):
    *_, prepare = material
    verification.verify_material(*prepare())


@pytest.mark.parametrize("change", [None, "missing_event", "source"])
def test_melee_only_release_preserves_fixed_inputs_without_mtgo_regeneration(material, tmp_path, change):
    import build_pages_artifact as builder
    root, site, accepted, _ = material
    relative = "stats/standard/melee/index.json"
    for base in (root, site):
        path = base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"events": [{"event_id": "123"}]}))
    builder.publication_paths(root, {}).add(relative)
    record = weekly.create_record(tmp_path / "melee.delivery.json", kind="reviewed_data", root=root, site=site,
        scope={"week": "2025-W02", "mtgo_formats": [], "melee": [{"format": "standard", "event_id": "123"}]},
        references=[accepted], source="a" * 40, target="Jacelber/mtgo-data-governance-verification")
    candidate = tmp_path / "melee-package"
    packages.prepare(site, candidate, target=record["identity"]["target"], source=record["identity"]["source"])
    if change == "source":
        (root / "data/standard/100.json").write_text("changed")
        with pytest.raises(ValueError, match="Fixed material changed"):
            verification.verify_material(record, candidate)
    elif change == "missing_event":
        record["identity"]["scope"]["melee"][0]["event_id"] = "999"
        with pytest.raises(ValueError, match="Selected Melee event"):
            verification.verify_material(record, candidate)
    else:
        verification.verify_material(record, candidate)


@pytest.mark.parametrize("consumer", ["statistics", "retained_landing"])
def test_prebuilt_package_does_not_bypass_shared_representative_check(material, consumer):
    import build_pages_artifact as builder
    root, site, _, prepare = material
    relative = ("stats/standard/mtgo/range_4w.json" if consumer == "statistics"
                else "stats/standard/mtgo/landing/current.json")
    document = ({"archetypes": [{"id": "unselected", "high_score_share": .04}]}
                if consumer == "statistics" else {"environment": {"rows": [{"archetype_id": "unselected",
                      "key_cards": [{"name": "First"}, {"name": "Second"}]}]}})
    for base in (root, site):
        path = base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document))
    builder.publication_paths(root, {}).add(relative)
    with pytest.raises(ValueError, match="Shared representatives incomplete.*unselected"):
        verification.verify_material(*prepare())


@pytest.mark.parametrize("relative", ["configs/protection.json", "data/standard/100.json", "stats/catalog.json"])
def test_source_standard_or_public_material_change_invalidates_fixed_candidate(material, relative):
    root, _, _, prepare = material
    record, candidate = prepare()
    (root / relative).write_text("changed")
    with pytest.raises(ValueError, match="Fixed material changed"):
        verification.verify_material(record, candidate)


def test_data_package_cannot_replace_retained_landing(material):
    _, site, _, prepare = material
    (site / "stats/standard/mtgo/landing/current.json").write_text('{"new_unconfirmed_copy":true}')
    with pytest.raises(ValueError, match="unreviewed product"):
        verification.verify_material(*prepare())


def test_private_file_cannot_hide_inside_valid_package(material):
    _, site, _, prepare = material
    (site / "private-review.json").write_text('{}')
    with pytest.raises(ValueError, match="Non-public package"):
        verification.verify_material(*prepare())


@pytest.mark.parametrize("relative", ["features/index.json", "features/2024-W52.json"])
def test_content_delivery_preserves_historical_archives(material, relative):
    _, site, _, prepare = material
    (site / "stats/standard/mtgo/landing" / relative).write_text('{"weeks":[]}')
    with pytest.raises(ValueError, match="historical Feature index|unreviewed product"):
        verification.verify_material(*prepare("landing_content"))


def test_content_delivery_requires_existing_acceptance(material):
    *_, prepare = material
    with pytest.raises(ValueError, match="existing page acceptance"):
        verification.verify_material(*prepare("landing_content"))


@pytest.mark.parametrize("changed", [False, True])
def test_content_uses_real_acceptance_comparison(material, monkeypatch, changed):
    from mtgmeta.mtgo import review_submission as submissions
    _, site, accepted, prepare = material
    packet = submissions.make_packet("preview", "standard", "2025-W02", {"final_page": {"copy": "accepted"}}, bindings={})
    decisions = submissions.record_decision(packet, None, ["final_page"], evidence="synthetic-owner-decision",
        accepted_on="2025-01-07", entrypoint="http://localhost/synthetic")
    accepted.write_text(json.dumps({"submission": packet, "decisions": decisions}))
    current = submissions.make_packet("preview", "standard", "2025-W02",
        {"final_page": {"copy": "different" if changed else "accepted"}}, bindings={})
    monkeypatch.setattr(submissions, "preview_packet", lambda *a: current)
    (site / "stats/standard/mtgo/landing/current.json").write_text('{"copy":"accepted"}')
    if changed:
        with pytest.raises(ValueError):
            verification.verify_material(*prepare("landing_content"))
    else:
        verification.verify_material(*prepare("landing_content"))
