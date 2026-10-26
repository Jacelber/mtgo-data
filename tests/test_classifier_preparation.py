"""A real batch must resolve facts before classification and freeze its inputs."""
from dataclasses import replace
import gzip
from hashlib import sha256
import json
from pathlib import Path

import pytest
import yaml

from mtgmeta.classifier import classifier_digest, classify_counts
from mtgmeta.classifier_cards import read_card_facts, use_card_facts, classifier_card_name
from mtgmeta.classifier_preparation import FACTS, prepare_repository_facts, resume_repository_facts, facts_preparation_batch
from mtgmeta.config import load_rule_set
from test_classifier_shared_semantics import family

ROOT = Path(__file__).resolve().parents[1]


def setup_root(tmp_path):
    root = tmp_path / "candidate"
    library = json.loads((ROOT / FACTS).read_bytes())
    library["cards"] = [c for c in library["cards"] if c["key"] in {"Island", "Counterspell"}]
    library["source"] = {"uri": "https://data.scryfall.io/oracle-cards/old.jsonl.gz", "sha256": "a" * 64}
    path = root / FACTS
    path.parent.mkdir(parents=True)
    payload = (json.dumps(library, ensure_ascii=False, indent=2) + "\n").encode()
    path.write_bytes(payload)
    rule = {"schema_version": "1.2.0", "format": "standard", "card_facts_sha256": sha256(payload).hexdigest(),
            "archetypes": [{"id": "control", "name": "Control", "priority": 20,
                            "rules": [{"id": "control-core", "priority": 20, "conditions": {"all": [{"card": "Counterspell"}]}}]}]}
    semantic = yaml.safe_load((ROOT / "my_archetypes/standard.yaml").read_bytes())["semantic_features"]
    dependency = root / semantic["manifest_path"]
    dependency.parent.mkdir(parents=True)
    dependency.write_bytes((ROOT / semantic["manifest_path"]).read_bytes())
    rule["semantic_features"] = semantic
    rules = root / "my_archetypes/standard.yaml"
    rules.parent.mkdir()
    rules.write_text(yaml.safe_dump(rule), encoding="utf-8")
    event = root / "data/standard/mtgo/events/1.json"
    event.parent.mkdir(parents=True)
    event.write_text(json.dumps({"players": [{"main_deck": [{"name": "Counterspell", "qty": 4}, {"name": "Island", "qty": 20}],
                                             "sideboard": [{"name": "Newly Observed Spell", "qty": 1}]}]}), encoding="utf-8")
    return root, library


def new_card():
    return {"object": "card", "oracle_id": "new-oracle-identity", "name": "Newly Observed Spell",
            "layout": "normal", "mana_cost": "{U}", "type_line": "Instant",
            "oracle_text": "Draw a card.", "colors": ["U"], "legalities": {"standard": "legal"}}


def source_file(tmp_path, cards):
    path = tmp_path / "oracle.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for card in cards:
            handle.write(json.dumps(card) + "\n")
    return path


def test_complete_import_prepares_new_sideboard_and_keeps_prior_snapshot(tmp_path):
    root, old = setup_root(tmp_path)
    before = load_rule_set(root / "my_archetypes/standard.yaml")
    result = prepare_repository_facts(root, ["standard"], oracle_gzip=source_file(tmp_path, [new_card()]), refresh=False)
    assert result["requests"] == 0
    updated = read_card_facts(root / FACTS)
    assert len(updated.cards) == 3
    for card in old["cards"]:
        assert next(c for c in json.loads((root / FACTS).read_bytes())["cards"] if c["oracle_id"] == card["oracle_id"]) == card
    after = load_rule_set(root / "my_archetypes/standard.yaml")
    fixed = load_rule_set(Path(result["snapshot"]) / "my_archetypes/standard.yaml")
    assert classifier_digest(after) == classifier_digest(fixed) != classifier_digest(before)
    # Independent one-color rule: the new sideboard spell cannot obstruct it.
    rules = replace(family(), facts=after.facts)
    assert classify_counts(rules, {"Counterspell": 4, "Island": 20}, {"Newly Observed Spell": 1}).status == "classified"
    with use_card_facts(before.facts):
        assert "Newly Observed Spell" not in before.facts.cards
    assert before.facts.digest != after.facts.digest


def test_bulk_update_and_exact_missing_card_are_automatic_and_retained(tmp_path):
    root, _ = setup_root(tmp_path)
    bulk = source_file(tmp_path, [])
    calls = []

    def download(url):
        calls.append(url)
        if url.endswith("/bulk-data/oracle-cards"):
            return json.dumps({"object": "bulk_data", "type": "oracle_cards", "jsonl_download_uri": "https://data.scryfall.io/new.jsonl.gz"}).encode()
        if url.endswith("new.jsonl.gz"):
            return bulk.read_bytes()
        return json.dumps(new_card()).encode()

    result = prepare_repository_facts(root, ["standard"], download=download)
    assert len(calls) == result["requests"] == 3
    assert "Newly Observed Spell" in read_card_facts(root / FACTS).cards
    source = json.loads((root / FACTS).read_bytes())["source"]
    evidence = source["supplements"][0]
    assert sha256((root / evidence["response_path"]).read_bytes()).hexdigest() == evidence["response_sha256"]
    assert (Path(result["snapshot"]) / evidence["response_path"]).is_file()


