"""Prepare complete, fixed facts before a mutable classification batch starts.

Collection and read-only classifiers never call the network. Preparation writes
only facts and their rule metadata, retaining an immutable, resumable snapshot.
"""
from __future__ import annotations

from hashlib import sha256
from copy import deepcopy
from contextvars import ContextVar
from functools import wraps
import json
import os
from pathlib import Path
import re
from urllib.parse import urlencode, urlsplit
from uuid import uuid4

import requests
import yaml

from .classifier_cards import read_card_facts, resolve_card_name
from .classifier_fact_builder import build
from .card_names import normalize_card_name

FACTS = "src/mtgmeta/data/classifier_card_facts.json"
BULK = "https://api.scryfall.com/bulk-data/oracle-cards"
HEADERS = {"User-Agent": "mtgo-data/1.0 (classifier preparation)", "Accept": "application/json"}
MAX_BYTES = 128 * 1024 * 1024
_batch: ContextVar[dict | None] = ContextVar("facts_preparation_batch", default=None)


def facts_preparation_batch(function):
    """Share one fixed preparation across the existing nested producer calls."""
    @wraps(function)
    def run(*args, **kwargs):
        token = _batch.set({})
        try:
            return function(*args, **kwargs)
        finally:
            _batch.reset(token)
    return run


class FactsPreparationError(ValueError):
    pass


def _download(url: str) -> bytes:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not (
        parsed.hostname == "api.scryfall.com"
        or (parsed.hostname or "").endswith(".scryfall.io")
    ):
        raise FactsPreparationError("Untrusted card-fact source")
    with requests.get(url, headers=HEADERS, timeout=(10, 60), stream=True) as response:
        response.raise_for_status()
        chunks = []
        size = 0
        for chunk in response.iter_content(1024 * 1024):
            size += len(chunk)
            if size > MAX_BYTES:
                raise FactsPreparationError("Card-fact source is too large")
            chunks.append(chunk)
        return b"".join(chunks)


def _bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _names(value):
    if isinstance(value, list):
        for item in value:
            yield from _names(item)
    elif isinstance(value, dict):
        if isinstance(value.get("name"), str) and any(k in value for k in ("qty", "quantity")):
            yield value["name"]
        attributes = value.get("card_attributes")
        if isinstance(attributes, dict) and isinstance(attributes.get("card_name"), str):
            yield attributes["card_name"]
        if isinstance(value.get("card"), str):
            yield value["card"]
        if isinstance(value.get("cards"), list):
            yield from (c for c in value["cards"] if isinstance(c, str))
        if isinstance(value.get("card_uses"), dict):
            yield from value["card_uses"]
        for item in value.values():
            if isinstance(item, (dict, list)):
                yield from _names(item)


def require_facts(names, facts):
    missing = sorted({n for n in names if not n.startswith("__classifier-semantic-")
                      and resolve_card_name(n, facts) not in facts.cards})
    if missing:
        raise FactsPreparationError("Classification input facts are incomplete: " + ", ".join(missing))


