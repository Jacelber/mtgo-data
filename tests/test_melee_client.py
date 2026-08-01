"""P5-03 contract tests use a fake transport and never contact melee.gg."""

from __future__ import annotations

from datetime import UTC, datetime
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

import validate_schemas as schemas
import mtgmeta.melee.client as melee_client
from mtgmeta.melee.__main__ import main as melee_main
from mtgmeta.melee.client import MeleeFetchError, MeleeRawFetchResult, MeleeRequestBoundaryError, fetch_complete_event, fetch_raw_event, planned_request_urls
from mtgmeta.melee.config import DisabledMeleeEventError, MeleeConfigError, parse_melee_event_text
from mtgmeta.melee.parser import MeleeSourceParseError, parse_raw_snapshot
from mtgmeta.melee.normalize import normalize_parsed_snapshot
from mtgmeta.melee.retention import MeleeRetentionError, retain_normalized_event


WHITELIST = ROOT / "configs" / "melee_events.yaml"
TEST_HMAC_KEY = b"p10-03-test-key-material-is-not-secret"
TEST_HMAC_KEY_ID = "test-2026-08"


def privacy_options():
    return {
        "participant_hmac_key": TEST_HMAC_KEY,
        "participant_hmac_key_id": TEST_HMAC_KEY_ID,
    }


class Response:
    def __init__(
        self,
        status_code: int = 200,
        content: bytes = b"ok",
        *,
        url: str | None = None,
        redirect: bool = False,
        headers: dict[str, str] | None = None,
    ):
        self.status_code = status_code
        self.content = content
        self.url = url
        self.is_redirect = redirect
        self.headers = headers or {}
        self.closed = False

    def iter_content(self, chunk_size: int):
        for offset in range(0, len(self.content), chunk_size):
            yield self.content[offset:offset + chunk_size]

    def close(self):
        self.closed = True


def registry(*, enabled: bool = True, pagination: bool = False):
    data = yaml.safe_load(WHITELIST.read_text(encoding="utf-8"))
    event = data["events"][0]
    event["enabled"] = enabled
    if pagination:
        event["raw_requests"][0]["pagination"] = {"parameter": "page", "start_page": 2, "max_pages": 2}
    return parse_melee_event_text(yaml.safe_dump(data, sort_keys=False))


def fixed_now():
    return datetime(2026, 7, 21, 12, 0, tzinfo=UTC)


def test_disabled_event_fails_before_transport_or_archive_side_effects(tmp_path):
    calls = []
    with pytest.raises(DisabledMeleeEventError, match="disabled"):
        fetch_raw_event("434455", registry(enabled=False), tmp_path, request_get=lambda *_args, **_kwargs: calls.append(True))
    assert calls == []
    assert list(tmp_path.iterdir()) == []
    with pytest.raises(DisabledMeleeEventError, match="disabled"):
        fetch_complete_event(
            "434455", registry(enabled=False), tmp_path,
            request_send=lambda *_args, **_kwargs: calls.append(True),
        )
    assert calls == []
    assert list(tmp_path.iterdir()) == []


def test_complete_event_requires_hmac_settings_before_network_or_archive_side_effects(tmp_path):
    calls = []
    with pytest.raises(ValueError, match="at least 32 bytes"):
        fetch_complete_event(
            "434455",
            registry(),
            tmp_path,
            request_send=lambda *_args, **_kwargs: calls.append(True),
        )
    assert calls == []
    assert not tmp_path.exists() or list(tmp_path.iterdir()) == []


def test_dry_run_validates_enabled_request_plan_without_side_effects(tmp_path):
    calls = []
    result = fetch_raw_event(
        "434455",
        registry(),
        tmp_path,
        dry_run=True,
        request_get=lambda *_args, **_kwargs: calls.append(True),
    )
    assert result.dry_run is True
    assert result.archive_path is None
    assert result.planned_urls == ("https://melee.gg/Tournament/View/434455",)
    assert planned_request_urls("434455", registry()) == result.planned_urls
    assert calls == []
    assert list(tmp_path.iterdir()) == []


