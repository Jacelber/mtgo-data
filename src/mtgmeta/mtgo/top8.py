"""Generate complete-week MTGO Top 8 presentation documents."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import json
from pathlib import Path
import re
from typing import Any

from mtgmeta.public_contract import versioned
from mtgmeta.consumer import identity_display_name

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
        display_name = identity_display_name(parent_name, subtype_name)
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
    base: dict[str, Any],
    comparison_bases_file: str,
) -> dict[str, Any]:
    identity = _identity(record)
    vector = stats.deck_vector(record)
    base_available = base["sample_size"] > 0
    raw_deviation = (
        stats.weighted_l1(vector, base["mean"], base["weights"])
        if base_available
        else None
    )
    return {
        "rank": rank,
        "deck_status": "available",
        "identity": identity,
        "exact_deck": {
            "player": str(record.get("player") or "?"),
            "main_deck": stats.merge_cards(record.get("main_deck", [])),
            "sideboard": stats.merge_cards(record.get("side_deck", [])),
            "deviation": (
                stats.normalize_dev_abs(raw_deviation, base["denom"])
                if raw_deviation is not None
                else None
            ),
            "deviation_diff": (
                stats.deck_diff(vector, base["mean"])
                if base_available
                else None
            ),
        },
        "comparison": {
            "identity_id": identity["identity_id"],
            "base_period": "4w",
            "base_period_end": base_period_end.isoformat(),
            "base_status": "available" if base_available else "unavailable",
            "average_deck_ref": (
                f"{comparison_bases_file}#identity/{identity['identity_id']}"
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
    bases: dict[str, dict[str, Any]],
    comparison_bases_file: str,
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
            identity_id = _identity(record)["identity_id"]
            base = bases.get(identity_id)
            if base is None:
                raise MTGOTop8Error(
                    f"event {event.get('event_id', '?')} rank {rank} "
                    f"has no four-week comparison base for {identity_id}"
                )
            placements.append(
                _available_placement(
                    rank,
                    record,
                    base_period_end=base_period_end,
                    base=base,
                    comparison_bases_file=comparison_bases_file,
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
    week, _bases = _build_week_documents(
        events,
        rules,
        monday,
        format_id=format_id,
    )
    return week


def _average_deck(base: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_size": base["sample_size"],
        "medoid": base["medoid_display"],
        "core": base["core"],
        "flex": base["flex"],
        "recent_change": base["recent_change"],
        "recent_change_reason": base["recent_change_reason"],
    }


def _comparison_bases(
    events,
    rules,
    monday: date,
    *,
    format_id: str,
) -> dict[str, dict[str, Any]]:
    parent_bases, _parent_d99 = stats.build_base_pack(events, rules, monday)
    subtype_bases, _subtype_d99 = stats.build_subtype_base_pack(
        events,
        rules,
        monday,
    )
    definitions = {item.id: item for item in rules.archetypes}
    bases: dict[str, dict[str, Any]] = {}
    def empty_base(display_name: str) -> dict[str, Any]:
        return {
            "display_name": display_name,
            "mean": {},
            "weights": {},
            "denom": 0,
            "core": [],
            "flex": [],
            "medoid_display": None,
            "sample_size": 0,
            "recent_change": None,
            "recent_change_reason": "nobase",
        }

    bases["unknown"] = empty_base("Unknown")
    for parent in rules.archetypes:
        bases[parent.id] = empty_base(parent.name)
        for subtype in parent.subtypes:
            identity_id = f"{parent.id}/{subtype.id}"
            bases[identity_id] = empty_base(
                identity_display_name(parent.name, subtype.name)
            )
    for parent_id, base in parent_bases.items():
        parent = definitions[parent_id]
        bases[parent_id] = {
            **base,
            "display_name": parent.name,
        }
    for (parent_id, subtype_id), base in subtype_bases.items():
        parent = definitions[parent_id]
        subtype = next(
            item for item in parent.subtypes if item.id == subtype_id
        )
        identity_id = f"{parent_id}/{subtype_id}"
        bases[identity_id] = {
            **base,
            "display_name": identity_display_name(parent.name, subtype.name),
        }
    return bases


def _build_week_documents(
    events,
    rules,
    monday: date,
    *,
    format_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if monday.weekday() != 0:
        raise MTGOTop8Error("weekly Top 8 period must start on Monday")
    sunday = monday + timedelta(days=6)
    label = iso_week_label(monday)
    comparison_bases_file = f"{label}-bases.json"
    bases = _comparison_bases(events, rules, monday, format_id=format_id)
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
    week = versioned(
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
                    bases=bases,
                    comparison_bases_file=comparison_bases_file,
                )
                for event_date, event in ordered
            ],
        }
    )
    referenced_ids = sorted(
        placement["comparison"]["identity_id"]
        for item in week["events"]
        for placement in item["placements"]
        if placement["comparison"] is not None
    )
    base_document = versioned(
        {
            "document_type": "top8_comparison_bases",
            "source": SOURCE_ID,
            "format": format_id,
            "week": {
                "start": monday.isoformat(),
                "end": sunday.isoformat(),
            },
            "base_period": "4w",
            "base_period_end": sunday.isoformat(),
            "identities": {
                identity_id: {
                    "identity_id": identity_id,
                    "display_name": bases[identity_id]["display_name"],
                    "base_status": (
                        "available"
                        if bases[identity_id]["sample_size"] > 0
                        else "unavailable"
                    ),
                    "average_deck": _average_deck(bases[identity_id]),
                }
                for identity_id in sorted(set(referenced_ids))
            },
        }
    )
    return week, base_document


def _document_bytes(document: dict[str, Any]) -> bytes:
    return json.dumps(
        document,
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")


def _existing_catalog(output: Path) -> dict[str, Any] | None:
    path = output / "index.json"
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MTGOTop8Error("existing Top 8 catalog is unreadable") from exc
    if not isinstance(value, dict) or not isinstance(value.get("weeks"), list):
        raise MTGOTop8Error("existing Top 8 catalog is malformed")
    return value


def _verify_immutable_file(
    path: Path,
    document: dict[str, Any],
) -> None:
    if path.read_bytes() != _document_bytes(document):
        raise MTGOTop8Error(
            f"immutable historical Top 8 document changed: {path.name}"
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
    week, comparison_bases = _build_week_documents(
        events,
        rules,
        monday,
        format_id=format_id,
    )
    if generated_at is None:
        generated_value = datetime.now().isoformat(timespec="seconds")
    elif isinstance(generated_at, datetime):
        generated_value = generated_at.isoformat(timespec="seconds")
    else:
        generated_value = generated_at

    filename = f"{iso_week_label(monday)}.json"
    comparison_bases_filename = f"{iso_week_label(monday)}-bases.json"
    output = Path(output_directory)
    existing = _existing_catalog(output)
    existing_entries = existing["weeks"] if existing is not None else []
    existing_current = next(
        (item for item in existing_entries if item.get("file") == filename),
        None,
    )
    if (
        isinstance(existing_current, dict)
        and existing_current.get("comparison_bases_file")
        == comparison_bases_filename
    ):
        _verify_immutable_file(output / filename, week)
        _verify_immutable_file(
            output / comparison_bases_filename,
            comparison_bases,
        )
    current_entry = {
        "file": filename,
        "comparison_bases_file": comparison_bases_filename,
        "start": week["week"]["start"],
        "end": week["week"]["end"],
        "event_count": len(week["events"]),
    }
    retained_entries = [
        item for item in existing_entries if item.get("file") != filename
    ]
    catalog_entries = sorted(
        [current_entry, *retained_entries],
        key=lambda item: (item["start"], item["file"]),
        reverse=True,
    )
    catalog = versioned(
        {
            "document_type": "top8_index",
            "source": SOURCE_ID,
            "format": format_id,
            "generated": generated_value,
            "latest_complete_week": monday.isoformat(),
            "history_policy": "immutable_weekly_comparison_bases",
            "weeks": catalog_entries,
        }
    )
    output.mkdir(parents=True, exist_ok=True)
    documents = {
        filename: week,
        comparison_bases_filename: comparison_bases,
        "index.json": catalog,
    }
    written = {}
    for name, document in documents.items():
        destination = output / name
        destination.write_text(
            _document_bytes(document).decode("utf-8"),
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
