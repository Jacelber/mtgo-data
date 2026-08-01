"""P10-02 executable compatibility boundary for Melee event 434455."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath

import validate_schemas as schemas


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "tests/fixtures/melee/434455_compatibility_manifest.json"
SCHEMA_NAME = "melee-compatibility-manifest.schema.json"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _contract() -> dict[str, object]:
    return _load(CONTRACT_PATH)


def _repository_path(value: str) -> Path:
    relative = PurePosixPath(value)
    assert not relative.is_absolute()
    assert ".." not in relative.parts
    return ROOT.joinpath(*relative.parts)


def _assert_exact_file(entry: dict[str, object]) -> None:
    path = _repository_path(str(entry["path"]))
    payload = path.read_bytes()
    assert len(payload) == entry["bytes"]
    assert sha256(payload).hexdigest() == entry["sha256"]


def _selected_projection(
    document: dict[str, object], selection: list[dict[str, object]]
) -> dict[str, object]:
    selected = document
    for step in selection:
        collection = selected[step["collection"]]
        matches = [item for item in collection if item.get(step["field"]) == step["equals"]]
        assert len(matches) == 1
        selected = matches[0]
    return selected


def _assert_projection(
    document: dict[str, object], projection: dict[str, object]
) -> None:
    for key, value in projection["root_requirements"].items():
        assert document[key] == value
    assert _selected_projection(document, projection["selection"]) == projection["expected"]


def test_compatibility_manifest_is_schema_valid():
    loaded, registry = schemas.load_schemas(ROOT / "schemas")
    assert schemas.validate_instance(
        _contract(), loaded[SCHEMA_NAME], registry, CONTRACT_PATH.relative_to(ROOT).as_posix()
    ) == []


def test_exact_compatibility_files_match_bytes_and_digests():
    contract = _contract()
    entries = [contract["immutable_snapshot"]["manifest"], *contract["exact_files"]]
    assert {entry["role"] for entry in entries} == {
        "raw_snapshot_manifest",
        "normalized_event",
        "classification_overlay",
        "opportunity_ledger",
        "event_overview",
        "event_decks",
        "event_matchup",
        "event_quality",
        "event_meta",
    }
    assert len({entry["path"] for entry in entries}) == len(entries)
    for entry in entries:
        _assert_exact_file(entry)


def test_raw_snapshot_manifest_closes_over_every_retained_response():
    contract = _contract()
    snapshot_contract = contract["immutable_snapshot"]
    manifest_path = _repository_path(snapshot_contract["manifest"]["path"])
    snapshot_root = manifest_path.parent
    manifest = _load(manifest_path)

    assert manifest["schema_version"] == snapshot_contract["schema_version"]
    assert manifest["event_id"] == contract["event"]["event_id"]
    assert len(manifest["responses"]) == snapshot_contract["response_count"]

    declared = set()
    for response in manifest["responses"]:
        relative = PurePosixPath(response["path"])
        assert not relative.is_absolute()
        assert ".." not in relative.parts
        assert response["path"] not in declared
        declared.add(response["path"])
        payload = snapshot_root.joinpath(*relative.parts).read_bytes()
        assert len(payload) == response["bytes"]
        assert sha256(payload).hexdigest() == response["sha256"]

    retained = {
        path.relative_to(snapshot_root).as_posix()
        for path in snapshot_root.rglob("*")
        if path.is_file()
    }
    assert retained == declared | {manifest_path.name}


def test_expandable_catalogs_preserve_only_the_selected_projection():
    contract = _contract()
    for projection in contract["catalog_projections"]:
        document = _load(_repository_path(projection["path"]))
        _assert_projection(document, projection)


def test_unrelated_catalog_growth_does_not_change_the_selected_projection():
    contract = _contract()
    event_projection, global_projection = contract["catalog_projections"]

    event_catalog = _load(_repository_path(event_projection["path"]))
    expanded_event_catalog = deepcopy(event_catalog)
    expanded_event_catalog["default_event_id"] = "999999"
    expanded_event_catalog["events"].append({"event_id": "999999"})
    _assert_projection(expanded_event_catalog, event_projection)

    global_catalog = _load(_repository_path(global_projection["path"]))
    expanded_global_catalog = deepcopy(global_catalog)
    expanded_global_catalog["generated"] = "later-allowed-value"
    expanded_global_catalog["formats"].append({"id": "future", "products": []})
    _assert_projection(expanded_global_catalog, global_projection)


def test_global_catalogs_are_not_part_of_the_exact_byte_set():
    contract = _contract()
    exact_paths = {
        contract["immutable_snapshot"]["manifest"]["path"],
        *(entry["path"] for entry in contract["exact_files"]),
    }
    assert {projection["path"] for projection in contract["catalog_projections"]} == {
        "stats/modern/melee/index.json",
        "stats/catalog.json",
    }
    assert exact_paths.isdisjoint(
        projection["path"] for projection in contract["catalog_projections"]
    )


def test_contract_requires_separate_owner_approved_byte_migration():
    policy = _contract()["migration_policy"]
    assert policy == {
        "exact_byte_change": "separate_owner_approved_version_migration",
        "catalog_growth": "allowed_when_selected_projection_is_unchanged",
        "legacy_snapshot_regeneration": "prohibited",
    }
