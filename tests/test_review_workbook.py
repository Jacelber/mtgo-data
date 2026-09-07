import json
from pathlib import Path
import re
from xml.sax.saxutils import escape
import zipfile

import pytest

from mtgmeta.review_workbook import (
    ReviewWorkbookError,
    read_workbook_rows,
    semantic_diff,
)
from tools.review_workbook_intake import main as intake_main


def _write_workbook(
    path: Path,
    *,
    shared: list[str],
    cells: list[tuple[str, str | None, str | None]],
) -> None:
    shared_xml = "".join(f"<si><t>{escape(value)}</t></si>" for value in shared)
    rows: dict[int, list[str]] = {}
    for reference, cell_type, value in cells:
        type_attribute = f' t="{cell_type}"' if cell_type is not None else ""
        body = "" if value is None else f"<v>{escape(value)}</v>"
        row_number = int(re.search(r"[0-9]+$", reference).group())
        rows.setdefault(row_number, []).append(
            f'<c r="{reference}"{type_attribute}>{body}</c>'
        )
    row_xml = "".join(
        f'<row r="{row_number}">{"".join(row_cells)}</row>'
        for row_number, row_cells in sorted(rows.items())
    )
    worksheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{row_xml}</sheetData>"
        "</worksheet>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "xl/sharedStrings.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"{shared_xml}</sst>",
        )
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Review" sheetId="1" r:id="rId1"/></sheets>'
            "</workbook>",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/>'
            "</Relationships>",
        )
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)


def test_shared_strings_resolve_by_content_while_real_numbers_keep_their_type(tmp_path):
    workbook = tmp_path / "review.xlsx"
    shared = ["Owner Decision", *[f"filler-{index}" for index in range(37)]]
    empty_index = len(shared)
    shared.append("")
    numeric_text_index = len(shared)
    shared.append("731")
    decision_index = len(shared)
    shared.append("保留")
    _write_workbook(
        workbook,
        shared=shared,
        cells=[
            ("A1", "s", "0"),
            ("A2", "s", str(empty_index)),
            ("B2", None, "731"),
            ("C2", "s", str(numeric_text_index)),
            ("D2", "s", str(decision_index)),
        ],
    )

    rows = read_workbook_rows(workbook)["Review"]

    assert rows[1] == [None, 731, "731", "保留"]


def test_semantic_diff_ignores_changed_storage_indexes_for_the_same_blank(tmp_path):
    baseline_path = tmp_path / "baseline.xlsx"
    returned_path = tmp_path / "returned.xlsx"
    baseline_shared = ["Header", "", "Before"]
    returned_shared = ["unused", "Header", "Before", "", "After"]
    _write_workbook(
        baseline_path,
        shared=baseline_shared,
        cells=[
            ("A1", "s", str(baseline_shared.index("Header"))),
            ("A2", "s", str(baseline_shared.index(""))),
            ("B2", None, "1"),
            ("C2", "s", str(baseline_shared.index("Before"))),
        ],
    )
    _write_workbook(
        returned_path,
        shared=returned_shared,
        cells=[
            ("A1", "s", str(returned_shared.index("Header"))),
            ("A2", "s", str(returned_shared.index(""))),
            ("B2", None, "2"),
            ("C2", "s", str(returned_shared.index("After"))),
        ],
    )

    changes = semantic_diff(
        read_workbook_rows(baseline_path),
        read_workbook_rows(returned_path),
    )

    assert changes == [
        {"sheet": "Review", "cell": "B2", "before": 1, "after": 2},
        {"sheet": "Review", "cell": "C2", "before": "Before", "after": "After"},
    ]


@pytest.mark.parametrize("raw_index", ["-1", "1", "not-an-index"])
def test_invalid_shared_string_indexes_fail_closed(tmp_path, raw_index):
    workbook = tmp_path / "invalid.xlsx"
    _write_workbook(
        workbook,
        shared=["only value"],
        cells=[("A1", "s", raw_index)],
    )

    with pytest.raises(ReviewWorkbookError, match="invalid shared-string index"):
        read_workbook_rows(workbook)


def test_intake_command_writes_authoritative_semantic_diff(tmp_path):
    baseline_path = tmp_path / "baseline.xlsx"
    returned_path = tmp_path / "returned.xlsx"
    output_path = tmp_path / "diff.json"
    _write_workbook(
        baseline_path,
        shared=["", "pending"],
        cells=[("A1", "s", "0"), ("B1", "s", "1")],
    )
    _write_workbook(
        returned_path,
        shared=["accepted", ""],
        cells=[("A1", "s", "1"), ("B1", "s", "0")],
    )

    assert (
        intake_main(
            [
                "diff",
                "--baseline",
                str(baseline_path),
                "--workbook",
                str(returned_path),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["document_type"] == "owner_review_workbook_semantic_diff"
    assert result["changes"] == [
        {"sheet": "Review", "cell": "B1", "before": "pending", "after": "accepted"}
    ]


def test_snapshot_stdout_is_ascii_safe_and_round_trips_unicode(tmp_path, capsys):
    workbook = tmp_path / "review.xlsx"
    _write_workbook(
        workbook,
        shared=["保留"],
        cells=[("A1", "s", "0")],
    )

    assert intake_main(["snapshot", "--workbook", str(workbook)]) == 0

    output = capsys.readouterr().out
    assert output.isascii()
    assert json.loads(output)["sheets"]["Review"] == [["保留"]]
