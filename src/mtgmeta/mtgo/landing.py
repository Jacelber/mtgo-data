"""Deterministic latest-only MTGO Landing facts and reviewed Pickup features."""

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
from . import pickup, stats
from .normalize import load_rules_for_format
from .top8 import classifier_digest


SOURCE_ID = "mtgo"
PRODUCT_ID = "mtgo-landing"
ENVIRONMENT_THRESHOLD = 0.03
SHARE_MOVE_THRESHOLD = 0.05
EXIT_THRESHOLD = 0.05
BUILD_SHIFT_THRESHOLD = 20
LANDING_SCHEMA_VERSION = "1.1.0"
DEFAULT_VISUALS_PATH = Path("configs/mtgo_landing_visuals.yaml")
DECK_LINK_TOKEN_PATTERN = re.compile(r"deck:[0-9a-f]{20}")


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


def _summary_input_id(fact: Mapping[str, Any]) -> str:
    fact_type = str(fact["type"])
    return f"{fact_type}:{_fact_digest(fact)[:16]}"


def _load_published_pickup(
    path: Path,
    *,
    format_id: str,
    week: str,
    source_event_ids: list[str],
    rules_digest: str,
    selection_policy_digest: str,
) -> tuple[dict[str, Any], str]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MTGOLandingError(f"{path}: published Pickup could not be loaded") from exc
    if not isinstance(document, dict):
        raise MTGOLandingError(f"{path}: published Pickup must be a mapping")
    provenance_matches = (
        document.get("schema_version") == pickup.PICKUP_WEEK_SCHEMA_VERSION
        and document.get("format") == format_id
        and document.get("source") == SOURCE_ID
        and document.get("week") == week
        and document.get("source_event_ids") == source_event_ids
        and document.get("classifier_digest") == rules_digest
        and document.get("selection_policy_digest") == selection_policy_digest
    )
    if not provenance_matches:
        raise MTGOLandingError(
            f"{path}: published Pickup does not match the current Landing subject"
        )

    deck_ids: list[str] = []
    for collection in ("existing_changes", "new_archetypes"):
        entries = document.get(collection)
        if not isinstance(entries, list):
            raise MTGOLandingError(f"{path}: Pickup {collection} must be a list")
        for entry in entries:
            if not isinstance(entry, Mapping):
                raise MTGOLandingError(f"{path}: Pickup {collection} entry is invalid")
            deck_id = entry.get("deck_id")
            reason_types = entry.get("reason_types")
            if (
                not isinstance(deck_id, str)
                or not isinstance(reason_types, list)
                or any(not isinstance(value, str) for value in reason_types)
                or not isinstance(entry.get("comment_zh"), str)
                or not isinstance(entry.get("comment_en"), str)
            ):
                raise MTGOLandingError(
                    f"{path}: published Pickup entry lacks reviewed provenance or copy"
                )
            deck_ids.append(deck_id)
    if len(deck_ids) != len(set(deck_ids)):
        raise MTGOLandingError(f"{path}: published Pickup deck IDs are duplicated")
    return document, _fact_digest(document)


def _summary_review_inputs(
    observations: list[dict[str, Any]], published_pickup: Mapping[str, Any]
) -> list[dict[str, Any]]:
    inputs: list[dict[str, Any]] = []
    for observation in observations:
        fact = dict(observation)
        inputs.append(
            {
                "input_id": _summary_input_id(fact),
                "input_source": "machine_fact",
                **fact,
            }
        )

    for collection in ("existing_changes", "new_archetypes"):
        entries = published_pickup.get(collection)
        if not isinstance(entries, list):
            raise MTGOLandingError(f"Pickup {collection} must be a list")
        for entry in entries:
            if not isinstance(entry, Mapping):
                raise MTGOLandingError(f"Pickup {collection} entry is invalid")
            deck_id = str(entry["deck_id"])
            inputs.append(
                {
                    "input_id": f"published_pickup:{deck_id}",
                    "input_source": "published_pickup",
                    "type": "published_pickup",
                    "archetype_id": entry.get("archetype_id"),
                    "display_name": entry.get("archetype"),
                    "deck": {
                        "event_id": str(entry.get("event_id") or ""),
                        "deck_id": deck_id,
                        "deck_fingerprint_sha256": entry.get(
                            "deck_fingerprint_sha256"
                        ),
                        "player": str(entry.get("player") or ""),
                        "final_rank": entry.get("final_rank"),
                        "player_count": entry.get("player_count"),
                        "starttime": str(entry.get("starttime") or ""),
                    },
                    "reason_types": list(entry.get("reason_types", [])),
                    "text_zh": entry.get("comment_zh", ""),
                    "text_en": entry.get("comment_en", ""),
                }
            )

    input_ids = [item["input_id"] for item in inputs]
    if len(input_ids) != len(set(input_ids)):
        raise MTGOLandingError("Landing summary review input IDs are duplicated")
    return inputs


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


