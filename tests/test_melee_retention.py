"""P7-02 complete-snapshot retention contracts."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

import validate_schemas as schemas
from mtgmeta.melee.client import fetch_complete_event
from mtgmeta.melee.config import load_melee_event_registry
from mtgmeta.melee.retention import (
    MeleeRetentionError,
    main as retention_main,
    retain_normalized_event,
)


ROOT = Path(__file__).resolve().parents[1]
WHITELIST = ROOT / "configs" / "melee_events.yaml"


class Response:
    def __init__(self, content: bytes, url: str, content_type: str):
        self.status_code = 200
        self.content = content
        self.url = url
        self.is_redirect = False
        self.headers = {"Content-Type": content_type}

    def iter_content(self, chunk_size: int):
        for offset in range(0, len(self.content), chunk_size):
            yield self.content[offset:offset + chunk_size]

    def close(self):
        pass


def _event():
    return load_melee_event_registry(WHITELIST).require_fetchable("434455")


def _player(participant_id: int, name: str):
    return {
        "StatusDescription": "Active",
        "Players": [{"ID": participant_id, "DisplayName": name}],
    }


def _complete_snapshot(tmp_path: Path, *, round_number: int = 4) -> tuple[Path, Path]:
    raw_root = tmp_path / "data_raw"
    guid_one = "11111111-1111-1111-1111-111111111111"
    guid_two = "22222222-2222-2222-2222-222222222222"
    html = f"""<html><head><title>Fixture Pro Tour | Melee</title></head><body>
    <button class='round-selector' data-id='104' data-name='Round {round_number}' data-is-completed='True'></button>
    </body></html>""".encode()
    standings = {
        "recordsTotal": 2,
        "data": [
            {
                "ID": 1,
                "Rank": 1,
                "Points": 3,
                "MatchRecord": "1-0-0",
                "Team": _player(11, "Alpha"),
                "Decklists": [{"DecklistId": guid_one, "PlayerId": 11}],
            },
            {
                "ID": 2,
                "Rank": 2,
                "Points": 0,
                "MatchRecord": "0-1-0",
                "Team": _player(22, "Beta"),
                "Decklists": [{"DecklistId": guid_two, "PlayerId": 22}],
            },
        ],
    }
    matches = {
        "recordsTotal": 1,
        "data": [
            {
                "Guid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "RoundId": 104,
                "HasResult": True,
                "ResultString": "2-1-0",
                "TableNumber": 1,
                "ByeReasonDescription": None,
                "LossReasonDescription": None,
                "Competitors": [
                    {"Team": _player(11, "Alpha"), "GameWins": 2, "GameByes": 0},
                    {"Team": _player(22, "Beta"), "GameWins": 1, "GameByes": 0},
                ],
            }
        ],
    }

    def send(method, url, **_kwargs):
        if url.endswith("/Tournament/View/434455"):
            return Response(html, url, "text/html")
        if url.endswith("/Standing/GetRoundStandings"):
            payload = standings
        elif "/Match/GetRoundMatches/104" in url:
            payload = matches
        else:
            decklist_id = url.rsplit("=", 1)[-1]
            payload = {
                "Guid": decklist_id,
                "FormatName": "Modern",
                "Records": [{"c": 0, "n": "Fixture Card", "q": 4}],
            }
        return Response(json.dumps(payload).encode(), url, "application/json")

    result = fetch_complete_event(
        "434455",
        load_melee_event_registry(WHITELIST),
        raw_root,
        request_send=send,
        sleep=lambda _seconds: None,
        now=lambda: datetime(2026, 7, 24, 10, 0, tzinfo=UTC),
        request_delay=0,
        participant_hmac_key=b"p10-03-test-key-material-is-not-secret",
        participant_hmac_key_id="test-2026-08",
    )
    assert result.archive_path is not None
    return raw_root, result.archive_path


def test_complete_snapshot_is_retained_atomically_and_reused_byte_identically(tmp_path):
    raw_root, snapshot = _complete_snapshot(tmp_path)
    data_root = tmp_path / "data"

    first = retain_normalized_event(
        _event(),
        snapshot,
        raw_root=raw_root,
        data_root=data_root,
    )
    first_bytes = first.normalized_path.read_bytes()
    second = retain_normalized_event(
        _event(),
        snapshot,
        raw_root=raw_root,
        data_root=data_root,
    )

    assert first.reused is False
    assert second.reused is True
    assert second.normalized_path.read_bytes() == first_bytes
    assert first.response_count == 5
    assert first.participant_count == first.decklist_count == 2
    assert first.round_count == first.match_count == 1
    assert first.eligible_constructed_match_count == 1
    assert first.quality_status == "valid"
    assert first.quality_issue_codes == ()

    document = json.loads(first_bytes)
    assert document["schema_version"] == "2.2.0"
    assert document["provenance"]["normalized_at"] == document["provenance"]["fetched_at"]
    assert all(
        item["path"].startswith(
            f"data_raw/melee/434455/{snapshot.name}/"
        )
        for item in document["provenance"]["raw_artifacts"]
    )
    loaded, registry = schemas.load_schemas(ROOT / "schemas")
    assert schemas.validate_instance(
        document,
        loaded["melee-event.schema.json"],
        registry,
    ) == []


def test_retention_rejects_incomplete_or_unlisted_snapshot_content(tmp_path):
    raw_root, snapshot = _complete_snapshot(tmp_path)
    (snapshot / "unlisted.json").write_text("{}", encoding="utf-8")

    with pytest.raises(MeleeRetentionError, match="exactly match"):
        retain_normalized_event(
            _event(),
            snapshot,
            raw_root=raw_root,
            data_root=tmp_path / "data",
        )
    assert not (tmp_path / "data").exists()


def test_retention_rejects_snapshot_outside_the_event_archive(tmp_path):
    raw_root, snapshot = _complete_snapshot(tmp_path)
    outside = tmp_path / snapshot.name
    snapshot.rename(outside)

    with pytest.raises(MeleeRetentionError, match="direct immutable collection"):
        retain_normalized_event(
            _event(),
            outside,
            raw_root=raw_root,
            data_root=tmp_path / "data",
        )


def test_retention_refuses_to_overwrite_different_normalized_input(tmp_path):
    raw_root, snapshot = _complete_snapshot(tmp_path)
    data_root = tmp_path / "data"
    result = retain_normalized_event(
        _event(),
        snapshot,
        raw_root=raw_root,
        data_root=data_root,
    )
    result.normalized_path.write_text("{}\n", encoding="utf-8", newline="\n")

    with pytest.raises(MeleeRetentionError, match="different bytes"):
        retain_normalized_event(
            _event(),
            snapshot,
            raw_root=raw_root,
            data_root=data_root,
        )


def test_retention_quality_gate_blocks_draft_only_snapshot_before_output(tmp_path):
    raw_root, snapshot = _complete_snapshot(tmp_path, round_number=1)

    with pytest.raises(MeleeRetentionError, match="no_constructed_swiss_matches"):
        retain_normalized_event(
            _event(),
            snapshot,
            raw_root=raw_root,
            data_root=tmp_path / "data",
        )
    assert not (tmp_path / "data").exists()


def test_retention_cli_defaults_to_no_side_effects_and_requires_execute(tmp_path, capsys):
    raw_root, snapshot = _complete_snapshot(tmp_path)
    data_root = tmp_path / "data"
    args = [
        "--event-id",
        "434455",
        "--snapshot",
        str(snapshot),
        "--registry",
        str(WHITELIST),
        "--raw-root",
        str(raw_root),
        "--data-root",
        str(data_root),
    ]

    assert retention_main(args) == 0
    dry_run = json.loads(capsys.readouterr().out)
    assert dry_run["mode"] == "dry-run"
    assert not data_root.exists()

    assert retention_main([*args, "--execute"]) == 0
    executed = json.loads(capsys.readouterr().out)
    assert executed["mode"] == "execute"
    assert executed["eligible_constructed_matches"] == 1
    assert Path(executed["normalized_path"]).is_file()
