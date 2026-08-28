"""Build a deterministic card-localization manifest from synthetic MTGCH-shaped data."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import shutil
import tempfile
import uuid
from collections.abc import Collection
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit


SCHEMA_VERSION = "1.0.0"
PRODUCT = "card-localization"
PUBLIC_PREFIX = "assets/card-localization/v1"
LOCALIZED_STATUSES = frozenset({"official", "community"})
MAX_IMAGE_BYTES = 5 * 1024 * 1024


class LocalizationBuildError(ValueError):
    """Indicate that the synthetic localization contract cannot be built safely."""


def _nonempty(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped if stripped and stripped == value else None


def _uuid(record: dict[str, Any], field: str, label: str) -> str:
    try:
        return str(uuid.UUID(str(record.get(field))))
    except (ValueError, AttributeError) as exc:
        raise LocalizationBuildError(f"invalid {label}: {record.get(field)!r}") from exc


def _face_index(record: dict[str, Any]) -> int | None:
    value = record.get("face_index")
    if value is None or value == -1:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < -1:
        raise LocalizationBuildError(f"invalid face_index: {value!r}")
    return value


def _normal_uri(record: dict[str, Any], field: str) -> Any:
    value = record.get(field)
    return value.get("normal") if isinstance(value, dict) else None


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_webp(value: bytes, label: str) -> None:
    if len(value) > MAX_IMAGE_BYTES:
        raise LocalizationBuildError(f"synthetic WebP exceeds {MAX_IMAGE_BYTES} bytes: {label}")
    if len(value) < 12 or value[:4] != b"RIFF" or value[8:12] != b"WEBP":
        raise LocalizationBuildError(f"synthetic image is not WebP: {label}")


def _synthetic_payloads(bundle: dict[str, Any]) -> dict[str, bytes]:
    raw = bundle.get("synthetic_image_payloads", {})
    if not isinstance(raw, dict):
        raise LocalizationBuildError("synthetic_image_payloads must be an object")
    payloads: dict[str, bytes] = {}
    for uri, encoded in raw.items():
        trusted = _trusted_uri(uri, provider="mtgch", label="synthetic image URI")
        if not isinstance(encoded, str):
            raise LocalizationBuildError(f"synthetic image payload must be base64: {uri}")
        try:
            payload = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as exc:
            raise LocalizationBuildError(f"invalid synthetic image base64: {uri}") from exc
        _valid_webp(payload, uri)
        payloads[trusted] = payload
    return payloads


def _trusted_uri(value: Any, *, provider: str, label: str) -> str:
    if not isinstance(value, str):
        raise LocalizationBuildError(f"{label} is not a string: {value!r}")
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    try:
        port = parsed.port
    except ValueError as exc:
        raise LocalizationBuildError(f"untrusted {label}: {value!r}") from exc
    trusted = (
        parsed.scheme == "https"
        and not parsed.username
        and not parsed.password
        and port in (None, 443)
        and (
            (provider == "scryfall" and host.endswith(".scryfall.io"))
            or (provider == "mtgch" and host == "images.mtgch.com")
        )
        and bool(parsed.path)
    )
    if not trusted:
        raise LocalizationBuildError(f"untrusted {label}: {value!r}")
    return value


def _provenance(
    *,
    provider: str,
    field: str,
    contributor: str | None,
    attribution: str,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "field": field,
        "contributor": contributor,
        "attribution": attribution,
    }


def _attributions(bundle: dict[str, Any]) -> dict[str, str]:
    raw = bundle.get("attributions")
    required = ("official", "community", "english_fallback")
    if not isinstance(raw, dict):
        raise LocalizationBuildError("attributions must be an object")
    result: dict[str, str] = {}
    for status in required:
        value = _nonempty(raw.get(status))
        if value is None:
            raise LocalizationBuildError(f"missing {status} attribution")
        result[status] = value
    return result


def _source_snapshot(bundle: dict[str, Any]) -> dict[str, str]:
    raw = bundle.get("source_snapshot")
    if not isinstance(raw, dict) or set(raw) != {"provider", "snapshot_id", "sha256"}:
        raise LocalizationBuildError("source_snapshot must contain provider, snapshot_id, and sha256")
    provider = raw.get("provider")
    snapshot_id = _nonempty(raw.get("snapshot_id"))
    sha256 = raw.get("sha256")
    if provider != "mtgch":
        raise LocalizationBuildError("source_snapshot provider must be mtgch")
    if snapshot_id is None:
        raise LocalizationBuildError("source_snapshot snapshot_id must be non-empty")
    if not isinstance(sha256, str) or len(sha256) != 64 or any(
        char not in "0123456789abcdef" for char in sha256
    ):
        raise LocalizationBuildError("source_snapshot sha256 must be lowercase SHA-256")
    return {"provider": provider, "snapshot_id": snapshot_id, "sha256": sha256}


def _localized_name(
    record: dict[str, Any],
    english_name: str,
    english_field: str,
    face_index: int | None,
    attributions: dict[str, str],
    permitted: frozenset[str],
) -> dict[str, Any]:
    print_field = "zhs_face_name" if face_index is not None else "zhs_name"
    print_name = _nonempty(record.get(print_field))
    if (
        "official" in permitted
        and print_name is not None
        and record.get("zhs_language") == "Chinese Simplified"
    ):
        return {
            "value": print_name,
            "status": "official",
            "provenance": _provenance(
                provider="mtgch",
                field=print_field,
                contributor=None,
                attribution=attributions["official"],
            ),
        }

    atomic_official = _nonempty(record.get("atomic_official_name"))
    if "official" in permitted and atomic_official is not None:
        return {
            "value": atomic_official,
            "status": "official",
            "provenance": _provenance(
                provider="mtgch",
                field="atomic_official_name",
                contributor=None,
                attribution=attributions["official"],
            ),
        }

    community = _nonempty(record.get("atomic_translated_name"))
    contributor = _nonempty(record.get("atomic_name_translated_from"))
    if "community" in permitted and community is not None and contributor is not None:
        return {
            "value": community,
            "status": "community",
            "provenance": _provenance(
                provider="mtgch",
                field="atomic_translated_name",
                contributor=contributor,
                attribution=attributions["community"],
            ),
        }

    return {
        "value": english_name,
        "status": "english_fallback",
        "provenance": _provenance(
            provider="scryfall",
            field=english_field,
            contributor=None,
            attribution=attributions["english_fallback"],
        ),
    }


def _localized_image(
    record: dict[str, Any],
    attributions: dict[str, str],
    permitted: frozenset[str],
    payloads: dict[str, bytes],
    used_payload_uris: set[str],
) -> dict[str, Any]:
    def chinese_image(status: str, contributor: str | None, uri: Any) -> dict[str, Any]:
        source_uri = _trusted_uri(
            uri,
            provider="mtgch",
            label=f"{status} Chinese image URI",
        )
        payload = payloads.get(source_uri)
        if payload is None:
            raise LocalizationBuildError(
                f"permitted {status} image lacks a synthetic payload: {source_uri}"
            )
        used_payload_uris.add(source_uri)
        sha256 = _sha256_bytes(payload)
        return {
            "source_uri": source_uri,
            "local_path": f"{PUBLIC_PREFIX}/images/{sha256}.webp",
            "sha256": sha256,
            "bytes": len(payload),
            "media_type": "image/webp",
            "status": status,
            "provenance": _provenance(
                provider="mtgch",
                field="zhs_image_uris.normal",
                contributor=contributor,
                attribution=attributions[status],
            ),
        }

    chinese_uri = _normal_uri(record, "zhs_image_uris")
    image_credit = _nonempty(record.get("zhs_image"))
    if "official" in permitted and image_credit == "官方" and chinese_uri is not None:
        return chinese_image("official", None, chinese_uri)
    if (
        "community" in permitted
        and image_credit is not None
        and image_credit != "官方"
        and chinese_uri is not None
    ):
        return chinese_image("community", image_credit, chinese_uri)

    return {
        "source_uri": _trusted_uri(
            _normal_uri(record, "image_uris"),
            provider="scryfall",
            label="English image URI",
        ),
        "local_path": None,
        "sha256": None,
        "bytes": None,
        "media_type": None,
        "status": "english_fallback",
        "provenance": _provenance(
            provider="scryfall",
            field="image_uris.normal",
            contributor=None,
            attribution=attributions["english_fallback"],
        ),
    }


def build_manifest(
    bundle: dict[str, Any],
    *,
    permitted_name_statuses: Collection[str] = (),
    permitted_image_statuses: Collection[str] = (),
) -> dict[str, Any]:
    """Resolve one synthetic MTGCH-shaped bundle without network access."""

    if not isinstance(bundle, dict):
        raise LocalizationBuildError("input bundle must be an object")
    if bundle.get("schema_version") != SCHEMA_VERSION:
        raise LocalizationBuildError(f"input schema_version must be {SCHEMA_VERSION}")
    if bundle.get("fixture_mode") is not True:
        raise LocalizationBuildError("fixture_mode must be true")
    permitted_names = frozenset(permitted_name_statuses)
    permitted_images = frozenset(permitted_image_statuses)
    unsupported_names = permitted_names - LOCALIZED_STATUSES
    unsupported_images = permitted_images - LOCALIZED_STATUSES
    if unsupported_names:
        raise LocalizationBuildError(
            "unsupported permitted name statuses: "
            + ", ".join(sorted(unsupported_names))
        )
    if unsupported_images:
        raise LocalizationBuildError(
            "unsupported permitted image statuses: "
            + ", ".join(sorted(unsupported_images))
        )
    source_snapshot = _source_snapshot(bundle)
    attributions = _attributions(bundle)
    payloads = _synthetic_payloads(bundle)
    records = bundle.get("cards")
    if not isinstance(records, list) or not records:
        raise LocalizationBuildError("cards must be a non-empty list")

    cards: list[dict[str, Any]] = []
    identities: set[tuple[str, str, int | None]] = set()
    used_payload_uris: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise LocalizationBuildError(f"card record must be an object: {record!r}")
        scryfall_id = _uuid(record, "id", "scryfall_id")
        oracle_id = _uuid(record, "oracle_id", "oracle_id")
        face_index = _face_index(record)
        identity = (oracle_id, scryfall_id, face_index)
        if identity in identities:
            raise LocalizationBuildError(
                "duplicate card identity: "
                f"oracle_id={oracle_id} scryfall_id={scryfall_id} face_index={face_index}"
            )
        identities.add(identity)
        english_field = "face_name" if face_index is not None else "name"
        english_name = _nonempty(record.get(english_field))
        if english_name is None:
            raise LocalizationBuildError(f"English {english_field} must be non-empty")
        cards.append(
            {
                "oracle_id": oracle_id,
                "scryfall_id": scryfall_id,
                "face_index": face_index,
                "english_name": english_name,
                "name": _localized_name(
                    record,
                    english_name,
                    english_field,
                    face_index,
                    attributions,
                    permitted_names,
                ),
                "image": _localized_image(
                    record,
                    attributions,
                    permitted_images,
                    payloads,
                    used_payload_uris,
                ),
            }
        )

    unused_payload_uris = set(payloads) - used_payload_uris
    if unused_payload_uris:
        raise LocalizationBuildError(
            "undeclared synthetic image payloads: " + ", ".join(sorted(unused_payload_uris))
        )

    cards.sort(
        key=lambda card: (
            card["oracle_id"],
            card["scryfall_id"],
            -1 if card["face_index"] is None else card["face_index"],
        )
    )
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "product": PRODUCT,
        "public_prefix": PUBLIC_PREFIX,
        "fixture_mode": True,
        "source_snapshot": source_snapshot,
        "cards": cards,
    }
    canonical = json.dumps(
        manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    manifest["subject_sha256"] = hashlib.sha256(canonical).hexdigest()
    return manifest


def _read_bundle(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LocalizationBuildError(f"cannot read input bundle {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LocalizationBuildError("input bundle must be an object")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _safe_local_path(value: Any) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise LocalizationBuildError(f"unsafe localization path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise LocalizationBuildError(f"unsafe localization path: {value!r}")
    return path


def verify_bundle(output_path: Path) -> dict[str, Any]:
    """Verify manifest identity, path closure, and every synthetic image byte."""

    output_path = output_path.resolve()
    manifest = _read_bundle(output_path / "manifest.json")
    expected_top = {
        "cards",
        "fixture_mode",
        "product",
        "public_prefix",
        "schema_version",
        "source_snapshot",
        "subject_sha256",
    }
    if set(manifest) != expected_top:
        raise LocalizationBuildError("localization manifest keys are invalid")
    if (
        manifest.get("schema_version") != SCHEMA_VERSION
        or manifest.get("product") != PRODUCT
        or manifest.get("public_prefix") != PUBLIC_PREFIX
        or manifest.get("fixture_mode") is not True
    ):
        raise LocalizationBuildError("localization manifest identity is invalid")
    _source_snapshot(manifest)
    subject = dict(manifest)
    recorded_subject_sha256 = subject.pop("subject_sha256", None)
    canonical = json.dumps(
        subject, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    if recorded_subject_sha256 != _sha256_bytes(canonical):
        raise LocalizationBuildError("localization subject SHA-256 mismatch")

    cards = manifest.get("cards")
    if not isinstance(cards, list) or not cards or any(
        not isinstance(card, dict) for card in cards
    ):
        raise LocalizationBuildError("localization manifest cards are invalid")
    expected_files = {output_path / "manifest.json"}
    prefix = PurePosixPath(PUBLIC_PREFIX)
    identities: list[tuple[str, str, int | None]] = []
    for card in cards:
        if set(card) != {
            "english_name",
            "face_index",
            "image",
            "name",
            "oracle_id",
            "scryfall_id",
        }:
            raise LocalizationBuildError("localized card keys are invalid")
        oracle_id = _uuid(card, "oracle_id", "oracle_id")
        scryfall_id = _uuid(card, "scryfall_id", "scryfall_id")
        face_index = card.get("face_index")
        if face_index is not None and (
            not isinstance(face_index, int)
            or isinstance(face_index, bool)
            or face_index < 0
        ):
            raise LocalizationBuildError(f"invalid manifest face_index: {face_index!r}")
        identities.append((oracle_id, scryfall_id, face_index))
        image = card.get("image")
        if not isinstance(image, dict) or set(image) != {
            "bytes",
            "local_path",
            "media_type",
            "provenance",
            "sha256",
            "source_uri",
            "status",
        }:
            raise LocalizationBuildError("localized image record is invalid")
        status = image.get("status")
        if status == "english_fallback":
            _trusted_uri(
                image.get("source_uri"),
                provider="scryfall",
                label="English image URI",
            )
            if any(
                image.get(field) is not None
                for field in ("bytes", "local_path", "media_type", "sha256")
            ):
                raise LocalizationBuildError("English fallback must not declare sidecar bytes")
            continue
        if status not in LOCALIZED_STATUSES:
            raise LocalizationBuildError(f"unsupported localized image status: {status!r}")
        _trusted_uri(
            image.get("source_uri"),
            provider="mtgch",
            label=f"{status} Chinese image URI",
        )
        local_path = _safe_local_path(image.get("local_path"))
        try:
            relative = local_path.relative_to(prefix)
        except ValueError as exc:
            raise LocalizationBuildError(
                f"localized image path escapes public prefix: {local_path}"
            ) from exc
        sha256 = image.get("sha256")
        if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise LocalizationBuildError(f"invalid localized image SHA-256: {local_path}")
        if local_path.as_posix() != f"{PUBLIC_PREFIX}/images/{sha256}.webp":
            raise LocalizationBuildError(f"localized image path is not content addressed: {local_path}")
        if image.get("media_type") != "image/webp":
            raise LocalizationBuildError(f"unsupported localized image media type: {local_path}")
        byte_count = image.get("bytes")
        if not isinstance(byte_count, int) or isinstance(byte_count, bool) or not 12 <= byte_count <= MAX_IMAGE_BYTES:
            raise LocalizationBuildError(f"invalid localized image byte count: {local_path}")
        file_path = output_path / Path(*relative.parts)
        expected_files.add(file_path)
        if file_path.is_symlink() or not file_path.is_file():
            raise LocalizationBuildError(f"declared localized image is missing: {local_path}")
        if file_path.stat().st_size != byte_count:
            raise LocalizationBuildError(f"localized image byte count mismatch: {local_path}")
        if _sha256_file(file_path) != sha256:
            raise LocalizationBuildError(f"localized image SHA-256 mismatch: {local_path}")
        _valid_webp(file_path.read_bytes(), local_path.as_posix())

    sorted_identities = sorted(
        identities,
        key=lambda identity: (
            identity[0],
            identity[1],
            -1 if identity[2] is None else identity[2],
        ),
    )
    if identities != sorted_identities or len(identities) != len(set(identities)):
        raise LocalizationBuildError("localization identities are not closed and sorted")
    actual_files: set[Path] = set()
    for path in output_path.rglob("*"):
        if path.is_symlink():
            raise LocalizationBuildError(f"symbolic links are prohibited: {path}")
        if path.is_file():
            actual_files.add(path)
    if actual_files != expected_files:
        raise LocalizationBuildError("localization bundle contains undeclared files")
    return manifest


def build_bundle(
    input_path: Path,
    output_path: Path,
    *,
    permitted_name_statuses: Collection[str] = (),
    permitted_image_statuses: Collection[str] = (),
) -> dict[str, Any]:
    """Build one atomic, repository-external bundle from synthetic fixtures."""

    repository_root = Path(__file__).resolve().parents[1]
    output_path = output_path.resolve()
    try:
        output_path.relative_to(repository_root)
    except ValueError:
        pass
    else:
        raise LocalizationBuildError("localization bundle output must be outside the repository")
    if output_path.exists():
        raise LocalizationBuildError(f"localization bundle output already exists: {output_path}")
    bundle = _read_bundle(input_path)
    payloads = _synthetic_payloads(bundle)
    manifest = build_manifest(
        bundle,
        permitted_name_statuses=permitted_name_statuses,
        permitted_image_statuses=permitted_image_statuses,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix="card-localization-", dir=output_path.parent)
    )
    try:
        for card in manifest["cards"]:
            image = card["image"]
            if image["status"] == "english_fallback":
                continue
            payload = payloads[image["source_uri"]]
            relative = PurePosixPath(image["local_path"]).relative_to(PUBLIC_PREFIX)
            destination = temporary / Path(*relative.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists() and destination.read_bytes() != payload:
                raise LocalizationBuildError(f"content-addressed image collision: {destination.name}")
            destination.write_bytes(payload)
        _write_json(temporary / "manifest.json", manifest)
        verify_bundle(temporary)
        temporary.replace(output_path)
        return manifest
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build an offline card-localization manifest from synthetic fixtures."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--synthetic-permit-name-status",
        action="append",
        choices=sorted(LOCALIZED_STATUSES),
        default=[],
        help="Exercise a name provenance branch with synthetic fixture data only.",
    )
    parser.add_argument(
        "--synthetic-permit-image-status",
        action="append",
        choices=sorted(LOCALIZED_STATUSES),
        default=[],
        help="Exercise an image provenance branch with synthetic fixture data only.",
    )
    args = parser.parse_args(argv)
    try:
        manifest = build_bundle(
            args.input,
            args.output,
            permitted_name_statuses=args.synthetic_permit_name_status,
            permitted_image_statuses=args.synthetic_permit_image_status,
        )
    except (LocalizationBuildError, OSError) as exc:
        parser.error(str(exc))
    print(
        "Card localization bundle built: "
        f"cards={len(manifest['cards'])} subject_sha256={manifest['subject_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