def _summary_digest(
    week: str,
    source_event_ids: list[str],
    rules_digest: str,
    selection_policy_digest: str,
    pickup_document_digest: str,
    review_inputs: list[dict[str, Any]],
    deck_link_catalog: list[dict[str, Any]],
) -> str:
    return _fact_digest(
        {
            "week": week,
            "source_event_ids": source_event_ids,
            "classifier_digest": rules_digest,
            "selection_policy_digest": selection_policy_digest,
            "pickup_document_digest": pickup_document_digest,
            "review_inputs": review_inputs,
            "deck_link_catalog": deck_link_catalog,
        }
    )


def _summary_deck_tokens(text: str) -> list[str]:
    return list(dict.fromkeys(DECK_LINK_TOKEN_PATTERN.findall(text)))


def _summary_deck_labels(deck: Mapping[str, Any]) -> dict[str, str]:
    stem = f"{deck['display_name']} · {deck['player']} · "
    return {
        "zh": f"{stem}第{deck['final_rank']}名",
        "en": f"{stem}Rank {deck['final_rank']}",
    }


def _load_candidate(path: Path) -> dict[str, Any]:
    try:
        candidate = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise MTGOLandingError(f"{path}: candidate could not be loaded") from exc
    if not isinstance(candidate, dict):
        raise MTGOLandingError(f"{path}: candidate must be a mapping")
    return candidate


