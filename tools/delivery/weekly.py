"""Finite continuation of one fixed data or content delivery.

The record locates existing facts; it is neither an approval nor a verifier.
"""
from __future__ import annotations

import json
from pathlib import Path
import uuid

from mtgmeta.resource_progress import save
from mtgmeta.generation_progress import files
from tools.delivery import packages, commands


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def create_record(path, *, kind, root, site, scope, references, source, target="Jacelber/mtgo-data"):
    path, root = Path(path).resolve(), Path(root).resolve()
    if kind not in {"reviewed_data", "landing_content"}:
        raise ValueError("Unknown delivery type")
    refs = [{"path": str(Path(p).resolve()), "sha256": packages.sha256(Path(p))} for p in references]
    identity = {"kind": kind, "root": str(root), "scope": scope, "references": refs,
                "site": str(Path(site).resolve()) if site else None, "source": source, "target": target,
                "site_files": files(Path(site), ["**/*"]) if site else None}
    from tools.delivery.verification import material_snapshot
    identity["material"] = material_snapshot(root, scope)
    if path.exists():
        previous = read(path)
        if previous["identity"] != identity:
            raise ValueError("Existing handoff names different material; preserve it")
        return previous
    record = {"schema": 1, "identity": identity, "operation": "weekly-" + uuid.uuid4().hex,
              "progress": {}, "history": []}
    save(path, record)
    return record


class Remote:
    """Adapter to existing delivery operations; construction has no side effects."""
    def prepare(self, record):
        return commands.preflight(record["identity"]["target"], record["operation"])

    def archive(self, record, candidate):
        from tools.pages_writer import context
        archive, _ = context(record["identity"]["target"])
        archive.private()
        return archive.archive(candidate, target=record["identity"]["target"])

    def remember(self, record, package):
        commands.remember_candidate(record["identity"]["target"], record["operation"],
                                    package, record["progress"]["base"])

    def send(self, record, mode):
        return commands.dispatch(record["identity"]["target"], record["operation"],
                                 record["progress"]["package"], record["progress"].get("base"),
                                 mode, preparation=record["operation"], automatic=True)

    def query_original(self, record):
        return commands.query_operation(record["identity"]["target"], record["operation"])

    def retrieve(self, record, package, destination):
        from tools.pages_writer import context
        archive, _ = context(record["identity"]["target"])
        return archive.retrieve(package, destination, target=record["identity"]["target"])

    def observe(self, record):
        identity = record["identity"]
        value = commands.status(identity["target"], record["operation"])
        return value["control"]

def inspect(path, *, remote=None):
    record = read(path)
    if record.get("schema") != 1:
        raise ValueError("Unsupported handoff record")
    identity, progress = record["identity"], record["progress"]
    if identity["target"] not in {"Jacelber/mtgo-data", "Jacelber/mtgo-data-governance-verification"}:
        raise ValueError("Unsupported delivery target")
    observed = (remote or Remote()).observe(record)
    current, pending = observed.get("current"), observed.get("pending")
    if current and current["operation"] == record["operation"]:
        if current["package"] != progress.get("package"):
            raise ValueError("Operation and selected package differ")
        return {"next": "complete" if current.get("health") == "passed" else "verify",
                "observed": observed, "kind": identity["kind"]}
    if pending and pending["operation"] == record["operation"]:
        return {"next": "resume", "observed": observed}
    if progress.get("send_started"):
        # A missing remote record is not evidence that a timed-out request failed.
        return {"next": "query_original", "operation": record["operation"], "observed": observed}
    if pending or observed.get("recovery"):
        return {"next": "wait_existing", "observed": observed}
    base = current["operation"] if current else None
    if "base" in progress and progress["base"] != base:
        return {"next": "composition_changed", "original_base": progress["base"], "current_base": base}
    for reference in identity["references"]:
        source = Path(reference["path"])
        if not source.is_file() or packages.sha256(source) != reference["sha256"]:
            return {"next": "material_changed", "path": str(source)}
    from tools.delivery.verification import material_snapshot
    if identity.get("material") != material_snapshot(Path(identity["root"]), identity["scope"]):
        return {"next": "material_changed", "path": identity["root"],
                "detail": "Candidate inputs, policy or public products changed; compare with the confirmed scope"}
    if progress.get("package"):
        return {"next": "publish", "observed": observed}
    if progress.get("candidate"):
        candidate = Path(progress["candidate"])
        packages.verify(candidate / "product.tar.gz", read(candidate / "manifest.json"), target=identity["target"])
        return {"next": "archive", "observed": observed}
    site = progress.get("site") or identity["site"]
    if site and Path(site).is_dir():
        expected = progress.get("site_files") or identity.get("site_files")
        if expected is not None and files(Path(site), ["**/*"]) != expected:
            return {"next": "material_changed", "path": site, "detail": "Fixed site bytes changed"}
        return {"next": "package", "site": site, "observed": observed}
    return {"next": "resources", "root": identity["root"], "observed": observed}


