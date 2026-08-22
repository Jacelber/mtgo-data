"""Format-aware MTGO Weekly Pickup, metadata, and catalog helpers."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml

from mtgmeta.classifier import classify_deck
from mtgmeta.public_contract import versioned

from . import load_mtgo_context
from . import matchup
from . import stats
from .normalize import load_rules_for_format
from .top8 import classifier_digest
from .week_lifecycle import is_sealed, provisional_through, seal_on


SOURCE_ID = "mtgo"
INITIAL_KNOWN_WEEKS = 12
PICKUP_WEEK_SCHEMA_VERSION = "1.1.0"
DEFAULT_POLICY_PATH = Path("configs/mtgo_pickup_policy.yaml")


class MTGOPickupError(RuntimeError):
    """Raised when Pickup or publication metadata cannot be produced safely."""


def document_digest(value: Any) -> str:
    """Return the canonical digest used to bind private review inputs."""

    material = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def load_pickup_policy(
    repository_root: str | Path,
    policy_file: str | Path | None = None,
) -> dict[str, Any]:
    """Load the maintained private candidate-screening policy."""

    path = (
        Path(policy_file)
        if policy_file is not None
        else Path(repository_root) / DEFAULT_POLICY_PATH
    )
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise MTGOPickupError(f"{path}: Pickup policy could not be loaded") from exc
    if not isinstance(document, dict) or document.get("schema_version") != "1.0":
        raise MTGOPickupError(f"{path}: unsupported Pickup policy")

    thresholds = document.get("thresholds")
    required_thresholds = {
        "share_increase_pp",
        "return_share",
        "build_shift",
        "build_reference_minimum",
        "new_card_review_weeks",
    }
    if not isinstance(thresholds, dict) or not required_thresholds <= thresholds.keys():
        raise MTGOPickupError(f"{path}: incomplete Pickup thresholds")
    if thresholds["share_increase_pp"] != 5:
        raise MTGOPickupError(f"{path}: share increase must remain five points")
    if thresholds["return_share"] != 0.03:
        raise MTGOPickupError(f"{path}: return share must remain three percent")
    if thresholds["build_shift"] != 20:
        raise MTGOPickupError(f"{path}: build shift must remain twenty points")
    if thresholds["build_reference_minimum"] != stats.MIN_SAMPLE:
        raise MTGOPickupError(f"{path}: build reference minimum is incompatible")
    if thresholds["new_card_review_weeks"] != 2:
        raise MTGOPickupError(f"{path}: new-card review window must remain two weeks")

    continuity = document.get("identity_continuity")
    if not isinstance(continuity, dict):
        raise MTGOPickupError(f"{path}: identity_continuity must be a mapping")
    release_sets = document.get("release_sets")
    if not isinstance(release_sets, list):
        raise MTGOPickupError(f"{path}: release_sets must be a list")
    for item in release_sets:
        if not isinstance(item, dict):
            raise MTGOPickupError(f"{path}: release set must be a mapping")
        try:
            date.fromisoformat(str(item["arena_release_date"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise MTGOPickupError(f"{path}: invalid Arena release date") from exc
        cards = item.get("cards")
        if not isinstance(cards, list) or any(
            not isinstance(card, str) or not card.strip() for card in cards
        ):
            raise MTGOPickupError(f"{path}: release card manifest must be strings")
        if len(cards) != len(set(cards)):
            raise MTGOPickupError(f"{path}: release card manifest contains duplicates")
    return document


def iso_week_label(monday: date) -> str:
    year, week, _ = monday.isocalendar()
    return f"{year}-W{week:02d}"


def week_records(
    events,
    rules,
    end_monday: date,
    *,
    processed_events: Mapping[int, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    end_sunday = end_monday + timedelta(days=6)
    records: list[dict[str, Any]] = []
    for event_date, event in events:
        if end_monday <= event_date <= end_sunday:
            event_id = str(event.get("event_id", "")).strip()
            if not event_id.isdigit():
                raise MTGOPickupError("Pickup source event has no numeric event_id")
            processed = (
                processed_events[id(event)]
                if processed_events is not None
                else stats.process_event(event, rules)
            )
            for record_index, record in enumerate(processed["records"]):
                records.append(
                    {
                        **record,
                        "event_id": event_id,
                        "deck_id": _candidate_deck_id(
                            event_id,
                            record_index,
                            record,
                        ),
                    }
                )
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


def deck_fingerprint(
    record,
) -> tuple[tuple[tuple[str, int], ...], tuple[tuple[str, int], ...]]:
    main = tuple(
        (card["name"], card["qty"])
        for card in stats.merge_cards(record.get("main_deck", []))
    )
    side = tuple(
        (card["name"], card["qty"])
        for card in stats.merge_cards(record.get("side_deck", []))
    )
    return main, side


def _deck_fingerprint_sha256(record: Mapping[str, Any]) -> str:
    material = json.dumps(
        deck_fingerprint(record),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _candidate_deck_id(
    event_id: str,
    record_index: int,
    record: Mapping[str, Any],
) -> str:
    """Build a stable pseudonymous candidate identity without player data."""

    material = json.dumps(
        {
            "event_id": event_id,
            "record_index": record_index,
            "deck_fingerprint_sha256": _deck_fingerprint_sha256(record),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def better_record(first, second):
    first_rank = first["final_rank"] if first["final_rank"] != 9999 else 9999
    second_rank = second["final_rank"] if second["final_rank"] != 9999 else 9999
    if first_rank != second_rank:
        return first if first_rank < second_rank else second
    if first["player_count"] != second["player_count"]:
        return first if first["player_count"] > second["player_count"] else second
    return first if first["starttime"] >= second["starttime"] else second


def _best_record(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        raise MTGOPickupError("cannot select a representative from no records")
    best = records[0]
    for record in records[1:]:
        best = better_record(best, record)
    return best


def _active_release_sets(
    policy: Mapping[str, Any],
    monday: date,
) -> list[Mapping[str, Any]]:
    review_weeks = int(policy["thresholds"]["new_card_review_weeks"])
    active: list[Mapping[str, Any]] = []
    for item in policy["release_sets"]:
        release_date = date.fromisoformat(str(item["arena_release_date"]))
        release_monday = release_date - timedelta(days=release_date.weekday())
        if release_monday <= monday < release_monday + timedelta(weeks=review_weeks):
            if item.get("manifest_status") != "frozen" or not item.get("cards"):
                raise MTGOPickupError(
                    f"{item.get('code', '?')}: active release has no frozen card manifest"
                )
            active.append(item)
    return active


def _continuity_aliases(
    policy: Mapping[str, Any],
    format_id: str,
    archetype_id: str,
) -> set[str]:
    format_map = policy.get("identity_continuity", {}).get(format_id, {})
    item = format_map.get(archetype_id, {}) if isinstance(format_map, dict) else {}
    aliases = item.get("known_as", []) if isinstance(item, dict) else []
    if not isinstance(aliases, list) or any(not isinstance(value, str) for value in aliases):
        raise MTGOPickupError(
            f"identity continuity for {format_id}/{archetype_id} is invalid"
        )
    return set(aliases)


def _is_known_record(
    record: Mapping[str, Any],
    known: set[str],
    policy: Mapping[str, Any],
    format_id: str,
) -> bool:
    keys = {
        str(record["archetype_id"]),
        str(record["archetype"]),
        *_continuity_aliases(policy, format_id, str(record["archetype_id"])),
    }
    return bool(keys & known)


def _records_in_period(
    events,
    rules,
    start: date,
    end: date,
    *,
    processed_events: Mapping[int, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for event_date, event in events:
        if start <= event_date <= end:
            processed = (
                processed_events[id(event)]
                if processed_events is not None
                else stats.process_event(event, rules)
            )
            records.extend(processed["records"])
    return records


def _parent_high_score_counts(
    records: list[dict[str, Any]],
) -> tuple[dict[str, int], int]:
    counts: dict[str, int] = {}
    denominator = 0
    for record in records:
        if not record["is_high_score"]:
            continue
        denominator += 1
        archetype_id = str(record["archetype_id"])
        counts[archetype_id] = counts.get(archetype_id, 0) + 1
    return counts, denominator


def _manifest_card_names(item: Mapping[str, Any]) -> set[str]:
    names: set[str] = set()
    for value in item["cards"]:
        name = stats.normalize_legacy_card_name(str(value))
        names.add(name)
        names.add(name.split(" // ", 1)[0])
    return names


def _new_card_evidence(
    record: Mapping[str, Any],
    release_set: Mapping[str, Any],
) -> list[dict[str, Any]]:
    manifest = _manifest_card_names(release_set)
    quantities: dict[str, dict[str, int]] = {}
    for zone, output_field in (("main_deck", "main_qty"), ("side_deck", "side_qty")):
        for card in stats.merge_cards(record.get(zone, [])):
            name = stats.normalize_legacy_card_name(card["name"])
            if name not in manifest:
                continue
            item = quantities.setdefault(name, {"main_qty": 0, "side_qty": 0})
            item[output_field] += int(card["qty"])
    return [
        {"name": name, **quantities[name]}
        for name in sorted(quantities)
    ]


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
    output = (
        Path(output_directory).resolve() if output_directory is not None else configured
    )
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
    identity_id = (
        result.archetype_id
        if result.subtype_id is None
        else f"{result.archetype_id}/{result.subtype_id}"
    )
    return {
        "identity_id": identity_id,
        "archetype_id": result.archetype_id,
        "subtype_id": result.subtype_id,
        "subtype": result.subtype_name,
    }


def _entry_for_record(
    record: Mapping[str, Any],
    rules,
    *,
    known: bool,
    parent_base: Mapping[str, Any] | None,
) -> dict[str, Any]:
    cards = record_deck_cards(record)
    landing_category = "new_technology" if known else "new_deck"
    return {
        **_record_identity(record, rules),
        "event_id": record["event_id"],
        "deck_id": record["deck_id"],
        "deck_fingerprint_sha256": _deck_fingerprint_sha256(record),
        "archetype": record["archetype"],
        "player": record["player"],
        "final_rank": (
            record["final_rank"] if record["final_rank"] != 9999 else None
        ),
        "swiss_score": record["swiss_score"],
        "player_count": record["player_count"],
        "starttime": record["starttime"],
        "deviation": deck_deviation(record, parent_base),
        "source": "existing" if known else "new",
        "candidate_reasons": [],
        "approved": False,
        "comment_zh": "",
        "comment_en": "",
        "landing": {
            "category": landing_category,
            "order": None,
            "headline_zh": "",
            "headline_en": "",
            "positioning_zh": "",
            "positioning_en": "",
            "featured_cards": [],
        },
        "main_deck": cards["main_deck"],
        "side_deck": cards["side_deck"],
    }


def _prefer_new_card_record(
    first: tuple[dict[str, Any], list[dict[str, Any]]],
    second: tuple[dict[str, Any], list[dict[str, Any]]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    first_record, _first_cards = first
    second_record, _second_cards = second
    result_fields = ("final_rank", "player_count", "starttime")
    if all(first_record.get(field) == second_record.get(field) for field in result_fields):
        return min(
            (first, second),
            key=lambda item: (
                str(item[0].get("event_id", "")),
                str(item[0].get("deck_id", "")),
            ),
        )
    return first if better_record(first_record, second_record) is first_record else second


def _prefer_build_shift_record(
    first: tuple[dict[str, Any], dict[str, Any]],
    second: tuple[dict[str, Any], dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    first_record, first_reason = first
    second_record, second_reason = second
    if first_reason["score"] != second_reason["score"]:
        return first if first_reason["score"] > second_reason["score"] else second
    return first if better_record(first_record, second_record) is first_record else second


def _candidate_documents(
    events,
    rules,
    end_monday: date,
    known: set[str],
    policy: Mapping[str, Any],
    format_id: str,
    *,
    stable_ids: bool = False,
):
    week_label = iso_week_label(end_monday)
    end_sunday = end_monday + timedelta(days=6)
    reference_monday = end_monday - timedelta(weeks=1)
    reference_start = end_monday - timedelta(weeks=4)
    reference_end = end_monday - timedelta(days=1)
    processed_events = {
        id(event): stats.process_event(event, rules)
        for _event_date, event in events
    }
    current_records = week_records(
        events,
        rules,
        end_monday,
        processed_events=processed_events,
    )
    all_top8_records = [record for record in current_records if record["is_top8"]]
    top8_records = [
        record
        for record in all_top8_records
        if record["archetype"] != "Unknown"
    ]
    reference_records = _records_in_period(
        events,
        rules,
        reference_start,
        reference_end,
        processed_events=processed_events,
    )
    historical_records = _records_in_period(
        events,
        rules,
        date.min,
        reference_start - timedelta(days=1),
        processed_events=processed_events,
    )
    parent_bases, d99 = stats.build_base_pack(
        events,
        rules,
        reference_monday,
        processed_events=processed_events,
    )
    subtype_bases, _subtype_d99 = stats.build_subtype_base_pack(
        events,
        rules,
        reference_monday,
        processed_events=processed_events,
    )
    thresholds = policy["thresholds"]
    active_sets = _active_release_sets(policy, end_monday)
    parent_definitions = {item.id: item for item in rules.archetypes}

    by_parent: dict[str, list[dict[str, Any]]] = {}
    for record in top8_records:
        by_parent.setdefault(str(record["archetype_id"]), []).append(record)

    selections: list[tuple[dict[str, Any], dict[str, Any]]] = []

    current_counts, current_denominator = _parent_high_score_counts(current_records)
    reference_counts, reference_denominator = _parent_high_score_counts(reference_records)
    historical_parent_ids = {
        str(record["archetype_id"])
        for record in historical_records
        if record["archetype"] != "Unknown"
    }
    for parent_id, records in by_parent.items():
        representative = _best_record(records)
        if not _is_known_record(representative, known, policy, format_id):
            continue
        current_count = current_counts.get(parent_id, 0)
        reference_count = reference_counts.get(parent_id, 0)
        current_share = (
            current_count / current_denominator if current_denominator else 0.0
        )
        reference_share = (
            reference_count / reference_denominator if reference_denominator else 0.0
        )
        delta_pp = (current_share - reference_share) * 100
        if reference_count > 0 and delta_pp >= thresholds["share_increase_pp"]:
            selections.append(
                (
                    representative,
                    {
                        "type": "share_increase",
                        "current_high_score_count": current_count,
                        "current_high_score_denominator": current_denominator,
                        "current_share": round(current_share, 4),
                        "reference_high_score_count": reference_count,
                        "reference_high_score_denominator": reference_denominator,
                        "reference_share": round(reference_share, 4),
                        "delta_pp": round(delta_pp, 2),
                    },
                )
            )
        elif (
            reference_count == 0
            and parent_id in historical_parent_ids
            and current_share >= thresholds["return_share"]
        ):
            selections.append(
                (
                    representative,
                    {
                        "type": "return",
                        "current_high_score_count": current_count,
                        "current_high_score_denominator": current_denominator,
                        "current_share": round(current_share, 4),
                        "reference_high_score_count": 0,
                        "reference_high_score_denominator": reference_denominator,
                        "reference_share": 0.0,
                    },
                )
            )

    new_card_groups: dict[
        tuple[str, str, tuple[str, ...]],
        tuple[dict[str, Any], list[dict[str, Any]]],
    ] = {}
    for record in top8_records:
        for release_set in active_sets:
            evidence = _new_card_evidence(record, release_set)
            if not evidence:
                continue
            key = (
                str(record["archetype_id"]),
                str(release_set["code"]),
                tuple(item["name"] for item in evidence),
            )
            candidate = (record, evidence)
            if key in new_card_groups:
                candidate = _prefer_new_card_record(new_card_groups[key], candidate)
            new_card_groups[key] = candidate
    release_by_code = {str(item["code"]): item for item in active_sets}
    for (_parent_id, set_code, _package), (record, evidence) in new_card_groups.items():
        release_set = release_by_code[set_code]
        selections.append(
            (
                record,
                {
                    "type": "new_card",
                    "set_code": set_code,
                    "arena_release_date": str(release_set["arena_release_date"]),
                    "release_source_url": release_set["release_source_url"],
                    "distinct_card_count": len(evidence),
                    "main_card_count": sum(item["main_qty"] for item in evidence),
                    "side_card_count": sum(item["side_qty"] for item in evidence),
                    "cards": evidence,
                },
            )
        )

    for parent_id, records in by_parent.items():
        representative = _best_record(records)
        if _is_known_record(representative, known, policy, format_id):
            continue
        prior_record_count = sum(
            1
            for record in reference_records + historical_records
            if str(record["archetype_id"]) == parent_id
        )
        selections.append(
            (
                representative,
                {
                    "type": "new_archetype",
                    "known_state_match": False,
                    "continuity_alias_match": False,
                    "prior_record_count_under_current_classifier": prior_record_count,
                },
            )
        )

    build_groups: dict[
        str,
        tuple[dict[str, Any], dict[str, Any]],
    ] = {}
    for record in top8_records:
        if not _is_known_record(record, known, policy, format_id):
            continue
        parent_id = str(record["archetype_id"])
        parent = parent_definitions[parent_id]
        subtype_id = record.get("subtype_id")
        if subtype_id is not None:
            identity_level = "subtype"
            identity_id = f"{parent_id}/{subtype_id}"
            base = subtype_bases.get((parent_id, subtype_id))
        elif not parent.subtypes:
            identity_level = "parent"
            identity_id = parent_id
            base = parent_bases.get(parent_id)
        else:
            continue
        if not base or base["sample_size"] < thresholds["build_reference_minimum"]:
            continue
        score = deck_deviation(record, base)
        if score is None or score < thresholds["build_shift"]:
            continue
        reason = {
            "type": "build_shift",
            "identity_level": identity_level,
            "identity_id": identity_id,
            "reference_sample_size": base["sample_size"],
            "score": score,
            "difference": stats.deck_diff(stats.deck_vector(record), base["mean"]),
        }
        build_candidate = (record, reason)
        if identity_id in build_groups:
            build_candidate = _prefer_build_shift_record(
                build_groups[identity_id], build_candidate
            )
        build_groups[identity_id] = build_candidate
    selections.extend(build_groups.values())

    entries: dict[tuple[str, str], dict[str, Any]] = {}
    for record, reason in selections:
        entry_key = (str(record["event_id"]), str(record["deck_id"]))
        known_record = _is_known_record(record, known, policy, format_id)
        entry = entries.setdefault(
            entry_key,
            _entry_for_record(
                record,
                rules,
                known=known_record,
                parent_base=parent_bases.get(str(record["archetype_id"])),
            ),
        )
        reason_key = json.dumps(reason, ensure_ascii=False, sort_keys=True)
        existing_reason_keys = {
            json.dumps(item, ensure_ascii=False, sort_keys=True)
            for item in entry["candidate_reasons"]
        }
        if reason_key not in existing_reason_keys:
            entry["candidate_reasons"].append(reason)

    reason_order = {
        "share_increase": 2,
        "return": 2,
        "new_card": 3,
        "new_archetype": 4,
        "build_shift": 5,
    }
    for entry in entries.values():
        entry["candidate_reasons"].sort(
            key=lambda reason: (reason_order[reason["type"]], reason["type"])
        )
    existing_picks = [entry for entry in entries.values() if entry["source"] == "existing"]
    new_picks = [entry for entry in entries.values() if entry["source"] == "new"]
    sort_key = lambda entry: (
        min(reason_order[item["type"]] for item in entry["candidate_reasons"]),
        entry["final_rank"] is None,
        entry["final_rank"] or 9999,
        -entry["player_count"],
        entry["archetype"],
    )
    existing_picks.sort(key=sort_key)
    new_picks.sort(key=sort_key)
    candidates = {
        "week": week_label,
        "start": end_monday.isoformat(),
        "end": end_sunday.isoformat(),
        "selection_policy": {
            "schema_version": policy["schema_version"],
            "share_increase_pp": thresholds["share_increase_pp"],
            "return_share": thresholds["return_share"],
            "build_shift": thresholds["build_shift"],
            "build_reference_minimum": thresholds["build_reference_minimum"],
            "active_release_sets": [item["code"] for item in active_sets],
        },
        "machine_fact_digest": None,
        "note": "Machine candidates are evidence aids. The reviewer may select none, replace a candidate, and freely rewrite or remove all editorial copy.",
        "existing_changes": existing_picks,
        "new_archetypes": new_picks,
    }
    base_reference = {
        "week": week_label,
        "base_weeks": 4,
        "base_start": reference_start.isoformat(),
        "base_end": reference_end.isoformat(),
        "global_d99": round(d99, 4),
        "note": "The comparison base uses the four complete weeks before the review week. Parent identities without maintained subtypes use a parent base; maintained subtypes use their own base.",
        "archetypes": {},
        "subtypes": {},
    }
    for base in sorted(parent_bases.values(), key=lambda item: item["name"]):
        archetype = base["name"]
        base_reference["archetypes"][archetype] = {
            "sample_size": base["sample_size"],
            "core": base["core"],
            "flex": base["flex"],
            "medoid": (base["medoid_display"] or {}).get("player")
            if base["medoid_display"]
            else None,
        }
    for (parent_id, subtype_id), base in sorted(subtype_bases.items()):
        base_reference["subtypes"][f"{parent_id}/{subtype_id}"] = {
            "sample_size": base["sample_size"],
            "core": base["core"],
            "flex": base["flex"],
            "medoid": (base["medoid_display"] or {}).get("player")
            if base["medoid_display"]
            else None,
        }
    return candidates, base_reference, len(all_top8_records), len(entries)


def generate_candidates(
    repository_root: str | Path,
    format_id: str,
    *,
    today: date | None = None,
    registry_path: str | Path | None = None,
    output_directory: str | Path | None = None,
    known_file: str | Path | None = None,
    policy_file: str | Path | None = None,
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
    rules = load_rules_for_format(
        repository_root, format_id, registry_path=registry_path
    )
    policy = load_pickup_policy(repository_root, policy_file)
    policy_digest = document_digest(policy)
    events = stats.load_all_events(
        repository_root, format_id, registry_path=registry_path
    )
    reference_today = today or datetime.now().date()
    end_monday = stats.latest_complete_week(events, today=reference_today)
    if end_monday is None:
        return None

    known_path = (
        Path(known_file)
        if known_file is not None
        else configured / "known_archetypes.json"
    )
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
        policy,
        format_id,
        stable_ids=stable_ids,
    )
    source_event_ids = _source_event_ids(events, end_monday)
    current_classifier_digest = classifier_digest(rules)
    week_status = (
        "sealed" if is_sealed(end_monday, today=reference_today) else "provisional"
    )
    lifecycle = {
        "week_status": week_status,
        "provisional_through": provisional_through(end_monday).isoformat(),
        "seal_on": seal_on(end_monday).isoformat(),
        "source_event_ids": source_event_ids,
        "classifier_digest": current_classifier_digest,
    }
    candidates.update(lifecycle)
    base_reference.update(lifecycle)
    candidates["selection_policy_digest"] = policy_digest
    base_reference["selection_policy_digest"] = policy_digest

    output.mkdir(parents=True, exist_ok=True)
    week = candidates["week"]
    candidate_path = output / f"candidates_{week}.yaml"
    base_path = output / f"base_reference_{week}.yaml"
    existing_document: Mapping[str, Any] | None = None
    if candidate_path.exists():
        try:
            loaded = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
            if isinstance(loaded, Mapping):
                existing_document = loaded
        except (OSError, UnicodeError, yaml.YAMLError):
            existing_document = None
    same_provenance = (
        existing_document is not None
        and existing_document.get("source_event_ids") == source_event_ids
        and existing_document.get("classifier_digest") == current_classifier_digest
        and existing_document.get("selection_policy_digest") == policy_digest
    )
    if preserve_existing and same_provenance:
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
            "review_required": False,
        }
    if (
        preserve_existing
        and existing_document is not None
        and _has_manual_review(existing_document)
    ):
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
            "review_required": True,
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
        "review_required": False,
    }


def _has_manual_review(document: Mapping[str, Any]) -> bool:
    """Return whether a candidate contains decisions that must not be overwritten."""

    summary = document.get("landing_summary")
    if summary is not None:
        if not isinstance(summary, Mapping):
            return True
        if summary.get("reviewed") is True:
            return True
        items = summary.get("items", [])
        if not isinstance(items, list) or items:
            return True

    for key in ("existing_changes", "new_archetypes"):
        entries = document.get(key, [])
        if not isinstance(entries, list):
            return True
        for entry in entries:
            if not isinstance(entry, Mapping):
                return True
            if entry.get("approved") is True:
                return True
            if str(entry.get("comment_zh") or "").strip():
                return True
            if str(entry.get("comment_en") or "").strip():
                return True
            landing = entry.get("landing")
            if landing is not None:
                if not isinstance(landing, Mapping):
                    return True
                default_category = (
                    "new_technology" if key == "existing_changes" else "new_deck"
                )
                if landing.get("category", default_category) != default_category:
                    return True
                if landing.get("order") is not None:
                    return True
                for field in (
                    "headline_zh",
                    "headline_en",
                    "positioning_zh",
                    "positioning_en",
                ):
                    if str(landing.get(field) or "").strip():
                        return True
                if landing.get("featured_cards"):
                    return True
    return False


def _source_event_ids(events, monday: date) -> list[str]:
    return sorted(
        {
            str(event.get("event_id"))
            for event_date, event in events
            if monday <= event_date <= monday + timedelta(days=6)
            and event.get("event_id") is not None
        }
    )


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
        reason_types = list(
            dict.fromkeys(
                str(reason["type"])
                for reason in entry.get("candidate_reasons", [])
                if isinstance(reason, Mapping) and isinstance(reason.get("type"), str)
            )
        )
        published_entry = {
            "archetype_id": entry["archetype_id"],
            "subtype_id": entry.get("subtype_id"),
            "subtype": entry.get("subtype"),
            "event_id": str(entry["event_id"]),
            "deck_id": str(entry["deck_id"]),
            "deck_fingerprint_sha256": str(entry["deck_fingerprint_sha256"]),
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
            "reason_types": reason_types,
            "main_deck": entry.get("main_deck", []),
            "side_deck": entry.get("side_deck", []),
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
    rules = load_rules_for_format(
        repository_root, format_id, registry_path=registry_path
    )
    events = stats.load_all_events(
        repository_root, format_id, registry_path=registry_path
    )
    reference_today = today or datetime.now().date()
    end_monday = stats.latest_complete_week(events, today=reference_today)
    if end_monday is None:
        return None

    week = iso_week_label(end_monday)
    candidate_root = (
        Path(candidate_directory) if candidate_directory is not None else output
    )
    candidate_path = candidate_root / f"candidates_{week}.yaml"
    if not candidate_path.is_file():
        return None
    document = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise MTGOPickupError(f"{candidate_path}: expected a mapping")
    if document.get("source_event_ids") != _source_event_ids(events, end_monday):
        raise MTGOPickupError(
            f"{candidate_path}: Pickup candidate source events changed; regenerate and re-review"
        )
    if document.get("classifier_digest") != classifier_digest(rules):
        raise MTGOPickupError(
            f"{candidate_path}: Pickup candidate classifier changed; regenerate and re-review"
        )
    policy_digest = document_digest(load_pickup_policy(repository_root))
    if document.get("selection_policy_digest") != policy_digest:
        raise MTGOPickupError(
            f"{candidate_path}: Pickup selection policy changed; regenerate and re-review"
        )
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
            "source_event_ids": document["source_event_ids"],
            "classifier_digest": document["classifier_digest"],
            "selection_policy_digest": document["selection_policy_digest"],
            "existing_changes": existing,
            "new_archetypes": new_archetypes,
        },
        schema_version=PICKUP_WEEK_SCHEMA_VERSION,
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
    known_document = (
        {"known_ids": sorted(known)} if stable_ids else {"known": sorted(known)}
    )
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
    rules = load_rules_for_format(
        repository_root, format_id, registry_path=registry_path
    )
    events = stats.load_all_events(
        repository_root, format_id, registry_path=registry_path
    )
    reference_today = today or datetime.now().date()
    end_monday = stats.latest_complete_week(events, today=reference_today)
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
    rules = load_rules_for_format(
        repository_root, format_id, registry_path=registry_path
    )
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
            "top8_catalog": (
                "top8/index.json"
                if (context.paths["statistics"] / "top8" / "index.json").is_file()
                else None
            ),
            "completeness_catalog": (
                "completeness/index.json"
                if (
                    context.paths["statistics"] / "completeness" / "index.json"
                ).is_file()
                else None
            ),
            "pickup_catalog": (
                "pickup/index.json"
                if (context.paths["statistics"] / "pickup" / "index.json").is_file()
                else None
            ),
            "landing_document": (
                "landing/current.json"
                if (
                    context.paths["statistics"] / "landing" / "current.json"
                ).is_file()
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
    "document_digest",
    "generate_candidates",
    "generate_hierarchy_catalog",
    "generate_metadata",
    "initialize_known_state",
    "iso_week_label",
    "load_known",
    "load_pickup_policy",
    "publish",
    "record_deck_cards",
    "rules_last_commit_iso",
    "week_records",
]
