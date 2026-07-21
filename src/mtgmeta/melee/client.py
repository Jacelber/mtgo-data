"""Bounded raw-response collection for explicitly approved Melee events.

This module deliberately preserves source responses and performs only the
structural parsing required to discover completed rounds, pagination, and
referenced decklists. It performs no semantic normalization, classification,
statistics generation, or publication. A caller must provide a validated
registry; disabled events fail before either network or filesystem side effects
occur.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import shutil
import time
from typing import Any, Callable, Iterator, Mapping
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

from .config import MeleeEventRegistry, MeleeRawRequestDefinition


RAW_ARCHIVE_SCHEMA_VERSION = "1.0.0"
COMPLETE_RAW_ARCHIVE_SCHEMA_VERSION = "2.0.0"
MELEE_HOST = "melee.gg"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_ATTEMPTS = 3
DEFAULT_RETRY_DELAY_SECONDS = 2.0
DEFAULT_REQUEST_DELAY_SECONDS = 1.0
DEFAULT_COMPLETE_REQUEST_DELAY_SECONDS = 0.3
DATATABLES_PAGE_SIZE = 25
MAX_EVENT_ROUNDS = 32
MAX_EVENT_DECKLISTS = 500
MAX_RESPONSE_BYTES = 32 * 1024 * 1024
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_ARCHIVE_RESPONSES = 500
STREAM_CHUNK_BYTES = 64 * 1024
RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})
DEFAULT_HEADERS = {
    "Accept": "application/json, text/html;q=0.9",
    "User-Agent": "mtgo-data-melee-raw-archive/0.1",
}
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) "
    "Gecko/20100101 Firefox/130.0"
)
HTML_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": BROWSER_USER_AGENT,
}
API_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "User-Agent": BROWSER_USER_AGENT,
    "X-Requested-With": "XMLHttpRequest",
}
POST_HEADERS = {
    **API_HEADERS,
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}


class MeleeFetchError(RuntimeError):
    """Raised when an approved raw response cannot be collected safely."""


class MeleeRequestBoundaryError(MeleeFetchError):
    """Raised when a request would leave the approved Melee boundary."""


class MeleeArchiveError(MeleeFetchError):
    """Raised when a raw archive cannot be written atomically."""


@dataclass(frozen=True)
class RawResponseRecord:
    request_id: str
    resource_type: str
    page: int
    url: str
    path: str
    expected_content_type: str
    response_content_type: str | None
    etag: str | None
    last_modified: str | None
    status_code: int
    attempts: int
    sha256: str
    bytes: int
    method: str | None = None
    request_body_sha256: str | None = None
    source_round_id: str | None = None
    source_participant_id: str | None = None
    source_decklist_id: str | None = None


@dataclass(frozen=True)
class MeleeRawFetchResult:
    event_id: str
    dry_run: bool
    archive_path: Path | None
    planned_urls: tuple[str, ...]
    responses: tuple[RawResponseRecord, ...]


def _require_melee_url(url: str, event_id: str, resource_type: str) -> None:
    parsed = urlparse(url)
    unsafe_url = (
        parsed.scheme != "https"
        or parsed.hostname != MELEE_HOST
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
        or bool(parsed.fragment)
    )
    tournament_path = parsed.path == f"/Tournament/View/{event_id}"
    decklist_path = parsed.path.startswith("/Decklist/View/") and parsed.path.removeprefix("/Decklist/View/").isdigit()
    if unsafe_url or (resource_type == "tournament" and not tournament_path) or (resource_type == "decklist" and not decklist_path):
        raise MeleeRequestBoundaryError(f"raw request is outside the approved Melee event boundary: {url!r}")


def _page_urls(request: MeleeRawRequestDefinition, event_id: str) -> tuple[tuple[int, str], ...]:
    _require_melee_url(request.url, event_id, request.resource_type)
    if request.page_parameter is None:
        return ((1, request.url),)
    assert request.start_page is not None and request.max_pages is not None
    parsed = urlparse(request.url)
    base_query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key != request.page_parameter]
    urls: list[tuple[int, str]] = []
    for page in range(request.start_page, request.start_page + request.max_pages):
        query = urlencode([*base_query, (request.page_parameter, str(page))])
        url = urlunparse(parsed._replace(query=query))
        _require_melee_url(url, event_id, request.resource_type)
        urls.append((page, url))
    return tuple(urls)


def planned_request_urls(event_id: str, registry: MeleeEventRegistry) -> tuple[str, ...]:
    """Return the exact approved request URLs without network or file access."""

    event = registry.require_fetchable(event_id)
    urls = tuple(url for request in event.raw_requests for _page, url in _page_urls(request, event.id))
    if len(urls) > MAX_ARCHIVE_RESPONSES:
        raise MeleeRequestBoundaryError(f"raw request plan exceeds {MAX_ARCHIVE_RESPONSES} responses")
    return urls


def _close_response(response: Any) -> None:
    close = getattr(response, "close", None)
    if callable(close):
        close()


def _iter_response_content(response: Any) -> Iterator[bytes]:
    iterate = getattr(response, "iter_content", None)
    if callable(iterate):
        for chunk in iterate(chunk_size=STREAM_CHUNK_BYTES):
            if chunk:
                yield bytes(chunk)
        return
    content = getattr(response, "content", None)
    if isinstance(content, (bytes, bytearray)):
        yield bytes(content)
        return
    text = getattr(response, "text", None)
    if isinstance(text, str):
        yield text.encode("utf-8")
        return
    raise MeleeFetchError("Melee response did not provide a readable body")


def _response_headers(response: Any) -> dict[str, str | None]:
    headers = getattr(response, "headers", {})
    if not isinstance(headers, Mapping):
        headers = {}
    normalized = {str(key).lower(): str(value) for key, value in headers.items()}
    return {
        "response_content_type": normalized.get("content-type"),
        "etag": normalized.get("etag"),
        "last_modified": normalized.get("last-modified"),
    }


def _write_response(path: Path, response: Any, archive_bytes: int) -> tuple[int, str]:
    headers = getattr(response, "headers", {})
    content_length = headers.get("Content-Length") if isinstance(headers, Mapping) else None
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except (TypeError, ValueError):
            declared_length = -1
        if declared_length > MAX_RESPONSE_BYTES or archive_bytes + declared_length > MAX_ARCHIVE_BYTES:
            raise MeleeArchiveError("Melee response exceeds the configured raw archive size limit")
    digest = hashlib.sha256()
    written = 0
    try:
        with path.open("xb") as handle:
            for chunk in _iter_response_content(response):
                written += len(chunk)
                if written > MAX_RESPONSE_BYTES or archive_bytes + written > MAX_ARCHIVE_BYTES:
                    raise MeleeArchiveError("Melee response exceeds the configured raw archive size limit")
                digest.update(chunk)
                handle.write(chunk)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return written, digest.hexdigest()


def _download(
    url: str,
    *,
    request_get: Callable[..., Any],
    sleep: Callable[[float], None],
    attempts: int,
    timeout: int,
    retry_delay: float,
) -> tuple[Any, int]:
    if attempts < 1:
        raise ValueError("attempts must be at least one")
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = request_get(url, headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=False, stream=True)
            response_url = getattr(response, "url", url)
            if response_url != url or bool(getattr(response, "is_redirect", False)):
                raise MeleeRequestBoundaryError(f"redirects are not allowed for raw Melee collection: {url!r}")
            status_code = getattr(response, "status_code", None)
            if not isinstance(status_code, int):
                raise MeleeFetchError("Melee response did not provide an integer status code")
            if 200 <= status_code < 300:
                return response, attempt
            error = MeleeFetchError(f"Melee request returned HTTP {status_code} for {url!r}")
            if status_code not in RETRYABLE_STATUS_CODES:
                _close_response(response)
                raise error
            last_error = error
            _close_response(response)
        except MeleeRequestBoundaryError:
            raise
        except MeleeFetchError:
            raise
        except Exception as exc:
            last_error = exc
        if attempt < attempts and retry_delay:
            sleep(retry_delay)
    raise MeleeFetchError(f"failed to download {url!r} after {attempts} attempts") from last_error


def _next_snapshot_path(raw_root: Path, event_id: str, timestamp: datetime) -> Path:
    event_root = raw_root / "melee" / event_id
    base = timestamp.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    for suffix in range(1, 10_000):
        candidate = event_root / f"{base}-{suffix:02d}"
        if not candidate.exists() and not (event_root / f".{candidate.name}.tmp").exists():
            return candidate
    raise MeleeArchiveError(f"could not allocate a new raw archive snapshot for event {event_id!r}")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def fetch_raw_event(
    event_id: str,
    registry: MeleeEventRegistry,
    raw_root: str | Path,
    *,
    dry_run: bool = False,
    request_get: Callable[..., Any] | None = None,
    sleep: Callable[[float], None] | None = None,
    now: Callable[[], datetime] | None = None,
    attempts: int = DEFAULT_ATTEMPTS,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    retry_delay: float = DEFAULT_RETRY_DELAY_SECONDS,
    request_delay: float = DEFAULT_REQUEST_DELAY_SECONDS,
) -> MeleeRawFetchResult:
    """Fetch only the approved raw request plan into one new immutable snapshot.

    Disabled and unknown events fail before inspecting ``raw_root`` or selecting
    a transport.  No existing snapshot is overwritten; an interrupted fetch
    removes its temporary directory before raising.
    """

    event = registry.require_fetchable(event_id)
    plan = tuple((request, page, url) for request in event.raw_requests for page, url in _page_urls(request, event.id))
    if len(plan) > MAX_ARCHIVE_RESPONSES:
        raise MeleeRequestBoundaryError(f"raw request plan exceeds {MAX_ARCHIVE_RESPONSES} responses")
    planned_urls = tuple(url for _request, _page, url in plan)
    if dry_run:
        return MeleeRawFetchResult(event.id, True, None, planned_urls, ())

    if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 1:
        raise ValueError("attempts must be a positive integer")
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout < 1:
        raise ValueError("timeout must be a positive integer")
    if retry_delay < 0 or request_delay < 0:
        raise ValueError("request delays must be non-negative")
    request = request_get or requests.get
    wait = sleep or time.sleep
    timestamp = (now or (lambda: datetime.now(UTC)))()
    if timestamp.tzinfo is None:
        raise ValueError("now must return a timezone-aware datetime")
    destination = _next_snapshot_path(Path(raw_root), event.id, timestamp)
    temporary = destination.parent / f".{destination.name}.tmp"
    records: list[RawResponseRecord] = []
    archive_bytes = 0
    try:
        temporary.mkdir(parents=True, exist_ok=False)
        for index, (definition, page, url) in enumerate(plan):
            if index and request_delay:
                wait(request_delay)
            response, request_attempts = _download(
                url,
                request_get=request,
                sleep=wait,
                attempts=attempts,
                timeout=timeout,
                retry_delay=retry_delay,
            )
            extension = "html" if definition.content_type == "html" else "json"
            relative_path = f"{definition.id}-{page:03d}.{extension}"
            response_path = temporary / relative_path
            try:
                response_bytes, response_sha256 = _write_response(response_path, response, archive_bytes)
            finally:
                _close_response(response)
            archive_bytes += response_bytes
            metadata = _response_headers(response)
            records.append(
                RawResponseRecord(
                    request_id=definition.id,
                    resource_type=definition.resource_type,
                    page=page,
                    url=url,
                    path=relative_path,
                    expected_content_type=definition.content_type,
                    response_content_type=metadata["response_content_type"],
                    etag=metadata["etag"],
                    last_modified=metadata["last_modified"],
                    status_code=response.status_code,
                    attempts=request_attempts,
                    sha256=response_sha256,
                    bytes=response_bytes,
                )
            )
        _write_json(
            temporary / "manifest.json",
            {
                "schema_version": RAW_ARCHIVE_SCHEMA_VERSION,
                "source": "melee",
                "event_id": event.id,
                "event_url": event.url,
                "fetched_at": timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                "responses": [
                    {key: value for key, value in asdict(record).items() if key in {
                        "request_id", "resource_type", "page", "url", "path",
                        "expected_content_type", "response_content_type", "etag",
                        "last_modified", "status_code", "attempts", "sha256", "bytes",
                    }}
                    for record in records
                ],
            },
        )
        temporary.replace(destination)
    except Exception as exc:
        shutil.rmtree(temporary, ignore_errors=True)
        for directory in (temporary.parent, temporary.parent.parent):
            try:
                directory.rmdir()
            except OSError:
                pass
        if isinstance(exc, MeleeFetchError):
            raise
        raise MeleeArchiveError(f"could not create raw archive for event {event.id!r}") from exc
    return MeleeRawFetchResult(event.id, False, destination, planned_urls, tuple(records))


class _CompletedRoundCollector(HTMLParser):
    """Collect completed round-selector buttons without depending on a DOM package."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rounds: dict[str, tuple[str, bool]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "button":
            return
        values = {key.casefold(): value for key, value in attrs}
        classes = set((values.get("class") or "").split())
        if "round-selector" not in classes:
            return
        round_id = values.get("data-id") or ""
        if not round_id.isdigit():
            return
        label = (values.get("data-name") or "").strip()
        if not label:
            return
        completed = (values.get("data-is-completed") or "").casefold() == "true"
        previous = self.rounds.get(round_id)
        self.rounds[round_id] = (label, completed or bool(previous and previous[1]))


