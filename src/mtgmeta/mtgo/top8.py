"""Generate complete-week MTGO Top 8 presentation documents."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import json
from pathlib import Path
import re
from typing import Any

from public_contract import versioned

from . import load_mtgo_context
from . import stats
from .normalize import load_rules_for_format


SOURCE_ID = "mtgo"


class MTGOTop8Error(RuntimeError):
    """Raised when weekly Top 8 data cannot be generated safely."""


def iso_week_label(monday: date) -> str:
    year, week, _weekday = monday.isocalendar()
    return f"{year}-W{week:02d}"


def event_display_name(name: str, format_id: str) -> str:
    """Return the approved compact event label without repeating the format."""

    value = str(name).strip()
    value = re.sub(rf"^{re.escape(format_id)}\s+", "", value, flags=re.IGNORECASE)
    patterns = (
        (r"^Challenge\s+(\d+)$", lambda match: f"C{match.group(1)}"),
        (r"^Showcase Challenge$", lambda _match: "SC"),
        (r"^Showcase Qualifier$", lambda _match: "SCQ"),
        (r"^RC Qualifier$", lambda _match: "RCQ"),
        (r"^RC Super Qualifier$", lambda _match: "RCSQ"),
    )
    for pattern, render in patterns:
        match = re.fullmatch(pattern, value, flags=re.IGNORECASE)
        if match:
            return render(match)
    return value


def _identity(record: dict[str, Any]) -> dict[str, Any]:
    parent_id = record["archetype_id"]
    parent_name = record["archetype"]
    subtype_id = record.get("subtype_id")
    subtype_name = record.get("subtype")
    if subtype_id is None:
        identity_id = parent_id
        display_name = parent_name
    else:
        identity_id = f"{parent_id}/{subtype_id}"
        display_name = (
            subtype_name
            if parent_name.casefold() in str(subtype_name).casefold()
            else f"{subtype_name} {parent_name}"
        )
    return {
        "identity_id": identity_id,
        "parent_id": parent_id,
        "subtype_id": subtype_id,
        "display_name": display_name,
        "detail_id": identity_id,
    }


def _missing_placement(rank: int) -> dict[str, Any]:
    return {
        "rank": rank,
        "deck_status": "missing",
        "identity": None,
        "exact_deck": None,
        "comparison": None,
    }


def _available_placement(
    rank: int,
    record: dict[str, Any],
    *,
    base_period_end: date,
) -> dict[str, Any]:
    identity = _identity(record)
    return {
        "rank": rank,
        "deck_status": "available",
        "identity": identity,
        "exact_deck": {
            "player": str(record.get("player") or "?"),
            "main_deck": stats.merge_cards(record.get("main_deck", [])),
            "sideboard": stats.merge_cards(record.get("side_deck", [])),
        },
        "comparison": {
            "identity_id": identity["identity_id"],
            "base_period": "4w",
            "base_period_end": base_period_end.isoformat(),
            "average_deck_ref": (
                f"decks_4w.json#identity/{identity['identity_id']}"
            ),
        },
    }


def _event_document(
    event_date: date,
    event: dict[str, Any],
    rules,
    *,
    format_id: str,
    base_period_end: date,
) -> dict[str, Any]:
    processed = stats.process_event(event, rules)
    records_by_rank: dict[int, dict[str, Any]] = {}
    for record in processed["records"]:
        rank = record["final_rank"]
        if not 1 <= rank <= 8:
            continue
        if rank in records_by_rank:
            raise MTGOTop8Error(
                f"event {event.get('event_id', '?')} has duplicate final rank {rank}"
            )
        records_by_rank[rank] = record

    placements = []
    for rank in range(1, 9):
        record = records_by_rank.get(rank)
        if record is None or not record.get("main_deck"):
            placements.append(_missing_placement(rank))
        else:
            placements.append(
                _available_placement(
                    rank,
                    record,
                    base_period_end=base_period_end,
                )
            )

    event_id = str(event.get("event_id", "")).strip()
    name = str(event.get("description", "")).strip()
    player_count = stats.to_int(event.get("player_count"))
    if not event_id.isdigit() or not name or player_count < 1:
        raise MTGOTop8Error("event identity, name, and player_count are required")
    return {
        "event_id": event_id,
        "name": name,
        "display_name": event_display_name(name, format_id),
        "date": event_date.isoformat(),
        "player_count": player_count,
        "placements": placements,
    }


def build_week_document(
    events,
    rules,
    monday: date,
    *,
    format_id: str,
) -> dict[str, Any]:
    if monday.weekday() != 0:
        raise MTGOTop8Error("weekly Top 8 period must start on Monday")
    sunday = monday + timedelta(days=6)
    selected = [
        (event_date, event)
        for event_date, event in events
        if monday <= event_date <= sunday
    ]
    if not selected:
        raise MTGOTop8Error(f"no admitted events are available for week {monday}")
    ordered = sorted(
        selected,
        key=lambda item: (
            item[0],
            str(item[1].get("event_id", "")),
            str(item[1].get("description", "")),
        ),
    )
    event_ids = [str(event.get("event_id", "")).strip() for _date, event in ordered]
    if len(event_ids) != len(set(event_ids)):
        raise MTGOTop8Error(f"week {monday} contains a duplicate event_id")
    return versioned(
        {
            "document_type": "top8_week",
            "source": SOURCE_ID,
            "format": format_id,
            "week": {
                "start": monday.isoformat(),
                "end": sunday.isoformat(),
            },
            "events": [
                _event_document(
                    event_date,
                    event,
                    rules,
                    format_id=format_id,
                    base_period_end=sunday,
                )
                for event_date, event in ordered
            ],
        }
    )


def write_latest_week(
    events,
    rules,
    output_directory: str | Path,
    *,
    format_id: str,
    today: date | None = None,
    generated_at: datetime | str | None = None,
) -> dict[str, Path]:
    monday = stats.latest_complete_week(events, today=today)
    if monday is None:
        raise MTGOTop8Error("no complete MTGO event week is available")
    week = build_week_document(events, rules, monday, format_id=format_id)
    if generated_at is None:
        generated_value = datetime.now().isoformat(timespec="seconds")
    elif isinstance(generated_at, datetime):
        generated_value = generated_at.isoformat(timespec="seconds")
    else:
        generated_value = generated_at

    filename = f"{iso_week_label(monday)}.json"
    catalog = versioned(
        {
            "document_type": "top8_index",
            "source": SOURCE_ID,
            "format": format_id,
            "generated": generated_value,
            "latest_complete_week": monday.isoformat(),
            "weeks": [
                {
                    "file": filename,
                    "start": week["week"]["start"],
                    "end": week["week"]["end"],
                    "event_count": len(week["events"]),
                }
            ],
        }
    )
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    documents = {filename: week, "index.json": catalog}
    written = {}
    for name, document in documents.items():
        destination = output / name
        destination.write_text(
            json.dumps(document, ensure_ascii=False, indent=2),
            encoding="utf-8",
            newline="\n",
        )
        written[name] = destination
    return written


def build_all_top8(
    repository_root: str | Path,
    format_id: str,
    *,
    today: date | None = None,
    generated_at: datetime | str | None = None,
    output_directory: str | Path | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Path]:
    root = Path(repository_root).resolve()
    context = load_mtgo_context(
        root,
        format_id,
        "weekly_top8",
        registry_path=registry_path,
    )
    events = stats.load_events_from_directory(
        context.paths["events"],
        repository_root=context.repository_root,
        format_id=format_id,
    )
    rules = load_rules_for_format(root, format_id, registry_path=registry_path)
    output = (
        Path(output_directory)
        if output_directory is not None
        else context.paths["statistics"] / "top8"
    )
    return write_latest_week(
        events,
        rules,
        output,
        format_id=format_id,
        today=today,
        generated_at=generated_at,
    )


__all__ = [
    "MTGOTop8Error",
    "build_all_top8",
    "build_week_document",
    "event_display_name",
    "iso_week_label",
    "write_latest_week",
]