def test_fetch_creates_one_atomic_source_preserving_snapshot_and_manifest(tmp_path):
    calls = []

    def request(url, **kwargs):
        calls.append((url, kwargs))
        return Response(
            content=b"<html>source</html>",
            url=url,
            headers={"Content-Type": "text/html; charset=utf-8", "ETag": '"source-v1"', "Set-Cookie": "secret"},
        )

    result = fetch_raw_event(
        "434455", registry(), tmp_path, request_get=request, sleep=lambda _seconds: None, now=fixed_now
    )
    assert result.archive_path == tmp_path / "melee" / "434455" / "20260721T120000Z-01"
    assert (result.archive_path / "tournament-001.html").read_bytes() == b"<html>source</html>"
    manifest = json.loads((result.archive_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["event_id"] == "434455"
    assert manifest["fetched_at"] == "2026-07-21T12:00:00Z"
    assert manifest["responses"][0]["path"] == "tournament-001.html"
    assert manifest["responses"][0]["sha256"] == "41fef03dd7e2f1888f4065b10d6b547af06737cae69cb22fde9f3de74b3cec95"
    assert manifest["responses"][0]["resource_type"] == "tournament"
    assert manifest["responses"][0]["expected_content_type"] == "html"
    assert manifest["responses"][0]["response_content_type"] == "text/html; charset=utf-8"
    assert manifest["responses"][0]["etag"] == '"source-v1"'
    assert "set_cookie" not in manifest["responses"][0]
    assert calls[0][1]["allow_redirects"] is False
    assert calls[0][1]["stream"] is True
    assert "Cookie" not in calls[0][1]["headers"]
    assert "Authorization" not in calls[0][1]["headers"]
    loaded, schema_registry = schemas.load_schemas(ROOT / "schemas")
    assert schemas.validate_instance(manifest, loaded["melee-raw-archive.schema.json"], schema_registry) == []


def test_pagination_retry_and_request_delay_are_bounded_and_injectable(tmp_path):
    calls = []
    waits = []

    def request(url, **_kwargs):
        calls.append(url)
        if len(calls) == 1:
            return Response(status_code=503, url=url)
        return Response(content=url.encode("utf-8"), url=url)

    result = fetch_raw_event(
        "434455",
        registry(pagination=True),
        tmp_path,
        request_get=request,
        sleep=waits.append,
        now=fixed_now,
        retry_delay=2,
        request_delay=1,
    )
    assert calls == [
        "https://melee.gg/Tournament/View/434455?page=2",
        "https://melee.gg/Tournament/View/434455?page=2",
        "https://melee.gg/Tournament/View/434455?page=3",
    ]
    assert waits == [2, 1]
    assert [record.page for record in result.responses] == [2, 3]
    assert [record.attempts for record in result.responses] == [2, 1]


def test_failed_or_redirected_request_leaves_no_partial_snapshot(tmp_path):
    with pytest.raises(MeleeFetchError, match="after 2 attempts"):
        fetch_raw_event(
            "434455",
            registry(),
            tmp_path,
            request_get=lambda url, **_kwargs: Response(status_code=500, url=url),
            sleep=lambda _seconds: None,
            attempts=2,
            now=fixed_now,
        )
    assert not (tmp_path / "melee").exists()

    calls = []
    with pytest.raises(MeleeFetchError, match="HTTP 404"):
        fetch_raw_event(
            "434455",
            registry(),
            tmp_path,
            request_get=lambda url, **_kwargs: calls.append(url) or Response(status_code=404, url=url),
            sleep=lambda _seconds: None,
            attempts=3,
            now=fixed_now,
        )
    assert calls == ["https://melee.gg/Tournament/View/434455"]
    assert not (tmp_path / "melee").exists()

    with pytest.raises(MeleeRequestBoundaryError, match="redirects"):
        fetch_raw_event(
            "434455",
            registry(),
            tmp_path,
            request_get=lambda _url, **_kwargs: Response(url="https://example.invalid/redirect", redirect=True),
            sleep=lambda _seconds: None,
            now=fixed_now,
        )
    assert not (tmp_path / "melee").exists()


def test_refetch_preserves_existing_snapshot_instead_of_overwriting(tmp_path):
    def request(url, **_kwargs):
        return Response(content=b"source", url=url)

    first = fetch_raw_event("434455", registry(), tmp_path, request_get=request, sleep=lambda _seconds: None, now=fixed_now)
    second = fetch_raw_event("434455", registry(), tmp_path, request_get=request, sleep=lambda _seconds: None, now=fixed_now)
    assert first.archive_path != second.archive_path
    assert first.archive_path.name.endswith("-01")
    assert second.archive_path.name.endswith("-02")
    assert (first.archive_path / "tournament-001.html").read_bytes() == b"source"


def test_streaming_size_limit_cleans_partial_archive(tmp_path, monkeypatch):
    monkeypatch.setattr(melee_client, "MAX_RESPONSE_BYTES", 5)
    with pytest.raises(melee_client.MeleeArchiveError, match="size limit"):
        fetch_raw_event(
            "434455",
            registry(),
            tmp_path,
            request_get=lambda url, **_kwargs: Response(content=b"123456", url=url),
            sleep=lambda _seconds: None,
            now=fixed_now,
        )
    assert not (tmp_path / "melee").exists()


def test_archive_total_size_and_response_count_are_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(melee_client, "MAX_ARCHIVE_BYTES", 5)
    with pytest.raises(melee_client.MeleeArchiveError, match="size limit"):
        fetch_raw_event(
            "434455",
            registry(pagination=True),
            tmp_path,
            request_get=lambda url, **_kwargs: Response(content=b"123", url=url),
            sleep=lambda _seconds: None,
            now=fixed_now,
        )
    assert not (tmp_path / "melee").exists()

    monkeypatch.setattr(melee_client, "MAX_ARCHIVE_RESPONSES", 1)
    with pytest.raises(MeleeRequestBoundaryError, match="exceeds 1 responses"):
        planned_request_urls("434455", registry(pagination=True))
    assert not (tmp_path / "melee").exists()


def test_runtime_limits_fail_before_archive_or_transport_side_effects(tmp_path):
    calls = []
    for options in ({"attempts": 0}, {"timeout": 0}, {"retry_delay": -1}, {"request_delay": -1}):
        with pytest.raises(ValueError):
            fetch_raw_event(
                "434455",
                registry(),
                tmp_path,
                request_get=lambda *_args, **_kwargs: calls.append(True),
                **options,
            )
    assert calls == []
    assert list(tmp_path.iterdir()) == []


def test_cli_defaults_to_dry_run_and_requires_explicit_execute(tmp_path, capsys):
    data = yaml.safe_load(WHITELIST.read_text(encoding="utf-8"))
    data["events"][0]["enabled"] = True
    registry_path = tmp_path / "events.yaml"
    registry_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    calls = []

    def fake_fetch(event_id, _registry, raw_root, *, dry_run):
        calls.append((event_id, raw_root, dry_run))
        return MeleeRawFetchResult(event_id, dry_run, None, ("https://melee.gg/Tournament/View/434455",), ())

    args = ["--event-id", "434455", "--registry", str(registry_path), "--raw-root", str(tmp_path / "raw")]
    assert melee_main(args, fetch=fake_fetch) == 0
    assert calls[-1][2] is True
    assert json.loads(capsys.readouterr().out)["mode"] == "dry-run"
    assert melee_main([*args, "--execute"], fetch=fake_fetch) == 0
    assert calls[-1][2] is False


def test_cli_complete_mode_requires_execute_and_uses_complete_collector(tmp_path, capsys, monkeypatch):
    data = yaml.safe_load(WHITELIST.read_text(encoding="utf-8"))
    data["events"][0]["enabled"] = True
    registry_path = tmp_path / "events.yaml"
    registry_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    args = ["--event-id", "434455", "--registry", str(registry_path), "--raw-root", str(tmp_path / "raw"), "--complete"]
    assert melee_main(args) == 2
    assert "requires --execute" in capsys.readouterr().err
    calls = []

    assert melee_main([*args, "--execute"]) == 2
    assert "MELEE_PARTICIPANT_HMAC_KEY_BASE64" in capsys.readouterr().err

    monkeypatch.setenv("MELEE_PARTICIPANT_HMAC_KEY_BASE64", "cDEwLTAzLXRlc3Qta2V5LW1hdGVyaWFsLWlzLW5vdC1zZWNyZXQ=")
    monkeypatch.setenv("MELEE_PARTICIPANT_HMAC_KEY_ID", TEST_HMAC_KEY_ID)

    def fake_complete(
        event_id, _registry, raw_root, *, progress,
        participant_hmac_key, participant_hmac_key_id,
    ):
        calls.append((event_id, raw_root))
        assert participant_hmac_key == TEST_HMAC_KEY
        assert participant_hmac_key_id == TEST_HMAC_KEY_ID
        progress({"stage": "complete", "completed_responses": 1, "planned_responses": 1})
        return MeleeRawFetchResult(event_id, False, tmp_path / "snapshot", ("https://melee.gg/Tournament/View/434455",), ())

    assert melee_main([*args, "--execute"], complete_fetch=fake_complete) == 0
    assert calls == [("434455", tmp_path / "raw")]
    assert '"stage": "complete"' in capsys.readouterr().err


def test_raw_request_contract_rejects_cross_event_and_duplicate_request_ids():
    data = yaml.safe_load(WHITELIST.read_text(encoding="utf-8"))
    event = data["events"][0]
    event["raw_requests"].append(dict(event["raw_requests"][0]))
    with pytest.raises(MeleeConfigError, match="duplicate request IDs"):
        parse_melee_event_text(yaml.safe_dump(data, sort_keys=False))

    event["raw_requests"] = [dict(event["raw_requests"][0], url="https://melee.gg/Tournament/View/999999")]
    with pytest.raises(MeleeConfigError, match="for this event"):
        parse_melee_event_text(yaml.safe_dump(data, sort_keys=False))


def test_whitelist_v3_accepts_explicit_decklist_but_rejects_wrong_resource_path():
    data = yaml.safe_load(WHITELIST.read_text(encoding="utf-8"))
    assert data["schema_version"] == "3.0.0"
    event = data["events"][0]
    event["raw_requests"].append(
        {
            "id": "decklist_one",
            "resource_type": "decklist",
            "url": "https://melee.gg/Decklist/View/1",
            "content_type": "html",
        }
    )
    loaded = parse_melee_event_text(yaml.safe_dump(data, sort_keys=False))
    assert loaded.events[0].raw_requests[-1].resource_type == "decklist"
    event["raw_requests"][-1]["url"] = "https://melee.gg/Tournament/View/434455"
    with pytest.raises(MeleeConfigError, match="for this event"):
        parse_melee_event_text(yaml.safe_dump(data, sort_keys=False))


def test_complete_event_collects_and_parses_real_wire_shapes_without_credentials(tmp_path):
    guid_one = "11111111-1111-1111-1111-111111111111"
    guid_two = "22222222-2222-2222-2222-222222222222"
    html = b"""<html><head><title>Fixture Pro Tour | Melee</title></head><body>
    <button class='round-selector' data-id='101' data-name='Round 1' data-is-completed='True'></button>
    <button class='round-selector' data-id='101' data-name='Round 1'></button>
    </body></html>"""

    def player(participant_id, name):
        return {
            "StatusDescription": "Active",
            "Players": [{
                "ID": participant_id,
                "DisplayName": name,
                "Username": f"private-{participant_id}",
                "PronounsDescription": "unused",
            }],
        }

    standings = {
        "recordsTotal": 2,
        "data": [
            {"ID": 1, "Rank": 1, "Points": 3, "MatchRecord": "1-0-0", "Team": player(11, "Alpha"),
             "Decklists": [{"DecklistId": guid_one, "PlayerId": 11}]},
            {"ID": 2, "Rank": 2, "Points": 0, "MatchRecord": "0-1-0", "Team": player(22, "Beta"),
             "Decklists": [{"DecklistId": guid_two, "PlayerId": 22}]},
        ],
    }
    matches = {
        "recordsTotal": 1,
        "data": [{
            "Guid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "RoundId": 101,
            "HasResult": True, "ResultString": "2-1-0", "TableNumber": 1,
            "ByeReasonDescription": None, "LossReasonDescription": None,
            "Competitors": [
                {"Team": player(11, "Alpha"), "GameWins": 2, "GameByes": 0},
                {"Team": player(22, "Beta"), "GameWins": 1, "GameByes": 0},
            ],
        }],
    }
    calls = []

    def send(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if url.endswith("/Tournament/View/434455"):
            return Response(content=html, url=url, headers={"Content-Type": "text/html"})
        if url.endswith("/Standing/GetRoundStandings"):
            payload = standings
        elif "/Match/GetRoundMatches/101" in url:
            payload = matches
        else:
            decklist_id = url.rsplit("=", 1)[-1]
            payload = {"Guid": decklist_id, "FormatName": "Modern", "Records": [{"c": 0, "n": "Fixture Card", "q": 4}]}
        return Response(content=json.dumps(payload).encode(), url=url, headers={"Content-Type": "application/json"})

    result = fetch_complete_event(
        "434455", registry(), tmp_path, request_send=send,
        sleep=lambda _seconds: None, now=fixed_now, request_delay=0,
        **privacy_options(),
    )
    manifest = json.loads((result.archive_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "3.0.0"
    assert manifest["participant_identity"] == {
        "scheme": "hmac-sha256-event-v1",
        "key_id": TEST_HMAC_KEY_ID,
    }
    assert [item["resource_type"] for item in manifest["responses"]] == [
        "tournament", "standings", "matches", "decklist", "decklist"
    ]
    assert all("Cookie" not in call[2]["headers"] and "Authorization" not in call[2]["headers"] for call in calls)
    assert calls[0][0] == "GET"
    assert calls[1][0] == calls[2][0] == "POST"
    assert manifest["responses"][1]["source_round_id"] == "101"
    assert manifest["responses"][1]["request_body_sha256"]
    persisted_responses = b"".join(
        (result.archive_path / item["path"]).read_bytes()
        for item in manifest["responses"]
    )
    assert b'"display_name":"Alpha"' in persisted_responses
    for forbidden in (
        b'"Username"', b'"PronounsDescription"', b'"PlayerId"',
        b'"source_participant_id"', b"private-11", b"private-22",
    ):
        assert forbidden not in persisted_responses
    assert all(item["persisted_content_type"] == "json" for item in manifest["responses"])
    assert all(item["source_sha256"] for item in manifest["responses"])
    loaded, schema_registry = schemas.load_schemas(ROOT / "schemas")
    assert schemas.validate_instance(manifest, loaded["melee-raw-archive.schema.json"], schema_registry) == []

    parsed = parse_raw_snapshot(result.archive_path)
    assert parsed.archive_schema_version == "3.0.0"
    assert parsed.participant_identity_scheme == "hmac-sha256-event-v1"
    assert parsed.participant_key_id == TEST_HMAC_KEY_ID
    assert sum(len(page.standings) for page in parsed.pages) == 2
    assert sum(len(page.matches) for page in parsed.pages) == 1
    assert sum(len(page.decklists) for page in parsed.pages) == 2
    normalized = normalize_parsed_snapshot(
        parsed, registry().events[0], normalized_at="2026-07-21T12:01:00Z"
    )
    assert normalized["quality"]["status"] == "valid"
    assert normalized["matches"][0]["constructed_statistics_eligible"] is False
    assert all(
        item["id"] == item["source_id"]
        and item["id"].startswith("melee-v3-")
        for item in normalized["participants"]
    )

    manifest["responses"][0].pop("method")
    assert schemas.validate_instance(
        manifest, loaded["melee-raw-archive.schema.json"], schema_registry
    )
    (result.archive_path / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    with pytest.raises(MeleeSourceParseError, match="invalid v3 fields"):
        parse_raw_snapshot(result.archive_path)


def test_complete_collection_resumes_verified_responses_and_matches_uninterrupted_bytes(tmp_path):
    guid_one = "11111111-1111-1111-1111-111111111111"
    guid_two = "22222222-2222-2222-2222-222222222222"
    html = b"""<html><head><title>Fixture Pro Tour | Melee</title></head><body>
    <button class='round-selector' data-id='101' data-name='Round 1' data-is-completed='True'></button>
    </body></html>"""

    def player(participant_id, name):
        return {"StatusDescription": "Active", "Players": [{"ID": participant_id, "DisplayName": name}]}

    standings = {
        "recordsTotal": 2,
        "data": [
            {"ID": 1, "Rank": 1, "Points": 3, "Team": player(11, "Alpha"),
             "Decklists": [{"DecklistId": guid_one, "PlayerId": 11}]},
            {"ID": 2, "Rank": 2, "Points": 0, "Team": player(22, "Beta"),
             "Decklists": [{"DecklistId": guid_two, "PlayerId": 22}]},
        ],
    }
    matches = {
        "recordsTotal": 1,
        "data": [{
            "Guid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "RoundId": 101,
            "HasResult": True, "ResultString": "2-0-0", "TableNumber": 1,
            "ByeReasonDescription": None, "LossReasonDescription": None,
            "Competitors": [
                {"Team": player(11, "Alpha"), "GameWins": 2, "GameByes": 0},
                {"Team": player(22, "Beta"), "GameWins": 0, "GameByes": 0},
            ],
        }],
    }
    failed_url = f"https://melee.gg/Decklist/GetDecklistDetails?id={guid_two}"

    def payload(method, url):
        if url.endswith("/Tournament/View/434455"):
            return html, "text/html"
        if url.endswith("/Standing/GetRoundStandings"):
            value = standings
        elif "/Match/GetRoundMatches/101" in url:
            value = matches
        else:
            decklist_id = url.rsplit("=", 1)[-1]
            value = {
                "Guid": decklist_id,
                "FormatName": "Modern",
                "Records": [{"c": 0, "n": "Fixture Card", "q": 4}],
            }
        return json.dumps(value, sort_keys=True).encode(), "application/json"

    first_calls = []

    def interrupted_send(method, url, **_kwargs):
        first_calls.append(url)
        if url == failed_url:
            return Response(status_code=500, url=url)
        content, content_type = payload(method, url)
        return Response(content=content, url=url, headers={"Content-Type": content_type})

    progress = []
    interrupted_root = tmp_path / "interrupted"
    with pytest.raises(MeleeFetchError, match="after 1 attempts"):
        fetch_complete_event(
            "434455", registry(), interrupted_root,
            request_send=interrupted_send, sleep=lambda _seconds: None,
            now=fixed_now, attempts=1, request_delay=0, progress=progress.append,
            **privacy_options(),
        )
    event_root = interrupted_root / "melee" / "434455"
    partial = event_root / melee_client.COMPLETE_PARTIAL_DIRECTORY
    checkpoint = event_root / melee_client.COMPLETE_CHECKPOINT_FILE
    assert partial.is_dir()
    assert checkpoint.is_file()
    assert not (partial / "manifest.json").exists()
    incomplete_bytes = checkpoint.read_bytes() + b"".join(
        path.read_bytes() for path in partial.iterdir()
    )
    for forbidden in (
        b'"PlayerId"', b'"source_participant_id"', b'"Players"',
        TEST_HMAC_KEY,
    ):
        assert forbidden not in incomplete_bytes
    with pytest.raises(MeleeSourceParseError, match="manifest"):
        parse_raw_snapshot(partial)
    with pytest.raises(MeleeRetentionError, match="snapshot"):
        retain_normalized_event(
            registry().events[0],
            partial,
            raw_root=interrupted_root,
            data_root=tmp_path / "normalized",
        )

    resumed_calls = []

    def resumed_send(method, url, **_kwargs):
        resumed_calls.append(url)
        content, content_type = payload(method, url)
        return Response(content=content, url=url, headers={"Content-Type": content_type})

    resumed = fetch_complete_event(
        "434455", registry(), interrupted_root,
        request_send=resumed_send, sleep=lambda _seconds: None,
        now=lambda: datetime(2026, 7, 22, 12, 0, tzinfo=UTC),
        attempts=1, request_delay=0, progress=progress.append,
        **privacy_options(),
    )
    assert resumed_calls == [failed_url]
    assert resumed.resumed_responses == 4
    assert resumed.planned_responses == 5
    assert progress[-1]["stage"] == "complete"
    assert not partial.exists()
    assert not checkpoint.exists()

    uninterrupted_root = tmp_path / "uninterrupted"
    uninterrupted = fetch_complete_event(
        "434455", registry(), uninterrupted_root,
        request_send=resumed_send, sleep=lambda _seconds: None,
        now=fixed_now, attempts=1, request_delay=0,
        **privacy_options(),
    )
    resumed_files = {
        path.name: path.read_bytes()
        for path in resumed.archive_path.iterdir()
    }
    uninterrupted_files = {
        path.name: path.read_bytes()
        for path in uninterrupted.archive_path.iterdir()
    }
    assert resumed.archive_path.name == uninterrupted.archive_path.name
    assert resumed_files == uninterrupted_files


def test_complete_request_budget_supports_three_thousand_players_with_hard_ceiling():
    budget = melee_client.complete_request_budget(
        standings_total=3_000,
        round_match_totals=(1_500,) * 16,
        decklist_count=3_000,
    )
    assert budget == 4_081
    assert budget < melee_client.MAX_COMPLETE_ARCHIVE_RESPONSES
    assert melee_client.MAX_COMPLETE_EVENT_DECKLISTS >= 3_000
    loaded, _schema_registry = schemas.load_schemas(ROOT / "schemas")
    assert (
        loaded["melee-raw-archive.schema.json"]["properties"]["responses"]["maxItems"]
        == melee_client.MAX_COMPLETE_ARCHIVE_RESPONSES
    )
    with pytest.raises(MeleeRequestBoundaryError, match="decklists"):
        melee_client.complete_request_budget(
            standings_total=melee_client.MAX_COMPLETE_EVENT_DECKLISTS + 1,
            round_match_totals=(1,),
            decklist_count=melee_client.MAX_COMPLETE_EVENT_DECKLISTS + 1,
        )
