"""P5-04 stored-source parsing tests; no network access is permitted."""

from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
import shutil
import sys

import pytest

import validate_schemas as schemas


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import mtgmeta.melee.parser as parser
from mtgmeta.melee.parser import (
    MeleeSourceParseError,
    SourceArtifact,
    parse_raw_snapshot,
    parse_source_response,
)


FIXTURE = ROOT / "tests" / "fixtures" / "melee" / "source_snapshot"


def artifact(
    *, resource_type: str = "tournament", content_type: str = "json"
) -> SourceArtifact:
    return SourceArtifact(
        request_id="fixture",
        resource_type=resource_type,
        page=1,
        url="https://melee.gg/Tournament/View/434455",
        path=f"fixture.{content_type}",
        expected_content_type=content_type,
        sha256="0" * 64,
        bytes=0,
    )


def tournament_payload(**overrides):
    payload = {
        "resource_type": "tournament",
        "tournament": {
            "source_event_id": "434455",
            "name": "Fixture Event",
            "start_text": None,
            "end_text": None,
        },
        "standings": [],
        "decklist_references": [],
        "rounds": [],
        "matches": [],
    }
    payload.update(overrides)
    return payload


def encoded(payload) -> bytes:
    return json.dumps(payload).encode("utf-8")


def copied_snapshot(tmp_path: Path) -> Path:
    destination = tmp_path / "snapshot"
    shutil.copytree(FIXTURE, destination)
    return destination


def rewrite_manifest(snapshot: Path, mutate) -> None:
    path = snapshot / "manifest.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    mutate(value)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def test_stored_snapshot_parses_all_source_record_families_without_normalizing():
    result = parse_raw_snapshot(FIXTURE)
    assert result.event_id == "434455"
    assert result.event_url == "https://melee.gg/Tournament/View/434455"
    assert result.fetched_at == "2026-07-21T12:00:00Z"
    assert [page.artifact.resource_type for page in result.pages] == ["tournament", "decklist"]

    tournament_page, decklist_page = result.pages
    assert tournament_page.tournament.source_event_id == "434455"
    assert tournament_page.tournament.name == "Fixture Mixed Pro Tour"
    assert [standing.source_participant_id for standing in tournament_page.standings] == [
        "participant-101",
        "participant-202",
    ]
    assert tournament_page.standings[1].status_text == "Dropped"
    assert tournament_page.decklist_references[0].source_decklist_id == "9001"
    assert [(round_.label, round_.number) for round_ in tournament_page.rounds] == [
        ("Round 1", 1),
        ("Round 4", 4),
        ("Quarterfinals", None),
    ]
    assert tournament_page.matches[0].result_text == "2-1-0"
    assert [item.outcome_text for item in tournament_page.matches[0].competitor_results] == [
        "Win",
        "Loss",
    ]
    assert tournament_page.matches[1].competitor_source_ids == ("participant-101",)
    assert tournament_page.matches[1].status_text == "Bye"

    decklist = decklist_page.decklists[0]
    assert decklist.source_participant_id == "participant-101"
    assert [(card.name, card.quantity, card.section_text) for card in decklist.cards] == [
        ("Fixture Main Card", 4, "Main Deck"),
        ("Fixture Sideboard Card", 2, "Sideboard"),
    ]

    serialized = json.dumps(asdict(result), sort_keys=True)
    for forbidden in (
        '"stage"',
        '"round_phase"',
        '"game_format"',
        '"result_type"',
        '"constructed_statistics_eligible"',
        '"matchup_eligible"',
        '"archetype"',
    ):
        assert forbidden not in serialized


def test_stored_snapshot_manifest_passes_the_p5_03_archive_schema():
    loaded, registry = schemas.load_schemas(ROOT / "schemas")
    manifest = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))
    assert schemas.validate_instance(
        manifest,
        loaded["melee-raw-archive.schema.json"],
        registry,
    ) == []


def test_parser_is_deterministic_and_does_not_modify_the_snapshot():
    before = {path.name: path.read_bytes() for path in FIXTURE.iterdir()}
    first = parse_raw_snapshot(FIXTURE)
    second = parse_raw_snapshot(FIXTURE)
    after = {path.name: path.read_bytes() for path in FIXTURE.iterdir()}
    assert first == second
    assert before == after


