"""Refresh official final ranks without recollecting decklists or match results."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mtgmeta.melee.client import API_HEADERS, STANDINGS_COLUMNS, _datatables_body, _completed_rounds
from mtgmeta.melee.config import load_melee_event_registry
from mtgmeta.melee.parser import _real_player
from mtgmeta.melee.stats import apply_final_standings, statistics_document_bytes
from mtgmeta.melee.publish import _descriptor


def refresh(root, event_id, *, reviewed_semifinals=False):
    if reviewed_semifinals and event_id != "405588":
        raise ValueError("The reviewed Semifinals supplement is approved only for 405588")
    definition = load_melee_event_registry(root / "configs/melee_events.yaml").require_fetchable(event_id)
    event_path = root / "data" / definition.format / "melee/events" / f"{event_id}.json"
    event_bytes = event_path.read_bytes()
    event = json.loads(event_bytes)
    tournament_path = next(item["path"] for item in event["provenance"]["raw_artifacts"]
                           if item.get("source_url") == definition.url)
    if tournament_path.endswith(".html"):
        rounds = [{"source_round_id": identifier, "label": label}
                  for identifier, label in _completed_rounds((root / tournament_path).read_bytes())]
    else:
        tournament = json.loads((root / tournament_path).read_text(encoding="utf-8"))
        rounds = tournament.get("rounds", tournament.get("data", {}).get("rounds", []))
    source_label = "Semifinals" if reviewed_semifinals else "Finals"
    finals = [item for item in rounds if item["label"].casefold() == source_label.casefold()]
    if len(finals) != 1:
        raise ValueError(f"{event_id}: no unique completed official Finals round")
    round_id = finals[0]["source_round_id"]
    identities = {item["source_id"]: item["id"] for item in event["participants"]}
    ranks = {}
    total = None
    start = 0
    while total is None or start < total:
        request = urllib.request.Request("https://melee.gg/Standing/GetRoundStandings",
            data=_datatables_body(STANDINGS_COLUMNS, start, round_id=round_id),
            headers=API_HEADERS, method="POST")
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
        count = payload["recordsTotal"]
        if not isinstance(count, int) or not 0 < count <= 5000 or (total is not None and total != count):
            raise ValueError("Official standings count changed or exceeded the supported scope")
        total = count
        rows = payload["data"]
        if not rows:
            raise ValueError("Official standings page is incomplete")
        for row in rows:
            source_id, _, _ = _real_player(row["Team"], "standing.Team")
            rank = row["Rank"]
            if not isinstance(rank, int) or rank < 1 or source_id in ranks:
                raise ValueError("Invalid or repeated official ranking")
            ranks[source_id] = rank
        start += len(rows)
        if start < total:
            time.sleep(0.25)
    if not identities.keys() <= ranks.keys():
        raise ValueError("Official final standings omit retained participants")
    selected = {identities[key]: ranks[key] for key in identities}
    if len(set(selected.values())) != len(selected):
        raise ValueError("Official final ranks are not unique")
    result = {"event_id": event_id, "source_url": definition.url,
        "source_round_id": round_id, "source_round_label": source_label,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "event_sha256": hashlib.sha256(event_bytes).hexdigest(), "ranks": selected}
    if reviewed_semifinals:
        supplement_from_semifinals(result, event)
    destination = event_path.parent.parent / "final_standings" / f"{event_id}.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"event_id": event_id, "participants": len(selected), "path": str(destination)}


def supplement_from_semifinals(result, event):
    """Apply the reviewed event exception using identities and retained playoff results."""
    ranks = result["ranks"]
    if set(ranks.values()) != set(range(1, len(event["participants"]) + 1)):
        raise ValueError("Semifinals ranks must cover all retained participants exactly once")
    rounds = {r["source_label"]: r["id"] for r in event["rounds"] if r["stage"] == "playoff"}
    matches = {label: [m for m in event["matches"] if m["round_id"] == rounds.get(label)]
               for label in ("Quarterfinals", "Semifinals", "Finals")}
    for label, count in (("Quarterfinals", 4), ("Semifinals", 2), ("Finals", 1)):
        if len(matches[label]) != count or any(
                sorted(c["result_type"] for c in m["competitors"]) != ["played_loss", "played_win"]
                for m in matches[label]):
            raise ValueError(f"Incomplete decisive {label} results")
    def players(label, outcome=None):
        return {c["participant_id"] for m in matches[label] for c in m["competitors"]
                if outcome is None or c["result_type"] == outcome}
    if (players("Quarterfinals") != {p for p, rank in ranks.items() if rank <= 8}
            or players("Quarterfinals", "played_win") != players("Semifinals")
            or players("Semifinals", "played_win") != players("Finals")
            or players("Semifinals", "played_loss") != {p for p, rank in ranks.items() if rank in (3, 4)}
            or players("Finals") != {p for p, rank in ranks.items() if rank in (1, 2)}):
        raise ValueError("Semifinals standings do not agree with the retained playoff bracket")
    result["base_ranks"] = dict(ranks)
    for competitor in matches["Finals"][0]["competitors"]:
        ranks[competitor["participant_id"]] = 1 if competitor["result_type"] == "played_win" else 2
    result["method"] = "reviewed_semifinals_with_final_result"
    result["decisive_match_id"] = matches["Finals"][0]["id"]
    result["note"] = {
        "zh": "最终排名根据官方半决赛排名及决赛结果补齐；冠亚军按决赛结果确定，第 3 名起沿用半决赛排名。",
        "en": "Final standings supplemented from official semifinal standings and the final result. First and second follow the final result; places 3 onward retain the semifinal standings.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--reviewed-semifinals", action="store_true", help="Apply the Owner-approved 405588 ranking exception")
    parser.add_argument("--materialize", action="store_true", help="Use the saved official source; perform no network requests")
    args = parser.parse_args()
    if args.materialize:
        definition = load_melee_event_registry(ROOT / "configs/melee_events.yaml").require_fetchable(args.event_id)
        directory = ROOT / "stats" / definition.format / "melee/events" / args.event_id
        decks = json.loads((directory / "decks.json").read_text(encoding="utf-8"))
        event_path = ROOT / "data" / definition.format / "melee/events" / f"{args.event_id}.json"
        if not (event_path.parent.parent / "final_standings" / event_path.name).is_file():
            raise ValueError("Fetch official final standings before materializing ranks")
        apply_final_standings(decks, event_path, ROOT)
        payload = statistics_document_bytes(decks)
        meta = json.loads((directory / "meta.json").read_text(encoding="utf-8"))
        meta["outputs"]["decks"] = _descriptor("decks", decks, payload)
        (directory / "decks.json").write_bytes(payload)
        (directory / "meta.json").write_bytes(statistics_document_bytes(meta))
        print(json.dumps({"event_id": args.event_id, "state": "materialized"}))
    else:
        print(json.dumps(refresh(ROOT, args.event_id, reviewed_semifinals=args.reviewed_semifinals)))
