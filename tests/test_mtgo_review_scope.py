from __future__ import annotations

import json
import shutil
import zipfile
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import pytest
import yaml

from mtgmeta.mtgo import landing, landing_editorial as editorial
from mtgmeta.weekly_review import build_v2_completion_record
from mtgmeta.mtgo.review_scope import MTGOReviewScopeError, parse_review_scopes
from validate_schemas import validate_manifest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _registry(root: Path) -> Path:
    formats = []
    for format_id, public in (("standard", True), ("modern", True), ("pauper", False)):
        formats.append({
            "id": format_id,
            "display_name": format_id.title(),
            "state": "executable",
            "public": public,
            "mtgo": {
                "enabled": True,
                "event_collection_enabled": False,
                "capabilities": [
                    "classification",
                    "event_statistics",
                    "landing_generation",
                ],
                "paths": {
                    "events": f"data/{format_id}",
                    "matches": f"data/{format_id}/mtgo/matches",
                    "rules": f"my_archetypes/{format_id}.yaml",
                    "statistics": f"stats/{format_id}/mtgo",
                    "reports": f"reports/{format_id}/mtgo",
                },
            },
        })
    path = root / "configs/formats.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"schema_version": "1.3.0", "formats": formats}), encoding="utf-8")
    return path


def _write_yaml(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True), encoding="utf-8")


def _column_name(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(ord("A") + remainder) + result
    return result


def _worksheet_xml(headers, rows) -> str:
    def cell(reference, value):
        if value is None:
            return f'<c r="{reference}"/>'
        if isinstance(value, int) and not isinstance(value, bool):
            return f'<c r="{reference}"><v>{value}</v></c>'
        return (
            f'<c r="{reference}" t="inlineStr"><is><t>'
            f"{escape(str(value))}</t></is></c>"
        )

    xml_rows = ['<row r="1"/>', '<row r="2"/>', '<row r="3"/>']
    for row_number, values in enumerate([headers, *rows], start=4):
        cells = "".join(
            cell(f"{_column_name(index)}{row_number}", value)
            for index, value in enumerate(values, start=1)
        )
        xml_rows.append(f'<row r="{row_number}">{cells}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(xml_rows)}</sheetData></worksheet>"
    )


def _write_workbook(path: Path, sheets) -> None:
    workbook_sheets = []
    relationships = []
    with zipfile.ZipFile(path, "w") as archive:
        for index, name in enumerate(editorial.WORKBOOK_SHEETS, start=1):
            headers, rows = sheets[name]
            workbook_sheets.append(
                f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
            )
            relationships.append(
                f'<Relationship Id="rId{index}" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                f'Target="worksheets/sheet{index}.xml"/>'
            )
            archive.writestr(
                f"xl/worksheets/sheet{index}.xml",
                _worksheet_xml(headers, rows),
            )
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f"<sheets>{''.join(workbook_sheets)}</sheets></workbook>",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f"{''.join(relationships)}</Relationships>",
        )


def _synthetic_landing_repository(root: Path) -> tuple[Path, Path, str]:
    registry = _registry(root)
    shutil.copytree(REPOSITORY_ROOT / "schemas", root / "schemas")
    _write_yaml(
        root / "my_archetypes/pauper.yaml",
        {
            "schema_version": "1.0.0",
            "format": "pauper",
            "archetypes": [
                {
                    "id": "alpha",
                    "name": "Alpha",
                    "priority": 100,
                    "rules": [
                        {
                            "id": "alpha-rule",
                            "priority": 100,
                            "conditions": {
                                "all": [{"card": "Signal Card", "zone": "main"}]
                            },
                        }
                    ],
                }
            ],
        },
    )
    event = {
        "event_id": "100",
        "format": "CPAUPER",
        "description": "Synthetic Challenge",
        "starttime": "2025-01-13T12:00:00Z",
        "player_count": 8,
        "players": [
            {
                "player": f"Player {rank}",
                "loginid": str(rank),
                "final_rank": rank,
                "swiss_score": 9,
                "main_deck": [{"name": "Signal Card", "qty": 60}],
                "sideboard": [{"name": "Side Card", "qty": 15}],
            }
            for rank in range(1, 9)
        ],
    }
    event_path = root / "data/pauper/100.json"
    event_path.parent.mkdir(parents=True)
    event_path.write_text(json.dumps(event), encoding="utf-8")
    _write_yaml(
        root / "configs/mtgo_pickup_policy.yaml",
        {
            "schema_version": "1.0",
            "thresholds": {
                "share_increase_pp": 5,
                "return_share": 0.03,
                "build_shift": 20,
                "build_reference_minimum": 8,
                "new_card_review_weeks": 2,
            },
            "identity_continuity": {"pauper": {}},
            "release_sets": [],
        },
    )
    name_path = root / "configs/mtgo_archetype_names.yaml"
    _write_yaml(
        name_path,
        {
            "schema_version": "1.0.0",
            "names": [
                {
                    "format": "pauper",
                    "parent_id": "alpha",
                    "subtype_id": None,
                    "english": "Alpha",
                    "chinese": "阿尔法",
                    "review_status": "approved",
                    "identity_key": "pauper|alpha|none",
                }
            ],
        },
    )
    visuals_path = root / "configs/mtgo_landing_visuals.yaml"
    _write_yaml(
        visuals_path,
        {
            "schema_version": "1.0",
            "formats": {
                "pauper": {
                    "parents": {"alpha": ["Signal Card", "Side Card"]},
                    "subtypes": {},
                    "allow_parent_fallback_for_subtypes": [],
                }
            },
        },
    )
    return registry, visuals_path, "2025-W03"


