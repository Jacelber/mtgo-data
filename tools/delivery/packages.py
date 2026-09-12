"""Immutable static packages. No execution, fetch or product generation."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import tempfile
import zipfile

MAX_BYTES = 1_000_000_000
MAX_FILES = 100_000
PROBES = ("index.html", "melee/index.html", "stats/catalog.json")
VERSION_FILE = ".product-version.json"


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def safe_name(name: str) -> str:
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or ".." in path.parts or "\\" in name:
        raise ValueError(f"Unsafe package path: {name!r}")
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    if any(":" in part or part.endswith((" ", ".")) or part.split(".")[0].upper() in reserved for part in path.parts):
        raise ValueError(f"Nonportable package path: {name!r}")
    return path.as_posix()


def inspect(package: Path) -> dict:
    names: set[str] = set()
    probes = {}
    total = count = 0
    with tarfile.open(package, "r:*") as archive:
        for member in archive:
            if member.name in (".", "./") and member.isdir():
                continue
            name = safe_name(member.name)
            if name.casefold() in names:
                raise ValueError(f"Duplicate package path: {name}")
            names.add(name.casefold())
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError(f"Links or special files are forbidden: {name}")
            total += member.size
            count += 1
            if total > MAX_BYTES or count > MAX_FILES:
                raise ValueError("Package exceeds supported Pages limits")
            if name in (*PROBES, VERSION_FILE):
                handle = archive.extractfile(member)
                if handle is None:
                    raise ValueError(f"Unreadable entry: {name}")
                with handle:
                    probes[name] = hashlib.file_digest(handle, "sha256").hexdigest()
    if missing := set(PROBES) - set(probes):
        raise ValueError(f"Missing product entry: {sorted(missing)}")
    return {"file_count": count, "expanded_bytes": total, "probes": probes}


def describe(package: Path, *, target: str, source: str) -> dict:
    structure = inspect(package)
    digest = sha256(package)
    return {"schema": 1, "id": f"pages-{digest}", "target": target,
            "sha256": digest, "bytes": package.stat().st_size, "source": source, **structure}


def prepare(site: Path, destination: Path, *, target: str, source: str) -> dict:
    """Input must be the approved public builder output, not a repository root."""
    site, destination = site.resolve(), destination.resolve()
    if not site.is_dir() or destination == site or site in destination.parents:
        raise ValueError("Use an existing selected site and an external destination")
    if destination.exists():
        raise ValueError("Destination must be new; reuse existing candidates explicitly")
    destination.mkdir(parents=True)
    package = destination / "product.tar.gz"
    try:
        content_digest = hashlib.sha256()
        with package.open("wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as zipped:
            with tarfile.open(fileobj=zipped, mode="w|") as archive:
                # Match the root-relative tree emitted by the official Pages
                # tar command. Include parent directories with explicit modes.
                root_entry = tarfile.TarInfo(".")
                root_entry.type, root_entry.mode, root_entry.mtime = tarfile.DIRTYPE, 0o755, 0
                archive.addfile(root_entry)
                for path in sorted(site.rglob("*")):
                    if path.is_symlink():
                        raise ValueError("Site contains a link")
                    if path.is_dir():
                        directory = tarfile.TarInfo("./" + safe_name(path.relative_to(site).as_posix()))
                        directory.type, directory.mode, directory.mtime = tarfile.DIRTYPE, 0o755, 0
                        archive.addfile(directory)
                        continue
                    if not path.is_file():
                        raise ValueError("Site contains a special file")
                    if path.relative_to(site).as_posix() == VERSION_FILE:
                        continue  # A new candidate gets a marker for its actual selected bytes.
                    relative = safe_name(path.relative_to(site).as_posix())
                    info = archive.gettarinfo(str(path), arcname="./" + relative)
                    info.uid = info.gid = info.mtime = 0
                    info.uname = info.gname = ""
                    info.mode = 0o644
                    with path.open("rb") as handle:
                        digest = hashlib.sha256()
                        class SelectedBytes:
                            def read(self, size=-1):
                                data = handle.read(size)
                                digest.update(data)
                                return data
                        archive.addfile(info, SelectedBytes())
                        if handle.read(1):
                            raise ValueError("Site changed while packaging; prepare a stable candidate")
                        content_digest.update(relative.encode() + b"\0" + digest.hexdigest().encode() + b"\0")
                marker = json.dumps({"content_sha256": content_digest.hexdigest()}, sort_keys=True).encode() + b"\n"
                info = tarfile.TarInfo("./" + VERSION_FILE)
                info.size, info.mode, info.mtime = len(marker), 0o644, 0
                archive.addfile(info, io.BytesIO(marker))
        manifest = describe(package, target=target, source=source)
        (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return manifest
    except Exception:
        package.unlink(missing_ok=True)
        raise


def verify(package: Path, manifest: dict, *, target: str) -> dict:
    if manifest.get("schema") != 1 or manifest.get("target") != target:
        raise ValueError("Wrong package schema or deployment target")
    digest = sha256(package)
    if manifest.get("sha256") != digest or manifest.get("id") != f"pages-{digest}":
        raise ValueError("Package integrity mismatch")
    if manifest.get("bytes") != package.stat().st_size:
        raise ValueError("Package size mismatch")
    if any(manifest.get(key) != value for key, value in inspect(package).items()):
        raise ValueError("Manifest does not describe the package")
    return manifest


def pages_transport(package: Path, manifest: dict, destination: Path, *, target: str) -> None:
    """Remove only gzip transport compression; preserve the original complete tar.

    upload-pages-artifact rebuilds a tar and excludes hidden files. Passing this
    tar to upload-artifact instead preserves the selected product, including its
    version marker, without a second file-selection step.
    """
    verify(package, manifest, target=target)
    if destination.exists():
        raise ValueError("Transport destination must be new")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with gzip.open(package, "rb") as source, destination.open("xb") as output:
            shutil.copyfileobj(source, output)
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def extract(package: Path, manifest: dict, destination: Path, *, target: str) -> None:
    verify(package, manifest, target=target)
    destination = destination.resolve()
    if destination.exists():
        raise ValueError("Extract destination must be new")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".package-", dir=destination.parent))
    try:
        with tarfile.open(package, "r:*") as archive:
            for member in archive:
                if member.isdir():
                    continue
                path = temporary / safe_name(member.name)
                path.parent.mkdir(parents=True, exist_ok=True)
                handle = archive.extractfile(member)
                if handle is None:
                    raise ValueError("Unreadable member")
                with handle, path.open("xb") as output:
                    shutil.copyfileobj(handle, output)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def seal_candidate(candidate: Path, destination: Path, certificate: Path, *, target: str, openssl: str = "openssl") -> None:
    """Public Actions handoff carries ciphertext, never an unaccepted product.

    The builder needs only the recipient's public certificate. The private key
    and archive credential belong solely to the trusted upload environment.
    CMS encryption does not grant provenance, quality or publication authority.
    """
    manifest = json.loads((candidate / "manifest.json").read_text(encoding="utf-8"))
    verify(candidate / "product.tar.gz", manifest, target=target)
    if destination.exists():
        raise ValueError("Encrypted handoff destination must be new")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="handoff-", dir=destination.parent) as temporary:
        bundle = Path(temporary) / "candidate.zip"
        encrypted = Path(temporary) / "candidate.cms"
        with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_STORED) as archive:
            for name in ("product.tar.gz", "manifest.json"):
                archive.write(candidate / name, name)
        result = subprocess.run([openssl, "cms", "-encrypt", "-binary", "-stream", "-outform", "DER",
            "-aes-256-gcm", "-recip", str(certificate), "-keyopt", "rsa_padding_mode:oaep",
            "-keyopt", "rsa_oaep_md:sha256", "-in", str(bundle), "-out", str(encrypted)], capture_output=True)
        if result.returncode:
            raise ValueError("Candidate encryption failed; no plaintext handoff may be uploaded")
        encrypted.rename(destination)


def open_candidate(encrypted: Path, destination: Path, private_key: Path, *, target: str, openssl: str = "openssl") -> dict:
    """Trusted environment only. Decrypt, validate and expose exactly two files."""
    if destination.exists() or encrypted.stat().st_size > MAX_BYTES + 2_000_000:
        raise ValueError("Use a new destination and a supported handoff size")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="handoff-", dir=destination.parent) as temporary:
        root = Path(temporary)
        bundle = root / "candidate.zip"
        result = subprocess.run([openssl, "cms", "-decrypt", "-binary", "-inform", "DER",
            "-inkey", str(private_key), "-in", str(encrypted), "-out", str(bundle)], capture_output=True)
        if result.returncode:
            raise ValueError("Candidate decryption or authentication failed")
        candidate = root / "candidate"
        candidate.mkdir()
        with zipfile.ZipFile(bundle) as archive:
            if sorted(archive.namelist()) != ["manifest.json", "product.tar.gz"]:
                raise ValueError("Handoff must contain exactly the product package and manifest")
            for info in archive.infolist():
                limit = 1_000_000 if info.filename == "manifest.json" else MAX_BYTES
                if info.file_size > limit or info.compress_type != zipfile.ZIP_STORED:
                    raise ValueError("Unsupported handoff member size or compression")
                with archive.open(info) as source, (candidate / info.filename).open("xb") as output:
                    shutil.copyfileobj(source, output)
        manifest = json.loads((candidate / "manifest.json").read_text(encoding="utf-8"))
        verify(candidate / "product.tar.gz", manifest, target=target)
        candidate.rename(destination)
        return manifest
