from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import pytest

import build_pages_artifact
from mtgmeta.catalog import write_catalog
from tools.build_landing_card_image_cache import (
    CacheBuildError,
    build_cache_bundle,
    cache_subject,
    verify_cache_bundle,
)
from validate_schemas import load_schemas, validate_instance


JPEG_A = b"\xff\xd8\xff\xe0synthetic-image-a\xff\xd9"
JPEG_B = b"\xff\xd8\xff\xe0synthetic-image-b\xff\xd9"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_bulk_jsonl_gzip(path: Path, cards: list[dict[str, object]]) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as handle:
        for card in cards:
            handle.write(json.dumps(card, ensure_ascii=False, sort_keys=True) + "\n")


def _write_feature_week(root: Path, format_name: str, week: str, names: list[str]) -> None:
    _write_json(
        root / f"stats/{format_name}/mtgo/landing/features/{week}.json",
        {
            "schema_version": "1.0.0",
            "product": "mtgo-landing-features",
            "source": "mtgo",
            "format": format_name,
            "week": {"id": week},
            "features": {
                "items": [
                    {
                        "featured_cards": [{"name": name} for name in names],
                    }
                ]
                if names
                else []
            },
        },
    )


def _write_format(
    root: Path,
    format_name: str,
    weeks: list[tuple[str, str]],
    cards_by_week: dict[str, list[str]],
) -> None:
    _write_json(
        root / f"stats/{format_name}/mtgo/landing/features/index.json",
        {
            "schema_version": "1.0.0",
            "product": "mtgo-landing-features",
            "source": "mtgo",
            "format": format_name,
            "weeks": [
                {
                    "week": week,
                    "start": start,
                    "end": start,
                    "file": f"{week}.json",
                    "feature_count": 1 if cards_by_week.get(week) else 0,
                }
                for week, start in weeks
            ],
        },
    )
    for week, _start in weeks:
        _write_feature_week(root, format_name, week, cards_by_week.get(week, []))