def test_html_selects_exactly_one_supported_json_payload():
    payload = json.dumps(tournament_payload())
    body = (
        "<html><script type='application/json'>{\"unrelated\":true}</script>"
        f"<script type='application/json'>{payload}</script></html>"
    ).encode()
    result = parse_source_response(body, artifact(content_type="html"))
    assert result.tournament.name == "Fixture Event"

    ambiguous = (
        f"<script type='application/json'>{payload}</script>"
        f"<script type='application/json'>{payload}</script>"
    ).encode()
    with pytest.raises(MeleeSourceParseError, match="exactly one"):
        parse_source_response(ambiguous, artifact(content_type="html"))


def test_json_rejects_duplicate_keys_and_invalid_utf8():
    with pytest.raises(MeleeSourceParseError, match="duplicate key"):
        parse_source_response(
            b'{"resource_type":"tournament","resource_type":"tournament"}',
            artifact(),
        )
    with pytest.raises(MeleeSourceParseError, match="valid UTF-8"):
        parse_source_response(b"\xff", artifact())


def test_unknown_source_fields_are_not_silently_discarded():
    payload = tournament_payload(unreviewed_source_field="must fail")
    with pytest.raises(MeleeSourceParseError, match="unsupported fields"):
        parse_source_response(encoded(payload), artifact())

    payload = tournament_payload()
    payload["tournament"]["unreviewed_source_field"] = "must fail"
    with pytest.raises(MeleeSourceParseError, match="unsupported fields"):
        parse_source_response(encoded(payload), artifact())


def test_resource_and_content_type_mismatches_fail_explicitly():
    with pytest.raises(MeleeSourceParseError, match="does not match manifest"):
        parse_source_response(
            encoded({"resource_type": "decklist", "decklist": {}}), artifact()
        )
    with pytest.raises(MeleeSourceParseError, match="unsupported resource type"):
        parse_source_response(encoded(tournament_payload()), replace(artifact(), resource_type="unknown"))
    with pytest.raises(MeleeSourceParseError, match="unsupported content type"):
        parse_source_response(encoded(tournament_payload()), replace(artifact(), expected_content_type="xml"))


def test_real_qualified_single_competitor_preserves_top8_lock_evidence():
    body = encoded({
        "recordsTotal": 1,
        "data": [{
            "Guid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "RoundId": 116,
            "HasResult": True,
            "ResultString": "Participant was assigned a bye",
            "ByeReasonDescription": "Qualified",
            "LossReasonDescription": None,
            "TableNumber": None,
            "Competitors": [{
                "Team": {"StatusDescription": "Active", "Players": [{"ID": 11, "DisplayName": "Fixture"}]},
                "GameWins": 0,
                "GameByes": 2,
            }],
        }],
    })
    match_artifact = replace(
        artifact(resource_type="matches"),
        source_round_id="116",
        url="https://melee.gg/Match/GetRoundMatches/116",
    )
    parsed = parse_source_response(body, match_artifact).matches[0]
    assert parsed.status_text == "Qualified"
    assert parsed.competitor_results[0].outcome_text == "Qualified"
    assert parsed.competitor_results[0].match_points == 3


def test_real_zero_zero_three_result_preserves_intentional_draw_evidence():
    team = lambda participant_id, name: {
        "StatusDescription": "Active",
        "Players": [{"ID": participant_id, "DisplayName": name}],
    }
    body = encoded({
        "recordsTotal": 1,
        "data": [{
            "Guid": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "RoundId": 116,
            "HasResult": True,
            "ResultString": "Fixture result (0-0-3)",
            "GameDraws": 3,
            "ByeReasonDescription": None,
            "LossReasonDescription": None,
            "TableNumber": 1,
            "Competitors": [
                {"Team": team(11, "Alpha"), "GameWins": 0, "GameByes": 0},
                {"Team": team(22, "Beta"), "GameWins": 0, "GameByes": 0},
            ],
        }],
    })
    match_artifact = replace(
        artifact(resource_type="matches"),
        source_round_id="116",
        url="https://melee.gg/Match/GetRoundMatches/116",
    )
    parsed = parse_source_response(body, match_artifact).matches[0]
    assert parsed.status_text == "Intentional Draw"
    assert [item.outcome_text for item in parsed.competitor_results] == ["Draw", "Draw"]


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"tournament": {"name": "Missing source ID"}}, "source_event_id"),
        ({"standings": [{"source_standing_id": "one"}]}, "source_participant_id"),
        ({"rounds": [{"source_round_id": "one", "label": "Round", "number": 0}]}, "integer >= 1"),
        (
            {
                "matches": [
                    {
                        "source_match_id": "one",
                        "source_round_id": "round-one",
                        "competitor_source_ids": [],
                    }
                ]
            },
            "one or two distinct",
        ),
    ],
)
def test_required_source_fields_and_primitive_types_are_fail_closed(override, message):
    with pytest.raises(MeleeSourceParseError, match=message):
        parse_source_response(encoded(tournament_payload(**override)), artifact())


