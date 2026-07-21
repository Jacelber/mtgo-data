"""Bounded raw-response collection for explicitly approved Melee events.

This module deliberately preserves source responses and performs no parsing,
classification, statistics generation, or publication.  A caller must provide
a validated registry; disabled events fail before either network or filesystem
side effects occur.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil
import time
from typing import Any, Callable, Iterator, Mapping
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

from .config import MeleeEventRegistry, MeleeRawRequestDefinition


RAW_ARCHIVE_SCHEMA_VERSION = "1.0.0"
MELEE_HOST = "melee.gg"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_ATTEMPTS = 3
DEFAULT_RETRY_DELAY_SECONDS = 2.0
DEFAULT_REQUEST_DELAY_SECONDS = 1.0
MAX_RESPONSE_BYTES = 32 * 1024 * 1024
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_ARCHIVE_RESPONSES = 500
STREAM_CHUNK_BYTES = 64 * 1024
RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})
DEFAULT_HEADERS = {
    "Accept": "application/json, text/html;q=0.9",
    "User-Agent": "mtgo-data-melee-raw-archive/0.1",
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
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
                "responses": [asdict(record) for record in records],
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


__all__ = [
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
    "fetch_raw_event",
    "planned_request_urls",
]
