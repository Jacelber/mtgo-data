"""Read Owner review workbooks with authoritative raw OOXML semantics."""

from __future__ import annotations

import math
import posixpath
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


_OOXML_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_OOXML_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PACKAGE_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_CELL_REFERENCE = re.compile(r"^([A-Za-z]+)([1-9][0-9]*)$")
_UNSIGNED_INTEGER = re.compile(r"^(0|[1-9][0-9]*)$")


class ReviewWorkbookError(ValueError):
    """Raised when an XLSX review carrier cannot be interpreted safely."""


def _column_index(reference: str) -> int:
    match = _CELL_REFERENCE.fullmatch(reference)
    if match is None:
        raise ReviewWorkbookError(f"invalid cell reference {reference!r}")
    result = 0
    for character in match.group(1):
        result = result * 26 + ord(character.upper()) - ord("A") + 1
    return result - 1


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    namespace = {"x": _OOXML_MAIN}
    return [
        "".join(node.text or "" for node in item.findall(".//x:t", namespace))
        for item in root.findall("x:si", namespace)
    ]


def _sheet_targets(archive: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    relation_targets: dict[str, str] = {}
    for relation in relationships.findall(f"{{{_PACKAGE_REL}}}Relationship"):
        relation_id = relation.attrib["Id"]
        if relation_id in relation_targets:
            raise ReviewWorkbookError(
                f"duplicate workbook relationship {relation_id!r}"
            )
        if relation.attrib.get("TargetMode") == "External":
            raise ReviewWorkbookError(
                f"external workbook relationship {relation_id!r} is not allowed"
            )
        relation_targets[relation_id] = relation.attrib["Target"]

    targets: list[tuple[str, str]] = []
    names: set[str] = set()
    for sheet in workbook.findall(f".//{{{_OOXML_MAIN}}}sheet"):
        name = sheet.attrib["name"]
        if name in names:
            raise ReviewWorkbookError(f"duplicate worksheet name {name!r}")
        names.add(name)
        relation_id = sheet.attrib[f"{{{_OOXML_REL}}}id"]
        try:
            target = relation_targets[relation_id]
        except KeyError as exc:
            raise ReviewWorkbookError(
                f"worksheet {name!r} has no package relationship"
            ) from exc
        target = target.replace("\\", "/")
        if target.startswith("/"):
            normalized = posixpath.normpath(target.lstrip("/"))
        else:
            normalized = posixpath.normpath(posixpath.join("xl", target))
        if not normalized.startswith("xl/") or normalized.startswith("xl/../"):
            raise ReviewWorkbookError(
                f"worksheet {name!r} has an invalid package target"
            )
        targets.append((name, normalized))
    return targets


def _cell_value(cell: ElementTree.Element, shared: list[str]) -> Any:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        text = "".join(
            node.text or "" for node in cell.findall(f".//{{{_OOXML_MAIN}}}t")
        )
        return text or None

    value_node = cell.find(f"{{{_OOXML_MAIN}}}v")
    if value_node is None or value_node.text is None or value_node.text == "":
        return None
    raw = value_node.text

    if cell_type == "s":
        if _UNSIGNED_INTEGER.fullmatch(raw) is None:
            raise ReviewWorkbookError(f"invalid shared-string index {raw!r}")
        index = int(raw)
        if index >= len(shared):
            raise ReviewWorkbookError(f"invalid shared-string index {raw!r}")
        return shared[index] or None
    if cell_type == "str":
        return raw
    if cell_type == "b":
        if raw not in {"0", "1"}:
            raise ReviewWorkbookError(f"invalid boolean cell value {raw!r}")
        return raw == "1"
    if cell_type == "d":
        return raw
    if cell_type == "e":
        raise ReviewWorkbookError(f"worksheet contains cell error {raw!r}")
    if cell_type not in {None, "n"}:
        raise ReviewWorkbookError(f"unsupported cell type {cell_type!r}")

    try:
        number = float(raw)
    except ValueError as exc:
        raise ReviewWorkbookError(f"invalid numeric cell value {raw!r}") from exc
    if not math.isfinite(number):
        raise ReviewWorkbookError(f"invalid numeric cell value {raw!r}")
    return int(number) if number.is_integer() else number


def _sheet_rows(
    archive: zipfile.ZipFile,
    target: str,
    shared: list[str],
) -> list[list[Any]]:
    root = ElementTree.fromstring(archive.read(target))
    rows: list[list[Any]] = []
    seen_rows: set[int] = set()
    for row in root.findall(f".//{{{_OOXML_MAIN}}}row"):
        row_number = int(row.attrib.get("r", len(rows) + 1))
        row_index = row_number - 1
        if row_index < 0:
            raise ReviewWorkbookError("worksheet contains an invalid row index")
        if row_index in seen_rows:
            raise ReviewWorkbookError(
                f"worksheet contains duplicate row index {row_number}"
            )
        seen_rows.add(row_index)
        while len(rows) <= row_index:
            rows.append([])
        values: list[Any] = []
        seen_columns: set[int] = set()
        for cell in row.findall(f"{{{_OOXML_MAIN}}}c"):
            reference = cell.attrib.get("r")
            if reference is None:
                raise ReviewWorkbookError(
                    "worksheet contains a cell without a reference"
                )
            reference_match = _CELL_REFERENCE.fullmatch(reference)
            if reference_match is None:
                raise ReviewWorkbookError(f"invalid cell reference {reference!r}")
            reference_row = int(reference_match.group(2))
            if reference_row != row_number:
                raise ReviewWorkbookError(
                    f"cell reference {reference!r} does not match row {row_number}"
                )
            index = _column_index(reference)
            if index in seen_columns:
                raise ReviewWorkbookError(
                    f"worksheet contains duplicate cell reference {reference!r}"
                )
            seen_columns.add(index)
            if index >= len(values):
                values.extend([None] * (index - len(values) + 1))
            values[index] = _cell_value(cell, shared)
        rows[row_index] = values
    while rows and not rows[-1]:
        rows.pop()
    return rows


def read_workbook_rows(path: str | Path) -> dict[str, list[list[Any]]]:
    """Return every worksheet using raw OOXML values and normalized blanks."""

    workbook_path = Path(path)
    try:
        with zipfile.ZipFile(workbook_path) as archive:
            shared = _shared_strings(archive)
            targets = _sheet_targets(archive)
            if not targets:
                raise ReviewWorkbookError("workbook contains no worksheets")
            return {
                name: _sheet_rows(archive, target, shared) for name, target in targets
            }
    except ReviewWorkbookError:
        raise
    except (
        OSError,
        ValueError,
        zipfile.BadZipFile,
        ElementTree.ParseError,
        KeyError,
    ) as exc:
        raise ReviewWorkbookError(
            f"{workbook_path}: review workbook could not be read"
        ) from exc


def _column_name(index: int) -> str:
    result = ""
    current = index + 1
    while current:
        current, remainder = divmod(current - 1, 26)
        result = chr(ord("A") + remainder) + result
    return result


def semantic_diff(
    baseline: dict[str, list[list[Any]]],
    returned: dict[str, list[list[Any]]],
) -> list[dict[str, Any]]:
    """Compare two parsed review carriers by normalized cell value."""

    if tuple(baseline) != tuple(returned):
        raise ReviewWorkbookError("returned workbook changed the worksheet layout")

    changes: list[dict[str, Any]] = []
    for sheet_name in baseline:
        before_rows = baseline[sheet_name]
        after_rows = returned[sheet_name]
        row_count = max(len(before_rows), len(after_rows))
        for row_index in range(row_count):
            before_row = before_rows[row_index] if row_index < len(before_rows) else []
            after_row = after_rows[row_index] if row_index < len(after_rows) else []
            column_count = max(len(before_row), len(after_row))
            for column_index in range(column_count):
                before = (
                    before_row[column_index] if column_index < len(before_row) else None
                )
                after = (
                    after_row[column_index] if column_index < len(after_row) else None
                )
                if type(before) is type(after) and before == after:
                    continue
                changes.append(
                    {
                        "sheet": sheet_name,
                        "cell": f"{_column_name(column_index)}{row_index + 1}",
                        "before": before,
                        "after": after,
                    }
                )
    return changes


__all__ = ["ReviewWorkbookError", "read_workbook_rows", "semantic_diff"]
