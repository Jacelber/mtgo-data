"""Landing-owned weekly screening and shared deck-selection helpers."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

import yaml

from mtgmeta.classifier import classify_deck
from mtgmeta.card_names import front_face_card_name

from . import load_mtgo_context
from . import stats
from .normalize import load_rules_for_format
from .top8 import classifier_digest
from .week_lifecycle import is_sealed, provisional_through, seal_on


SOURCE_ID = "mtgo"
INITIAL_KNOWN_WEEKS = 12
DEFAULT_POLICY_PATH = Path("configs/mtgo_pickup_policy.yaml")


class MTGOLandingScreeningError(RuntimeError):
    """Raised when Landing screening inputs cannot be produced safely."""


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


def load_screening_policy(
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
        raise MTGOLandingScreeningError(
            f"{path}: Landing screening policy could not be loaded"
        ) from exc
    if not isinstance(document, dict) or document.get("schema_version") != "1.0":
        raise MTGOLandingScreeningError(
            f"{path}: unsupported Landing screening policy"
        )

    thresholds = document.get("thresholds")
    required_thresholds = {
        "share_increase_pp",
        "return_share",
        "build_shift",
        "build_reference_minimum",
        "new_card_review_weeks",
    }
    if not isinstance(thresholds, dict) or not required_thresholds <= thresholds.keys():
        raise MTGOLandingScreeningError(
            f"{path}: incomplete Landing screening thresholds"
        )
    if thresholds["share_increase_pp"] != 5:
        raise MTGOLandingScreeningError(f"{path}: share increase must remain five points")
    if thresholds["return_share"] != 0.03:
        raise MTGOLandingScreeningError(f"{path}: return share must remain three percent")
    if thresholds["build_shift"] != 20:
        raise MTGOLandingScreeningError(f"{path}: build shift must remain twenty points")
    if thresholds["build_reference_minimum"] != stats.MIN_SAMPLE:
        raise MTGOLandingScreeningError(f"{path}: build reference minimum is incompatible")
    if thresholds["new_card_review_weeks"] != 2:
        raise MTGOLandingScreeningError(f"{path}: new-card review window must remain two weeks")

    continuity = document.get("identity_continuity")
    if not isinstance(continuity, dict):
        raise MTGOLandingScreeningError(f"{path}: identity_continuity must be a mapping")
    release_sets = document.get("release_sets")
    if not isinstance(release_sets, list):
        raise MTGOLandingScreeningError(f"{path}: release_sets must be a list")
    for item in release_sets:
        if not isinstance(item, dict):
            raise MTGOLandingScreeningError(f"{path}: release set must be a mapping")
        try:
            date.fromisoformat(str(item["arena_release_date"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise MTGOLandingScreeningError(f"{path}: invalid Arena release date") from exc
        cards = item.get("cards")
        if not isinstance(cards, list) or any(
            not isinstance(card, str) or not card.strip() for card in cards
        ):
            raise MTGOLandingScreeningError(f"{path}: release card manifest must be strings")
        if len(cards) != len(set(cards)):
            raise MTGOLandingScreeningError(f"{path}: release card manifest contains duplicates")
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
                raise MTGOLandingScreeningError(
                    "Landing screening source event has no numeric event_id"
                )
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
        raise MTGOLandingScreeningError("n_weeks must be a positive integer")
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
        raise MTGOLandingScreeningError(f"{source}: {field} must be a list of strings")
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
        raise MTGOLandingScreeningError("cannot select a representative from no records")
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
                raise MTGOLandingScreeningError(
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
        raise MTGOLandingScreeningError(
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
        names.add(front_face_card_name(name))
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


def _screening_directories(
    repository_root: str | Path,
    format_id: str,
    *,
    registry_path: str | Path | None,
    output_directory: str | Path | None,
) -> tuple[Path, Path]:
    context = load_mtgo_context(
        repository_root,
        format_id,
        "landing_generation",
        registry_path=registry_path,
    )
    configured = context.paths["statistics"] / "landing" / "review"
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
        raise MTGOLandingScreeningError(
            "Landing screening record could not reproduce its classified "
            f"identity: {result.status}"
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



def prepare_candidates(
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
    """Prepare private Landing screening candidates for one MTGO format."""

    configured, output = _screening_directories(
        repository_root,
        format_id,
        registry_path=registry_path,
        output_directory=output_directory,
    )
    rules = load_rules_for_format(
        repository_root, format_id, registry_path=registry_path
    )
    policy = load_screening_policy(repository_root, policy_file)
    policy_digest = document_digest(policy)
    events = stats.load_all_events(
        repository_root, format_id, registry_path=registry_path, public=False
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
    known = load_known(known_path, stable_ids=True)
    first_run = known is None
    if known is None:
        known = archetypes_in_window(
            events,
            rules,
            end_monday,
            INITIAL_KNOWN_WEEKS,
            stable_ids=True,
        )
    from .landing_editorial import build_candidate_documents

    candidates, base_reference, top8_count, deduplicated_count = (
        build_candidate_documents(
            events,
            rules,
            end_monday,
            known,
            policy,
            format_id,
            stable_ids=True,
        )
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

__all__ = [
    "INITIAL_KNOWN_WEEKS",
    "MTGOLandingScreeningError",
    "archetypes_in_window",
    "better_record",
    "deck_deviation",
    "deck_fingerprint",
    "document_digest",
    "iso_week_label",
    "load_known",
    "load_screening_policy",
    "prepare_candidates",
    "record_deck_cards",
    "week_records",
]
