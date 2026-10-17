from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from tools import build_archetype_visuals


def _write_jpeg(path: Path, *, width: int, height: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = (
        b"\xff\xc0\x00\x11\x08"
        + height.to_bytes(2, "big")
        + width.to_bytes(2, "big")
        + b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00"
    )
    path.write_bytes(b"\xff\xd8" + frame + b"\xff\xd9")


def _write_fixture(
    root: Path,
    *,
    cards: dict[str, list[str]],
    statistics: dict[int, list[tuple[str, float]]] | None = None,
) -> None:
    config = root / "configs/mtgo_landing_visuals.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        yaml.safe_dump(
            {
                "formats": {
                    "fixture": {
                        "parents": cards,
                        "subtypes": {},
                        "allow_parent_fallback_for_subtypes": [],
                    }
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    rendered = root / "assets/js/phase8/archetype-visuals.js"
    rendered.parent.mkdir(parents=True, exist_ok=True)
    rendered.write_text(
        "const representativeCards = Object.freeze({\n"
        "  fixture: Object.freeze({\n"
        "  }),\n"
        "});\n",
        encoding="utf-8",
    )
    for weeks, rows in (statistics or {}).items():
        path = root / f"stats/fixture/mtgo/range_{weeks}w.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "archetypes": [
                        {"id": identity, "high_score_share": share}
                        for identity, share in rows
                    ]
                }
            ),
            encoding="utf-8",
        )


def test_representative_card_rejects_full_card_portrait(tmp_path: Path) -> None:
    _write_fixture(tmp_path, cards={"example": ["Example Card"]})
    image = tmp_path / "assets/images/representative-cards/fixture/example-card.jpg"
    _write_jpeg(image, width=488, height=680)

    with pytest.raises(ValueError, match=r"full-card portrait.*488x680"):
        build_archetype_visuals.generate(tmp_path, "fixture")


def test_representative_card_accepts_landscape_art_crop(tmp_path: Path) -> None:
    _write_fixture(tmp_path, cards={"example": ["Example Card"]})
    image = tmp_path / "assets/images/representative-cards/fixture/example-card.jpg"
    _write_jpeg(image, width=626, height=457)

    build_archetype_visuals.generate(tmp_path, "fixture")

    rendered = (tmp_path / "assets/js/phase8/archetype-visuals.js").read_text(
        encoding="utf-8"
    )
    assert '"example": Object.freeze([' in rendered


def test_representative_card_accepts_vertical_art_crop_layout(tmp_path: Path) -> None:
    _write_fixture(tmp_path, cards={"example": ["Example Card"]})
    image = tmp_path / "assets/images/representative-cards/fixture/example-card.jpg"
    _write_jpeg(image, width=312, height=752)

    build_archetype_visuals.generate(tmp_path, "fixture")


def test_representative_card_accepts_panorama_art_crop_layout(tmp_path: Path) -> None:
    _write_fixture(tmp_path, cards={"example": ["Example Card"]})
    image = tmp_path / "assets/images/representative-cards/fixture/example-card.jpg"
    _write_jpeg(image, width=808, height=280)

    build_archetype_visuals.generate(tmp_path, "fixture")


def test_public_statistics_rejects_visible_archetype_without_art(
    tmp_path: Path,
) -> None:
    _write_fixture(
        tmp_path,
        cards={"configured": ["Configured Card"]},
        statistics={
            1: [("configured", 0.04), ("below-threshold", 0.0299)],
            4: [("missing", 0.03), ("unknown", 0.10)],
        },
    )
    image = tmp_path / "assets/images/representative-cards/fixture/configured-card.jpg"
    _write_jpeg(image, width=626, height=457)

    with pytest.raises(
        ValueError,
        match=r"public statistics.*fixture.*4w=missing",
    ):
        build_archetype_visuals.generate(tmp_path, "fixture")


def _shared_fixture(root):
    _write_fixture(root, cards={"shared": ["First", "Second"]},
                   statistics={1: [("shared", .04), ("small", .0299)],
                               4: [("shared", .08), ("unknown", .1)],
                               12: [("shared", .03)]})
    for card in ("first", "second"):
        _write_jpeg(root / f"assets/images/representative-cards/fixture/{card}.jpg", width=626, height=457)
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and "configs" not in p.parts}


def test_shared_inventory_uses_all_three_windows_and_does_not_generate(tmp_path):
    selected = _shared_fixture(tmp_path)
    before = {p: (tmp_path / p).read_bytes() for p in selected}
    result = build_archetype_visuals.inspect_statistics(tmp_path, "fixture")
    assert len(result["rows"]) == 1
    assert result["rows"][0]["windows"] == [1, 4, 12]
    assert result["rows"][0]["cards"] == ["First", "Second"]
    assert result["rows"][0]["problems"] == ["rendered_binding_differs"]
    assert before == {p: (tmp_path / p).read_bytes() for p in selected}