def test_private_review_scope_preserves_order_and_independent_weeks(tmp_path):
    registry = _registry(tmp_path)

    scopes = parse_review_scopes(
        tmp_path,
        ["pauper=2026-W32"],
        capability="landing_generation",
        registry_path=registry,
        private=True,
        today=date(2026, 9, 5),
    )

    assert [(scope.format_id, scope.week) for scope in scopes] == [("pauper", "2026-W32")]

    public = parse_review_scopes(
        tmp_path,
        ["modern=2026-W31", "standard=2026-W32"],
        capability="landing_generation",
        registry_path=registry,
        private=False,
        today=date(2026, 9, 5),
    )
    assert [(scope.format_id, scope.week) for scope in public] == [
        ("modern", "2026-W31"),
        ("standard", "2026-W32"),
    ]


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ([], "must not be empty"),
        (["pauper=2026-W32", "pauper=2026-W31"], "duplicates format"),
        (["pauper=2026-W54"], "invalid ISO"),
        (["pauper=2026-W36"], "has not ended"),
        (["missing=2026-W32"], "unknown format"),
    ],
)
def test_private_review_scope_rejects_invalid_subjects(tmp_path, values, message):
    registry = _registry(tmp_path)
    with pytest.raises(MTGOReviewScopeError, match=message):
        parse_review_scopes(
            tmp_path,
            values,
            capability="landing_generation",
            registry_path=registry,
            private=True,
            today=date(2026, 9, 5),
        )


def test_public_and_private_boundaries_are_explicit(tmp_path):
    registry = _registry(tmp_path)
    with pytest.raises(MTGOReviewScopeError, match="public: false"):
        parse_review_scopes(
            tmp_path, ["standard=2026-W32"], capability="landing_generation",
            registry_path=registry, private=True, today=date(2026, 9, 5)
        )
    with pytest.raises(MTGOReviewScopeError, match="cannot include private"):
        parse_review_scopes(
            tmp_path, ["pauper=2026-W32"], capability="landing_generation",
            registry_path=registry, private=False, today=date(2026, 9, 5)
        )


def test_single_format_completion_binds_exact_week_and_rejects_duplicates():
    digest = "a" * 64
    review = {
        "format": "pauper",
        "week": "2026-W32",
        "event_ids": ["1"],
        "classifier": {"subject_digest": digest},
        "classification_review_digest": digest,
    }
    record = build_v2_completion_record(
        [review],
        week_id="2026-W32",
        completed_on="2026-09-01",
        evidence="owner acceptance",
        landing_content_digests={"pauper": digest},
        independent_format=True,
    )
    assert list(record["formats"]) == ["pauper"]
    with pytest.raises(ValueError, match="duplicate format"):
        build_v2_completion_record(
            [review, review], week_id="2026-W32", completed_on="2026-09-01",
            evidence="owner acceptance", landing_content_digests={"pauper": digest},
            independent_format=True,
        )
    with pytest.raises(ValueError, match="week does not match"):
        build_v2_completion_record(
            [review], week_id="2026-W31", completed_on="2026-09-01",
            evidence="owner acceptance", landing_content_digests={"pauper": digest},
            independent_format=True,
        )


def test_generic_name_mapping_keeps_registry_and_path_identity(tmp_path):
    registry = _registry(tmp_path)
    assert registry.is_file()
    output = tmp_path / "stats/pauper/archetype_names.json"
    output.parent.mkdir(parents=True)
    digest = "b" * 64
    output.write_text(json.dumps({
        "schema_version": "1.1.0",
        "format": "pauper",
        "provenance": {
            "classifier_identity_digest": digest,
            "name_catalog_digest": digest,
            "projection_subject_digest": digest,
        },
        "names": [{
            "identity_id": "test-deck",
            "parent_id": "test-deck",
            "subtype_id": None,
            "display": {"en": "Test Deck", "zh": "Test Deck ZH"},
        }],
    }), encoding="utf-8")
    checked, failures = validate_manifest(
        tmp_path,
        REPOSITORY_ROOT / "schemas/manifest.json",
        {"stats/pauper/archetype_names.json"},
    )
    assert checked == 1
    assert failures == []

    document = json.loads(output.read_text(encoding="utf-8"))
    document["format"] = "modern"
    output.write_text(json.dumps(document), encoding="utf-8")
    _checked, failures = validate_manifest(
        tmp_path,
        REPOSITORY_ROOT / "schemas/manifest.json",
        {"stats/pauper/archetype_names.json"},
    )
    assert any("registered output path" in failure.message for failure in failures)


