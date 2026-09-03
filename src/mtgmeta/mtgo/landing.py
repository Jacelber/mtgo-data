"""Deterministic latest MTGO Landing facts and reviewed feature archive."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from mtgmeta.public_contract import versioned

from . import load_mtgo_context
from . import landing_editorial as editorial
from . import landing_screening as screening, stats
from .normalize import load_rules_for_format
from .top8 import classifier_digest


SOURCE_ID = "mtgo"
PRODUCT_ID = "mtgo-landing"
ENVIRONMENT_THRESHOLD = 0.03
SHARE_MOVE_THRESHOLD = 0.05
EXIT_THRESHOLD = 0.05
BUILD_SHIFT_THRESHOLD = 20
LANDING_SCHEMA_VERSION = "1.2.0"
FEATURE_ARCHIVE_SCHEMA_VERSION = "1.0.0"
FEATURE_ARCHIVE_PRODUCT_ID = "mtgo-landing-features"
DEFAULT_VISUALS_PATH = Path("configs/mtgo_landing_visuals.yaml")
DECK_LINK_TOKEN_PATTERN = re.compile(r"deck:[0-9a-f]{20}")
CLASSIFIER_RESTATEMENT_BINDINGS = frozenset(
    {"classifier_digest", "machine_fact_digest"}
)
CLASSIFIER_RESTATEMENT_MATERIAL_FIELDS = (
    "week",
    "state",
    "source_event_ids",
    "comparison",
    "thresholds",
    "populations",
    "environment",
)


class MTGOLandingError(RuntimeError):
    """Raised when Landing facts or reviewed features cannot be admitted."""


def _classifier_restatement_preserves_accepted_material(
    binding_mismatches: set[str],
    prior_document: Mapping[str, Any],
    fact_payload: Mapping[str, Any],
) -> bool:
    return binding_mismatches <= CLASSIFIER_RESTATEMENT_BINDINGS and all(
        prior_document.get(field) == fact_payload.get(field)
        for field in CLASSIFIER_RESTATEMENT_MATERIAL_FIELDS
    )


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


def _known_parent_ids(statistics: Path) -> set[str]:
    path = statistics / "landing" / "review" / "known_archetypes.json"
    if path.is_file():
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise MTGOLandingError(f"{path}: Landing known state could not be loaded") from exc
        known_ids = document.get("known_ids") if isinstance(document, Mapping) else None
        if not isinstance(known_ids, list) or any(
            not isinstance(value, str) for value in known_ids
        ):
            raise MTGOLandingError(f"{path}: Landing known state is invalid")
        return set(known_ids)

    raise MTGOLandingError(f"{path}: Landing requires initialized known state")


def _deck_fingerprint_sha256(record: Mapping[str, Any]) -> str:
    material = json.dumps(
        screening.deck_fingerprint(record),
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
        score = screening.deck_deviation(record, base)
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
            and screening.better_record(record, previous_record) is record
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
    return screening.document_digest(document)


def _deck_link_catalog(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    for record in records:
        if not record.get("is_top8"):
            continue
        deck_id = str(record.get("deck_id") or "")
        event_id = str(record.get("event_id") or "")
        final_rank = record.get("final_rank")
        if (
            not deck_id
            or not event_id.isdigit()
            or not isinstance(final_rank, int)
            or isinstance(final_rank, bool)
            or not 1 <= final_rank <= 8
        ):
            raise MTGOLandingError("Landing deck-link catalog contains invalid identity")
        catalog.append(
            {
                "link_id": f"deck:{deck_id}",
                "archetype_id": str(record.get("archetype_id") or "unknown"),
                "display_name": str(record.get("archetype") or "Unknown"),
                "event_id": event_id,
                "deck_id": deck_id,
                "deck_fingerprint_sha256": _deck_fingerprint_sha256(record),
                "player": str(record.get("player") or ""),
                "final_rank": final_rank,
                "starttime": str(record.get("starttime") or ""),
            }
        )
    catalog.sort(
        key=lambda item: (
            item["starttime"],
            item["event_id"],
            item["final_rank"],
            item["deck_id"],
        )
    )
    link_ids = [item["link_id"] for item in catalog]
    placements = [(item["event_id"], item["final_rank"]) for item in catalog]
    if len(link_ids) != len(set(link_ids)) or len(placements) != len(set(placements)):
        raise MTGOLandingError("Landing deck-link catalog identities are duplicated")
    return catalog


def _summary_deck_tokens(text: str) -> list[str]:
    return list(dict.fromkeys(DECK_LINK_TOKEN_PATTERN.findall(text)))


def _summary_deck_labels(deck: Mapping[str, Any]) -> dict[str, str]:
    stem = f"{deck['display_name']} · {deck['player']} · "
    return {
        "zh": f"{stem}第{deck['final_rank']}名",
        "en": f"{stem}Rank {deck['final_rank']}",
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
    raise MTGOLandingError(
        f"unsupported Landing screening supporting fact: {reason_type!r}"
    )


def _public_feature(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "category": item["category"],
        "order": item["order"],
        "destination_id": item["destination_id"],
        "archetype_id": item["archetype_id"],
        "subtype_id": item["subtype_id"],
        "display_name": item["display_name"],
        "deck": item["deck"],
        "headline": item["title"],
        "positioning": item["positioning"],
        "featured_cards": item["featured_cards"],
        "supporting_facts": [
            _public_supporting_fact(reason) for reason in item["supporting_facts"]
        ],
    }


def _feature_archive_documents(
    root: Path,
    format_id: str,
    review_root: Path,
    name_catalog_path: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    editorial.validate_name_catalog(root, name_catalog_path)
    names = editorial.load_name_catalog(name_catalog_path)
    week_documents: dict[str, dict[str, Any]] = {}
    index_entries: list[dict[str, Any]] = []
    for review_path in sorted(review_root.glob("????-W??.yaml")):
        review = editorial.load_review_document(
            review_path,
            root / editorial.DEFAULT_REVIEW_SCHEMA,
        )
        if review["format"] != format_id or review["source"] != SOURCE_ID:
            raise MTGOLandingError(
                f"{review_path}: Landing review format/source does not match archive"
            )
        week = review["week"]
        if review_path.stem != week["id"]:
            raise MTGOLandingError(
                f"{review_path}: Landing review filename does not match week"
            )
        materialized = editorial.materialize_review(review, names)
        items = [_public_feature(item) for item in materialized["features"]]
        destinations = [item["destination_id"] for item in items]
        if len(destinations) != len(set(destinations)):
            raise MTGOLandingError(
                f"{review_path}: Landing feature destinations must be unique"
            )
        document = {
            "schema_version": FEATURE_ARCHIVE_SCHEMA_VERSION,
            "product": FEATURE_ARCHIVE_PRODUCT_ID,
            "format": format_id,
            "source": SOURCE_ID,
            "week": week,
            "source_event_ids": review["bindings"]["source_event_ids"],
            "classifier_digest": review["bindings"]["classifier_digest"],
            "content_digest": editorial.document_digest(items),
            "features": {"items": items},
        }
        week_documents[week["id"]] = document
        index_entries.append(
            {
                "week": week["id"],
                "file": f"{week['id']}.json",
                "start": week["start"],
                "end": week["end"],
                "feature_count": len(items),
            }
        )
    if not week_documents:
        raise MTGOLandingError(f"{review_root}: no Landing review weeks found")
    index = {
        "schema_version": FEATURE_ARCHIVE_SCHEMA_VERSION,
        "product": FEATURE_ARCHIVE_PRODUCT_ID,
        "format": format_id,
        "source": SOURCE_ID,
        "weeks": sorted(index_entries, key=lambda item: item["week"], reverse=True),
    }
    return index, week_documents


def build_document(
    repository_root: str | Path,
    format_id: str,
    *,
    today: date | None = None,
    registry_path: str | Path | None = None,
    review_directory: str | Path | None = None,
    name_catalog_path: str | Path | None = None,
    visuals_path: str | Path | None = None,
    allow_classifier_restatement: bool = False,
    _admit_review: bool = True,
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
    selection_policy_digest = screening.document_digest(screening.load_screening_policy(root))
    visual_metadata = load_visual_metadata(root, visuals_path)
    visual_metadata_digest = screening.document_digest(visual_metadata)
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
    observations: list[dict[str, Any]] = []
    current_top8: list[dict[str, Any]] = []
    if current["event_ids"]:
        current_top8 = screening.week_records(
            events,
            rules,
            target_monday,
            processed_events=processed_events,
        )
        current_top8 = [record for record in current_top8 if record["is_top8"]]
    if comparison_available:
        known_parent_ids = _known_parent_ids(context.paths["statistics"])
        historical_parent_ids = {
            str(record["archetype_id"])
            for event_date, event in events
            if event_date < reference_start
            for record in processed_events[id(event)]["records"]
            if record["archetype"] != "Unknown"
        }
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
        observations = share + builds

    week = screening.iso_week_label(target_monday)
    deck_link_catalog = _deck_link_catalog(current_top8)
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
    }
    machine_fact_digest = _fact_digest(
        {**fact_payload, "observations": observations[:5]}
    )
    features: list[dict[str, Any]] = []
    summary_items: list[dict[str, Any]] = []
    pickup_document_digest = _fact_digest(
        {"week": week, "state": "no_current_events"}
    )
    summary_fact_digest = _fact_digest(
        {
            "week": week,
            "source_event_ids": [],
            "pickup_document_digest": pickup_document_digest,
            "review_inputs": [],
            "deck_link_catalog": deck_link_catalog,
        }
    )
    review_status = "not_applicable"
    if current["event_ids"] and _admit_review:
        review_root = (
            Path(review_directory)
            if review_directory is not None
            else context.paths["statistics"] / "landing" / "review"
        )
        review_path = review_root / f"{week}.yaml"
        if not review_path.is_file():
            review_status = "stale_review_required"
        else:
            catalog_path = (
                Path(name_catalog_path)
                if name_catalog_path is not None
                else root / editorial.DEFAULT_NAME_CATALOG
            )
            editorial.validate_name_catalog(root, catalog_path)
            name_document = editorial.load_name_catalog_document(catalog_path)
            names = editorial.load_name_catalog(catalog_path)
            review = editorial.load_review_document(
                review_path,
                root / editorial.DEFAULT_REVIEW_SCHEMA,
            )
            current_catalog = editorial.build_top8_catalog(current_top8)
            current_binding = {
                "workbook_sha256": review["bindings"]["workbook_sha256"],
                "source_event_ids": current["event_ids"],
                "classifier_digest": rules_digest,
                "selection_policy_digest": selection_policy_digest,
                "machine_fact_digest": machine_fact_digest,
                "link_catalog_digest": editorial.document_digest(current_catalog),
                "bilingual_catalog_digest": editorial.document_digest(name_document),
            }
            binding_fields = (
                "workbook_sha256",
                "source_event_ids",
                "classifier_digest",
                "selection_policy_digest",
                "machine_fact_digest",
                "link_catalog_digest",
                "bilingual_catalog_digest",
            )
            binding_mismatches = {
                field
                for field in binding_fields
                if review["bindings"].get(field) != current_binding.get(field)
            }
            prior_document: dict[str, Any] | None = None
            if allow_classifier_restatement and binding_mismatches <= (
                CLASSIFIER_RESTATEMENT_BINDINGS
            ):
                current_path = context.paths["statistics"] / "landing" / "current.json"
                try:
                    loaded = json.loads(current_path.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, json.JSONDecodeError):
                    loaded = None
                if isinstance(loaded, dict):
                    prior_document = loaded
            restatement_safe = (
                allow_classifier_restatement
                and prior_document is not None
                and _classifier_restatement_preserves_accepted_material(
                    binding_mismatches,
                    prior_document,
                    fact_payload,
                )
            )
            if binding_mismatches and not restatement_safe:
                review_status = "stale_review_required"
            else:
                materialized = editorial.materialize_review(review, names)
                summary_items = materialized["weekly_summary"]
                features = [_public_feature(item) for item in materialized["features"]]
                pickup_document_digest = editorial.document_digest(review)
                summary_fact_digest = editorial.document_digest(
                    {
                        "week": week,
                        "bindings": review["bindings"],
                        "top_copy": review["review"]["top_copy"],
                    }
                )
                review_status = "current"

    document = versioned(
        {
            "product": PRODUCT_ID,
            "format": format_id,
            "source": SOURCE_ID,
            **fact_payload,
            "weekly_summary": {
                "week": week,
                "items": summary_items,
            },
            "features": {
                "week": week,
                "items": features,
            },
            "review_binding": {
                "source_event_ids": current["event_ids"],
                "classifier_digest": rules_digest,
                "visual_metadata_digest": visual_metadata_digest,
                "machine_fact_digest": machine_fact_digest,
                "pickup_document_digest": pickup_document_digest,
                "summary_fact_digest": summary_fact_digest,
            },
        },
        schema_version=LANDING_SCHEMA_VERSION,
    )
    validate_document(document)
    return review_status, document


def machine_fact_digest_for_week(
    repository_root: str | Path,
    format_id: str,
    week: str,
) -> str:
    """Return the exact Landing fact digest used to admit one review week."""

    try:
        monday = datetime.strptime(f"{week}-1", "%G-W%V-%u").date()
    except ValueError as exc:
        raise MTGOLandingError(f"invalid ISO Landing week: {week}") from exc
    _review_status, document = build_document(
        repository_root,
        format_id,
        today=monday + timedelta(days=7),
        _admit_review=False,
    )
    if document["week"]["id"] != week:
        raise MTGOLandingError(
            f"Landing machine fact week mismatch: expected {week}, "
            f"got {document['week']['id']}"
        )
    return str(document["review_binding"]["machine_fact_digest"])


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
        or (
            document["schema_version"] != "1.0.0"
            and (
                not isinstance(binding.get("pickup_document_digest"), str)
                or not isinstance(binding.get("summary_fact_digest"), str)
            )
        )
    ):
        raise MTGOLandingError("Landing review binding is inconsistent")

    if document["schema_version"] != "1.0.0":
        summary = document["weekly_summary"]
        if summary["week"] != document["week"]["id"]:
            raise MTGOLandingError("Landing weekly summary week is inconsistent")
        summary_orders = [item["order"] for item in summary["items"]]
        if summary_orders != sorted(set(summary_orders)):
            raise MTGOLandingError("Landing weekly summary order is invalid")
        if any(
            not item["text"]["zh"].strip() and not item["text"]["en"].strip()
            for item in summary["items"]
        ):
            raise MTGOLandingError("Landing weekly summary contains empty final text")
        for item in summary["items"]:
            links = item["deck_links"]
            link_orders = [link["order"] for link in links]
            link_tokens = [link["token"] for link in links]
            placements = [
                (link["deck"]["event_id"], link["deck"]["final_rank"])
                for link in links
            ]
            if link_orders != sorted(set(link_orders)):
                raise MTGOLandingError("Landing weekly summary deck-link order is invalid")
            if len(placements) != len(set(placements)) or any(
                event_id not in source_event_ids for event_id, _rank in placements
            ):
                raise MTGOLandingError("Landing weekly summary deck link is invalid")
            localized_tokens = [
                _summary_deck_tokens(text)
                for text in item["text"].values()
                if text.strip()
            ]
            if (
                (len(localized_tokens) == 2 and set(localized_tokens[0]) != set(localized_tokens[1]))
                or (localized_tokens and localized_tokens[0] != link_tokens)
                or any(
                    link["token"] != f"deck:{link['deck']['deck_id']}"
                    for link in links
                )
            ):
                raise MTGOLandingError(
                    "Landing weekly summary deck-link token mapping is invalid"
                )
            if any(
                not isinstance(link.get("label"), Mapping)
                or link["label"].get("en")
                != _summary_deck_labels(link["deck"])["en"]
                or not isinstance(link["label"].get("zh"), str)
                or not link["label"]["zh"].endswith(
                    f" · {link['deck']['player']} · 第{link['deck']['final_rank']}名"
                )
                for link in links
            ):
                raise MTGOLandingError("Landing weekly summary deck-link label is invalid")
        if document["schema_version"] == LANDING_SCHEMA_VERSION:
            feature_destinations = {
                item.get("destination_id") for item in document["features"]["items"]
            }
            if None in feature_destinations or len(feature_destinations) != len(
                document["features"]["items"]
            ):
                raise MTGOLandingError(
                    "Landing feature destinations are missing or duplicated"
                )
            linked_destinations = {
                link["token"]
                for item in summary["items"]
                for link in item["deck_links"]
            }
            if not linked_destinations <= feature_destinations:
                raise MTGOLandingError(
                    "Landing weekly summary deck link has no exact reviewed feature"
                )

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
        editorial_items = (
            document["weekly_summary"]["items"]
            if document["schema_version"] != "1.0.0"
            else document["observations"]
        )
        if source_event_ids or rows or editorial_items or document["features"]["items"]:
            raise MTGOLandingError("Landing no_events document contains current content")
    elif not source_event_ids:
        raise MTGOLandingError("Landing ready document has no source events")


def generate(
    repository_root: str | Path,
    format_id: str,
    *,
    today: date | None = None,
    registry_path: str | Path | None = None,
    review_directory: str | Path | None = None,
    name_catalog_path: str | Path | None = None,
    output_directory: str | Path | None = None,
    visuals_path: str | Path | None = None,
    allow_classifier_restatement: bool = False,
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
        review_directory=review_directory,
        name_catalog_path=name_catalog_path,
        visuals_path=visuals_path,
        allow_classifier_restatement=allow_classifier_restatement,
    )
    output = (
        Path(output_directory).resolve()
        if output_directory is not None
        else context.paths["statistics"] / "landing"
    )
    destination = output / "current.json"
    if review_status in {"stale_review_required", "summary_review_required"}:
        if not destination.is_file():
            raise MTGOLandingError(
                "Landing review is incomplete or stale and no admitted current document exists"
            )
        return {
            "status": review_status,
            "path": destination,
            "week": document["week"]["id"],
            "feature_count": len(document["features"]["items"]),
            "summary_count": len(document["weekly_summary"]["items"]),
        }
    review_root = (
        Path(review_directory).resolve()
        if review_directory is not None
        else context.paths["statistics"] / "landing" / "review"
    )
    catalog_path = (
        Path(name_catalog_path).resolve()
        if name_catalog_path is not None
        else root / editorial.DEFAULT_NAME_CATALOG
    )
    feature_index, feature_weeks = _feature_archive_documents(
        root,
        format_id,
        review_root,
        catalog_path,
    )
    current_feature = feature_weeks.get(document["week"]["id"])
    if current_feature is None or current_feature["features"]["items"] != document["features"]["items"]:
        raise MTGOLandingError(
            "Landing latest document and feature archive do not share one reviewed source"
        )
    output.mkdir(parents=True, exist_ok=True)
    feature_output = output / "features"
    feature_output.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (feature_output / "index.json").write_text(
        json.dumps(feature_index, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    for week_id, week_document in feature_weeks.items():
        (feature_output / f"{week_id}.json").write_text(
            json.dumps(week_document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return {
        "status": "written",
        "path": destination,
        "week": document["week"]["id"],
        "feature_count": len(document["features"]["items"]),
        "summary_count": len(document["weekly_summary"]["items"]),
        "archive_week_count": len(feature_weeks),
    }


__all__ = [
    "MTGOLandingError",
    "build_document",
    "_feature_archive_documents",
    "generate",
    "load_visual_metadata",
    "machine_fact_digest_for_week",
    "validate_document",
]