def _completed_rounds(body: bytes) -> tuple[tuple[str, str], ...]:
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise MeleeFetchError("tournament page is not valid UTF-8") from exc
    collector = _CompletedRoundCollector()
    collector.feed(text)
    collector.close()
    rounds = tuple(
        (round_id, label)
        for round_id, (label, completed) in collector.rounds.items()
        if completed
    )
    if not rounds:
        raise MeleeFetchError("tournament page did not expose any completed rounds")
    if len(rounds) > MAX_EVENT_ROUNDS:
        raise MeleeRequestBoundaryError(f"tournament exposes more than {MAX_EVENT_ROUNDS} completed rounds")
    return rounds


def _datatables_body(columns: tuple[str, ...], start: int, *, round_id: str | None = None) -> bytes:
    values: list[tuple[str, str]] = [("draw", "1")]
    for index, column in enumerate(columns):
        values.extend(
            (
                (f"columns[{index}][data]", column),
                (f"columns[{index}][name]", column),
                (f"columns[{index}][searchable]", "true" if column in {"Rank", "Points", "TableNumber"} else "false"),
                (f"columns[{index}][orderable]", "true" if column not in {"Player", "Result"} else "false"),
                (f"columns[{index}][search][value]", ""),
                (f"columns[{index}][search][regex]", "false"),
            )
        )
    values.extend(
        (
            ("order[0][column]", "0"),
            ("order[0][dir]", "asc"),
            ("start", str(start)),
            ("length", str(DATATABLES_PAGE_SIZE)),
            ("search[value]", ""),
            ("search[regex]", "false"),
        )
    )
    if round_id is not None:
        values.append(("roundId", round_id))
    return urlencode(values).encode("ascii")