def test_landing_binding_digests_ignore_unrelated_third_format_rows():
    standard_name = {
        "format": "standard",
        "parent_id": "alpha",
        "subtype_id": None,
        "english": "Alpha",
        "chinese": "甲",
        "review_status": "approved",
        "identity_key": "standard|alpha|none",
    }
    modern_name = {
        **standard_name,
        "format": "modern",
        "identity_key": "modern|alpha|none",
    }
    pauper_name = {
        **standard_name,
        "format": "pauper",
        "identity_key": "pauper|alpha|none",
    }
    historical_names = {
        "schema_version": "1.0.0",
        "names": [standard_name, modern_name],
    }
    expanded_names = {
        "schema_version": "1.0.0",
        "names": [standard_name, modern_name, pauper_name],
    }

    historical_digest = editorial.name_catalog_binding_digest(
        historical_names, review_schema_version="1.0.0", format_id="standard"
    )
    assert editorial.name_catalog_binding_digest(
        expanded_names, review_schema_version="1.0.0", format_id="standard"
    ) == historical_digest
    changed_historical = json.loads(json.dumps(expanded_names))
    changed_historical["names"][0]["chinese"] = "已修改"
    assert editorial.name_catalog_binding_digest(
        changed_historical, review_schema_version="1.0.0", format_id="standard"
    ) != historical_digest
    review = {"bindings": {"bilingual_catalog_digest": historical_digest}}
    with pytest.raises(editorial.MTGOLandingEditorialError, match="bilingual catalog"):
        editorial.validate_review_binding(
            review,
            {
                "bilingual_catalog_digest": editorial.name_catalog_binding_digest(
                    changed_historical,
                    review_schema_version="1.0.0",
                    format_id="standard",
                )
            },
        )

    private_digest = editorial.name_catalog_binding_digest(
        expanded_names, review_schema_version="1.1.0", format_id="pauper"
    )
    unrelated_name_change = json.loads(json.dumps(expanded_names))
    unrelated_name_change["names"][0]["chinese"] = "无关修改"
    assert editorial.name_catalog_binding_digest(
        unrelated_name_change, review_schema_version="1.1.0", format_id="pauper"
    ) == private_digest

    standard_visual = {
        "parents": {"alpha": ["A", "B"]},
        "subtypes": {},
        "allow_parent_fallback_for_subtypes": [],
    }
    modern_visual = {
        "parents": {"alpha": ["C", "D"]},
        "subtypes": {},
        "allow_parent_fallback_for_subtypes": [],
    }
    pauper_visual = {
        "parents": {"alpha": ["E", "F"]},
        "subtypes": {},
        "allow_parent_fallback_for_subtypes": [],
    }
    historical_visuals = {
        "schema_version": "1.0",
        "formats": {"standard": standard_visual, "modern": modern_visual},
    }
    expanded_visuals = {
        "schema_version": "1.0",
        "formats": {
            "standard": standard_visual,
            "modern": modern_visual,
            "pauper": pauper_visual,
        },
    }
    public_visual_digest = landing.visual_metadata_binding_digest(
        historical_visuals,
        landing_schema_version=landing.LANDING_SCHEMA_VERSION,
        format_id="standard",
    )
    assert landing.visual_metadata_binding_digest(
        expanded_visuals,
        landing_schema_version=landing.LANDING_SCHEMA_VERSION,
        format_id="standard",
    ) == public_visual_digest
    changed_visuals = json.loads(json.dumps(expanded_visuals))
    changed_visuals["formats"]["standard"]["parents"]["alpha"][0] = "Changed"
    assert landing.visual_metadata_binding_digest(
        changed_visuals,
        landing_schema_version=landing.LANDING_SCHEMA_VERSION,
        format_id="standard",
    ) != public_visual_digest

    private_visual_digest = landing.visual_metadata_binding_digest(
        expanded_visuals,
        landing_schema_version=landing.PRIVATE_LANDING_SCHEMA_VERSION,
        format_id="pauper",
    )
    assert landing.visual_metadata_binding_digest(
        changed_visuals,
        landing_schema_version=landing.PRIVATE_LANDING_SCHEMA_VERSION,
        format_id="pauper",
    ) == private_visual_digest


