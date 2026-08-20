"""Network, discovery, parsing, and storage helpers for MTGO events."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import re
import tempfile
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
REQUIRED_EVENT_FIELDS = frozenset(
    {"event_id", "description", "player_count", "inplayoffs", "decklists"}
)
PLAYOFF_REQUIRED_EVENT_FIELDS = frozenset({"standings", "final_rank"})
INCOMPLETE_EVENT_GRACE_DAYS = 2
LISTING_OBSERVATION_ATTEMPTS = 3
DISCOVERY_SCHEMA_VERSION = "1.0.0"


class MTGOFetchError(RuntimeError):
    """Raised after an MTGO page cannot be downloaded within the retry policy."""


class MTGOParseError(RuntimeError):
    """Raised when an MTGO page does not contain one complete event payload."""


class MTGOPageUnavailableError(MTGOParseError):
    """Raised when an event page lacks the expected embedded payload."""


class MTGOIncompleteEventError(MTGOParseError):
    """Raised when MTGO lists an event before publishing all required records."""


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
        except (
            Exception
        ) as exc:  # Preserve legacy retry behavior across request adapters.
            last_error = exc
            if on_error is not None:
                on_error(attempt, attempts, exc)
            if retry_delay and attempt < attempts:
                wait(retry_delay)
    raise MTGOFetchError(
        f"failed to download {url!r} after {attempts} attempts"
    ) from last_error


def extract_event_data(html: str) -> dict[str, Any]:
    start = html.find(DECKLIST_MARKER)
    if start == -1:
        raise MTGOPageUnavailableError("MTGO decklist marker was not found")
    brace_start = html.find("{", start + len(DECKLIST_MARKER))
    if brace_start == -1:
        raise MTGOPageUnavailableError("MTGO event JSON did not start")
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
                        value = json.loads(html[brace_start : index + 1])
                    except json.JSONDecodeError as exc:
                        raise MTGOPageUnavailableError(
                            f"MTGO event JSON is invalid: {exc.msg}"
                        ) from exc
                    if not isinstance(value, dict):
                        raise MTGOParseError("MTGO event JSON must be an object")
                    return value
    raise MTGOPageUnavailableError("MTGO event JSON did not end")


def _is_int_at_least(value: Any, minimum: int) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return False
    return parsed >= minimum


def _invalid_event_message(data: Any) -> str | None:
    if not isinstance(data, dict):
        return "MTGO event JSON must be an object"
    collection_names = ["decklists"]
    if str(data.get("inplayoffs")) == "1":
        collection_names.extend(["standings", "final_rank"])
    for name in collection_names:
        if name not in data:
            continue
        records = data[name]
        if not isinstance(records, list):
            return f"MTGO event {name} must be a list"
        seen = set()
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                return f"MTGO event {name}[{index}] must be an object"
            login_id = record.get("loginid")
            if (
                isinstance(login_id, bool)
                or not isinstance(login_id, (str, int))
                or not str(login_id).strip()
            ):
                return f"MTGO event {name}[{index}] has an invalid loginid"
            if login_id in seen:
                return f"MTGO event has duplicate {name} loginid {login_id!r}"
            seen.add(login_id)
            if name == "standings":
                for field, minimum in (("rank", 1), ("score", 0)):
                    value = record.get(field)
                    if (
                        value is not None
                        and value != ""
                        and not _is_int_at_least(value, minimum)
                    ):
                        return f"MTGO event standings[{index}].{field} is invalid"
            elif name == "final_rank":
                value = record.get("rank")
                if value is not None and value != "" and not _is_int_at_least(value, 1):
                    return f"MTGO event final_rank[{index}].rank is invalid"
    return None


def is_event_data_complete(data: Any) -> bool:
    return (
        _invalid_event_message(data) is None and _incomplete_event_message(data) is None
    )


def is_event_data_pending(data: Any) -> bool:
    """Return whether a valid event object is still being published."""

    return (
        _invalid_event_message(data) is None
        and _incomplete_event_message(data) is not None
    )


def _incomplete_event_message(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None
    required = REQUIRED_EVENT_FIELDS
    if str(data.get("inplayoffs")) == "1":
        required |= PLAYOFF_REQUIRED_EVENT_FIELDS
    missing = sorted(required - set(data))
    if missing:
        return f"MTGO event publication is incomplete (missing fields: {', '.join(missing)})"
    if isinstance(data.get("decklists"), list) and not data["decklists"]:
        return "MTGO event decklists have not been published yet"
    if str(data.get("inplayoffs")) != "1":
        return None
    if isinstance(data.get("standings"), list) and not data["standings"]:
        return "MTGO event standings have not been published yet"
    if isinstance(data.get("final_rank"), list) and not data["final_rank"]:
        return "MTGO event final ranks have not been published yet"
    if not all(
        isinstance(data.get(name), list)
        for name in ("decklists", "standings", "final_rank")
    ):
        return None
    deck_ids = {record["loginid"] for record in data["decklists"]}
    standing_ids = {record["loginid"] for record in data["standings"]}
    final_rank_ids = {record["loginid"] for record in data["final_rank"]}
    if not deck_ids <= standing_ids:
        return (
            "MTGO event standings do not cover published decklists "
            f"(missing={len(deck_ids - standing_ids)})"
        )
    if not deck_ids <= final_rank_ids:
        return (
            "MTGO event final ranks do not cover published decklists "
            f"(missing={len(deck_ids - final_rank_ids)})"
        )
    standings_by_id = {record["loginid"]: record for record in data["standings"]}
    final_ranks_by_id = {record["loginid"]: record for record in data["final_rank"]}
    missing_standing_values = sum(
        standings_by_id[login_id].get("rank") in (None, "")
        or standings_by_id[login_id].get("score") in (None, "")
        for login_id in deck_ids
    )
    if missing_standing_values:
        return (
            "MTGO event standings are missing rank or score values "
            f"for {missing_standing_values} published decklists"
        )
    missing_final_ranks = sum(
        final_ranks_by_id[login_id].get("rank") in (None, "") for login_id in deck_ids
    )
    if missing_final_ranks:
        return (
            "MTGO event final ranks are missing values "
            f"for {missing_final_ranks} published decklists"
        )
    return None


def _is_within_incomplete_event_grace(link: str, now: datetime) -> bool:
    _, event_date_value = parse_event_link(link, ())
    if event_date_value is None:
        return False
    try:
        event_date = datetime.strptime(event_date_value, "%Y-%m-%d").date()
    except ValueError:
        return False
    age_days = (now.date() - event_date).days
    return 0 <= age_days <= INCOMPLETE_EVENT_GRACE_DAYS


def download_event_data(
    url: str,
    *,
    attempts: int = 5,
    timeout: int = 90,
    retry_delay: float = 5,
    request_get: Callable[..., Any] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    """Download, parse, and validate one event within a shared retry policy."""

    if attempts < 1:
        raise ValueError("attempts must be at least one")
    wait = sleep or time.sleep
    last_error: MTGOFetchError | MTGOParseError | None = None
    for attempt in range(1, attempts + 1):
        try:
            html = download_page(
                url,
                attempts=1,
                timeout=timeout,
                retry_delay=0,
                request_get=request_get,
                sleep=wait,
            )
            data = extract_event_data(html)
            invalid_message = _invalid_event_message(data)
            if invalid_message is not None:
                last_error = MTGOParseError(invalid_message)
            else:
                incomplete_message = _incomplete_event_message(data)
                if incomplete_message is None:
                    return data
                last_error = MTGOIncompleteEventError(incomplete_message)
        except (MTGOFetchError, MTGOParseError) as exc:
            last_error = exc
        if retry_delay and attempt < attempts:
            wait(retry_delay)
    if isinstance(last_error, MTGOIncompleteEventError):
        raise MTGOIncompleteEventError(f"{last_error} after {attempts} attempts")
    if last_error is None:  # Defensive guard; attempts >= 1 always assigns or returns.
        raise MTGOFetchError(f"failed to download event data from {url!r}")
    raise last_error


def parse_event_link(
    link: str, recognized_format_ids: Iterable[str]
) -> tuple[str, str | None]:
    path = urlparse(link).path
    name = path.removeprefix("/decklist/")
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", name)
    first_word = name.split("-", 1)[0].lower()
    recognized = frozenset(recognized_format_ids)
    return (
        first_word if first_word in recognized else "other",
        date_match.group(1) if date_match else None,
    )


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
    destination.write_text(
        json.dumps(event, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return destination


def load_fetched(path: str | Path) -> set[str]:
    source = Path(path)
    if not source.exists():
        return set()
    return {
        line.strip()
        for line in source.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def mark_fetched(path: str | Path, link: str) -> None:
    with Path(path).open("a", encoding="utf-8") as handle:
        handle.write(link + "\n")


def _discovery_path(events_directory: Path) -> Path:
    return events_directory / "mtgo" / "discovery.json"


def _load_discovery(path: Path, format_id: str) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MTGOStorageError("MTGO discovery state is unreadable") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != DISCOVERY_SCHEMA_VERSION
        or value.get("source") != "mtgo"
        or value.get("format") != format_id
        or not isinstance(value.get("events"), list)
    ):
        raise MTGOStorageError("MTGO discovery state is malformed")
    records: dict[str, dict[str, str]] = {}
    for item in value["events"]:
        if not isinstance(item, dict) or set(item) != {"link", "event_date", "status"}:
            raise MTGOStorageError("MTGO discovery state contains a malformed event")
        link = item["link"]
        parsed_format, parsed_date = parse_event_link(link, (format_id,))
        if parsed_format != format_id or parsed_date != item["event_date"]:
            raise MTGOStorageError(
                "MTGO discovery state contains an invalid event identity"
            )
        if item["status"] not in {
            "discovered",
            "processed",
            "retained",
            "excluded_no_playoff",
            "deferred_incomplete",
        }:
            raise MTGOStorageError("MTGO discovery state contains an invalid status")
        if link in records:
            raise MTGOStorageError("MTGO discovery state contains duplicate links")
        records[link] = dict(item)
    return records


def _write_discovery(
    path: Path, format_id: str, records: dict[str, dict[str, str]]
) -> None:
    document = {
        "schema_version": DISCOVERY_SCHEMA_VERSION,
        "source": "mtgo",
        "format": format_id,
        "events": sorted(
            records.values(), key=lambda item: (item["event_date"], item["link"])
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
    ) as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
        temporary = Path(handle.name)
    temporary.replace(path)


def _links_for_month(
    links: Iterable[str], format_id: str, year: int, month: int
) -> set[str]:
    prefix = f"{year:04d}-{month:02d}-"
    selected = set()
    for link in links:
        parsed_format, event_date = parse_event_link(link, (format_id,))
        if (
            parsed_format == format_id
            and event_date is not None
            and event_date.startswith(prefix)
        ):
            selected.add(link)
    return selected


def _observe_listing(
    url: str,
    format_id: str,
    expected_links: set[str],
    *,
    year: int,
    month: int,
    request_get: Callable[..., Any] | None,
    wait: Callable[[float], None],
) -> list[str]:
    observed: set[str] = set()
    for attempt in range(1, LISTING_OBSERVATION_ATTEMPTS + 1):
        listing = download_page(url, request_get=request_get, sleep=wait)
        observed.update(
            _links_for_month(
                discover_event_links(listing, (format_id,)),
                format_id,
                year,
                month,
            )
        )
        if attempt < LISTING_OBSERVATION_ATTEMPTS:
            wait(2)
    return sorted(observed | expected_links)


def recent_months(now: datetime | None = None) -> list[tuple[int, int]]:
    """Return the current and previous calendar month in stable order."""

    current = now or datetime.now()
    previous = (
        (current.year - 1, 12)
        if current.month == 1
        else (current.year, current.month - 1)
    )
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
    now: datetime | None = None,
) -> dict[str, Any]:
    """Fetch one format's recent event pages after capability authorization."""

    context = load_mtgo_event_collection_context(
        repository_root,
        format_id,
        registry_path=registry_path,
    )
    reference_now = now or datetime.now()
    selected_months = (
        list(months) if months is not None else recent_months(reference_now)
    )
    if not selected_months or any(
        not isinstance(year, int)
        or not isinstance(month, int)
        or year < 2000
        or month not in range(1, 13)
        for year, month in selected_months
    ):
        raise ValueError("months must contain valid (year, month) pairs")

    ledger = (
        Path(fetched_path)
        if fetched_path is not None
        else context.repository_root / "fetched.txt"
    )
    fetched = load_fetched(ledger)
    discovery_path = _discovery_path(context.paths["events"])
    discovery = _load_discovery(discovery_path, format_id)
    wait = sleep or time.sleep
    summary: dict[str, Any] = {
        "format": format_id,
        "months": selected_months,
        "candidates": 0,
        "fetched": 0,
        "skipped": 0,
        "excluded_no_playoff": 0,
        "deferred_incomplete": 0,
        "failed": 0,
        "transient_failed": 0,
        "written": [],
        "warnings": [],
        "errors": [],
    }
    for year, month in selected_months:
        list_url = f"{MTGO_BASE_URL}/decklists/{year}/{month:02d}"
        try:
            expected = _links_for_month(
                set(fetched) | set(discovery), format_id, year, month
            )
            candidates = _observe_listing(
                list_url,
                format_id,
                expected,
                year=year,
                month=month,
                request_get=request_get,
                wait=wait,
            )
        except MTGOFetchError as exc:
            summary["failed"] += 1
            summary["transient_failed"] += 1
            summary["errors"].append((list_url, str(exc)))
            break
        summary["candidates"] += len(candidates)
        for link in candidates:
            _format, event_date_value = parse_event_link(link, (format_id,))
            discovery.setdefault(
                link,
                {
                    "link": link,
                    "event_date": str(event_date_value),
                    "status": "processed" if link in fetched else "discovered",
                },
            )
            if link in fetched:
                discovery[link]["status"] = "processed"
                summary["skipped"] += 1
                continue
            event_url = f"{MTGO_BASE_URL}{link}"
            try:
                raw = download_event_data(
                    event_url,
                    request_get=request_get,
                    sleep=wait,
                )
                clean = normalize_event(raw, include_inplayoffs=True)
                if str(clean.get("inplayoffs")) != "1":
                    mark_fetched(ledger, link)
                    fetched.add(link)
                    discovery[link]["status"] = "excluded_no_playoff"
                    summary["excluded_no_playoff"] += 1
                else:
                    destination = save_event(clean, context.paths["events"])
                    mark_fetched(ledger, link)
                    fetched.add(link)
                    discovery[link]["status"] = "retained"
                    summary["fetched"] += 1
                    summary["written"].append(destination)
            except MTGOIncompleteEventError as exc:
                if _is_within_incomplete_event_grace(link, reference_now):
                    summary["deferred_incomplete"] += 1
                    discovery[link]["status"] = "deferred_incomplete"
                    summary["warnings"].append(
                        (event_url, f"{exc}; will retry on a later scheduled run")
                    )
                else:
                    summary["failed"] += 1
                    summary["errors"].append(
                        (
                            event_url,
                            f"{exc}; event is outside the "
                            f"{INCOMPLETE_EVENT_GRACE_DAYS}-day publication grace period",
                        )
                    )
            except (MTGOFetchError, MTGOPageUnavailableError) as exc:
                summary["failed"] += 1
                summary["transient_failed"] += 1
                summary["errors"].append((event_url, str(exc)))
            except (MTGOParseError, MTGOStorageError, OSError) as exc:
                summary["failed"] += 1
                summary["errors"].append((event_url, str(exc)))
            if inter_event_delay:
                wait(inter_event_delay)
        _write_discovery(discovery_path, format_id, discovery)
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
    missing = {
        "raw_event_storage",
        "normalization",
    } - context.definition.mtgo.capabilities
    if missing:
        raise MTGOStorageError(
            f"MTGO format {format_id!r} lacks required capabilities: {', '.join(sorted(missing))}"
        )
    link_format, _ = parse_event_link(url, (format_id,))
    if link_format != format_id:
        raise MTGOFetchError(
            f"event URL does not identify requested format {format_id!r}"
        )
    raw = download_event_data(url, request_get=request_get, sleep=sleep)
    clean = normalize_event(raw, include_inplayoffs=True)
    return save_event(clean, context.paths["events"])


