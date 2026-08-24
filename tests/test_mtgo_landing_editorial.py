import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from mtgmeta.mtgo import landing_editorial as editorial


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = (
    ROOT
    / "outputs"
    / "p12-15c-20260823-02"
    / "P12-15C_Landing_Bilingual_Review_v6.xlsx"
)
WORKBOOK_SHA256 = "f871c769450da13a1fa25783b8f6094fede3229b38eee69667d40980ddef5a2f"


@pytest.fixture(scope="module")
def imported(tmp_path_factory):
    output_root = tmp_path_factory.mktemp("landing-editorial-import")
    result = editorial.import_review_workbook(
        ROOT,
        WORKBOOK,
        output_root=output_root,
        expected_sha256=WORKBOOK_SHA256,
    )
    return output_root, result


def test_raw_xlsx_reader_preserves_true_blank_cells():
    sheets = editorial.read_review_workbook(WORKBOOK)

    first_top8 = sheets["All Top 8"][0]
    assert first_top8["Add to Featured?"] is None
    assert first_top8["Owner Note"] is None
    assert first_top8["Rank"] == 1
    assert first_top8["Add to Featured?"] != first_top8["Rank"]


def test_accepted_v6_imports_complete_private_subject(imported):
    output_root, result = imported

    assert result["workbook_sha256"] == WORKBOOK_SHA256
    assert result["name_count"] == 323
    assert result["review_count"] == 3
    assert result["feature_count"] == 16
    assert result["copy_count"] == 11

    standard_w27 = yaml.safe_load(
        (output_root / "stats/standard/mtgo/landing/review/2026-W27.yaml").read_text(
            encoding="utf-8"
        )
    )
    standard_w33 = yaml.safe_load(
        (output_root / "stats/standard/mtgo/landing/review/2026-W33.yaml").read_text(
            encoding="utf-8"
        )
    )
    modern_w33 = yaml.safe_load(
        (output_root / "stats/modern/mtgo/landing/review/2026-W33.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert standard_w27["review"]["features"] == {
        "reviewed": True,
        "explicit_empty": True,
        "items": [],
    }
    assert len(standard_w33["review"]["top_copy"]["items"]) == 9
    assert len(standard_w33["review"]["features"]["items"]) == 14
    assert len(modern_w33["review"]["top_copy"]["items"]) == 2
    assert len(modern_w33["review"]["features"]["items"]) == 2


def test_imported_documents_validate_against_internal_schemas(imported):
    output_root, _result = imported
    review_schema = json.loads(
        (ROOT / "schemas/mtgo-landing-review.schema.json").read_text(encoding="utf-8")
    )
    names_schema = json.loads(
        (ROOT / "schemas/mtgo-archetype-names.schema.json").read_text(
            encoding="utf-8"
        )
    )
    names = yaml.safe_load(
        (output_root / "configs/mtgo_archetype_names.yaml").read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator(names_schema).validate(names)
    for path in result_paths(output_root):
        jsonschema.Draft202012Validator(review_schema).validate(
            yaml.safe_load(path.read_text(encoding="utf-8"))
        )


def test_copy_tokens_are_selected_features_and_drive_derived_order(imported):
    output_root, _result = imported
    review = editorial.load_review_document(
        output_root / "stats/standard/mtgo/landing/review/2026-W33.yaml"
    )
    names = editorial.load_name_catalog(
        output_root / "configs/mtgo_archetype_names.yaml"
    )

    public = editorial.materialize_review(review, names)
    copy_tokens = editorial.copy_deck_tokens(review["review"]["top_copy"]["items"])
    feature_tokens = {
        item["destination_id"] for item in review["review"]["features"]["items"]
    }
    assert set(copy_tokens) <= feature_tokens
    assert [item["category"] for item in public["features"]] == sorted(
        [item["category"] for item in public["features"]],
        key={"new_deck": 0, "new_technology": 1}.get,
    )
    for category in ("new_deck", "new_technology"):
        expected = [token for token in copy_tokens if token in {
            item["destination_id"]
            for item in review["review"]["features"]["items"]
            if item["category"] == category
        }]
        actual = [
            item["destination_id"]
            for item in public["features"]
            if item["category"] == category and item["destination_id"] in expected
        ]
        assert actual == expected


def test_review_binding_changes_fail_closed(imported):
    output_root, _result = imported
    review = editorial.load_review_document(
        output_root / "stats/modern/mtgo/landing/review/2026-W33.yaml"
    )
    current = dict(review["bindings"])
    editorial.validate_review_binding(review, current)
    stale = dict(current)
    stale["classifier_digest"] = "0" * 64

    with pytest.raises(editorial.MTGOLandingEditorialError, match="classifier"):
        editorial.validate_review_binding(review, stale)


def test_top_copy_token_without_feature_fails_closed(imported):
    output_root, _result = imported
    path = output_root / "stats/standard/mtgo/landing/review/2026-W33.yaml"
    review = editorial.load_review_document(path)
    token = editorial.copy_deck_tokens(review["review"]["top_copy"]["items"])[0]
    review["review"]["features"]["items"] = [
        item
        for item in review["review"]["features"]["items"]
        if item["destination_id"] != token
    ]

    with pytest.raises(editorial.MTGOLandingEditorialError, match="lacks an exact"):
        editorial.validate_review_document(
            review,
            ROOT / "schemas/mtgo-landing-review.schema.json",
        )


def test_bilingual_catalog_coverage_fails_closed(imported, tmp_path):
    output_root, _result = imported
    catalog = yaml.safe_load(
        (output_root / "configs/mtgo_archetype_names.yaml").read_text(encoding="utf-8")
    )
    catalog["names"].pop()
    path = tmp_path / "incomplete.yaml"
    path.write_text(yaml.safe_dump(catalog, allow_unicode=True), encoding="utf-8")

    with pytest.raises(editorial.MTGOLandingEditorialError, match="coverage"):
        editorial.validate_name_catalog(ROOT, path)


@pytest.mark.parametrize("format_id", ["standard", "modern"])
def test_public_name_contract_matches_approved_format_catalog(format_id, tmp_path):
    destination = editorial.generate_public_name_contract(
        ROOT,
        format_id,
        output_directory=tmp_path / format_id,
    )
    document = json.loads(destination.read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "schemas/mtgo-archetype-localization.schema.json").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.Draft202012Validator(schema).validate(document)

    approved = editorial.load_name_catalog(ROOT / "configs/mtgo_archetype_names.yaml")
    expected = {
        f"{parent_id}/{subtype_id}" if subtype_id is not None else parent_id: names
        for (item_format, parent_id, subtype_id), names in approved.items()
        if item_format == format_id
    }
    actual = {item["identity_id"]: item["display"] for item in document["names"]}
    assert document["format"] == format_id
    assert actual == expected


def test_explicit_empty_review_advances_landing_known_state(imported):
    output_root, _result = imported
    review = editorial.load_review_document(
        output_root / "stats/standard/mtgo/landing/review/2026-W27.yaml"
    )
    known = json.loads(
        (output_root / "stats/standard/mtgo/landing/review/known_archetypes.json").read_text(
            encoding="utf-8"
        )
    )
    assert review["review"]["features"]["explicit_empty"] is True
    assert review["known_archetype_ids"]
    assert set(review["known_archetype_ids"]) <= set(known["known_ids"])
    assert known["accepted_through_week"] == "2026-W33"


def test_import_is_deterministic_for_same_workbook_subject(imported):
    output_root, result = imported
    paths = [result["catalog_path"], *result["review_paths"], *result["known_paths"]]
    before = {str(path.relative_to(output_root)): editorial.file_sha256(path) for path in paths}

    repeated = editorial.import_review_workbook(
        ROOT,
        WORKBOOK,
        output_root=output_root,
        expected_sha256=WORKBOOK_SHA256,
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


def test_import_rejects_a_different_workbook_hash(tmp_path):
    with pytest.raises(editorial.MTGOLandingEditorialError, match="SHA-256 changed"):
        editorial.import_review_workbook(
            ROOT,
            WORKBOOK,
            output_root=tmp_path,
            expected_sha256="0" * 64,
        )


def result_paths(root: Path) -> list[Path]:
    return [
        root / "stats/standard/mtgo/landing/review/2026-W27.yaml",
        root / "stats/standard/mtgo/landing/review/2026-W33.yaml",
        root / "stats/modern/mtgo/landing/review/2026-W33.yaml",
    ]
