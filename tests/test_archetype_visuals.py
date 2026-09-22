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
