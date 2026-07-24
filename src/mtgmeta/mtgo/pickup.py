"""Format-aware MTGO Weekly Pickup, metadata, and catalog helpers."""

from __future__ import annotations

import json
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml

from mtgmeta.classifier import classify_deck
from public_contract import versioned

from . import load_mtgo_context
from . import matchup
from . import stats
from .normalize import load_rules_for_format


SOURCE_ID = "mtgo"
INITIAL_KNOWN_WEEKS = 12


class MTGOPickupError(RuntimeError):
    """Raised when Pickup or publication metadata cannot be produced safely."""


def iso_week_label(monday: date) -> str:
    year, week, _ = monday.isocalendar()
    return f"{year}-W{week:02d}"


def week_records(events, rules, end_monday: date) -> list[dict[str, Any]]:
    end_sunday = end_monday + timedelta(days=6)
    records: list[dict[str, Any]] = []
    for event_date, event in events:
        if end_monday <= event_date <= end_sunday:
            records.extend(stats.process_event(event, rules)["records"])
    return records


def archetypes_in_window(
    events,
    rules,
    end_monday: date,
    n_weeks: int,
    *,
    stable_ids: bool = False,
) -> set[str]:
    if not isinstance(n_weeks, int) or isinstance(n_weeks, bool) or n_weeks <= 0:
        raise MTGOPickupError("n_weeks must be a positive integer")
    start = end_monday - timedelta(weeks=n_weeks - 1)
    end_sunday = end_monday + timedelta(days=6)
    names: set[str] = set()
    for event_date, event in events:
        if start <= event_date <= end_sunday:
            for record in stats.process_event(event, rules)["records"]:
                if record["archetype"] != "Unknown":
                    names.add(
                        record["archetype_id"] if stable_ids else record["archetype"]
                    )
    return names


def load_known(path: str | Path, *, stable_ids: bool = False) -> set[str] | None:
    source = Path(path)
    if not source.exists():
        return None
    document = json.loads(source.read_text(encoding="utf-8"))
    field = "known_ids" if stable_ids else "known"
    known = document.get(field, [])
    if not isinstance(known, list) or any(not isinstance(item, str) for item in known):
        raise MTGOPickupError(f"{source}: {field} must be a list of strings")
    return set(known)


def deck_deviation(record, base, _d99=None):
    if not base:
        return None
    vector = stats.deck_vector(record)
    raw = stats.weighted_l1(vector, base["mean"], base["weights"])
    return stats.normalize_dev_abs(raw, base["denom"])


def record_deck_cards(record) -> dict[str, list[dict[str, Any]]]:
    return {
        "main_deck": stats.merge_cards(record.get("main_deck", [])),
        "side_deck": stats.merge_cards(record.get("side_deck", [])),
    }


def deck_fingerprint(record) -> tuple[tuple[tuple[str, int], ...], tuple[tuple[str, int], ...]]:
    main = tuple(
        (card["name"], card["qty"])
        for card in stats.merge_cards(record.get("main_deck", []))
    )
    side = tuple(
        (card["name"], card["qty"])
        for card in stats.merge_cards(record.get("side_deck", []))
    )
    return main, side


def better_record(first, second):
    first_key = (first["final_rank"], -first["player_count"], first["starttime"])
    second_key = (second["final_rank"], -second["player_count"], second["starttime"])
    return first if first_key <= second_key else second


def _pickup_directories(
    repository_root: str | Path,
    format_id: str,
    capability: str,
    *,
    registry_path: str | Path | None,
    output_directory: str | Path | None,
) -> tuple[Path, Path]:
    context = load_mtgo_context(
        repository_root,
        format_id,
        capability,
        registry_path=registry_path,
    )
    configured = context.paths["statistics"] / "pickup"
    output = Path(output_directory).resolve() if output_directory is not None else configured
    return configured, output


def _record_identity(record: Mapping[str, Any], rules) -> dict[str, Any]:
    result = classify_deck(
        rules,
        {
            "main_deck": record.get("main_deck", []),
            "sideboard": record.get("side_deck", []),
        },
    )
    if result.status != "classified":
        raise MTGOPickupError(
            f"Pickup record could not reproduce its classified identity: {result.status}"
        )
    return {
        "archetype_id": result.archetype_id,
        "subtype_id": result.subtype_id,
        "subtype": result.subtype_name,
    }


