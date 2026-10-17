"""Reuse local resource bundles, then trusted caches, then missing requests."""
from __future__ import annotations

import json
import argparse
import re
from pathlib import Path
import shutil
import tempfile
from urllib.parse import urlencode, quote

from mtgmeta.generation_progress import files
from mtgmeta.resource_progress import digest, save

from tools import build_simple_card_localization as names
from tools import build_landing_card_image_cache as images
from tools import select_trusted_pages_artifact as selection
from tools.delivery.github import GitHub


def merge_localization(root, sources, destination):
    """Earlier sources retain their reviewed image identity; later ones fill gaps."""
    destination = destination / digest({"sources": [files(source, ["**/*"]) for source in sources],
        "subject": names.cache_subject(root), "compatibility": names.seed_compatibility(root)})
    seed = destination / "seed"
    if seed.is_dir():
        names.verify_seed(root, seed)
        return seed
    bundle = destination / "bundle-input"
    bundle.mkdir(parents=True, exist_ok=True)
    lookup = {}
    desired, hot = set(names.product_card_names(root)), set(names.current_landing_names(root))
    for source in sources:
        if (source / names.SEED_FILE).is_file():
            source_lookup = names.verify_seed(root, source)
            source = source / names.SEED_BUNDLE_DIRECTORY
        else:
            source_lookup = names._verify_bundle_structure(source)
        for name, value in source_lookup.items():
            if name not in desired:
                continue
            if name in lookup:
                # Fill a missing image only when it is the already-selected image.
                if ("local_image" in lookup[name] or "local_image" not in value
                        or value.get("image_url") != lookup[name].get("image_url")):
                    continue
                value = {**lookup[name], "local_image": value["local_image"]}
            entry = dict(value)
            image = entry.pop("local_image", None)
            if image and name in hot:
                relative = names._safe_local_image(image).relative_to(names.PUBLIC_PREFIX)
                target = bundle / Path(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / Path(*relative.parts), target)
                entry["local_image"] = image
            lookup[name] = entry
    names._write_json(bundle / names.LOOKUP_FILE, lookup)
    if not seed.exists():
        names.write_seed(root, bundle, seed)
    return seed


def complete_localization(root, source):
    lookup = names._verify_bundle_structure(source)
    return (set(names.product_card_names(root)) <= set(lookup)
            and all("image_url" not in lookup[name] or "local_image" in lookup[name]
                    for name in names.current_landing_names(root) if name in lookup))


def trusted_cache(repository, work, *, exact=None, prefix=None):
    client = GitHub(repository)
    class API:
        def get(self, path, query=None):
            return client.api(path.lstrip("/") + ("?" + urlencode(query) if query else ""))
    candidates = selection._artifacts(API(), repository, exact)
    runs = {}
    def get_run(identifier):
        if identifier not in runs:
            runs[identifier] = client.api(f"repos/{repository}/actions/runs/{identifier}")
        return runs[identifier]
    selected, errors = [], []
    for path in selection.TRUSTED_WORKFLOW_PATHS:
        try:
            workflow = client.api(f"repos/{repository}/actions/workflows/{quote(path, safe='')}")
            item = selection.select_trusted_artifact(candidates, repository=repository,
                workflow_id=workflow["id"], workflow_path=path, get_run=get_run,
                name_matches=lambda value: value == exact if exact else re.fullmatch(re.escape(prefix) + r"[0-9a-f]{64}", value) is not None)
            if item:
                selected.append(item)
        except RuntimeError as error:
            if getattr(error, "status", None) != 404:
                errors.append(str(error))
    if not selected:
        if errors:
            raise RuntimeError("Cache query failed: " + "; ".join(errors))
        return None
    item = selection.newest(selected)
    destination = work / f"cache-{item.artifact_id}"
    if not destination.exists():
        temporary = work / f"download-{item.artifact_id}"
        temporary.mkdir(parents=True, exist_ok=True)
        client.command(["run", "download", str(item.run_id), "--repo", repository,
                        "--name", item.artifact_name, "--dir", str(temporary)])
        temporary.replace(destination)
    save(destination.with_suffix(".provenance.json"), {
        "artifact": item.artifact_id, "run": item.run_id, "attempt": item.run_attempt,
        "source": item.head_sha, "created_at": item.created_at.isoformat()})
    return destination