def _synthetic_subject_root(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    _write_format(
        root,
        "standard",
        [
            ("2026-W34", "2026-08-17"),
            ("2026-W33", "2026-08-10"),
            ("2026-W27", "2026-06-29"),
        ],
        {
            "2026-W34": ["Shared Card", "New Card"],
            "2026-W33": ["Shared Card", "Front Face"],
            "2026-W27": ["Too Old"],
        },
    )
    _write_format(
        root,
        "modern",
        [("2026-W34", "2026-08-17"), ("2026-W33", "2026-08-10")],
        {"2026-W34": ["New Card"], "2026-W33": ["Modern Card"]},
    )
    return root


def _bulk_cards() -> list[dict[str, object]]:
    return [
        {
            "id": "99999999-9999-4999-8999-999999999999",
            "oracle_id": "99999999-aaaa-4aaa-8aaa-999999999999",
            "layout": "art_series",
            "name": "New Card // New Card",
            "card_faces": [
                {
                    "name": "New Card",
                    "image_uris": {"normal": "https://cards.scryfall.io/normal/art-front.jpg"},
                },
                {
                    "name": "New Card",
                    "image_uris": {"normal": "https://cards.scryfall.io/normal/art-back.jpg"},
                },
            ],
        },
        {
            "id": "11111111-1111-4111-8111-111111111111",
            "oracle_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "name": "New Card",
            "image_uris": {"normal": "https://cards.scryfall.io/normal/new-card.jpg"},
        },
        {
            "id": "22222222-2222-4222-8222-222222222222",
            "oracle_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            "name": "Front Face // Back Face",
            "card_faces": [
                {
                    "name": "Front Face",
                    "image_uris": {"normal": "https://cards.scryfall.io/normal/front.jpg"},
                },
                {
                    "name": "Back Face",
                    "image_uris": {"normal": "https://cards.scryfall.io/normal/back.jpg"},
                },
            ],
        },
        {
            "id": "33333333-3333-4333-8333-333333333333",
            "oracle_id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
            "name": "Modern Card",
            "image_uris": {"normal": "https://cards.scryfall.io/normal/modern.jpg"},
        },
        {
            "id": "44444444-4444-4444-8444-444444444444",
            "oracle_id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
            "name": "Shared Card",
            "image_uris": {"normal": "https://cards.scryfall.io/normal/shared.jpg"},
        },
    ]


def test_subject_uses_latest_published_week_and_three_iso_predecessors(tmp_path):
    root = _synthetic_subject_root(tmp_path)

    subject = cache_subject(root)

    by_format = {item["format"]: item for item in subject["formats"]}
    assert by_format["standard"]["anchor_week"] == "2026-W34"
    assert by_format["standard"]["window_start"] == "2026-W31"
    assert by_format["standard"]["selected_weeks"] == ["2026-W34", "2026-W33"]
    assert by_format["modern"]["selected_weeks"] == ["2026-W34", "2026-W33"]
    assert [card["name"] for card in subject["cards"]] == [
        "Front Face",
        "Modern Card",
        "New Card",
        "Shared Card",
    ]
    assert "Too Old" not in json.dumps(subject)
    assert subject["cache_schema_version"] == "1.1.0"
    assert len(subject["subject_sha256"]) == 64
    assert subject == cache_subject(root)


def test_build_ignores_repository_art_and_resolves_every_full_card_image(tmp_path):
    root = _synthetic_subject_root(tmp_path)
    visuals = root / "assets/js/phase8/archetype-visuals.js"
    visuals.parent.mkdir(parents=True, exist_ok=True)
    visuals.write_text(
        'Object.freeze({ name: "Shared Card", image: "../images/representative-cards/standard/shared-card.jpg" }),\n',
        encoding="utf-8",
    )
    reused = root / "assets/images/representative-cards/standard/shared-card.jpg"
    reused.parent.mkdir(parents=True, exist_ok=True)
    reused.write_bytes(JPEG_A)
    bulk_path = tmp_path / "oracle-cards.jsonl.gz"
    _write_bulk_jsonl_gzip(bulk_path, _bulk_cards())
    payloads = {
        "https://cards.scryfall.io/normal/new-card.jpg": JPEG_A,
        "https://cards.scryfall.io/normal/front.jpg": JPEG_B,
        "https://cards.scryfall.io/normal/modern.jpg": JPEG_A,
        "https://cards.scryfall.io/normal/shared.jpg": JPEG_B,
    }
    output = tmp_path / "cache"

    manifest = build_cache_bundle(
        root,
        output,
        bulk_data_path=bulk_path,
        fetch_image=lambda url: payloads[url],
    )

    entries = {item["name"]: item for item in manifest["cards"]}
    assert manifest["schema_version"] == "1.1.0"
    assert {entry["cache_source"] for entry in entries.values()} == {"generated"}
    assert entries["Shared Card"]["source_image_uri"].endswith("/shared.jpg")
    assert entries["Shared Card"]["local_path"].startswith(
        "assets/card-cache/v1/images/44444444-4444-4444-8444-444444444444"
    )
    assert entries["Front Face"]["face_index"] == 0
    assert entries["Front Face"]["source_image_uri"].endswith("/front.jpg")
    assert entries["New Card"]["local_path"].startswith(
        "assets/card-cache/v1/images/11111111-1111-4111-8111-111111111111"
    )
    assert reused.read_bytes() == JPEG_A
    assert (
        output / "images" / "44444444-4444-4444-8444-444444444444.jpg"
    ).read_bytes() == JPEG_B
    verified = verify_cache_bundle(root, output)
    assert verified == manifest

    schemas, registry = load_schemas(REPOSITORY_ROOT / "schemas")
    assert not validate_instance(
        manifest,
        schemas["landing-card-image-cache.schema.json"],
        registry,
    )


def test_missing_recent_card_fails_without_partial_bundle(tmp_path):
    root = _synthetic_subject_root(tmp_path)
    bulk_path = tmp_path / "oracle-cards.json"
    _write_json(bulk_path, _bulk_cards()[:-1])
    output = tmp_path / "cache"

    with pytest.raises(CacheBuildError, match="unresolved featured cards"):
        build_cache_bundle(
            root,
            output,
            bulk_data_path=bulk_path,
            fetch_image=lambda _url: JPEG_A,
        )

    assert not output.exists()


def test_build_resolves_maintained_alias_without_changing_feature_name(tmp_path):
    root = tmp_path / "repository"
    _write_format(
        root,
        "standard",
        [("2026-W35", "2026-08-24")],
        {"2026-W35": ["Reality Fulcrum"]},
    )
    _write_format(root, "modern", [("2026-W35", "2026-08-24")], {})
    bulk_path = tmp_path / "oracle-cards.json"
    _write_json(
        bulk_path,
        [
            {
                "id": "55555555-5555-4555-8555-555555555555",
                "oracle_id": "456dbec4-1b0e-48c4-abae-5c8205651872",
                "name": "Interdimensional Web Watch",
                "image_uris": {
                    "normal": "https://cards.scryfall.io/normal/interdimensional-web-watch.jpg"
                },
            }
        ],
    )
    output = tmp_path / "cache"

    manifest = build_cache_bundle(
        root,
        output,
        bulk_data_path=bulk_path,
        fetch_image=lambda _url: JPEG_A,
    )

    assert manifest["cards"][0]["name"] == "Reality Fulcrum"
    assert manifest["cards"][0]["oracle_id"] == "456dbec4-1b0e-48c4-abae-5c8205651872"
    assert manifest["cards"][0]["source_image_uri"].endswith(
        "/interdimensional-web-watch.jpg"
    )
    assert verify_cache_bundle(root, output) == manifest


def test_adventure_face_name_uses_the_combined_card_image(tmp_path):
    root = _synthetic_subject_root(tmp_path)
    cards = _bulk_cards()
    combined = next(card for card in cards if card.get("name") == "Front Face // Back Face")
    combined["image_uris"] = {
        "normal": "https://cards.scryfall.io/normal/combined.jpg"
    }
    for face in combined["card_faces"]:
        face.pop("image_uris")
    bulk_path = tmp_path / "oracle-cards.jsonl.gz"
    _write_bulk_jsonl_gzip(bulk_path, cards)
    output = tmp_path / "cache"

    manifest = build_cache_bundle(
        root,
        output,
        bulk_data_path=bulk_path,
        fetch_image=lambda _url: JPEG_A,
    )

    entry = next(card for card in manifest["cards"] if card["name"] == "Front Face")
    assert entry["face_index"] is None
    assert entry["source_image_uri"].endswith("/combined.jpg")


def test_verifier_rejects_changed_image_bytes(tmp_path):
    root = _synthetic_subject_root(tmp_path)
    bulk_path = tmp_path / "oracle-cards.json"
    _write_json(bulk_path, _bulk_cards())
    output = tmp_path / "cache"
    build_cache_bundle(
        root,
        output,
        bulk_data_path=bulk_path,
        fetch_image=lambda _url: JPEG_A,
    )
    image = next((output / "images").glob("*.jpg"))
    image.write_bytes(JPEG_B)

    with pytest.raises(CacheBuildError, match="SHA-256 mismatch"):
        verify_cache_bundle(root, output)


def test_pages_builder_admits_only_verified_configured_overlay(tmp_path, monkeypatch):
    root = _synthetic_subject_root(tmp_path)
    # The overlay fixture must also satisfy the shared Pages admission boundary.
    formats = []
    for format_name in ("standard", "modern"):
        formats.append({
            "id": format_name, "display_name": format_name.title(),
            "state": "executable", "public": True,
            "mtgo": {
                "enabled": True, "event_collection_enabled": True,
                "capabilities": [
                    "classification", "event_statistics", "range_statistics",
                    "matchup_statistics", "weekly_top8", "completeness_reporting",
                    "landing_generation", "metadata_generation", "catalog_generation",
                ],
                "paths": {
                    "events": f"data/{format_name}",
                    "matches": f"data/{format_name}/mtgo/matches",
                    "rules": f"my_archetypes/{format_name}.yaml",
                    "statistics": f"stats/{format_name}/mtgo",
                    "reports": f"reports/{format_name}/mtgo",
                },
            },
        })
        for suffix in ("meta.json", "matchup_index.json", "top8/index.json", "landing/current.json"):
            path = root / f"stats/{format_name}/mtgo/{suffix}"
            if not path.exists():
                _write_json(path, {})
    _write_json(root / "configs/formats.yaml", {"schema_version": "1.3.0", "formats": formats})
    write_catalog(root, generated_at="2026-08-17T00:00:00+00:00")
    (root / "index.html").write_text("ok", encoding="utf-8")
    (root / "assets/base.txt").parent.mkdir(parents=True, exist_ok=True)
    (root / "assets/base.txt").write_text("base", encoding="utf-8")
    config_path = root / "configs/pages_publication.json"
    _write_json(
        config_path,
        {
            "schema_version": "1.3.0",
            "site_files": ["index.html"],
            "site_directories": ["assets"],
            "excluded_patterns": ["assets/private/*"],
            "compatibility_manifests": ["compatibility.json"],
            "generated_overlays": [
                {
                    "id": "landing_card_images",
                    "public_prefix": "assets/card-cache/v1",
                    "manifest": "manifest.json",
                    "maximum_bytes": 10_000_000,
                },
                {
                    "id": "card_localization",
                    "public_prefix": "assets/card-localization",
                    "manifest": "cards.json",
                    "maximum_bytes": 10_000_000,
                }
            ],
            "maximum_artifact_bytes": 20_000_000,
        },
    )
    bulk_path = tmp_path / "oracle-cards.json"
    _write_json(bulk_path, _bulk_cards())
    cache = tmp_path / "cache"
    build_cache_bundle(
        root,
        cache,
        bulk_data_path=bulk_path,
        fetch_image=lambda _url: JPEG_A,
    )
    localization = tmp_path / "localization"
    _write_json(localization / "cards.json", {})
    monkeypatch.setattr(build_pages_artifact, "validate_compatibility", lambda *_args: set())
    monkeypatch.setattr(
        build_pages_artifact,
        "_tracked_files",
        lambda *_args: ["assets/base.txt", "index.html"],
    )
    monkeypatch.setattr(build_pages_artifact, "_git_storage_bytes", lambda *_args: 0)
    output = tmp_path / "site"
    report_path = tmp_path / "report.json"

    report = build_pages_artifact.build_artifact(
        root,
        config_path,
        output,
        report_path,
        overlays={
            "landing_card_images": cache,
            "card_localization": localization,
        },
    )

    assert (output / "assets/card-cache/v1/manifest.json").is_file()
    generated = [
        path
        for path in (output / "assets/card-cache/v1/images").glob("*.jpg")
    ]
    assert generated
    localization_map = output / "assets/card-localization/cards.json"
    assert localization_map.is_file()
    assert report["generated_overlays"] == {
        "files": len(generated) + 2,
        "bytes": sum(path.stat().st_size for path in generated)
        + (output / "assets/card-cache/v1/manifest.json").stat().st_size
        + localization_map.stat().st_size,
    }


def test_manifest_digest_covers_every_cached_byte(tmp_path):
    root = _synthetic_subject_root(tmp_path)
    bulk_path = tmp_path / "oracle-cards.json"
    _write_json(bulk_path, _bulk_cards())
    output = tmp_path / "cache"
    manifest = build_cache_bundle(
        root,
        output,
        bulk_data_path=bulk_path,
        fetch_image=lambda _url: JPEG_A,
    )

    for entry in manifest["cards"]:
        local = output / Path(entry["local_path"]).relative_to("assets/card-cache/v1")
        assert hashlib.sha256(local.read_bytes()).hexdigest() == entry["sha256"]