def _player_final_ranks(event: dict[str, Any]) -> dict[str | int, int]:
    players = event.get("players")
    if not isinstance(players, list) or not players:
        raise MTGOStorageError("retained event players must be a non-empty list")
    ranks = {}
    for index, player in enumerate(players):
        if not isinstance(player, dict):
            raise MTGOStorageError(f"retained event players[{index}] must be an object")
        login_id = player.get("loginid")
        if (
            isinstance(login_id, bool)
            or not isinstance(login_id, (str, int))
            or not str(login_id).strip()
        ):
            raise MTGOStorageError(
                f"retained event players[{index}] has an invalid loginid"
            )
        if login_id in ranks:
            raise MTGOStorageError(f"retained event has duplicate loginid {login_id!r}")
        final_rank = player.get("final_rank")
        if not _is_int_at_least(final_rank, 1):
            raise MTGOStorageError(
                f"retained event player {login_id!r} has an invalid final_rank"
            )
        ranks[login_id] = int(str(final_rank).strip())
    return ranks


def refresh_existing_event(
    repository_root: str | Path,
    format_id: str,
    url: str,
    *,
    registry_path: str | Path | None = None,
    request_get: Callable[..., Any] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> Path:
    """Atomically refresh one retained event after stable-identity verification."""

    context = load_mtgo_event_collection_context(
        repository_root,
        format_id,
        registry_path=registry_path,
    )
    link_format, _ = parse_event_link(url, (format_id,))
    if link_format != format_id:
        raise MTGOFetchError(
            f"event URL does not identify requested format {format_id!r}"
        )
    clean = normalize_event(
        download_event_data(url, request_get=request_get, sleep=sleep),
        include_inplayoffs=True,
    )
    if str(clean.get("inplayoffs")) != "1":
        raise MTGOStorageError("controlled refresh requires a playoff event")
    event_id = str(clean.get("event_id", "")).strip()
    if not event_id or not event_id.isdigit():
        raise MTGOStorageError("controlled refresh requires a numeric event_id")
    matches = sorted(context.paths["events"].glob(f"*_{event_id}.json"))
    if len(matches) != 1:
        raise MTGOStorageError(
            f"controlled refresh requires exactly one retained event {event_id}; "
            f"found {len(matches)}"
        )
    destination = matches[0]
    try:
        retained = json.loads(destination.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MTGOStorageError(
            f"cannot read retained event {destination.name}: {exc}"
        ) from exc
    if str(retained.get("event_id")) != event_id:
        raise MTGOStorageError("retained event_id does not match refreshed event")
    retained_format = str(retained.get("format", "")).lower().removeprefix("c")
    refreshed_format = str(clean.get("format", "")).lower().removeprefix("c")
    if retained_format != format_id or refreshed_format != format_id:
        raise MTGOStorageError(
            "retained or refreshed event format does not match request"
        )
    retained_ranks = _player_final_ranks(retained)
    refreshed_ranks = _player_final_ranks(clean)
    if set(retained_ranks) != set(refreshed_ranks):
        raise MTGOStorageError("retained event player identities changed")
    if retained_ranks != refreshed_ranks:
        raise MTGOStorageError("retained event final ranks changed")

    payload = json.dumps(clean, ensure_ascii=False, indent=2).encode("utf-8")
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(payload)
            temporary_path = Path(handle.name)
        temporary_path.replace(destination)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return destination


__all__ = [
    "DEFAULT_HEADERS",
    "DECKLIST_MARKER",
    "MTGOFetchError",
    "MTGOIncompleteEventError",
    "MTGOPageUnavailableError",
    "MTGOParseError",
    "MTGOStorageError",
    "discover_event_links",
    "download_event_data",
    "download_page",
    "event_filename",
    "extract_event_data",
    "fetch_event_months",
    "fetch_and_store_event",
    "is_event_data_complete",
    "is_event_data_pending",
    "load_fetched",
    "mark_fetched",
    "parse_event_link",
    "recent_months",
    "refresh_existing_event",
    "save_event",
]