def _summary_document(
    candidate_path: Path,
    week: str,
    source_event_ids: list[str],
    rules_digest: str,
    selection_policy_digest: str,
    pickup_document_digest: str,
    review_inputs: list[dict[str, Any]],
    deck_link_catalog: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]], str]:
    candidate = _load_candidate(candidate_path)
    provenance_matches = (
        candidate.get("week") == week
        and candidate.get("source_event_ids") == source_event_ids
        and candidate.get("classifier_digest") == rules_digest
        and candidate.get("selection_policy_digest") == selection_policy_digest
    )
    if not provenance_matches:
        return "stale_review_required", [], _fact_digest(
            {
                "week": week,
                "review_inputs": review_inputs,
                "deck_link_catalog": deck_link_catalog,
            }
        )

    summary_fact_digest = _summary_digest(
        week,
        source_event_ids,
        rules_digest,
        selection_policy_digest,
        pickup_document_digest,
        review_inputs,
        deck_link_catalog,
    )
    summary = candidate.get("landing_summary")
    changed = False
    if summary is None:
        summary = {
            "summary_fact_digest": summary_fact_digest,
            "pickup_document_digest": pickup_document_digest,
            "review_inputs": review_inputs,
            "deck_link_catalog": deck_link_catalog,
            "reviewed": False,
            "items": [],
        }
        candidate["landing_summary"] = summary
        changed = True
    elif not isinstance(summary, dict):
        raise MTGOLandingError(f"{candidate_path}: landing_summary must be a mapping")

    if summary.get("reviewed") not in {True, False}:
        raise MTGOLandingError(
            f"{candidate_path}: landing_summary.reviewed must be a boolean"
        )
    reviewed = summary["reviewed"] is True
    items = summary.get("items")
    if not isinstance(items, list):
        raise MTGOLandingError(f"{candidate_path}: landing_summary.items must be a list")
    if not reviewed:
        if items:
            raise MTGOLandingError(
                f"{candidate_path}: summary items require reviewed: true"
            )
        if (
            summary.get("summary_fact_digest") != summary_fact_digest
            or summary.get("pickup_document_digest") != pickup_document_digest
            or summary.get("review_inputs") != review_inputs
            or summary.get("deck_link_catalog") != deck_link_catalog
        ):
            summary["summary_fact_digest"] = summary_fact_digest
            summary["pickup_document_digest"] = pickup_document_digest
            summary["review_inputs"] = review_inputs
            summary["deck_link_catalog"] = deck_link_catalog
            changed = True
        if changed:
            _write_candidate(candidate_path, candidate)
        return "summary_review_required", [], summary_fact_digest

    if (
        summary.get("summary_fact_digest") != summary_fact_digest
        or summary.get("pickup_document_digest") != pickup_document_digest
        or summary.get("review_inputs") != review_inputs
        or summary.get("deck_link_catalog") != deck_link_catalog
    ):
        return "stale_review_required", [], summary_fact_digest

    known_input_ids = {item["input_id"] for item in review_inputs}
    links_by_id = {item["link_id"]: item for item in deck_link_catalog}
    orders: set[int] = set()
    public_items: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, Mapping):
            raise MTGOLandingError("Landing summary item must be a mapping")
        order = item.get("order")
        if not isinstance(order, int) or isinstance(order, bool) or order < 1:
            raise MTGOLandingError("Landing summary item requires a positive order")
        if order in orders:
            raise MTGOLandingError("Landing summary item order is duplicated")
        orders.add(order)
        text_zh = item.get("text_zh")
        text_en = item.get("text_en")
        if not isinstance(text_zh, str) or not isinstance(text_en, str):
            raise MTGOLandingError("Landing summary item requires text_zh and text_en")
        if not text_zh.strip() and not text_en.strip():
            raise MTGOLandingError("Landing summary item requires human final text")
        source_input_ids = item.get("source_input_ids", [])
        if (
            not isinstance(source_input_ids, list)
            or len(source_input_ids) != len(set(source_input_ids))
            or any(not isinstance(value, str) for value in source_input_ids)
        ):
            raise MTGOLandingError("Landing summary source_input_ids must be unique strings")
        unknown = sorted(set(source_input_ids) - known_input_ids)
        if unknown:
            raise MTGOLandingError(
                "Landing summary references unknown review inputs: " + ", ".join(unknown)
            )
        if "deck_links" in item:
            raise MTGOLandingError(
                "Landing summary deck links must use exact deck:ID text tokens"
            )
        localized_tokens = [
            _summary_deck_tokens(text)
            for text in (text_zh, text_en)
            if text.strip()
        ]
        if len(localized_tokens) == 2 and set(localized_tokens[0]) != set(
            localized_tokens[1]
        ):
            raise MTGOLandingError(
                "Landing summary localized deck-link tokens do not match"
            )
        selected_link_ids = localized_tokens[0] if localized_tokens else []
        unknown_links = sorted(set(selected_link_ids) - links_by_id.keys())
        if unknown_links:
            raise MTGOLandingError(
                "Landing summary references unknown deck-link tokens: "
                + ", ".join(unknown_links)
            )
        public_links: list[dict[str, Any]] = []
        for link_order, link_id in enumerate(selected_link_ids, start=1):
            catalog_entry = links_by_id[link_id]
            public_links.append(
                {
                    "order": link_order,
                    "token": link_id,
                    "label": _summary_deck_labels(catalog_entry),
                    "deck": {
                        key: catalog_entry[key]
                        for key in (
                            "archetype_id",
                            "display_name",
                            "event_id",
                            "deck_id",
                            "deck_fingerprint_sha256",
                            "player",
                            "final_rank",
                            "starttime",
                        )
                    },
                }
            )
        public_links.sort(key=lambda value: value["order"])
        public_items.append(
            {
                "order": order,
                "text": {"zh": text_zh, "en": text_en},
                "deck_links": public_links,
            }
        )
    public_items.sort(key=lambda item: item["order"])
    return "current", public_items, summary_fact_digest


