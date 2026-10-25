"""Independent identity and arithmetic oracles for construction statistics."""
from copy import deepcopy
from datetime import date, timedelta
import json

import pytest

from mtgmeta.classifier_closure import _direct_digest_family
from mtgmeta.mtgo import landing_screening, stats, top8
from test_mtgo_top8_restatement import _events, _rules


ALIAS = "Darval, Whose Web Protects"
ENTITY = "Spider-Man, Web-Slinger"


def deck(*cards):
    return {"main_deck": [{"name": name, "qty": qty} for name, qty in cards]}


@pytest.mark.parametrize("left,right", [
    (ALIAS, ENTITY),
    ("Wear // Tear", "Wear/Tear"),
    ("Roaring Furnace // Steaming Sauna", "Roaring Furnace/Steaming Sauna"),
    ("Callous Sell-Sword // Burn Together", "Callous Sell-Sword"),
])
def test_same_entity_representations_have_zero_distance(left, right):
    a, b = stats.deck_vector(deck((left, 2))), stats.deck_vector(deck((right, 2)))
    assert a == b
    assert sum(a.values()) == 2
    assert stats.weighted_l1(a, b, {key: 1 for key in a}) == 0


def test_alias_quantities_merge_before_per_deck_appearance():
    vectors = [stats.deck_vector(deck((ALIAS, 1), (ENTITY, 2))),
               stats.deck_vector(deck(("Island", 3)))]
    assert vectors[0] == {ENTITY: 3}
    assert stats.mean_vector(vectors) == {ENTITY: 1.5, "Island": 1.5}
    assert stats.appearance_rates(vectors) == {ENTITY: 0.5, "Island": 0.5}


def test_identity_is_not_casting_policy_or_source_fingerprint():
    source = deck((ALIAS, 2), ("Atraxa, Grand Unifier", 4),
                  ("Snow-Covered Island", 1), ("Island", 2),
                  ("SP//dr, Piloted by Peni", 1), ("Unregistered / Card", 1))
    source["side_deck"] = [{"name": "Mountain", "qty": 15}]
    original = deepcopy(source)
    vector = stats.deck_vector(source)
    assert vector == {ENTITY: 2, "Atraxa, Grand Unifier": 4, "Island": 3,
                      "SP//dr, Piloted by Peni": 1, "Unregistered / Card": 1}
    assert source == original
    assert landing_screening.deck_fingerprint(deck((ALIAS, 2))) != (
        landing_screening.deck_fingerprint(deck((ENTITY, 2))))
    assert stats.merge_cards(source["main_deck"]) == stats.merge_cards(original["main_deck"])
    assert ALIAS in {card["name"] for card in stats.merge_cards(source["main_deck"])}


def _sample_events():
    events = _events("Island")
    for index, player in enumerate(events[0][1]["players"]):
        player["main_deck"] = deck(("Island", 10),
            (ALIAS if index < 6 else ENTITY, 2 if index < 6 else 4))["main_deck"]
    return events


def test_real_base_pipeline_uses_entity_means_rates_medoid_and_anchor():
    events = _sample_events()
    rules = _rules("island-deck", "Island")
    bases, anchor = stats.build_base_pack(events, rules, events[0][0])
    base = bases["island-deck"]
    # Six decks have two copies, two have four: mean=20/8=2.5, presence=8/8.
    assert base["sample_size"] == 8
    assert base["mean"] == {"Island": 10, ENTITY: 2.5}
    assert base["weights"] == {"Island": 1, ENTITY: 1}
    assert base["denom"] == 12.5
    assert base["core"] == [
        {"name": "Island", "mean_qty": 10.0, "rate": 1.0},
        {"name": ENTITY, "mean_qty": 2.5, "rate": 1.0}]
    assert base["flex"] == []
    assert base["medoid_display"]["player"] == "Player 1"
    assert {c["name"] for c in base["medoid_display"]["main_deck"]} == {"Island", ALIAS}
    assert anchor == 1.5
    first, last = [stats.deck_vector(p) for p in (events[0][1]["players"][0],
                                                events[0][1]["players"][-1])]
    assert stats.normalize_dev_abs(stats.weighted_l1(first, base["mean"], base["weights"]), 12.5) == 4
    assert stats.normalize_dev_abs(stats.weighted_l1(last, base["mean"], base["weights"]), 12.5) == 12
    renamed = deepcopy(events)
    for player in renamed[0][1]["players"]:
        player["main_deck"][1]["name"] = ENTITY
    other, other_anchor = stats.build_base_pack(renamed, rules, events[0][0])
    assert other_anchor == anchor
    assert {k: v for k, v in base.items() if k != "medoid_display"} == {
        k: v for k, v in other["island-deck"].items() if k != "medoid_display"}


