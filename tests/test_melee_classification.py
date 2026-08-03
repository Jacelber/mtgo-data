"""P7-03 shared-classifier overlay contracts."""

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
from mtgmeta.config import parse_rule_text
from mtgmeta.melee.classification import (
    MeleeClassificationError,
    build_classification_overlay,
    build_classification_overlay_from_paths,
    classification_overlay_bytes,
    main,
    write_classification_overlay,
)


EVENT_ID = "434455"
EVENT_PATH = ROOT / "data" / "modern" / "melee" / "events" / f"{EVENT_ID}.json"
RULE_PATH = ROOT / "my_archetypes" / "modern.yaml"
OVERLAY_PATH = (
    ROOT / "data" / "modern" / "melee" / "classifications" / f"{EVENT_ID}.json"
)


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _fixture_event(cards: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema_version": "2.2.0",
        "metadata": {
            "source": "melee",
            "event_id": "123",
            "constructed_format": "modern",
        },
        "participants": [{"id": "participant-1"}],
        "decklists": [
            {
                "participant_id": "participant-1",
                "game_format": "modern",
                "status": "submitted",
                "cards": cards,
            }
        ],
    }


def _fixture_rules():
    return parse_rule_text(
        """
schema_version: "1.0.0"
format: modern
archetypes:
  - id: example
    name: Example
    priority: 100
    subtypes:
      - id: alpha
        name: Alpha
    rules:
      - id: example-alpha
        priority: 200
        subtype_id: alpha
        conditions:
          all:
            - card: Alpha Card
              zone: main
              min_count: 1
      - id: example-parent
        priority: 100
        subtype_id: null
        conditions:
          all:
            - card: Parent Card
              zone: main
              min_count: 1
"""
    )


def _fixture_overlay(event: dict[str, object]) -> dict[str, object]:
    return build_classification_overlay(
        event,
        _fixture_rules(),
        event_path="data/modern/melee/events/123.json",
        event_sha256="a" * 64,
        rule_path="my_archetypes/modern.yaml",
        rule_sha256="b" * 64,
    )


def test_adapter_uses_shared_rules_and_retains_full_evidence():
    document = _fixture_overlay(
        _fixture_event(
            [
                {"name": "Alpha Card", "quantity": 4, "section": "main"},
                {"name": "Side Card", "quantity": 2, "section": "sideboard"},
            ]
        )
    )

    assert document["summary"] == {
        "total_records": 1,
        "classified": 1,
        "unknown": 0,
        "conflicts": 0,
        "invalid_decks": 0,
        "multiple_matches": 0,
        "overridden_matches": 0,
        "selected_subtypes": 1,
        "parent_only": 0,
        "same_parent_multiple_subtype_matches": 0,
        "residual_subtype_violations": 0,
        "selected_by_parent": {"example": 1},
        "selected_by_subtype": {"example/alpha": 1},
        "strict_validation": "pass",
    }
    record = document["records"][0]
    assert record["participant_id"] == "participant-1"
    assert record["selected"] == {
        "archetype_id": "example",
        "archetype_name": "Example",
        "subtype_id": "alpha",
        "subtype_name": "Alpha",
        "rule_id": "example-alpha",
        "priority": 200,
    }
    assert record["matched_rules"][0]["evidence"] == [
        {
            "card": "Alpha Card",
            "zone": "main",
            "actual_count": 4,
            "min_count": 1,
            "max_count": None,
            "exact_count": None,
        }
    ]


def test_adapter_normalizes_double_faced_names_before_shared_rules():
    document = _fixture_overlay(
        _fixture_event(
            [
                {
                    "name": "Alpha Card // Alpha Back",
                    "quantity": 4,
                    "section": "main",
                }
            ]
        )
    )

    assert document["summary"]["classified"] == 1
    assert document["summary"]["unknown"] == 0
    assert document["records"][0]["selected"]["archetype_id"] == "example"


