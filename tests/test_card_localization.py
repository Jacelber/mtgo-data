from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest

from tools.build_card_localization import (
    LocalizationBuildError,
    build_bundle,
    build_manifest,
    verify_bundle,
)
from validate_schemas import load_schemas, validate_instance


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_SHA256 = hashlib.sha256(b"synthetic-mtgch-snapshot").hexdigest()
WEBP_A = b"RIFF\x08\x00\x00\x00WEBPVP8 "


def _card(
    *,
    scryfall_id: str = "11111111-1111-4111-8111-111111111111",
    oracle_id: str = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    face_index: int | None = None,
    name: str = "Example Card",
    **overrides: object,
) -> dict[str, object]:
    card: dict[str, object] = {
        "id": scryfall_id,
        "oracle_id": oracle_id,
        "face_index": face_index,
        "name": name,
        "face_name": None,
        "image_uris": {
            "normal": f"https://cards.scryfall.io/normal/{scryfall_id}.jpg"
        },
        "zhs_name": None,
        "zhs_face_name": None,
        "zhs_language": None,
        "zhs_image": None,
        "zhs_image_uris": None,
        "atomic_official_name": None,
        "atomic_translated_name": None,
        "atomic_name_translated_from": None,
    }
    card.update(overrides)
    return card


def _bundle(cards: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "fixture_mode": True,
        "source_snapshot": {
            "provider": "mtgch",
            "snapshot_id": "synthetic-2026-08-28",
            "sha256": SNAPSHOT_SHA256,
        },
        "attributions": {
            "official": "Synthetic official Chinese source",
            "community": "Synthetic community translation source",
            "english_fallback": "Synthetic Scryfall English source",
        },
        "cards": cards,
    }


def _with_payload(
    bundle: dict[str, object], uri: str, payload: bytes = WEBP_A
) -> dict[str, object]:
    bundle["synthetic_image_payloads"] = {
        uri: base64.b64encode(payload).decode("ascii")
    }
    return bundle


def _assert_schema_valid(manifest: dict[str, object]) -> None:
    schemas, registry = load_schemas(ROOT / "schemas")
    assert not validate_instance(
        manifest,
        schemas["card-localization.schema.json"],
        registry,
    )


def test_official_print_name_and_image_keep_exact_provenance():
    image_uri = "https://images.mtgch.com/zhs/normal/official.webp"
    bundle = _with_payload(
        _bundle(
            [
                _card(
                    zhs_name="官方牌名",
                    zhs_language="Chinese Simplified",
                    zhs_image="官方",
                    zhs_image_uris={"normal": image_uri},
                    atomic_official_name="原子官方牌名",
                    atomic_translated_name="社区牌名",
                    atomic_name_translated_from="MTGZH",
                )
            ]
        ),
        image_uri,
    )

    manifest = build_manifest(
        bundle,
        permitted_name_statuses={"official"},
        permitted_image_statuses={"official"},
    )

    card = manifest["cards"][0]
    assert card["name"] == {
        "value": "官方牌名",
        "status": "official",
        "provenance": {
            "provider": "mtgch",
            "field": "zhs_name",
            "contributor": None,
            "attribution": "Synthetic official Chinese source",
        },
    }
    assert card["image"]["status"] == "official"
    assert card["image"]["provenance"]["field"] == "zhs_image_uris.normal"
    assert card["image"]["sha256"] == hashlib.sha256(WEBP_A).hexdigest()
    assert card["image"]["local_path"].endswith(f"/{card['image']['sha256']}.webp")
    _assert_schema_valid(manifest)


def test_atomic_official_name_precedes_community_when_print_is_not_official():
    manifest = build_manifest(
        _bundle(
            [
                _card(
                    zhs_name="含糊印次牌名",
                    zhs_language=None,
                    atomic_official_name="原子官方牌名",
                    atomic_translated_name="社区牌名",
                    atomic_name_translated_from="MTGZH",
                )
            ]
        ),
        permitted_name_statuses={"official"},
    )

    selected = manifest["cards"][0]["name"]
    assert selected["value"] == "原子官方牌名"
    assert selected["status"] == "official"
    assert selected["provenance"]["field"] == "atomic_official_name"