def continue_delivery(path, *, remote=None, verify=None, resources=None):
    """Advance existing actions, checkpointing before uncertain remote effects."""
    remote = remote or Remote()
    if verify is None:
        from tools.delivery.verification import verify_material
        verify = verify_material
    path = Path(path).resolve()
    record = read(path)
    work = path.parent / (path.stem + ".work")
    work.mkdir(parents=True, exist_ok=True)
    for _ in range(12):
        state = inspect(path, remote=remote)
        action = state["next"]
        progress, identity = record["progress"], record["identity"]
        if action == "query_original":
            queried = remote.query_original(record)
            record["history"].append({"action": action, "result": queried})
            save(path, record)
            if queried["state"] == "recorded":
                continue
            return queried
        if action in {"wait_existing", "composition_changed", "material_changed"}:
            return state
        if action == "complete":
            # This is the delivery fact. A data delivery never writes weekly completion.
            progress["delivered"] = {"kind": identity["kind"], "current": state["observed"]["current"]}
            if identity["kind"] == "landing_content" and not progress.get("content_completion"):
                from tools.review_submission import confirmed_completions
                candidate = Path(progress["candidate"]) if progress.get("candidate") else work / "delivered-package"
                if not candidate.exists():
                    remote.retrieve(record, progress["package"], candidate)
                envelopes = [read(item["path"]) for item in identity["references"]]
                selected = []
                for fmt in identity["scope"]["mtgo_formats"]:
                    matching = [e for e in envelopes if e.get("submission", {}).get("kind") == "preview"
                                and e["submission"].get("format") == fmt]
                    if len(matching) != 1:
                        raise ValueError(f"Expected one existing final page acceptance for {fmt}")
                    selected.append(matching[0])
                progress["content_completion"] = confirmed_completions(selected, candidate, state["observed"], target=identity["target"])
            save(path, record)
            return {"state": "delivered", "kind": identity["kind"], "operation": record["operation"],
                    "weekly_completion": "not_implied"}
        if action in {"resume", "verify"}:
            result = remote.send(record, "resume")
            record["history"].append({"action": action, "result": result})
            save(path, record)
            if result.get("state") in {"already_submitted", "waiting", "unknown", "submitted"}:
                return result
            continue
        if "base" not in progress:
            preparation = remote.prepare(record)
            if preparation["state"] != "ready":
                return preparation
            progress["base"] = preparation["base"]
            if preparation.get("package"):
                progress["package"] = preparation["package"]
            save(path, record)
            if progress.get("package"):
                continue
        try:
            if action == "resources":
                if resources is None:
                    from tools.delivery.resources import prepare_site
                    resources = prepare_site
                progress["site"] = str(resources(record, work))
                progress["site_files"] = files(Path(progress["site"]), ["**/*"])
            elif action == "package":
                site = Path(state["site"])
                candidate = work / "package"
                if candidate.exists():
                    manifest = read(candidate / "manifest.json")
                    packages.verify(candidate / "product.tar.gz", manifest, target=identity["target"])
                else:
                    manifest = packages.prepare(site, candidate, target=identity["target"], source=identity["source"])
                progress["candidate"] = str(candidate)
            elif action == "archive":
                candidate = Path(progress["candidate"])
                from tools.delivery.verification import verify_once
                verification = verify_once(record, candidate, lambda: save(path, record), verifier=verify)
                record['history'].append({'action': 'material_verification', 'state': verification})
                if not progress.get("archived"):
                    result = remote.archive(record, candidate)
                    progress["archived"] = result["id"]
                    save(path, record)
                remote.remember(record, progress["archived"])
                progress["package"] = progress["archived"]
            elif action == "publish":
                candidate = Path(progress["candidate"]) if progress.get("candidate") else work / "archived-package"
                if not candidate.exists():
                    remote.retrieve(record, progress["package"], candidate)
                manifest = read(candidate / "manifest.json")
                if manifest["id"] != progress["package"]:
                    raise ValueError("Archived package differs from selected candidate")
                from tools.delivery.verification import verify_once
                verification = verify_once(record, candidate, lambda: save(path, record), verifier=verify)
                record['history'].append({'action': 'material_verification', 'state': verification})
                progress["send_started"] = True
                save(path, record)
                result = remote.send(record, "publish")
                record["history"].append({"action": action, "result": result})
                save(path, record)
                if result.get("state") in {"submitted", "already_submitted", "waiting", "unknown"}:
                    return result
                if result.get("state") in {"publication_paused", "recovery_required"}:
                    progress.pop("send_started", None)
                    save(path, record)
                    return result
            record["history"].append({"action": action, "state": "done"})
            progress.pop("failure", None)
            save(path, record)
        except (OSError, ValueError, RuntimeError) as error:
            progress["failure"] = {"action": action, "type": type(error).__name__, "detail": str(error)}
            save(path, record)
            return {"state": "repair_required", **progress["failure"], "record": str(path)}
    return {"state": "waiting", "operation": record["operation"]}