def test_unknown_deck_retains_reviewable_normalized_cards_without_blocking():
    document = _fixture_overlay(
        _fixture_event(
            [
                {"name": " Unknown Card ", "quantity": 4, "section": "main"},
                {"name": "Side Card", "quantity": 1, "section": "sideboard"},
            ]
        )
    )

    assert document["summary"]["unknown"] == 1
    assert document["summary"]["strict_validation"] == "pass"
    assert document["quality"] == {
        "status": "pass",
        "blocking": False,
        "blocking_reasons": [],
        "unknowns_blocking": False,
    }
    assert document["records"][0]["unknown_deck"] == {
        "main_deck": [{"name": "Unknown Card", "quantity": 4}],
        "sideboard": [{"name": "Side Card", "quantity": 1}],
    }


@pytest.mark.parametrize(
    ("cards", "reason"),
    [
        ([], "invalid_decks"),
        ([{"name": "Card", "quantity": 1, "section": "commander"}], "invalid_decks"),
        ([{"name": "Parent Card", "quantity": 4, "section": "main"}], "residual_subtype_violations"),
    ],
)
def test_invalid_or_residual_subtype_records_block_strict_generation(cards, reason):
    document = _fixture_overlay(_fixture_event(cards))

    assert document["summary"]["strict_validation"] == "fail"
    assert document["quality"]["status"] == "blocked"
    assert reason in document["quality"]["blocking_reasons"]


def test_duplicate_participant_or_wrong_event_format_fails_closed():
    event = _fixture_event(
        [{"name": "Alpha Card", "quantity": 4, "section": "main"}]
    )
    event["decklists"].append(deepcopy(event["decklists"][0]))
    with pytest.raises(MeleeClassificationError, match="unique participant_id"):
        _fixture_overlay(event)

    event = _fixture_event(
        [{"name": "Alpha Card", "quantity": 4, "section": "main"}]
    )
    event["metadata"]["constructed_format"] = "standard"
    with pytest.raises(MeleeClassificationError, match="does not match rules"):
        _fixture_overlay(event)

    event = _fixture_event(
        [{"name": "Alpha Card", "quantity": 4, "section": "main"}]
    )
    event["participants"] = [{"id": "participant-other"}]
    with pytest.raises(MeleeClassificationError, match="unknown participants"):
        _fixture_overlay(event)


def test_bytes_and_atomic_writer_are_deterministic(tmp_path):
    document = _fixture_overlay(
        _fixture_event(
            [{"name": "Alpha Card", "quantity": 4, "section": "main"}]
        )
    )
    first = classification_overlay_bytes(document)
    second = classification_overlay_bytes(deepcopy(document))
    destination = tmp_path / "classifications" / "123.json"

    assert first == second
    assert write_classification_overlay(destination, first) is False
    assert write_classification_overlay(destination, second) is True
    assert destination.read_bytes() == first
    assert not list(destination.parent.glob("*.tmp"))


def test_strict_cli_does_not_write_a_blocked_overlay(tmp_path, capsys):
    event_path = tmp_path / "data/modern/melee/events/123.json"
    rule_path = tmp_path / "my_archetypes/modern.yaml"
    event_path.parent.mkdir(parents=True)
    rule_path.parent.mkdir(parents=True)
    event_path.write_text(
        json.dumps(
            _fixture_event(
                [{"name": "Card", "quantity": 1, "section": "commander"}]
            )
        ),
        encoding="utf-8",
    )
    rule_path.write_text(
        """
schema_version: "1.0.0"
format: modern
archetypes:
  - id: example
    name: Example
    priority: 1
    subtypes: []
    rules:
      - id: example-rule
        priority: 1
        subtype_id: null
        conditions:
          all:
            - card: Card
              zone: main
              min_count: 1
""",
        encoding="utf-8",
    )

    assert main(
        [
            "--root",
            str(tmp_path),
            "--format",
            "modern",
            "--event-id",
            "123",
            "--execute",
            "--strict",
        ]
    ) == 1
    assert "strict validation FAIL" in capsys.readouterr().err
    assert not (tmp_path / "data/modern/melee/classifications/123.json").exists()


def test_committed_reference_overlay_is_schema_valid_and_byte_reproducible():
    committed = json.loads(OVERLAY_PATH.read_text(encoding="utf-8"))
    rebuilt = build_classification_overlay_from_paths(EVENT_PATH, RULE_PATH, ROOT)

    assert classification_overlay_bytes(rebuilt) == OVERLAY_PATH.read_bytes()
    loaded, registry = schemas.load_schemas(ROOT / "schemas")
    assert schemas.validate_instance(
        committed,
        loaded["melee-classification.schema.json"],
        registry,
    ) == []


