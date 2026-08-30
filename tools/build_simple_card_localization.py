"""Build the flat MTGCH lookup and current-Landing Chinese image files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CARD_NAME_SOURCE = ROOT / "src" / "mtgmeta"
if str(CARD_NAME_SOURCE) not in sys.path:
    sys.path.insert(0, str(CARD_NAME_SOURCE))

from card_names import card_name_lookup_candidates  # noqa: E402


PUBLIC_PREFIX = "assets/card-localization"
LOOKUP_FILE = "cards.json"
MTGCH_RESULT_URL = "https://mtgch.com/api/v1/result"
MTGCH_IMAGE_HOST = "images.mtgch.com"
MTGCH_CARD_ORIGIN = "https://mtgch.com"
PAGE_SIZE = 1000
BATCH_SIZE = 20
FALLBACK_BATCH_SIZE = 5
FINAL_BATCH_SIZE = 1
API_REQUEST_INTERVAL_SECONDS = 2.1
IMAGE_REQUEST_INTERVAL_SECONDS = 1.0
MAX_PAGES = 100
MAX_IMAGE_BYTES = 5 * 1024 * 1024
HTTP_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "mtgo-data-simple-card-localization/1.0",
}
IMAGE_HEADERS = {
    "Accept": "image/webp,image/*;q=0.8,*/*;q=0.5",
    "User-Agent": "mtgo-data-simple-card-localization/1.0",
}
CARD_ARRAY_KEYS = frozenset(
    {
        "cards",
        "featured_cards",
        "key_cards",
        "main_deck",
        "mainboard",
        "side_deck",
        "sideboard",
    }
)
CARD_VALUE_KEYS = frozenset(
    {"deck_qty", "mean_qty", "qty", "quantity", "rate", "section", "typical_qty"}
)


class LocalizationBuildError(ValueError):
    """Indicate that the small localization bundle is invalid."""


def _read_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LocalizationBuildError(f"cannot read {label} {path}: {exc}") from exc


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _card_names(value: Any, parent_key: str | None = None) -> Iterable[str]:
    if isinstance(value, list):
        for item in value:
            yield from _card_names(item, parent_key)
        return
    if not isinstance(value, dict):
        return
    name = value.get("name")
    if (
        isinstance(name, str)
        and name
        and name == name.strip()
        and (parent_key in CARD_ARRAY_KEYS or bool(CARD_VALUE_KEYS & value.keys()))
    ):
        yield name
    for key, child in value.items():
        yield from _card_names(child, key)


def product_card_names(root: Path) -> list[str]:
    """Return exact English card names already emitted in public product JSON."""

    names: set[str] = set()
    for path in sorted((root / "stats").rglob("*.json")):
        names.update(_card_names(_read_json(path, "public product JSON")))
    return sorted(names)


def current_landing_names(root: Path) -> list[str]:
    """Return cards visible on each current default MTGO Landing."""

    names: set[str] = set()
    for current_path in sorted((root / "stats").glob("*/mtgo/landing/current.json")):
        current = _read_json(current_path, "current Landing")
        if not isinstance(current, dict):
            raise LocalizationBuildError(f"current Landing is not an object: {current_path}")
        environment = current.get("environment")
        rows = environment.get("rows") if isinstance(environment, dict) else None
        if not isinstance(rows, list):
            raise LocalizationBuildError(f"current Landing rows are missing: {current_path}")
        for row in rows:
            cards = row.get("key_cards") if isinstance(row, dict) else None
            if not isinstance(cards, list):
                raise LocalizationBuildError(f"current Landing key_cards are missing: {current_path}")
            names.update(_card_names(cards, "key_cards"))

        week = current.get("week")
        week_id = week.get("id") if isinstance(week, dict) else None
        if not isinstance(week_id, str) or not re.fullmatch(r"\d{4}-W\d{2}", week_id):
            raise LocalizationBuildError(f"current Landing week is invalid: {current_path}")
        feature_path = current_path.parent / "features" / f"{week_id}.json"
        feature = _read_json(feature_path, "current Landing feature week")
        features = feature.get("features") if isinstance(feature, dict) else None
        items = features.get("items") if isinstance(features, dict) else None
        if not isinstance(items, list):
            raise LocalizationBuildError(f"current Landing features are missing: {feature_path}")
        for item in items:
            cards = item.get("featured_cards") if isinstance(item, dict) else None
            if not isinstance(cards, list):
                raise LocalizationBuildError(f"featured_cards are missing: {feature_path}")
            names.update(_card_names(cards, "featured_cards"))
    return sorted(names)


def _trusted_mtgch_image(value: Any) -> str:
    if not isinstance(value, str):
        raise LocalizationBuildError(f"MTGCH image URL is not a string: {value!r}")
    parsed = urllib.parse.urlsplit(value)
    if (
        parsed.scheme != "https"
        or (parsed.hostname or "").lower() != MTGCH_IMAGE_HOST
        or not parsed.path.startswith("/zhs/")
    ):
        raise LocalizationBuildError(f"unsupported MTGCH Chinese image URL: {value}")
    return value


def _trusted_mtgch_card(value: Any) -> str:
    if not isinstance(value, str):
        raise LocalizationBuildError(f"MTGCH card URL is not a string: {value!r}")
    absolute = urllib.parse.urljoin(f"{MTGCH_CARD_ORIGIN}/", value)
    parsed = urllib.parse.urlsplit(absolute)
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != "mtgch.com"
        or parsed.query
        or parsed.fragment
        or not re.fullmatch(r"/card/[^/]+/[^/]+/?", parsed.path)
    ):
        raise LocalizationBuildError(f"unsupported MTGCH card URL: {value}")
    return absolute


def _download(url: str, headers: dict[str, str], maximum_bytes: int) -> bytes:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read(maximum_bytes + 1)
    if len(payload) > maximum_bytes:
        raise LocalizationBuildError(f"response exceeds {maximum_bytes} bytes: {url}")
    return payload


def _live_page(names: list[str], page: int) -> dict[str, Any]:
    time.sleep(API_REQUEST_INTERVAL_SECONDS)
    search = " or ".join(f"({name})" for name in names)
    query = urllib.parse.urlencode(
        {
            "q": search,
            "page": page,
            "page_size": PAGE_SIZE,
            "unique": "oracle_id",
            "priority_chinese": "true",
            "view": 1,
            "include_fav": "false",
        }
    )
    payload = _download(f"{MTGCH_RESULT_URL}?{query}", HTTP_HEADERS, 16 * 1024 * 1024)
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LocalizationBuildError(f"MTGCH page {page} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise LocalizationBuildError(f"MTGCH page {page} is not an object")
    return value


def _live_image(url: str) -> bytes:
    time.sleep(IMAGE_REQUEST_INTERVAL_SECONDS)
    return _download(url, IMAGE_HEADERS, MAX_IMAGE_BYTES)


def _records(value: dict[str, Any]) -> Iterable[dict[str, Any]]:
    yield value
    faces = value.get("other_faces")
    if isinstance(faces, list):
        for face in faces:
            if isinstance(face, dict):
                yield from _records(face)


def resolve_lookup(
    names: Iterable[str],
    fetch_page: Callable[[list[str], int], dict[str, Any]] = _live_page,
) -> dict[str, dict[str, str]]:
    """Resolve product names after the project's existing name normalization."""

    original_names = sorted(set(names))
    lookup_names = {
        original: card_name_lookup_candidates(original) for original in original_names
    }
    targets = sorted({candidate for candidates in lookup_names.values() for candidate in candidates})
    candidates: dict[str, list[tuple[bool, bool, str, str, str | None, str | None]]] = {}
    target_set = set(targets)

    def collect(batch_targets: list[str], batch_size: int) -> None:
        for start in range(0, len(batch_targets), batch_size):
            batch = batch_targets[start : start + batch_size]
            page = 1
            total_pages: int | None = None
            while total_pages is None or page <= total_pages:
                response = fetch_page(batch, page)
                response_page = response.get("page")
                response_total = response.get("total_pages")
                items = response.get("items")
                if (
                    response_page != page
                    or not isinstance(response_total, int)
                    or not 0 <= response_total <= MAX_PAGES
                    or not isinstance(items, list)
                ):
                    raise LocalizationBuildError(f"invalid MTGCH pagination at page {page}")
                if total_pages is None:
                    total_pages = response_total
                elif total_pages != response_total:
                    raise LocalizationBuildError("MTGCH total_pages changed during the build")
                for item in items:
                    if not isinstance(item, dict):
                        raise LocalizationBuildError(f"invalid MTGCH item at page {page}")
                    for record in _records(item):
                        english = record.get("display_name")
                        chinese = record.get("display_name_zh")
                        if (
                            english not in target_set
                            or not isinstance(chinese, str)
                            or not chinese.strip()
                        ):
                            continue
                        try:
                            image = _trusted_mtgch_image(record.get("image_url"))
                        except LocalizationBuildError:
                            image = None
                        try:
                            card_url = _trusted_mtgch_card(record.get("card_detail_url"))
                        except LocalizationBuildError:
                            card_url = None
                        identifier = str(record.get("id") or "")
                        candidates.setdefault(english, []).append(
                            (
                                image is None,
                                card_url is None,
                                identifier,
                                chinese.strip(),
                                image,
                                card_url,
                            )
                        )
                page += 1

    for batch_size in (BATCH_SIZE, FALLBACK_BATCH_SIZE, FINAL_BATCH_SIZE):
        missing = sorted(
            {
                candidate
                for candidates_for_name in lookup_names.values()
                if not any(candidate in candidates for candidate in candidates_for_name)
                for candidate in candidates_for_name
            }
        )
        if not missing:
            break
        collect(missing, batch_size)

    normalized_lookup: dict[str, dict[str, str]] = {}
    for normalized in sorted(candidates):
        _missing_image, _missing_card_url, _identifier, chinese, image, card_url = min(
            candidates[normalized]
        )
        entry = {"zh_name": chinese}
        if image is not None:
            entry["image_url"] = image
        if card_url is not None:
            entry["mtgch_url"] = card_url
        normalized_lookup[normalized] = entry
    lookup = {}
    for original, candidates_for_name in lookup_names.items():
        resolved = next(
            (
                normalized_lookup[candidate]
                for candidate in candidates_for_name
                if candidate in normalized_lookup
            ),
            None,
        )
        if resolved is not None:
            lookup[original] = dict(resolved)
    return lookup


