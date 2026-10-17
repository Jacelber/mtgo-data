"""Encrypted recovery inputs for the existing resource builders, never a product.

Only registered, individually validated bytes are transferred. The private
archive stores this material separately from Pages packages and control state.
The next builder revalidates semantics and completes its normal cache checks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import uuid
import zipfile

from mtgmeta.resource_progress import ResourceProgress, digest, save
from tools.delivery.github import GitHub, APIError

MAX_BYTES = 140 * 1024 * 1024
MAX_ENTRIES = 100000


def validate_entry(identity, key, payload):
    from tools import build_simple_card_localization as names
    from tools import build_landing_card_image_cache as images
    if identity.get("kind") == "localization":
        if set(key) == {"query", "page"}:
            value = json.loads(payload)
            if (not isinstance(key["query"], list) or not key["query"]
                    or any(not isinstance(name, str) or not name for name in key["query"])
                    or type(key["page"]) is not int or not 1 <= key["page"] <= names.MAX_PAGES
                    or value.get("page") != key["page"]
                    or type(value.get("total_pages")) is not int
                    or not 0 <= value["total_pages"] <= names.MAX_PAGES
                    or not isinstance(value.get("items"), list)
                    or any(not isinstance(item, dict) for item in value["items"])):
                raise ValueError("Invalid saved query page")
        elif set(key) == {"card", "image"}:
            names._trusted_mtgch_image(key["image"])
            names._valid_webp(payload, key["card"])
        else:
            raise ValueError("Unsupported localization recovery entry")
    elif identity.get("kind") == images.CACHE_PRODUCT:
        if set(key) == {"resolve"}:
            value = json.loads(payload)
            if set(value) != {"source_image_uri", "scryfall_id", "oracle_id", "face_index"}:
                raise ValueError("Invalid saved image selection")
            images._valid_scryfall_image_uri(value["source_image_uri"])
            uuid.UUID(value["scryfall_id"])
            uuid.UUID(value["oracle_id"])
            face = value["face_index"]
            if face is not None and (type(face) is not int or face < 0):
                raise ValueError("Invalid saved face selection")
        elif set(key) == {"image"}:
            images._valid_scryfall_image_uri(key["image"])
            images._valid_jpeg(payload, key["image"])
        else:
            raise ValueError("Unsupported image recovery entry")
    else:
        raise ValueError("Unsupported recovery builder")


def validate_origin(origin):
    if (set(origin) != {"repository", "operation", "source", "run", "attempt", "workflow"}
            or origin["repository"] not in {"Jacelber/mtgo-data", "Jacelber/mtgo-data-governance-verification"}
            or not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", origin["operation"])
            or not re.fullmatch(r"[0-9a-f]{40}", origin["source"])
            or type(origin["run"]) is not int or origin["run"] < 1
            or type(origin["attempt"]) is not int or origin["attempt"] < 1
            or origin["workflow"] != ".github/workflows/prepare-pages.yml"):
        raise ValueError("Invalid recovery provenance")


def snapshot(work, destination, origin):
    validate_origin(origin)
    state = json.loads((work / "progress.json").read_text(encoding="utf-8"))
    entries, rejected, payloads = {}, [], {}
    for identifier, entry in state["entries"].items():
        try:
            if identifier != digest(entry["key"]):
                raise ValueError("Wrong entry key")
            path = work / (identifier + ".bin")
            if path.is_symlink():
                raise ValueError("Recovery link")
            payload = path.read_bytes()
            if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
                raise ValueError("Saved bytes changed")
            validate_entry(state["identity"], entry["key"], payload)
        except (OSError, ValueError, TypeError, KeyError):
            rejected.append(identifier)
            continue
        entries[identifier], payloads[identifier] = entry, payload
    if not entries:
        raise ValueError("No validated resources to preserve")
    if len(entries) > MAX_ENTRIES or sum(map(len, payloads.values())) > MAX_BYTES:
        raise ValueError("Recovery exceeds resource limits")
    retained = {"identity": state["identity"], "entries": entries, "complete": False}
    if "bulk_sha256" in state:
        if not re.fullmatch(r"[0-9a-f]{64}", str(state["bulk_sha256"])):
            raise ValueError("Invalid bulk source binding")
        retained["bulk_sha256"] = state["bulk_sha256"]
    manifest = {"schema": 1, "kind": "resource-recovery", "origin": origin,
                "progress": retained, "excluded_entries": rejected}
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_STORED) as bundle:
        bundle.writestr("recovery.json", json.dumps(manifest, ensure_ascii=False))
        for identifier, payload in payloads.items():
            bundle.writestr(identifier + ".bin", payload)
    return manifest


def inspect_bundle(bundle, *, origin=None):
    if bundle.stat().st_size > MAX_BYTES + 20_000_000:
        raise ValueError("Oversized recovery transfer")
    with zipfile.ZipFile(bundle) as archive:
        infos = archive.infolist()
        if (len(infos) > MAX_ENTRIES + 1 or len({info.filename for info in infos}) != len(infos)
                or any(info.compress_type != zipfile.ZIP_STORED for info in infos)
                or sum(info.file_size for info in infos) > MAX_BYTES + 20_000_000):
            raise ValueError("Invalid recovery container")
        if archive.getinfo("recovery.json").file_size > 20_000_000:
            raise ValueError("Oversized recovery index")
        manifest = json.loads(archive.read("recovery.json"))
        if manifest.get("kind") != "resource-recovery" or manifest.get("schema") != 1:
            raise ValueError("Not a resource recovery input")
        validate_origin(manifest["origin"])
        if origin is not None and manifest["origin"] != origin:
            raise ValueError("Recovery belongs to another operation or run")
        state = manifest["progress"]
        if state.get("complete") is not False:
            raise ValueError("Recovery inputs cannot claim complete-cache status")
        expected = {"recovery.json"} | {identifier + ".bin" for identifier in state["entries"]}
        if set(archive.namelist()) != expected:
            raise ValueError("Unregistered recovery file")
        for identifier, entry in state["entries"].items():
            if identifier != digest(entry["key"]):
                raise ValueError("Recovery entry identity mismatch")
            payload = archive.read(identifier + ".bin")
            if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
                raise ValueError("Recovery entry bytes mismatch")
            validate_entry(state["identity"], entry["key"], payload)
    return manifest


def seal(work, destination, certificate, origin, *, openssl="openssl"):
    if destination.exists():
        raise ValueError("Preserve the existing encrypted recovery")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        root = Path(temporary)
        manifest = snapshot(work, root / "resources.zip", origin)
        result = subprocess.run([openssl, "cms", "-encrypt", "-binary", "-stream", "-outform", "DER",
            "-aes-256-gcm", "-recip", str(certificate), "-keyopt", "rsa_padding_mode:oaep",
            "-keyopt", "rsa_oaep_md:sha256", "-in", str(root / "resources.zip"),
            "-out", str(root / "resources.cms")], capture_output=True)
        if result.returncode:
            raise ValueError("Recovery encryption failed; do not upload plaintext")
        (root / "resources.cms").rename(destination)
        return manifest


def decrypt(encrypted, destination, key, *, origin, openssl="openssl"):
    if destination.exists() or encrypted.stat().st_size > MAX_BYTES + 22_000_000:
        raise ValueError("Use a new supported recovery destination")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        bundle = Path(temporary) / "resources.zip"
        result = subprocess.run([openssl, "cms", "-decrypt", "-binary", "-inform", "DER",
            "-inkey", str(key), "-in", str(encrypted), "-out", str(bundle)], capture_output=True)
        if result.returncode:
            raise ValueError("Recovery decryption or authentication failed")
        manifest = inspect_bundle(bundle, origin=origin)
        bundle.rename(destination)
        return manifest


def restore(bundle, work, *, origin):
    manifest = inspect_bundle(bundle, origin=origin)
    state = manifest["progress"]
    progress = ResourceProgress(work, state["identity"])
    with zipfile.ZipFile(bundle) as archive:
        for identifier, entry in state["entries"].items():
            progress.bytes(entry["key"], lambda: archive.read(identifier + ".bin"),
                           lambda payload: validate_entry(state["identity"], entry["key"], payload))
    if "bulk_sha256" in state and "bulk_sha256" not in progress.state:
        progress.state["bulk_sha256"] = state["bulk_sha256"]
        save(progress.record, progress.state)
    return {"state": "restored_inputs", "entries": len(state["entries"]), "work": str(work)}


def validate_source_run(origin, run):
    validate_origin(origin)
    if (run.get("id") != origin["run"] or run.get("run_attempt") != origin["attempt"]
            or run.get("path") != origin["workflow"] or run.get("head_sha") != origin["source"]
            or run.get("head_branch") != ("master" if origin["repository"] == "Jacelber/mtgo-data" else "main")
            or run.get("event") not in {"workflow_dispatch", "push", "repository_dispatch"}
            or run.get("repository", {}).get("full_name") != origin["repository"]
            or run.get("head_repository", {}).get("full_name") != origin["repository"]):
        raise ValueError("Resource recovery source run is not a supported trusted producer")


def preserve_private(bundle, client, *, origin, source_run):
    """Trusted uploader only; read back bytes before claiming durable storage."""
    manifest = inspect_bundle(bundle, origin=origin)
    validate_source_run(origin, source_run)
    client.private()
    identifier = "resource-recovery-" + hashlib.sha256(bundle.read_bytes()).hexdigest()
    try:
        release = client.api(f"repos/{client.repository}/releases/tags/{identifier}")
    except APIError as error:
        if error.status != 404:
            raise
        release = client.api(f"repos/{client.repository}/releases", method="POST", body={
            "tag_name": identifier, "name": identifier, "draft": False,
            "body": json.dumps({"kind": "resource-recovery", "origin": origin,
                                "builder": manifest["progress"]["identity"]["kind"]})})
    if not any(asset["name"] == "resources.zip" for asset in release["assets"]):
        with tempfile.TemporaryDirectory() as temporary:
            upload = Path(temporary) / "resources.zip"
            upload.write_bytes(bundle.read_bytes())
            client.command(["release", "upload", identifier, str(upload), "--repo", client.repository])
    with tempfile.TemporaryDirectory() as temporary:
        returned = Path(temporary) / "resources.zip"
        client.command(["release", "download", identifier, "--repo", client.repository,
                        "--pattern", "resources.zip", "--output", str(returned)])
        if returned.read_bytes() != bundle.read_bytes():
            raise ValueError("Private recovery read-back differs; not preserved")
        inspect_bundle(returned, origin=origin)
    return {"state": "preserved", "repository": client.repository, "reference": identifier,
            "origin": origin, "entries": len(inspect_bundle(bundle)["progress"]["entries"])}


def retrieve_private(reference, client, destination, *, origin):
    if not re.fullmatch(r"resource-recovery-[0-9a-f]{64}", reference):
        raise ValueError("Not a resource recovery reference")
    client.private()
    if destination.exists():
        raise ValueError("Use a new recovery download destination")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        bundle = Path(temporary) / "resources.zip"
        client.command(["release", "download", reference, "--repo", client.repository,
                        "--pattern", "resources.zip", "--output", str(bundle)])
        if "resource-recovery-" + hashlib.sha256(bundle.read_bytes()).hexdigest() != reference:
            raise ValueError("Recovery archive bytes do not match its reference")
        inspect_bundle(bundle, origin=origin)
        bundle.rename(destination)


def resume_private(client, work, *, repository, operation, builder):
    """Newest preserved input for this task, not every historical cache."""
    client.private()
    selected = None
    for page in range(1, 11):
        releases = client.api(f"repos/{client.repository}/releases?per_page=100&page={page}")
        for item in releases:
            if not re.fullmatch(r"resource-recovery-[0-9a-f]{64}", item.get("tag_name", "")):
                continue
            try:
                metadata = json.loads(item["body"])
            except (ValueError, TypeError):
                continue
            origin = metadata.get("origin", {})
            if (metadata.get("kind") == "resource-recovery" and metadata.get("builder") == builder
                    and origin.get("repository") == repository and origin.get("operation") == operation):
                if selected is None or (origin["run"], origin["attempt"], item["created_at"]) > selected[0]:
                    selected = ((origin["run"], origin["attempt"], item["created_at"]), item["tag_name"], origin)
        if len(releases) < 100:
            break
    else:
        raise ValueError("Recovery release listing exceeded its query limit; retain work and narrow the lookup")
    if selected is None:
        return {"state": "no_preserved_input"}
    _, reference, origin = selected
    with tempfile.TemporaryDirectory() as temporary:
        bundle = Path(temporary) / "resources.zip"
        retrieve_private(reference, client, bundle, origin=origin)
        result = restore(bundle, work, origin=origin)
    return {**result, "reference": reference}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("origin", "seal", "preserve", "restore"))
    parser.add_argument("--origin", type=Path)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--certificate", type=Path)
    parser.add_argument("--openssl", default="openssl")
    parser.add_argument("--archive", default="Jacelber/mtgo-data-releases")
    args = parser.parse_args(argv)
    if args.command == "origin":
        origin = {"repository": os.environ["GITHUB_REPOSITORY"], "operation": os.environ["PREPARATION"],
            "source": os.environ["GITHUB_SHA"], "run": int(os.environ["GITHUB_RUN_ID"]),
            "attempt": int(os.environ["GITHUB_RUN_ATTEMPT"]), "workflow": ".github/workflows/prepare-pages.yml"}
        validate_origin(origin)
        save(args.output, origin)
        return 0
    if args.origin is None or args.input is None:
        parser.error("origin and input are required for this operation")
    origin = json.loads(args.origin.read_text(encoding="utf-8"))
    if args.command == "seal":
        if args.certificate is None:
            parser.error("seal requires --certificate")
        seal(args.input, args.output, args.certificate, origin, openssl=args.openssl)
        result = {"state": "encrypted_local", "path": str(args.output)}
    elif args.command == "preserve":
        key_value = os.environ.get("ARCHIVE_HANDOFF_KEY")
        if not key_value:
            raise ValueError("Trusted preserver lacks the decryption key")
        source = GitHub(origin["repository"])
        source_run = source.api(f"repos/{origin['repository']}/actions/runs/{origin['run']}")
        validate_source_run(origin, source_run)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            key = root / "key.pem"
            key.write_text(key_value, encoding="ascii")
            key.chmod(0o600)
            decrypt(args.input, root / "resources.zip", key, origin=origin, openssl=args.openssl)
            result = preserve_private(root / "resources.zip", GitHub(args.archive, token_env="ARCHIVE_TOKEN"),
                                      origin=origin, source_run=source_run)
        save(args.output, result)
    else:
        result = restore(args.input, args.output, origin=origin)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
