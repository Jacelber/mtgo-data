"""Build a verified four-week Landing card-image cache outside Git history."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import shutil
import sys
import tempfile
import unicodedata
import urllib.request
import uuid
from collections.abc import Iterable
from datetime import date, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from urllib.parse import urlsplit


CARD_NAME_SOURCE = Path(__file__).resolve().parents[1] / "src" / "mtgmeta"
if str(CARD_NAME_SOURCE) not in sys.path:
    sys.path.insert(0, str(CARD_NAME_SOURCE))

from card_names import card_name_lookup_candidates  # noqa: E402


CACHE_SCHEMA_VERSION = "1.1.0"
CACHE_PRODUCT = "mtgo-landing-card-image-cache"
CACHE_PUBLIC_PREFIX = "assets/card-cache/v1"
CACHE_WINDOW_WEEKS = 4
SUPPORTED_FORMATS = ("standard", "modern")
SCRYFALL_BULK_DEFINITION = "https://api.scryfall.com/bulk-data/oracle-cards"
HTTP_HEADERS = {
    "Accept": "application/json;q=0.9,*/*;q=0.8",
    "User-Agent": "mtgo-data-landing-card-image-cache/1.0",
}
IMAGE_HEADERS = {
    "Accept": "image/jpeg,image/*;q=0.8,*/*;q=0.5",
    "User-Agent": "mtgo-data-landing-card-image-cache/1.0",
}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_BULK_BYTES = 1024 * 1024 * 1024
class CacheBuildError(ValueError):
    """Indicate that the rolling image cache cannot be built safely."""


def _read_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CacheBuildError(f"cannot read {label} {path}: {exc}") from exc


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_name(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def _week_monday(week_id: str) -> date:
    match = re.fullmatch(r"([0-9]{4})-W([0-9]{2})", week_id)
    if not match:
        raise CacheBuildError(f"invalid ISO week: {week_id!r}")
    try:
        return date.fromisocalendar(int(match.group(1)), int(match.group(2)), 1)
    except ValueError as exc:
        raise CacheBuildError(f"invalid ISO week: {week_id!r}") from exc


def _week_id(value: date) -> str:
    year, week, _weekday = value.isocalendar()
    return f"{year:04d}-W{week:02d}"


def _safe_feature_file(value: Any, week: str) -> str:
    if not isinstance(value, str) or PurePosixPath(value).name != value:
        raise CacheBuildError(f"unsafe feature file for {week}: {value!r}")
    if value != f"{week}.json":
        raise CacheBuildError(f"feature file does not match week {week}: {value!r}")
    return value


def _feature_names(path: Path, format_name: str, week: str) -> list[str]:
    document = _read_json(path, "Landing feature week")
    if not isinstance(document, dict):
        raise CacheBuildError(f"Landing feature week is not an object: {path}")
    if document.get("format") != format_name:
        raise CacheBuildError(f"Landing feature format mismatch: {path}")
    week_value = document.get("week")
    if not isinstance(week_value, dict) or week_value.get("id") != week:
        raise CacheBuildError(f"Landing feature week mismatch: {path}")
    features = document.get("features")
    items = features.get("items") if isinstance(features, dict) else None
    if not isinstance(items, list):
        raise CacheBuildError(f"Landing feature items are not a list: {path}")
    names: list[str] = []
    for item in items:
        cards = item.get("featured_cards") if isinstance(item, dict) else None
        if not isinstance(cards, list):
            raise CacheBuildError(f"Landing feature cards are not a list: {path}")
        for card in cards:
            name = card.get("name") if isinstance(card, dict) else None
            if not isinstance(name, str) or not name.strip() or name != name.strip():
                raise CacheBuildError(f"invalid featured card name in {path}: {name!r}")
            names.append(name)
    return names


def cache_subject(
    root: Path,
    *,
    formats: tuple[str, ...] = SUPPORTED_FORMATS,
) -> dict[str, Any]:
    """Return the deterministic rolling-window card set and its subject digest."""

    root = root.resolve()
    uses: dict[str, dict[str, Any]] = {}
    format_records: list[dict[str, Any]] = []
    for format_name in formats:
        index_path = root / f"stats/{format_name}/mtgo/landing/features/index.json"
        index = _read_json(index_path, "Landing feature index")
        weeks = index.get("weeks") if isinstance(index, dict) else None
        if not isinstance(weeks, list) or not weeks:
            raise CacheBuildError(f"Landing feature index has no weeks: {index_path}")
        parsed: list[tuple[date, dict[str, Any]]] = []
        for record in weeks:
            if not isinstance(record, dict) or not isinstance(record.get("week"), str):
                raise CacheBuildError(f"invalid Landing feature index record: {index_path}")
            week = record["week"]
            parsed.append((_week_monday(week), record))
        parsed.sort(key=lambda item: item[0], reverse=True)
        anchor_date, anchor = parsed[0]
        minimum = anchor_date - timedelta(weeks=CACHE_WINDOW_WEEKS - 1)
        selected = [item for item in parsed if minimum <= item[0] <= anchor_date]
        selected_weeks: list[str] = []
        for _start, record in selected:
            week = record["week"]
            selected_weeks.append(week)
            file_name = _safe_feature_file(record.get("file"), week)
            feature_path = index_path.parent / file_name
            for name in _feature_names(feature_path, format_name, week):
                key = _normalized_name(name)
                item = uses.setdefault(key, {"name": name, "formats": {}})
                if item["name"] != name:
                    raise CacheBuildError(
                        f"card names collide after normalization: {item['name']!r}, {name!r}"
                    )
                item["formats"].setdefault(format_name, set()).add(week)
        format_records.append(
            {
                "anchor_week": anchor["week"],
                "format": format_name,
                "selected_weeks": selected_weeks,
                "window_end": anchor["week"],
                "window_start": _week_id(minimum),
            }
        )

    cards: list[dict[str, Any]] = []
    for key in sorted(uses):
        item = uses[key]
        record = {
            "name": item["name"],
            "uses": [
                {"format": format_name, "weeks": sorted(weeks, reverse=True)}
                for format_name, weeks in sorted(item["formats"].items())
            ],
        }
        cards.append(record)
    subject: dict[str, Any] = {
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        "cards": cards,
        "formats": format_records,
        "window_size_weeks": CACHE_WINDOW_WEEKS,
    }
    canonical = json.dumps(subject, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    subject["subject_sha256"] = _sha256_bytes(canonical.encode("utf-8"))
    return subject


def _valid_scryfall_image_uri(value: Any) -> str:
    if not isinstance(value, str):
        raise CacheBuildError(f"Scryfall image URI is not a string: {value!r}")
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host.endswith(".scryfall.io"):
        raise CacheBuildError(f"untrusted Scryfall image URI: {value}")
    if not parsed.path.lower().endswith((".jpg", ".jpeg")):
        raise CacheBuildError(f"unsupported Scryfall image type: {value}")
    return value


def _candidate(
    card: dict[str, Any], name: str, image_uris: Any, face_index: int | None
) -> dict[str, Any] | None:
    uri = image_uris.get("normal") if isinstance(image_uris, dict) else None
    if uri is None:
        return None
    try:
        scryfall_id = str(uuid.UUID(str(card.get("id"))))
    except (ValueError, AttributeError) as exc:
        raise CacheBuildError(f"invalid Scryfall card id for {name!r}") from exc
    oracle_value = card.get("oracle_id")
    try:
        oracle_id = str(uuid.UUID(str(oracle_value))) if oracle_value is not None else None
    except (ValueError, AttributeError) as exc:
        raise CacheBuildError(f"invalid Scryfall oracle id for {name!r}") from exc
    return {
        "face_index": face_index,
        "name": name,
        "oracle_id": oracle_id,
        "scryfall_id": scryfall_id,
        "source_image_uri": _valid_scryfall_image_uri(uri),
    }


def _bulk_lookup(
    cards: Iterable[Any], requested_names: set[str]
) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    ranks: dict[str, int] = {}

    def add(value: dict[str, Any], rank: int) -> None:
        key = _normalized_name(value["name"])
        if key not in requested_names:
            return
        previous = lookup.get(key)
        previous_rank = ranks.get(key)
        if previous is not None and previous_rank is not None and rank > previous_rank:
            return
        if previous is not None and previous_rank == rank and previous != value:
            raise CacheBuildError(f"ambiguous Scryfall card name: {value['name']}")
        lookup[key] = value
        ranks[key] = rank

    for raw in cards:
        if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
            continue
        if raw.get("layout") == "art_series":
            continue
        top = _candidate(raw, raw["name"], raw.get("image_uris"), None)
        if top is not None:
            add(top, 0)
        faces = raw.get("card_faces")
        if isinstance(faces, list):
            first: dict[str, Any] | None = None
            for index, face in enumerate(faces):
                if not isinstance(face, dict) or not isinstance(face.get("name"), str):
                    continue
                value = _candidate(raw, face["name"], face.get("image_uris"), index)
                if value is None and top is not None:
                    value = {**top, "name": face["name"]}
                if value is not None:
                    if first is None:
                        first = value
                    add(value, 1)
            if top is None and first is not None:
                combined = {**first, "name": raw["name"]}
                add(combined, 0)
    return lookup


def _bulk_cards(path: Path) -> Iterable[Any]:
    with path.open("rb") as handle:
        compressed = handle.read(2) == b"\x1f\x8b"
    if not compressed:
        value = _read_json(path, "Scryfall oracle-cards bulk data")
        if not isinstance(value, list):
            raise CacheBuildError("Scryfall oracle-cards bulk data is not a list")
        return value

    def records() -> Iterable[Any]:
        try:
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise CacheBuildError(
                            f"invalid Scryfall JSONL record at line {line_number}: {exc}"
                        ) from exc
        except OSError as exc:
            raise CacheBuildError(f"cannot read Scryfall JSONL bulk data: {exc}") from exc

    return records()


def _download(url: str, headers: dict[str, str], *, maximum_bytes: int) -> bytes:
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read(maximum_bytes + 1)
    except OSError as exc:
        raise CacheBuildError(f"download failed: {url}: {exc}") from exc
    if len(payload) > maximum_bytes:
        raise CacheBuildError(f"download exceeds {maximum_bytes} bytes: {url}")
    return payload


def _download_file(
    url: str, headers: dict[str, str], destination: Path, *, maximum_bytes: int
) -> None:
    request = urllib.request.Request(url, headers=headers)
    total = 0
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            with destination.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > maximum_bytes:
                        raise CacheBuildError(
                            f"download exceeds {maximum_bytes} bytes: {url}"
                        )
                    handle.write(chunk)
    except OSError as exc:
        raise CacheBuildError(f"download failed: {url}: {exc}") from exc


def _live_bulk_data(temp_root: Path) -> Path:
    definition = json.loads(
        _download(SCRYFALL_BULK_DEFINITION, HTTP_HEADERS, maximum_bytes=1024 * 1024)
    )
    download_uri = (
        definition.get("jsonl_download_uri") if isinstance(definition, dict) else None
    )
    parsed = urlsplit(download_uri) if isinstance(download_uri, str) else None
    if (
        not isinstance(definition, dict)
        or definition.get("object") != "bulk_data"
        or definition.get("type") != "oracle_cards"
        or parsed is None
        or parsed.scheme != "https"
        or not (parsed.hostname or "").lower().endswith(".scryfall.io")
        or not parsed.path.endswith(".jsonl.gz")
    ):
        raise CacheBuildError(
            "Scryfall bulk definition lacks a trusted oracle-cards JSONL download"
        )
    path = temp_root / "oracle-cards.jsonl.gz"
    _download_file(download_uri, HTTP_HEADERS, path, maximum_bytes=MAX_BULK_BYTES)
    return path


def _valid_jpeg(value: bytes, name: str) -> None:
    if len(value) > MAX_IMAGE_BYTES:
        raise CacheBuildError(f"card image exceeds {MAX_IMAGE_BYTES} bytes: {name}")
    if len(value) < 8 or not value.startswith(b"\xff\xd8\xff") or not value.endswith(b"\xff\xd9"):
        raise CacheBuildError(f"card image is not a JPEG: {name}")


def build_cache_bundle(
    root: Path,
    output: Path,
    *,
    bulk_data_path: Path | None = None,
    fetch_image: Callable[[str], bytes] | None = None,
) -> dict[str, Any]:
    """Build an atomic cache bundle from repository Landing documents."""

    root = root.resolve()
    output = output.resolve()
    try:
        output.relative_to(root)
    except ValueError:
        pass
    else:
        raise CacheBuildError("cache bundle output must be outside the repository")
    if output.exists():
        raise CacheBuildError(f"cache bundle output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="landing-card-cache-", dir=output.parent))
    try:
        subject = cache_subject(root)
        unresolved = subject["cards"]
        bulk_sha256: str | None = None
        lookup: dict[str, dict[str, Any]] = {}
        if unresolved:
            downloaded_bulk = bulk_data_path is None
            bulk_path = (
                bulk_data_path.resolve()
                if bulk_data_path
                else _live_bulk_data(temporary)
            )
            bulk_sha256 = _sha256_file(bulk_path)
            lookup_names = {
                card["name"]: tuple(
                    _normalized_name(candidate)
                    for candidate in card_name_lookup_candidates(card["name"])
                )
                for card in unresolved
            }
            requested_names = {
                candidate
                for candidates in lookup_names.values()
                for candidate in candidates
            }
            lookup = _bulk_lookup(_bulk_cards(bulk_path), requested_names)
            if downloaded_bulk:
                bulk_path.unlink()
            missing = [
                name
                for name, candidates in lookup_names.items()
                if not any(candidate in lookup for candidate in candidates)
            ]
            if missing:
                raise CacheBuildError("unresolved featured cards: " + ", ".join(missing))

        image_fetch = fetch_image or (
            lambda url: _download(url, IMAGE_HEADERS, maximum_bytes=MAX_IMAGE_BYTES)
        )
        image_dir = temporary / "images"
        entries: list[dict[str, Any]] = []
        for card in subject["cards"]:
            common = {"name": card["name"], "uses": card["uses"]}
            resolved = next(
                lookup[candidate]
                for candidate in lookup_names[card["name"]]
                if candidate in lookup
            )
            suffix = "" if resolved["face_index"] is None else f"-face-{resolved['face_index']}"
            file_name = f"{resolved['scryfall_id']}{suffix}.jpg"
            payload = image_fetch(resolved["source_image_uri"])
            _valid_jpeg(payload, card["name"])
            image_dir.mkdir(parents=True, exist_ok=True)
            image_path = image_dir / file_name
            image_path.write_bytes(payload)
            entries.append(
                {
                    **common,
                    "bytes": len(payload),
                    "cache_source": "generated",
                    "face_index": resolved["face_index"],
                    "local_path": f"{CACHE_PUBLIC_PREFIX}/images/{file_name}",
                    "oracle_id": resolved["oracle_id"],
                    "scryfall_id": resolved["scryfall_id"],
                    "sha256": _sha256_bytes(payload),
                    "source_image_uri": resolved["source_image_uri"],
                }
            )
        manifest = {
            "bulk_data_sha256": bulk_sha256,
            "cards": entries,
            "formats": subject["formats"],
            "product": CACHE_PRODUCT,
            "public_prefix": CACHE_PUBLIC_PREFIX,
            "schema_version": CACHE_SCHEMA_VERSION,
            "subject_sha256": subject["subject_sha256"],
            "window_size_weeks": CACHE_WINDOW_WEEKS,
        }
        _write_json(temporary / "manifest.json", manifest)
        verify_cache_bundle(root, temporary)
        temporary.replace(output)
        return manifest
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def _safe_local_path(value: Any) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise CacheBuildError(f"unsafe cache path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise CacheBuildError(f"unsafe cache path: {value!r}")
    return path


def verify_cache_bundle(root: Path, cache_root: Path) -> dict[str, Any]:
    """Verify subject identity, path closure, and every declared cache byte."""

    root = root.resolve()
    cache_root = cache_root.resolve()
    manifest = _read_json(cache_root / "manifest.json", "card-image cache manifest")
    if not isinstance(manifest, dict):
        raise CacheBuildError("card-image cache manifest is not an object")
    expected_top = {
        "bulk_data_sha256",
        "cards",
        "formats",
        "product",
        "public_prefix",
        "schema_version",
        "subject_sha256",
        "window_size_weeks",
    }
    if set(manifest) != expected_top:
        raise CacheBuildError("card-image cache manifest keys are invalid")
    if manifest.get("schema_version") != CACHE_SCHEMA_VERSION:
        raise CacheBuildError("unsupported card-image cache schema_version")
    if manifest.get("product") != CACHE_PRODUCT or manifest.get("public_prefix") != CACHE_PUBLIC_PREFIX:
        raise CacheBuildError("card-image cache identity is invalid")
    bulk_sha256 = manifest.get("bulk_data_sha256")
    if bulk_sha256 is not None and not re.fullmatch(r"[0-9a-f]{64}", str(bulk_sha256)):
        raise CacheBuildError("card-image cache bulk-data SHA-256 is invalid")
    if manifest.get("window_size_weeks") != CACHE_WINDOW_WEEKS:
        raise CacheBuildError("card-image cache window size is invalid")
    subject = cache_subject(root)
    if manifest.get("subject_sha256") != subject["subject_sha256"]:
        raise CacheBuildError("card-image cache subject SHA-256 mismatch")
    if manifest.get("formats") != subject["formats"]:
        raise CacheBuildError("card-image cache format window mismatch")
    subject_cards = {card["name"]: card for card in subject["cards"]}
    cards = manifest.get("cards")
    if not isinstance(cards, list) or any(not isinstance(card, dict) for card in cards):
        raise CacheBuildError("card-image cache cards are invalid")
    if [card.get("name") for card in cards] != list(subject_cards):
        raise CacheBuildError("card-image cache card closure mismatch")

    expected_bundle_files = {cache_root / "manifest.json"}
    generated_count = 0
    seen_local_paths: set[str] = set()
    for card in cards:
        if set(card) != {
            "bytes",
            "cache_source",
            "face_index",
            "local_path",
            "name",
            "oracle_id",
            "scryfall_id",
            "sha256",
            "source_image_uri",
            "uses",
        }:
            raise CacheBuildError("card-image cache card keys are invalid")
        subject_card = subject_cards[card["name"]]
        if card.get("uses") != subject_card["uses"]:
            raise CacheBuildError("card-image cache usage mismatch")
        local_path = _safe_local_path(card.get("local_path"))
        local_path_text = local_path.as_posix()
        if local_path_text in seen_local_paths:
            raise CacheBuildError(f"duplicate cache image path: {local_path}")
        seen_local_paths.add(local_path_text)
        byte_count = card.get("bytes")
        if (
            not isinstance(byte_count, int)
            or isinstance(byte_count, bool)
            or not 8 <= byte_count <= MAX_IMAGE_BYTES
        ):
            raise CacheBuildError(f"invalid cache byte count: {local_path}")
        if not isinstance(card.get("sha256"), str) or not re.fullmatch(
            r"[0-9a-f]{64}", card["sha256"]
        ):
            raise CacheBuildError(f"invalid cache SHA-256: {local_path}")
        if card.get("cache_source") != "generated":
            raise CacheBuildError(f"unsupported cache source: {card.get('cache_source')!r}")
        generated_count += 1
        prefix = PurePosixPath(CACHE_PUBLIC_PREFIX)
        try:
            relative = local_path.relative_to(prefix)
        except ValueError as exc:
            raise CacheBuildError(f"generated cache path escapes public prefix: {local_path}") from exc
        file_path = cache_root / Path(*relative.parts)
        expected_bundle_files.add(file_path)
        _valid_scryfall_image_uri(card.get("source_image_uri"))
        try:
            scryfall_id = str(uuid.UUID(str(card.get("scryfall_id"))))
            uuid.UUID(str(card.get("oracle_id")))
        except (ValueError, AttributeError) as exc:
            raise CacheBuildError(f"invalid generated card identity: {card['name']}") from exc
        face_index = card.get("face_index")
        if face_index is not None and (
            not isinstance(face_index, int)
            or isinstance(face_index, bool)
            or face_index < 0
        ):
            raise CacheBuildError(f"invalid face index: {card['name']}")
        suffix = "" if face_index is None else f"-face-{face_index}"
        expected_path = f"{CACHE_PUBLIC_PREFIX}/images/{scryfall_id}{suffix}.jpg"
        if local_path_text != expected_path:
            raise CacheBuildError(f"generated cache path does not match identity: {local_path}")
        if file_path.is_symlink() or not file_path.is_file():
            raise CacheBuildError(f"declared cache image is missing: {local_path}")
        if file_path.stat().st_size != card.get("bytes"):
            raise CacheBuildError(f"byte count mismatch: {local_path}")
        if _sha256_file(file_path) != card.get("sha256"):
            raise CacheBuildError(f"SHA-256 mismatch: {local_path}")
        _valid_jpeg(file_path.read_bytes(), card["name"])

    if (generated_count == 0) != (bulk_sha256 is None):
        raise CacheBuildError("card-image cache bulk-data evidence is inconsistent")

    actual_bundle_files: set[Path] = set()
    for path in cache_root.rglob("*"):
        if path.is_symlink():
            raise CacheBuildError(f"symbolic links are prohibited in cache bundle: {path}")
        if path.is_file():
            actual_bundle_files.add(path)
    if actual_bundle_files != expected_bundle_files:
        raise CacheBuildError("card-image cache bundle contains undeclared files")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("subject", "build", "verify"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--bulk-data", type=Path)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "subject":
            subject = cache_subject(args.root)
            print(json.dumps(subject, ensure_ascii=False, sort_keys=True))
            if args.github_output:
                with args.github_output.open("a", encoding="utf-8") as handle:
                    handle.write(f"sha256={subject['subject_sha256']}\n")
                    handle.write(f"card-count={len(subject['cards'])}\n")
        elif args.command == "build":
            if args.output is None:
                raise CacheBuildError("build requires --output")
            manifest = build_cache_bundle(
                args.root,
                args.output,
                bulk_data_path=args.bulk_data,
            )
            print(
                "Landing card-image cache: "
                f"cards={len(manifest['cards'])} subject={manifest['subject_sha256']}"
            )
        else:
            if args.output is None:
                raise CacheBuildError("verify requires --output")
            manifest = verify_cache_bundle(args.root, args.output)
            print(
                "Landing card-image cache verified: "
                f"cards={len(manifest['cards'])} subject={manifest['subject_sha256']}"
            )
    except (CacheBuildError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"Landing card-image cache error: {exc}")
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
