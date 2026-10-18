import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from mtgmeta.mtgo import landing_editorial, landing_tabletop
from tools import weekly_maintenance
from test_weekly_cross_week_and_faces import retained_content

ROOT = Path(__file__).resolve().parents[1]


def retained_event(root):
    event = {"metadata": {"constructed_format": "modern", "name": "Two-day event",
                         "date": {"start": "2026-10-03", "end": "2026-10-04"}},
             "rounds": ([{"swiss": True, "game_format": "modern", "stage": "day1" if n < 8 else "day2"} for n in range(12)]
                        + [{"swiss": False, "game_format": "modern", "stage": "playoff"}])}
    paths = {"event": "data/modern/melee/events/123.json", "classification": "data/class.json",
             "opportunity": "data/opportunities.json", "taxonomy": "configs/taxonomy.json"}
    inputs = {}
    for key, path in paths.items():
        weekly_maintenance.write(root / path, event if key == "event" else {})
        inputs[key + "_path"] = path
        inputs[key + "_sha256"] = hashlib.sha256((root / path).read_bytes()).hexdigest()
    base = {"participant_id": "p1", "player_name": "One", "final_rank": 11,
            "classification": {"status": "classified", "archetype_id": "prowess", "subtype_id": None,
                               "archetype_name": "Prowess", "subtype_name": None},
            "decklist": {"status": "submitted", "cards": [{"name": "Card A", "quantity": 60, "section": "main"}]},
            "scopes": {"all_constructed": {"constructed_points": 28, "result_counts": {"played_win": 9, "played_loss": 2, "intentional_draw": 1}}}}
    three_losses = deepcopy(base)
    three_losses.update(participant_id="p2", final_rank=12)
    three_losses["scopes"]["all_constructed"].update(constructed_points=25,
        result_counts={"played_win": 8, "played_loss": 3, "intentional_draw": 1})
    unknown_score = deepcopy(base)
    unknown_score.update(participant_id="p3", final_rank=13)
    unknown_score["scopes"]["all_constructed"]["result_counts"]["unknown_result"] = 1
    top8 = []
    for rank in range(1, 9):
        entry = deepcopy(base)
        entry.update(participant_id=f"top{rank}", final_rank=rank,
                     decklist={"status": "unavailable", "cards": []})
        entry["scopes"]["all_constructed"].update(constructed_points=31,
            result_counts={"played_win": 10, "played_loss": 1, "intentional_draw": 1})
        top8.append(entry)
    weekly_maintenance.write(root / "stats/modern/melee/events/123/decks.json",
                             {"event_id": "123", "format": "modern", "input": inputs,
                              "decks": [base, three_losses, unknown_score, *top8]})


def test_swiss_boundary_draws_and_unresolved_results():
    assert landing_tabletop.swiss_record({"played_win": 10, "played_loss": 2,
                                         "intentional_draw": 1, "bye": 1}) == {"wins": 11, "losses": 2, "draws": 1}
    assert landing_tabletop.swiss_record({"drop_unplayed": 4}) is None
    assert landing_tabletop.swiss_record({"played_win": 9, "unknown_result": 1}) is None


def test_retained_catalog_exact_source_and_no_rank_eight_limit(tmp_path):
    retained_event(tmp_path)
    value = landing_tabletop.build_catalog(tmp_path, "modern", "2026-W40", ["123"])
    assert len(value["decks"]) == 1
    deck = value["decks"][0]
    assert deck["final_rank"] == 11 and deck["reference"] == "melee:123:11"
    assert deck["swiss_record"] == {"wins": 9, "losses": 2, "draws": 1}
    assert value["events"][0]["unresolved_record_count"] == 1
    source = {"format": "modern", "week": {"id": "2026-W40"}, "all_top8": [], "tabletop": value,
              "bindings": {"tabletop_digest": landing_tabletop.digest(value)}}
    assert landing_tabletop.validate_retained(tmp_path, source) == source["bindings"]
    changed = deepcopy(source)
    changed["tabletop"]["decks"][0]["main_deck"][0]["qty"] -= 1
    with pytest.raises(ValueError, match="changed"):
        landing_tabletop.validate_retained(tmp_path, changed)
    with pytest.raises(ValueError, match="format/week"):
        landing_tabletop.build_catalog(tmp_path, "modern", "2026-W39", ["123"])
    (tmp_path / "data/class.json").write_text('{"changed":true}')
    with pytest.raises(ValueError, match="input changed"):
        landing_tabletop.build_catalog(tmp_path, "modern", "2026-W40", ["123"])


