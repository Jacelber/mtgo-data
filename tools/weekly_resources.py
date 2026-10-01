"""Selected Landing resource closure; preserve all unrelated cache entries."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from urllib.parse import quote

from tools import build_landing_card_image_cache as cache
from tools import build_simple_card_localization as localization
from tools import build_archetype_visuals as visuals


def replace_bytes(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".new")
    temporary.write_bytes(payload)
    temporary.replace(path)  # Never write through a retained hardlink.


def _art_crop_candidate(card, name, image_uris, face_index):
    """Use shared name/face ranking, with the environment's art-only contract."""
    uri = image_uris.get("art_crop") if isinstance(image_uris, dict) else None
    if uri is None:
        return None
    return {"name": name, "face_index": face_index, "source_image_uri": cache._valid_scryfall_image_uri(uri)}


def ensure(site: Path, page: dict, *, fetch_missing=False, fixture: Path | None = None):
    """Use existing resolvers/validators, requesting only selected missing art.

    A fixture supplies finite synthetic HTTP responses for isolated replay; it
    cannot fall through to live network. Normal live fetching is explicit.
    """
    fixture_data = json.loads(fixture.read_text(encoding="utf-8")) if fixture else None
    work = {"downloaded": [], "reused": [], "resolved_names": []}
    resolved = {}
    def card(name):
        if name not in resolved:
            if fixture_data is not None:
                value = fixture_data["cards"][name]
            elif fetch_missing:
                value = json.loads(cache._download("https://api.scryfall.com/cards/named?exact=" + quote(name),
                    cache.HTTP_HEADERS, maximum_bytes=1024 * 1024))
            else:
                raise ValueError(f"Missing selected card resource: {name}; use --fetch-missing-resources or an isolated fixture")
            if name not in {value.get("name"), *(face.get("name") for face in value.get("card_faces", []))}:
                raise ValueError("Resource response belongs to another card")
            resolved[name] = value
            work["resolved_names"].append(name)
        return resolved[name]
    def image(uri, path, validate):
        if path.is_file():
            validate(path.read_bytes())
            work["reused"].append(path.relative_to(site).as_posix())
            return
        if fixture_data is not None:
            source = (fixture.parent / fixture_data["images"][uri]).resolve()
            if not source.is_relative_to(fixture.parent.resolve()):
                raise ValueError("Fixture resource escapes its directory")
            payload = source.read_bytes()
        elif fetch_missing:
            payload = (localization._live_image(uri) if uri.startswith("https://images.mtgch.com/") else
                       cache._download(uri, cache.IMAGE_HEADERS, maximum_bytes=cache.MAX_IMAGE_BYTES))
        else:
            raise ValueError(f"Missing selected resource: {path.relative_to(site)}")
        validate(payload)
        replace_bytes(path, payload)
        work["downloaded"].append(path.relative_to(site).as_posix())
    format_id, week = page["format"], page["week"]["id"]
    names = set()
    for row in page["environment"]["rows"]:
        for item in row["key_cards"]:
            name = item["name"]
            names.add(name)
            target = site / f"assets/images/representative-cards/{format_id}/{visuals.image_slug(name)}.jpg"
            uri = ""
            if not target.is_file():
                value = card(name)
                key = cache._normalized_name(name)
                found = cache._bulk_lookup([value], {key}, candidate_factory=_art_crop_candidate).get(key)
                if found is None:
                    raise ValueError(f"No art_crop image for selected environment card {name}")
                uri = found["source_image_uri"]
            image(uri, target, lambda data: cache._valid_jpeg(data, name))
            visuals.require_art_crop_shape(target, format_id=format_id, identity=row["archetype_id"], card=name)
    manifest_path = site / "assets/card-cache/v1/manifest.json"
    original_manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {"cards": []}
    manifest = deepcopy(original_manifest)
    for name in sorted({c["name"] for f in page["features"]["items"] for c in f["featured_cards"]}):
        names.add(name)
        entry = next((c for c in manifest["cards"] if c["name"] == name), None)
        if entry is None:
            value = card(name)
            key = cache._normalized_name(name)
            found = cache._bulk_lookup([value], {key}).get(key)
            if found is None:
                raise ValueError(f"No normal image for selected Feature card {name}")
            index = found["face_index"]
            suffix = "" if index is None else f"-face-{index}"
            entry = {**found, "local_path": f"assets/card-cache/v1/images/{found['scryfall_id']}{suffix}.jpg",
                     "uses": [], "cache_source": "generated"}
            manifest["cards"].append(entry)
        relative = cache._safe_local_path(entry["local_path"])
        image(cache._valid_scryfall_image_uri(entry["source_image_uri"]), site / str(relative),
              lambda data: cache._valid_jpeg(data, name))
        data = (site / str(relative)).read_bytes()
        entry.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        use = next((u for u in entry["uses"] if u["format"] == format_id), None)
        if use is None:
            entry["uses"].append({"format": format_id, "weeks": [week]})
        elif week not in use["weeks"]:
            use["weeks"].append(week)
    if manifest != original_manifest or not manifest_path.is_file():
        replace_bytes(manifest_path, (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode())
    lookup_path = site / "assets/card-localization/cards.json"
    original_lookup = json.loads(lookup_path.read_text(encoding="utf-8")) if lookup_path.is_file() else {}
    lookup = deepcopy(original_lookup)
    missing_names = sorted(name for name in names if not (lookup.get(name) or lookup.get(name.split(" // ")[0])))
    if missing_names and fixture_data is not None:
        lookup.update({name: value for name, value in fixture_data.get("localizations", {}).items() if name in missing_names})
    elif missing_names and fetch_missing:
        lookup.update(localization.resolve_lookup(missing_names, localization._live_page))
    # A resolver-confirmed untranslated card uses the established English
    # fallback. Existing Chinese selections must have their chosen bytes.
    for name in sorted(names):
        entry = lookup.get(name) or lookup.get(name.split(" // ")[0])
        if not entry or not entry.get("image_url"):
            continue
        uri = localization._trusted_mtgch_image(entry["image_url"])
        relative = entry.get("local_image") or f"assets/card-localization/images/{localization._image_file_name(name)}"
        localization._safe_local_image(relative)
        image(uri, site / relative, lambda data: localization._valid_webp(data, name))
        entry["local_image"] = relative
    if lookup != original_lookup or not lookup_path.is_file():
        replace_bytes(lookup_path, (json.dumps(lookup, ensure_ascii=False, indent=2) + "\n").encode())
    return work
