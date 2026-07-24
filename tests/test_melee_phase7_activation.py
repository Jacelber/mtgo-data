"""P7-01 reference-event activation and production-boundary contracts."""

from __future__ import annotations

from pathlib import Path

from mtgmeta.melee import load_melee_event_registry
from mtgmeta.melee.__main__ import main
from mtgmeta.melee.client import planned_request_urls


ROOT = Path(__file__).resolve().parents[1]
WHITELIST = ROOT / "configs" / "melee_events.yaml"


def test_only_reviewed_reference_event_is_activated_for_manual_collection():
    registry = load_melee_event_registry(WHITELIST)

    assert tuple(event.id for event in registry.events) == ("434455",)
    event = registry.require_fetchable("434455")
    assert event.enabled is True
    assert event.review_status == "verified"
    assert event.format == "modern"
    assert event.structure == "mixed"
    assert planned_request_urls(event.id, registry) == (
        "https://melee.gg/Tournament/View/434455",
    )


def test_activation_dry_run_does_not_create_data_or_statistics_outputs(tmp_path, capsys):
    raw_root = tmp_path / "data_raw"

    exit_code = main(
        (
            "--event-id",
            "434455",
            "--registry",
            str(WHITELIST),
            "--raw-root",
            str(raw_root),
        )
    )

    assert exit_code == 0
    assert '"mode": "dry-run"' in capsys.readouterr().out
    assert not raw_root.exists()


def test_complete_collection_still_requires_explicit_execute_flag(capsys):
    exit_code = main(
        (
            "--event-id",
            "434455",
            "--registry",
            str(WHITELIST),
            "--complete",
        )
    )

    assert exit_code == 2
    assert "--complete requires --execute" in capsys.readouterr().err
