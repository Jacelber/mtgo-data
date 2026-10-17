"""Check fixed materials using existing product contracts; never invent consent.

These local checks are not an independently protected permission boundary.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tarfile

from tools.delivery import packages
from mtgmeta.generation_progress import files


def material_snapshot(root, scope):
    from build_pages_artifact import load_config, publication_paths
    from mtgmeta.classifier_closure import _protected_input_fingerprints
    root = Path(root)
    config_path = root / "configs/pages_publication.json"
    if not config_path.is_file():
        return None  # Synthetic adapter tests; the real verifier rejects this.
    config = load_config(root, config_path)
    paths = publication_paths(root, config) | {"configs/pages_publication.json"} | set(config["compatibility_manifests"])
    inputs = {fmt: _protected_input_fingerprints(root, fmt)
              for fmt in scope.get("mtgo_formats", [])}
    return {"files": files(root, sorted(paths)), "inputs": inputs}


def verify_material(record, candidate):
    from build_pages_artifact import load_config, publication_paths, validate_compatibility
    from mtgmeta.classifier_closure import validate_current_melee
    from mtgmeta.mtgo.publication import resolve_scope, inspect_publication
    identity = record["identity"]
    root = Path(identity["root"])
    fixed = identity.get("material")
    if fixed is None or material_snapshot(root, identity["scope"]) != fixed:
        raise ValueError("Fixed material changed or missing; compare with the confirmed standard before repair")
    for ref in identity["references"]:
        if not Path(ref["path"]).is_file() or packages.sha256(Path(ref["path"])) != ref["sha256"]:
            raise ValueError("Existing confirmation or scope reference changed")
    manifest = json.loads((candidate / "manifest.json").read_text(encoding="utf-8"))
    packages.verify(candidate / "product.tar.gz", manifest, target=identity["target"])
    config = load_config(root, root / "configs/pages_publication.json")
    selected = publication_paths(root, config)
    from tools.build_archetype_visuals import require_public_representatives
    require_public_representatives(root, selected)
    validate_compatibility(root, config, selected)
    formats = identity["scope"].get("mtgo_formats", [])
    if not formats or len(formats) != len(set(formats)):
        raise ValueError("Delivery requires distinct admitted formats")
    for fmt in formats:
        approved = resolve_scope(root, fmt)
        if approved.week.strftime("%G-W%V") != identity["scope"]["week"]:
            raise ValueError("Delivery differs from admitted data week")
        if inspect_publication(root, fmt):
            raise ValueError("Data consumer binding is stale")
        validate_current_melee(root, fmt)
    # Compare the whole public package to the fixed selected site, not a few probes.
    site = Path(record["progress"].get("site") or identity["site"])
    expected_site = record["progress"].get("site_files") or identity.get("site_files")
    if expected_site is None or files(site, ["**/*"]) != expected_site:
        raise ValueError("Fixed site changed or lacks its completed build record")
    with tarfile.open(candidate / "product.tar.gz", "r:gz") as archive:
        actual = {}
        for member in archive:
            if member.isfile():
                name = packages.safe_name(member.name)
                if name != packages.VERSION_FILE:
                    actual[name] = hashlib.sha256(archive.extractfile(member).read()).hexdigest()
    expected = {p.relative_to(site).as_posix(): packages.sha256(p) for p in site.rglob("*")
                if p.is_file() and p.name != packages.VERSION_FILE}
    if actual != expected:
        raise ValueError("Package differs from fixed candidate")
    prefixes = [item["public_prefix"] + "/" for item in config["generated_overlays"]]
    extras = [name for name in actual if name not in selected and name != ".nojekyll"
              and not any(name.startswith(prefix) for prefix in prefixes)]
    if extras:
        raise ValueError("Non-public package files: " + ", ".join(extras[:10]))
    if not selected <= set(actual):
        raise ValueError("Package omits selected public files")
    editable = set()
    if identity["kind"] == "landing_content":
        week = identity["scope"]["week"]
        for fmt in formats:
            base = f"stats/{fmt}/mtgo/landing"
            editable.update({f"{base}/current.json", f"{base}/features/{week}.json",
                             f"{base}/features/index.json"})
            editable.update(f"{base}/weeks/{week}/{part}.json" for part in
                            ("range", "completeness", "environment_decks", "feature_decks"))
            index = f"{base}/features/index.json"
            before = json.loads((root / index).read_text(encoding="utf-8"))
            after = json.loads((site / index).read_text(encoding="utf-8"))
            def historical(value):
                return {**value, "weeks": [item for item in value["weeks"] if item["week"] != week]}
            if historical(before) != historical(after):
                raise ValueError("Content delivery changes historical Feature index")
    for relative in selected:
        if relative not in editable and actual[relative] != packages.sha256(root / relative):
            raise ValueError("Package changes an unreviewed product: " + relative)
    # Validate overlays as resources, not arbitrary files sharing a public prefix.
    from tools import build_simple_card_localization as names, build_landing_card_image_cache as images
    for overlay in config["generated_overlays"]:
        bundle = site / overlay["public_prefix"]
        if overlay["id"] == "card_localization":
            names.verify_bundle(root, bundle)
        elif overlay["id"] == "landing_card_images":
            images.verify_cache_bundle(root, bundle)
        else:
            raise ValueError("Unsupported resource overlay")
    if identity["kind"] == "landing_content":
        from mtgmeta.mtgo.review_submission import require_accepted, preview_packet
        accepted = [json.loads(Path(ref["path"]).read_text(encoding="utf-8")) for ref in identity["references"]]
        for fmt in formats:
            matches = [item for item in accepted if item.get("submission", {}).get("format") == fmt
                       and item["submission"].get("kind") == "preview"]
            if len(matches) != 1:
                raise ValueError("Content delivery lacks the existing page acceptance")
            envelope = matches[0]
            if envelope["submission"].get("week") != identity["scope"]["week"]:
                raise ValueError("Content acceptance differs from the selected week")
            require_accepted(envelope["submission"], envelope["decisions"], current=preview_packet(site, fmt))
