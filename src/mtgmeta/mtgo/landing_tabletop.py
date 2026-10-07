"""Explicit tabletop Feature sources; independent of MTGO populations."""
from copy import deepcopy
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def deck_catalog(source):
    return [*source["all_top8"], *source.get("tabletop", {}).get("decks", [])]


def swiss_record(counts):
    # These are the existing all_constructed Swiss counters, including both days.
    # Administrative/unknown results cannot establish a complete loss count.
    if not counts or any(counts.get(key, 0) for key in
                         ("administrative_result", "unknown_result", "no_show")):
        return None
    wins = sum(counts.get(key, 0) for key in ("played_win", "bye", "awarded_win_top8_lock"))
    losses = counts.get("played_loss", 0)
    draws = counts.get("played_draw", 0) + counts.get("intentional_draw", 0)
    return {"wins": wins, "losses": losses, "draws": draws} if wins + losses + draws else None


def build_catalog(root, format_id, week, event_ids):
    """Read only explicitly selected, already retained and classified events."""
    root = Path(root)
    year, number = week.split("-W")
    monday = date.fromisocalendar(int(year), int(number), 1)
    end = monday + timedelta(days=6)
    result = {"max_swiss_losses": 2, "events": [], "decks": []}
    for event_id in sorted(set(event_ids)):
        if not str(event_id).isdigit():
            raise ValueError("Invalid tabletop event identity")
        event_path = Path(f"data/{format_id}/melee/events/{event_id}.json")
        deck_path = Path(f"stats/{format_id}/melee/events/{event_id}/decks.json")
        event = json.loads((root / event_path).read_text(encoding="utf-8"))
        public = json.loads((root / deck_path).read_text(encoding="utf-8"))
        if (public.get("event_id") != str(event_id) or public.get("format") != format_id
                or public["input"]["event_path"] != event_path.as_posix()):
            raise ValueError("Tabletop deck catalog belongs to another event/format")
        meta = event["metadata"]
        event_end = date.fromisoformat(meta["date"]["end"])
        if meta["constructed_format"] != format_id or not monday <= event_end <= end:
            raise ValueError("Tabletop Feature event is outside the requested format/week")
        for key in ("event", "classification", "opportunity", "taxonomy"):
            relative = Path(public["input"][key + "_path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Unsafe tabletop input path")
            if hashlib.sha256((root / relative).read_bytes()).hexdigest() != public["input"][key + "_sha256"]:
                raise ValueError(f"Tabletop classified deck input changed: {relative}")
        record = {"event_id": str(event_id), "name": meta["name"], "date": meta["date"],
                  "event_sha256": hashlib.sha256((root / event_path).read_bytes()).hexdigest(),
                  "decks_sha256": hashlib.sha256((root / deck_path).read_bytes()).hexdigest(),
                  "eligible_count": 0, "unresolved_record_count": 0}
        for item in public["decks"]:
            score = swiss_record(item.get("scopes", {}).get("all_constructed", {}).get("result_counts"))
            if score is None:
                record["unresolved_record_count"] += 1
                continue
            if score["losses"] > 2 or item["classification"]["status"] != "classified":
                continue
            cards = item["decklist"]["cards"]
            if item["decklist"]["status"] != "submitted" or not cards:
                continue
            zones = {zone: [{"name": c["name"], "qty": c["quantity"]} for c in cards if c["section"] == section]
                     for zone, section in (("main_deck", "main"), ("side_deck", "sideboard"))}
            deck_id = digest(["melee", str(event_id), item["participant_id"]])[:20]
            cls = item["classification"]
            result["decks"].append({"token": "deck:" + deck_id, "source": "melee",
                "reference": f"melee:{event_id}:{item['final_rank']}",
                "event_id": str(event_id), "event_name": meta["name"], "deck_id": deck_id,
                "deck_fingerprint_sha256": digest(zones), "date": meta["date"]["start"],
                "starttime": meta["date"]["start"], "final_rank": item["final_rank"],
                "player_count": len(public["decks"]), "player": item["player_name"],
                "parent_id": cls["archetype_id"], "subtype_id": cls["subtype_id"],
                "display_name": cls["subtype_name"] or cls["archetype_name"],
                "swiss_record": score, **zones})
            record["eligible_count"] += 1
        result["events"].append(record)
    result["decks"].sort(key=lambda item: (item["starttime"], item["event_id"], item["final_rank"]))
    return result


def validate_retained(root, source):
    retained = source.get("tabletop")
    if retained is None:
        return {}
    actual = build_catalog(root, source["format"], source["week"]["id"],
                           [item["event_id"] for item in retained["events"]])
    if actual != retained or source["bindings"].get("tabletop_digest") != digest(actual):
        raise ValueError("Retained tabletop Feature material changed")
    return {"tabletop_digest": digest(actual)}


def provenance(deck):
    return {key: deepcopy(deck[key]) for key in ("source", "event_name", "swiss_record") if key in deck}