def test_unavailable_source_never_writes_partial_facts_or_rule_metadata(tmp_path):
    root, _ = setup_root(tmp_path)
    paths = [root / FACTS, root / "my_archetypes/standard.yaml"]
    before = [p.read_bytes() for p in paths]

    def unavailable(url):
        raise OSError("source offline")

    with pytest.raises(OSError, match="source offline"):
        prepare_repository_facts(root, ["standard"], download=unavailable)
    assert [p.read_bytes() for p in paths] == before
    assert not (root / ".classifier-facts/preparing").exists()
    assert not list((root / ".classifier-facts").glob("*/preparation.json"))


def test_exact_lookup_can_complete_a_batch_when_bulk_definition_is_unavailable(tmp_path):
    root, _ = setup_root(tmp_path)

    def download(url):
        if url.endswith("bulk-data/oracle-cards"):
            raise OSError("bulk unavailable")
        return json.dumps(new_card()).encode()

    result = prepare_repository_facts(root, ["standard"], download=download)
    assert result["changed"]
    assert "Newly Observed Spell" in read_card_facts(root / FACTS).cards
    assert load_rule_set(root / "my_archetypes/standard.yaml").facts.digest == result["facts_sha256"]


def test_complete_local_input_can_continue_when_remote_is_offline(tmp_path):
    root, _ = setup_root(tmp_path)
    path = root / "data/standard/mtgo/events/1.json"
    value = json.loads(path.read_bytes())
    value["players"][0]["sideboard"] = []
    path.write_text(json.dumps(value), encoding="utf-8")
    before = (root / FACTS).read_bytes()

    def unavailable(url):
        raise OSError("source offline")

    result = prepare_repository_facts(root, ["standard"], download=unavailable)
    assert result["source_error"] == "source offline"
    assert not result["changed"] and (root / FACTS).read_bytes() == before


def test_snapshot_name_resolution_does_not_leak_between_two_loaded_versions(tmp_path):
    root, _ = setup_root(tmp_path)
    first = load_rule_set(root / "my_archetypes/standard.yaml")
    value = json.loads((root / FACTS).read_bytes())
    value["cards"][0]["names"].append("Snapshot Alias")
    payload = json.dumps(value).encode()
    (root / FACTS).write_bytes(payload)
    path = root / "my_archetypes/standard.yaml"
    rules = yaml.safe_load(path.read_bytes())
    rules["card_facts_sha256"] = sha256(payload).hexdigest()
    path.write_text(yaml.safe_dump(rules), encoding="utf-8")
    second = load_rule_set(path)
    for facts, expected in [(first.facts, "Snapshot Alias"), (second.facts, value["cards"][0]["key"]), (first.facts, "Snapshot Alias")]:
        with use_card_facts(facts):
            assert classifier_card_name("Snapshot Alias") == expected


def test_interrupted_installation_blocks_readers_and_resumes_without_network(tmp_path):
    root, _ = setup_root(tmp_path)
    paths = [root / FACTS, root / "my_archetypes/standard.yaml"]
    before = [p.read_bytes() for p in paths]
    result = prepare_repository_facts(root, ["standard"], oracle_gzip=source_file(tmp_path, [new_card()]), refresh=False)
    after = [p.read_bytes() for p in paths]
    # Reproduce a process interruption between replacing facts and rule metadata.
    paths[1].write_bytes(before[1])
    home = root / ".classifier-facts"
    (home / "pending.json").write_text(json.dumps({"snapshot": Path(result["snapshot"]).name}), encoding="utf-8")
    (home / "preparing").mkdir()
    with pytest.raises(ValueError, match="resume interrupted fact preparation"):
        load_rule_set(paths[1])
    resumed = resume_repository_facts(root)
    assert resumed["resumed"]
    assert [p.read_bytes() for p in paths] == after
    assert load_rule_set(paths[1]).facts.digest == result["facts_sha256"]


def test_nested_generation_reuses_one_prepared_batch(tmp_path):
    root, _ = setup_root(tmp_path)
    source = source_file(tmp_path, [new_card()])

    @facts_preparation_batch
    def generate():
        first = prepare_repository_facts(root, ["standard"], oracle_gzip=source, refresh=False)
        def no_second_request(url):
            raise AssertionError("A prepared batch must not check the source again")
        second = prepare_repository_facts(root, ["standard"], download=no_second_request)
        assert second["reused_batch"] and second["requests"] == 0
        assert second["snapshot"] == first["snapshot"]
    generate()
