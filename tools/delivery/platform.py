"""Pages API and served-byte observation; queries do not invoke product checks."""
from __future__ import annotations

import hashlib
import json
import os
import re
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen
from urllib.error import URLError

from tools.delivery.github import APIError, GitHub
from tools.delivery.state import Conflict


class Pages:
    def __init__(self, repository: str):
        self.client = GitHub(repository)
        self.repository = repository

    def current(self, *, expected: str | None, own_run: str | None = None) -> dict | None:
        records = self.client.api(f"repos/{self.repository}/deployments?environment=github-pages&per_page=100")
        for record in records:
            statuses = self.client.api(f"repos/{self.repository}/deployments/{record['id']}/statuses?per_page=1")
            status = statuses[0] if statuses else {"state": "unknown"}
            link = status.get("log_url", "")
            match = re.search(r"/actions/runs/(\d+)(?:/|$)", link)
            if own_run and match and match[1] == own_run and status["state"] != "success":
                continue
            if expected is not None and str(record["id"]) == expected:
                return {"id": str(record["id"]), "sha": record["sha"], "state": status["state"]}
            if status["state"] == "success":
                if expected is not None:
                    raise Conflict("Another deployment changed the production base")
                return {"id": str(record["id"]), "sha": record["sha"], "state": "success"}
            if status["state"] in {"failure", "error"} and self.no_send_job(link):
                continue
            if status["state"] != "inactive":
                raise Conflict("Unresolved or external deployment exists; inspect its actual effects")
        if expected is not None:
            raise Conflict("Recorded deployment cannot be located in current platform facts")
        return None

    def no_send_job(self, log_url: str) -> bool:
        """An environment record can fail BEFORE any Pages request was sent."""
        match = re.search(r"/actions/runs/(\d+)/job/(\d+)$", log_url)
        if not match:
            return False
        job = self.client.api(f"repos/{self.repository}/actions/jobs/{match[2]}")
        if job["name"] != "Deploy selected product" or job["status"] != "completed":
            return False
        sends = [step for step in job.get("steps", []) if step["name"] == "Send selected package once"]
        return len(sends) == 1 and sends[0]["conclusion"] == "skipped"

    def operation_record(self, run: str, attempt: str) -> str | None:
        jobs = self.client.api(f"repos/{self.repository}/actions/runs/{run}/attempts/{attempt}/jobs?per_page=100")["jobs"]
        job_ids = {str(job["id"]) for job in jobs if job["name"] == "Deploy selected product"}
        records = self.client.api(f"repos/{self.repository}/deployments?environment=github-pages&per_page=100")
        matching = []
        for record in records:
            statuses = self.client.api(f"repos/{self.repository}/deployments/{record['id']}/statuses?per_page=1")
            if not statuses:
                continue
            match = re.search(r"/actions/runs/(\d+)/job/(\d+)", statuses[0].get("log_url", ""))
            if match and match[1] == run and match[2] in job_ids:
                matching.append(str(record["id"]))
        if len(matching) > 1:
            raise Conflict("Multiple platform operations match this attempt")
        return matching[0] if matching else None

    def attempt_never_sent(self, run: str, attempt: str) -> bool:
        jobs = self.client.api(f"repos/{self.repository}/actions/runs/{run}/attempts/{attempt}/jobs?per_page=100")["jobs"]
        writers = [job for job in jobs if job["name"] == "Deploy selected product"]
        if len(writers) != 1 or writers[0]["status"] != "completed":
            return False
        sends = [step for step in writers[0].get("steps", []) if step["name"] == "Send selected package once"]
        return len(sends) == 1 and sends[0]["conclusion"] == "skipped"

    def create(self, artifact: int) -> dict:
        oidc_url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL", "")
        oidc_auth = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "")
        if not oidc_url or not oidc_auth or urlsplit(oidc_url).scheme != "https":
            raise APIError("Pages creation requires the protected Actions OIDC context")
        request = Request(oidc_url, headers={"Authorization": f"Bearer {oidc_auth}"})
        with urlopen(request, timeout=30) as response:
            oidc = json.load(response)["value"]
        result = self.client.api(f"repos/{self.repository}/pages/deployments", method="POST", body={
            "artifact_id": artifact, "pages_build_version": os.environ["GITHUB_SHA"], "oidc_token": oidc})
        identifier = result.get("id") or result.get("status_url", "").rstrip("/").split("/")[-1]
        if not identifier:
            raise APIError("Request may have been accepted but returned no operation identifier")
        return {"pages_id": str(identifier), "page_url": result.get("page_url")}

    def query(self, identifier: str) -> dict:
        return self.client.api(f"repos/{self.repository}/pages/deployments/{quote(identifier, safe='')}")

    def cancel(self, identifier: str) -> dict:
        return self.client.api(f"repos/{self.repository}/pages/deployments/{quote(identifier, safe='')}/cancel", method="POST")

    def site_url(self) -> str:
        return self.client.api(f"repos/{self.repository}/pages")["html_url"]


def observe_content(base_url: str, manifest: dict, operation: str) -> dict:
    mismatches = []
    for relative, expected in manifest["probes"].items():
        url = f"{base_url.rstrip('/')}/{quote(relative, safe='/')}?delivery={quote(operation, safe='')}"
        request = Request(url, headers={"Cache-Control": "no-cache", "Accept-Encoding": "identity"})
        try:
            with urlopen(request, timeout=30) as response:
                digest = hashlib.file_digest(response, "sha256").hexdigest()
        except (OSError, URLError):
            mismatches.append(relative + " (unavailable; not a confirmed product defect)")
            continue
        if digest != expected:
            mismatches.append(relative)
    return {"state": "matching" if not mismatches else "unconfirmed", "mismatches": mismatches}