STANDINGS_COLUMNS = (
    "Rank", "Player", "Decklists", "MatchRecord", "GameRecord", "Points",
    "OpponentMatchWinPercentage", "TeamGameWinPercentage",
    "OpponentGameWinPercentage", "FinalTiebreaker", "OpponentCount",
)
MATCH_COLUMNS = (
    "TableNumber", "Player1", "Player1Decklist", "Player2",
    "Player2Decklist", "Result",
)


def _require_complete_url(url: str, event_id: str, resource_type: str, source_id: str | None) -> None:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https" or parsed.hostname != MELEE_HOST or parsed.port is not None
        or parsed.username is not None or parsed.password is not None or parsed.fragment
    ):
        raise MeleeRequestBoundaryError(f"complete request is outside melee.gg: {url!r}")
    if resource_type == "tournament":
        valid = parsed.path == f"/Tournament/View/{event_id}" and not parsed.query
    elif resource_type == "standings":
        valid = parsed.path == "/Standing/GetRoundStandings" and not parsed.query and bool(source_id and source_id.isdigit())
    elif resource_type == "matches":
        valid = parsed.path == f"/Match/GetRoundMatches/{source_id}" and not parsed.query and bool(source_id and source_id.isdigit())
    elif resource_type == "decklist":
        valid = parsed.path == "/Decklist/GetDecklistDetails" and parse_qsl(parsed.query) == [("id", source_id or "")]
    else:
        valid = False
    if not valid:
        raise MeleeRequestBoundaryError(f"complete request is outside the approved event resource boundary: {url!r}")