def _valid_webp(payload: bytes, label: str) -> None:
    if len(payload) < 12 or payload[:4] != b"RIFF" or payload[8:12] != b"WEBP":
        raise LocalizationBuildError(f"MTGCH image is not WebP: {label}")


def _image_file_name(english_name: str) -> str:
    return f"{hashlib.sha256(english_name.encode('utf-8')).hexdigest()}.webp"


def build_bundle(
    root: Path,
    output: Path,
    *,
    fetch_page: Callable[[list[str], int], dict[str, Any]] = _live_page,
    fetch_image: Callable[[str], bytes] | None = None,
) -> dict[str, dict[str, str]]:
    """Build one repository-external flat lookup and current-Landing image set."""

    root = root.resolve()
    output = output.resolve()
    try:
        output.relative_to(root)
    except ValueError:
        pass
    else:
        raise LocalizationBuildError("localization output must be outside the repository")
    if output.exists():
        raise LocalizationBuildError(f"localization output already exists: {output}")

    product_names = product_card_names(root)
    landing_names = set(current_landing_names(root))
    lookup = resolve_lookup(product_names, fetch_page)
    image_fetch = fetch_image or _live_image
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="card-localization-", dir=output.parent))
    try:
        image_dir = temporary / "images"
        for english in sorted(landing_names & lookup.keys()):
            entry = lookup[english]
            if "image_url" not in entry:
                continue
            payload = image_fetch(entry["image_url"])
            _valid_webp(payload, english)
            image_dir.mkdir(parents=True, exist_ok=True)
            file_name = _image_file_name(english)
            (image_dir / file_name).write_bytes(payload)
            entry["local_image"] = f"{PUBLIC_PREFIX}/images/{file_name}"
        _write_json(temporary / LOOKUP_FILE, lookup)
        verify_bundle(root, temporary)
        temporary.replace(output)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return lookup


