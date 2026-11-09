import json

import pytest

from mtgmeta.melee.publish import MeleePublicationError, _verified_outputs
from mtgmeta.melee.stats import statistics_document_bytes


@pytest.mark.parametrize("compact_name", ["matchup", "overview", "decks", "quality"])
def test_compact_matchup_preserves_values_and_binds_actual_bytes(
    tmp_path, compact_name
):
    rebuilt = {
        name: {"schema_version": "1.0.0", "count": 3}
        for name in ("overview", "decks", "quality")
    }
    rebuilt["matchup"] = {
        "schema_version": "1.0.0",
        "name": "洁斯凯控制",
        "wins": 2,
        "losses": 1,
        "draws": 0,
    }
    for name, document in rebuilt.items():
        payload = statistics_document_bytes(document, compact=name == compact_name)
        (tmp_path / f"{name}.json").write_bytes(payload)
    documents, descriptors = _verified_outputs(tmp_path, rebuilt)
    payload = (tmp_path / f"{compact_name}.json").read_bytes()
    assert json.loads(payload) == rebuilt[compact_name] == documents[compact_name]
    assert len(payload) < len(statistics_document_bytes(rebuilt[compact_name]))
    assert descriptors[compact_name]["bytes"] == len(payload)
    changed = dict(rebuilt["matchup"], wins=3)
    (tmp_path / "matchup.json").write_bytes(
        statistics_document_bytes(changed, compact=True)
    )
    with pytest.raises(MeleePublicationError, match="deterministic rebuild"):
        _verified_outputs(tmp_path, rebuilt)
