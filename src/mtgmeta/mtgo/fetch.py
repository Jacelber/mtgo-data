"""Network, discovery, parsing, and storage helpers for MTGO events."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import re
import time
from typing import Any, Callable, Iterable
from urllib.parse import urlparse

import requests

from . import load_mtgo_context, load_mtgo_event_collection_context
from .normalize import normalize_event


MTGO_BASE_URL = "https://www.mtgo.com"
DECKLIST_MARKER = "window.MTGO.decklists.data ="
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
REQUIRED_EVENT_FIELDS = frozenset({"event_id", "description", "player_count", "decklists"})


class MTGOFetchError(RuntimeError):
    """Raised after an MTGO page cannot be downloaded within the retry policy."""


class MTGOParseError(RuntimeError):
    """Raised when an MTGO page does not contain one complete event payload."""


class MTGOStorageError(RuntimeError):
    """Raised when an event filename or output operation is unsafe."""


def download_page(
    url: str,
    *,
    attempts: int = 5,
    timeout: int = 90,
    retry_delay: float = 5,
    request_get: Callable[..., Any] | None = None,
    sleep: Callable[[float], None] | None = None,
    on_attempt: Callable[[int, int], None] | None = None,
    on_error: Callable[[int, int, Exception], None] | None = None,
) -> str:
    if attempts < 1:
        raise ValueError("attempts must be at least one")
    request = request_get or requests.get
    wait = sleep or time.sleep
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        if on_attempt is not None:
            on_attempt(attempt, attempts)
        try:
            response = request(url, headers=DEFAULT_HEADERS, timeout=timeout)
            response.raise_for_status()
            return response.text
        except Exception as exc:  # Preserve legacy retry behavior across request adapters.
            last_error = exc
            if on_error is not None:
                on_error(attempt, attempts, exc)
            if retry_delay and attempt < attempts:
                wait(retry_delay)
    raise MTGOFetchError(f"failed to download {url!r} after {attempts} attempts") from last_error


def extract_event_data(html: str) -> dict[str, Any]:
    start = html.find(DECKLIST_MARKER)
    if start == -1:
        raise MTGOParseError("MTGO decklist marker was not found")
    brace_start = html.find("{", start + len(DECKLIST_MARKER))
    if brace_start == -1:
        raise MTGOParseError("MTGO event JSON did not start")
    depth = 0
    in_string = False
    escaped = False
    for index in range(brace_start, len(html)):
        character = html[index]
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
        else:
            if character == '"':
                in_string = True
            elif character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
                if depth == 0:
                    try:
                        value = json.loads(html[brace_start:index + 1])
                    except json.JSONDecodeError as exc:
                        raise MTGOParseError(f"MTGO event JSON is invalid: {exc.msg}") from exc
                    if not isinstance(value, dict):
                        raise MTGOParseError("MTGO event JSON must be an object")
                    return value
    raise MTGOParseError("MTGO event JSON did not end")


def is_event_data_complete(data: Any) -> bool:
    return (
        isinstance(data, dict)
        and REQUIRED_EVENT_FIELDS <= set(data)
        and isinstance(data.get("decklists"), list)
        and bool(data["decklists"])
    )


def parse_event_link(link: str, recognized_format_ids: Iterable[str]) -> tuple[str, str | None]:
    path = urlparse(link).path
    name = path.removeprefix("/decklist/")
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", name)
    first_word = name.split("-", 1)[0].lower()
    recognized = frozenset(recognized_format_ids)
    return (first_word if first_word in recognized else "other", date_match.group(1) if date_match else None)


def discover_event_links(html: str, recognized_format_ids: Iterable[str]) -> list[str]:
    format_ids = tuple(recognized_format_ids)
    links = sorted(set(re.findall(r"/decklist/[a-zA-Z0-9\-]+", html)))
    candidates: list[str] = []
    for link in links:
        if "league" in link.lower():
            continue
        format_id, date = parse_event_link(link, format_ids)
        if format_id != "other" and date is not None:
            candidates.append(link)
    return candidates


def event_filename(event: dict[str, Any]) -> str:
    description = str(event["description"]).replace(" ", "_")
    filename = f"{description}_{event['event_id']}.json"
    if Path(filename).name != filename or filename in {".", ".."}:
        raise MTGOStorageError("event description produced an unsafe filename")
    return filename


def save_event(event: dict[str, Any], output_directory: str | Path) -> Path:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / event_filename(event)
    destination.write_text(json.dumps(event, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination


def load_fetched(path: str | Path) -> set[str]:
    source = Path(path)
    if not source.exists():
        return set()
    return {line.strip() for line in source.read_text(encoding="utf-8").splitlines() if line.strip()}


def mark_fetched(path: str | Path, link: str) -> None:
    with Path(path).open("a", encoding="utf-8") as handle:
        handle.write(link + "\n")


def recent_months(now: datetime | None = None) -> list[tuple[int, int]]:
    """Return the current and previous calendar month in stable order."""

    current = now or datetime.now()
    previous = (current.year - 1, 12) if current.month == 1 else (current.year, current.month - 1)
    return [(current.year, current.month), previous]


def fetch_event_months(
    repository_root: str | Path,
    format_id: str,
    *,
    months: Iterable[tuple[int, int]] | None = None,
    registry_path: str | Path | None = None,
    fetched_path: str | Path | None = None,
    request_get: Callable[..., Any] | None = None,
    sleep: Callable[[float], None] | None = None,
    inter_event_delay: float = 4,
) -> dict[str, Any]:
    """Fetch one format's recent event pages after capability authorization."""

    context = load_mtgo_event_collection_context(
        repository_root,
        format_id,
        registry_path=registry_path,
    )
    selected_months = list(months) if months is not None else recent_months()
    if not selected_months or any(
        not isinstance(year, int)
        or not isinstance(month, int)
        or year < 2000
        or month not in range(1, 13)
        for year, month in selected_months
    ):
        raise ValueError("months must contain valid (year, month) pairs")

    ledger = Path(fetched_path) if fetched_path is not None else context.repository_root / "fetched.txt"
    fetched = load_fetched(ledger)
    wait = sleep or time.sleep
    summary: dict[str, Any] = {
        "format": format_id,
        "months": selected_months,
        "candidates": 0,
        "fetched": 0,
        "skipped": 0,
        "excluded_no_playoff": 0,
        "failed": 0,
        "written": [],
        "errors": [],
    }
    for year, month in selected_months:
        list_url = f"{MTGO_BASE_URL}/decklists/{year}/{month:02d}"
        try:
            listing = download_page(
                list_url,
                request_get=request_get,
                sleep=wait,
            )
        except MTGOFetchError as exc:
            summary["failed"] += 1
            summary["errors"].append((list_url, str(exc)))
            continue
        candidates = discover_event_links(listing, (format_id,))
        summary["candidates"] += len(candidates)
        for link in candidates:
            if link in fetched:
                summary["skipped"] += 1
                continue
            event_url = f"{MTGO_BASE_URL}{link}"
            try:
                html = download_page(
                    event_url,
                    request_get=request_get,
                    sleep=wait,
                )
                raw = extract_event_data(html)
                if not is_event_data_complete(raw):
                    raise MTGOParseError("MTGO event data is incomplete")
                clean = normalize_event(raw, include_inplayoffs=True)
                if str(clean.get("inplayoffs")) != "1":
                    mark_fetched(ledger, link)
                    fetched.add(link)
                    summary["excluded_no_playoff"] += 1
                else:
                    destination = save_event(clean, context.paths["events"])
                    mark_fetched(ledger, link)
                    fetched.add(link)
                    summary["fetched"] += 1
                    summary["written"].append(destination)
            except (MTGOFetchError, MTGOParseError, MTGOStorageError, OSError) as exc:
                summary["failed"] += 1
                summary["errors"].append((event_url, str(exc)))
            if inter_event_delay:
                wait(inter_event_delay)
    return summary


