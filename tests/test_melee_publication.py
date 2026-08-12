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
import mtgmeta.melee.publish as publication
from mtgmeta.melee.publish import (
    MeleePublicationError,
    _quality_summary,
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


def test_catalog_exposes_the_verified_reference_event():
    catalog = _load(CATALOG_PATH)
    assert catalog["default_event_id"] == EVENT_ID
    matching_events = [event for event in catalog["events"] if event["event_id"] == EVENT_ID]
    assert len(matching_events) == 1
    event = matching_events[0]
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
    copied_features = copied / "configs/classifier_semantic_features.yaml"
    for source, destination in (
        (EVENT_PATH, copied_event),
        (CLASSIFICATION_PATH, copied_classification),
        (OPPORTUNITY_PATH, copied_opportunity),
        (TAXONOMY_PATH, copied_taxonomy),
        (REGISTRY_PATH, copied_registry),
        (ROOT / "configs/classifier_semantic_features.yaml", copied_features),
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


def test_clean_quality_maps_ready_to_public_pass():
    assert _quality_summary(
        {
            "status": "ready",
            "blocking": False,
            "issues": [],
        }
    ) == {
        "status": "pass",
        "blocking": False,
        "issue_codes": [],
    }


def test_single_stage_publication_advertises_only_supported_scope(
    tmp_path,
    monkeypatch,
):
    event_id = "125"
    input_document = {
        "event_path": f"data/modern/melee/events/{event_id}.json",
        "event_sha256": "a" * 64,
        "event_schema_version": "2.2.0",
        "classification_path": (
            f"data/modern/melee/classifications/{event_id}.json"
        ),
        "classification_sha256": "b" * 64,
        "classification_schema_version": "1.0.0",
        "opportunity_path": (
            f"data/modern/melee/opportunities/{event_id}.json"
        ),
        "opportunity_sha256": "c" * 64,
        "opportunity_schema_version": "1.0.0",
        "taxonomy_path": "my_archetypes/modern.yaml",
        "taxonomy_sha256": "d" * 64,
        "taxonomy_schema_version": "1.0.0",
    }
    identity = {
        "source": "melee",
        "event_id": event_id,
        "format": "modern",
        "input": input_document,
    }
    overview = {
        "schema_version": "1.0.0",
        "document_type": "overview",
        **identity,
        "event_structure": "constructed_single_stage",
        "event": {
            "name": "Synthetic single-stage event",
            "series": "spotlight_series",
            "date": {"start": "2026-07-01", "end": "2026-07-02"},
            "source_url": f"https://melee.gg/Tournament/View/{event_id}",
        },
        "scope_order": ["all_constructed"],
        "default_scope": "all_constructed",
    }
    statistics = {
        "overview": overview,
        "decks": {
            "schema_version": "1.0.0",
            "document_type": "decks",
            **identity,
        },
        "quality": {
            "schema_version": "1.0.0",
            "document_type": "quality",
            **identity,
            "status": "ready",
            "blocking": False,
            "issues": [],
        },
    }
    matchup = {
        "schema_version": "1.0.0",
        "document_type": "matchup",
        **identity,
    }
    monkeypatch.setattr(
        publication,
        "build_event_statistics_from_paths",
        lambda *args: statistics,
    )
    monkeypatch.setattr(
        publication,
        "build_event_matchup_from_paths",
        lambda *args: matchup,
    )

    root = tmp_path / "repo"
    event_directory = (
        root / "stats/modern/melee/events" / event_id
    )
    event_directory.mkdir(parents=True)
    for name, document in {**statistics, "matchup": matchup}.items():
        (event_directory / f"{name}.json").write_bytes(
            statistics_document_bytes(document)
        )
    registry_path = root / "configs/melee_events.yaml"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(
        f"""schema_version: "3.0.0"
events:
  - id: "{event_id}"
    url: "https://melee.gg/Tournament/View/{event_id}"
    name: "Synthetic single-stage event"
    date:
      start: "2026-07-01"
      end: "2026-07-02"
    format: "modern"
    series: "spotlight_series"
    structure: "constructed_single_stage"
    enabled: true
    review_status: "verified"
    tabletop: true
    team_event: false
    mixed_format: false
    raw_requests:
      - id: "tournament"
        resource_type: "tournament"
        url: "https://melee.gg/Tournament/View/{event_id}"
        content_type: "html"
    include:
      swiss: true
      playoffs: true
    phases:
      - id: "constructed"
        stage: "other"
        round_phase: "constructed"
        game_format: "modern"
        swiss: true
        rounds: [1]
    statistics:
      default_match_scope: "all_constructed_swiss"
      constructed_game_format: "modern"
      include_playoffs: false
    source_evidence:
      - "https://example.com/evidence"
    special_handling: []
    notes: "Synthetic publication contract."
""",
        encoding="utf-8",
    )

    built = build_event_publication_from_paths(
        root / input_document["event_path"],
        root / input_document["classification_path"],
        root / input_document["opportunity_path"],
        root / input_document["taxonomy_path"],
        registry_path,
        root,
    )
    assert built["meta"]["event_structure"] == "constructed_single_stage"
    assert built["meta"]["scope_order"] == ["all_constructed"]
    assert built["meta"]["quality"]["status"] == "pass"
    assert built["catalog"]["events"][0]["scope_order"] == ["all_constructed"]
    assert built["catalog"]["events"][0]["quality_status"] == "pass"

    loaded, schema_registry = schemas.load_schemas(ROOT / "schemas")
    assert schemas.validate_instance(
        built["meta"],
        loaded["melee-event-meta.schema.json"],
        schema_registry,
    ) == []
    assert schemas.validate_instance(
        built["catalog"],
        loaded["melee-event-catalog.schema.json"],
        schema_registry,
    ) == []