def test_alias_only_week_change_does_not_create_construction_shift():
    events = _sample_events()
    day, first = events[0]
    newer = deepcopy(first)
    newer["event_id"] = "1002"
    newer["starttime"] = str(day + timedelta(weeks=1)) + "T12:00:00Z"
    for player in newer["players"]:
        player["main_deck"][1]["name"] = ENTITY
    events.append((day + timedelta(weeks=1), newer))
    result = stats.recent_change_for_arch(events, _rules("island-deck", "Island"),
                                              events[-1][0], "island-deck", 1.5)
    assert result == (0, None)


def test_construction_digest_tracks_identity_policy_without_changing_source(monkeypatch):
    original = stats.construction_digest()
    monkeypatch.setattr(stats, "CARD_ALIASES", {**stats.CARD_ALIASES, "New Alias": ENTITY})
    assert stats.construction_digest() != original
    monkeypatch.undo()
    monkeypatch.setattr(stats, "CONSTRUCTION_CONTRACT_VERSION", "2.0.0")
    assert stats.construction_digest() != original


def test_live_construction_binding_rejects_legacy_or_stale_but_not_other_families(tmp_path):
    path = tmp_path / "range.json"
    doc = {"classifier_digest": "a" * 64}
    path.write_text(json.dumps(doc))
    assert _direct_digest_family(tmp_path, "mtgo_statistics", [path], "a" * 64)["state"] == "STALE_REGENERABLE"
    assert _direct_digest_family(tmp_path, "mtgo_matchups", [path], "a" * 64)["state"] == "CURRENT"
    doc["construction_digest"] = stats.construction_digest()
    path.write_text(json.dumps(doc))
    assert _direct_digest_family(tmp_path, "mtgo_statistics", [path], "a" * 64)["state"] == "CURRENT"
    doc["construction_digest"] = "b" * 64
    path.write_text(json.dumps(doc))
    assert _direct_digest_family(tmp_path, "mtgo_top8", [path], "a" * 64)["state"] == "STALE_REGENERABLE"


def test_top8_restatement_changes_derived_metrics_not_exact_source_or_classification(tmp_path, monkeypatch):
    events = _sample_events()
    rules = _rules("island-deck", "Island")
    day = events[0][0]
    current_vector = stats.deck_vector
    def old_vector(record):
        result = {}
        for card in record["main_deck"]:
            name = stats.normalize_legacy_card_name(card["name"])
            result[name] = result.get(name, 0) + card["qty"]
        return result
    monkeypatch.setattr(stats, "deck_vector", old_vector)
    monkeypatch.setattr(stats, "construction_digest", lambda: "b" * 64)
    old = top8.write_latest_week(events, rules, tmp_path, format_id="modern",
                                 today=date(2026, 1, 20), generated_at="fixed")
    filename = top8.iso_week_label(day) + ".json"
    before = json.loads(old[filename].read_text())
    monkeypatch.undo()
    assert stats.deck_vector is current_vector
    new = top8.write_latest_week(events, rules, tmp_path, format_id="modern",
                                 today=date(2026, 1, 20), generated_at="fixed")
    after = json.loads(new[filename].read_text())
    assert before["classifier_digest"] == after["classifier_digest"]
    assert before["construction_digest"] != after["construction_digest"]
    assert [top8._event_source(e) for e in before["events"]] == [
        top8._event_source(e) for e in after["events"]]
    assert json.loads(new["index.json"].read_text())["classification_impact"]["summary"]["classification_change_count"] == 0
    assert before["events"][0]["placements"][0]["exact_deck"]["deviation"] != after["events"][0]["placements"][0]["exact_deck"]["deviation"]