def prepare_localization(root, work, repository):
    local = root / names.PUBLIC_PREFIX
    localization = work / "localization"
    if not localization.exists():
        sources = [local] if local.is_dir() else []
        if not (sources and complete_localization(root, local)):
            cached = trusted_cache(repository, work, exact="simple-card-localization-" + names.cache_subject(root)["subject_sha256"])
            if cached is None:
                cached = trusted_cache(repository, work, exact="simple-card-localization-seed-v1")
            if cached is None:
                old = trusted_cache(repository, work, prefix="simple-card-localization-")
                if old:
                    provenance = json.loads(old.with_suffix(".provenance.json").read_text(encoding="utf-8"))
                    candidate_seed = work / (old.name + "-compatible-seed")
                    if not candidate_seed.exists():
                        names.bootstrap_seed(root, old, provenance["source"], candidate_seed)
                    if candidate_seed.exists():
                        cached = candidate_seed
            if cached:
                sources.append(cached)
        seed = merge_localization(root, sources, work / "name-seed") if sources else None
        statistics = {}
        names.build_bundle(root, localization, seed=seed, statistics=statistics)
        save(work / "localization-result.json", statistics)
    names.verify_bundle(root, localization)
    return localization


def prepare_images(root, work, repository):
    image_cache = work / "images"
    if not image_cache.exists():
        local_images = root / images.CACHE_PUBLIC_PREFIX
        try:
            images.verify_cache_bundle(root, local_images)
            image_cache = local_images
        except (ValueError, OSError):
            seeds = [local_images] if local_images.is_dir() else []
            needed = {card["name"] for card in images.cache_subject(root)["cards"]}
            local_names = set()
            if seeds:
                retained = images.verify_cache_bundle(root, local_images, exact=False)
                local_names = {card["name"] for card in retained["cards"]}
            if not needed <= local_names:
                cached = trusted_cache(repository, work, exact="landing-card-image-cache-" + images.cache_subject(root)["subject_sha256"])
                if cached is None:
                    cached = trusted_cache(repository, work, prefix="landing-card-image-cache-")
                if cached:
                    seeds.append(cached)
            images.build_cache_bundle(root, image_cache, seeds=tuple(seeds))
    images.verify_cache_bundle(root, image_cache)
    return image_cache


def prepare_site(record, work):
    from build_pages_artifact import build_artifact, load_config, publication_paths
    root = Path(record["identity"]["root"])
    repository = record["identity"]["target"]
    localization = prepare_localization(root, work, repository)
    image_cache = prepare_images(root, work, repository)
    # Builder accepts overlays outside its input tree. Copying verified bytes is
    # packaging work, not a second query, image selection or generation.
    overlays = {}
    for identifier, source in (("card_localization", localization), ("landing_card_images", image_cache)):
        if source.is_relative_to(root):
            target = work / (identifier + "-retained")
            if not target.exists():
                shutil.copytree(source, target)
            source = target
        overlays[identifier] = source
    site = work / "site"
    config = load_config(root, root / "configs/pages_publication.json")
    selected = publication_paths(root, config)
    signature = {"source": files(root, sorted(selected | {"configs/pages_publication.json"}
                                  | set(config["compatibility_manifests"]))),
                 "overlays": {name: files(path, ["**/*"]) for name, path in overlays.items()}}
    # The source candidate is already fixed by the handoff. A completed build
    # receipt plus exact bytes is required; a half-written directory is not one.
    marker = work / "site-complete.json"
    completed = json.loads(marker.read_text(encoding="utf-8")) if marker.is_file() else None
    if site.exists():
        if not completed or completed["basis"] != signature or completed["files"] != files(site, ["**/*"]):
            raise ValueError("Existing site has no applicable completed build; preserve and inspect it")
        return site
    if completed and completed["basis"] == signature and completed.get("generated"):
        retained = Path(completed["generated"]).resolve()
        if (retained.is_relative_to(work.resolve()) and retained.name == "site"
                and retained.is_dir() and completed["files"] == files(retained, ["**/*"])):
            retained.replace(site)
            return site
    temporary = Path(tempfile.mkdtemp(prefix="site-build-", dir=work))
    build_artifact(root, root / "configs/pages_publication.json", temporary / "site", work / "site-report.json", overlays=overlays)
    # Save proof of a finished build before promoting its directory. A process
    # exit between promotion and the next outer checkpoint must not regenerate.
    save(marker, {"basis": signature, "files": files(temporary / "site", ["**/*"]),
                  "generated": str(temporary / "site")})
    (temporary / "site").replace(site)
    temporary.rmdir()
    return site


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("localization", "images"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    args = parser.parse_args(argv)
    args.work.mkdir(parents=True, exist_ok=True)
    path = (prepare_localization if args.kind == "localization" else prepare_images)(args.root.resolve(), args.work.resolve(), args.repository)
    print(json.dumps({"state": "complete", "kind": args.kind, "path": str(path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
