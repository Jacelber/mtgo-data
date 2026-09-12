"""GitHub transport for the trusted uploader and writer. Never executes candidate code."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import quote

from tools.delivery import packages
from tools.delivery.state import Conflict, expired_packages, initial


class APIError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class GitHub:
    def __init__(self, repository: str, *, token_env: str | None = None, state_path: str = "state/pages.json"):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("Invalid repository")
        self.repository = repository
        if state_path not in {"state/pages.json", "state/verification-pages.json"}:
            raise ValueError("Unknown deployment control record")
        self.state_path = state_path
        self.environment = os.environ.copy()
        if token_env:
            token = os.environ.get(token_env)
            if not token:
                raise APIError(f"Missing required environment credential: {token_env}")
            self.environment["GH_TOKEN"] = token

    def command(self, arguments: list[str], *, body: dict | None = None) -> str:
        execution = subprocess.run(["gh", *arguments], input=json.dumps(body) if body is not None else None,
                                   capture_output=True, text=True, env=self.environment)
        if execution.returncode:
            match = re.search(r"HTTP (\d{3})", execution.stderr)
            # gh does not echo token environment variables; do not log command environment.
            raise APIError(execution.stderr.strip(), int(match[1]) if match else None)
        return execution.stdout

    def api(self, path: str, *, method: str = "GET", body: dict | None = None):
        arguments = ["api", path, "--method", method, "-H", "Accept: application/vnd.github+json"]
        if body is not None:
            arguments += ["--input", "-"]
        output = self.command(arguments, body=body)
        return json.loads(output) if output.strip() else None

    def private(self) -> None:
        if not self.api(f"repos/{self.repository}")["private"]:
            raise APIError("Product archive must remain private")

    def load_state(self) -> tuple[dict, str | None]:
        try:
            content = self.api(f"repos/{self.repository}/contents/{self.state_path}")
        except APIError as error:
            if error.status != 404:
                raise
            return initial(), None
        state = json.loads(base64.b64decode(content["content"]))
        if state.get("schema") != 1:
            raise APIError("Unsupported writer state; do not reset it")
        return state, content["sha"]

    def save_state(self, state: dict, sha: str | None) -> str:
        body = {"message": "Update Pages operation facts",
                "content": base64.b64encode((json.dumps(state, indent=2) + "\n").encode()).decode()}
        if sha:
            body["sha"] = sha
        try:
            result = self.api(f"repos/{self.repository}/contents/{self.state_path}", method="PUT", body=body)
        except APIError as error:
            if error.status in {409, 422}:
                raise Conflict("Writer state changed: read actual state and reconsider the operation") from error
            # A timed-out PUT might have succeeded. Caller reads before any retry.
            raise
        return result["content"]["sha"]

    def release(self, identifier: str) -> dict | None:
        if not re.fullmatch(r"pages-[0-9a-f]{64}", identifier):
            raise ValueError("Invalid immutable candidate identifier")
        try:
            return self.api(f"repos/{self.repository}/releases/tags/{quote(identifier, safe='')}")
        except APIError as error:
            if error.status != 404:
                raise
            # GitHub's tag endpoint omits draft releases. Locate the existing
            # upload before deciding it is absent; never create a second draft.
            page = 1
            while True:
                releases = self.api(f"repos/{self.repository}/releases?per_page=100&page={page}")
                matching = [item for item in releases if item["tag_name"] == identifier]
                if len(matching) > 1:
                    raise APIError("Multiple releases claim the same immutable candidate")
                if matching:
                    return matching[0]
                if len(releases) < 100:
                    return None
                page += 1

    def archive(self, candidate: Path, *, target: str) -> dict:
        self.private()
        manifest = json.loads((candidate / "manifest.json").read_text(encoding="utf-8"))
        packages.verify(candidate / "product.tar.gz", manifest, target=target)
        identifier = manifest["id"]
        release = self.release(identifier)
        if release is None:
            release = self.api(f"repos/{self.repository}/releases", method="POST", body={
                "tag_name": identifier, "name": identifier, "draft": True,
                "body": "Private complete product package. Archival alone grants no publication eligibility."})
        expected = {name: packages.sha256(candidate / name) for name in ("product.tar.gz", "manifest.json")}
        by_name = {asset["name"]: asset for asset in release["assets"]}
        for name, digest in expected.items():
            existing = by_name.get(name)
            if existing:
                if existing.get("state") != "uploaded":
                    raise APIError(f"Incomplete asset {name}; inspect the interrupted upload before removing it")
                if existing.get("digest") != f"sha256:{digest}":
                    # Older assets may have no platform digest: verify by actual download.
                    with tempfile.TemporaryDirectory(prefix="archive-verify-") as temporary:
                        self.command(["release", "download", identifier, "--repo", self.repository,
                                      "--pattern", name, "--dir", temporary])
                        if packages.sha256(Path(temporary) / name) != digest:
                            raise APIError(f"Immutable asset differs: {name}; never overwrite it")
                continue
            self.command(["release", "upload", identifier, str(candidate / name), "--repo", self.repository])
        release = self.release(identifier)
        if not release or {asset["name"] for asset in release["assets"] if asset.get("state") == "uploaded"} != set(expected):
            raise APIError("Archive is incomplete; do not publish or register it as complete")
        for asset in release["assets"]:
            if asset.get("digest") and asset["digest"] != f"sha256:{expected[asset['name']]}":
                raise APIError("Uploaded asset checksum differs")
            if not asset.get("digest"):
                with tempfile.TemporaryDirectory(prefix="archive-verify-") as temporary:
                    self.command(["release", "download", identifier, "--repo", self.repository,
                                  "--pattern", asset["name"], "--dir", temporary])
                    if packages.sha256(Path(temporary) / asset["name"]) != expected[asset["name"]]:
                        raise APIError("Uploaded asset checksum differs")
        if release["draft"]:
            release = self.api(f"repos/{self.repository}/releases/{release['id']}", method="PATCH", body={"draft": False})
        state, sha = self.load_state()
        if identifier not in state["packages"]:
            state["packages"][identifier] = {"complete": True, "eligible": False, "active": True,
                                              "release": release["id"], "target": target}
            self.save_state(state, sha)
        return {"id": identifier, "release": release["id"], "url": release["html_url"], "state": "archived"}

    def retrieve(self, identifier: str, destination: Path, *, target: str) -> dict:
        self.private()
        release = self.release(identifier)
        if not release or release["draft"]:
            raise APIError("Complete archived candidate is not available")
        if destination.exists():
            raise ValueError("Download destination must be new; reuse or verify an existing local candidate")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="archive-download-", dir=destination.parent) as temporary:
            self.command(["release", "download", identifier, "--repo", self.repository,
                          "--pattern", "product.tar.gz", "--pattern", "manifest.json", "--dir", temporary])
            downloaded = Path(temporary)
            manifest = json.loads((downloaded / "manifest.json").read_text(encoding="utf-8"))
            if manifest.get("id") != identifier:
                raise APIError("Retrieved a different candidate")
            packages.verify(downloaded / "product.tar.gz", manifest, target=target)
            downloaded.rename(destination)
        return manifest

    def prune(self, *, execute: bool = False) -> dict:
        self.private()
        state, _ = self.load_state()
        candidates = expired_packages(state, datetime.now(timezone.utc))
        if not execute:
            return {"state": "preview", "expired": candidates}
        removed = []
        for identifier in candidates:
            state, sha = self.load_state()
            if identifier not in expired_packages(state, datetime.now(timezone.utc)):
                continue
            # Claim exclusion before deleting bytes. A concurrent publication
            # changes the same state SHA; it cannot silently lose its package.
            info = state["packages"][identifier]
            info.update(complete=False, eligible=False, deleting=True)
            self.save_state(state, sha)
            release = self.release(identifier)
            if release:
                if release["id"] != info["release"]:
                    raise APIError("Archive release identity changed during cleanup")
                self.api(f"repos/{self.repository}/releases/{release['id']}", method="DELETE")
            if self.release(identifier) is not None:
                raise APIError("Release deletion is not yet confirmed; keep cleanup state")
            state, sha = self.load_state()
            if not state["packages"].get(identifier, {}).get("deleting"):
                raise Conflict("Cleanup state changed; inspect the remaining archive reference")
            del state["packages"][identifier]
            self.save_state(state, sha)
            removed.append(identifier)
        return {"state": "cleaned", "removed": removed}