def _candidate_documents(
    events,
    rules,
    end_monday: date,
    known: set[str],
    *,
    stable_ids: bool = False,
):
    week_label = iso_week_label(end_monday)
    end_sunday = end_monday + timedelta(days=6)
    base_pack, d99 = stats.build_base_pack(events, rules, end_monday)
    top8_records = [record for record in week_records(events, rules, end_monday) if record["is_top8"]]

    deduplicated: dict[tuple[str, object], dict[str, Any]] = {}
    for record in top8_records:
        if record["archetype"] == "Unknown":
            continue
        key = (record["archetype_id"], deck_fingerprint(record))
        if key not in deduplicated:
            deduplicated[key] = record
        else:
            deduplicated[key] = better_record(deduplicated[key], record)

    existing_picks: list[dict[str, Any]] = []
    new_picks: list[dict[str, Any]] = []
    for record in deduplicated.values():
        archetype = record["archetype"]
        identity_key = record["archetype_id"] if stable_ids else archetype
        cards = record_deck_cards(record)
        entry = {
            "archetype": archetype,
            "player": record["player"],
            "final_rank": record["final_rank"] if record["final_rank"] != 9999 else None,
            "swiss_score": record["swiss_score"],
            "player_count": record["player_count"],
            "starttime": record["starttime"],
            "deviation": deck_deviation(
                record,
                base_pack.get(record["archetype_id"]),
                d99,
            ),
            "source": "new" if identity_key not in known else "existing",
            "approved": False,
            "comment_zh": "",
            "comment_en": "",
            "main_deck": cards["main_deck"],
            "side_deck": cards["side_deck"],
        }
        if stable_ids:
            entry = {**_record_identity(record, rules), **entry}
        (new_picks if identity_key not in known else existing_picks).append(entry)

    existing_picks.sort(
        key=lambda entry: (entry["deviation"] is None, -(entry["deviation"] or 0))
    )
    new_picks.sort(
        key=lambda entry: (entry["final_rank"] is None, entry["final_rank"] or 9999)
    )
    candidates = {
        "week": week_label,
        "start": end_monday.isoformat(),
        "end": end_sunday.isoformat(),
        "note": "编辑说明：删掉不想 pickup 的条目；保留的把 approved 改为 true 并填 comment_zh；"
        "existing 类已按偏离度从高到低排列，从上往下筛即可。"
        "偏离度可疑时对照同目录 base_reference_*.yaml 逐卡核对。",
        "existing_changes": existing_picks,
        "new_archetypes": new_picks,
    }
    base_reference = {
        "week": week_label,
        "base_weeks": 4,
        "global_d99": round(d99, 4),
        "note": "每套牌最近 4 周架空平均构筑（Core=常备/Flex=自选），"
        "mean_qty 为均值张数，rate 为出现率（权重）。用于人工核对某副牌偏离度是否合理。",
        "archetypes": {},
    }
    for base in sorted(base_pack.values(), key=lambda item: item["name"]):
        archetype = base["name"]
        base_reference["archetypes"][archetype] = {
            "sample_size": base["sample_size"],
            "core": base["core"],
            "flex": base["flex"],
            "medoid": (base["medoid_display"] or {}).get("player")
            if base["medoid_display"]
            else None,
        }
    return candidates, base_reference, len(top8_records), len(deduplicated)


