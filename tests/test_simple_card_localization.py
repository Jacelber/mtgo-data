from __future__ import annotations

import json
import urllib.error
from pathlib import Path

import pytest

from tools import build_simple_card_localization as localization


WEBP = b"RIFF\x04\x00\x00\x00WEBP"


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://mtgch.com/api/v1/result",
        code,
        "test error",
        None,
        None,
    )


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    landing = root / "stats/standard/mtgo/landing"
    _write_json(
        landing / "current.json",
        {
            "week": {"id": "2026-W34"},
            "environment": {"rows": [{"key_cards": [{"name": "Local Card"}]}]},
        },
    )
    _write_json(
        landing / "features/2026-W34.json",
        {
            "features": {
                "items": [{"featured_cards": [{"name": "Feature Card"}]}]
            }
        },
    )
    _write_json(
        root / "stats/standard/mtgo/decks_1w.json",
        {"decks": [{"main_deck": [{"name": "Remote Card", "qty": 4}]}]},
    )
    return root


def _page(_names: list[str], _page_number: int) -> dict:
    def card(name: str, chinese: str, marker: str) -> dict:
        return {
            "id": marker,
            "card_detail_url": f"/card/TST/{marker}/",
            "display_name": name,
            "display_name_zh": chinese,
            "image_url": f"https://images.mtgch.com/zhs/normal/front/{marker}.webp",
            "other_faces": [],
        }

    return {
        "page": 1,
        "total_pages": 1,
        "items": [
            card("Feature Card", "精选牌", "b"),
            card("Local Card", "本地牌", "a"),
            card("Remote Card", "远程牌", "c"),
        ],
    }


def test_collects_existing_product_names_and_current_landing_only(tmp_path: Path):
    root = _root(tmp_path)
    assert localization.product_card_names(root) == [
        "Feature Card",
        "Local Card",
        "Remote Card",
    ]
    assert localization.current_landing_names(root) == ["Feature Card", "Local Card"]


def test_cache_subject_is_stable_and_changes_with_product_inputs(tmp_path: Path):
    root = _root(tmp_path)
    first = localization.cache_subject(root)

    assert first == localization.cache_subject(root)
    assert first["schema_version"] == "1.0.0"
    assert first["product_card_names"] == [
        "Feature Card",
        "Local Card",
        "Remote Card",
    ]
    assert first["current_landing_names"] == ["Feature Card", "Local Card"]
    assert len(first["subject_sha256"]) == 64

    _write_json(
        root / "stats/modern/mtgo/decks_1w.json",
        {"decks": [{"sideboard": [{"name": "New Card", "qty": 1}]}]},
    )

    second = localization.cache_subject(root)
    assert second["subject_sha256"] != first["subject_sha256"]
    assert "New Card" in second["product_card_names"]


def test_builds_flat_lookup_and_only_current_landing_images(tmp_path: Path):
    root = _root(tmp_path)
    output = tmp_path / "bundle"
    lookup = localization.build_bundle(
        root,
        output,
        fetch_page=_page,
        fetch_image=lambda _url: WEBP,
    )

    assert set(lookup) == {"Feature Card", "Local Card", "Remote Card"}
    assert "local_image" in lookup["Feature Card"]
    assert "local_image" in lookup["Local Card"]
    assert "local_image" not in lookup["Remote Card"]
    assert lookup["Remote Card"]["mtgch_url"] == "https://mtgch.com/card/TST/c/"
    assert len(list((output / "images").glob("*.webp"))) == 2
    assert localization.verify_bundle(root, output) == lookup


def test_resolve_lookup_uses_existing_name_normalizer_and_keeps_product_keys(
    monkeypatch: pytest.MonkeyPatch,
):
    candidates = {
        "Old Product Name": ("Canonical Name",),
        "Front Face // Back Face": ("Front Face // Back Face", "Front Face"),
    }
    monkeypatch.setattr(
        localization,
        "card_name_lookup_candidates",
        lambda name: candidates[name],
    )

    def page(names: list[str], page_number: int) -> dict:
        assert names == ["Canonical Name", "Front Face", "Front Face // Back Face"]
        assert page_number == 1
        return {
            "page": 1,
            "total_pages": 1,
            "items": [
                {
                    "id": "a",
                    "card_detail_url": "/card/TST/1/",
                    "display_name": "Canonical Name",
                    "display_name_zh": "规范牌名",
                    "image_url": "https://images.mtgch.com/zhs/a.webp",
                },
                {
                    "id": "b",
                    "card_detail_url": "/card/TST/2/",
                    "display_name": "Front Face // Back Face",
                    "display_name_zh": "正面 // 背面",
                    "image_url": "https://images.mtgch.com/zhs/b.webp",
                },
            ],
        }

    lookup = localization.resolve_lookup(candidates, page)

    assert lookup["Old Product Name"]["zh_name"] == "规范牌名"
    assert lookup["Front Face // Back Face"]["zh_name"] == "正面 // 背面"


