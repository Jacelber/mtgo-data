"""Read-only retained-source checks, independent of static-site publication.

Bindings follow each event's own provenance and versioned snapshot. They are
not a historical golden: a reviewed source revision can establish a new chain,
and classifier updates do not change source identity or freeze derived bytes.
"""
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from .assembler import assemble_parsed_snapshot
from .config import MeleeEventDefinition
from .parser import parse_raw_snapshot
from .quality import DEFAULT_SCHEMA, _validate
from .retention import DEFAULT_RAW_SCHEMA, _load_manifest, _validate_snapshot_contents


class MeleeSourceIntegrityError(ValueError):
    """Retained source is missing, damaged, or bound to different identities."""


def _file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise MeleeSourceIntegrityError("invalid retained source path")
    child = Path(relative)
    if child.is_absolute() or ".." in child.parts or child.as_posix() != relative:
        raise MeleeSourceIntegrityError(f"unsafe retained source path: {relative}")
    path = root / child
    if any(part.is_symlink() for part in (path, *path.parents) if part != root):
        raise MeleeSourceIntegrityError(f"symlink in retained source path: {relative}")
    if not path.is_file():
        raise MeleeSourceIntegrityError(f"missing retained source file: {relative}")
    return path


def retained_source_paths(root: Path, format_id: str, event_id: str) -> set[Path]:
    """Select provenance inputs for integrity and candidate-change detection.

    Include the actual snapshot set as well as declarations: adding an
    undeclared response must invalidate a previously completed check too.
    """
    event_path = _file(root, f"data/{format_id}/melee/events/{event_id}.json")
    document = json.loads(event_path.read_bytes())
    if document.get("metadata", {}).get("event_id") != event_id or document.get("metadata", {}).get("constructed_format") != format_id:
        raise MeleeSourceIntegrityError("retained event identity does not match its path")
    artifacts = document.get("provenance", {}).get("raw_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise MeleeSourceIntegrityError("retained event has no source provenance")
    paths = {event_path}
    snapshots = set()
    for artifact in artifacts:
        path = _file(root, artifact.get("path"))
        relative = path.relative_to(root)
        if relative.parts[:3] != ("data_raw", "melee", event_id) or len(relative.parts) != 5:
            raise MeleeSourceIntegrityError("raw artifact does not belong to this event snapshot")
        paths.add(path)
        snapshots.add(path.parent)
    if len(snapshots) != 1:
        raise MeleeSourceIntegrityError("retained event must bind one complete snapshot")
    snapshot = snapshots.pop()
    paths.add(_file(root, (snapshot / "manifest.json").relative_to(root).as_posix()))
    for path in snapshot.rglob("*"):
        if path.is_symlink():
            raise MeleeSourceIntegrityError("symlink in retained snapshot")
        if path.is_file():
            paths.add(path)
    return paths


def _identities(document):
    """Compare source membership and joins, without replaying old normalization."""
    return {
        "participants": sorted((p["id"], p["source_id"]) for p in document["participants"]),
        "rounds": sorted((r["id"], r["number"], r["source_label"]) for r in document["rounds"]),
        "matches": sorted((m["id"], m["source_record_id"], m["round_id"],
                           tuple(sorted(c["participant_id"] for c in m["competitors"])))
                          for m in document["matches"]),
        "standings": sorted(s["participant_id"] for s in document["standings"]),
        "decklists": sorted(d["participant_id"] for d in document["decklists"]),
    }


def validate_retained_source(root: Path, event: MeleeEventDefinition) -> set[Path]:
    """Validate existing v2/v3/v4 sources; never collect or rewrite anything."""
    try:
        paths = retained_source_paths(root, event.format, event.id)
        event_path = root / f"data/{event.format}/melee/events/{event.id}.json"
        document = json.loads(event_path.read_bytes())
        _validate(document, DEFAULT_SCHEMA)
        snapshot = next(p.parent for p in paths if p.name == "manifest.json")
        manifest, _ = _load_manifest(snapshot, DEFAULT_RAW_SCHEMA)
        if manifest["event_id"] != event.id or manifest["event_url"] != event.url:
            raise MeleeSourceIntegrityError("snapshot identity differs from retained event")
        _validate_snapshot_contents(snapshot, manifest)
        parsed = parse_raw_snapshot(snapshot)  # Validates every persisted size/hash and source context.
        assembled = assemble_parsed_snapshot(parsed, event,
            normalized_at=document["provenance"]["normalized_at"],
            raw_artifact_prefix=snapshot.relative_to(root).as_posix())
        for field in ("metadata", "event_structure"):
            if document[field] != assembled[field]:
                raise MeleeSourceIntegrityError(f"retained {field} differs from event definition")
        actual = document["provenance"]["raw_artifacts"]
        expected = assembled["provenance"]["raw_artifacts"]
        if sorted(actual, key=lambda x: x["path"]) != sorted(expected, key=lambda x: x["path"]):
            raise MeleeSourceIntegrityError("normalized provenance differs from snapshot response set")
        if document["provenance"]["fetched_at"] != manifest["fetched_at"]:
            raise MeleeSourceIntegrityError("normalized provenance snapshot time differs")
        actual_ids, expected_ids = _identities(document), _identities(assembled)
        for name in actual_ids:
            if actual_ids[name] != expected_ids[name]:
                raise MeleeSourceIntegrityError(f"retained {name} identities differ from source")
        return paths
    except (ValueError, OSError, KeyError, TypeError, StopIteration) as exc:
        raise MeleeSourceIntegrityError(f"Melee source {event.format}/{event.id}: {exc}") from exc


def validate_derived_inputs(root, event, classification, ledger, taxonomy):
    """Reuse production input contracts without running any generator."""
    from .stats import _validate_inputs
    event_id, format_id = event["metadata"]["event_id"], event["metadata"]["constructed_format"]
    expected = {
        "event": f"data/{format_id}/melee/events/{event_id}.json",
        "classification": f"data/{format_id}/melee/classifications/{event_id}.json",
        "opportunity": f"data/{format_id}/melee/opportunities/{event_id}.json",
        "taxonomy": f"my_archetypes/{format_id}.yaml",
    }
    hashes = {name: sha256((root / path).read_bytes()).hexdigest() for name, path in expected.items()}
    _validate_inputs(event, classification, ledger, taxonomy,
        event_sha256=hashes["event"], classification_sha256=hashes["classification"],
        ledger_sha256=hashes["opportunity"], taxonomy_sha256=hashes["taxonomy"])
    for document, names in ((classification, ("event",)), (ledger, ("event", "classification"))):
        if document.get("source") != "melee":
            raise ValueError("derived source identity differs")
        for name in names:
            if document["input"].get(name + "_path") != expected[name]:
                raise ValueError(f"derived {name} path differs")
    rounds = {r["id"] for r in event["rounds"]}
    matches = {m["id"]: m for m in event["matches"]}
    seen = set()
    for row in ledger["opportunities"]:
        key = (row["participant_id"], row["round_id"])
        if key in seen or row["round_id"] not in rounds:
            raise ValueError("duplicate or unknown opportunity participant-round")
        seen.add(key)
        if row["match_id"] is not None:
            match = matches.get(row["match_id"])
            participants = {c["participant_id"] for c in match["competitors"]} if match else set()
            if not match or match["round_id"] != row["round_id"] or row["participant_id"] not in participants:
                raise ValueError("opportunity match identity differs")
            if participants - {row["participant_id"]} != ({row["opponent_participant_id"]} if row["opponent_participant_id"] else set()):
                raise ValueError("opportunity opponent identity differs")
