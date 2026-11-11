"""Small invented source tournament; no production taxonomy or event snapshot.

Four players, two advancing to day two. All expected statistics live in tests,
never in these builders. Raw match rows deliberately have no eligibility flags.
"""
from datetime import date
from hashlib import sha256
import json

from mtgmeta.config import parse_rule_text
from mtgmeta.melee.config import MeleeAdvancement, MeleeEventDefinition, MeleePhaseDefinition
from mtgmeta.melee.normalize import normalize_raw_snapshot
from mtgmeta.melee.quality import finalize_event_quality
from mtgmeta.melee.classification import build_classification_overlay
from mtgmeta.melee.opportunities import build_opportunity_ledger
from mtgmeta.melee.stats import build_event_statistics
from mtgmeta.melee.matchup import build_event_matchup

RULES = """schema_version: 1.0.0
format: modern
archetypes:
  - id: alpha
    name: Alpha
    priority: 10
    subtypes:
      - id: blue
        name: Blue
      - id: red
        name: Red
    rules:
      - id: blue
        priority: 20
        subtype_id: blue
        conditions:
          all: [{card: Island, zone: main, min_count: 1}]
      - id: red
        priority: 10
        subtype_id: red
        conditions:
          all: [{card: Mountain, zone: main, min_count: 1}]
"""
STAMP = "2026-01-01T00:00:00Z"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return path


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def source_fixture(root, *, event_id="900001", day1_rounds=2, playoff_format="limited", dq=False):
    day1 = tuple(range(2, day1_rounds + 2))
    draft2 = day1_rounds + 2
    day2 = (draft2 + 1, draft2 + 2)
    phases = (
        MeleePhaseDefinition("draft1", "day1", "draft", "limited", True, (1,), ()),
        MeleePhaseDefinition("constructed1", "day1", "constructed", "modern", True, day1, ()),
        MeleePhaseDefinition("draft2", "day2", "draft", "limited", True, (draft2,), ()),
        MeleePhaseDefinition("constructed2", "day2", "constructed", "modern", True, day2, ()),
        MeleePhaseDefinition("final", "playoff", "playoff", playoff_format, False, (), ("Finals",)),
    )
    event = MeleeEventDefinition(event_id, f"https://melee.gg/Tournament/View/{event_id}",
        "Invented Four Player Open", date(2026, 1, 1), date(2026, 1, 2), "modern",
        "pro_tour", "mixed", True, "verified", True, (), True, phases,
        MeleeAdvancement(draft2 - 1, 4, True, "awarded_win_top8_lock"), (),
        "modern", (), (), "Independent mechanism fixture")
    snapshot = root / "data_raw/melee" / event_id / "20260101T000000Z-01"
    snapshot.mkdir(parents=True)
    responses = []

    def resource(name, kind, value, *, round_id=None, player=None, deck=None):
        path = write_json(snapshot / name, value)
        responses.append({"request_id": kind, "resource_type": kind, "page": 1,
            "url": event.url, "path": name, "expected_content_type": "json",
            "response_content_type": "application/json", "etag": None, "last_modified": None,
            "status_code": 200, "attempts": 1, "sha256": digest(path), "bytes": path.stat().st_size,
            "method": "POST" if kind in {"standings", "matches"} else "GET",
            "request_body_sha256": "a" * 64 if kind in {"standings", "matches"} else None, "source_round_id": round_id,
            "source_participant_id": player, "source_decklist_id": deck})

    rounds = [{"source_round_id": str(n), "label": f"Round {n}", "number": n}
              for n in range(1, day2[-1] + 1)]
    rounds.append({"source_round_id": "99", "label": "Finals", "number": None})
    resource("tournament-001.json", "tournament", {"resource_type": "tournament",
        "tournament": {"source_event_id": event_id, "name": event.name}, "rounds": rounds})

    def team(pid):
        status = "Disqualified" if dq and pid == "2" else "Dropped" if pid == "3" else "Active"
        return {"ID": int(pid), "Name": f"Player {pid}", "StatusDescription": status,
                "Players": [{"ID": int(pid), "DisplayName": f"Player {pid}"}]}

    resource("standings-001.json", "standings", {"data": [
        {"ID": int(pid), "Team": team(pid), "Rank": int(pid), "Points": 0,
         "Decklists": [{"DecklistId": "00000000-0000-0000-0000-00000000000" + pid, "PlayerId": int(pid)}] if pid != "4" else []}
        for pid in ("1", "2", "3", "4")]}, round_id="99")
    for pid, card in (("1", "Island"), ("2", "Mountain"), ("3", "Plains")):
        resource(f"deck-{pid}.json", "decklist", {"resource_type": "decklist", "decklist": {
            "source_decklist_id": "00000000-0000-0000-0000-00000000000" + pid, "source_participant_id": pid,
            "cards": [{"name": card, "quantity": 60, "section_text": "Main Deck"},
                      {"name": "Plains", "quantity": 15, "section_text": "Sideboard"}]}},
            player=pid, deck="00000000-0000-0000-0000-00000000000" + pid)

    def match(rid, players=("1", "2"), wins=(2, 0), draws=0, reason=None):
        return {"Guid": f"m-{rid}-{'-'.join(players)}", "RoundId": rid, "HasResult": True,
            "GameDraws": draws, "ResultString": f"{wins[0]}-{wins[-1]}-{draws}",
            "ByeReasonDescription": reason, "Competitors": [
                {"Team": team(pid), "GameWins": w, "GameByes": int(reason == "Bye")}
                for pid, w in zip(players, wins, strict=True)]}

    for round_ in rounds:
        rid = round_["source_round_id"]
        if rid == str(day2[0]):
            rows = [match(rid, wins=(0, 0), draws=3)]
        elif rid == str(day2[1]):
            rows = [match(rid, ("1",), (0,), reason="Qualified"), match(rid, ("2",), (0,), reason="Bye")]
        elif rid in {str(n) for n in day1}:
            rows = [match(rid, wins=(1, 1), draws=1) if rid == "3" else match(rid),
                    match(rid, ("4",), (0,), reason="Bye")]
            if rid == "2":
                rows.append(match(rid, ("3",), (0,), reason="Bye"))
                if dq:
                    rows = [rows[0], match(rid, ("3", "4"))]
        else:
            rows = [match(rid)]
        resource(f"matches-{rid}.json", "matches", {"data": rows}, round_id=rid)
    write_json(snapshot / "manifest.json", {"schema_version": "2.0.0", "source": "melee",
        "event_id": event_id, "event_url": event.url, "fetched_at": STAMP, "responses": responses})
    document = normalize_raw_snapshot(snapshot, event, normalized_at=STAMP,
        raw_artifact_prefix=snapshot.relative_to(root).as_posix())
    document = finalize_event_quality(document, event)
    event_path = write_json(root / f"data/modern/melee/events/{event_id}.json", document)
    return event, document, event_path, snapshot