def test_five_sheet_workbook_imports_without_names_and_generates_private_landing(
    tmp_path,
):
    repository = tmp_path / "repository"
    registry, visuals_path, week = _synthetic_landing_repository(repository)
    subject = editorial.build_top8_subject(repository, "pauper", week)
    assert subject["source_event_ids"] == ["100"]
    assert len(subject["all_top8"]) == 8
    top8_rows = [
        [
            "pauper",
            week,
            item["token"],
            item["event_id"],
            item["date"],
            item["final_rank"],
            item["display_name"],
            item["player"],
            None,
            None,
        ]
        for item in subject["all_top8"]
    ]
    workbook = tmp_path / "review.xlsx"
    _write_workbook(
        workbook,
        {
            "Review Control": (
                ["Format", "Week", "Top Copy Review", "Feature Review"],
                [["pauper", week, "PENDING", "PENDING"]],
            ),
            "Landing Copy": (
                ["Review Result", "Order", "Format", "Chinese Copy", "English Final"],
                [],
            ),
            "Featured Decks": (["Selection"], []),
            "All Top 8": (
                [
                    "Format",
                    "Week",
                    "Deck Link ID",
                    "Event",
                    "Date",
                    "Rank",
                    "Deck",
                    "Player",
                    "Add to Featured?",
                    "Owner Note",
                ],
                top8_rows,
            ),
            "Field Guide": (
                ["Field", "Meaning"],
                [["Deck Link ID", "Generated exact-deck reference; not a name row."]],
            ),
        },
    )
    workbook_digest = editorial.file_sha256(workbook)
    name_path = repository / "configs/mtgo_archetype_names.yaml"
    authority_bytes = name_path.read_bytes()

    validation = editorial.validate_review_workbook(
        repository,
        workbook,
        stage="bilingual",
        expected_sha256=workbook_digest,
        formats={"pauper"},
    )
    assert validation == {
        "workbook_sha256": workbook_digest,
        "name_count": 1,
        "review_count": 1,
        "feature_count": 0,
        "copy_count": 0,
        "stage": "bilingual",
    }

    in_place = editorial.import_review_workbook(
        repository,
        workbook,
        expected_sha256=workbook_digest,
        formats={"pauper"},
    )
    assert name_path.read_bytes() == authority_bytes
    assert in_place["catalog_path"] == name_path

    imported_root = tmp_path / "imported"
    imported = editorial.import_review_workbook(
        repository,
        workbook,
        output_root=imported_root,
        expected_sha256=workbook_digest,
        formats={"pauper"},
    )
    imported_names = imported_root / "configs/mtgo_archetype_names.yaml"
    assert imported_names.read_bytes() == authority_bytes
    review = editorial.load_review_document(imported["review_paths"][0])
    assert review["schema_version"] == "1.1.0"
    assert review["format"] == "pauper"
    assert review["week"]["id"] == week

    output_root = tmp_path / "result"
    landing_output = output_root / "stats/pauper/mtgo/landing"
    result = landing.generate(
        repository,
        "pauper",
        today=date(2025, 1, 27),
        registry_path=registry,
        review_directory=imported_root / "stats/pauper/mtgo/landing/review",
        name_catalog_path=imported_names,
        output_directory=landing_output,
        visuals_path=visuals_path,
        private=True,
        review_week=week,
    )
    assert result == {
        "status": "written",
        "path": landing_output / "current.json",
        "week": week,
        "feature_count": 0,
        "summary_count": 0,
        "archive_week_count": 1,
    }
    current = json.loads((landing_output / "current.json").read_text(encoding="utf-8"))
    feature_week = json.loads(
        (landing_output / f"features/{week}.json").read_text(encoding="utf-8")
    )
    feature_index = json.loads(
        (landing_output / "features/index.json").read_text(encoding="utf-8")
    )
    assert current["schema_version"] == "1.3.0"
    assert (
        current["format"]
        == feature_week["format"]
        == feature_index["format"]
        == "pauper"
    )
    assert current["week"]["id"] == feature_week["week"]["id"] == week
    assert current["features"] == {"week": week, "items": []}
    assert feature_week["features"] == {"items": []}
    assert feature_index["weeks"] == [
        {
            "week": week,
            "file": f"{week}.json",
            "start": "2025-01-13",
            "end": "2025-01-19",
            "feature_count": 0,
        }
    ]

    paths = {
        "stats/pauper/mtgo/landing/current.json",
        "stats/pauper/mtgo/landing/features/index.json",
        f"stats/pauper/mtgo/landing/features/{week}.json",
    }
    output_registry = output_root / "configs/formats.yaml"
    output_registry.parent.mkdir(parents=True)
    shutil.copyfile(registry, output_registry)
    checked, failures = validate_manifest(
        output_root,
        REPOSITORY_ROOT / "schemas/manifest.json",
        paths,
    )
    assert checked == 3
    assert failures == []