@pytest.mark.parametrize("window", [1, 4, 12])
def test_missing_choice_in_any_public_window_blocks_packaging(tmp_path, monkeypatch, window):
    import build_pages_artifact as builder
    root = tmp_path / "root"
    selected = _shared_fixture(root)
    build_archetype_visuals.generate(root, "fixture")
    path = root / f"stats/fixture/mtgo/range_{window}w.json"
    document = json.loads(path.read_text())
    document["archetypes"].append({"id": "unselected", "high_score_share": .03})
    path.write_text(json.dumps(document))
    monkeypatch.setattr(builder, "load_config", lambda *a: {})
    monkeypatch.setattr(builder, "publication_paths", lambda *a: selected)
    with pytest.raises(builder.PublicationError, match="unselected.*two_ordered_cards_required"):
        builder.build_artifact(root, root / "config.json", tmp_path / "site", tmp_path / "report.json")
    assert not (tmp_path / "site").exists()


@pytest.mark.parametrize("damage", ["one_card", "duplicate", "swapped", "missing_image", "excluded_image", "portrait"])
def test_shared_delivery_rejects_incomplete_or_wrong_actual_resources(tmp_path, damage):
    selected = _shared_fixture(tmp_path)
    build_archetype_visuals.generate(tmp_path, "fixture")
    path = tmp_path / "configs/mtgo_landing_visuals.yaml"
    config = yaml.safe_load(path.read_text())
    if damage in {"one_card", "duplicate", "swapped"}:
        config["formats"]["fixture"]["parents"]["shared"] = {
            "one_card": ["First"], "duplicate": ["First", "First"], "swapped": ["Second", "First"]}[damage]
        path.write_text(yaml.safe_dump(config))
    image = "assets/images/representative-cards/fixture/second.jpg"
    if damage == "missing_image":
        (tmp_path / image).unlink()
    elif damage == "excluded_image":
        selected.remove(image)
    elif damage == "portrait":
        _write_jpeg(tmp_path / image, width=488, height=680)
    with pytest.raises(ValueError, match="Shared representatives incomplete"):
        build_archetype_visuals.require_public_representatives(tmp_path, selected)


def test_shared_pair_passes_real_packager_and_preserves_existing_landing(tmp_path, monkeypatch):
    import build_pages_artifact as builder
    root = tmp_path / "root"
    selected = _shared_fixture(root)
    build_archetype_visuals.generate(root, "fixture")
    landing = "stats/fixture/mtgo/landing/current.json"
    (root / landing).parent.mkdir()
    (root / landing).write_text('{"week":"previous","features":{"items":[]}}')
    selected.add(landing)
    monkeypatch.setattr(builder, "load_config", lambda *a: {"maximum_artifact_bytes": 1000000})
    monkeypatch.setattr(builder, "publication_paths", lambda *a: selected)
    monkeypatch.setattr(builder, "validate_compatibility", lambda *a: [])
    monkeypatch.setattr(builder, "_copy_generated_overlays", lambda *a: set())
    monkeypatch.setattr(builder, "_tracked_files", lambda *a: list(selected))
    monkeypatch.setattr(builder, "_git_storage_bytes", lambda *a: 0)
    site = tmp_path / "site"
    builder.build_artifact(root, root / "config.json", site, tmp_path / "report.json")
    assert all((site / p).read_bytes() == (root / p).read_bytes() for p in selected)
    # Private ranges outside the selected public scope cannot block this product.
    build_archetype_visuals.require_public_representatives(root, {landing})


@pytest.mark.parametrize("damage", [None, "missing_image", "excluded_image", "old_binding", "missing_name", "excluded_names"])
def test_retained_landing_is_protected_outside_current_statistics(tmp_path, damage):
    _write_fixture(tmp_path, cards={"previous": ["First", "Second"]},
                   statistics={1: [], 4: [], 12: []})
    for card in ("first", "second"):
        _write_jpeg(tmp_path / f"assets/images/representative-cards/fixture/{card}.jpg", width=626, height=457)
    build_archetype_visuals.generate(tmp_path, "fixture")
    landing = tmp_path / "stats/fixture/mtgo/landing/current.json"
    landing.parent.mkdir()
    landing.write_text(json.dumps({"environment": {"rows": [{"archetype_id": "previous",
                         "key_cards": [{"name": "First"}, {"name": "Second"}]}]}}))
    names = tmp_path / "stats/fixture/archetype_names.json"
    names.write_text(json.dumps({"names": [{"identity_id": "previous", "display": {"en": "Previous", "zh": "旧名称"}}]}), encoding="utf-8")
    selected = {p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file()}
    image = "assets/images/representative-cards/fixture/second.jpg"
    if damage == "missing_image":
        (tmp_path / image).unlink()
    elif damage == "excluded_image":
        selected.remove(image)
    elif damage == "old_binding":
        path = tmp_path / "assets/js/phase8/archetype-visuals.js"
        path.write_text(path.read_text().replace('"name": "First"', '"name": "Old"'))
    elif damage == "missing_name":
        names.write_text('{"names":[]}')
    elif damage == "excluded_names":
        selected.remove(names.relative_to(tmp_path).as_posix())
    if damage:
        with pytest.raises(ValueError, match="previous.*retained Landing|retained Landing missing bilingual names.*previous"):
            build_archetype_visuals.require_public_representatives(tmp_path, selected)
    else:
        build_archetype_visuals.require_public_representatives(tmp_path, selected)


