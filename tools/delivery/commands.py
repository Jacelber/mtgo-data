"""Manual/task delivery entry. Decisions stay with the task, operation facts with GitHub."""
from __future__ import annotations

import re
from tools.delivery import state as transitions
from tools.pages_writer import context, resume_completed


def dispatch(target: str, operation: str, package: str, base: str | None, mode: str, reason: str = "",
             *, automatic: bool = False) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", operation):
        raise ValueError("Use the same short operation ID for continuation")
    archive, pages = context(target)
    archive.private()
    state, sha = archive.load_state()
    if transitions.current_id(state) == operation and not state["pending"]:
        if mode == "resume":
            return resume_completed(archive, pages, state, sha, target=target, operation=operation)
        health = state["current"].get("health", "unknown")
        return {"state": "already_recorded" if health == "passed" else health, "current": state["current"]}
    if mode == "resume":
        pending = state["pending"]
        if not pending or pending["operation"] != operation:
            intent = state["recovery"]
            if not intent or intent["id"] != operation:
                raise transitions.Conflict("No recorded operation or recovery intent to resume")
            package, base, mode, reason = intent["package"], intent["failed_operation"], "recovery", intent["reason"]
        else:
            package, base = pending["package"], pending["base"]
            automatic = pending.get("automatic", True)
            if pending.get("run"):
                original = pages.client.api(f"repos/{target}/actions/runs/{pending['run']}")
                if original["status"] != "completed":
                    return {"state": "already_submitted", "run": original["id"], "url": original["html_url"]}
    elif mode == "recovery":
        info = state["packages"].get(package, {})
        if not info.get("complete") or info.get("target") != target:
            raise transitions.Conflict("Recovery candidate is not completely archived for this target")
        state = transitions.request_recovery(state, intent=operation, failed_operation=base,
                                             package=package, reason=reason)
        # This precedes workflow submission, so queue replacement/cancellation
        # cannot erase the recovery decision.
        archive.save_state(state, sha)
    elif mode == "publish":
        if automatic and state.get("automatic_publication_pause"):
            return {"state": "publication_paused", "pause": state["automatic_publication_pause"],
                    "next": "Preparation may continue; release requires Owner instruction or prior authorization"}
        if state["pending"] or state["recovery"] or base != transitions.current_id(state):
            raise transitions.Conflict("Resolve the current write/recovery or stale candidate base first")
    else:
        raise ValueError("Unsupported operation mode")
    info = state["packages"].get(package, {})
    if not info.get("complete") or info.get("target") != target:
        raise transitions.Conflict("Selected candidate is not completely archived for this target")
    runs = pages.client.api(f"repos/{target}/actions/workflows/pages.yml/runs?per_page=100")["workflow_runs"]
    for run in runs:
        if run.get("display_title", "").startswith(f"{operation} (") and run["status"] != "completed":
            return {"state": "already_submitted", "run": run["id"], "url": run["html_url"]}
    ref = "master" if target == "Jacelber/mtgo-data" else "main"
    pages.client.api(f"repos/{target}/actions/workflows/pages.yml/dispatches", method="POST", body={
        "ref": ref, "inputs": {"operation": operation, "package": package, "base": base or "", "mode": mode,
                               "reason": reason, "automatic": str(automatic).lower()}})
    return {"state": "submitted", "operation": operation, "target": target,
            "next": "Query this operation; do not invent a new ID after an uncertain response"}


def enable_automatic(target: str, recovery: str, reason: str) -> dict:
    archive, _ = context(target)
    archive.private()
    state, sha = archive.load_state()
    updated = transitions.enable_automatic_publication(state, recovery=recovery, reason=reason)
    if updated != state:
        archive.save_state(updated, sha)
    return {"state": "automatic_publication_enabled", "target": target, "dispatch_started": False}


def status(target: str, operation: str | None = None) -> dict:
    archive, pages = context(target)
    archive.private()
    state, _ = archive.load_state()
    result = {"control": state}
    pending = state["pending"]
    if pending and (operation is None or pending["operation"] == operation):
        if pending["remote"]:
            result["remote"] = pages.query(pending["remote"]["pages_id"])
        else:
            result["remote"] = {"state": "unknown", "next": "Inspect the original run before repeating a write"}
    return result