def generate_candidates(
    repository_root: str | Path,
    format_id: str,
    *,
    today: date | None = None,
    registry_path: str | Path | None = None,
    output_directory: str | Path | None = None,
    known_file: str | Path | None = None,
    preserve_existing: bool = False,
) -> dict[str, Any] | None:
    """Generate human-reviewed Pickup candidates for one explicit MTGO format."""

    configured, output = _pickup_directories(
        repository_root,
        format_id,
        "weekly_pickup",
        registry_path=registry_path,
        output_directory=output_directory,
    )
    rules = load_rules_for_format(repository_root, format_id, registry_path=registry_path)
    events = stats.load_all_events(repository_root, format_id, registry_path=registry_path)
    end_monday = stats.latest_complete_week(events, today=today)
    if end_monday is None:
        return None

    known_path = Path(known_file) if known_file is not None else configured / "known_archetypes.json"
    stable_ids = format_id == "modern"
    known = load_known(known_path, stable_ids=stable_ids)
    first_run = known is None
    if known is None:
        known = archetypes_in_window(
            events,
            rules,
            end_monday,
            INITIAL_KNOWN_WEEKS,
            stable_ids=stable_ids,
        )
    candidates, base_reference, top8_count, deduplicated_count = _candidate_documents(
        events,
        rules,
        end_monday,
        known,
        stable_ids=stable_ids,
    )

    output.mkdir(parents=True, exist_ok=True)
    week = candidates["week"]
    candidate_path = output / f"candidates_{week}.yaml"
    base_path = output / f"base_reference_{week}.yaml"
    if preserve_existing and candidate_path.exists():
        return {
            "week": week,
            "candidate_path": candidate_path,
            "base_reference_path": base_path,
            "existing_count": len(candidates["existing_changes"]),
            "new_count": len(candidates["new_archetypes"]),
            "top8_count": top8_count,
            "deduplicated_count": deduplicated_count,
            "first_run": first_run,
            "skipped_existing": True,
        }
    candidate_path.write_text(
        yaml.dump(
            candidates,
            allow_unicode=True,
            sort_keys=False,
            width=1000,
            default_flow_style=False,
        ),
        encoding="utf-8",
        newline="\n",
    )
    base_path.write_text(
        yaml.dump(
            base_reference,
            allow_unicode=True,
            sort_keys=False,
            width=1000,
            default_flow_style=False,
        ),
        encoding="utf-8",
        newline="\n",
    )
    return {
        "week": week,
        "candidate_path": candidate_path,
        "base_reference_path": base_path,
        "existing_count": len(candidates["existing_changes"]),
        "new_count": len(candidates["new_archetypes"]),
        "top8_count": top8_count,
        "deduplicated_count": deduplicated_count,
        "first_run": first_run,
        "skipped_existing": False,
    }