def prepare_repository_facts(root: Path, formats, *, input_paths=None,
                             oracle_gzip: Path | None = None, source_uri=None,
                             refresh=True, download=None) -> dict:
    """Prepare a new batch on its mutable root; fixed reviews stay unchanged.

    Explicit source/transport arguments support retained-source continuation.
    A completed snapshot is saved before updating the root's technical bindings.
    An exception rolls back all touched files; the snapshot remains recoverable.
    """
    root = Path(root).resolve()
    if (root / ".classifier-facts/pending.json").exists():
        raise FactsPreparationError("Resume interrupted fact preparation before starting a new batch")
    formats = tuple(dict.fromkeys(formats))
    if not formats or any(not re.fullmatch(r"[a-z][a-z0-9-]*", f) for f in formats):
        raise FactsPreparationError("Preparation requires explicit formats")
    batch = _batch.get()
    saved = batch.get(str(root)) if batch is not None else None
    if saved and set(formats) <= set(saved["formats"]):
        if sha256((root / FACTS).read_bytes()).hexdigest() != saved["result"]["facts_sha256"]:
            raise FactsPreparationError("Fixed batch facts changed during generation")
        return {**saved["result"], "requests": 0, "reused_batch": True}
    registry_path = root / "configs/formats.yaml"
    registry = None
    if registry_path.is_file():
        from .config import load_format_registry
        registry = load_format_registry(registry_path)
        for f in formats:
            registry.get(f)
    facts_path = root / FACTS
    # Older, fact-independent rule schemas remain valid for legacy consumers.
    selected_rules = [root / "my_archetypes" / (f + ".yaml") for f in formats]
    if all(yaml.safe_load(p.read_bytes()).get("schema_version") in {"1.0.0", "1.1.0"}
           for p in selected_rules):
        return {"snapshot": None, "requests": 0, "changed": False, "legacy_rules": True}
    old_bytes = facts_path.read_bytes()
    old = json.loads(old_bytes)
    facts = read_card_facts(facts_path)
    rules = sorted((root / "my_archetypes").glob("*.yaml"))
    if input_paths is not None:
        paths = list(input_paths)
    else:
        paths = []
        if registry is not None:
            for f in formats:
                directory = registry.get(f).mtgo.paths.resolve(root)["events"]
                paths.extend(directory.glob("*.json"))
        else:
            for f in formats:
                paths.extend((root / "data" / f).glob("*.json"))
                paths.extend((root / "data" / f / "mtgo/events").glob("*.json"))
        for f in formats:
            paths.extend((root / "data" / f / "melee/events").glob("*.json"))
    inputs = {}
    names = set()
    for path in [*paths, *rules]:
        path = Path(path).resolve()
        if not path.is_relative_to(root):
            raise FactsPreparationError("Classification input escapes the preparation root")
        payload = path.read_bytes()
        inputs[path.relative_to(root).as_posix()] = sha256(payload).hexdigest()
        names.update(_names(yaml.safe_load(payload) if path.suffix == ".yaml" else json.loads(payload)))
    missing = {n for n in names if not n.startswith("__classifier-semantic-")
               and resolve_card_name(n, facts) not in facts.cards}
    transport = download or _download
    home = root / ".classifier-facts"
    home.mkdir(exist_ok=True)
    lock = home / "preparing"
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise FactsPreparationError("Another fact preparation is active; resume it before starting a new one") from exc
    try:
        request_count = 0
        source_error = None
        source = oracle_gzip
        uri = source_uri
        if source is None and (refresh or missing):
            try:
                request_count += 1
                definition = json.loads(transport(BULK))
                if definition.get("object") != "bulk_data" or definition.get("type") != "oracle_cards":
                    raise FactsPreparationError("Invalid Oracle bulk definition")
                uri = definition.get("jsonl_download_uri")
                parsed = urlsplit(uri or "")
                if parsed.scheme != "https" or not (parsed.hostname or "").endswith(".scryfall.io") or not parsed.path.endswith(".jsonl.gz"):
                    raise FactsPreparationError("Oracle source is not a trusted JSONL gzip")
                if uri != old["source"]["uri"] or missing:
                    cache = home / "cache"
                    cache.mkdir(exist_ok=True)
                    source = cache / (sha256(uri.encode()).hexdigest() + ".jsonl.gz")
                    if not source.is_file():
                        request_count += 1
                        data = transport(uri)
                        temporary = source.with_suffix(".tmp")
                        temporary.write_bytes(data)
                        os.replace(temporary, source)
            except (OSError, ValueError, requests.RequestException) as exc:
                source_error = str(exc)
        value = deepcopy(old)
        if source is not None:
            cache = home / "cache"
            cache.mkdir(exist_ok=True)
            source_bytes = Path(source).read_bytes()
            retained_source = cache / (sha256(source_bytes).hexdigest() + ".jsonl.gz")
            if not retained_source.exists():
                retained_source.write_bytes(source_bytes)
            # Additive initial expansion preserves reviewed entities. Later
            # source revisions are imported as revisions, never hidden updates.
            value = build(Path(source), None, uri or old["source"]["uri"],
                          existing=old, preserve_existing="coverage" not in old["source"])
            value["source"]["coverage"] = "complete-constructed-v1"
        temporary = home / ("candidate-" + uuid4().hex + ".json")
        temporary.write_bytes(_bytes(value))
        try:
            candidate = read_card_facts(temporary)
            remaining = sorted(n for n in names if not n.startswith("__classifier-semantic-")
                               and resolve_card_name(n, candidate) not in candidate.cards)
            if remaining:
                # Missing from a current bulk export: ask only for exact names.
                from .classifier_fact_builder import spellings
                import gzip
                supplements = []
                evidence = []
                for name in remaining:
                    exact_name = normalize_card_name(name)
                    request_count += 1
                    response = transport("https://api.scryfall.com/cards/named?" + urlencode({"exact": exact_name}))
                    card = json.loads(response)
                    if card.get("object") != "card" or not card.get("oracle_id") or not any(
                        exact_name == normalize_card_name(spelling) for spelling in spellings(card)
                    ):
                        raise FactsPreparationError("Exact card identity could not be established: " + name)
                    response_path = home / (sha256(response).hexdigest() + ".response.json")
                    response_path.write_bytes(response)
                    evidence.append({"oracle_id": card["oracle_id"],
                                     "uri": "https://api.scryfall.com/cards/named?" + urlencode({"exact": exact_name}),
                                     "response_sha256": sha256(response).hexdigest(),
                                     "response_path": response_path.relative_to(root).as_posix()})
                    supplements.append(card)
                supplemental_source = home / ("supplement-" + uuid4().hex + ".jsonl.gz")
                with gzip.open(supplemental_source, "wt", encoding="utf-8") as handle:
                    for card in supplements:
                        handle.write(json.dumps(card) + "\n")
                extra = build(supplemental_source, [c["name"] for c in supplements], "https://api.scryfall.com/cards/named")
                by_id = {c["oracle_id"]: c for c in value["cards"]}
                by_id.update({c["oracle_id"]: c for c in extra["cards"]})
                value["cards"] = sorted(by_id.values(), key=lambda c: (c["name"], c["oracle_id"]))
                value["source"].setdefault("supplements", []).extend(evidence)
                temporary.write_bytes(_bytes(value))
                candidate = read_card_facts(temporary)
            require_facts(names, candidate)
            # Preserve bytes and bindings when a source check adds no facts.
            new_bytes = old_bytes if value["cards"] == old["cards"] else temporary.read_bytes()
            candidate_digest = sha256(new_bytes).hexdigest()
            old_entities = {c["oracle_id"]: c for c in old["cards"]}
            revised = [{"oracle_id": c["oracle_id"], "name": c["name"],
                        "fields": sorted(k for k in c if c.get(k) != old_entities[c["oracle_id"]].get(k))}
                       for c in value["cards"] if c["oracle_id"] in old_entities and c != old_entities[c["oracle_id"]]]
            replacements = {facts_path: new_bytes}
            for path in rules:
                text = path.read_text(encoding="utf-8")
                text = re.sub(r"(?m)^([ \t]*['\"]?card_facts_sha256['\"]?:[ \t]*)['\"]?[a-f0-9]{64}['\"]?",
                              lambda m: m[1] + candidate_digest, text)
                bound = yaml.safe_load(text)
                if bound.get("schema_version") == "1.2.0" and bound.get("card_facts_sha256") != candidate_digest:
                    raise FactsPreparationError("Cannot bind rules to the prepared facts: " + str(path))
                replacements[path] = text.encode("utf-8")
            material = {p.relative_to(root).as_posix(): sha256(b).hexdigest()
                        for p, b in replacements.items()}
            snapshot_id = sha256(json.dumps({"files": material, "inputs": inputs}, sort_keys=True).encode()).hexdigest()
            snapshot = home / snapshot_id
            if not snapshot.exists():
                pending = home / ("snapshot-" + uuid4().hex)
                pending.mkdir()
                for path, payload in replacements.items():
                    target = pending / path.relative_to(root)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(payload)
                for evidence in value["source"].get("supplements", []):
                    relative = evidence.get("response_path")
                    if relative and (root / relative).is_file():
                        dependency = (root / relative).resolve()
                        if not dependency.is_relative_to(root):
                            raise FactsPreparationError("Fact evidence escapes root")
                        target = pending / relative
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(dependency.read_bytes())
                # Semantic dependencies travel with the fixed rule snapshots.
                for path in rules:
                    semantic = yaml.safe_load(path.read_bytes()).get("semantic_features")
                    if semantic:
                        relative = semantic["manifest_path"]
                        dependency = (root / relative).resolve()
                        if not dependency.is_relative_to(root):
                            raise FactsPreparationError("Semantic dependency escapes root")
                        target = pending / relative
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(dependency.read_bytes())
                (pending / "preparation.json").write_bytes(_bytes({"facts_sha256": candidate_digest, "files": material, "inputs": inputs,
                    "oracle_source": retained_source.relative_to(root).as_posix() if source is not None else None,
                    "existing_fact_revisions": revised}))
                os.replace(pending, snapshot)
            for relative, expected in material.items():
                if sha256((snapshot / relative).read_bytes()).hexdigest() != expected:
                    raise FactsPreparationError("Retained fact snapshot is damaged: " + relative)
            if facts_path.read_bytes() != old_bytes or any(
                sha256((root / relative).read_bytes()).hexdigest() != expected
                for relative, expected in inputs.items()
            ):
                raise FactsPreparationError("Classification inputs changed during preparation; retain this snapshot and prepare the new inputs")
            backups = {p: p.read_bytes() for p in replacements}
            pending_install = home / "pending.json"
            pending_install.write_bytes(_bytes({"snapshot": snapshot.name,
                "previous": {p.relative_to(root).as_posix(): sha256(b).hexdigest() for p, b in backups.items()}}))
            try:
                for path, payload in replacements.items():
                    if payload != backups[path]:
                        staging = path.with_name(path.name + ".preparing")
                        staging.write_bytes(payload)
                        os.replace(staging, path)
            except BaseException:
                for path, payload in backups.items():
                    staging = path.with_name(path.name + ".preparing")
                    staging.write_bytes(payload)
                    os.replace(staging, path)
                pending_install.unlink(missing_ok=True)
                raise
            else:
                pending_install.unlink(missing_ok=True)
            result = {"snapshot": str(snapshot), "facts_sha256": candidate_digest,
                    "entities": len(candidate.cards), "requests": request_count,
                    "existing_fact_revisions": revised,
                    "source_error": source_error, "changed": new_bytes != old_bytes}
            if batch is not None:
                batch[str(root)] = {"formats": formats, "result": result}
            return result
        finally:
            temporary.unlink(missing_ok=True)
    finally:
        lock.rmdir()


