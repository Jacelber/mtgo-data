"""Read-only checks for the exact dependencies of a retained Landing.

This module never regenerates data or changes acceptance. Legacy rolling paths
remain readable only when they actually belong to the retained page.
"""
from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import re


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected an object")
    return value


def inspect_bundle(root: Path, format_id: str, *, landing_directory: Path | None = None) -> dict:
    """Return an exact product subject, or fail with the broken dependency."""
    if not re.fullmatch(r"[a-z][a-z0-9-]*", format_id):
        raise ValueError("Invalid format identity")
    base = root / "stats" / format_id / "mtgo"
    landing = landing_directory or base / "landing"
    current_path = landing / "current.json"
    page = read_json(current_path)
    week = page["week"]
    monday = date.fromisoformat(week["start"])
    if monday.isoweekday() != 1 or monday.strftime("%G-W%V") != week["id"]:
        raise ValueError("Landing week identity differs from its period")
    if (monday + timedelta(days=6)).isoformat() != week["end"]:
        raise ValueError("Landing week must end on its own Sunday")
    if page.get("format") != format_id:
        raise ValueError("Landing belongs to another format")
    expected = {key: f"weeks/{week['id']}/{key}.json" for key in
                ("range", "completeness", "environment_decks", "feature_decks")}
    pinned = page.get("data_files")
    if pinned is not None and pinned != expected:
        raise ValueError("Landing data_files must identify its exact fixed-week dependencies")
    paths = ({key: landing / value for key, value in expected.items()}
             if pinned is not None else {
                 "range": base / "range_1w.json", "completeness": base / "completeness/1w.json",
                 "environment_decks": base / "decks_1w.json", "feature_decks": base / "decks_4w.json"})
    documents = {"landing": page}
    for key, path in paths.items():
        value = read_json(path)
        period = value.get("period", {})
        start = monday - timedelta(weeks=3) if key == "feature_decks" else monday
        if (value.get("format") != format_id or period.get("start") != start.isoformat()
                or period.get("end") != week["end"]):
            raise ValueError(f"{path}: retained Landing format/period mismatch")
        if key != "completeness" and value.get("classifier_digest") != page["classifier"]["digest"]:
            raise ValueError(f"{path}: retained Landing classifier mismatch")
        documents[key] = value
    archive_path = landing / "features" / f"{week['id']}.json"
    archive = read_json(archive_path)
    index = read_json(landing / "features/index.json")
    if (archive.get("format") != format_id or archive.get("week") != week
            or archive.get("features", {}).get("items") != page.get("features", {}).get("items")):
        raise ValueError(f"{archive_path}: current page and Feature archive differ")
    entries = [entry for entry in index.get("weeks", []) if entry.get("week") == week["id"]]
    if (index.get("format") != format_id or len(entries) != 1
            or entries[0].get("file") != f"{week['id']}.json"
            or entries[0].get("feature_count") != len(archive["features"]["items"])):
        raise ValueError("Landing current Feature archive is missing from its index")
    documents["feature_archive"] = archive
    # Historical index growth does not change the current page's acceptance.
    documents["feature_index_entry"] = entries[0]
    return {"format": format_id, "week": week["id"], "pinned": pinned is not None,
            "documents": documents, "digest": digest(documents)}