def test_overlay_schema_rejects_status_payload_mismatches():
    document = _fixture_overlay(
        _fixture_event(
            [{"name": "Alpha Card", "quantity": 4, "section": "main"}]
        )
    )
    loaded, registry = schemas.load_schemas(ROOT / "schemas")
    document["records"][0]["selected"] = None

    assert schemas.validate_instance(
        document,
        loaded["melee-classification.schema.json"],
        registry,
    )


def test_committed_reference_overlay_conserves_all_submitted_decklists():
    event = json.loads(EVENT_PATH.read_text(encoding="utf-8"))
    overlay = json.loads(OVERLAY_PATH.read_text(encoding="utf-8"))
    submitted_ids = {
        item["participant_id"]
        for item in event["decklists"]
        if item["status"] == "submitted" and item["game_format"] == "modern"
    }
    record_ids = [item["participant_id"] for item in overlay["records"]]
    summary = overlay["summary"]

    assert len(record_ids) == len(set(record_ids)) == 362
    assert set(record_ids) == submitted_ids
    assert summary["total_records"] == (
        summary["classified"]
        + summary["unknown"]
        + summary["conflicts"]
        + summary["invalid_decks"]
    )
    assert summary["classified"] == (
        summary["selected_subtypes"] + summary["parent_only"]
    )
    assert summary == {
        **summary,
        "total_records": 362,
        "classified": 352,
        "unknown": 10,
        "conflicts": 0,
        "invalid_decks": 0,
        "multiple_matches": 76,
        "overridden_matches": 76,
        "selected_subtypes": 153,
        "parent_only": 199,
        "same_parent_multiple_subtype_matches": 2,
        "residual_subtype_violations": 0,
        "strict_validation": "pass",
    }
    assert summary["selected_by_parent"]["boros-energy"] == 45
    assert summary["selected_by_parent"]["mardu-energy"] == 1
    assert summary["selected_by_parent"]["ruby-storm"] == 16


def test_committed_overlay_hashes_exact_input_and_shared_taxonomy():
    overlay = json.loads(OVERLAY_PATH.read_text(encoding="utf-8"))

    assert overlay["input"] == {
        "event_path": "data/modern/melee/events/434455.json",
        "event_sha256": _digest(EVENT_PATH),
        "event_schema_version": "2.2.0",
        "event_decklist_count": 362,
        "submitted_format_decklist_count": 362,
        "excluded_decklist_count": 0,
    }
    assert overlay["taxonomy"]["rule_path"] == "my_archetypes/modern.yaml"
    assert overlay["taxonomy"]["rule_sha256"] == _digest(RULE_PATH)
    assert overlay["taxonomy"]["archetype_count"] == 55
    assert overlay["taxonomy"]["rule_count"] == 102
    assert overlay["taxonomy"]["subtype_count"] == 55


def test_unknowns_keep_deck_evidence_and_disqualified_deck_is_classified():
    event = json.loads(EVENT_PATH.read_text(encoding="utf-8"))
    overlay = json.loads(OVERLAY_PATH.read_text(encoding="utf-8"))
    unknowns = [
        item for item in overlay["records"]
        if item["classification_status"] == "unknown"
    ]
    disqualified_id = next(
        item["id"] for item in event["participants"]
        if item["status"] == "disqualified"
    )
    disqualified = next(
        item for item in overlay["records"]
        if item["participant_id"] == disqualified_id
    )

    assert len(unknowns) == 10
    assert all(item["unknown_deck"]["main_deck"] for item in unknowns)
    assert all(
        " // " not in card["name"]
        for item in unknowns
        for zone in ("main_deck", "sideboard")
        for card in item["unknown_deck"][zone]
    )
    assert disqualified["classification_status"] == "classified"
    assert disqualified["selected"]["archetype_id"] == "eldrazi-tron"
    assert disqualified["selected"]["subtype_id"] == "colorless"


def test_overlay_retains_no_participant_names_or_source_ids():
    overlay = json.loads(OVERLAY_PATH.read_text(encoding="utf-8"))

    def keys(value):
        if isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from keys(child)

    assert {"display_name", "source_id", "player_name"}.isdisjoint(keys(overlay))
