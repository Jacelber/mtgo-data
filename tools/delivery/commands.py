"""Manual/task delivery entry. Decisions stay with the task, operation facts with GitHub."""
from __future__ import annotations

import re
from tools.delivery import state as transitions
from tools.pages_writer import context, resume_completed, reconcile_pending


def remember_candidate(target: str, preparation: str, package: str, base: str | None) -> None:
    """Keep the archived result discoverable by the same preparation ID."""
    archive, _ = context(target)
    archive.private()
    state, sha = archive.load_state()
    info = state['packages'].get(package, {})
    if not info.get('complete') or info.get('target') != target:
        raise transitions.Conflict('Preparation result is not fully archived for this target')
    for identifier, other in state['packages'].items():
        if preparation in other.get('preparations', {}) and identifier != package:
            raise transitions.Conflict('Preparation already names another archived package; preserve it')
    recorded = info.setdefault('preparations', {})
    if preparation in recorded:
        if recorded[preparation] != base:
            raise transitions.Conflict('Original preparation base cannot be changed')
        return
    recorded[preparation] = base
    archive.save_state(state, sha)


def preflight(target: str, preparation: str | None = None, *, archived_package: str | None = None,
              archived_base: str | None = None, archived_preparation: str | None = None) -> dict:
    """Resolve old facts before expensive preparation; acquire no writer lock."""
    archive, pages = context(target)
    archive.private()
    state, sha = archive.load_state()
    observation = None
    if state["pending"]:
        pending = state["pending"]
        if pending.get("run"):
            run = pages.client.api(f"repos/{target}/actions/runs/{pending['run']}")
            if run["status"] != "completed":
                return {"state": "waiting", "operation": pending["operation"], "run": run["id"]}
        observation = reconcile_pending(archive, pages, state, sha, target=target)
        state, sha = archive.load_state()
        if state["pending"]:
            return {"state": "waiting", "operation": state["pending"]["operation"], "observation": observation}
    if (observation is None and state['current']
            and state['current'].get('health') == 'unknown'):
        observation = resume_completed(archive, pages, state, sha, target=target,
                                       operation=state['current']['operation'])
        state, sha = archive.load_state()
    if state["recovery"]:
        return {"state": "recovery_required", "recovery": state["recovery"], "observation": observation}
    current = state["current"]
    expected = current["remote"]["deployment_id"] if current else None
    actual = pages.current(expected=expected)
    if not current and actual:
        raise transitions.Conflict("Existing deployment needs its actual archived baseline")
    result = {"state": "ready", "base": transitions.current_id(state),
              "current": current, "observation": observation}
    if archived_package:
        result.update(transitions.archived_preparation(state, archived_package, archived_base, archived_preparation))
    elif preparation:
        matches = [(key, info['preparations'][preparation]) for key, info in state['packages'].items()
                   if preparation in info.get('preparations', {})]
        if len(matches) > 1:
            raise transitions.Conflict('Ambiguous archived preparation; preserve all candidates')
        if matches:
            result.update(transitions.archived_preparation(state, matches[0][0], matches[0][1], preparation))
    if result.get('package'):
        if state['packages'][result['package']].get('target') != target:
            raise transitions.Conflict('Archived candidate belongs to another target')
        already_current = (current and current['operation'] == preparation
                           and current['package'] == result['package'])
        if result['candidate_base'] != result['base'] and not already_current:
            raise transitions.Conflict(f"Candidate {result['package']} retained: stale combination; do not rebuild or rebase")
    return result


def dispatch(target: str, operation: str, package: str, base: str | None, mode: str, reason: str = "",
             *, automatic: bool = False, preparation: str | None = None) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", operation):
        raise ValueError("Use the same short operation ID for continuation")
    archive, pages = context(target)
    archive.private()
    state, sha = archive.load_state()
    if mode == 'publish':
        selected = transitions.archived_preparation(state, package, base, preparation)
        preparation, base = selected['preparation'], selected['candidate_base']
    if transitions.current_id(state) == operation and not state["pending"]:
        if mode == 'publish' and state['current']['package'] != package:
            raise transitions.Conflict('Operation is already bound to another package')
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
            if pending.get("remote") or pending.get("phase") != "claimed":
                return reconcile_pending(archive, pages, state, sha, target=target)
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
        if state["pending"]:
            result = preflight(target)
            if result['state'] != 'ready':
                return {**result, 'package': package, 'candidate_base': base}
            state, sha = archive.load_state()
            if transitions.current_id(state) == operation and not state['pending']:
                return resume_completed(archive, pages, state, sha, target=target, operation=operation)
        if state["pending"] or state["recovery"] or base != transitions.current_id(state):
            raise transitions.Conflict(
                f"Candidate {package} retained at base {base!r}; resolve the current write/recovery or stale "
                "combination, then deliver this archived package. Do not rerun preparation.")
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
                               "reason": reason, "automatic": str(automatic).lower(), "preparation": preparation or ""}})
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