def _json_mapping(body: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MeleeFetchError(f"{label} did not return valid JSON") from exc
    if not isinstance(value, dict):
        raise MeleeFetchError(f"{label} JSON must be a mapping")
    return value


def _send_request(
    method: str,
    url: str,
    *,
    headers: Mapping[str, str],
    body: bytes | None,
    request_send: Callable[..., Any],
    sleep: Callable[[float], None],
    attempts: int,
    timeout: int,
    retry_delay: float,
) -> tuple[Any, int]:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = request_send(
                method, url, headers=dict(headers), data=body, timeout=timeout,
                allow_redirects=False, stream=True,
            )
            response_url = getattr(response, "url", url) or url
            if response_url != url or bool(getattr(response, "is_redirect", False)):
                _close_response(response)
                raise MeleeRequestBoundaryError(f"redirects are not allowed for raw Melee collection: {url!r}")
            status_code = getattr(response, "status_code", None)
            if not isinstance(status_code, int):
                raise MeleeFetchError("Melee response did not provide an integer status code")
            if 200 <= status_code < 300:
                return response, attempt
            error = MeleeFetchError(f"Melee request returned HTTP {status_code} for {url!r}")
            _close_response(response)
            if status_code not in RETRYABLE_STATUS_CODES:
                raise error
            last_error = error
        except (MeleeRequestBoundaryError, MeleeFetchError):
            raise
        except Exception as exc:
            last_error = exc
        if attempt < attempts and retry_delay:
            sleep(retry_delay)
    raise MeleeFetchError(f"failed to download {url!r} after {attempts} attempts") from last_error


def fetch_complete_event(
    event_id: str,
    registry: MeleeEventRegistry,
    raw_root: str | Path,
    *,
    request_send: Callable[..., Any] | None = None,
    sleep: Callable[[float], None] | None = None,
    now: Callable[[], datetime] | None = None,
    attempts: int = DEFAULT_ATTEMPTS,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    retry_delay: float = DEFAULT_RETRY_DELAY_SECONDS,
    request_delay: float = DEFAULT_COMPLETE_REQUEST_DELAY_SECONDS,
) -> MeleeRawFetchResult:
    """Collect one complete whitelisted event through bounded public endpoints."""

    event = registry.require_fetchable(event_id)
    tournament_requests = [item for item in event.raw_requests if item.resource_type == "tournament"]
    if len(tournament_requests) != 1:
        raise MeleeRequestBoundaryError("complete collection requires exactly one configured tournament request")
    if not all(isinstance(value, int) and not isinstance(value, bool) and value >= 1 for value in (attempts, timeout)):
        raise ValueError("attempts and timeout must be positive integers")
    if retry_delay < 0 or request_delay < 0:
        raise ValueError("request delays must be non-negative")
    send = request_send or requests.request
    wait = sleep or time.sleep
    timestamp = (now or (lambda: datetime.now(UTC)))()
    if timestamp.tzinfo is None:
        raise ValueError("now must return a timezone-aware datetime")
    destination = _next_snapshot_path(Path(raw_root), event.id, timestamp)
    temporary = destination.parent / f".{destination.name}.tmp"
    records: list[RawResponseRecord] = []
    planned_urls: list[str] = []
    archive_bytes = 0
    request_count = 0

    def collect(
        *, request_id: str, resource_type: str, page: int, url: str,
        relative_path: str, method: str, headers: Mapping[str, str], body: bytes | None = None,
        source_round_id: str | None = None, source_participant_id: str | None = None,
        source_decklist_id: str | None = None,
    ) -> bytes:
        nonlocal archive_bytes, request_count
        source_id = source_round_id if resource_type in {"standings", "matches"} else source_decklist_id
        _require_complete_url(url, event.id, resource_type, source_id)
        request_count += 1
        if request_count > MAX_ARCHIVE_RESPONSES:
            raise MeleeRequestBoundaryError(f"complete event exceeds {MAX_ARCHIVE_RESPONSES} responses")
        if request_count > 1 and request_delay:
            wait(request_delay)
        response, used_attempts = _send_request(
            method, url, headers=headers, body=body, request_send=send, sleep=wait,
            attempts=attempts, timeout=timeout, retry_delay=retry_delay,
        )
        response_path = temporary / relative_path
        try:
            response_bytes, response_sha256 = _write_response(response_path, response, archive_bytes)
        finally:
            _close_response(response)
        archive_bytes += response_bytes
        metadata = _response_headers(response)
        records.append(RawResponseRecord(
            request_id=request_id, resource_type=resource_type, page=page, url=url,
            path=relative_path, expected_content_type="html" if relative_path.endswith(".html") else "json",
            response_content_type=metadata["response_content_type"], etag=metadata["etag"],
            last_modified=metadata["last_modified"], status_code=response.status_code,
            attempts=used_attempts, sha256=response_sha256, bytes=response_bytes,
            method=method, request_body_sha256=hashlib.sha256(body).hexdigest() if body is not None else None,
            source_round_id=source_round_id, source_participant_id=source_participant_id,
            source_decklist_id=source_decklist_id,
        ))
        planned_urls.append(url)
        return response_path.read_bytes()

    try:
        temporary.mkdir(parents=True, exist_ok=False)
        tournament_url = tournament_requests[0].url
        tournament_body = collect(
            request_id="tournament", resource_type="tournament", page=1,
            url=tournament_url, relative_path="tournament-001.html", method="GET", headers=HTML_HEADERS,
        )
        rounds = _completed_rounds(tournament_body)
        numeric_rounds = [(round_id, int(match.group(1))) for round_id, label in rounds if (match := re.fullmatch(r"Round\s+(\d+)", label, re.IGNORECASE))]
        if not numeric_rounds:
            raise MeleeFetchError("tournament page did not expose a completed Swiss round")
        standings_round_id = max(numeric_rounds, key=lambda item: item[1])[0]

        decklists: dict[str, str] = {}
        start = 0
        page = 1
        total: int | None = None
        while total is None or start < total:
            body = _datatables_body(STANDINGS_COLUMNS, start, round_id=standings_round_id)
            payload_body = collect(
                request_id="standings", resource_type="standings", page=page,
                url="https://melee.gg/Standing/GetRoundStandings",
                relative_path=f"standings-{standings_round_id}-{page:03d}.json", method="POST",
                headers=POST_HEADERS, body=body, source_round_id=standings_round_id,
            )
            payload = _json_mapping(payload_body, "standings")
            rows = payload.get("data")
            reported_total = payload.get("recordsTotal")
            if not isinstance(rows, list) or not isinstance(reported_total, int) or reported_total < 0 or reported_total > MAX_EVENT_DECKLISTS:
                raise MeleeFetchError("standings returned invalid or excessive pagination metadata")
            if total is not None and reported_total != total:
                raise MeleeFetchError("standings total changed during pagination")
            total = reported_total
            for row in rows:
                if not isinstance(row, dict):
                    raise MeleeFetchError("standings row must be a mapping")
                for reference in row.get("Decklists") or []:
                    if not isinstance(reference, dict):
                        raise MeleeFetchError("decklist reference must be a mapping")
                    decklist_id = str(reference.get("DecklistId") or "")
                    participant_id = str(reference.get("PlayerId") or "")
                    if not re.fullmatch(r"[0-9a-fA-F-]{32,36}", decklist_id) or not participant_id.isdigit():
                        raise MeleeFetchError("standings exposed an invalid decklist identity")
                    previous = decklists.setdefault(decklist_id, participant_id)
                    if previous != participant_id:
                        raise MeleeFetchError("decklist identity maps to multiple participants")
            if not rows or start + DATATABLES_PAGE_SIZE >= total:
                break
            start += DATATABLES_PAGE_SIZE
            page += 1

        for round_id, _label in rounds:
            start = 0
            page = 1
            total = None
            while total is None or start < total:
                body = _datatables_body(MATCH_COLUMNS, start)
                url = f"https://melee.gg/Match/GetRoundMatches/{round_id}"
                payload_body = collect(
                    request_id="matches", resource_type="matches", page=page, url=url,
                    relative_path=f"matches-{round_id}-{page:03d}.json", method="POST",
                    headers=POST_HEADERS, body=body, source_round_id=round_id,
                )
                payload = _json_mapping(payload_body, "matches")
                rows = payload.get("data")
                reported_total = payload.get("recordsTotal")
                if not isinstance(rows, list) or not isinstance(reported_total, int) or reported_total < 0 or reported_total > 2_000:
                    raise MeleeFetchError("matches returned invalid or excessive pagination metadata")
                if total is not None and reported_total != total:
                    raise MeleeFetchError("match total changed during pagination")
                total = reported_total
                if not rows or start + DATATABLES_PAGE_SIZE >= total:
                    break
                start += DATATABLES_PAGE_SIZE
                page += 1

        if len(decklists) > MAX_EVENT_DECKLISTS:
            raise MeleeRequestBoundaryError(f"event exposes more than {MAX_EVENT_DECKLISTS} decklists")
        for page, (decklist_id, participant_id) in enumerate(sorted(decklists.items()), 1):
            url = "https://melee.gg/Decklist/GetDecklistDetails?" + urlencode({"id": decklist_id})
            collect(
                request_id="decklist", resource_type="decklist", page=page, url=url,
                relative_path=f"decklist-{decklist_id.casefold()}.json", method="GET", headers=API_HEADERS,
                source_participant_id=participant_id, source_decklist_id=decklist_id,
            )
        _write_json(temporary / "manifest.json", {
            "schema_version": COMPLETE_RAW_ARCHIVE_SCHEMA_VERSION, "source": "melee",
            "event_id": event.id, "event_url": event.url,
            "fetched_at": timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "responses": [asdict(record) for record in records],
        })
        temporary.replace(destination)
    except Exception as exc:
        shutil.rmtree(temporary, ignore_errors=True)
        for directory in (temporary.parent, temporary.parent.parent):
            try:
                directory.rmdir()
            except OSError:
                pass
        if isinstance(exc, MeleeFetchError):
            raise
        raise MeleeArchiveError(f"could not create complete raw archive for event {event.id!r}") from exc
    return MeleeRawFetchResult(event.id, False, destination, tuple(planned_urls), tuple(records))


__all__ = [
    "API_HEADERS",
    "COMPLETE_RAW_ARCHIVE_SCHEMA_VERSION",
    "DEFAULT_ATTEMPTS",
    "DEFAULT_HEADERS",
    "DEFAULT_REQUEST_DELAY_SECONDS",
    "DEFAULT_RETRY_DELAY_SECONDS",
    "DEFAULT_TIMEOUT_SECONDS",
    "MAX_ARCHIVE_BYTES",
    "MAX_ARCHIVE_RESPONSES",
    "MAX_RESPONSE_BYTES",
    "MeleeArchiveError",
    "MeleeFetchError",
    "MeleeRawFetchResult",
    "MeleeRequestBoundaryError",
    "RAW_ARCHIVE_SCHEMA_VERSION",
    "RawResponseRecord",
    "fetch_complete_event",
    "fetch_raw_event",
    "planned_request_urls",
]