def _approved_entries(document: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    entries = document.get(key, [])
    if not isinstance(entries, list):
        raise MTGOPickupError(f"{key} must be a list")
    approved: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise MTGOPickupError(f"{key} entries must be mappings")
        if not entry.get("approved"):
            continue
        published_entry = {
                "archetype": entry["archetype"],
                "player": entry.get("player"),
                "final_rank": entry.get("final_rank"),
                "swiss_score": entry.get("swiss_score"),
                "player_count": entry.get("player_count"),
                "starttime": entry.get("starttime"),
                "deviation": entry.get("deviation"),
                "source": entry.get("source"),
                "comment_zh": (entry.get("comment_zh") or "").strip(),
                "comment_en": (entry.get("comment_en") or "").strip(),
                "main_deck": entry.get("main_deck", []),
                "side_deck": entry.get("side_deck", []),
            }
        if "archetype_id" in entry:
            published_entry = {
                "archetype_id": entry["archetype_id"],
                "subtype_id": entry.get("subtype_id"),
                "subtype": entry.get("subtype"),
                **published_entry,
            }
        approved.append(published_entry)
    return approved


def publish(
    repository_root: str | Path,
    format_id: str,
    *,
    today: date | None = None,
    registry_path: str | Path | None = None,
    output_directory: str | Path | None = None,
    candidate_directory: str | Path | None = None,
    state_directory: str | Path | None = None,
) -> dict[str, Any] | None:
    """Publish only manually approved Pickup rows and update its catalog/state."""

    configured, output = _pickup_directories(
        repository_root,
        format_id,
        "weekly_pickup",
        registry_path=registry_path,
        output_directory=output_directory,
    )
    load_mtgo_context(
        repository_root,
        format_id,
        "catalog_generation",
        registry_path=registry_path,
    )
    rules = load_rules_for_format(repository_root, format_id, registry_path=registry_path)
    events = stats.load_all_events(repository_root, format_id, registry_path=registry_path)
    end_monday = stats.latest_complete_week(events, today=today)
    if end_monday is None:
        return None

    week = iso_week_label(end_monday)
    candidate_root = Path(candidate_directory) if candidate_directory is not None else output
    candidate_path = candidate_root / f"candidates_{week}.yaml"
    if not candidate_path.is_file():
        return None
    document = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise MTGOPickupError(f"{candidate_path}: expected a mapping")
    existing = _approved_entries(document, "existing_changes")
    new_archetypes = _approved_entries(document, "new_archetypes")
    if not existing and not new_archetypes:
        return None

    output.mkdir(parents=True, exist_ok=True)
    published = versioned(
        {
            "format": format_id,
            "source": SOURCE_ID,
            "week": week,
            "start": document.get("start"),
            "end": document.get("end"),
            "existing_changes": existing,
            "new_archetypes": new_archetypes,
        }
    )
    published_path = output / f"{week}.json"
    published_path.write_text(
        json.dumps(published, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )

    state = Path(state_directory) if state_directory is not None else configured
    index_source = state / "index.json"
    if index_source.is_file():
        index_document = json.loads(index_source.read_text(encoding="utf-8"))
        entries = index_document.get("weeks", [])
    else:
        entries = []
    if not isinstance(entries, list):
        raise MTGOPickupError(f"{index_source}: weeks must be a list")
    entries = [entry for entry in entries if entry.get("week") != week]
    entries.append(
        {
            "week": week,
            "file": f"{week}.json",
            "start": document.get("start"),
            "end": document.get("end"),
            "existing_count": len(existing),
            "new_count": len(new_archetypes),
        }
    )
    entries.sort(key=lambda entry: entry["week"], reverse=True)
    index_path = output / "index.json"
    index_path.write_text(
        json.dumps(
            versioned({"format": format_id, "source": SOURCE_ID, "weeks": entries}),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
        newline="\n",
    )

    known_source = state / "known_archetypes.json"
    stable_ids = format_id == "modern"
    known = load_known(known_source, stable_ids=stable_ids) or set()
    if not known_source.is_file():
        known |= archetypes_in_window(
            events,
            rules,
            end_monday,
            INITIAL_KNOWN_WEEKS,
            stable_ids=stable_ids,
        )
    known |= archetypes_in_window(
        events,
        rules,
        end_monday,
        1,
        stable_ids=stable_ids,
    )
    known_path = output / "known_archetypes.json"
    known_document = {"known_ids": sorted(known)} if stable_ids else {"known": sorted(known)}
    known_path.write_text(
        json.dumps(known_document, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    return {
        "week": week,
        "published_path": published_path,
        "index_path": index_path,
        "known_path": known_path,
        "existing_count": len(existing),
        "new_count": len(new_archetypes),
    }


def initialize_known_state(
    repository_root: str | Path,
    format_id: str,
    *,
    today: date | None = None,
    registry_path: str | Path | None = None,
    output_directory: str | Path | None = None,
) -> Path | None:
    """Explicitly bootstrap stable Pickup state without publishing a weekly selection."""

    configured, output = _pickup_directories(
        repository_root,
        format_id,
        "weekly_pickup",
        registry_path=registry_path,
        output_directory=output_directory,
    )
    load_mtgo_context(
        repository_root,
        format_id,
        "catalog_generation",
        registry_path=registry_path,
    )
    destination = output / "known_archetypes.json"
    if destination.exists():
        raise MTGOPickupError(f"{destination}: known state already exists")
    rules = load_rules_for_format(repository_root, format_id, registry_path=registry_path)
    events = stats.load_all_events(repository_root, format_id, registry_path=registry_path)
    end_monday = stats.latest_complete_week(events, today=today)
    if end_monday is None:
        return None
    stable_ids = format_id == "modern"
    known = archetypes_in_window(
        events,
        rules,
        end_monday,
        INITIAL_KNOWN_WEEKS,
        stable_ids=stable_ids,
    )
    document = {"known_ids": sorted(known)} if stable_ids else {"known": sorted(known)}
    output.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(document, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    return destination


def generate_hierarchy_catalog(
    repository_root: str | Path,
    format_id: str,
    *,
    rules_updated: str | None = None,
    registry_path: str | Path | None = None,
    output_directory: str | Path | None = None,
) -> Path:
    """Generate the complete maintained parent/subtype catalog for one format."""

    context = load_mtgo_context(
        repository_root,
        format_id,
        "catalog_generation",
        registry_path=registry_path,
    )
    rules = load_rules_for_format(repository_root, format_id, registry_path=registry_path)
    if rules_updated is None:
        rules_updated = rules_last_commit_iso(
            context.repository_root,
            context.paths["rules"],
        )
    hierarchy = matchup.build_matchup_hierarchy(rules)
    parents = hierarchy["parents"]
    leaves = hierarchy["leaves"]
    document = versioned(
        {
            "format": format_id,
            "source": SOURCE_ID,
            "rules_updated": rules_updated,
            "summary": {
                "parents": len(parents),
                "leaves": len(leaves),
                "expandable_parents": sum(item["expandable"] for item in parents),
            },
            **hierarchy,
        }
    )
    output = (
        Path(output_directory).resolve()
        if output_directory is not None
        else context.paths["statistics"]
    )
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "archetype_hierarchy.json"
    destination.write_text(
        json.dumps(document, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    return destination


def _matchup_coverage(
    context,
    *,
    registry_path: str | Path | None = None,
) -> dict[str, int]:
    events = stats.load_all_events(
        context.repository_root,
        context.definition.id,
        registry_path=registry_path,
    )
    official_ids = {
        str(event.get("event_id"))
        for _event_date, event in events
        if event.get("event_id") is not None
    }
    archive_ids: set[str] = set()
    for path in sorted(context.paths["matches"].glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        event_id = document.get("event_id")
        if event_id is not None:
            archive_ids.add(str(event_id))
    overlap = official_ids & archive_ids
    return {
        "official_events": len(official_ids),
        "events_with_archives": len(overlap),
        "events_without_archives": len(official_ids - archive_ids),
        "stored_archives": len(archive_ids),
        "archives_outside_official_events": len(archive_ids - official_ids),
    }


def rules_last_commit_iso(
    repository_root: str | Path,
    rules_file: str | Path,
    *,
    runner: Callable[..., Any] = subprocess.run,
) -> str | None:
    root = Path(repository_root).resolve()
    rules = Path(rules_file).resolve()
    try:
        relative = rules.relative_to(root).as_posix()
        result = runner(
            ["git", "log", "-1", "--format=%cI", "--", relative],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        value = result.stdout.strip()
        return value or None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def generate_metadata(
    repository_root: str | Path,
    format_id: str,
    *,
    data_updated: datetime | str | None = None,
    rules_updated: str | None = None,
    registry_path: str | Path | None = None,
    output_directory: str | Path | None = None,
) -> Path:
    """Generate format-specific MTGO metadata after capability authorization."""

    context = load_mtgo_context(
        repository_root,
        format_id,
        "metadata_generation",
        registry_path=registry_path,
    )
    if rules_updated is None:
        rules_updated = rules_last_commit_iso(
            context.repository_root,
            context.paths["rules"],
        )
    if data_updated is None:
        data_updated_value = datetime.now(timezone.utc).isoformat(timespec="seconds")
    elif isinstance(data_updated, datetime):
        data_updated_value = data_updated.isoformat(timespec="seconds")
    else:
        data_updated_value = data_updated
    document = versioned(
        {
            "format": format_id,
            "source": SOURCE_ID,
            "rules_updated": rules_updated,
            "data_updated": data_updated_value,
        }
    )
    document.update(
        {
            "statistics_catalog": "index.json",
            "matchup_catalog": "matchup_index.json",
            "hierarchy_catalog": "archetype_hierarchy.json",
            "pickup_catalog": (
                "pickup/index.json"
                if (context.paths["statistics"] / "pickup" / "index.json").is_file()
                else None
            ),
            "matchup_source": "Videre",
            "matchup_coverage": _matchup_coverage(
                context,
                registry_path=registry_path,
            ),
        }
    )
    output = (
        Path(output_directory).resolve()
        if output_directory is not None
        else context.paths["statistics"]
    )
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "meta.json"
    destination.write_text(
        json.dumps(document, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    return destination


__all__ = [
    "INITIAL_KNOWN_WEEKS",
    "MTGOPickupError",
    "archetypes_in_window",
    "better_record",
    "deck_deviation",
    "deck_fingerprint",
    "generate_candidates",
    "generate_hierarchy_catalog",
    "generate_metadata",
    "initialize_known_state",
    "iso_week_label",
    "load_known",
    "publish",
    "record_deck_cards",
    "rules_last_commit_iso",
    "week_records",
]
