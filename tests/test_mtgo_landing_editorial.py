import json
from pathlib import Path
from xml.sax.saxutils import escape
import zipfile

import pytest
import yaml

from mtgmeta.mtgo import landing_editorial as editorial


ROOT = Path(__file__).resolve().parents[1]


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


def _sheets(scope=None, *, all_top8_rows=()):
    control_rows = [] if scope is None else [[scope[0], scope[1], "PENDING", "PENDING"]]
    return {
        "Review Control": (
            ["Format", "Week", "Top Copy Review", "Feature Review"],
            control_rows,
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
            list(all_top8_rows),
        ),
        "Bilingual Names": (["Review Result"], []),
    }


def _current_scope():
    document = json.loads(
        (ROOT / "stats/standard/mtgo/landing/current.json").read_text(
            encoding="utf-8"
        )
    )
    return "standard", document["week"]["id"]


@pytest.fixture(scope="module")
def review_workbook(tmp_path_factory):
    path = tmp_path_factory.mktemp("landing-editorial-workbook") / "review.xlsx"
    scope = _current_scope()
    _write_workbook(path, _sheets(scope))
    return path, scope, editorial.file_sha256(path)


@pytest.fixture(scope="module")
def imported(tmp_path_factory, review_workbook):
    workbook, scope, digest = review_workbook
    output_root = tmp_path_factory.mktemp("landing-editorial-import")
    result = editorial.import_review_workbook(
        ROOT,
        workbook,
        output_root=output_root,
        expected_sha256=digest,
    )
    return output_root, result, scope, workbook, digest


def test_raw_xlsx_reader_preserves_true_blank_cells(tmp_path):
    workbook = tmp_path / "blank-cells.xlsx"
    row = [
        "standard",
        "2099-W02",
        "deck:0123456789abcdefabcd",
        "Event 1",
        "2099-01-05",
        1,
        "Deck",
        "Player",
        None,
        None,
    ]
    _write_workbook(workbook, _sheets(all_top8_rows=[row]))

    first_top8 = editorial.read_review_workbook(workbook)["All Top 8"][0]

    assert first_top8["Add to Featured?"] is None
    assert first_top8["Owner Note"] is None
    assert first_top8["Rank"] == 1


def test_single_week_copy_uses_content_instead_of_repeated_control_approval():
    scope = ("standard", "2099-W02")
    scopes = editorial._control_scopes(
        [{"Format": scope[0], "Week": scope[1], "Top Copy Review": "PENDING"}]
    )
    rows = [
        {
            "Review Result": "KEEP",
            "Order": 1,
            "Format": scope[0],
            "Chinese Copy": "已完成的中文内容",
            "English Final": None,
        }
    ]

    assert editorial._copy_rows_by_scope(scopes, rows, stage="chinese")[scope][0][
        "text"
    ] == {"zh": "已完成的中文内容", "en": "已完成的中文内容"}
    with pytest.raises(editorial.MTGOLandingEditorialError, match="English final"):
        editorial._copy_rows_by_scope(scopes, rows, stage="bilingual")


def test_synthetic_workbook_imports_one_private_subject(imported):
    output_root, result, (format_id, week), _workbook, digest = imported

    assert result["workbook_sha256"] == digest
    assert result["name_count"] > 0
    assert result["review_count"] == 1
    assert result["feature_count"] == 0
    assert result["copy_count"] == 0
    review = editorial.load_review_document(
        output_root / f"stats/{format_id}/mtgo/landing/review/{week}.yaml"
    )
    assert review["bindings"]["workbook_sha256"] == digest
    assert review["review"]["features"] == {
        "reviewed": True,
        "explicit_empty": True,
        "items": [],
    }


def test_review_binding_changes_fail_closed(imported):
    _output_root, result, _scope, _workbook, _digest = imported
    review = editorial.load_review_document(result["review_paths"][0])
    current = dict(review["bindings"])
    editorial.validate_review_binding(review, current)

    for field, message in (
        ("classifier_digest", "classifier"),
        ("machine_fact_digest", "machine fact"),
    ):
        stale = dict(current)
        stale[field] = "0" * 64
        with pytest.raises(editorial.MTGOLandingEditorialError, match=message):
            editorial.validate_review_binding(review, stale)


def test_top_copy_token_without_feature_fails_closed(imported):
    _output_root, result, _scope, _workbook, _digest = imported
    review = editorial.load_review_document(result["review_paths"][0])
    token = review["all_top8"][0]["token"]
    review["review"]["top_copy"]["items"] = [
        {"order": 1, "text": {"zh": f"关注 {token}", "en": f"Watch {token}"}}
    ]

    with pytest.raises(editorial.MTGOLandingEditorialError, match="lacks an exact"):
        editorial.validate_review_document(
            review,
            ROOT / "schemas/mtgo-landing-review.schema.json",
        )


def test_bilingual_catalog_coverage_fails_closed(imported, tmp_path):
    output_root, _result, _scope, _workbook, _digest = imported
    catalog = yaml.safe_load(
        (output_root / "configs/mtgo_archetype_names.yaml").read_text(encoding="utf-8")
    )
    catalog["names"].pop()
    path = tmp_path / "incomplete.yaml"
    path.write_text(yaml.safe_dump(catalog, allow_unicode=True), encoding="utf-8")

    with pytest.raises(editorial.MTGOLandingEditorialError, match="coverage"):
        editorial.validate_name_catalog(ROOT, path)


def test_explicit_empty_review_advances_landing_known_state(imported):
    _output_root, result, (_format_id, week), _workbook, _digest = imported
    review = editorial.load_review_document(result["review_paths"][0])
    known = json.loads(result["known_paths"][0].read_text(encoding="utf-8"))

    assert review["review"]["features"]["explicit_empty"] is True
    assert review["known_archetype_ids"]
    assert set(review["known_archetype_ids"]) <= set(known["known_ids"])
    assert known["accepted_through_week"] >= week


def test_import_is_deterministic_for_same_workbook_subject(imported):
    output_root, result, _scope, workbook, digest = imported
    paths = [result["catalog_path"], *result["review_paths"], *result["known_paths"]]
    before = {
        str(path.relative_to(output_root)): editorial.file_sha256(path) for path in paths
    }

    repeated = editorial.import_review_workbook(
        ROOT,
        workbook,
        output_root=output_root,
        expected_sha256=digest,
    )
    repeated_paths = [
        repeated["catalog_path"],
        *repeated["review_paths"],
        *repeated["known_paths"],
    ]
    after = {
        str(path.relative_to(output_root)): editorial.file_sha256(path)
        for path in repeated_paths
    }

    assert after == before


def test_import_rejects_a_different_workbook_hash(imported, tmp_path):
    _output_root, _result, _scope, workbook, _digest = imported
    with pytest.raises(editorial.MTGOLandingEditorialError, match="SHA-256 changed"):
        editorial.import_review_workbook(
            ROOT,
            workbook,
            output_root=tmp_path,
            expected_sha256="0" * 64,
        )
