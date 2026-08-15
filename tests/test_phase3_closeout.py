"""P3-08 cross-format capability isolation contract."""

from __future__ import annotations

from pathlib import Path

from mtgmeta.mtgo import __main__ as cli


ROOT = Path(__file__).resolve().parents[1]
NONSTANDARD_FORMATS = ("pauper", "modern", "pioneer", "legacy", "vintage")


def test_nonstandard_product_commands_obey_current_capabilities_before_dispatch(
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
        ["generate-hierarchy"],
        ["classification-reports"],
    )
    for format_id in NONSTANDARD_FORMATS:
        for command in product_commands:
            enabled_modern_commands = (
                ["fetch-matches"],
                ["build-statistics"],
                ["build-matchups"],
                ["pickup", "candidates"],
                ["pickup", "publish"],
                ["generate-metadata"],
                ["generate-hierarchy"],
                ["classification-reports"],
            )
            expected = (
                0
                if format_id == "modern" and command in enabled_modern_commands
                else 2
            )
            assert cli.main(
                ["--root", str(tmp_path), "--format", format_id, *command]
            ) == expected
    assert [(format_id, command) for format_id, command, _, _ in dispatched] == [
        ("modern", "fetch-matches"),
        ("modern", "build-statistics"),
        ("modern", "build-matchups"),
        ("modern", "pickup"),
        ("modern", "pickup"),
        ("modern", "generate-metadata"),
        ("modern", "generate-hierarchy"),
        ("modern", "classification-reports"),
    ]
    assert sorted(
        path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*")
    ) == [
        "configs",
        "configs/formats.yaml",
    ]
    assert capsys.readouterr().err.count("MTGO command ERROR") == (
        len(NONSTANDARD_FORMATS) * len(product_commands) - 8
    )

    for format_id in ("standard", *NONSTANDARD_FORMATS):
        assert cli.main(
            ["--root", str(tmp_path), "--format", format_id, "fetch-events"]
        ) == 0
    assert [(format_id, command) for format_id, command, _, _ in dispatched] == [
        ("modern", "fetch-matches"),
        ("modern", "build-statistics"),
        ("modern", "build-matchups"),
        ("modern", "pickup"),
        ("modern", "pickup"),
        ("modern", "generate-metadata"),
        ("modern", "generate-hierarchy"),
        ("modern", "classification-reports"),
    ] + [
        (format_id, "fetch-events")
        for format_id in ("standard", *NONSTANDARD_FORMATS)
    ]
