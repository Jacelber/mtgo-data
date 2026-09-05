"""Private MTGO Landing screening, review, and bilingual editorial contracts."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from mtgmeta.public_contract import versioned

from . import landing_screening as screening, load_mtgo_context, stats
from .normalize import load_rules_for_format
from .top8 import classifier_digest


SOURCE_ID = "mtgo"
REVIEW_SCHEMA_VERSION = "1.0.0"
FORMAT_SCOPED_REVIEW_SCHEMA_VERSION = "1.1.0"
NAME_SCHEMA_VERSION = "1.0.0"
PUBLIC_NAME_SCHEMA_VERSION = "1.1.0"
DEFAULT_NAME_CATALOG = Path("configs/mtgo_archetype_names.yaml")
DEFAULT_REVIEW_SCHEMA = Path("schemas/mtgo-landing-review.schema.json")
DEFAULT_NAME_SCHEMA = Path("schemas/mtgo-archetype-names.schema.json")
PUBLIC_NAME_CONTRACT = "archetype_names.json"
DECK_TOKEN_PATTERN = re.compile(r"deck:[0-9a-f]{20}")
WORKBOOK_SHEETS = (
    "Review Control",
    "Landing Copy",
    "Featured Decks",
    "All Top 8",
    "Field Guide",
)
WORKBOOK_REVIEW_STAGES = {"chinese", "bilingual"}
_OOXML_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_OOXML_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PACKAGE_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


class MTGOLandingEditorialError(RuntimeError):
    """Raised when private Landing review data is incomplete, stale, or invalid."""


def document_digest(value: Any) -> str:
    """Return the canonical digest used by the Landing review boundary."""

    material = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_candidate_documents(
    events,
    rules,
    end_monday: date,
    known: set[str],
    policy: Mapping[str, Any],
    format_id: str,
    *,
    stable_ids: bool = False,
):
    """Screen and deduplicate Landing candidates while preserving machine evidence."""

    week_label = screening.iso_week_label(end_monday)
    end_sunday = end_monday + timedelta(days=6)
    reference_monday = end_monday - timedelta(weeks=1)
    reference_start = end_monday - timedelta(weeks=4)
    reference_end = end_monday - timedelta(days=1)
    processed_events = {
        id(event): stats.process_event(event, rules)
        for _event_date, event in events
    }
    current_records = screening.week_records(
        events,
        rules,
        end_monday,
        processed_events=processed_events,
    )
    all_top8_records = [record for record in current_records if record["is_top8"]]
    top8_records = [
        record for record in all_top8_records if record["archetype"] != "Unknown"
    ]
    reference_records = screening._records_in_period(
        events,
        rules,
        reference_start,
        reference_end,
        processed_events=processed_events,
    )
    historical_records = screening._records_in_period(
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
    active_sets = screening._active_release_sets(policy, end_monday)
    parent_definitions = {item.id: item for item in rules.archetypes}
    by_parent: dict[str, list[dict[str, Any]]] = {}
    for record in top8_records:
        by_parent.setdefault(str(record["archetype_id"]), []).append(record)

    selections: list[tuple[dict[str, Any], dict[str, Any]]] = []
    current_counts, current_denominator = screening._parent_high_score_counts(
        current_records
    )
    reference_counts, reference_denominator = screening._parent_high_score_counts(
        reference_records
    )
    historical_parent_ids = {
        str(record["archetype_id"])
        for record in historical_records
        if record["archetype"] != "Unknown"
    }
    for parent_id, records in by_parent.items():
        representative = screening._best_record(records)
        if not screening._is_known_record(
            representative, known, policy, format_id
        ):
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
            evidence = screening._new_card_evidence(record, release_set)
            if not evidence:
                continue
            key = (
                str(record["archetype_id"]),
                str(release_set["code"]),
                tuple(item["name"] for item in evidence),
            )
            candidate = (record, evidence)
            if key in new_card_groups:
                candidate = screening._prefer_new_card_record(
                    new_card_groups[key], candidate
                )
            new_card_groups[key] = candidate
    release_by_code = {str(item["code"]): item for item in active_sets}
    for (_parent_id, set_code, _package), (
        record,
        evidence,
    ) in new_card_groups.items():
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
        representative = screening._best_record(records)
        if screening._is_known_record(representative, known, policy, format_id):
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

    build_groups: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for record in top8_records:
        if not screening._is_known_record(record, known, policy, format_id):
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
        score = screening.deck_deviation(record, base)
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
            build_candidate = screening._prefer_build_shift_record(
                build_groups[identity_id], build_candidate
            )
        build_groups[identity_id] = build_candidate
    selections.extend(build_groups.values())

    entries: dict[tuple[str, str], dict[str, Any]] = {}
    for record, reason in selections:
        entry_key = (str(record["event_id"]), str(record["deck_id"]))
        known_record = screening._is_known_record(record, known, policy, format_id)
        entry = entries.setdefault(
            entry_key,
            screening._entry_for_record(
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
    existing_picks = [
        entry for entry in entries.values() if entry["source"] == "existing"
    ]
    new_picks = [entry for entry in entries.values() if entry["source"] == "new"]

    def sort_key(entry: Mapping[str, Any]) -> tuple[Any, ...]:
        return (
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
        base_reference["archetypes"][base["name"]] = {
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


def _column_index(reference: str) -> int:
    letters = "".join(character for character in reference if character.isalpha())
    result = 0
    for character in letters:
        result = result * 26 + ord(character.upper()) - ord("A") + 1
    return result - 1


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    namespace = {"x": _OOXML_MAIN}
    return [
        "".join(node.text or "" for node in item.findall(".//x:t", namespace))
        for item in root.findall("x:si", namespace)
    ]


def _sheet_targets(archive: zipfile.ZipFile) -> dict[str, str]:
    workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    relationships = ElementTree.fromstring(
        archive.read("xl/_rels/workbook.xml.rels")
    )
    relation_targets = {
        relation.attrib["Id"]: relation.attrib["Target"]
        for relation in relationships.findall(f"{{{_PACKAGE_REL}}}Relationship")
    }
    targets: dict[str, str] = {}
    for sheet in workbook.findall(f".//{{{_OOXML_MAIN}}}sheet"):
        name = sheet.attrib["name"]
        relation_id = sheet.attrib[f"{{{_OOXML_REL}}}id"]
        target = relation_targets[relation_id].replace("\\", "/").lstrip("/")
        while target.startswith("../"):
            target = target[3:]
        if not target.startswith("xl/"):
            target = f"xl/{target}"
        targets[name] = target
    return targets


def _cell_value(cell: ElementTree.Element, shared: list[str]) -> Any:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        text = "".join(
            node.text or "" for node in cell.findall(f".//{{{_OOXML_MAIN}}}t")
        )
        return text or None
    value_node = cell.find(f"{{{_OOXML_MAIN}}}v")
    if value_node is None or value_node.text is None or value_node.text == "":
        return None
    raw = value_node.text
    if cell_type == "s":
        try:
            return shared[int(raw)]
        except (ValueError, IndexError) as exc:
            raise MTGOLandingEditorialError(
                f"invalid shared-string index {raw!r}"
            ) from exc
    if cell_type in {"str", "e"}:
        return raw
    if cell_type == "b":
        return raw == "1"
    try:
        number = float(raw)
    except ValueError:
        return raw
    return int(number) if number.is_integer() else number


def _sheet_rows(
    archive: zipfile.ZipFile,
    target: str,
    shared: list[str],
) -> list[list[Any]]:
    root = ElementTree.fromstring(archive.read(target))
    rows: list[list[Any]] = []
    for row in root.findall(f".//{{{_OOXML_MAIN}}}row"):
        row_index = int(row.attrib.get("r", len(rows) + 1)) - 1
        while len(rows) < row_index:
            rows.append([])
        values: list[Any] = []
        for cell in row.findall(f"{{{_OOXML_MAIN}}}c"):
            index = _column_index(cell.attrib.get("r", "A1"))
            if index >= len(values):
                values.extend([None] * (index - len(values) + 1))
            values[index] = _cell_value(cell, shared)
        if len(rows) == row_index:
            rows.append(values)
        else:
            rows[row_index] = values
    return rows


def read_review_workbook(path: str | Path) -> dict[str, list[dict[str, Any]]]:
    """Read the Landing carrier with raw OOXML blank/shared-string semantics."""

    workbook_path = Path(path)
    try:
        with zipfile.ZipFile(workbook_path) as archive:
            shared = _shared_strings(archive)
            targets = _sheet_targets(archive)
            missing = sorted(set(WORKBOOK_SHEETS) - targets.keys())
            if missing:
                raise MTGOLandingEditorialError(
                    "review workbook is missing sheets: " + ", ".join(missing)
                )
            result: dict[str, list[dict[str, Any]]] = {}
            for name in WORKBOOK_SHEETS:
                rows = _sheet_rows(archive, targets[name], shared)
                if len(rows) < 4:
                    raise MTGOLandingEditorialError(
                        f"review workbook sheet {name!r} has no header row"
                    )
                headers = [str(value).strip() if value is not None else "" for value in rows[3]]
                if not headers or not headers[0]:
                    raise MTGOLandingEditorialError(
                        f"review workbook sheet {name!r} has an invalid header"
                    )
                entries: list[dict[str, Any]] = []
                for values in rows[4:]:
                    padded = values + [None] * max(0, len(headers) - len(values))
                    row = {
                        header: padded[index]
                        for index, header in enumerate(headers)
                        if header
                    }
                    if any(value is not None and value != "" for value in row.values()):
                        entries.append(row)
                result[name] = entries
            return result
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        raise MTGOLandingEditorialError(
            f"{workbook_path}: review workbook could not be read"
        ) from exc


def _identity_key(format_id: str, parent_id: str, subtype_id: str | None) -> str:
    return f"{format_id}|{parent_id}|{subtype_id or 'none'}"


def _display_english(parent_name: str, subtype_name: str | None) -> str:
    if subtype_name is None:
        return parent_name
    if parent_name in subtype_name:
        return subtype_name
    parent_words = parent_name.split()
    subtype_words = subtype_name.split()
    if subtype_words == parent_words[: len(subtype_words)]:
        return parent_name
    color_prefixes = {
        "Azorius",
        "Bant",
        "Boros",
        "Dimir",
        "Esper",
        "Golgari",
        "Grixis",
        "Gruul",
        "Izzet",
        "Jeskai",
        "Jund",
        "Mardu",
        "Naya",
        "Orzhov",
        "Rakdos",
        "Selesnya",
        "Simic",
        "Sultai",
        "Temur",
    }
    if parent_words[0] in color_prefixes:
        return " ".join([*subtype_words, *parent_words[1:]])
    return " ".join([*subtype_words, *parent_words])


def _taxonomy_rows(repository_root: Path, format_id: str) -> list[dict[str, Any]]:
    rules = load_rules_for_format(repository_root, format_id)
    rows: list[dict[str, Any]] = []
    for parent in rules.archetypes:
        rows.append(
            {
                "format": format_id,
                "parent_id": parent.id,
                "subtype_id": None,
                "english": parent.name,
                "identity_key": _identity_key(format_id, parent.id, None),
            }
        )
        for subtype in parent.subtypes:
            rows.append(
                {
                    "format": format_id,
                    "parent_id": parent.id,
                    "subtype_id": subtype.id,
                    "english": _display_english(parent.name, subtype.name),
                    "identity_key": _identity_key(format_id, parent.id, subtype.id),
                }
            )
    return rows


def _schema_validator(path: Path) -> Draft202012Validator:
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MTGOLandingEditorialError(f"{path}: internal Schema could not be loaded") from exc
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate_schema(document: Any, path: Path, subject: str) -> None:
    errors = sorted(_schema_validator(path).iter_errors(document), key=lambda item: list(item.path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "root"
        raise MTGOLandingEditorialError(
            f"{subject} does not match its internal Schema at {location}: {first.message}"
        )


def load_name_catalog_document(path: str | Path) -> dict[str, Any]:
    catalog_path = Path(path)
    try:
        document = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise MTGOLandingEditorialError(
            f"{catalog_path}: bilingual name catalog could not be loaded"
        ) from exc
    if not isinstance(document, dict):
        raise MTGOLandingEditorialError(
            f"{catalog_path}: bilingual name catalog must be a mapping"
        )
    return document


def load_name_catalog(path: str | Path) -> dict[tuple[str, str, str | None], dict[str, str]]:
    """Load an already validated bilingual name catalog for exact identity lookup."""

    document = load_name_catalog_document(path)
    names: dict[tuple[str, str, str | None], dict[str, str]] = {}
    for item in document.get("names", []):
        if not isinstance(item, Mapping):
            raise MTGOLandingEditorialError("bilingual name catalog row is invalid")
        key = (str(item.get("format")), str(item.get("parent_id")), item.get("subtype_id"))
        if key in names:
            raise MTGOLandingEditorialError(
                "bilingual name catalog identity is duplicated: " + "|".join(str(part) for part in key)
            )
        names[key] = {"en": str(item.get("english") or ""), "zh": str(item.get("chinese") or "")}
    return names


def validate_name_catalog(
    repository_root: str | Path,
    catalog_path: str | Path | None = None,
    formats: set[str] | None = None,
) -> dict[str, int]:
    """Fail closed unless the catalog covers the selected current taxonomies."""

    root = Path(repository_root).resolve()
    path = Path(catalog_path) if catalog_path is not None else root / DEFAULT_NAME_CATALOG
    document = load_name_catalog_document(path)
    return _validate_name_catalog_document(root, document, formats=formats)


def _validate_name_catalog_document(
    repository_root: Path,
    document: Mapping[str, Any],
    *,
    formats: set[str] | None = None,
) -> dict[str, int]:
    """Validate one in-memory bilingual catalog against the current taxonomy."""

    root = repository_root.resolve()
    _validate_schema(document, root / DEFAULT_NAME_SCHEMA, "bilingual name catalog")
    selected = formats or {"standard", "modern"}
    expected = {
        row["identity_key"]: row
        for format_id in sorted(selected)
        for row in _taxonomy_rows(root, format_id)
    }
    actual: dict[str, Mapping[str, Any]] = {}
    for item in document["names"]:
        identity_key = str(item["identity_key"])
        if identity_key in actual:
            raise MTGOLandingEditorialError(
                f"bilingual name catalog identity is duplicated: {identity_key}"
            )
        if item.get("format") in selected:
            actual[identity_key] = item
    missing = sorted(expected.keys() - actual.keys())
    extra = sorted(actual.keys() - expected.keys())
    mismatched = sorted(
        key
        for key in expected.keys() & actual.keys()
        if actual[key].get("format") != expected[key]["format"]
        or actual[key].get("parent_id") != expected[key]["parent_id"]
        or actual[key].get("subtype_id") != expected[key]["subtype_id"]
        or actual[key].get("english") != expected[key]["english"]
        or actual[key].get("review_status") != "approved"
        or not str(actual[key].get("chinese") or "").strip()
    )
    if missing or extra or mismatched:
        details = []
        if missing:
            details.append("missing=" + ",".join(missing[:5]))
        if extra:
            details.append("extra=" + ",".join(extra[:5]))
        if mismatched:
            details.append("mismatched=" + ",".join(mismatched[:5]))
        raise MTGOLandingEditorialError(
            "bilingual name catalog coverage is incomplete or stale: " + "; ".join(details)
        )
    return {
        "name_count": len(actual),
        "parent_count": sum(item["subtype_id"] is None for item in actual.values()),
        "subtype_count": sum(item["subtype_id"] is not None for item in actual.values()),
    }


def build_public_name_contract(
    repository_root: str | Path,
    format_id: str,
    *,
    catalog_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build one public bilingual name contract from the approved private catalog."""

    root = Path(repository_root).resolve()
    path = Path(catalog_path) if catalog_path is not None else root / DEFAULT_NAME_CATALOG
    validate_name_catalog(root, path, formats={format_id})
    catalog = load_name_catalog_document(path)
    taxonomy_rows = _taxonomy_rows(root, format_id)
    identity_subject = [
        {
            "parent_id": item["parent_id"],
            "subtype_id": item["subtype_id"],
        }
        for item in taxonomy_rows
    ]
    identity_subject.sort(
        key=lambda item: (item["parent_id"], item["subtype_id"] or "")
    )
    authority_subject = [
        dict(item) for item in catalog["names"] if item["format"] == format_id
    ]
    authority_subject.sort(key=lambda item: item["identity_key"])
    classifier_identity_digest = document_digest(
        {"format": format_id, "identities": identity_subject}
    )
    name_catalog_digest = document_digest(
        {"format": format_id, "names": authority_subject}
    )
    projection_subject_digest = document_digest(
        {
            "format": format_id,
            "classifier_identity_digest": classifier_identity_digest,
            "name_catalog_digest": name_catalog_digest,
        }
    )
    names = []
    for item in catalog["names"]:
        if item["format"] != format_id:
            continue
        subtype_id = item["subtype_id"]
        identity_id = (
            f"{item['parent_id']}/{subtype_id}"
            if subtype_id is not None
            else item["parent_id"]
        )
        names.append(
            {
                "identity_id": identity_id,
                "parent_id": item["parent_id"],
                "subtype_id": subtype_id,
                "display": {
                    "en": item["english"],
                    "zh": item["chinese"],
                },
            }
        )
    if not names:
        raise MTGOLandingEditorialError(
            f"bilingual name catalog has no approved identities for {format_id}"
        )
    names.sort(key=lambda item: item["identity_id"])
    return versioned(
        {
            "format": format_id,
            "provenance": {
                "classifier_identity_digest": classifier_identity_digest,
                "name_catalog_digest": name_catalog_digest,
                "projection_subject_digest": projection_subject_digest,
            },
            "names": names,
        },
        schema_version=PUBLIC_NAME_SCHEMA_VERSION,
    )


