"""Supplement only match identities omitted from retained Melee standings.

Copies the verified immutable snapshot and adds minimized DQ identity/deck
responses. Existing tournament, standings, matches and decks are never fetched
again or overwritten. No statistics or public candidate is generated.
"""
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
from pathlib import Path
import shutil
import sys
import time

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mtgmeta.melee.client import RawResponseRecord, _require_complete_url, _complete_record_payload
from mtgmeta.melee.config import load_melee_event_registry
from mtgmeta.melee.parser import SourceArtifact, parse_raw_snapshot
from mtgmeta.melee.privacy import minimize_source_response
from mtgmeta.melee.retention import (_load_manifest, _validate_snapshot_contents,
                                    _validated_snapshot_path, DEFAULT_RAW_SCHEMA)


def supplement(root, event_id, snapshot, *, get=requests.get):
    root = Path(root).resolve()
    event = load_melee_event_registry(root / "configs/melee_events.yaml").require_fetchable(event_id)
    source = _validated_snapshot_path(snapshot, root / "data_raw", event)
    manifest, original_manifest = _load_manifest(source, DEFAULT_RAW_SCHEMA)
    _validate_snapshot_contents(source, manifest)
    parsed = parse_raw_snapshot(source)
    if parsed.event_id != event_id or parsed.event_url != event.url or manifest["schema_version"] != "4.0.0":
        raise ValueError("Expected this event's retained v4 source")
    known = {s.source_participant_id for p in parsed.pages for s in p.standings}
    matched = {pid for p in parsed.pages for m in p.matches for pid in m.competitor_source_ids}
    missing = sorted(matched - known)
    archived_decks = {p.artifact.source_decklist_id for p in parsed.pages if p.artifact.resource_type == "decklist"}
    pending = [r for p in parsed.pages if p.artifact.resource_type == "participant"
               for r in p.decklist_references if r.source_decklist_id not in archived_decks]
    if not missing and not pending:
        return {"snapshot": str(source), "requests": 0, "reused_responses": len(parsed.pages)}
    if len(missing) > 100:
        raise ValueError("Excessive missing participant coverage; inspect source selection first")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for number in range(1, 10000):
        destination = source.parent / f"{stamp}-{number:02d}"
        if not destination.exists():
            break
    else:
        raise ValueError("No unused snapshot destination")
    shutil.copytree(source, destination)
    requests_made = 0

    def collect(kind, identifier, participant, url, filename):
        nonlocal requests_made
        _require_complete_url(url, event_id, kind, identifier)
        if requests_made:
            time.sleep(0.35)
        response = get(url, headers={"Accept": "application/json"}, timeout=30, allow_redirects=False)
        requests_made += 1
        if not 200 <= response.status_code < 300:
            raise ValueError(f"Supplement HTTP {response.status_code}: {url}; retained at {destination}")
        body = response.content
        if len(body) > 32 * 1024 * 1024:
            raise ValueError("Supplement exceeds response size boundary")
        source_hash = sha256(body).hexdigest()
        artifact = SourceArtifact(request_id=kind, resource_type=kind, page=1, url=url,
            path=filename, expected_content_type="json", sha256=source_hash, bytes=len(body),
            method="GET", source_participant_id=participant,
            source_decklist_id=identifier if kind == "decklist" else None)
        minimized = minimize_source_response(body, artifact, event_id=event_id)
        with (destination / filename).open("xb") as handle:
            handle.write(minimized.body)
        record = RawResponseRecord(request_id=kind, resource_type=kind, page=1, url=url,
            path=filename, expected_content_type="json", response_content_type=response.headers.get("Content-Type"),
            etag=response.headers.get("ETag"), last_modified=response.headers.get("Last-Modified"),
            status_code=response.status_code, attempts=1, sha256=sha256(minimized.body).hexdigest(),
            bytes=len(minimized.body), method="GET", source_participant_id=participant,
            source_decklist_id=identifier if kind == "decklist" else None,
            persisted_content_type="json", source_sha256=source_hash, source_bytes=len(body))
        manifest["responses"].append(_complete_record_payload(record))
        # Preserve a successful minimized response before attempting the next.
        (destination / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        return minimized.page

    existing_decks = set(archived_decks)
    for participant in missing:
        page = collect("participant", participant, participant,
            f"https://melee.gg/Player/GetPlayerDetails?id={participant}", f"participant-{participant}.json")
        pending.extend(page.decklist_references)
    for reference in pending:
        if reference.source_decklist_id not in existing_decks:
            collect("decklist", reference.source_decklist_id, reference.source_participant_id, reference.url,
                f"decklist-{reference.source_decklist_id.casefold()}.json")
            existing_decks.add(reference.source_decklist_id)
    _load_manifest(destination, DEFAULT_RAW_SCHEMA)
    _validate_snapshot_contents(destination, manifest)
    parse_raw_snapshot(destination)
    for record in json.loads(original_manifest)["responses"]:
        assert (source / record["path"]).read_bytes() == (destination / record["path"]).read_bytes()
    assert (source / "manifest.json").read_bytes() == original_manifest
    return {"snapshot": str(destination), "source_snapshot": str(source), "missing_participants": missing,
        "source_manifest_sha256": sha256(original_manifest).hexdigest(),
        "manifest_sha256": sha256((destination / "manifest.json").read_bytes()).hexdigest(),
        "requests": requests_made, "reused_responses": len(parsed.pages)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(supplement(args.root, args.event_id, args.snapshot), ensure_ascii=False))
