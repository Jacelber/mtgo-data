import json
from pathlib import Path

from validate_schemas import validate_manifest


ROOT = Path(__file__).resolve().parents[1]


def test_melee_manifests_are_dynamic_and_cover_internal_and_public_documents():
    public = json.loads((ROOT / "schemas/manifest.json").read_text(encoding="utf-8"))
    internal = json.loads(
        (ROOT / "schemas/melee-data-manifest.json").read_text(encoding="utf-8")
    )
    public_patterns = {item["pattern"] for item in public["mappings"]}
    internal_patterns = {item["pattern"] for item in internal["mappings"]}

    assert not any("434455" in pattern for pattern in public_patterns)
    assert {
        "stats/*/melee/index.json",
        "stats/*/melee/events/*/overview.json",
        "stats/*/melee/events/*/decks.json",
        "stats/*/melee/events/*/matchup.json",
        "stats/*/melee/events/*/quality.json",
        "stats/*/melee/events/*/meta.json",
    } <= public_patterns
    assert internal_patterns == {
        "data/*/melee/events/*.json",
        "data/*/melee/classifications/*.json",
        "data/*/melee/opportunities/*.json",
    }


def test_current_melee_documents_pass_both_complete_manifests():
    for relative in ("schemas/manifest.json", "schemas/melee-data-manifest.json"):
        checked, failures = validate_manifest(ROOT, ROOT / relative)
        assert checked > 0
        assert failures == []
