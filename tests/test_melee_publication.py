"""P7-07 deterministic Tabletop Major Events publication contracts."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import validate_schemas as schemas
from mtgmeta.melee.publish import (
    MeleePublicationError,
    build_event_publication_from_paths,
)
from mtgmeta.melee.stats import statistics_document_bytes


EVENT_ID = "434455"
EVENT_PATH = ROOT / "data/modern/melee/events" / f"{EVENT_ID}.json"
CLASSIFICATION_PATH = ROOT / "data/modern/melee/classifications" / f"{EVENT_ID}.json"
OPPORTUNITY_PATH = ROOT / "data/modern/melee/opportunities" / f"{EVENT_ID}.json"
TAXONOMY_PATH = ROOT / "my_archetypes/modern.yaml"
REGISTRY_PATH = ROOT / "configs/melee_events.yaml"
EVENT_STATS = ROOT / "stats/modern/melee/events" / EVENT_ID
META_PATH = EVENT_STATS / "meta.json"
CATALOG_PATH = ROOT / "stats/modern/melee/index.json"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build() -> dict[str, dict[str, object]]:
    return build_event_publication_from_paths(
        EVENT_PATH,
        CLASSIFICATION_PATH,
        OPPORTUNITY_PATH,
        TAXONOMY_PATH,
        REGISTRY_PATH,
        ROOT,
    )


def test_committed_publication_is_byte_reproducible_and_schema_valid():
    rebuilt = _build()
    assert statistics_document_bytes(rebuilt["meta"]) == META_PATH.read_bytes()
    assert statistics_document_bytes(rebuilt["catalog"]) == CATALOG_PATH.read_bytes()

    loaded, registry = schemas.load_schemas(ROOT / "schemas")
    assert schemas.validate_instance(
        _load(META_PATH),
        loaded["melee-event-meta.schema.json"],
        registry,
        META_PATH.relative_to(ROOT).as_posix(),
    ) == []
    assert schemas.validate_instance(
        _load(CATALOG_PATH),
        loaded["melee-event-catalog.schema.json"],
        registry,
        CATALOG_PATH.relative_to(ROOT).as_posix(),
    ) == []


def test_meta_descriptors_match_exact_event_output_bytes():
    meta = _load(META_PATH)
    assert meta["default_scope"] == "all_constructed"
    assert meta["quality"] == {
        "status": "warning",
        "blocking": False,
        "issue_codes": [
            "unknown_classifications",
            "disqualified_participant_matches_excluded",
            "mixed_event_day2_selection_bias",
        ],
    }
    for name in ("overview", "decks", "matchup", "quality"):
        path = EVENT_STATS / f"{name}.json"
        payload = path.read_bytes()
        document = json.loads(payload)
        assert meta["outputs"][name] == {
            "path": f"{name}.json",
            "schema_version": document["schema_version"],
            "bytes": len(payload),
            "sha256": sha256(payload).hexdigest(),
        }


def test_catalog_exposes_only_the_verified_reference_event():
    catalog = _load(CATALOG_PATH)
    assert catalog["default_event_id"] == EVENT_ID
    assert len(catalog["events"]) == 1
    event = catalog["events"][0]
    assert event["event_id"] == EVENT_ID
    assert event["meta"] == f"events/{EVENT_ID}/meta.json"
    assert event["overview"] == f"events/{EVENT_ID}/overview.json"
    assert event["decks"] == f"events/{EVENT_ID}/decks.json"
    assert event["matchup"] == f"events/{EVENT_ID}/matchup.json"
    assert event["quality"] == f"events/{EVENT_ID}/quality.json"
    assert event["quality_status"] == "warning"


def test_changed_committed_statistic_fails_closed(tmp_path):
    copied = tmp_path / "repo"
    copied.mkdir()
    copied_event = copied / "data/modern/melee/events" / f"{EVENT_ID}.json"
    copied_classification = (
        copied / "data/modern/melee/classifications" / f"{EVENT_ID}.json"
    )
    copied_opportunity = (
        copied / "data/modern/melee/opportunities" / f"{EVENT_ID}.json"
    )
    copied_taxonomy = copied / "my_archetypes/modern.yaml"
    copied_registry = copied / "configs/melee_events.yaml"
    for source, destination in (
        (EVENT_PATH, copied_event),
        (CLASSIFICATION_PATH, copied_classification),
        (OPPORTUNITY_PATH, copied_opportunity),
        (TAXONOMY_PATH, copied_taxonomy),
        (REGISTRY_PATH, copied_registry),
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    event_stats = copied / "stats/modern/melee/events" / EVENT_ID
    event_stats.mkdir(parents=True)
    for name in ("overview", "decks", "matchup", "quality"):
        (event_stats / f"{name}.json").write_bytes((EVENT_STATS / f"{name}.json").read_bytes())
    tampered = _load(event_stats / "overview.json")
    tampered["default_scope"] = "day1"
    (event_stats / "overview.json").write_bytes(statistics_document_bytes(tampered))

    with pytest.raises(MeleePublicationError, match="does not match deterministic rebuild"):
        build_event_publication_from_paths(
            copied_event,
            copied_classification,
            copied_opportunity,
            copied_taxonomy,
            copied_registry,
            copied,
        )


def test_publication_objects_are_deterministic():
    first = _build()
    second = deepcopy(first)
    assert statistics_document_bytes(first["meta"]) == statistics_document_bytes(second["meta"])
    assert statistics_document_bytes(first["catalog"]) == statistics_document_bytes(second["catalog"])
