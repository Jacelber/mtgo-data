from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from mtgmeta import mana_identity


def write_fixture(root: Path, *, approved=None, candidates=None) -> None:
    config = root / "configs/archetype_mana_identities.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "formats": {
                    "fixture": {
                        "approved": approved or {},
                        "candidates": candidates or {},
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    hierarchy = root / "stats/fixture/mtgo/archetype_hierarchy.json"
    hierarchy.parent.mkdir(parents=True, exist_ok=True)
    hierarchy.write_text(
        json.dumps(
            {
                "parents": [{"id": "artifacts"}],
                "leaves": [{"id": "artifacts"}],
            }
        ),
        encoding="utf-8",
    )
    rendered = root / "assets/js/phase8/archetype-visuals.js"
    rendered.parent.mkdir(parents=True, exist_ok=True)
    rendered.write_text(
        'const manaIdentities = Object.freeze({\n'
        '  fixture: Object.freeze({\n'
        '    "artifacts": Object.freeze(["c"]),\n'
        '  }),\n'
        '});\n',
        encoding="utf-8",
    )


def test_colorless_requires_the_c_indicator(tmp_path):
    write_fixture(tmp_path, approved={"artifacts": []})
    with pytest.raises(ValueError, match="at least one indicator"):
        mana_identity.load_mana_identities(tmp_path)

    write_fixture(tmp_path, approved={"artifacts": ["c", "u"]})
    with pytest.raises(ValueError, match="cannot combine colorless"):
        mana_identity.load_mana_identities(tmp_path)

    write_fixture(tmp_path, approved={"artifacts": ["c"]})
    mana_identity.require_complete_mana_identities(tmp_path, "fixture")


def test_public_coverage_rejects_missing_and_unreviewed_identities(tmp_path):
    write_fixture(tmp_path)
    with pytest.raises(ValueError, match="missing mana identities: artifacts"):
        mana_identity.require_complete_mana_identities(tmp_path, "fixture")

    write_fixture(
        tmp_path,
        candidates={"artifacts": {"colors": ["c"], "basis": "review fixture"}},
    )
    with pytest.raises(ValueError, match="unreviewed mana identities: artifacts"):
        mana_identity.require_complete_mana_identities(tmp_path, "fixture")


def test_public_coverage_rejects_stale_rendered_metadata(tmp_path):
    write_fixture(tmp_path, approved={"artifacts": ["u"]})
    with pytest.raises(ValueError, match="stale rendered mana identities"):
        mana_identity.require_complete_mana_identities(tmp_path, "fixture")


@pytest.mark.parametrize("format_id", ("standard", "modern", "pauper", "pioneer"))
def test_classifier_rules_have_approved_rendered_mana_identities(format_id):
    root = Path(__file__).resolve().parents[1]
    archetypes = yaml.safe_load(
        (root / "my_archetypes" / f"{format_id}.yaml").read_text(encoding="utf-8")
    )["archetypes"]
    required = {archetype["id"] for archetype in archetypes}
    required.update(
        f'{archetype["id"]}/{subtype["id"]}'
        for archetype in archetypes
        for subtype in archetype.get("subtypes", [])
    )
    entries = mana_identity.load_mana_identities(root)[format_id]
    assert required <= entries.keys()
    assert all(entries[identity_id].status == "approved" for identity_id in required)
    assert mana_identity.rendered_mana_identities(root, format_id) == {
        identity_id: entry.colors for identity_id, entry in entries.items()
    }
