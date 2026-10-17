"""Private, resumable resource work. A work directory is never a release cache."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def save(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".new")
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


class ResourceProgress:
    def __init__(self, path: Path, identity: dict):
        self.path = path
        path.mkdir(parents=True, exist_ok=True)
        self.record = path / "progress.json"
        if self.record.exists():
            self.state = json.loads(self.record.read_text(encoding="utf-8"))
            if self.state["identity"] != identity:
                raise ValueError(f"Resource implementation changed; preserve and inspect work: {path}")
        else:
            self.state = {"identity": identity, "entries": {}, "complete": False}
            save(self.record, self.state)
        self.reused = 0
        self.requests = 0

    def bytes(self, key, fetch, validate):
        identifier = digest(key)
        path = self.path / (identifier + ".bin")
        payload = self.lookup(key, validate)
        if payload is not None:
            self.reused += 1
            return payload
        self.requests += 1
        payload = fetch()
        validate(payload)
        temporary = path.with_suffix(".part")
        temporary.write_bytes(payload)
        temporary.replace(path)
        self.state["entries"][identifier] = {"key": key, "sha256": hashlib.sha256(payload).hexdigest()}
        save(self.record, self.state)
        return payload

    def lookup(self, key, validate):
        identifier = digest(key)
        path = self.path / (identifier + ".bin")
        entry = self.state["entries"].get(identifier)
        if entry and path.is_file():
            payload = path.read_bytes()
            if hashlib.sha256(payload).hexdigest() == entry["sha256"]:
                validate(payload)
                return payload
        return None

    def page(self, names, page, fetch, maximum_pages):
        # Pages are recovery inputs, not selected card entries. The resolver still
        # completes pagination and applies its unchanged selection rules.
        def validate(payload):
            value = json.loads(payload)
            if (value.get("page") != page or not isinstance(value.get("total_pages"), int)
                    or not 0 <= value["total_pages"] <= maximum_pages
                    or not isinstance(value.get("items"), list)
                    or any(not isinstance(item, dict) for item in value["items"])):
                raise ValueError("Invalid resource response; not saved as recovery input")
        payload = self.bytes({"query": names, "page": page},
                             lambda: json.dumps(fetch(names, page), ensure_ascii=False).encode(), validate)
        return json.loads(payload)

    def completed(self):
        self.state["complete"] = True
        save(self.record, self.state)