def resume_repository_facts(root: Path) -> dict:
    """Complete an interrupted installation from its already verified snapshot.

    Call only after the original preparation process has stopped. No source
    lookup, collection, or classification occurs during this continuation.
    """
    root = Path(root).resolve()
    home = root / ".classifier-facts"
    pending = home / "pending.json"
    installation = json.loads(pending.read_bytes())
    name = installation["snapshot"]
    if not re.fullmatch(r"[a-f0-9]{64}", name):
        raise FactsPreparationError("Invalid pending fact snapshot")
    snapshot = home / name
    record = json.loads((snapshot / "preparation.json").read_bytes())
    payloads = {}
    for relative, expected in record["files"].items():
        target = (root / relative).resolve()
        source = (snapshot / relative).resolve()
        if not target.is_relative_to(root) or not source.is_relative_to(snapshot):
            raise FactsPreparationError("Snapshot path escapes root")
        if relative != FACTS and not re.fullmatch(r"my_archetypes/[a-z0-9-]+\.yaml", relative):
            raise FactsPreparationError("Snapshot contains an unexpected installation path")
        payload = source.read_bytes()
        if sha256(payload).hexdigest() != expected:
            raise FactsPreparationError("Pending fact snapshot is damaged")
        previous = installation.get("previous", {}).get(relative)
        if previous and sha256(target.read_bytes()).hexdigest() not in {previous, expected}:
            raise FactsPreparationError("Preparation files changed after interruption; preserve and reconcile those edits")
        payloads[target] = payload
    for path, payload in payloads.items():
        staging = path.with_name(path.name + ".preparing")
        staging.write_bytes(payload)
        os.replace(staging, path)
    pending.unlink()
    lock = home / "preparing"
    if lock.is_dir():
        lock.rmdir()
    return {"snapshot": str(snapshot), "facts_sha256": record["facts_sha256"], "resumed": True}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--format", action="append", default=[])
    parser.add_argument("--oracle-gzip", type=Path)
    parser.add_argument("--source-uri")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    result = (resume_repository_facts(args.root) if args.resume else
              prepare_repository_facts(args.root, args.format, oracle_gzip=args.oracle_gzip, source_uri=args.source_uri))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
