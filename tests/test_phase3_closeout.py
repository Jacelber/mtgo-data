"""P3-08 end-to-end regression and cross-format isolation closeout."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from generate_classification_reports import generate_reports
from mtgmeta.mtgo import __main__ as cli
from mtgmeta.mtgo import matchup, pickup, stats


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DATE = date(2026, 7, 19)
STATISTICS_GENERATED = "2026-07-19T21:00:04"
MATCHUPS_GENERATED = "2026-07-19T21:00:07"
METADATA_DATA_UPDATED = "2026-07-19T21:00:08+00:00"
METADATA_RULES_UPDATED = "2026-07-20T05:34:31+09:00"
NONSTANDARD_FORMATS = ("pauper", "modern", "pioneer", "legacy", "vintage")


def assert_byte_identical(generated: Path, committed: Path) -> None:
    assert generated.read_bytes() == committed.read_bytes(), committed.relative_to(ROOT)


@pytest.mark.committed_baseline
def test_fixed_reference_standard_product_is_byte_identical(tmp_path):
    generated_stats = tmp_path / "stats"
    generated_pickup = tmp_path / "pickup"
    generated_reports = tmp_path / "reports"
    committed_stats = ROOT / "stats" / "standard" / "mtgo"
    committed_pickup = committed_stats / "pickup"
    committed_reports = ROOT / "reports" / "standard" / "mtgo"

    statistics = stats.build_all_stats(
        ROOT,
        "standard",
        today=REFERENCE_DATE,
        generated_at=STATISTICS_GENERATED,
        output_directory=generated_stats,
    )
    matchups, matchup_counts = matchup.build_all_matchups(
        ROOT,
        "standard",
        today=REFERENCE_DATE,
        generated_at=MATCHUPS_GENERATED,
        output_directory=generated_stats,
    )
    candidates = pickup.generate_candidates(
        ROOT,
        "standard",
        today=REFERENCE_DATE,
        output_directory=generated_pickup,
        known_file=committed_pickup / "known_archetypes.json",
    )
    metadata = pickup.generate_metadata(
        ROOT,
        "standard",
        data_updated=METADATA_DATA_UPDATED,
        rules_updated=METADATA_RULES_UPDATED,
        output_directory=generated_stats,
    )
    reports = generate_reports(ROOT, "standard", output_directory=generated_reports)

    assert set(statistics) == {
        "index.json",
        "range_1w.json",
        "range_4w.json",
        "range_12w.json",
        "range_36w.json",
        "decks_1w.json",
        "decks_4w.json",
        "decks_12w.json",
        "decks_36w.json",
    }
    assert set(matchups) == {
        "matchup_index.json",
        "matchup_1w.json",
        "matchup_4w.json",
        "matchup_12w.json",
        "matchup_36w.json",
    }
    assert {weeks: values["counted"] for weeks, values in matchup_counts.items()} == {
        1: 619,
        4: 2564,
        12: 6732,
        36: 8247,
    }
    assert candidates is not None
    assert candidates["week"] == "2026-W28"
    assert reports["index"]["summary"] == {
        "total_decks": 3936,
        "classified": 3865,
        "unknown": 71,
        "multiple_matches": 947,
        "overridden_matches": 947,
        "conflicts": 0,
        "invalid_decks": 0,
        "selected_subtypes": 45,
        "same_parent_multiple_subtype_matches": 21,
        "strict_validation": "pass",
    }

    for name in statistics | matchups:
        assert_byte_identical(generated_stats / name, committed_stats / name)
    assert_byte_identical(metadata, committed_stats / "meta.json")
    assert_byte_identical(candidates["candidate_path"], committed_pickup / candidates["candidate_path"].name)
    assert_byte_identical(
        candidates["base_reference_path"],
        committed_pickup / candidates["base_reference_path"].name,
    )
    for generated in sorted(generated_reports.glob("*.json")):
        assert_byte_identical(generated, committed_reports / generated.name)
    assert len(list(generated_reports.glob("*.json"))) == 6


def test_all_nonstandard_product_commands_fail_before_dispatch_or_output(
    tmp_path, monkeypatch, capsys
):
    registry = tmp_path / "configs" / "formats.yaml"
    registry.parent.mkdir(parents=True)
    registry.write_bytes((ROOT / "configs" / "formats.yaml").read_bytes())
    dispatched = []

    def record_dispatch(args, root, registry_path):
        dispatched.append((args.format_id, args.command, root, registry_path))
        return 0

    for command in cli.RUNNERS:
        monkeypatch.setitem(cli.RUNNERS, command, record_dispatch)

    product_commands = (
        ["fetch-matches"],
        ["build-statistics"],
        ["build-matchups"],
        ["pickup", "candidates"],
        ["pickup", "publish"],
        ["generate-metadata"],
        ["classification-reports"],
    )
    for format_id in NONSTANDARD_FORMATS:
        for command in product_commands:
            assert cli.main(
                ["--root", str(tmp_path), "--format", format_id, *command]
            ) == 2
    assert dispatched == []
    assert sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*")) == [
        "configs",
        "configs/formats.yaml",
    ]
    assert capsys.readouterr().err.count("MTGO command ERROR") == (
        len(NONSTANDARD_FORMATS) * len(product_commands)
    )

    for format_id in ("standard", *NONSTANDARD_FORMATS):
        assert cli.main(
            ["--root", str(tmp_path), "--format", format_id, "fetch-events"]
        ) == 0
    assert [(format_id, command) for format_id, command, _, _ in dispatched] == [
        (format_id, "fetch-events") for format_id in ("standard", *NONSTANDARD_FORMATS)
    ]