def _safe_local_image(value: Any) -> PurePosixPath:
    if not isinstance(value, str) or "\\" in value:
        raise LocalizationBuildError(f"invalid local image path: {value!r}")
    path = PurePosixPath(value)
    pattern = rf"^{re.escape(PUBLIC_PREFIX)}/images/[0-9a-f]{{64}}\.webp$"
    if path.is_absolute() or ".." in path.parts or not re.fullmatch(pattern, value):
        raise LocalizationBuildError(f"invalid local image path: {value!r}")
    return path


def verify_bundle(root: Path, output: Path) -> dict[str, dict[str, str]]:
    """Verify the flat map and every local image it declares."""

    del root  # The flat lookup intentionally has no second identity contract.
    output = output.resolve()
    lookup = _read_json(output / LOOKUP_FILE, "card-localization lookup")
    if not isinstance(lookup, dict):
        raise LocalizationBuildError("card-localization lookup is not an object")
    expected = {output / LOOKUP_FILE}
    for english, entry in lookup.items():
        if not isinstance(english, str) or not english or english != english.strip():
            raise LocalizationBuildError(f"invalid English lookup name: {english!r}")
        if not isinstance(entry, dict) or set(entry) not in (
            {"zh_name"},
            {"image_url", "zh_name"},
            {"image_url", "local_image", "zh_name"},
            {"mtgch_url", "zh_name"},
            {"image_url", "mtgch_url", "zh_name"},
            {"image_url", "local_image", "mtgch_url", "zh_name"},
        ):
            raise LocalizationBuildError(f"invalid lookup entry: {english}")
        chinese = entry.get("zh_name")
        if not isinstance(chinese, str) or not chinese.strip():
            raise LocalizationBuildError(f"invalid Chinese display name: {english}")
        if "image_url" in entry:
            _trusted_mtgch_image(entry["image_url"])
        if "mtgch_url" in entry:
            _trusted_mtgch_card(entry["mtgch_url"])
        if "local_image" not in entry:
            continue
        local_path = _safe_local_image(entry["local_image"])
        relative = local_path.relative_to(PUBLIC_PREFIX)
        file_path = output / Path(*relative.parts)
        expected.add(file_path)
        if file_path.is_symlink() or not file_path.is_file():
            raise LocalizationBuildError(f"declared local image is missing: {local_path}")
        payload = file_path.read_bytes()
        if len(payload) > MAX_IMAGE_BYTES:
            raise LocalizationBuildError(f"local image exceeds {MAX_IMAGE_BYTES} bytes: {local_path}")
        _valid_webp(payload, local_path.as_posix())

    actual = {path for path in output.rglob("*") if path.is_file()}
    if actual != expected:
        extras = sorted(path.relative_to(output).as_posix() for path in actual - expected)
        raise LocalizationBuildError("undeclared localization files: " + ", ".join(extras))
    return lookup


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("build", "verify"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    root = ROOT
    try:
        if args.command == "build":
            lookup = build_bundle(root, args.output)
        else:
            lookup = verify_bundle(root, args.output)
    except (LocalizationBuildError, OSError) as exc:
        parser.error(str(exc))
    local_count = sum("local_image" in entry for entry in lookup.values())
    print(f"Simple card localization: cards={len(lookup)} local_images={local_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