def _default_landing_fields(category: str) -> dict[str, Any]:
    return {
        "approved": False,
        "category": category,
        "order": None,
        "headline_zh": "",
        "headline_en": "",
        "positioning_zh": "",
        "positioning_en": "",
        "featured_cards": [],
    }


def _has_landing_feature_review(document: Mapping[str, Any]) -> bool:
    for collection, default_category in (
        ("existing_changes", "new_technology"),
        ("new_archetypes", "new_deck"),
    ):
        entries = document.get(collection, [])
        if not isinstance(entries, list):
            return True
        default = _default_landing_fields(default_category)
        for entry in entries:
            if not isinstance(entry, Mapping):
                return True
            fields = entry.get("landing")
            if fields is None:
                continue
            if not isinstance(fields, Mapping):
                return True
            normalized = {"approved": False, **dict(fields)}
            if normalized != default:
                return True
    return False


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
    reviewed = _has_landing_feature_review(candidate)
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
            elif isinstance(entry["landing"], Mapping) and "approved" not in entry["landing"]:
                normalized = {"approved": False, **dict(entry["landing"])}
                if normalized == _default_landing_fields(default_category):
                    entry["landing"] = normalized
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
            landing = entry.get("landing")
            if not isinstance(landing, Mapping):
                raise MTGOLandingError("Pickup entry has no Landing review fields")
            if landing.get("approved") is not True:
                continue
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
    current_top8: list[dict[str, Any]] = []
    if current["event_ids"]:
        current_top8 = pickup.week_records(
            events,
            rules,
            target_monday,
            processed_events=processed_events,
        )
        current_top8 = [record for record in current_top8 if record["is_top8"]]
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

    week = pickup.iso_week_label(target_monday)
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
    if current["event_ids"]:
        candidate_root = (
            Path(candidate_directory)
            if candidate_directory is not None
            else context.paths["statistics"] / "pickup"
        )
        candidate_path = candidate_root / f"candidates_{week}.yaml"
        if not candidate_path.is_file():
            raise MTGOLandingError(f"{candidate_path}: current Pickup candidate is missing")
        published_pickup_path = (
            context.paths["statistics"] / "pickup" / f"{week}.json"
        )
        published_pickup, pickup_document_digest = _load_published_pickup(
            published_pickup_path,
            format_id=format_id,
            week=week,
            source_event_ids=current["event_ids"],
            rules_digest=rules_digest,
            selection_policy_digest=selection_policy_digest,
        )
        review_inputs = _summary_review_inputs(observations, published_pickup)
        feature_status, features = _feature_document(
            candidate_path,
            week,
            current["event_ids"],
            rules_digest,
            selection_policy_digest,
            visual_metadata_digest,
            visual_diagnostics,
            machine_fact_digest,
        )
        summary_fact_digest = _summary_digest(
            week,
            current["event_ids"],
            rules_digest,
            selection_policy_digest,
            pickup_document_digest,
            review_inputs,
            deck_link_catalog,
        )
        if feature_status == "stale_review_required":
            review_status = feature_status
        else:
            summary_status, summary_items, summary_fact_digest = _summary_document(
                candidate_path,
                week,
                current["event_ids"],
                rules_digest,
                selection_policy_digest,
                pickup_document_digest,
                review_inputs,
                deck_link_catalog,
            )
            review_status = summary_status

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
            document["schema_version"] == LANDING_SCHEMA_VERSION
            and (
                not isinstance(binding.get("pickup_document_digest"), str)
                or not isinstance(binding.get("summary_fact_digest"), str)
            )
        )
    ):
        raise MTGOLandingError("Landing review binding is inconsistent")

    if document["schema_version"] == LANDING_SCHEMA_VERSION:
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
                link["label"] != _summary_deck_labels(link["deck"])
                for link in links
            ):
                raise MTGOLandingError("Landing weekly summary deck-link label is invalid")

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
            if document["schema_version"] == LANDING_SCHEMA_VERSION
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
        "summary_count": len(document["weekly_summary"]["items"]),
    }


__all__ = [
    "MTGOLandingError",
    "build_document",
    "generate",
    "load_visual_metadata",
    "validate_document",
]
