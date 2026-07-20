"""Executable P3-01 contract for generalizing the MTGO pipeline."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "tests/fixtures/mtgo/format_pipeline_contract.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_contract_is_pinned_to_the_phase_2_recovery_baseline():
    contract = load_json(CONTRACT_PATH)

    assert contract["schema_version"] == 1
    assert contract["task"] == "P3-01"
    assert contract["baseline"] == {
        "tag": "phase-2-shared-classifier-baseline",
        "commit": "a9e35a2c957d32f2bc0fb43c8a0777a25f71c31c",
    }
    assert not any(contract["scope"].values())


def test_only_standard_is_executable_and_vintage_remains_decision_gated():
    states = load_json(CONTRACT_PATH)["format_state_model"]

    known = set(states["known_format_ids"])
    executable = set(states["executable_format_ids"])
    planned = set(states["planned_non_executable_format_ids"])
    gated = set(states["decision_gated_format_ids"])

    assert known == {"standard", "pauper", "modern", "pioneer", "legacy", "vintage"}
    assert executable == {"standard"}
    assert executable | planned | gated == known
    assert not executable & planned
    assert not executable & gated
    assert gated == {"vintage"}


def test_standard_paths_resolve_from_format_templates_and_match_public_contract():
    contract = load_json(CONTRACT_PATH)
    templates = contract["format_path_templates"]
    standard = contract["standard_contract"]
    paths = standard["paths"]

    for key in ("events", "matches", "rules", "statistics", "reports"):
        assert "{format}" in templates[key]
        assert templates[key].format(format="standard") == paths[key]

    assert (ROOT / paths["events"]).is_dir()
    assert (ROOT / paths["matches"]).is_dir()
    assert (ROOT / paths["rules"]).is_file()
    assert (ROOT / paths["statistics"]).is_dir()
    assert (ROOT / paths["reports"]).is_dir()

    public_contract = load_json(ROOT / standard["public_contract_fixture"])
    assert public_contract["format"] == standard["format"]
    assert public_contract["source"] == standard["source"]
    assert public_contract["ranges"] == standard["ranges"]
    assert public_contract["catalogs"] == standard["public_catalogs"]


def test_generalized_interface_requires_explicit_safe_format_selection():
    interface = load_json(CONTRACT_PATH)["generalized_interface"]

    assert interface["explicit_format_required"] is True
    assert interface["legacy_wrappers_default_to"] == "standard"
    assert interface["unsupported_format_fails_clearly"] is True
    assert interface["disabled_format_fails_clearly"] is True
    assert interface["cross_format_reads_prohibited"] is True
    assert interface["cross_format_writes_prohibited"] is True
    assert interface["implicit_standard_fallback_prohibited"] is True


def test_migration_sequence_covers_every_phase_3_pipeline_capability_once():
    contract = load_json(CONTRACT_PATH)
    units = contract["migration_units"]
    tasks = [unit["task"] for unit in units]
    covered = [capability for unit in units for capability in unit["capabilities"]]

    assert tasks == ["P3-02", "P3-03", "P3-04", "P3-05", "P3-06", "P3-07", "P3-08"]
    assert len(covered) == len(set(covered))
    assert set(covered) == set(contract["required_capabilities"])
    for unit in units:
        for entry_point in unit["current_entry_points"]:
            assert (ROOT / entry_point).is_file(), entry_point


def test_hardcoded_inventory_tracks_migrated_and_remaining_boundaries():
    inventory = load_json(CONTRACT_PATH)["hardcoded_inventory"]
    migrated_snippets = {
        "batch_mtgo.py": {"folder = os.path.join(DATA_DIR, fmt)"},
        "classify_standard.py": {
            'RULES_FILE = "my_archetypes/standard.yaml"',
            'DATA_DIR = "data/standard"',
        },
        "stats_standard.py": {
            'DATA_DIR = "data/standard"',
            'os.path.join("stats", "standard", "mtgo")',
        },
        "fetch_videre_matches.py": {
            'FORMAT = "standard"',
            'OUT_DIR = os.path.join("data", "standard", "mtgo", "matches")',
        },
        "stats_matchup.py": {
            'OFFICIAL_DIR = "data/standard"',
            'MATCHES_DIR = "data/standard/mtgo/matches"',
            'OUT_DIR = "stats/standard/mtgo"',
        },
        "generate_classification_reports.py": {
            'default=Path("data/standard")',
            'default=Path("my_archetypes/standard.yaml")',
            'default=Path("reports/standard/mtgo")',
        },
        "src/mtgmeta/reports.py": {'"format": "standard"'},
        "weekly_pickup.py": {
            'OUT_DIR = os.path.join("stats", "standard", "mtgo", "pickup")'
        },
        "gen_meta.py": {
            'RULES_FILE = "my_archetypes/standard.yaml"',
            'OUT_DIR = os.path.join("stats", "standard", "mtgo")',
        },
        ".github/workflows/update.yml": {
            "run: python -B batch_mtgo.py",
            "run: python -B stats_standard.py",
            "run: python -B stats_matchup.py",
            "stats/standard/mtgo/pickup",
        },
    }

    assert len(inventory) == 12
    for item in inventory:
        path = ROOT / item["file"]
        assert path.is_file(), item["file"]
        source = path.read_text(encoding="utf-8")
        for snippet in item["snippets"]:
            if snippet in migrated_snippets.get(item["file"], set()):
                assert snippet not in source, f"migrated Phase 3 snippet remains in {item['file']}: {snippet}"
            else:
                assert snippet in source, f"missing unresolved inventory snippet in {item['file']}: {snippet}"
