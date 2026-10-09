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


def build_catalog(root, format_id, week, event_ids, *, classification_cache=None):
    """Read only explicitly selected, already retained and classified events."""
    root = Path(root)
    year, number = week.split("-W")
    monday = date.fromisocalendar(int(year), int(number), 1)
    end = monday + timedelta(days=6)
    result = {"max_swiss_losses": 2, "events": [], "decks": []}
    classification_cache = classification_cache if classification_cache is not None else {}
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
            current_digest = hashlib.sha256((root / relative).read_bytes()).hexdigest()
            if key != "taxonomy" and current_digest != public["input"][key + "_sha256"]:
                raise ValueError(f"Tabletop classified deck input changed: {relative}")
        current_classes = None
        if current_digest != public["input"]["taxonomy_sha256"]:
            from mtgmeta.config import load_rule_set
            from mtgmeta.classifier import classify_deck
            from mtgmeta.melee.classification import _adapt_decklist
            cache_key = (format_id, str(event_id), current_digest)
            if cache_key not in classification_cache:
                rules = load_rule_set(root / relative)
                if rules.format != format_id:
                    raise ValueError("Tabletop taxonomy belongs to another format")
                classes = {}
                for item in public["decks"]:
                    if item["decklist"]["status"] != "submitted":
                        continue
                    deck, errors = _adapt_decklist(item["decklist"])
                    if errors:
                        raise ValueError("Invalid retained tabletop decklist")
                    classes[item["participant_id"]] = classify_deck(rules, deck)
                classification_cache[cache_key] = classes
            current_classes = classification_cache[cache_key]
        record = {"event_id": str(event_id), "name": meta["name"], "date": meta["date"],
                  "event_sha256": hashlib.sha256((root / event_path).read_bytes()).hexdigest(),
                  "decks_sha256": hashlib.sha256((root / deck_path).read_bytes()).hexdigest(),
                  "eligible_count": 0, "unresolved_record_count": 0}
        for item in public["decks"]:
            score = swiss_record(item.get("scopes", {}).get("all_constructed", {}).get("result_counts"))
            if score is None:
                record["unresolved_record_count"] += 1
                continue
            cls = item["classification"]
            if current_classes is not None and item["participant_id"] in current_classes:
                classification = current_classes[item["participant_id"]]
                if classification.status not in {"classified", "unknown"}:
                    raise ValueError("Retained tabletop classification is unresolved")
                cls = {"status": classification.status, "archetype_id": classification.archetype_id,
                       "subtype_id": classification.subtype_id, "archetype_name": classification.archetype_name,
                       "subtype_name": classification.subtype_name}
            if score["losses"] > 2 or cls["status"] != "classified":
                continue
            cards = item["decklist"]["cards"]
            if item["decklist"]["status"] != "submitted" or not cards:
                continue
            zones = {zone: [{"name": c["name"], "qty": c["quantity"]} for c in cards if c["section"] == section]
                     for zone, section in (("main_deck", "main"), ("side_deck", "sideboard"))}
            deck_id = digest(["melee", str(event_id), item["participant_id"]])[:20]
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


def validate_retained(root, source, *, classification_cache=None):
    retained = source.get("tabletop")
    if retained is None:
        return {}
    actual = build_catalog(root, source["format"], source["week"]["id"],
                           [item["event_id"] for item in retained["events"]],
                           classification_cache=classification_cache)
    if source["bindings"].get("tabletop_digest") != digest(retained):
        raise ValueError("Retained tabletop Feature material changed")
    event_fields = ("event_id", "name", "date", "event_sha256")
    if ([{key: item[key] for key in event_fields} for item in actual["events"]]
            != [{key: item[key] for key in event_fields} for item in retained["events"]]):
        raise ValueError("Retained tabletop Feature material changed")
    selected = {item["destination_id"] for item in source.get("review", {}).get("features", {}).get("items", [])}
    decks = {item["token"]: item for item in actual["decks"]}
    for original in retained["decks"]:
        if selected and original["token"] not in selected:
            continue
        deck = decks.get(original["token"])
        fields = {key: value for key, value in original.items()
                  if key not in {"parent_id", "subtype_id", "display_name"}}
        if deck is None or fields != {key: deck[key] for key in fields}:
            raise ValueError("Retained tabletop Feature material changed")
    return {"tabletop_digest": digest(retained)}


def provenance(deck):
    return {key: deepcopy(deck[key]) for key in ("source", "event_name", "swiss_record") if key in deck}
