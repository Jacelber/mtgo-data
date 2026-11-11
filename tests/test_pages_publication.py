"""Website selection, source protection and the final package byte budget."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

import build_pages_artifact as pages
from tools.delivery import packages
from mtgmeta.generation_progress import files
from melee_synthetic import source_fixture, registry_file, public_products, write_json

ROOT = Path(__file__).resolve().parents[1]


def test_current_selection_excludes_maintenance_but_keeps_historical_products():
    config = pages.load_config(ROOT, ROOT / "configs/pages_publication.json")
    selected = pages.publication_paths(ROOT, config)
    assert config["maximum_artifact_bytes"] == packages.MAX_BYTES == 1_000_000_000
    assert not ({p.split("/")[0] for p in selected} & {"data", "data_raw", "reports", "fetched.txt"})
    assert {"index.html", "melee/index.html", "stats/catalog.json"} <= selected
    assert any("/pickup/" in p for p in selected)
    assert any("/landing/weeks/" in p for p in selected)
    assert not any("/landing/review/" in p or p.startswith("stats/vintage/") for p in selected)
    pages.validate_public_consumers(ROOT, selected)


@pytest.mark.parametrize("change", ["data", "data_raw", "reports", "fetched.txt", "limit"])
def test_config_rejects_retained_data_or_a_larger_limit(tmp_path, change):
    config = json.loads((ROOT / "configs/pages_publication.json").read_bytes())
    if change == "limit":
        config["maximum_artifact_bytes"] = 1_073_741_824
    elif change == "fetched.txt":
        config["site_files"].append(change)
    else:
        config["site_directories"].append(change)
    path = write_json(tmp_path / "config.json", config)
    with pytest.raises(pages.PublicationError):
        pages.load_config(tmp_path, path)


def test_retained_sources_and_derived_inputs_still_invalidate_fixed_material(tmp_path):
    event, document, path, snapshot = source_fixture(tmp_path)
    registry_file(tmp_path, [event])
    _, catalog = public_products(tmp_path, event, document, path)
    selected = {p.relative_to(tmp_path).as_posix() for p in (tmp_path / "stats").rglob("*.json")}
    write_json(tmp_path / "configs/pages_publication.json", {})
    inputs = pages.publication_inputs(tmp_path, selected)
    assert selected <= inputs
    assert snapshot.relative_to(tmp_path).as_posix() + "/manifest.json" in inputs
    assert path.relative_to(tmp_path).as_posix() in inputs
    assert f"data/modern/melee/classifications/{event.id}.json" in inputs
    assert f"data/modern/melee/opportunities/{event.id}.json" in inputs
    assert not any(p.startswith("data") for p in selected)
    before = files(tmp_path, sorted(inputs))
    raw = snapshot / "deck-1.json"
    raw.write_bytes(raw.read_bytes() + b" ")
    assert files(tmp_path, sorted(pages.publication_inputs(tmp_path, selected))) != before
    extra = snapshot / "extra.json"
    extra.write_text("{}")
    assert extra.relative_to(tmp_path).as_posix() in pages.publication_inputs(tmp_path, selected)


def test_consumer_checks_distinguish_build_bindings_and_public_references(tmp_path):
    write_json(tmp_path / "stats/catalog.json", {"formats": [{"products": [
        {"available": True, "path": "stats/modern/mtgo/meta.json"}]}]})
    meta = {"statistics_catalog": "index.json", "publication": {"artifacts": {"reports/modern/internal.json": "a" * 64}}}
    write_json(tmp_path / "stats/modern/mtgo/meta.json", meta)
    write_json(tmp_path / "stats/modern/mtgo/index.json", {"ranges": [{"file": "range.json", "decks_file": "decks.json"}]})
    write_json(tmp_path / "stats/modern/mtgo/range.json", {})
    write_json(tmp_path / "stats/modern/mtgo/decks.json", {})
    selected = {p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*.json")}
    pages.validate_public_consumers(tmp_path, selected)
    with pytest.raises(pages.PublicationError, match="consumer file is absent"):
        pages.validate_public_consumers(tmp_path, selected - {"stats/modern/mtgo/decks.json"})
    changed = deepcopy(meta)
    changed["statistics_catalog"] = "../../../data/raw.json"
    write_json(tmp_path / "stats/modern/mtgo/meta.json", changed)
    with pytest.raises(pages.PublicationError, match="unsafe"):
        pages.validate_public_consumers(tmp_path, selected)


def test_byte_budget_includes_the_exact_generated_version_marker(tmp_path):
    site = tmp_path / "site"
    for p in packages.PROBES:
        target = site / p
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{}")
    selected = set(packages.PROBES)
    size = 6 + packages.VERSION_MARKER_BYTES
    config = {"maximum_artifact_bytes": size, "generated_overlays": []}
    measurement = pages.measure_artifact(site, config, selected=selected)
    manifest = packages.prepare(site, tmp_path / "package", target="synthetic", source="test")
    assert measurement["packaged_bytes"] == manifest["expanded_bytes"] == size
    config["maximum_artifact_bytes"] -= 1
    with pytest.raises(pages.PublicationError):
        pages.measure_artifact(site, config, selected=selected)
