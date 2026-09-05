"""Build the flat MTGCH lookup and current-Landing Chinese image files."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SOURCE = ROOT / "src"
CARD_NAME_SOURCE = PACKAGE_SOURCE / "mtgmeta"
if str(PACKAGE_SOURCE) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SOURCE))

from mtgmeta.card_names import card_name_lookup_candidates  # noqa: E402
from mtgmeta.catalog import complete_public_formats  # noqa: E402


PUBLIC_PREFIX = "assets/card-localization"
LOOKUP_FILE = "cards.json"
CACHE_SUBJECT_VERSION = "1.1.0"
SEED_SCHEMA_VERSION = "1.0.0"
SEED_FILE = "seed.json"
SEED_BUNDLE_DIRECTORY = "bundle"
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
RESOLVER_CONTRACT_FUNCTIONS = frozenset(
    {
        "_image_file_name",
        "_records",
        "_safe_local_image",
        "_trusted_mtgch_card",
        "_trusted_mtgch_image",
        "_valid_webp",
        "resolve_lookup",
    }
)
RESOLVER_CONTRACT_CONSTANTS = frozenset(
    {
        "BATCH_SIZE",
        "FALLBACK_BATCH_SIZE",
        "FINAL_BATCH_SIZE",
        "MAX_IMAGE_BYTES",
        "MAX_PAGES",
        "MTGCH_CARD_ORIGIN",
        "MTGCH_IMAGE_HOST",
        "MTGCH_RESULT_URL",
        "PAGE_SIZE",
    }
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git_file(root: Path, commit: str, relative: str) -> bytes:
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise LocalizationBuildError(f"invalid seed source commit: {commit!r}")
    ancestor = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", commit, "HEAD"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if ancestor.returncode != 0:
        raise LocalizationBuildError("seed source commit is not an ancestor of HEAD")
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"{commit}:{relative}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise LocalizationBuildError(
            f"cannot read seed compatibility input {relative} at {commit}"
        )
    return result.stdout


def _resolver_ast_sha256(builder_source: bytes) -> str:
    try:
        tree = ast.parse(builder_source.decode("utf-8"))
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise LocalizationBuildError("seed source builder is not valid UTF-8 Python") from exc
    selected: list[ast.stmt] = []
    found_functions: set[str] = set()
    found_constants: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in RESOLVER_CONTRACT_FUNCTIONS:
                selected.append(node)
                found_functions.add(node.name)
            continue
        if isinstance(node, ast.Assign):
            names = {
                target.id for target in node.targets if isinstance(target, ast.Name)
            }
            if names & RESOLVER_CONTRACT_CONSTANTS:
                selected.append(node)
                found_constants.update(names & RESOLVER_CONTRACT_CONSTANTS)
    if found_functions != RESOLVER_CONTRACT_FUNCTIONS:
        missing = sorted(RESOLVER_CONTRACT_FUNCTIONS - found_functions)
        raise LocalizationBuildError(
            "seed source builder lacks resolver functions: " + ", ".join(missing)
        )
    if found_constants != RESOLVER_CONTRACT_CONSTANTS:
        missing = sorted(RESOLVER_CONTRACT_CONSTANTS - found_constants)
        raise LocalizationBuildError(
            "seed source builder lacks resolver constants: " + ", ".join(missing)
        )
    contract = ast.Module(body=selected, type_ignores=[])
    return _sha256_bytes(
        ast.dump(contract, annotate_fields=True, include_attributes=False).encode("utf-8")
    )


def seed_compatibility(root: Path, source_commit: str | None = None) -> dict[str, str]:
    """Bind reusable mappings to only their direct resolver semantics."""

    if source_commit:
        builder = _git_file(root, source_commit, "tools/build_simple_card_localization.py")
        card_names = _git_file(root, source_commit, "src/mtgmeta/card_names.py")
        aliases = _git_file(
            root, source_commit, "src/mtgmeta/data/om1_spm_aliases.json"
        )
    else:
        builder = Path(__file__).read_bytes()
        card_names = (CARD_NAME_SOURCE / "card_names.py").read_bytes()
        aliases = (CARD_NAME_SOURCE / "data" / "om1_spm_aliases.json").read_bytes()
    contract = {
        "schema_version": SEED_SCHEMA_VERSION,
        "resolver_ast_sha256": _resolver_ast_sha256(builder),
        "card_names_sha256": _sha256_bytes(card_names),
        "card_name_aliases_sha256": _sha256_bytes(aliases),
    }
    canonical = json.dumps(contract, separators=(",", ":"), sort_keys=True)
    contract["compatibility_sha256"] = _sha256_bytes(canonical.encode("utf-8"))
    return contract


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


def _pages_statistics_exclusions(root: Path) -> tuple[str, ...] | None:
    policy = _read_json(root / "configs" / "pages_publication.json", "Pages policy")
    directories = policy.get("site_directories") if isinstance(policy, dict) else None
    patterns = policy.get("excluded_patterns") if isinstance(policy, dict) else None
    if (
        not isinstance(directories, list)
        or any(not isinstance(directory, str) for directory in directories)
        or not isinstance(patterns, list)
        or any(not isinstance(pattern, str) for pattern in patterns)
    ):
        raise LocalizationBuildError("Pages publication policy is incompatible")
    if "stats" not in directories:
        return None
    return tuple(patterns)


def product_card_names(root: Path) -> list[str]:
    """Return exact English card names already emitted in public product JSON."""

    patterns = _pages_statistics_exclusions(root)
    if patterns is None:
        return []
    names: set[str] = set()
    for definition in complete_public_formats(root):
        statistics_root = root / definition.mtgo.paths.statistics
        for path in sorted(statistics_root.rglob("*.json")):
            relative = path.relative_to(root).as_posix()
            if any(fnmatchcase(relative, pattern) for pattern in patterns):
                continue
            names.update(_card_names(_read_json(path, "public product JSON")))
    return sorted(names)


def current_landing_names(root: Path) -> list[str]:
    """Return cards visible on each current default MTGO Landing."""

    patterns = _pages_statistics_exclusions(root)
    if patterns is None:
        return []
    names: set[str] = set()
    current_paths = [
        root / definition.mtgo.paths.statistics / "landing" / "current.json"
        for definition in complete_public_formats(root)
    ]
    for current_path in sorted(current_paths):
        current_relative = current_path.relative_to(root).as_posix()
        if any(fnmatchcase(current_relative, pattern) for pattern in patterns):
            continue
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
        feature_relative = feature_path.relative_to(root).as_posix()
        if any(fnmatchcase(feature_relative, pattern) for pattern in patterns):
            continue
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


def cache_subject(root: Path) -> dict[str, Any]:
    """Bind one reusable bundle to its exact product and builder inputs."""

    subject = {
        "schema_version": CACHE_SUBJECT_VERSION,
        "product_card_names": product_card_names(root),
        "current_landing_names": current_landing_names(root),
        "builder_sha256": _sha256_file(Path(__file__)),
        "card_names_sha256": _sha256_file(CARD_NAME_SOURCE / "card_names.py"),
        "card_name_aliases_sha256": _sha256_file(
            CARD_NAME_SOURCE / "data" / "om1_spm_aliases.json"
        ),
    }
    canonical = json.dumps(
        subject,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    subject["subject_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return subject


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
        payload: bytes = response.read(maximum_bytes + 1)
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
                try:
                    response = fetch_page(batch, page)
                except urllib.error.HTTPError as exc:
                    next_batch_size = next(
                        (
                            size
                            for size in (FALLBACK_BATCH_SIZE, FINAL_BATCH_SIZE)
                            if size < len(batch)
                        ),
                        None,
                    )
                    if exc.code != 400 or page != 1 or next_batch_size is None:
                        raise
                    collect(batch, next_batch_size)
                    break
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
                        candidates.setdefault(english, []).append(  # type: ignore[arg-type]
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
    seed: Path | None = None,
    statistics: dict[str, int | str] | None = None,
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
    product_name_set = set(product_names)
    landing_names = set(current_landing_names(root))
    seed_lookup: dict[str, dict[str, str]] = {}
    seed_bundle: Path | None = None
    if seed is not None:
        seed_lookup = verify_seed(root, seed)
        seed_bundle = seed.resolve() / SEED_BUNDLE_DIRECTORY
    reusable_names = sorted(product_name_set & seed_lookup.keys())
    missing_names = sorted(product_name_set - seed_lookup.keys())
    api_requests = 0
    image_requests = 0

    def counted_page(names: list[str], page: int) -> dict[str, Any]:
        nonlocal api_requests
        api_requests += 1
        return fetch_page(names, page)

    lookup = {
        name: {key: value for key, value in seed_lookup[name].items() if key != "local_image"}
        for name in reusable_names
    }
    lookup.update(resolve_lookup(missing_names, counted_page))
    image_fetch = fetch_image or _live_image
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="card-localization-", dir=output.parent))
    try:
        image_dir = temporary / "images"
        reused_images = 0
        fetched_images = 0
        for english in sorted(landing_names & lookup.keys()):
            entry = lookup[english]
            if "image_url" not in entry:
                continue
            image_dir.mkdir(parents=True, exist_ok=True)
            file_name = _image_file_name(english)
            destination = image_dir / file_name
            seed_entry = seed_lookup.get(english, {})
            reusable_image = (
                seed_bundle is not None
                and seed_entry.get("image_url") == entry["image_url"]
                and isinstance(seed_entry.get("local_image"), str)
            )
            if reusable_image:
                assert seed_bundle is not None
                seed_relative = _safe_local_image(seed_entry["local_image"]).relative_to(
                    PUBLIC_PREFIX
                )
                source = seed_bundle / Path(*seed_relative.parts)
                shutil.copyfile(source, destination)
                _valid_webp(destination.read_bytes(), english)
                reused_images += 1
            else:
                image_requests += 1
                payload = image_fetch(entry["image_url"])
                _valid_webp(payload, english)
                destination.write_bytes(payload)
                fetched_images += 1
            entry["local_image"] = f"{PUBLIC_PREFIX}/images/{file_name}"
        _write_json(temporary / LOOKUP_FILE, lookup)
        verify_bundle(root, temporary)
        temporary.replace(output)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    if statistics is not None:
        statistics.update(
            {
                "desired_card_count": len(product_names),
                "seed_entry_count": len(seed_lookup),
                "reused_localization_count": len(reusable_names),
                "fetched_localization_count": len(lookup) - len(reusable_names),
                "removed_current_demand_count": len(set(seed_lookup) - product_name_set),
                "reused_image_count": reused_images,
                "fetched_image_count": fetched_images,
                "api_request_count": api_requests,
                "image_request_count": image_requests,
                "external_request_count": api_requests + image_requests,
                "final_card_count": len(lookup),
                "final_image_count": sum("local_image" in entry for entry in lookup.values()),
                "seed_used": "true" if seed is not None else "false",
            }
        )
    return lookup


def _safe_local_image(value: Any) -> PurePosixPath:
    if not isinstance(value, str) or "\\" in value:
        raise LocalizationBuildError(f"invalid local image path: {value!r}")
    path = PurePosixPath(value)
    pattern = rf"^{re.escape(PUBLIC_PREFIX)}/images/[0-9a-f]{{64}}\.webp$"
    if path.is_absolute() or ".." in path.parts or not re.fullmatch(pattern, value):
        raise LocalizationBuildError(f"invalid local image path: {value!r}")
    return path


def _verify_bundle_structure(output: Path) -> dict[str, dict[str, str]]:
    """Verify the flat map and every local image it declares."""

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

    for path in output.rglob("*"):
        if path.is_symlink():
            raise LocalizationBuildError(f"symbolic links are prohibited: {path}")
    actual = {path for path in output.rglob("*") if path.is_file()}
    if actual != expected:
        extras = sorted(path.relative_to(output).as_posix() for path in actual - expected)
        raise LocalizationBuildError("undeclared localization files: " + ", ".join(extras))
    return lookup


def verify_bundle(root: Path, output: Path) -> dict[str, dict[str, str]]:
    """Verify that one exact bundle stays inside the current public demand."""

    lookup = _verify_bundle_structure(output)
    desired = set(product_card_names(root))
    landing = set(current_landing_names(root))
    extras = sorted(set(lookup) - desired)
    if extras:
        raise LocalizationBuildError(
            "localization lookup contains names outside current public demand: "
            + ", ".join(extras)
        )
    outside_hot_set = sorted(
        name for name, entry in lookup.items() if "local_image" in entry and name not in landing
    )
    if outside_hot_set:
        raise LocalizationBuildError(
            "local images fall outside the current Landing hot set: "
            + ", ".join(outside_hot_set)
        )
    return lookup


def _bundle_manifest(bundle: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted(bundle.rglob("*")):
        if path.is_symlink():
            raise LocalizationBuildError(f"symbolic links are prohibited: {path}")
        if not path.is_file():
            continue
        records.append(
            {
                "path": path.relative_to(bundle).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
        )
    return records


def write_seed(root: Path, bundle: Path, output: Path) -> dict[str, Any]:
    """Create a current-demand-only seed from a structurally valid exact bundle."""

    root = root.resolve()
    bundle = bundle.resolve()
    output = output.resolve()
    try:
        output.relative_to(root)
    except ValueError:
        pass
    else:
        raise LocalizationBuildError("localization seed output must be outside the repository")
    if output.exists():
        raise LocalizationBuildError(f"localization seed output already exists: {output}")
    desired = set(product_card_names(root))
    landing = set(current_landing_names(root))
    source_lookup = _verify_bundle_structure(bundle)
    lookup: dict[str, dict[str, str]] = {}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="card-localization-seed-", dir=output.parent))
    try:
        seed_bundle = temporary / SEED_BUNDLE_DIRECTORY
        for english in sorted(desired & source_lookup.keys()):
            entry = dict(source_lookup[english])
            local_image = entry.pop("local_image", None)
            if english in landing and local_image is not None:
                relative = _safe_local_image(local_image).relative_to(PUBLIC_PREFIX)
                source = bundle / Path(*relative.parts)
                destination = seed_bundle / Path(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
                entry["local_image"] = local_image
            lookup[english] = entry
        seed_bundle.mkdir(parents=True, exist_ok=True)
        _write_json(seed_bundle / LOOKUP_FILE, lookup)
        _verify_bundle_structure(seed_bundle)
        manifest = {
            "schema_version": SEED_SCHEMA_VERSION,
            "compatibility": seed_compatibility(root),
            "source_subject_sha256": cache_subject(root)["subject_sha256"],
            "product_card_names": sorted(desired),
            "current_landing_names": sorted(landing),
            "bundle_files": _bundle_manifest(seed_bundle),
        }
        _write_json(temporary / SEED_FILE, manifest)
        temporary.replace(output)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    verify_seed(root, output)
    return manifest


def verify_seed(root: Path, output: Path) -> dict[str, dict[str, str]]:
    """Verify one seed snapshot and its direct resolver compatibility."""

    output = output.resolve()
    manifest = _read_json(output / SEED_FILE, "localization seed")
    expected_keys = {
        "schema_version",
        "compatibility",
        "source_subject_sha256",
        "product_card_names",
        "current_landing_names",
        "bundle_files",
    }
    if not isinstance(manifest, dict) or set(manifest) != expected_keys:
        raise LocalizationBuildError("localization seed manifest is malformed")
    if manifest["schema_version"] != SEED_SCHEMA_VERSION:
        raise LocalizationBuildError("localization seed schema is incompatible")
    if manifest["compatibility"] != seed_compatibility(root):
        raise LocalizationBuildError("localization seed resolver contract is incompatible")
    if re.fullmatch(r"[0-9a-f]{64}", str(manifest["source_subject_sha256"])) is None:
        raise LocalizationBuildError("localization seed source subject is invalid")
    product_names = manifest["product_card_names"]
    landing_names = manifest["current_landing_names"]
    if not isinstance(product_names, list) or not isinstance(landing_names, list):
        raise LocalizationBuildError("localization seed demand is malformed")
    if (
        any(not isinstance(name, str) or not name for name in product_names)
        or any(not isinstance(name, str) or not name for name in landing_names)
        or product_names != sorted(product_names)
        or landing_names != sorted(landing_names)
        or len(product_names) != len(set(product_names))
        or len(landing_names) != len(set(landing_names))
        or not set(landing_names) <= set(product_names)
    ):
        raise LocalizationBuildError("localization seed demand is malformed")
    seed_bundle = output / SEED_BUNDLE_DIRECTORY
    lookup = _verify_bundle_structure(seed_bundle)
    if not set(lookup) <= set(product_names):
        raise LocalizationBuildError("localization seed contains out-of-demand mappings")
    if any("local_image" in entry and name not in landing_names for name, entry in lookup.items()):
        raise LocalizationBuildError("localization seed contains an out-of-demand image")
    if manifest["bundle_files"] != _bundle_manifest(seed_bundle):
        raise LocalizationBuildError("localization seed bundle digest mismatch")
    actual = {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()}
    expected = {SEED_FILE} | {
        f"{SEED_BUNDLE_DIRECTORY}/{record['path']}" for record in manifest["bundle_files"]
    }
    if actual != expected:
        raise LocalizationBuildError("localization seed contains undeclared files")
    return lookup


def bootstrap_seed(
    root: Path, bundle: Path, source_commit: str, output: Path
) -> dict[str, Any]:
    """Convert a trusted legacy exact bundle only when resolver semantics match."""

    source_contract = seed_compatibility(root, source_commit)
    if source_contract != seed_compatibility(root):
        raise LocalizationBuildError("legacy exact bundle resolver contract is incompatible")
    return write_seed(root, bundle, output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subject_parser = subparsers.add_parser("subject")
    subject_parser.add_argument("--github-output", type=Path)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--output", type=Path, required=True)
    build_parser.add_argument("--seed", type=Path)
    build_parser.add_argument("--summary", type=Path)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--output", type=Path, required=True)
    seed_parser = subparsers.add_parser("seed")
    seed_parser.add_argument("--bundle", type=Path, required=True)
    seed_parser.add_argument("--output", type=Path, required=True)
    verify_seed_parser = subparsers.add_parser("verify-seed")
    verify_seed_parser.add_argument("--output", type=Path, required=True)
    bootstrap_parser = subparsers.add_parser("bootstrap-seed")
    bootstrap_parser.add_argument("--bundle", type=Path, required=True)
    bootstrap_parser.add_argument("--source-commit", required=True)
    bootstrap_parser.add_argument("--output", type=Path, required=True)
    bootstrap_parser.add_argument("--github-output", type=Path)
    args = parser.parse_args(argv)
    root = ROOT
    try:
        if args.command == "subject":
            subject = cache_subject(root)
            if args.github_output:
                with args.github_output.open("a", encoding="utf-8") as handle:
                    handle.write(f"sha256={subject['subject_sha256']}\n")
            print(json.dumps(subject, ensure_ascii=False, sort_keys=True))
            return 0
        if args.command == "build":
            statistics: dict[str, int | str] = {}
            lookup = build_bundle(
                root, args.output, seed=args.seed, statistics=statistics
            )
            if args.summary:
                with args.summary.open("a", encoding="utf-8") as handle:
                    handle.write("## Simple card localization\n\n")
                    for key, value in statistics.items():
                        handle.write(f"- {key}: `{value}`\n")
                    handle.write("\n")
            print(json.dumps(statistics, ensure_ascii=False, sort_keys=True))
        elif args.command == "verify":
            lookup = verify_bundle(root, args.output)
        elif args.command == "seed":
            manifest = write_seed(root, args.bundle, args.output)
            lookup = verify_seed(root, args.output)
            print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
        elif args.command == "verify-seed":
            lookup = verify_seed(root, args.output)
        else:
            try:
                manifest = bootstrap_seed(
                    root, args.bundle, args.source_commit, args.output
                )
            except (LocalizationBuildError, OSError) as exc:
                if args.output.exists():
                    shutil.rmtree(args.output, ignore_errors=True)
                if args.github_output:
                    with args.github_output.open("a", encoding="utf-8") as handle:
                        handle.write("usable=false\n")
                        handle.write(f"reason={str(exc).replace(chr(10), ' ')}\n")
                print(f"Trusted exact bootstrap rejected: {exc}")
                return 0
            if args.github_output:
                with args.github_output.open("a", encoding="utf-8") as handle:
                    handle.write("usable=true\n")
                    handle.write("reason=\n")
            lookup = verify_seed(root, args.output)
            print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    except (LocalizationBuildError, OSError) as exc:
        parser.error(str(exc))
    local_count = sum("local_image" in entry for entry in lookup.values())
    print(f"Simple card localization: cards={len(lookup)} local_images={local_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
