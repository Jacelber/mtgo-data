"""Prepare a complete Melee preview from a fixed delivery; never collect or deploy."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import sys
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from mtgmeta.mtgo.publication import require_private_output
from mtgmeta.resource_progress import save
from tools.delivery import resources
from tools.delivery.verification import material_snapshot
from tools import build_simple_card_localization as names, build_landing_card_image_cache as images


def audit(root: Path, format_id: str, event_id: str) -> dict:
    """Report retained coverage and Unknown decks without changing inputs."""
    from mtgmeta.classifier import classifier_digest
    from mtgmeta.mtgo.normalize import load_rules_for_format
    root = root.resolve()
    event_path = root / f"data/{format_id}/melee/events/{event_id}.json"
    event = json.loads(event_path.read_bytes())
    overlay = json.loads((root / f"data/{format_id}/melee/classifications/{event_id}.json").read_bytes())
    if (event["metadata"]["event_id"] != event_id or event["metadata"]["constructed_format"] != format_id
            or overlay["event_id"] != event_id or overlay["format"] != format_id
            or overlay["input"]["event_sha256"] != hashlib.sha256(event_path.read_bytes()).hexdigest()
            or overlay["classifier"]["digest"] != classifier_digest(load_rules_for_format(root, format_id))):
        raise ValueError("Event, classification and selected rules do not bind the same input")
    def indexed(values, key):
        result = {item[key]: item for item in values}
        if len(result) != len(values):
            raise ValueError(f"Duplicate {key} in retained input")
        return result
    participants = indexed(event["participants"], "id")
    standings = indexed(event["standings"], "participant_id")
    decks = indexed(event["decklists"], "participant_id")
    records = indexed(overlay["records"], "participant_id")
    for artifact in event["provenance"]["raw_artifacts"]:
        path = (root / artifact["path"]).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != artifact["sha256"]:
            raise ValueError("Retained raw artifact hash differs")
    def row(identifier):
        return {"participant_id": identifier, "name": participants[identifier]["display_name"],
                "rank": standings.get(identifier, {}).get("rank"), "decklist": decks.get(identifier),
                "classification": records.get(identifier)}
    unknown = [row(identifier) for identifier, record in records.items() if record["classification_status"] == "unknown"]
    unavailable = [row(identifier) for identifier, deck in decks.items() if deck["status"] != "submitted"]
    return {"event_id": event_id, "format": format_id, "participants": len(participants),
            "standings": len(standings), "deck_entries": len(decks),
            "participant_coverage_equal": set(participants) == set(standings) == set(decks),
            "deck_statuses": dict(Counter(item["status"] for item in decks.values())),
            "classification": overlay["summary"], "unknown": sorted(unknown, key=lambda item: item["rank"] or 0),
            "unavailable": unavailable, "disqualified": [row(i) for i, p in participants.items() if p["status"] == "disqualified"],
            "raw_artifacts_verified": len(event["provenance"]["raw_artifacts"]),
            "quality": event["quality"], "classification_quality": overlay["quality"], "fetched": 0}


def preview(record_path: Path, *, resource_site: Path | None = None, offline: bool = False) -> dict:
    record_path = record_path.resolve()
    record = json.loads(record_path.read_text(encoding="utf-8"))
    identity = record["identity"]
    root = Path(identity["root"])
    if record.get("schema") != 1 or identity["kind"] != "reviewed_data":
        raise ValueError("Use a fixed reviewed-data delivery record")
    if identity.get("material") is None or material_snapshot(root, identity["scope"]) != identity["material"]:
        raise ValueError("Fixed candidate changed; retain it and prepare a new candidate")
    work = record_path.parent / (record_path.stem + ".work")
    require_private_output(ROOT, work / "index.html")
    work.mkdir(parents=True, exist_ok=True)
    for target, prefix, verify in (("localization", names.PUBLIC_PREFIX, names.verify_bundle),
                                    ("images", images.CACHE_PUBLIC_PREFIX, images.verify_cache_bundle)):
        destination = work / target
        if resource_site is not None and not destination.exists():
            source = resource_site / prefix
            verify(root, source)
            shutil.copytree(source, destination)
        if offline:
            # Fail before prepare_site can enter any cache query or request path.
            verify(root, destination)
    site = resources.prepare_site(record, work)
    entries = identity["scope"].get("melee", [])
    urls = []
    for entry in entries:
        fmt, event = entry["format"], entry["event_id"]
        required = ["stats/catalog.json", f"stats/{fmt}/archetype_names.json",
                    f"stats/{fmt}/melee/index.json", f"stats/{fmt}/mtgo/decks_4w.json"]
        catalog = json.loads((site / required[2]).read_text(encoding="utf-8"))
        matches = [item for item in catalog["events"] if str(item["event_id"]) == event]
        if len(matches) != 1:
            raise ValueError(f"Selected event is absent or duplicated: {event}")
        base = Path(f"stats/{fmt}/melee")
        required += [(base / matches[0][key]).as_posix() for key in ("meta", "overview", "quality", "decks", "matchup")]
        if any(not (site / relative).is_file() for relative in required):
            raise ValueError(f"Incomplete consumer dependencies: {event}")
        urls.append("/melee/index.html?" + urlencode({"format": fmt, "product": "tabletop-major-events",
                    "view": "overview", "event": event, "scope": "all_constructed", "lang": "zh"}))
    result = {"site": str(site), "urls": urls, "record": str(record_path), "operation": record["operation"],
              "offline": offline, "collection_requests": 0, "remote_writes": 0,
              "next": "Serve this site, check the actual page, then reuse this record only within publication authorization"}
    save(work / "melee-preview.json", result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("audit")
    check.add_argument("--root", type=Path, required=True)
    check.add_argument("--format", required=True)
    check.add_argument("--event-id", required=True)
    check.add_argument("--output", type=Path, required=True)
    command = sub.add_parser("preview")
    command.add_argument("--record", type=Path, required=True)
    command.add_argument("--resource-site", type=Path)
    command.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "audit":
            import re
            if not re.fullmatch(r"[a-z][a-z0-9-]*", args.format) or not re.fullmatch(r"[1-9][0-9]*", args.event_id):
                raise ValueError("Invalid event identity")
            require_private_output(args.root.resolve(), args.output.resolve())
            if args.output.exists():
                raise ValueError("Audit output exists; retain it and choose a new path")
            result = audit(args.root, args.format, args.event_id)
            save(args.output, result)
            print(json.dumps({"audit": str(args.output), "participants": result["participants"],
                              "classification": {key: result["classification"][key] for key in
                               ("classified", "unknown", "conflicts", "invalid_decks")}, "fetched": 0}, ensure_ascii=False))
        else:
            print(json.dumps(preview(args.record, resource_site=args.resource_site, offline=args.offline), ensure_ascii=False))
        return 0
    except (ValueError, OSError, RuntimeError) as error:
        print(json.dumps({"state": "blocked", "error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