@pytest.mark.parametrize(
    "field",
    ["standings", "decklist_references", "rounds", "matches"],
)
def test_duplicate_source_record_ids_are_rejected(field):
    records = {
        "standings": {
            "source_standing_id": "duplicate",
            "source_participant_id": "participant",
            "display_name": "Fixture",
        },
        "decklist_references": {
            "source_decklist_id": "duplicate",
            "source_participant_id": "participant",
            "url": "https://melee.gg/Decklist/View/1",
        },
        "rounds": {"source_round_id": "duplicate", "label": "Round", "number": 1},
        "matches": {
            "source_match_id": "duplicate",
            "source_round_id": "round",
            "competitor_source_ids": ["participant"],
        },
    }
    with pytest.raises(MeleeSourceParseError, match="duplicate source IDs"):
        parse_source_response(
            encoded(tournament_payload(**{field: [records[field], records[field]]})),
            artifact(),
        )


def test_snapshot_rejects_wrong_byte_count_and_hash(tmp_path):
    snapshot = copied_snapshot(tmp_path)
    rewrite_manifest(snapshot, lambda value: value["responses"][0].update(bytes=1))
    with pytest.raises(MeleeSourceParseError, match="byte count"):
        parse_raw_snapshot(snapshot)

    snapshot = copied_snapshot(tmp_path / "hash")
    rewrite_manifest(snapshot, lambda value: value["responses"][0].update(sha256="0" * 64))
    with pytest.raises(MeleeSourceParseError, match="SHA-256"):
        parse_raw_snapshot(snapshot)


def test_snapshot_rejects_unsafe_or_duplicate_manifest_paths(tmp_path):
    snapshot = copied_snapshot(tmp_path)
    rewrite_manifest(snapshot, lambda value: value["responses"][0].update(path="../escape.json"))
    with pytest.raises(MeleeSourceParseError, match="unsafe"):
        parse_raw_snapshot(snapshot)

    snapshot = copied_snapshot(tmp_path / "duplicate")

    def duplicate(value):
        value["responses"][1]["path"] = value["responses"][0]["path"]

    rewrite_manifest(snapshot, duplicate)
    with pytest.raises(MeleeSourceParseError, match="duplicate response paths"):
        parse_raw_snapshot(snapshot)


def test_snapshot_rejects_event_identity_mismatch(tmp_path):
    snapshot = copied_snapshot(tmp_path)
    rewrite_manifest(snapshot, lambda value: value.update(event_id="999999"))
    with pytest.raises(MeleeSourceParseError, match="event ID does not match"):
        parse_raw_snapshot(snapshot)


def test_parser_size_limit_is_enforced_before_decoding(monkeypatch):
    monkeypatch.setattr(parser, "MAX_SOURCE_BYTES", 3)
    with pytest.raises(MeleeSourceParseError, match="size limit"):
        parse_source_response(encoded(tournament_payload()), artifact())


def test_parser_module_has_no_network_or_normalization_dependencies():
    source = (SRC / "mtgmeta" / "melee" / "parser.py").read_text(encoding="utf-8")
    assert "import requests" not in source
    assert "requests." not in source
    assert "from .normalize" not in source
    assert "import mtgmeta.melee.normalize" not in source
    assert "from ..classifier" not in source
    assert "from .stats" not in source