def test_community_name_keeps_contributor_but_image_falls_back_without_permission():
    manifest = build_manifest(
        _bundle(
            [
                _card(
                    zhs_name="不能冒充官方的牌名",
                    zhs_language=None,
                    zhs_image="MTGZH自制",
                    zhs_image_uris={
                        "normal": "https://images.mtgch.com/zhs/normal/community.webp"
                    },
                    atomic_translated_name="社区牌名",
                    atomic_name_translated_from="MTGZH",
                )
            ]
        ),
        permitted_name_statuses={"community"},
    )

    card = manifest["cards"][0]
    assert card["name"]["status"] == "community"
    assert card["name"]["value"] == "社区牌名"
    assert card["name"]["provenance"]["contributor"] == "MTGZH"
    assert card["image"]["status"] == "english_fallback"
    assert card["image"]["provenance"]["provider"] == "scryfall"


def test_community_name_without_permission_falls_back_to_english():
    manifest = build_manifest(
        _bundle(
            [
                _card(
                    atomic_translated_name="社区牌名",
                    atomic_name_translated_from="MTGZH",
                )
            ]
        )
    )

    assert manifest["cards"][0]["name"]["status"] == "english_fallback"


def test_synthetic_permission_can_exercise_community_image_contract():
    image_uri = "https://images.mtgch.com/zhs/normal/community.webp"
    manifest = build_manifest(
        _with_payload(
            _bundle(
                [
                    _card(
                        zhs_image="Synthetic Community",
                        zhs_image_uris={"normal": image_uri},
                    )
                ]
            ),
            image_uri,
        ),
        permitted_image_statuses={"community"},
    )

    image = manifest["cards"][0]["image"]
    assert image["status"] == "community"
    assert image["provenance"]["contributor"] == "Synthetic Community"
    assert image["source_uri"].endswith("/community.webp")
    assert image["media_type"] == "image/webp"


def test_chinese_image_bytes_require_permission_and_exact_payload_closure():
    image_uri = "https://images.mtgch.com/zhs/normal/official.webp"
    card = _card(zhs_image="官方", zhs_image_uris={"normal": image_uri})

    with pytest.raises(LocalizationBuildError, match="lacks a synthetic payload"):
        build_manifest(
            _bundle([card]),
            permitted_image_statuses={"official"},
        )
    with pytest.raises(LocalizationBuildError, match="undeclared synthetic image payloads"):
        build_manifest(_with_payload(_bundle([card]), image_uri))


def test_missing_chinese_values_use_explicit_english_fallback():
    manifest = build_manifest(_bundle([_card()]))

    card = manifest["cards"][0]
    assert card["name"]["value"] == "Example Card"
    assert card["name"]["status"] == "english_fallback"
    assert card["image"]["status"] == "english_fallback"
    _assert_schema_valid(manifest)


def test_schema_rejects_status_that_lies_about_provenance():
    manifest = build_manifest(_bundle([_card()]))
    manifest["cards"][0]["name"]["status"] = "official"
    schemas, registry = load_schemas(ROOT / "schemas")

    failures = validate_instance(
        manifest,
        schemas["card-localization.schema.json"],
        registry,
    )

    assert failures
    assert any(failure.location.endswith(".name.provenance.provider") for failure in failures)


