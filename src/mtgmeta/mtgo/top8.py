"""Generate complete-week MTGO Top 8 presentation documents."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import json
from pathlib import Path
import re
from typing import Any

from mtgmeta.classifier import classifier_digest
from mtgmeta.consumer import identity_display_name
from mtgmeta.rules import ArchetypeDefinition

from . import load_mtgo_context
from . import stats
from .normalize import load_rules_for_format
from . import week_lifecycle


SOURCE_ID = "mtgo"
TOP8_SCHEMA_VERSION = "1.1.0"


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


def _identity(
    record: dict[str, Any], parent: ArchetypeDefinition | None
) -> dict[str, Any]:
    parent_id = record["archetype_id"]
    parent_name = record["archetype"]
    subtype_id = record.get("subtype_id")
    subtype_name = record.get("subtype")
    if parent is None:
        if parent_id != "unknown" or parent_name != "Unknown" or subtype_id is not None:
            raise MTGOTop8Error("unrecognized classifier identity")
        identity_id = "unknown"
        display_name = "Unknown"
    elif subtype_id is None:
        identity_id = parent_id
        display_name = parent_name
    else:
        identity_id = f"{parent_id}/{subtype_id}"
        display_name = identity_display_name(
            parent_name,
            subtype_name,
            maintained_subtype_names=(item.name for item in parent.subtypes),
        )
    return {
        "identity_id": identity_id,
        "parent_id": parent_id,
        "subtype_id": subtype_id,
        "display_name": display_name,
        "detail_id": identity_id,
    }


def _versioned(document: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": TOP8_SCHEMA_VERSION, **document}


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
    parent: ArchetypeDefinition,
) -> dict[str, Any]:
    identity = _identity(record, parent)
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
                stats.deck_diff(vector, base["mean"]) if base_available else None
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
    processed_events: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if processed_events is None:
        processed = stats.process_event(event, rules)
    else:
        key = id(event)
        if key not in processed_events:
            processed_events[key] = stats.process_event(event, rules)
        processed = processed_events[key]
    definitions = {item.id: item for item in rules.archetypes}
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
            parent = definitions.get(record["archetype_id"])
            identity_id = _identity(record, parent)["identity_id"]
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
                    parent=parent,
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
    processed_events: dict[int, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    parent_bases, _parent_d99 = stats.build_base_pack(
        events,
        rules,
        monday,
        processed_events=processed_events,
    )
    subtype_bases, _subtype_d99 = stats.build_subtype_base_pack(
        events,
        rules,
        monday,
        processed_events=processed_events,
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
                identity_display_name(
                    parent.name,
                    subtype.name,
                    maintained_subtype_names=(
                        item.name for item in parent.subtypes
                    ),
                )
            )
    for parent_id, base in parent_bases.items():
        parent = definitions[parent_id]
        bases[parent_id] = {
            **base,
            "display_name": parent.name,
        }
    for (parent_id, subtype_id), base in subtype_bases.items():
        parent = definitions[parent_id]
        subtype = next(item for item in parent.subtypes if item.id == subtype_id)
        identity_id = f"{parent_id}/{subtype_id}"
        bases[identity_id] = {
            **base,
            "display_name": identity_display_name(
                parent.name,
                subtype.name,
                maintained_subtype_names=(
                    item.name for item in parent.subtypes
                ),
            ),
        }
    return bases


def _build_week_documents(
    events,
    rules,
    monday: date,
    *,
    format_id: str,
    processed_events: dict[int, dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if monday.weekday() != 0:
        raise MTGOTop8Error("weekly Top 8 period must start on Monday")
    sunday = monday + timedelta(days=6)
    label = iso_week_label(monday)
    comparison_bases_file = f"{label}-bases.json"
    bases = _comparison_bases(
        events,
        rules,
        monday,
        format_id=format_id,
        processed_events=processed_events,
    )
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
    digest = classifier_digest(rules)
    week = _versioned(
        {
            "document_type": "top8_week",
            "source": SOURCE_ID,
            "format": format_id,
            "classifier_digest": digest,
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
                    processed_events=processed_events,
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
    base_document = _versioned(
        {
            "document_type": "top8_comparison_bases",
            "source": SOURCE_ID,
            "format": format_id,
            "classifier_digest": digest,
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


def _load_document(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MTGOTop8Error(
            f"existing Top 8 document is unreadable: {path.name}"
        ) from exc
    if not isinstance(value, dict):
        raise MTGOTop8Error(f"existing Top 8 document is malformed: {path.name}")
    return value


def _placement_source(placement: dict[str, Any]) -> dict[str, Any]:
    exact = placement.get("exact_deck")
    return {
        "rank": placement.get("rank"),
        "deck_status": placement.get("deck_status"),
        "exact_deck": (
            {
                "player": exact.get("player"),
                "main_deck": exact.get("main_deck"),
                "sideboard": exact.get("sideboard"),
            }
            if isinstance(exact, dict)
            else None
        ),
    }


def _event_source(event: dict[str, Any]) -> dict[str, Any]:
    return {
        key: event.get(key)
        for key in ("event_id", "name", "date", "player_count")
    } | {
        "placements": [
            _placement_source(item)
            for item in event.get("placements", [])
            if isinstance(item, dict)
        ]
    }


def _verify_retained_sources(
    path: Path,
    document: dict[str, Any],
    *,
    allow_added_events: bool,
) -> dict[str, Any]:
    previous = _load_document(path)
    previous_events = {
        str(item.get("event_id")): item
        for item in previous.get("events", [])
        if isinstance(item, dict)
    }
    current_events = {
        str(item.get("event_id")): item
        for item in document.get("events", [])
        if isinstance(item, dict)
    }
    removed = sorted(set(previous_events) - set(current_events))
    if removed:
        raise MTGOTop8Error(
            "retained Top 8 update removed existing events: " + ", ".join(removed)
        )
    for event_id, prior in previous_events.items():
        if _event_source(prior) != _event_source(current_events[event_id]):
            raise MTGOTop8Error(
                f"retained Top 8 source facts changed: event {event_id}"
            )
    added = sorted(set(current_events) - set(previous_events))
    if added and not allow_added_events:
        raise MTGOTop8Error(
            "sealed Top 8 update added events: " + ", ".join(added)
        )
    return previous


def _placement_identity(placement: dict[str, Any]) -> str | None:
    identity = placement.get("identity")
    return identity.get("identity_id") if isinstance(identity, dict) else None


def _week_impact(
    previous_week: dict[str, Any] | None,
    current_week: dict[str, Any],
    previous_bases: dict[str, Any] | None,
    current_bases: dict[str, Any],
) -> dict[str, Any]:
    previous_events = {
        str(item.get("event_id")): item
        for item in (previous_week or {}).get("events", [])
        if isinstance(item, dict)
    }
    current_events = {
        str(item.get("event_id")): item
        for item in current_week.get("events", [])
        if isinstance(item, dict)
    }
    changes = []
    for event_id in sorted(set(previous_events) & set(current_events)):
        previous_placements = {
            item.get("rank"): item
            for item in previous_events[event_id].get("placements", [])
            if isinstance(item, dict)
        }
        current_placements = {
            item.get("rank"): item
            for item in current_events[event_id].get("placements", [])
            if isinstance(item, dict)
        }
        for rank in sorted(set(previous_placements) & set(current_placements)):
            before = _placement_identity(previous_placements[rank])
            after = _placement_identity(current_placements[rank])
            if before != after:
                changes.append(
                    {
                        "event_id": event_id,
                        "rank": rank,
                        "before": before,
                        "after": after,
                    }
                )

    previous_identities = (previous_bases or {}).get("identities", {})
    current_identities = current_bases.get("identities", {})
    if not isinstance(previous_identities, dict):
        previous_identities = {}
    if not isinstance(current_identities, dict):
        current_identities = {}
    common_identities = set(previous_identities) & set(current_identities)
    return {
        "week": current_week["week"]["start"],
        "previous_classifier_digest": (
            previous_week.get("classifier_digest")
            if previous_week is not None
            else None
        ),
        "added_event_ids": sorted(set(current_events) - set(previous_events)),
        "classification_changes": changes,
        "comparison_base_changes": {
            "added_identity_ids": sorted(
                set(current_identities) - set(previous_identities)
            ),
            "removed_identity_ids": sorted(
                set(previous_identities) - set(current_identities)
            ),
            "changed_identity_ids": sorted(
                identity_id
                for identity_id in common_identities
                if previous_identities[identity_id] != current_identities[identity_id]
            ),
        },
    }


def _entry_lifecycle(
    monday: date, *, today: date, already_sealed: bool = False
) -> dict[str, str]:
    sealed = already_sealed or week_lifecycle.is_sealed(monday, today=today)
    return {
        "status": "sealed" if sealed else "provisional",
        "provisional_through": week_lifecycle.provisional_through(monday).isoformat(),
        "seal_on": week_lifecycle.seal_on(monday).isoformat(),
    }


def write_latest_week(
    events,
    rules,
    output_directory: str | Path,
    *,
    format_id: str,
    today: date | None = None,
    generated_at: datetime | str | None = None,
) -> dict[str, Path]:
    reference_today = today or date.today()
    monday = stats.latest_complete_week(events, today=today)
    if monday is None:
        raise MTGOTop8Error("no complete MTGO event week is available")
    if generated_at is None:
        generated_value = datetime.now().isoformat(timespec="seconds")
    elif isinstance(generated_at, datetime):
        generated_value = generated_at.isoformat(timespec="seconds")
    else:
        generated_value = generated_at

    output = Path(output_directory)
    existing = _existing_catalog(output)
    existing_entries = existing["weeks"] if existing is not None else []
    entries_by_start: dict[date, dict[str, Any]] = {}
    for item in existing_entries:
        if not isinstance(item, dict):
            raise MTGOTop8Error("existing Top 8 catalog contains a malformed week")
        start = date.fromisoformat(str(item.get("start")))
        if start in entries_by_start:
            raise MTGOTop8Error("existing Top 8 catalog contains a duplicate week")
        entries_by_start[start] = item

    retained_mondays = sorted({monday, *entries_by_start})
    documents: dict[str, dict[str, Any]] = {}
    catalog_entries = []
    impacts = []
    digest = classifier_digest(rules)
    processed_events: dict[int, dict[str, Any]] = {}
    for retained_monday in retained_mondays:
        label = iso_week_label(retained_monday)
        filename = f"{label}.json"
        bases_filename = f"{label}-bases.json"
        week, comparison_bases = _build_week_documents(
            events,
            rules,
            retained_monday,
            format_id=format_id,
            processed_events=processed_events,
        )
        existing_entry = entries_by_start.get(retained_monday)
        previous_week = None
        previous_bases = None
        already_sealed = False
        if existing_entry is not None:
            if (
                existing_entry.get("file") != filename
                or existing_entry.get("comparison_bases_file") != bases_filename
            ):
                raise MTGOTop8Error(
                    f"existing Top 8 catalog paths do not match week {label}"
                )
            already_sealed = existing_entry.get("status") == "sealed"
            allow_added_events = not already_sealed and not week_lifecycle.is_sealed(
                retained_monday,
                today=reference_today,
            )
            previous_week = _verify_retained_sources(
                output / filename,
                week,
                allow_added_events=allow_added_events,
            )
            previous_bases = _load_document(output / bases_filename)
        impacts.append(
            _week_impact(
                previous_week,
                week,
                previous_bases,
                comparison_bases,
            )
        )
        documents[filename] = week
        documents[bases_filename] = comparison_bases
        catalog_entries.append(
            {
                "file": filename,
                "comparison_bases_file": bases_filename,
                "start": week["week"]["start"],
                "end": week["week"]["end"],
                "event_count": len(week["events"]),
                **_entry_lifecycle(
                    retained_monday,
                    today=reference_today,
                    already_sealed=already_sealed,
                ),
            }
        )

    catalog_entries = sorted(
        catalog_entries,
        key=lambda item: (item["start"], item["file"]),
        reverse=True,
    )
    impact = {
        "weeks": impacts,
        "summary": {
            "retained_week_count": len(impacts),
            "added_event_count": sum(
                len(item["added_event_ids"]) for item in impacts
            ),
            "classification_change_count": sum(
                len(item["classification_changes"]) for item in impacts
            ),
        },
    }
    catalog = _versioned(
        {
            "document_type": "top8_index",
            "source": SOURCE_ID,
            "format": format_id,
            "classifier_digest": digest,
            "generated": generated_value,
            "latest_complete_week": monday.isoformat(),
            "history_policy": "source_immutable_classifier_restatement",
            "classification_impact": impact,
            "weeks": catalog_entries,
        }
    )
    output.mkdir(parents=True, exist_ok=True)
    documents["index.json"] = catalog
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
    "classifier_digest",
    "event_display_name",
    "iso_week_label",
    "write_latest_week",
]
