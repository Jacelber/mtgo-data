"""Source protection follows provenance, not a special event or Pages contents."""
import json

import pytest

from mtgmeta.melee.integrity import MeleeSourceIntegrityError, retained_source_paths, validate_retained_source
from melee_synthetic import source_fixture, derived, write_json


@pytest.mark.parametrize("event_id", ["900001", "900002"])
def test_sources_need_no_pages_copy_and_allow_new_events_and_classification(tmp_path, event_id):
    event, document, path, snapshot = source_fixture(tmp_path, event_id=event_id)
    paths = validate_retained_source(tmp_path, event)
    assert paths == retained_source_paths(tmp_path, "modern", event_id)
    assert path in paths and snapshot / "manifest.json" in paths
    before = {p: p.read_bytes() for p in paths}
    derived(tmp_path, document, path)
    from melee_synthetic import RULES
    derived(tmp_path, document, path, rule_text=RULES.replace("name: Alpha", "name: Renamed Alpha"))
    assert validate_retained_source(tmp_path, event) == paths
    assert all(p.read_bytes() == b for p, b in before.items())
    assert not (tmp_path / "site").exists()


@pytest.mark.parametrize("damage", ["bytes", "hash", "missing", "extra", "manifest_event", "provenance",
    "normalized_event", "participant", "round", "match", "competitor", "duplicate_participant"])
def test_source_corruption_and_identity_mismatch_are_rejected(tmp_path, damage):
    event, document, path, snapshot = source_fixture(tmp_path)
    if damage == "bytes":
        with (snapshot / "deck-1.json").open("ab") as f:
            f.write(b" ")
    elif damage == "hash":
        p = snapshot / "deck-1.json"
        p.write_bytes(p.read_bytes().replace(b"Island", b"Forest"))
    elif damage == "missing":
        (snapshot / "deck-1.json").unlink()
    elif damage == "extra":
        (snapshot / "undeclared.json").write_text("{}")
    elif damage == "manifest_event":
        manifest = json.loads((snapshot / "manifest.json").read_bytes())
        manifest["event_id"] = "900099"
        write_json(snapshot / "manifest.json", manifest)
    else:
        if damage == "provenance":
            document["provenance"]["raw_artifacts"].pop()
        elif damage == "normalized_event":
            document["metadata"]["event_id"] = "900099"
        elif damage == "participant":
            document["participants"][0]["source_id"] = "99"
        elif damage == "round":
            document["rounds"][0]["number"] = 88
        elif damage == "match":
            document["matches"][0]["source_record_id"] = "another-match"
        elif damage == "competitor":
            document["matches"][0]["competitors"][0]["participant_id"] = document["participants"][-1]["id"]
        elif damage == "duplicate_participant":
            document["participants"].append(document["participants"][0])
        write_json(path, document)
    with pytest.raises(MeleeSourceIntegrityError):
        validate_retained_source(tmp_path, event)