def test_tabletop_materialization_carries_source_without_mtgo_population_change(tmp_path):
    retained_event(tmp_path)
    value = landing_tabletop.build_catalog(tmp_path, "modern", "2026-W40", ["123"])
    deck = value["decks"][0]
    token = deck["token"]
    source = {"format": "modern", "all_top8": [], "tabletop": value, "review": {
        "top_copy": {"items": [{"order": 1, "text": {"zh": token, "en": token}}]},
        "features": {"items": [{"destination_id": token, "parent_id": "prowess", "subtype_id": None,
            "category": "new_technology", "source_order": 1, "featured_cards": ["Card A"],
            "positioning": {"zh": "说明", "en": "Copy"}, "supporting_facts": []}]}}}
    names = {("modern", "prowess", None): {"zh": "灵技", "en": "Prowess"}}
    result = landing_editorial.materialize_review(source, names, decks={token: deck})
    assert source["all_top8"] == []
    for actual in (result["features"][0]["deck"], result["weekly_summary"][0]["deck_links"][0]["deck"]):
        assert actual["source"] == "melee" and actual["event_name"] == "Two-day event"
        assert actual["final_rank"] == 11 and actual["swiss_record"]["losses"] == 2


def test_source_qualified_public_rank_contract():
    schema = json.loads((ROOT / "schemas/mtgo-landing.schema.json").read_text())
    definition = schema["$defs"]["featureDeck"]
    validator = Draft202012Validator({**definition, "$defs": schema["$defs"]})
    deck = {"event_id": "123", "deck_id": "a" * 20, "deck_fingerprint_sha256": "a" * 64,
            "player": "Player", "final_rank": 11, "player_count": 100, "starttime": "2026-10-03",
            "main_deck": [], "side_deck": []}
    assert not validator.is_valid(deck)

    deck.update(source="melee", event_name="Event", swiss_record={"wins": 9, "losses": 2, "draws": 1})
    assert validator.is_valid(deck)
    deck["swiss_record"]["losses"] = 3
    assert validator.is_valid(deck)
    deck["swiss_record"]["losses"] = -1
    assert not validator.is_valid(deck)


def test_retained_tabletop_reference_follows_current_taxonomy_without_changing_cards(tmp_path):
    retained_event(tmp_path)
    original = landing_tabletop.build_catalog(tmp_path, "modern", "2026-W40", ["123"])
    source = {"format": "modern", "week": {"id": "2026-W40"}, "all_top8": [], "tabletop": original,
              "bindings": {"tabletop_digest": landing_tabletop.digest(original)}}
    weekly_maintenance.write(tmp_path / "configs/taxonomy.json", {
        "schema_version": "1.0.0", "format": "modern", "archetypes": [{
            "id": "current", "name": "Current", "priority": 1, "rules": [{
                "id": "current", "priority": 1, "conditions": {"all": [{"card": "Card A", "zone": "main", "min_count": 1}]}}]}]})
    cache = {}
    current = landing_tabletop.build_catalog(tmp_path, "modern", "2026-W40", ["123"], classification_cache=cache)
    assert current["decks"][0]["parent_id"] == "current"
    assert current["decks"][0]["token"] == original["decks"][0]["token"]
    assert current["decks"][0]["main_deck"] == original["decks"][0]["main_deck"]
    assert landing_tabletop.validate_retained(tmp_path, source, classification_cache=cache) == source["bindings"]
    assert len(cache) == 1


