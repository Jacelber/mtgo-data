"""Transport an existing private package in parts; never generate or execute it."""
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import tempfile

from tools.delivery import packages
from tools.delivery.github import APIError, GitHub

PART_BYTES = 4 * 1024 * 1024


def part_sizes(manifest: dict, identifier: str, target: str) -> dict[str, int]:
    size = manifest.get("bytes")
    if (not re.fullmatch(r"pages-[0-9a-f]{64}", identifier)
            or manifest.get("id") != identifier
            or manifest.get("sha256") != identifier[6:]
            or manifest.get("schema") != 1 or manifest.get("target") != target
            or type(size) is not int or not 0 < size <= packages.MAX_BYTES):
        raise ValueError("Invalid fixed package manifest")
    return {f"product.tar.gz.part-{index:04d}": min(PART_BYTES, size - offset)
            for index, offset in enumerate(range(0, size, PART_BYTES))}


def split(candidate: Path, destination: Path, *, target: str) -> dict:
    manifest = json.loads((candidate / "manifest.json").read_text())
    packages.verify(candidate / "product.tar.gz", manifest, target=target)
    sizes = part_sizes(manifest, manifest["id"], target)
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(candidate / "manifest.json", destination / "manifest.json")
    with (candidate / "product.tar.gz").open("rb") as source:
        for name, size in sizes.items():
            (destination / name).write_bytes(source.read(size))
    return {"id": manifest["id"], "parts": len(sizes), "bytes": manifest["bytes"]}


def archive_parts(client: GitHub, identifier: str, *, target: str) -> dict:
    """Resume one private draft, including interruption after full-file upload.

    Parts are removed only after the complete remote asset is verified. The
    normal archive entry then checks both final assets and records completeness.
    This function never changes deployment selection or preparation provenance.
    """
    client.private()
    release = client.release(identifier)
    if not release:
        raise APIError("Fixed package release is missing")

    def assets(value: dict) -> dict:
        result = {a["name"]: a for a in value["assets"]}
        if len(result) != len(value["assets"]) or any(
                a.get("state") != "uploaded" for a in result.values()):
            raise APIError("Duplicate or incomplete assets; preserve and inspect")
        return result

    current = assets(release)
    if "manifest.json" not in current or not 0 < current["manifest.json"]["size"] <= 1024 * 1024:
        raise APIError("Missing or oversized manifest")
    with tempfile.TemporaryDirectory(prefix="trusted-package-parts-") as temporary:
        root = Path(temporary)

        def download(name: str, directory: Path = root) -> None:
            client.command(["release", "download", identifier, "--repo", client.repository,
                            "--pattern", name, "--dir", str(directory)])

        download("manifest.json")
        manifest = json.loads((root / "manifest.json").read_text())
        sizes = part_sizes(manifest, identifier, target)
        if set(current) - {"manifest.json", "product.tar.gz", *sizes}:
            raise APIError("Unexpected assets; do not delete or register them")
        package = root / "product.tar.gz"
        if "product.tar.gz" in current:
            if current["product.tar.gz"]["size"] != manifest["bytes"]:
                raise APIError("Existing full asset has the wrong size; never overwrite it")
            download("product.tar.gz")
        else:
            if not release["draft"] or set(current) != {"manifest.json", *sizes}:
                raise APIError("Part handoff is incomplete or not a draft")
            if any(current[name]["size"] != size for name, size in sizes.items()):
                raise APIError("Part size differs from fixed manifest")
            with package.open("xb") as output:
                for name, size in sizes.items():
                    download(name)
                    part = root / name
                    if part.stat().st_size != size:
                        raise APIError("Downloaded part size differs")
                    with part.open("rb") as source:
                        shutil.copyfileobj(source, output)
                    part.unlink()
        packages.verify(package, manifest, target=target)
        if "product.tar.gz" not in current:
            client.command(["release", "upload", identifier, str(package), "--repo", client.repository])
        refreshed = client.release(identifier)
        if not refreshed or refreshed["id"] != release["id"]:
            raise APIError("Release changed; preserve handoff")
        current = assets(refreshed)
        full = current.get("product.tar.gz", {})
        if (set(current) - {"manifest.json", "product.tar.gz", *sizes}
                or full.get("size") != manifest["bytes"]):
            raise APIError("Remote full package is not confirmed; preserve handoff")
        if full.get("digest"):
            if full["digest"] != "sha256:" + manifest["sha256"]:
                raise APIError("Remote package digest differs; preserve handoff")
        else:
            check = root / "remote-check"
            check.mkdir()
            download("product.tar.gz", check)
            packages.verify(check / "product.tar.gz", manifest, target=target)
        for name in sizes:
            if name in current:
                client.api(f"repos/{client.repository}/releases/assets/{current[name]['id']}", method="DELETE")
        return client.archive(root, target=target)
