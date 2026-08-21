"""Deterministic latest-only MTGO Landing facts and reviewed Pickup features."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from mtgmeta.public_contract import versioned

from . import load_mtgo_context
from . import pickup, stats
from .normalize import load_rules_for_format
from .top8 import classifier_digest


SOURCE_ID = "mtgo"
PRODUCT_ID = "mtgo-landing"
ENVIRONMENT_THRESHOLD = 0.03
SHARE_MOVE_THRESHOLD = 0.05
EXIT_THRESHOLD = 0.05
BUILD_SHIFT_THRESHOLD = 20
DEFAULT_VISUALS_PATH = Path("configs/mtgo_landing_visuals.yaml")


class MTGOLandingError(RuntimeError):
    """Raised when Landing facts or reviewed features cannot be admitted."""


def _closed_week_monday(today: date) -> date:
    return stats.week_monday(today) - timedelta(days=7)


def _period(start: date, end: date, events, processed_events) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    event_ids: set[str] = set()
    for event_date, event in events:
        if not start <= event_date <= end:
            continue
        event_id = str(event.get("event_id", "")).strip()
        if not event_id.isdigit():
            raise MTGOLandingError("Landing source event has no numeric event_id")
        event_ids.add(event_id)
        records.extend(processed_events[id(event)]["records"])
    return {
        "start": start,
        "end": end,
        "event_ids": sorted(event_ids),
        "records": records,
    }


def _metric(count: int, denominator: int) -> dict[str, Any]:
    return {
        "count": count,
        "denominator": denominator,
        "share": round(count / denominator, 4) if denominator else None,
    }


def _population(period: Mapping[str, Any]) -> dict[str, Any]:
    records = period["records"]
    high_score_count = sum(bool(record["is_high_score"]) for record in records)
    top8_count = sum(bool(record["is_top8"]) for record in records)
    return {
        "start": period["start"].isoformat(),
        "end": period["end"].isoformat(),
        "event_ids": period["event_ids"],
        "event_count": len(period["event_ids"]),
        "high_score_count": high_score_count,
        "top8_count": top8_count,
    }


def _parent_counts(records, field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        if record["archetype"] == "Unknown" or not record[field]:
            continue
        parent_id = str(record["archetype_id"])
        counts[parent_id] = counts.get(parent_id, 0) + 1
    return counts


def _unknown_count(records, field: str) -> int:
    return sum(
        record["archetype"] == "Unknown" and bool(record[field])
        for record in records
    )


def _display_names(rules) -> dict[str, str]:
    return {parent.id: parent.name for parent in rules.archetypes}


def load_visual_metadata(
    repository_root: str | Path,
    path: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(path) if path is not None else Path(repository_root) / DEFAULT_VISUALS_PATH
    try:
        document = yaml.safe_load(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise MTGOLandingError(f"{source}: Landing visual metadata could not be loaded") from exc
    if not isinstance(document, Mapping) or document.get("schema_version") != "1.0":
        raise MTGOLandingError(f"{source}: unsupported Landing visual metadata")
    formats = document.get("formats")
    if not isinstance(formats, Mapping):
        raise MTGOLandingError(f"{source}: formats must be a mapping")
    for format_id, value in formats.items():
        if not isinstance(format_id, str) or not isinstance(value, Mapping):
            raise MTGOLandingError(f"{source}: invalid format visual metadata")
        if set(value) != {
            "parents",
            "subtypes",
            "allow_parent_fallback_for_subtypes",
        }:
            raise MTGOLandingError(f"{source}: {format_id} visual keys are incomplete")
        for section in ("parents", "subtypes"):
            entries = value[section]
            if not isinstance(entries, Mapping):
                raise MTGOLandingError(f"{source}: {format_id}.{section} must be a mapping")
            for identity, cards in entries.items():
                if (
                    not isinstance(identity, str)
                    or not isinstance(cards, list)
                    or len(cards) != 2
                    or len(set(cards)) != 2
                    or any(not isinstance(card, str) or not card.strip() for card in cards)
                ):
                    raise MTGOLandingError(
                        f"{source}: {format_id}.{section}.{identity} must contain two unique cards"
                    )
        fallbacks = value["allow_parent_fallback_for_subtypes"]
        if not isinstance(fallbacks, list) or any(
            not isinstance(item, str) for item in fallbacks
        ):
            raise MTGOLandingError(
                f"{source}: {format_id} subtype fallback list is invalid"
            )
    return dict(document)


def _key_cards(
    visual_metadata: Mapping[str, Any],
    format_id: str,
    parent_id: str,
    subtype_id: str | None = None,
) -> list[dict[str, str]]:
    format_metadata = visual_metadata.get("formats", {}).get(format_id, {})
    if subtype_id is not None:
        subtype_key = f"{parent_id}/{subtype_id}"
        cards = format_metadata.get("subtypes", {}).get(subtype_key)
        if cards is None and subtype_key in format_metadata.get(
            "allow_parent_fallback_for_subtypes", []
        ):
            cards = format_metadata.get("parents", {}).get(parent_id)
    else:
        cards = format_metadata.get("parents", {}).get(parent_id)
    return [{"name": card} for card in cards] if cards else []


def _known_parent_ids(repository_root: Path, format_id: str, rules, statistics: Path) -> set[str]:
    path = statistics / "pickup" / "known_archetypes.json"
    stable_ids = format_id == "modern"
    known = pickup.load_known(path, stable_ids=stable_ids)
    if known is None:
        raise MTGOLandingError(f"{path}: Landing requires initialized Pickup known state")
    if stable_ids:
        return known
    by_name = {parent.name: parent.id for parent in rules.archetypes}
    unresolved = sorted(known - set(by_name))
    if unresolved:
        raise MTGOLandingError(
            f"{path}: known Standard parents do not resolve: {', '.join(unresolved)}"
        )
    return {by_name[name] for name in known}


def _deck_fingerprint_sha256(record: Mapping[str, Any]) -> str:
    material = json.dumps(
        pickup.deck_fingerprint(record),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _deck_identity(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "event_id": str(record["event_id"]),
        "deck_id": str(record["deck_id"]),
        "deck_fingerprint_sha256": _deck_fingerprint_sha256(record),
        "player": str(record.get("player") or ""),
        "final_rank": int(record["final_rank"]),
        "player_count": int(record["player_count"]),
        "starttime": str(record["starttime"]),
    }


def _build_shift_observations(
    events,
    rules,
    target_monday: date,
    current_top8: list[dict[str, Any]],
    processed_events,
) -> list[dict[str, Any]]:
    reference_monday = target_monday - timedelta(weeks=1)
    parent_bases, _ = stats.build_base_pack(
        events,
        rules,
        reference_monday,
        processed_events=processed_events,
    )
    subtype_bases, _ = stats.build_subtype_base_pack(
        events,
        rules,
        reference_monday,
        processed_events=processed_events,
    )
    parent_definitions = {parent.id: parent for parent in rules.archetypes}
    selected: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for record in current_top8:
        if record["archetype"] == "Unknown":
            continue
        parent_id = str(record["archetype_id"])
        subtype_id = record.get("subtype_id")
        parent = parent_definitions[parent_id]
        if subtype_id is not None:
            identity_level = "subtype"
            identity_id = f"{parent_id}/{subtype_id}"
            display_name = str(record.get("subtype") or record["archetype"])
            base = subtype_bases.get((parent_id, subtype_id))
        elif not parent.subtypes:
            identity_level = "parent"
            identity_id = parent_id
            display_name = str(record["archetype"])
            base = parent_bases.get(parent_id)
        else:
            continue
        if not base or base["sample_size"] < stats.MIN_SAMPLE:
            continue
        score = pickup.deck_deviation(record, base)
        if score is None or score < BUILD_SHIFT_THRESHOLD:
            continue
        observation = {
            "type": "build_shift",
            "archetype_id": parent_id,
            "display_name": display_name,
            "identity_level": identity_level,
            "identity_id": identity_id,
            "subtype_id": subtype_id,
            "score": score,
            "reference_sample_size": base["sample_size"],
            "deck": _deck_identity(record),
            "difference": stats.deck_diff(stats.deck_vector(record), base["mean"]),
        }
        previous = selected.get(identity_id)
        if previous is None:
            selected[identity_id] = (record, observation)
            continue
        previous_record, previous_observation = previous
        if score > previous_observation["score"] or (
            score == previous_observation["score"]
            and pickup.better_record(record, previous_record) is record
        ):
            selected[identity_id] = (record, observation)
    return sorted(
        (observation for _record, observation in selected.values()),
        key=lambda item: (-item["score"], item["identity_id"]),
    )


def _share_observations(
    current: Mapping[str, Any],
    reference: Mapping[str, Any],
    current_top8_counts: Mapping[str, int],
    historical_parent_ids: set[str],
    known_parent_ids: set[str],
    display_names: Mapping[str, str],
) -> list[dict[str, Any]]:
    current_counts = _parent_counts(current["records"], "is_high_score")
    reference_counts = _parent_counts(reference["records"], "is_high_score")
    current_total = sum(bool(record["is_high_score"]) for record in current["records"])
    reference_total = sum(
        bool(record["is_high_score"]) for record in reference["records"]
    )
    observations: list[dict[str, Any]] = []
    for parent_id in sorted(known_parent_ids | set(current_counts) | set(reference_counts)):
        current_count = current_counts.get(parent_id, 0)
        reference_count = reference_counts.get(parent_id, 0)
        current_share = current_count / current_total if current_total else 0.0
        reference_share = reference_count / reference_total if reference_total else 0.0
        delta = current_share - reference_share
        common = {
            "archetype_id": parent_id,
            "display_name": display_names.get(parent_id, parent_id),
            "current": _metric(current_count, current_total),
            "previous_four_weeks": _metric(reference_count, reference_total),
        }
        if (
            parent_id in known_parent_ids
            and reference_count == 0
            and parent_id in historical_parent_ids
            and current_top8_counts.get(parent_id, 0) > 0
            and current_share >= ENVIRONMENT_THRESHOLD
        ):
            observations.append(
                {
                    "type": "share_move",
                    **common,
                    "state": "return",
                    "direction": "up",
                    "delta_pp": round(delta * 100, 2),
                }
            )
        elif reference_count and current_count and abs(delta) >= SHARE_MOVE_THRESHOLD:
            observations.append(
                {
                    "type": "share_move",
                    **common,
                    "state": "increase" if delta > 0 else "decrease",
                    "direction": "up" if delta > 0 else "down",
                    "delta_pp": round(delta * 100, 2),
                }
            )
        elif reference_share >= EXIT_THRESHOLD and current_count == 0:
            observations.append(
                {
                    "type": "exit",
                    **common,
                    "direction": "down",
                    "delta_pp": round(delta * 100, 2),
                }
            )
    return sorted(
        observations,
        key=lambda item: (-abs(item["delta_pp"]), item["archetype_id"]),
    )


def _environment(
    current: Mapping[str, Any],
    previous: Mapping[str, Any],
    reference: Mapping[str, Any],
    display_names: Mapping[str, str],
    visual_metadata: Mapping[str, Any],
    format_id: str,
) -> dict[str, Any]:
    periods = {
        "current": current,
        "previous_week": previous,
        "previous_four_weeks": reference,
    }
    high_counts = {
        key: _parent_counts(period["records"], "is_high_score")
        for key, period in periods.items()
    }
    high_totals = {
        key: sum(bool(record["is_high_score"]) for record in period["records"])
        for key, period in periods.items()
    }
    current_top8_counts = _parent_counts(current["records"], "is_top8")
    current_top8_total = sum(bool(record["is_top8"]) for record in current["records"])
    admitted = {
        parent_id
        for parent_id, count in high_counts["current"].items()
        if high_totals["current"]
        and count / high_totals["current"] >= ENVIRONMENT_THRESHOLD
    }
    rows = []
    for parent_id in admitted:
        rows.append(
            {
                "archetype_id": parent_id,
                "display_name": display_names.get(parent_id, parent_id),
                "key_cards": _key_cards(visual_metadata, format_id, parent_id),
                "current": _metric(
                    high_counts["current"].get(parent_id, 0),
                    high_totals["current"],
                ),
                "previous_week": _metric(
                    high_counts["previous_week"].get(parent_id, 0),
                    high_totals["previous_week"],
                ),
                "previous_four_weeks": _metric(
                    high_counts["previous_four_weeks"].get(parent_id, 0),
                    high_totals["previous_four_weeks"],
                ),
                "current_top8": _metric(
                    current_top8_counts.get(parent_id, 0), current_top8_total
                ),
            }
        )
    rows.sort(key=lambda item: (-float(item["current"]["share"] or 0), item["archetype_id"]))

    def residual(kind: str) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for key, period in periods.items():
            if kind == "unknown":
                count = _unknown_count(period["records"], "is_high_score")
            else:
                count = sum(
                    count
                    for parent_id, count in high_counts[key].items()
                    if parent_id not in admitted
                )
            values[key] = _metric(count, high_totals[key])
        if kind == "unknown":
            top8_count = _unknown_count(current["records"], "is_top8")
        else:
            top8_count = sum(
                count
                for parent_id, count in current_top8_counts.items()
                if parent_id not in admitted
            )
        values["current_top8"] = _metric(top8_count, current_top8_total)
        return values

    return {
        "threshold": ENVIRONMENT_THRESHOLD,
        "rows": rows,
        "other_classified": residual("other_classified"),
        "unknown": residual("unknown"),
    }


def _visual_review_diagnostics(
    environment: Mapping[str, Any], current_records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    diagnostics = []
    for row in environment["rows"]:
        configured = [card["name"] for card in row["key_cards"]]
        if not configured:
            continue
        observed = {
            card.get("name")
            for record in current_records
            if record["archetype"] != "Unknown"
            and str(record["archetype_id"]) == row["archetype_id"]
            for deck_key in ("main_deck", "side_deck")
            for card in record.get(deck_key, [])
            if isinstance(card, Mapping)
        }
        missing = [card for card in configured if card not in observed]
        if missing:
            diagnostics.append(
                {
                    "archetype_id": row["archetype_id"],
                    "missing_cards": missing,
                }
            )
    return diagnostics


def _fact_digest(document: Mapping[str, Any]) -> str:
    return pickup.document_digest(document)


def _default_landing_fields(category: str) -> dict[str, Any]:
    return {
        "category": category,
        "order": None,
        "headline_zh": "",
        "headline_en": "",
        "positioning_zh": "",
        "positioning_en": "",
        "featured_cards": [],
    }


def _public_supporting_fact(reason: Mapping[str, Any]) -> dict[str, Any]:
    reason_type = reason.get("type")
    if reason_type in {"share_increase", "return"}:
        fields = (
            "current_high_score_count",
            "current_high_score_denominator",
            "current_share",
            "reference_high_score_count",
            "reference_high_score_denominator",
            "reference_share",
            "delta_pp",
        )
        return {
            "type": reason_type,
            "values": {field: reason[field] for field in fields if field in reason},
        }
    if reason_type == "new_card":
        return {
            "type": reason_type,
            "values": {
                "set_code": reason.get("set_code"),
                "cards": [
                    card.get("name")
                    for card in reason.get("cards", [])
                    if isinstance(card, Mapping) and isinstance(card.get("name"), str)
                ],
            },
        }
    if reason_type == "new_archetype":
        return {
            "type": reason_type,
            "values": {
                "prior_record_count_under_current_classifier": reason.get(
                    "prior_record_count_under_current_classifier"
                )
            },
        }
    if reason_type == "build_shift":
        return {
            "type": reason_type,
            "values": {
                field: reason.get(field)
                for field in (
                    "identity_level",
                    "identity_id",
                    "reference_sample_size",
                    "score",
                )
            },
        }
    raise MTGOLandingError(f"unsupported Pickup supporting fact: {reason_type!r}")


def _write_candidate(path: Path, document: Mapping[str, Any]) -> None:
    path.write_text(
        yaml.dump(
            dict(document),
            allow_unicode=True,
            sort_keys=False,
            width=1000,
            default_flow_style=False,
        ),
        encoding="utf-8",
        newline="\n",
    )


def _feature_document(
    candidate_path: Path,
    week: str,
    source_event_ids: list[str],
    rules_digest: str,
    selection_policy_digest: str,
    visual_metadata_digest: str,
    visual_diagnostics: list[dict[str, Any]],
    machine_fact_digest: str,
) -> tuple[str, list[dict[str, Any]]]:
    try:
        candidate = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise MTGOLandingError(f"{candidate_path}: candidate could not be loaded") from exc
    if not isinstance(candidate, Mapping):
        raise MTGOLandingError(f"{candidate_path}: candidate must be a mapping")
    provenance_matches = (
        candidate.get("week") == week
        and candidate.get("source_event_ids") == source_event_ids
        and candidate.get("classifier_digest") == rules_digest
        and candidate.get("selection_policy_digest") == selection_policy_digest
    )
    reviewed = pickup._has_manual_review(candidate)
    if not provenance_matches:
        if reviewed:
            return "stale_review_required", []
        raise MTGOLandingError(
            f"{candidate_path}: unreviewed candidate provenance is stale; regenerate it"
        )
    if candidate.get("visual_metadata_digest") != visual_metadata_digest and reviewed:
        return "stale_review_required", []

    mutable = dict(candidate)
    changed = (
        mutable.get("machine_fact_digest") != machine_fact_digest
        or mutable.get("visual_metadata_digest") != visual_metadata_digest
        or mutable.get("landing_visual_diagnostics") != visual_diagnostics
    )
    if changed and reviewed:
        return "stale_review_required", []
    mutable["machine_fact_digest"] = machine_fact_digest
    mutable["visual_metadata_digest"] = visual_metadata_digest
    mutable["landing_visual_diagnostics"] = visual_diagnostics
    for collection, default_category in (
        ("existing_changes", "new_technology"),
        ("new_archetypes", "new_deck"),
    ):
        entries = mutable.get(collection)
        if not isinstance(entries, list):
            raise MTGOLandingError(f"{candidate_path}: {collection} must be a list")
        for entry in entries:
            if not isinstance(entry, dict):
                raise MTGOLandingError(f"{candidate_path}: {collection} entry is invalid")
            if "landing" not in entry:
                if reviewed:
                    return "stale_review_required", []
                entry["landing"] = _default_landing_fields(default_category)
                changed = True
    if changed:
        _write_candidate(candidate_path, mutable)

    features: list[dict[str, Any]] = []
    orders: set[tuple[str, int]] = set()
    for collection, default_category in (
        ("existing_changes", "new_technology"),
        ("new_archetypes", "new_deck"),
    ):
        for entry in mutable[collection]:
            if entry.get("approved") is not True:
                continue
            landing = entry.get("landing")
            if not isinstance(landing, Mapping):
                raise MTGOLandingError("approved Pickup entry has no Landing review fields")
            category = landing.get("category", default_category)
            order = landing.get("order")
            if category not in {"new_deck", "new_technology"}:
                raise MTGOLandingError("approved Landing feature has an invalid category")
            if not isinstance(order, int) or isinstance(order, bool) or order < 1:
                raise MTGOLandingError("approved Landing feature requires a positive order")
            if (category, order) in orders:
                raise MTGOLandingError("approved Landing feature order is duplicated")
            orders.add((category, order))
            localized = {}
            for field in (
                "headline_zh",
                "headline_en",
                "positioning_zh",
                "positioning_en",
            ):
                value = landing.get(field)
                if not isinstance(value, str):
                    raise MTGOLandingError(f"approved Landing feature requires {field}")
                localized[field] = value
            featured_cards = landing.get("featured_cards")
            if (
                not isinstance(featured_cards, list)
                or len(featured_cards) != 4
                or len(set(featured_cards)) != 4
                or any(not isinstance(card, str) or not card.strip() for card in featured_cards)
            ):
                raise MTGOLandingError("approved Landing feature requires four unique cards")
            deck_cards = {
                card.get("name")
                for key in ("main_deck", "side_deck")
                for card in entry.get(key, [])
                if isinstance(card, Mapping)
            }
            if not set(featured_cards) <= deck_cards:
                raise MTGOLandingError(
                    "approved Landing featured cards must come from the exact deck"
                )
            required_identity = (
                "archetype_id",
                "event_id",
                "deck_id",
                "deck_fingerprint_sha256",
                "archetype",
                "player",
                "final_rank",
                "player_count",
                "starttime",
            )
            missing = [field for field in required_identity if entry.get(field) is None]
            if missing:
                raise MTGOLandingError(
                    "approved Landing feature is missing identity fields: "
                    + ", ".join(missing)
                )
            features.append(
                {
                    "category": category,
                    "order": order,
                    "archetype_id": entry["archetype_id"],
                    "subtype_id": entry.get("subtype_id"),
                    "display_name": entry["archetype"],
                    "deck": {
                        "event_id": str(entry["event_id"]),
                        "deck_id": str(entry["deck_id"]),
                        "deck_fingerprint_sha256": entry["deck_fingerprint_sha256"],
                        "player": entry["player"],
                        "final_rank": entry["final_rank"],
                        "player_count": entry["player_count"],
                        "starttime": entry["starttime"],
                        "main_deck": entry.get("main_deck", []),
                        "side_deck": entry.get("side_deck", []),
                    },
                    "headline": {
                        "zh": localized["headline_zh"],
                        "en": localized["headline_en"],
                    },
                    "positioning": {
                        "zh": localized["positioning_zh"],
                        "en": localized["positioning_en"],
                    },
                    "featured_cards": [{"name": card} for card in featured_cards],
                    "supporting_facts": [
                        _public_supporting_fact(reason)
                        for reason in entry.get("candidate_reasons", [])
                        if isinstance(reason, Mapping)
                    ],
                }
            )
    category_order = {"new_deck": 0, "new_technology": 1}
    features.sort(
        key=lambda item: (
            category_order[item["category"]],
            item["order"],
            item["deck"]["event_id"],
            item["deck"]["deck_id"],
        )
    )
    return "current", features


def build_document(
    repository_root: str | Path,
    format_id: str,
    *,
    today: date | None = None,
    registry_path: str | Path | None = None,
    candidate_directory: str | Path | None = None,
    visuals_path: str | Path | None = None,
) -> tuple[str, dict[str, Any]]:
    root = Path(repository_root).resolve()
    context = load_mtgo_context(
        root,
        format_id,
        "landing_generation",
        registry_path=registry_path,
    )
    rules = load_rules_for_format(root, format_id, registry_path=registry_path)
    events = stats.load_all_events(root, format_id, registry_path=registry_path)
    reference_today = today or datetime.now().date()
    target_monday = _closed_week_monday(reference_today)
    target_sunday = target_monday + timedelta(days=6)
    previous_monday = target_monday - timedelta(weeks=1)
    reference_start = target_monday - timedelta(weeks=4)
    processed_events = {
        id(event): stats.process_event(event, rules) for _event_date, event in events
    }
    current = _period(target_monday, target_sunday, events, processed_events)
    previous = _period(
        previous_monday,
        previous_monday + timedelta(days=6),
        events,
        processed_events,
    )
    reference = _period(
        reference_start,
        target_monday - timedelta(days=1),
        events,
        processed_events,
    )
    rules_digest = classifier_digest(rules)
    selection_policy_digest = pickup.document_digest(pickup.load_pickup_policy(root))
    visual_metadata = load_visual_metadata(root, visuals_path)
    visual_metadata_digest = pickup.document_digest(visual_metadata)
    display_names = _display_names(rules)
    comparison_available = bool(
        current["event_ids"] and previous["event_ids"] and reference["event_ids"]
    )
    if not current["event_ids"]:
        unavailable_reason = "no_current_events"
    elif not previous["event_ids"]:
        unavailable_reason = "no_previous_week_events"
    elif not reference["event_ids"]:
        unavailable_reason = "no_previous_four_week_events"
    else:
        unavailable_reason = None

    environment = _environment(
        current,
        previous,
        reference,
        display_names,
        visual_metadata,
        format_id,
    )
    visual_diagnostics = _visual_review_diagnostics(
        environment, current["records"]
    )
    observations: list[dict[str, Any]] = []
    if comparison_available:
        known_parent_ids = _known_parent_ids(
            root, format_id, rules, context.paths["statistics"]
        )
        historical_parent_ids = {
            str(record["archetype_id"])
            for event_date, event in events
            if event_date < reference_start
            for record in processed_events[id(event)]["records"]
            if record["archetype"] != "Unknown"
        }
        current_top8 = pickup.week_records(
            events,
            rules,
            target_monday,
            processed_events=processed_events,
        )
        current_top8 = [record for record in current_top8 if record["is_top8"]]
        current_top8_counts = _parent_counts(current_top8, "is_top8")
        share = _share_observations(
            current,
            reference,
            current_top8_counts,
            historical_parent_ids,
            known_parent_ids,
            display_names,
        )
        builds = _build_shift_observations(
            events,
            rules,
            target_monday,
            current_top8,
            processed_events,
        )
        observations = (share + builds)[:5]

    week = pickup.iso_week_label(target_monday)
    fact_payload = {
        "week": {
            "id": week,
            "start": target_monday.isoformat(),
            "end": target_sunday.isoformat(),
        },
        "state": "ready" if current["event_ids"] else "no_events",
        "source_event_ids": current["event_ids"],
        "classifier": {"digest": rules_digest},
        "comparison": {
            "available": comparison_available,
            "unavailable_reason": unavailable_reason,
        },
        "thresholds": {
            "environment_share": ENVIRONMENT_THRESHOLD,
            "share_move_pp": SHARE_MOVE_THRESHOLD * 100,
            "exit_reference_share": EXIT_THRESHOLD,
            "build_shift": BUILD_SHIFT_THRESHOLD,
            "build_reference_minimum": stats.MIN_SAMPLE,
        },
        "populations": {
            "current": _population(current),
            "previous_week": _population(previous),
            "previous_four_weeks": _population(reference),
        },
        "environment": environment,
        "observations": observations,
    }
    machine_fact_digest = _fact_digest(fact_payload)
    features: list[dict[str, Any]] = []
    review_status = "not_applicable"
    if current["event_ids"]:
        candidate_root = (
            Path(candidate_directory)
            if candidate_directory is not None
            else context.paths["statistics"] / "pickup"
        )
        candidate_path = candidate_root / f"candidates_{week}.yaml"
        if not candidate_path.is_file():
            raise MTGOLandingError(f"{candidate_path}: current Pickup candidate is missing")
        review_status, features = _feature_document(
            candidate_path,
            week,
            current["event_ids"],
            rules_digest,
            selection_policy_digest,
            visual_metadata_digest,
            visual_diagnostics,
            machine_fact_digest,
        )

    document = versioned(
        {
            "product": PRODUCT_ID,
            "format": format_id,
            "source": SOURCE_ID,
            **fact_payload,
            "features": {
                "week": week,
                "items": features,
            },
            "review_binding": {
                "source_event_ids": current["event_ids"],
                "classifier_digest": rules_digest,
                "visual_metadata_digest": visual_metadata_digest,
                "machine_fact_digest": machine_fact_digest,
            },
        }
    )
    validate_document(document)
    return review_status, document


def validate_document(document: Mapping[str, Any]) -> None:
    """Reject cross-field inconsistencies that JSON Schema cannot express."""

    source_event_ids = document["source_event_ids"]
    if source_event_ids != sorted(set(source_event_ids)):
        raise MTGOLandingError("Landing source_event_ids must be sorted and unique")
    if source_event_ids != document["populations"]["current"]["event_ids"]:
        raise MTGOLandingError("Landing current population event binding is inconsistent")
    binding = document["review_binding"]
    if (
        binding["source_event_ids"] != source_event_ids
        or binding["classifier_digest"] != document["classifier"]["digest"]
        or not isinstance(binding["visual_metadata_digest"], str)
    ):
        raise MTGOLandingError("Landing review binding is inconsistent")

    rows = document["environment"]["rows"]
    other = document["environment"]["other_classified"]
    unknown = document["environment"]["unknown"]
    for period_key in ("current", "previous_week", "previous_four_weeks"):
        total = document["populations"][period_key]["high_score_count"]
        metrics = [row[period_key] for row in rows] + [other[period_key], unknown[period_key]]
        if any(metric["denominator"] != total for metric in metrics):
            raise MTGOLandingError(
                f"Landing {period_key} high-score denominator is inconsistent"
            )
        if sum(metric["count"] for metric in metrics) != total:
            raise MTGOLandingError(
                f"Landing {period_key} high-score decomposition is inconsistent"
            )
    top8_total = document["populations"]["current"]["top8_count"]
    top8_metrics = [row["current_top8"] for row in rows] + [
        other["current_top8"],
        unknown["current_top8"],
    ]
    if any(metric["denominator"] != top8_total for metric in top8_metrics):
        raise MTGOLandingError("Landing current Top 8 denominator is inconsistent")
    if sum(metric["count"] for metric in top8_metrics) != top8_total:
        raise MTGOLandingError("Landing current Top 8 decomposition is inconsistent")

    if document["state"] == "no_events":
        if source_event_ids or rows or document["observations"] or document["features"]["items"]:
            raise MTGOLandingError("Landing no_events document contains current content")
    elif not source_event_ids:
        raise MTGOLandingError("Landing ready document has no source events")


def generate(
    repository_root: str | Path,
    format_id: str,
    *,
    today: date | None = None,
    registry_path: str | Path | None = None,
    candidate_directory: str | Path | None = None,
    output_directory: str | Path | None = None,
    visuals_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    context = load_mtgo_context(
        root,
        format_id,
        "landing_generation",
        registry_path=registry_path,
    )
    review_status, document = build_document(
        root,
        format_id,
        today=today,
        registry_path=registry_path,
        candidate_directory=candidate_directory,
        visuals_path=visuals_path,
    )
    output = (
        Path(output_directory).resolve()
        if output_directory is not None
        else context.paths["statistics"] / "landing"
    )
    destination = output / "current.json"
    if review_status == "stale_review_required":
        if not destination.is_file():
            raise MTGOLandingError(
                "reviewed Landing facts are stale and no admitted current document exists"
            )
        return {
            "status": review_status,
            "path": destination,
            "week": document["week"]["id"],
        }
    output.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {
        "status": "written",
        "path": destination,
        "week": document["week"]["id"],
        "feature_count": len(document["features"]["items"]),
        "observation_count": len(document["observations"]),
    }


__all__ = [
    "MTGOLandingError",
    "build_document",
    "generate",
    "load_visual_metadata",
    "validate_document",
]