@pytest.mark.parametrize("losses", [2, 3])
def test_tabletop_accepted_import_and_generation_keep_mtgo_facts(retained_content, losses):
    from datetime import date
    from mtgmeta.mtgo import landing, review_submission as submissions
    from tools.import_landing_conversation import import_content
    root, path, facts = retained_content
    source = landing_editorial.load_review_document(path, root / landing_editorial.DEFAULT_REVIEW_SCHEMA)
    before = deepcopy(facts["page"])
    # Synthetic retained Melee input only; this does not select a live Feature.
    original = source["all_top8"][0]
    retained_event(root)
    event = weekly_maintenance.read(root / "data/modern/melee/events/123.json")
    event["metadata"].update(constructed_format="pauper", date={"start": "2026-09-26", "end": "2026-09-27"})
    for round_ in event["rounds"]:
        round_["game_format"] = "pauper"
    weekly_maintenance.write(root / "data/pauper/melee/events/123.json", event)
    public = weekly_maintenance.read(root / "stats/modern/melee/events/123/decks.json")
    public["format"] = "pauper"
    public["input"].update(event_path="data/pauper/melee/events/123.json",
        event_sha256=hashlib.sha256((root / "data/pauper/melee/events/123.json").read_bytes()).hexdigest())
    item = public["decks"][0]
    if losses == 3:
        item["scopes"]["all_constructed"].update(constructed_points=27,
            result_counts={"played_win": 9, "played_loss": 3})
        for qualifier in public["decks"][3:]:
            qualifier["scopes"]["all_constructed"].update(constructed_points=30,
                result_counts={"played_win": 10, "played_loss": 2})
    item["classification"].update(archetype_id=original["parent_id"], subtype_id=original["subtype_id"])
    item["decklist"]["cards"] = [dict(name=c["name"], quantity=c["qty"], section=section)
        for zone, section in (("main_deck", "main"), ("side_deck", "sideboard")) for c in original[zone]]
    weekly_maintenance.write(root / "stats/pauper/melee/events/123/decks.json", public)
    source["tabletop"] = landing_tabletop.build_catalog(root, "pauper", "2026-W39", ["123"])
    source["bindings"]["tabletop_digest"] = landing_tabletop.digest(source["tabletop"])
    deck = source["tabletop"]["decks"][0]
    token = deck["token"]
    source["review"] = {"top_copy": {"reviewed": True, "items": [{"order": 1, "text": {"zh": token, "en": token}}]},
        "features": {"reviewed": True, "explicit_empty": False, "items": [{"destination_id": token,
            "parent_id": deck["parent_id"], "subtype_id": deck["subtype_id"], "category": "new_technology",
            "source_order": 1, "featured_cards": [c["name"] for c in deck["main_deck"][:4]],
            "positioning": {"zh": "隔离测试", "en": "Synthetic test"}, "supporting_facts": []}]}}
    bindings = {k: source["bindings"][k] for k in ("source_event_ids", "classifier_digest",
        "selection_policy_digest", "machine_fact_digest", "link_catalog_digest", "tabletop_digest")}
    packet = submissions.make_content_packet(root, "pauper", "2026-W39", source["review"], before["environment"],
        landing_editorial.load_name_catalog_document(root / landing_editorial.DEFAULT_NAME_CATALOG),
        bindings=bindings, facts=facts["review_facts"])
    receipt = submissions.record_decision(packet, None, list(packet["dimensions"]),
        evidence="SYNTHETIC retained tabletop test", accepted_on="2026-09-30", entrypoint="private://synthetic")
    receipt["admitted_scope"] = facts["admitted_scope"]
    source["acceptance"] = {"submission": packet, "decisions": receipt}
    path = import_content(root, source)
    restored = landing_editorial.load_review_document(path, root / landing_editorial.DEFAULT_REVIEW_SCHEMA)
    assert restored["tabletop"] == source["tabletop"] and restored["all_top8"] == source["all_top8"]
    assert all("parent_id" not in item and "subtype_id" not in item
               for item in restored["review"]["features"]["items"])
    status, page = landing.build_document(root, "pauper", today=date(2026, 9, 28))
    assert page["features"]["items"][0]["deck"]["source"] == "melee", status
    assert page["features"]["items"][0]["deck"]["final_rank"] == 11
    assert page["features"]["items"][0]["deck"]["swiss_record"]["losses"] == losses
    assert page["populations"] == before["populations"]
    assert page["environment"] == before["environment"]
    assert page["source_event_ids"] == before["source_event_ids"]