def generate_public_name_contract(
    repository_root: str | Path,
    format_id: str,
    *,
    catalog_path: str | Path | None = None,
    output_directory: str | Path | None = None,
) -> Path:
    """Write the format-scoped public bilingual name contract."""

    root = Path(repository_root).resolve()
    output = (
        Path(output_directory).resolve()
        if output_directory is not None
        else root / "stats" / format_id
    )
    output.mkdir(parents=True, exist_ok=True)
    destination = output / PUBLIC_NAME_CONTRACT
    destination.write_text(
        json.dumps(
            build_public_name_contract(root, format_id, catalog_path=catalog_path),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
        newline="\n",
    )
    return destination


def _week_monday(week: str) -> date:
    try:
        return datetime.strptime(f"{week}-1", "%G-W%V-%u").date()
    except ValueError as exc:
        raise MTGOLandingEditorialError(f"invalid ISO review week: {week}") from exc


def build_top8_subject(
    repository_root: str | Path,
    format_id: str,
    week: str,
) -> dict[str, Any]:
    """Build the exact classified Top 8 and provenance subject for one week."""

    root = Path(repository_root).resolve()
    context = load_mtgo_context(root, format_id, "landing_generation")
    rules = load_rules_for_format(root, format_id)
    events = stats.load_all_events(root, format_id, public=False)
    monday = _week_monday(week)
    records = [
        record
        for record in screening.week_records(events, rules, monday)
        if record.get("is_top8")
    ]
    catalog = build_top8_catalog(records)
    week_records = [
        record
        for event_date, event in events
        if monday <= event_date <= monday + timedelta(days=6)
        for record in stats.process_event(event, rules)["records"]
        if record.get("archetype") != "Unknown"
    ]
    source_event_ids = sorted({item["event_id"] for item in catalog})
    known_archetype_ids = sorted(
        {str(record["archetype_id"]) for record in week_records}
    )
    candidate_path = (
        context.paths["statistics"]
        / "landing"
        / "review"
        / f"candidates_{week}.yaml"
    )
    candidate: Mapping[str, Any] | None = None
    if candidate_path.is_file():
        loaded = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
        if isinstance(loaded, Mapping):
            candidate = loaded
    candidate_evidence: list[dict[str, Any]] = []
    if candidate is not None:
        source_order = 0
        for collection in ("new_archetypes", "existing_changes"):
            for item in candidate.get(collection, []):
                if not isinstance(item, Mapping):
                    continue
                source_order += 1
                token = f"deck:{item.get('deck_id')}"
                if token not in set(item["token"] for item in catalog):
                    continue
                candidate_evidence.append(
                    {
                        "token": token,
                        "source_order": source_order,
                        "reasons": [
                            dict(reason)
                            for reason in item.get("candidate_reasons", [])
                            if isinstance(reason, Mapping)
                        ],
                    }
                )
    from . import landing

    machine_fact_digest = landing.machine_fact_digest_for_week(root, format_id, week)
    candidate_machine_fact_digest = (
        str(candidate.get("machine_fact_digest"))
        if candidate is not None and isinstance(candidate.get("machine_fact_digest"), str)
        else None
    )
    if (
        candidate_machine_fact_digest is not None
        and candidate_machine_fact_digest != machine_fact_digest
    ):
        raise MTGOLandingEditorialError(
            f"{candidate_path}: machine_fact_digest is stale"
        )
    return {
        "format": format_id,
        "week": {
            "id": week,
            "start": monday.isoformat(),
            "end": (monday + timedelta(days=6)).isoformat(),
        },
        "source_event_ids": source_event_ids,
        "classifier_digest": classifier_digest(rules),
        "selection_policy_digest": document_digest(screening.load_screening_policy(root)),
        "machine_fact_digest": machine_fact_digest,
        "link_catalog_digest": document_digest(catalog),
        "candidate_evidence": candidate_evidence,
        "all_top8": catalog,
        "known_archetype_ids": known_archetype_ids,
    }


def build_top8_catalog(records: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Build the stable exact-deck catalog shared by import and Landing generation."""

    catalog: list[dict[str, Any]] = []
    for record in records:
        event_id = str(record.get("event_id") or "")
        deck_id = str(record.get("deck_id") or "")
        rank = record.get("final_rank")
        if not event_id.isdigit() or not re.fullmatch(r"[0-9a-f]{20}", deck_id):
            raise MTGOLandingEditorialError("classified Top 8 record has an invalid exact identity")
        if not isinstance(rank, int) or isinstance(rank, bool) or not 1 <= rank <= 8:
            raise MTGOLandingEditorialError("classified Top 8 record has an invalid rank")
        fingerprint = hashlib.sha256(
            json.dumps(
                screening.deck_fingerprint(record),
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        catalog.append(
            {
                "token": f"deck:{deck_id}",
                "event_id": event_id,
                "deck_id": deck_id,
                "deck_fingerprint_sha256": fingerprint,
                "date": str(record.get("starttime") or "")[:10],
                "starttime": str(record.get("starttime") or ""),
                "final_rank": rank,
                "player_count": int(record.get("player_count") or 0),
                "player": str(record.get("player") or ""),
                "parent_id": str(record.get("archetype_id") or ""),
                "subtype_id": record.get("subtype_id"),
                "display_name": str(record.get("archetype") or ""),
                "main_deck": screening.record_deck_cards(record)["main_deck"],
                "side_deck": screening.record_deck_cards(record)["side_deck"],
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
    tokens = [item["token"] for item in catalog]
    placements = [(item["event_id"], item["final_rank"]) for item in catalog]
    if len(tokens) != len(set(tokens)) or len(placements) != len(set(placements)):
        raise MTGOLandingEditorialError("classified Top 8 identities are duplicated")
    return catalog


def _event_id(value: Any) -> str:
    match = re.search(r"([0-9]+)\s*$", str(value or ""))
    return match.group(1) if match else ""


def _catalog_from_workbook(
    repository_root: Path,
    rows: list[dict[str, Any]],
    *,
    formats: set[str] | None = None,
) -> dict[str, Any]:
    selected = formats or {"standard", "modern"}
    taxonomy = {
        row["identity_key"]: row
        for format_id in sorted(selected)
        for row in _taxonomy_rows(repository_root, format_id)
    }
    names: list[dict[str, Any]] = []
    for row in rows:
        format_id = str(row.get("Format") or "")
        if format_id not in selected:
            continue
        if row.get("Review Result") != "APPROVED":
            raise MTGOLandingEditorialError("bilingual name row lacks explicit APPROVED review")
        parent_id = str(row.get("Parent ID") or "")
        subtype_id = str(row.get("Subtype ID") or "").strip() or None
        identity_key = _identity_key(format_id, parent_id, subtype_id)
        if row.get("Identity Key") != identity_key:
            raise MTGOLandingEditorialError(
                f"bilingual name identity key changed: {row.get('Identity Key')!r}"
            )
        if identity_key not in taxonomy:
            raise MTGOLandingEditorialError(
                f"bilingual name identity is absent from the classifier: {identity_key}"
            )
        names.append(
            {
                "format": format_id,
                "parent_id": parent_id,
                "subtype_id": subtype_id,
                "english": taxonomy[identity_key]["english"],
                "chinese": str(row.get("Chinese Final") or "").strip(),
                "review_status": "approved",
                "identity_key": identity_key,
            }
        )
    workbook_keys = {item["identity_key"] for item in names}
    if workbook_keys != set(taxonomy):
        missing = sorted(set(taxonomy) - workbook_keys)
        extra = sorted(workbook_keys - set(taxonomy))
        raise MTGOLandingEditorialError(
            "workbook name scope is incomplete or stale: "
            f"missing={missing[:5]}; extra={extra[:5]}"
        )
    current_path = repository_root / DEFAULT_NAME_CATALOG
    if current_path.is_file():
        current_document = load_name_catalog_document(current_path)
        selected_rows = {item["identity_key"]: item for item in names}
        merged: list[dict[str, Any]] = []
        for item in current_document["names"]:
            if item["format"] in selected:
                replacement = selected_rows.pop(item["identity_key"], None)
                if replacement is not None:
                    merged.append(replacement)
            else:
                merged.append(dict(item))
        merged.extend(
            selected_rows[key]
            for key in sorted(selected_rows)
        )
        names = merged
    document = {"schema_version": NAME_SCHEMA_VERSION, "names": names}
    _validate_schema(
        document,
        repository_root / DEFAULT_NAME_SCHEMA,
        "imported bilingual name catalog",
    )
    _validate_name_catalog_document(repository_root, document, formats=selected)
    return document


def _name_lookup_from_document(
    document: Mapping[str, Any],
) -> dict[tuple[str, str, str | None], dict[str, str]]:
    names: dict[tuple[str, str, str | None], dict[str, str]] = {}
    for item in document["names"]:
        key = (item["format"], item["parent_id"], item["subtype_id"])
        names[key] = {"en": item["english"], "zh": item["chinese"]}
    return names


def _control_scopes(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    scopes: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        format_id = str(row.get("Format") or "").strip()
        week = str(row.get("Week") or "").strip()
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", format_id) or not re.fullmatch(
            r"[0-9]{4}-W[0-9]{2}", week
        ):
            continue
        key = (format_id, week)
        if key in scopes:
            raise MTGOLandingEditorialError(f"review control scope is duplicated: {format_id} {week}")
        scopes[key] = row
    if not scopes:
        raise MTGOLandingEditorialError("review workbook contains no valid scopes")
    return scopes


def _copy_rows_by_scope(
    scopes: Mapping[tuple[str, str], Mapping[str, Any]],
    rows: list[dict[str, Any]],
    *,
    stage: str = "bilingual",
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    if stage not in WORKBOOK_REVIEW_STAGES:
        raise ValueError(f"unsupported workbook review stage: {stage}")
    result = {key: [] for key in scopes}
    copy_scope_by_format: dict[str, tuple[str, str]] = {}
    for format_id in sorted({key[0] for key in scopes}):
        format_scopes = [key for key in scopes if key[0] == format_id]
        if len(format_scopes) == 1:
            copy_scope_by_format[format_id] = format_scopes[0]
            continue
        legacy_scopes = [
            key
            for key in format_scopes
            if scopes[key].get("Top Copy Review") == "APPROVED"
        ]
        if len(legacy_scopes) != 1:
            raise MTGOLandingEditorialError(
                f"review workbook has ambiguous top-copy weeks for {format_id}"
            )
        copy_scope_by_format[format_id] = legacy_scopes[0]
    orders: dict[tuple[str, str], set[int]] = {key: set() for key in scopes}
    for row in rows:
        if row.get("Review Result") != "KEEP":
            continue
        format_id = str(row.get("Format") or "")
        if format_id not in copy_scope_by_format:
            if format_id not in {scope[0] for scope in scopes}:
                continue
            raise MTGOLandingEditorialError(f"kept top copy has no valid scope: {format_id}")
        key = copy_scope_by_format[format_id]
        order = row.get("Order")
        if not isinstance(order, int) or isinstance(order, bool) or order < 1:
            raise MTGOLandingEditorialError("kept top copy requires a positive integer order")
        if order in orders[key]:
            raise MTGOLandingEditorialError(f"top-copy order is duplicated for {format_id}")
        orders[key].add(order)
        zh = str(row.get("Chinese Copy") or "").strip()
        if not zh:
            raise MTGOLandingEditorialError("kept top copy requires Chinese final text")
        en = str(row.get("English Final") or "").strip()
        if stage == "bilingual" and not en:
            raise MTGOLandingEditorialError("kept top copy requires English final text")
        if stage == "chinese":
            en = zh
        result[key].append({"order": order, "text": {"zh": zh, "en": en}})
    for items in result.values():
        items.sort(key=lambda item: item["order"])
    return result


def _verify_workbook_top8(
    scope: tuple[str, str],
    subject: Mapping[str, Any],
    rows: list[dict[str, Any]],
) -> None:
    format_id, week = scope
    workbook_rows = [
        row
        for row in rows
        if row.get("Format") == format_id and row.get("Week") == week
    ]
    if not workbook_rows:
        return
    by_token = {item["token"]: item for item in subject["all_top8"]}
    if {str(row.get("Deck Link ID")) for row in workbook_rows} != set(by_token):
        raise MTGOLandingEditorialError(f"{format_id} {week} All Top 8 catalog changed")
    for row in workbook_rows:
        deck = by_token[str(row["Deck Link ID"])]
        expected = {
            "event_id": _event_id(row.get("Event")),
            "date": str(row.get("Date") or ""),
            "rank": row.get("Rank"),
            "display_name": str(row.get("Deck") or ""),
            "player": str(row.get("Player") or ""),
        }
        actual = {
            "event_id": deck["event_id"],
            "date": deck["date"],
            "rank": deck["final_rank"],
            "display_name": deck["display_name"],
            "player": deck["player"],
        }
        if expected != actual:
            raise MTGOLandingEditorialError(
                f"{format_id} {week} All Top 8 identity changed for {deck['token']}"
            )


def _feature_rows_by_scope(
    scopes: Mapping[tuple[str, str], Mapping[str, Any]],
    rows: list[dict[str, Any]],
    subjects: Mapping[tuple[str, str], Mapping[str, Any]],
    names: Mapping[tuple[str, str, str | None], Mapping[str, str]],
    *,
    stage: str = "bilingual",
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    if stage not in WORKBOOK_REVIEW_STAGES:
        raise ValueError(f"unsupported workbook review stage: {stage}")
    result = {key: [] for key in scopes}
    evidence = {
        key: {item["token"]: item["reasons"] for item in subject["candidate_evidence"]}
        for key, subject in subjects.items()
    }
    for source_order, row in enumerate(rows, start=1):
        if row.get("Selection") != "KEEP":
            continue
        key = (str(row.get("Format") or ""), str(row.get("Feature Week") or ""))
        if key not in scopes:
            if key[0] not in {
                scope[0] for scope in scopes
            }:
                continue
            raise MTGOLandingEditorialError(f"kept feature has no valid scope: {key}")
        subject = subjects[key]
        by_token = {item["token"]: item for item in subject["all_top8"]}
        token = str(row.get("Deck Link ID") or "")
        if token not in by_token:
            raise MTGOLandingEditorialError(f"kept feature references an unknown deck: {token}")
        deck = by_token[token]
        subtype_id = str(row.get("Subtype ID") or "").strip() or None
        identity = (key[0], str(row.get("Parent ID") or ""), subtype_id)
        if identity not in names:
            raise MTGOLandingEditorialError(f"kept feature lacks bilingual identity: {identity}")
        identity_key = _identity_key(*identity)
        expected = {
            "event_id": _event_id(row.get("Event")),
            "date": str(row.get("Date") or ""),
            "rank": row.get("Rank"),
            "display_name": str(row.get("Deck Name EN") or ""),
            "player": str(row.get("Player") or ""),
            "parent_id": identity[1],
            "subtype_id": identity[2],
        }
        actual = {
            "event_id": deck["event_id"],
            "date": deck["date"],
            "rank": deck["final_rank"],
            "display_name": deck["display_name"],
            "player": deck["player"],
            "parent_id": deck["parent_id"],
            "subtype_id": deck["subtype_id"],
        }
        if expected != actual or row.get("Identity Key") != identity_key:
            raise MTGOLandingEditorialError(f"kept feature identity changed: {token}")
        if row.get("Name Status") != "APPROVED" or row.get("Deck Name ZH") != names[identity]["zh"]:
            raise MTGOLandingEditorialError(f"kept feature bilingual title changed: {token}")
        category = str(row.get("Category") or "")
        if category not in {"new_deck", "new_technology"}:
            raise MTGOLandingEditorialError(f"kept feature category is invalid: {token}")
        positioning_zh = str(row.get("Chinese Positioning") or "").strip()
        positioning_en = str(row.get("English Final") or "").strip()
        if not positioning_zh:
            raise MTGOLandingEditorialError(
                f"kept feature Chinese positioning is incomplete: {token}"
            )
        if stage == "bilingual" and not positioning_en:
            raise MTGOLandingEditorialError(
                f"kept feature English positioning is incomplete: {token}"
            )
        positioning = {
            "zh": positioning_zh,
            "en": positioning_en if stage == "bilingual" else positioning_zh,
        }
        featured_cards = [
            str(row.get(f"Featured Card {index}") or "").strip()
            for index in range(1, 5)
        ]
        if len(set(featured_cards)) != 4 or not all(featured_cards):
            raise MTGOLandingEditorialError(f"kept feature requires four unique cards: {token}")
        deck_cards = {card["name"] for zone in ("main_deck", "side_deck") for card in deck[zone]}
        if not set(featured_cards) <= deck_cards:
            raise MTGOLandingEditorialError(f"kept feature cards changed for exact deck: {token}")
        result[key].append(
            {
                "source_order": source_order,
                "category": category,
                "destination_id": token,
                "parent_id": deck["parent_id"],
                "subtype_id": deck["subtype_id"],
                "positioning": positioning,
                "featured_cards": featured_cards,
                "supporting_facts": evidence[key].get(token, []),
            }
        )
    return result


def copy_deck_tokens(items: list[Mapping[str, Any]]) -> list[str]:
    """Return exact deck tokens in final copy order, deduplicated by first use."""

    tokens: list[str] = []
    for item in sorted(items, key=lambda value: value["order"]):
        localized: list[list[str]] = []
        for language in ("zh", "en"):
            text = str(item["text"][language])
            localized.append(list(dict.fromkeys(DECK_TOKEN_PATTERN.findall(text))))
        if set(localized[0]) != set(localized[1]):
            raise MTGOLandingEditorialError(
                "localized top-copy deck-token sets do not match"
            )
        for token in localized[0]:
            if token not in tokens:
                tokens.append(token)
    return tokens


def validate_review_document(document: Mapping[str, Any], schema_path: str | Path) -> None:
    _validate_schema(document, Path(schema_path), "Landing review document")
    top8_tokens = [item["token"] for item in document["all_top8"]]
    if top8_tokens != sorted(
        top8_tokens,
        key=lambda token: next(
            (
                item["starttime"],
                item["event_id"],
                item["final_rank"],
                item["deck_id"],
            )
            for item in document["all_top8"]
            if item["token"] == token
        ),
    ) or len(top8_tokens) != len(set(top8_tokens)):
        raise MTGOLandingEditorialError("Landing review Top 8 catalog order or identity is invalid")
    feature_items = document["review"]["features"]["items"]
    feature_tokens = [item["destination_id"] for item in feature_items]
    if len(feature_tokens) != len(set(feature_tokens)):
        raise MTGOLandingEditorialError("Landing review feature deck identity is duplicated")
    copy_tokens = copy_deck_tokens(document["review"]["top_copy"]["items"])
    unknown = sorted(set(copy_tokens) - set(feature_tokens))
    if unknown:
        raise MTGOLandingEditorialError(
            "Landing top-copy token lacks an exact selected feature: " + ", ".join(unknown)
        )
    catalog_tokens = set(top8_tokens)
    missing = sorted(set(feature_tokens) - catalog_tokens)
    if missing:
        raise MTGOLandingEditorialError(
            "Landing feature is absent from the exact Top 8 catalog: " + ", ".join(missing)
        )
    decks = {item["token"]: item for item in document["all_top8"]}
    for feature in feature_items:
        deck = decks[feature["destination_id"]]
        deck_cards = {
            card["name"]
            for zone in ("main_deck", "side_deck")
            for card in deck[zone]
        }
        if not deck_cards or not set(feature["featured_cards"]) <= deck_cards:
            raise MTGOLandingEditorialError(
                "Landing feature cards do not match its exact reviewed deck: "
                + feature["destination_id"]
            )


def load_review_document(
    path: str | Path,
    schema_path: str | Path | None = None,
) -> dict[str, Any]:
    review_path = Path(path)
    try:
        document = yaml.safe_load(review_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise MTGOLandingEditorialError(f"{review_path}: Landing review could not be loaded") from exc
    if not isinstance(document, dict):
        raise MTGOLandingEditorialError(f"{review_path}: Landing review must be a mapping")
    resolved_schema = Path(schema_path) if schema_path is not None else next(
        (
            parent / DEFAULT_REVIEW_SCHEMA
            for parent in review_path.parents
            if (parent / DEFAULT_REVIEW_SCHEMA).is_file()
        ),
        None,
    )
    if resolved_schema is not None:
        validate_review_document(document, resolved_schema)
    return document


def validate_review_binding(
    document: Mapping[str, Any],
    current: Mapping[str, Any],
) -> None:
    """Reject a reviewed week when any machine or provenance subject changed."""

    for field in (
        "workbook_sha256",
        "source_event_ids",
        "classifier_digest",
        "selection_policy_digest",
        "machine_fact_digest",
        "link_catalog_digest",
        "bilingual_catalog_digest",
    ):
        if document["bindings"].get(field) != current.get(field):
            raise MTGOLandingEditorialError(
                f"Landing review {field.replace('_', ' ')} changed; explicit re-review is required"
            )


def materialize_review(
    document: Mapping[str, Any],
    names: Mapping[tuple[str, str, str | None], Mapping[str, str]],
) -> dict[str, list[dict[str, Any]]]:
    """Derive localized titles, links, and feature order from one reviewed source."""

    format_id = str(document["format"])
    decks = {item["token"]: item for item in document["all_top8"]}
    summary_items: list[dict[str, Any]] = []
    for item in sorted(document["review"]["top_copy"]["items"], key=lambda value: value["order"]):
        tokens = list(dict.fromkeys(DECK_TOKEN_PATTERN.findall(item["text"]["zh"])))
        links: list[dict[str, Any]] = []
        for order, token in enumerate(tokens, start=1):
            deck = decks[token]
            name = names[(format_id, deck["parent_id"], deck["subtype_id"])]
            links.append(
                {
                    "order": order,
                    "token": token,
                    "label": {
                        "zh": f"{name['zh']} · {deck['player']} · 第{deck['final_rank']}名",
                        "en": f"{name['en']} · {deck['player']} · Rank {deck['final_rank']}",
                    },
                    "deck": {
                        "archetype_id": deck["parent_id"],
                        "display_name": name["en"],
                        "event_id": deck["event_id"],
                        "deck_id": deck["deck_id"],
                        "deck_fingerprint_sha256": deck["deck_fingerprint_sha256"],
                        "player": deck["player"],
                        "final_rank": deck["final_rank"],
                        "starttime": deck["starttime"],
                    },
                }
            )
        summary_items.append(
            {"order": item["order"], "text": dict(item["text"]), "deck_links": links}
        )

    copy_order = {token: index for index, token in enumerate(copy_deck_tokens(document["review"]["top_copy"]["items"]))}
    category_order = {"new_deck": 0, "new_technology": 1}
    source_features = sorted(
        document["review"]["features"]["items"],
        key=lambda item: (
            category_order[item["category"]],
            copy_order.get(item["destination_id"], 10**9),
            item["source_order"],
            item["destination_id"],
        ),
    )
    category_counts = {"new_deck": 0, "new_technology": 0}
    features: list[dict[str, Any]] = []
    for item in source_features:
        category = item["category"]
        category_counts[category] += 1
        deck = decks[item["destination_id"]]
        name = names[(format_id, item["parent_id"], item["subtype_id"])]
        features.append(
            {
                "category": category,
                "order": category_counts[category],
                "destination_id": item["destination_id"],
                "archetype_id": item["parent_id"],
                "subtype_id": item["subtype_id"],
                "display_name": name["en"],
                "title": dict(name),
                "deck": {
                    key: deck[key]
                    for key in (
                        "event_id",
                        "deck_id",
                        "deck_fingerprint_sha256",
                        "player",
                        "final_rank",
                        "player_count",
                        "starttime",
                        "main_deck",
                        "side_deck",
                    )
                },
                "positioning": dict(item["positioning"]),
                "featured_cards": [{"name": card} for card in item["featured_cards"]],
                "supporting_facts": [dict(fact) for fact in item["supporting_facts"]],
            }
        )
    return {"weekly_summary": summary_items, "features": features}


def _write_yaml(path: Path, document: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            dict(document),
            allow_unicode=True,
            sort_keys=False,
            width=1000,
        ),
        encoding="utf-8",
        newline="\n",
    )


def _known_ids(repository_root: Path, format_id: str) -> set[str]:
    path = repository_root / f"stats/{format_id}/mtgo/landing/review/known_archetypes.json"
    if not path.is_file():
        return set()
    document = json.loads(path.read_text(encoding="utf-8"))
    known_ids = document.get("known_ids")
    if not isinstance(known_ids, list) or any(
        not isinstance(value, str) for value in known_ids
    ):
        raise MTGOLandingEditorialError(f"{path}: Landing known state is invalid")
    return set(known_ids)


def _validated_workbook_subject(
    repository_root: str | Path,
    workbook_path: str | Path,
    *,
    expected_sha256: str | None = None,
    formats: set[str] | None = None,
    stage: str = "bilingual",
) -> dict[str, Any]:
    if stage not in WORKBOOK_REVIEW_STAGES:
        raise ValueError(f"unsupported workbook review stage: {stage}")

    root = Path(repository_root).resolve()
    workbook = Path(workbook_path).resolve()
    workbook_digest = file_sha256(workbook)
    if expected_sha256 is not None and workbook_digest != expected_sha256:
        raise MTGOLandingEditorialError(
            f"accepted workbook SHA-256 changed: expected {expected_sha256}, got {workbook_digest}"
        )
    sheets = read_review_workbook(workbook)
    scopes = _control_scopes(sheets["Review Control"])
    if formats is not None:
        scopes = {scope: row for scope, row in scopes.items() if scope[0] in formats}
        if not scopes:
            raise MTGOLandingEditorialError(
                "review workbook has no valid scope for the requested format"
            )
    selected_formats = {scope[0] for scope in scopes}
    catalog_document = _catalog_from_workbook(
        root,
        sheets["Field Guide"],
        formats=selected_formats,
    )
    names = _name_lookup_from_document(catalog_document)
    subjects = {scope: build_top8_subject(root, *scope) for scope in scopes}
    for scope, subject in subjects.items():
        _verify_workbook_top8(scope, subject, sheets["All Top 8"])
    copy_rows = _copy_rows_by_scope(
        scopes,
        sheets["Landing Copy"],
        stage=stage,
    )
    feature_rows = _feature_rows_by_scope(
        scopes,
        sheets["Featured Decks"],
        subjects,
        names,
        stage=stage,
    )
    reviews: dict[tuple[str, str], dict[str, Any]] = {}
    for scope in sorted(scopes):
        format_id, week = scope
        format_catalog = {
            "schema_version": catalog_document["schema_version"],
            "names": [
                dict(item) for item in catalog_document["names"]
                if item["format"] == format_id
            ],
        }
        subject = subjects[scope]
        features = feature_rows[scope]
        feature_tokens = {item["destination_id"] for item in features}
        stored_top8 = [
            {
                **item,
                "main_deck": item["main_deck"] if item["token"] in feature_tokens else [],
                "side_deck": item["side_deck"] if item["token"] in feature_tokens else [],
            }
            for item in subject["all_top8"]
        ]
        document = {
            "schema_version": (
                REVIEW_SCHEMA_VERSION
                if selected_formats <= {"standard", "modern"}
                else FORMAT_SCOPED_REVIEW_SCHEMA_VERSION
            ),
            "format": format_id,
            "source": SOURCE_ID,
            "week": subject["week"],
            "bindings": {
                "workbook_sha256": workbook_digest,
                "source_event_ids": subject["source_event_ids"],
                "classifier_digest": subject["classifier_digest"],
                "selection_policy_digest": subject["selection_policy_digest"],
                "machine_fact_digest": subject["machine_fact_digest"],
                "link_catalog_digest": subject["link_catalog_digest"],
                "bilingual_catalog_digest": document_digest(
                    format_catalog
                    if selected_formats - {"standard", "modern"}
                    else catalog_document
                ),
            },
            "candidate_evidence": subject["candidate_evidence"],
            "all_top8": stored_top8,
            "review": {
                "top_copy": {"reviewed": True, "items": copy_rows[scope]},
                "features": {
                    "reviewed": True,
                    "explicit_empty": not features,
                    "items": features,
                },
            },
            "known_archetype_ids": subject["known_archetype_ids"],
        }
        validate_review_document(document, root / DEFAULT_REVIEW_SCHEMA)
        reviews[scope] = document
    return {
        "workbook_sha256": workbook_digest,
        "catalog_document": catalog_document,
        "reviews": reviews,
        "name_count": len(catalog_document["names"]),
        "review_count": len(reviews),
        "feature_count": sum(
            len(document["review"]["features"]["items"])
            for document in reviews.values()
        ),
        "copy_count": sum(
            len(document["review"]["top_copy"]["items"])
            for document in reviews.values()
        ),
    }


def validate_review_workbook(
    repository_root: str | Path,
    workbook_path: str | Path,
    *,
    stage: str,
    expected_sha256: str | None = None,
    formats: set[str] | None = None,
) -> dict[str, Any]:
    """Validate one review stage without writing repository review state."""

    result = _validated_workbook_subject(
        repository_root,
        workbook_path,
        expected_sha256=expected_sha256,
        formats=formats,
        stage=stage,
    )
    return {
        key: result[key]
        for key in (
            "workbook_sha256",
            "name_count",
            "review_count",
            "feature_count",
            "copy_count",
        )
    } | {"stage": stage}


def import_review_workbook(
    repository_root: str | Path,
    workbook_path: str | Path,
    *,
    output_root: str | Path | None = None,
    expected_sha256: str | None = None,
    formats: set[str] | None = None,
) -> dict[str, Any]:
    """Validate and import one accepted bilingual workbook into private review files."""

    root = Path(repository_root).resolve()
    output = Path(output_root).resolve() if output_root is not None else root
    validated = _validated_workbook_subject(
        root,
        workbook_path,
        expected_sha256=expected_sha256,
        formats=formats,
        stage="bilingual",
    )
    catalog_document = validated["catalog_document"]
    reviews = validated["reviews"]
    catalog_path = output / DEFAULT_NAME_CATALOG
    _write_yaml(catalog_path, catalog_document)
    review_paths: list[Path] = []
    for (format_id, week), document in sorted(reviews.items()):
        review_path = output / f"stats/{format_id}/mtgo/landing/review/{week}.yaml"
        _write_yaml(review_path, document)
        review_paths.append(review_path)

    known_paths: list[Path] = []
    for format_id in sorted({scope[0] for scope in reviews}):
        known = _known_ids(root, format_id)
        accepted_weeks = sorted(
            week for current_format, week in reviews if current_format == format_id
        )
        for week in accepted_weeks:
            known.update(reviews[(format_id, week)]["known_archetype_ids"])
        known_path = output / f"stats/{format_id}/mtgo/landing/review/known_archetypes.json"
        known_path.parent.mkdir(parents=True, exist_ok=True)
        known_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "format": format_id,
                    "accepted_through_week": accepted_weeks[-1],
                    "known_ids": sorted(known),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
            newline="\n",
        )
        known_paths.append(known_path)
    return {
        "workbook_sha256": validated["workbook_sha256"],
        "catalog_path": catalog_path,
        "review_paths": review_paths,
        "known_paths": known_paths,
        "name_count": validated["name_count"],
        "review_count": validated["review_count"],
        "feature_count": validated["feature_count"],
        "copy_count": validated["copy_count"],
    }


__all__ = [
    "MTGOLandingEditorialError",
    "build_public_name_contract",
    "build_top8_catalog",
    "build_top8_subject",
    "copy_deck_tokens",
    "document_digest",
    "file_sha256",
    "generate_public_name_contract",
    "import_review_workbook",
    "load_name_catalog",
    "load_name_catalog_document",
    "load_review_document",
    "materialize_review",
    "read_review_workbook",
    "validate_name_catalog",
    "validate_review_binding",
    "validate_review_document",
    "validate_review_workbook",
]