def fetch_and_store_event(
    repository_root: str | Path,
    format_id: str,
    url: str,
    *,
    registry_path: str | Path | None = None,
    request_get: Callable[..., Any] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> Path:
    """Fetch one event only after explicit format authorization and safe path resolution."""

    context = load_mtgo_context(
        repository_root,
        format_id,
        "event_fetching",
        registry_path=registry_path,
    )
    missing = {"raw_event_storage", "normalization"} - context.definition.mtgo.capabilities
    if missing:
        raise MTGOStorageError(
            f"MTGO format {format_id!r} lacks required capabilities: {', '.join(sorted(missing))}"
        )
    link_format, _ = parse_event_link(url, (format_id,))
    if link_format != format_id:
        raise MTGOFetchError(f"event URL does not identify requested format {format_id!r}")
    html = download_page(url, request_get=request_get, sleep=sleep)
    raw = extract_event_data(html)
    if not is_event_data_complete(raw):
        raise MTGOParseError("MTGO event data is incomplete")
    clean = normalize_event(raw, include_inplayoffs=True)
    return save_event(clean, context.paths["events"])


__all__ = [
    "DEFAULT_HEADERS",
    "DECKLIST_MARKER",
    "MTGOFetchError",
    "MTGOParseError",
    "MTGOStorageError",
    "discover_event_links",
    "download_page",
    "event_filename",
    "extract_event_data",
    "fetch_event_months",
    "fetch_and_store_event",
    "is_event_data_complete",
    "load_fetched",
    "mark_fetched",
    "parse_event_link",
    "recent_months",
    "save_event",
]