def test_points_cutoff_uses_lowest_qualifier_and_keeps_all_ties(tmp_path):
    retained_event(tmp_path)
    path = tmp_path / "stats/modern/melee/events/123/decks.json"
    public = weekly_maintenance.read(path)
    # Final 8th is not necessarily the lowest Swiss scorer: final 2nd has 30.
    public["decks"][4]["scopes"]["all_constructed"].update(constructed_points=30,
        result_counts={"played_win": 10, "played_loss": 2})
    def add(pid, counts, rank=20):
        deck = deepcopy(public["decks"][0])
        deck.update(participant_id=pid, final_rank=rank)
        score = landing_tabletop.swiss_record(counts)
        deck["scopes"]["all_constructed"].update(result_counts=counts,
            constructed_points=3 * score["wins"] + score["draws"])
        public["decks"].append(deck)
    add("three-loss", {"played_win": 9, "played_loss": 3})
    add("tie", {"played_win": 8, "played_loss": 1, "intentional_draw": 3}, 99)
    add("bye", {"played_win": 8, "bye": 1, "played_loss": 3})
    add("exempt", {"played_win": 8, "awarded_win_top8_lock": 1, "played_loss": 3})
    add("below", {"played_win": 8, "played_loss": 2, "intentional_draw": 2})
    add("early", {"played_win": 9})
    add("zero-two", {"played_loss": 2})
    add("inconsistent", {"played_win": 9, "played_loss": 3})
    public["decks"][-1]["scopes"]["all_constructed"]["constructed_points"] = 50
    weekly_maintenance.write(path, public)
    result = landing_tabletop.build_catalog(tmp_path, "modern", "2026-W40", ["123"])
    event = result["events"][0]
    assert event["top8_min_swiss_points"] == 30
    assert event["minimum_swiss_points"] == 27
    expected = {"p1", "three-loss", "tie", "bye", "exempt"}
    assert {d["token"] for d in result["decks"]} == {
        "deck:" + landing_tabletop.digest(["melee", "123", pid])[:20] for pid in expected}
    # Candidate selection is not a different public statistics definition.
    assert weekly_maintenance.read(path) == public


@pytest.mark.parametrize("missing", ["rank", "score", "rounds"])
def test_missing_cutoff_does_not_guess_or_expand(tmp_path, missing):
    retained_event(tmp_path)
    path = tmp_path / "stats/modern/melee/events/123/decks.json"
    public = weekly_maintenance.read(path)
    # A verified top-eight deck remains available independently of expansion.
    public["decks"][3]["decklist"] = deepcopy(public["decks"][0]["decklist"])
    if missing == "rank":
        public["decks"][-1]["final_rank"] = 9
    elif missing == "score":
        public["decks"][-1]["scopes"]["all_constructed"]["result_counts"]["unknown_result"] = 1
    else:
        event_path = tmp_path / "data/modern/melee/events/123.json"
        event = weekly_maintenance.read(event_path)
        event["rounds"] = []
        weekly_maintenance.write(event_path, event)
        public["input"]["event_sha256"] = hashlib.sha256(event_path.read_bytes()).hexdigest()
    weekly_maintenance.write(path, public)
    result = landing_tabletop.build_catalog(tmp_path, "modern", "2026-W40", ["123"])
    assert result["events"][0]["minimum_swiss_points"] is None
    assert result["events"][0]["selection_issue"]
    assert [d["final_rank"] for d in result["decks"]] == [1]


def test_retained_legacy_selection_survives_new_candidate_policy(tmp_path):
    retained_event(tmp_path)
    path = tmp_path / "stats/modern/melee/events/123/decks.json"
    public = weekly_maintenance.read(path)
    public["decks"][0]["scopes"]["all_constructed"].update(constructed_points=0,
        result_counts={"played_loss": 2})
    weekly_maintenance.write(path, public)
    old = landing_tabletop.build_catalog(tmp_path, "modern", "2026-W40", ["123"],
        selection_policy=landing_tabletop.LEGACY_POLICY)
    assert len(old["decks"]) == 1
    source = {"format": "modern", "week": {"id": "2026-W40"}, "all_top8": [],
              "tabletop": old, "bindings": {"tabletop_digest": landing_tabletop.digest(old)},
              "review": {"features": {"items": [{"destination_id": old["decks"][0]["token"]}]}}}
    unchanged = deepcopy(source)
    assert not landing_tabletop.build_catalog(tmp_path, "modern", "2026-W40", ["123"])["decks"]
    assert landing_tabletop.validate_retained(tmp_path, source) == source["bindings"]
    resolved = landing_editorial.resolve_review_decks(tmp_path, source, mtgo_catalog={})
    assert resolved[old["decks"][0]["token"]]["swiss_record"]["wins"] == 0
    assert source == unchanged