def derived(root, document, event_path, *, rule_text=RULES):
    rules_path = root / "my_archetypes/modern.yaml"
    rules_path.parent.mkdir(parents=True, exist_ok=True)
    rules_path.write_text(rule_text)
    rules = parse_rule_text(rule_text)
    eid = document["metadata"]["event_id"]
    inputs = {"event_path": event_path.relative_to(root).as_posix(), "event_sha256": digest(event_path)}
    classification = build_classification_overlay(document, rules, **inputs,
        rule_path="my_archetypes/modern.yaml", rule_sha256=digest(rules_path))
    cp = write_json(root / f"data/modern/melee/classifications/{eid}.json", classification)
    inputs.update(classification_path=cp.relative_to(root).as_posix(), classification_sha256=digest(cp))
    ledger = build_opportunity_ledger(document, classification, **inputs)
    op = write_json(root / f"data/modern/melee/opportunities/{eid}.json", ledger)
    inputs.update(opportunity_path=op.relative_to(root).as_posix(), opportunity_sha256=digest(op))
    statistics = build_event_statistics(document, classification, ledger, rules, **inputs,
        taxonomy_path="my_archetypes/modern.yaml", taxonomy_sha256=digest(rules_path))
    matchup = build_event_matchup(statistics["overview"], ledger)
    return classification, ledger, statistics, matchup


def registry_file(root, events):
    import yaml
    from dataclasses import asdict
    records = []
    for event in events:
        records.append({"id": event.id, "url": event.url, "name": event.name,
            "date": {"start": str(event.start_date), "end": str(event.end_date)},
            "format": event.format, "series": event.series, "structure": event.structure,
            "enabled": event.enabled, "review_status": event.review_status, "tabletop": True,
            "team_event": False, "mixed_format": event.mixed_format,
            "raw_requests": [{"id": "tournament", "resource_type": "tournament", "url": event.url, "content_type": "html"}],
            "include": {"swiss": True, "playoffs": event.include_playoffs},
            "statistics": {"default_match_scope": "all_constructed_swiss",
                           "constructed_game_format": event.format, "include_playoffs": False},
            "phases": [{k: list(v) if isinstance(v, tuple) else v for k, v in asdict(p).items()
                        if v != ()} for p in event.phases],
            "advancement": asdict(event.advancement), "source_evidence": [event.url],
            "special_handling": [], "notes": event.notes})
    path = root / "configs/melee_events.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"schema_version": "3.2.0", "events": records}))
    return path


def public_products(root, event, document, event_path, *, rule_text=RULES):
    from mtgmeta.melee.publish import build_event_publication_from_paths
    from mtgmeta.melee.stats import statistics_document_bytes
    c, ledger, stats, matchup = derived(root, document, event_path, rule_text=rule_text)
    public = root / f"stats/modern/melee/events/{event.id}"
    public.mkdir(parents=True, exist_ok=True)
    for name, value in {**stats, "matchup": matchup}.items():
        (public / f"{name}.json").write_bytes(statistics_document_bytes(value))
    result = build_event_publication_from_paths(event_path,
        root / f"data/modern/melee/classifications/{event.id}.json",
        root / f"data/modern/melee/opportunities/{event.id}.json",
        root / "my_archetypes/modern.yaml", root / "configs/melee_events.yaml", root)
    write_json(public / "meta.json", result["meta"])
    catalog = write_json(root / "stats/modern/melee/index.json", result["catalog"])
    return c["classifier"]["digest"], catalog