def test_resolve_lookup_rechecks_only_missing_names_in_smaller_batches(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(localization, "BATCH_SIZE", 4)
    monkeypatch.setattr(localization, "FALLBACK_BATCH_SIZE", 2)
    monkeypatch.setattr(localization, "FINAL_BATCH_SIZE", 1)
    calls: list[list[str]] = []

    def page(names: list[str], _page_number: int) -> dict:
        calls.append(names)
        items = []
        if len(names) == 1:
            items = [
                {
                    "id": name,
                    "card_detail_url": f"/card/TST/{name}/",
                    "display_name": name,
                    "display_name_zh": f"中-{name}",
                    "image_url": f"https://images.mtgch.com/zhs/{name}.webp",
                }
                for name in names
            ]
        return {"page": 1, "total_pages": 1, "items": items}

    lookup = localization.resolve_lookup(["A", "B", "C", "D"], page)

    assert calls == [
        ["A", "B", "C", "D"],
        ["A", "B"],
        ["C", "D"],
        ["A"],
        ["B"],
        ["C"],
        ["D"],
    ]
    assert set(lookup) == {"A", "B", "C", "D"}


def test_resolve_lookup_splits_multi_name_bad_requests(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(localization, "BATCH_SIZE", 4)
    monkeypatch.setattr(localization, "FALLBACK_BATCH_SIZE", 2)
    monkeypatch.setattr(localization, "FINAL_BATCH_SIZE", 1)
    calls: list[list[str]] = []

    def page(names: list[str], _page_number: int) -> dict:
        calls.append(names)
        if len(names) > 1:
            raise _http_error(400)
        name = names[0]
        return {
            "page": 1,
            "total_pages": 1,
            "items": [
                {
                    "id": name,
                    "card_detail_url": f"/card/TST/{name}/",
                    "display_name": name,
                    "display_name_zh": f"Localized {name}",
                    "image_url": f"https://images.mtgch.com/zhs/{name}.webp",
                }
            ],
        }

    lookup = localization.resolve_lookup(["A", "B", "C", "D"], page)

    assert calls == [
        ["A", "B", "C", "D"],
        ["A", "B"],
        ["A"],
        ["B"],
        ["C", "D"],
        ["C"],
        ["D"],
    ]
    assert set(lookup) == {"A", "B", "C", "D"}


@pytest.mark.parametrize(
    ("code", "names"),
    [(400, ["A"]), (429, ["A", "B"])],
)
def test_resolve_lookup_keeps_unrecoverable_http_errors_fatal(
    code: int,
    names: list[str],
):
    def page(_names: list[str], _page_number: int) -> dict:
        raise _http_error(code)

    with pytest.raises(urllib.error.HTTPError) as exc_info:
        localization.resolve_lookup(names, page)

    assert exc_info.value.code == code


def test_resolved_product_keys_do_not_share_mutable_entries(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        localization,
        "card_name_lookup_candidates",
        lambda _name: ("Shared Card",),
    )

    def page(_names: list[str], _page_number: int) -> dict:
        return {
            "page": 1,
            "total_pages": 1,
            "items": [
                {
                    "id": "a",
                    "card_detail_url": "/card/TST/1/",
                    "display_name": "Shared Card",
                    "display_name_zh": "共享牌",
                    "image_url": "https://images.mtgch.com/zhs/shared.webp",
                }
            ],
        }

    lookup = localization.resolve_lookup(["Alias A", "Alias B"], page)
    lookup["Alias A"]["local_image"] = "local.webp"

    assert "local_image" not in lookup["Alias B"]


def test_keeps_a_chinese_name_when_mtgch_has_no_chinese_image():
    def page(_names: list[str], _page_number: int) -> dict:
        return {
            "page": 1,
            "total_pages": 1,
            "items": [
                {
                    "id": "a",
                    "card_detail_url": "/card/ACR/276/",
                    "display_name": "Name Only Card",
                    "display_name_zh": "只有中文名",
                    "image_url": "https://images.mtgch.com/en/card.webp",
                }
            ],
        }

    assert localization.resolve_lookup(["Name Only Card"], page) == {
        "Name Only Card": {
            "zh_name": "只有中文名",
            "mtgch_url": "https://mtgch.com/card/ACR/276/",
        }
    }


def test_verify_rejects_a_declared_missing_landing_image(tmp_path: Path):
    root = _root(tmp_path)
    output = tmp_path / "bundle"
    lookup = localization.build_bundle(
        root,
        output,
        fetch_page=_page,
        fetch_image=lambda _url: WEBP,
    )
    missing = output / Path(lookup["Local Card"]["local_image"]).relative_to(
        localization.PUBLIC_PREFIX
    )
    missing.unlink()

    with pytest.raises(localization.LocalizationBuildError, match="is missing"):
        localization.verify_bundle(root, output)