def test_identity_not_display_name_controls_sorting_and_duplicate_rejection():
    first = _card(
        scryfall_id="22222222-2222-4222-8222-222222222222",
        oracle_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        face_index=1,
        name="Shared Name",
        face_name="Shared Name",
    )
    second = _card(name="Shared Name")

    forward = build_manifest(_bundle([first, second]))
    reverse = build_manifest(_bundle([second, first]))

    assert forward == reverse
    assert [card["oracle_id"] for card in forward["cards"]] == [
        "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    ]
    assert len({card["scryfall_id"] for card in forward["cards"]}) == 2
    with pytest.raises(LocalizationBuildError, match="duplicate card identity"):
        build_manifest(_bundle([second, dict(second)]))


def test_two_faces_share_printing_identity_without_colliding():
    front = _card(
        face_index=0,
        name="Front Face // Back Face",
        face_name="Front Face",
        zhs_name="正面 // 背面",
        zhs_face_name="正面",
        zhs_language="Chinese Simplified",
    )
    back = _card(
        face_index=1,
        name="Front Face // Back Face",
        face_name="Back Face",
        zhs_name="正面 // 背面",
        zhs_face_name="背面",
        zhs_language="Chinese Simplified",
    )

    manifest = build_manifest(
        _bundle([back, front]),
        permitted_name_statuses={"official"},
    )

    assert [card["face_index"] for card in manifest["cards"]] == [0, 1]
    assert [card["english_name"] for card in manifest["cards"]] == [
        "Front Face",
        "Back Face",
    ]
    assert [card["name"]["value"] for card in manifest["cards"]] == ["正面", "背面"]
    assert all(
        card["name"]["provenance"]["field"] == "zhs_face_name"
        for card in manifest["cards"]
    )
    _assert_schema_valid(manifest)


def test_mtgch_single_face_sentinel_normalizes_to_null_identity():
    manifest = build_manifest(_bundle([_card(face_index=-1)]))

    assert manifest["cards"][0]["face_index"] is None


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"id": "not-a-uuid"}, "invalid scryfall_id"),
        ({"oracle_id": None}, "invalid oracle_id"),
        ({"face_index": -2}, "invalid face_index"),
        (
            {"image_uris": {"normal": "https://cards.scryfall.io.evil/fake.jpg"}},
            "untrusted English image URI",
        ),
    ],
)
def test_invalid_identity_or_fallback_uri_fails_closed(
    mutation: dict[str, object], message: str
):
    with pytest.raises(LocalizationBuildError, match=message):
        build_manifest(_bundle([_card(**mutation)]))


def test_missing_community_contributor_does_not_create_unattributed_translation():
    manifest = build_manifest(
        _bundle(
            [
                _card(
                    atomic_translated_name="Unattributed",
                    atomic_name_translated_from=None,
                )
            ]
        ),
        permitted_name_statuses={"community"},
    )

    assert manifest["cards"][0]["name"]["status"] == "english_fallback"


def test_bundle_builder_requires_fixture_mode_without_leaving_output(tmp_path):
    source = tmp_path / "input.json"
    output = tmp_path / "bundle"
    bundle = _bundle([_card()])
    bundle["fixture_mode"] = False
    source.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(LocalizationBuildError, match="fixture_mode must be true"):
        build_bundle(source, output)

    assert not output.exists()


def test_bundle_builder_writes_one_deterministic_closed_bundle_atomically(tmp_path):
    source = tmp_path / "input.json"
    output_a = tmp_path / "bundle-a"
    output_b = tmp_path / "bundle-b"
    source.write_text(
        json.dumps(_bundle([_card()]), ensure_ascii=False),
        encoding="utf-8",
    )

    first = build_bundle(source, output_a)
    second = build_bundle(source, output_b)

    assert second == first
    assert (output_a / "manifest.json").read_bytes() == (
        output_b / "manifest.json"
    ).read_bytes()
    assert verify_bundle(output_a) == first
    existing_bytes = (output_a / "manifest.json").read_bytes()
    with pytest.raises(LocalizationBuildError, match="output already exists"):
        build_bundle(source, output_a)
    assert (output_a / "manifest.json").read_bytes() == existing_bytes
    assert not list(tmp_path.glob("card-localization-*"))


def test_bundle_verifier_rejects_digest_mismatch_and_undeclared_files(tmp_path):
    source = tmp_path / "input.json"
    output = tmp_path / "bundle"
    image_uri = "https://images.mtgch.com/zhs/normal/official.webp"
    bundle = _with_payload(
        _bundle(
            [
                _card(
                    zhs_image="官方",
                    zhs_image_uris={"normal": image_uri},
                )
            ]
        ),
        image_uri,
    )
    source.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    manifest = build_bundle(source, output, permitted_image_statuses={"official"})
    image_path = output / "images" / f"{manifest['cards'][0]['image']['sha256']}.webp"

    image_path.write_bytes(WEBP_A + b"tampered")
    with pytest.raises(LocalizationBuildError, match="byte count mismatch"):
        verify_bundle(output)

    image_path.write_bytes(WEBP_A)
    (output / "undeclared.txt").write_text("synthetic", encoding="utf-8")
    with pytest.raises(LocalizationBuildError, match="undeclared files"):
        verify_bundle(output)
