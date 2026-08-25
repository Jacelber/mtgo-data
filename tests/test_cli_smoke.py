"""Smallest offline smoke for each installed command entry point."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from mtgmeta import catalog
from mtgmeta.melee.__main__ import main as melee_main
from mtgmeta.melee.client import MeleeRawFetchResult
from mtgmeta.mtgo import __main__ as mtgo_cli


ROOT = Path(__file__).resolve().parents[1]


def test_mtgo_cli_smoke(monkeypatch, tmp_path):
    calls = []

    def run(args, root, registry):
        calls.append((args.format_id, root, registry))
        return 0

    monkeypatch.setitem(mtgo_cli.RUNNERS, "build-statistics", run)

    result = mtgo_cli.main(
        [
            "--root",
            str(tmp_path),
            "--registry",
            str(ROOT / "configs" / "formats.yaml"),
            "--format",
            "modern",
            "build-statistics",
        ]
    )

    assert result == 0
    assert calls == [
        (
            "modern",
            tmp_path.resolve(),
            (ROOT / "configs" / "formats.yaml").resolve(),
        )
    ]


def test_landing_screening_uses_the_landing_review_command():
    args = mtgo_cli.build_parser().parse_args(
        ["--format", "standard", "landing-review", "prepare", "--if-absent"]
    )

    assert args.command == "landing-review"
    assert args.landing_review_command == "prepare"
    assert args.if_absent is True
    assert mtgo_cli.COMMAND_CAPABILITIES[args.command] == "landing_generation"


def test_landing_workbook_validation_stage_is_explicit_and_read_only():
    args = mtgo_cli.build_parser().parse_args(
        [
            "--format",
            "modern",
            "landing-review",
            "validate-xlsx",
            "review.xlsx",
            "--stage",
            "chinese",
            "--expected-sha256",
            "0" * 64,
        ]
    )

    assert args.landing_review_command == "validate-xlsx"
    assert args.stage == "chinese"
    assert args.expected_sha256 == "0" * 64


def test_melee_cli_smoke(tmp_path, capsys):
    def fetch(event_id, _registry, raw_root, *, dry_run):
        assert raw_root == tmp_path / "raw"
        assert dry_run is True
        return MeleeRawFetchResult(
            event_id,
            True,
            None,
            ("https://melee.gg/Tournament/View/434455",),
            (),
        )

    result = melee_main(
        [
            "--event-id",
            "434455",
            "--registry",
            str(ROOT / "configs" / "melee_events.yaml"),
            "--raw-root",
            str(tmp_path / "raw"),
        ],
        fetch=fetch,
    )

    assert result == 0
    assert json.loads(capsys.readouterr().out) == {
        "archive_path": None,
        "event_id": "434455",
        "mode": "dry-run",
        "planned_responses": None,
        "planned_urls": ["https://melee.gg/Tournament/View/434455"],
        "responses": 0,
        "resumed_responses": 0,
    }
    assert not (tmp_path / "raw").exists()


def test_catalog_cli_smoke(tmp_path):
    config = tmp_path / "configs" / "formats.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.3.0",
                "formats": [
                    {
                        "id": "fixture",
                        "display_name": "Fixture",
                        "state": "executable",
                        "public": False,
                        "mtgo": {
                            "enabled": True,
                            "event_collection_enabled": False,
                            "capabilities": ["catalog_generation"],
                            "paths": {
                                "events": "data/fixture",
                                "matches": "data/fixture/mtgo/matches",
                                "rules": "my_archetypes/fixture.yaml",
                                "statistics": "stats/fixture/mtgo",
                                "reports": "reports/fixture/mtgo",
                            },
                        },
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    output = tmp_path / "candidate" / "catalog.json"

    assert catalog.main(["--root", str(tmp_path), "--output", str(output)]) == 0

    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["document_type"] == "consumer_catalog"
    assert [item["id"] for item in document["formats"]] == ["fixture"]
    assert all(
        item["available"] is False
        for item in document["formats"][0]["products"]
    )


def test_catalog_requires_complete_mtgo_products_and_defaults_to_landing(tmp_path):
    document = catalog.build_catalog(ROOT, generated_at="2026-08-25T00:00:00+00:00")
    by_format = {item["id"]: item for item in document["formats"]}

    for format_id in ("standard", "modern"):
        assert by_format[format_id]["default_product_id"] == "mtgo-landing"
        assert {
            item["id"]
            for item in by_format[format_id]["products"]
            if item["available"] and item["id"].startswith("mtgo-")
        } == catalog.REQUIRED_MTGO_PRODUCT_IDS

    with pytest.raises(
        ValueError,
        match=r"public format 'standard' is missing required MTGO products:.*mtgo-landing",
    ):
        catalog.build_catalog(
            tmp_path,
            generated_at="2026-08-25T00:00:00+00:00",
            registry_path=ROOT / "configs" / "formats.yaml",
        )