@pytest.fixture
def accepted_representatives(tmp_path, monkeypatch):
    """Finite acceptance/import adapters; actual resource adoption and checks run."""
    import hashlib
    from tools import weekly_maintenance as workflow, import_landing_conversation
    from mtgmeta.mtgo import review_submission as submissions
    root, preparation = tmp_path / "root", tmp_path / "preparation"
    site = preparation / "site"
    for directory in (root, site):
        _write_fixture(directory, cards={"shared": ["First", "Second"], "unrelated": ["Keep", "These"]},
                       statistics={1: [("shared", .1)], 4: [], 12: []})
    for card in ("first", "second"):
        _write_jpeg(site / f"assets/images/representative-cards/fixture/{card}.jpg", width=626, height=457)
    build_archetype_visuals.generate(site, "fixture", identities={"shared"})
    page = {"environment": {"rows": [{"archetype_id": "shared",
                                     "key_cards": [{"name": "First"}, {"name": "Second"}]}]}}
    workflow.write(site / "stats/fixture/mtgo/landing/current.json", page)
    # The preview adapter binds all synthetic resources, so post-acceptance
    # corruption cannot be hidden by returning an always-successful packet.
    def packet(directory, fmt):
        return submissions.make_packet("preview", fmt, "2026-W41", {"final_page": {
            p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob("*") if p.is_file()}}, bindings={})
    monkeypatch.setattr(submissions, "preview_packet", packet)
    preview = packet(site, "fixture")
    decision = submissions.record_decision(preview, None, ["final_page"], evidence="synthetic-test-only",
        accepted_on="2026-10-17", entrypoint="fixture://page")
    workflow.write(preparation / "preview.json", preview)
    workflow.write(preparation / "visuals.yaml", yaml.safe_load((site / "configs/mtgo_landing_visuals.yaml").read_text()))
    source = {"format": "fixture", "week": {"id": "2026-W41"}, "acceptance": {"decisions": {
        "accepted_page_binding": {"preview_digest": preview["digest"],
                                 "acceptance": {"submission": preview, "decisions": decision}}}}}
    def importer(directory, document):
        path = directory / "stats/fixture/mtgo/landing/review/2026-W41.yaml"
        workflow.write(path, document)
        return path
    monkeypatch.setattr(import_landing_conversation, "import_content", importer)
    return root, preparation, source


def test_adoption_survives_fresh_checkout_and_next_legal_choice(accepted_representatives, tmp_path):
    import shutil
    from tools import weekly_maintenance as workflow
    root, preparation, source = accepted_representatives
    result = workflow.adopt_content(root, source, preparation)
    assert len(result["retained_representative_files"]) == 3
    fresh = tmp_path / "fresh"
    shutil.copytree(root, fresh)
    assert build_archetype_visuals.inspect_statistics(fresh, "fixture")["ready"]
    config = yaml.safe_load((fresh / "configs/mtgo_landing_visuals.yaml").read_text())
    assert config["formats"]["fixture"]["parents"]["unrelated"] == ["Keep", "These"]
    # A later confirmed pair changes normally; no check or protected rule edit.
    config["formats"]["fixture"]["parents"]["shared"] = ["Second", "Third"]
    workflow.write(fresh / "configs/mtgo_landing_visuals.yaml", config)
    _write_jpeg(fresh / "assets/images/representative-cards/fixture/third.jpg", width=626, height=457)
    build_archetype_visuals.generate(fresh, "fixture", identities={"shared"})
    assert build_archetype_visuals.inspect_statistics(fresh, "fixture")["ready"]


def test_adoption_rejects_changed_accepted_resources(accepted_representatives):
    from tools import weekly_maintenance as workflow
    root, preparation, source = accepted_representatives
    original = (root / "configs/mtgo_landing_visuals.yaml").read_bytes()
    (preparation / "site/assets/images/representative-cards/fixture/first.jpg").unlink()
    with pytest.raises(ValueError, match="resources changed"):
        workflow.adopt_content(root, source, preparation)
    assert (root / "configs/mtgo_landing_visuals.yaml").read_bytes() == original
    assert not (root / "assets/images").exists()


def test_failed_adoption_restores_config_bindings_and_images(accepted_representatives, monkeypatch):
    from tools import weekly_maintenance as workflow, import_landing_conversation
    root, preparation, source = accepted_representatives
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    def fail(*args):
        raise ValueError("injected importer failure")
    monkeypatch.setattr(import_landing_conversation, "import_content", fail)
    with pytest.raises(ValueError, match="injected"):
        workflow.adopt_content(root, source, preparation)
    assert {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()} == before
