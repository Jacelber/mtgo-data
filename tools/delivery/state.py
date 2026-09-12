"""Transitions for one Pages writer; GitHub contents SHA supplies compare-and-swap."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone


class Conflict(ValueError):
    """The write is stale, unresolved, or conflicts with recovery."""


def initial() -> dict:
    return {"schema": 1, "current": None, "previous": None, "pending": None,
            "recovery": None, "automatic_publication_pause": None, "packages": {}}


def current_id(state: dict) -> str | None:
    return state["current"]["operation"] if state["current"] else None


def request_recovery(state: dict, *, intent: str, failed_operation: str, package: str, reason: str) -> dict:
    """Execute an Owner-directed restore; the caller establishes that instruction."""
    state = deepcopy(state)
    current, previous = state["current"], state["previous"]
    if not reason.strip() or not current or current["operation"] != failed_operation:
        raise Conflict("Recovery requires the selected current deployment and Owner instruction context")
    if not previous or previous["package"] != package:
        raise Conflict("Recovery requires the immediately applicable confirmed predecessor")
    if not state["packages"].get(package, {}).get("eligible", False):
        raise Conflict("Recovery package is not applicable")
    recovery = {"id": intent, "failed_operation": failed_operation, "package": package, "reason": reason}
    if state["recovery"] and state["recovery"] != recovery:
        raise Conflict("Another recovery intent exists")
    state["recovery"] = recovery
    state["automatic_publication_pause"] = {"recovery": intent, "reason": reason}
    return state


def require_publication_enabled(state: dict, *, automatic: bool, recovery: str | None = None) -> None:
    if automatic and not recovery and state.get("automatic_publication_pause"):
        raise Conflict("Automatic publication is paused by Owner-directed recovery; preparation may continue")


def enable_automatic_publication(state: dict, *, recovery: str, reason: str) -> dict:
    """Caller establishes explicit Owner release or fulfilment of prior authorization."""
    state = deepcopy(state)
    if not reason.strip():
        raise Conflict("Specify the Owner instruction or fulfilled prior authorization")
    if state["pending"] or state["recovery"]:
        raise Conflict("Resolve the pending write and recovery before enabling automatic publication")
    pause = state.get("automatic_publication_pause")
    if pause and pause["recovery"] != recovery:
        raise Conflict("Release refers to a different recovery pause")
    state["automatic_publication_pause"] = None
    return state


def claim(state: dict, *, operation: str, package: str, base: str | None, recovery: str | None = None,
          automatic: bool = False) -> dict:
    state = deepcopy(state)
    pending = state["pending"]
    if pending:
        if (pending["operation"], pending["package"], pending["base"], pending["recovery"]) == (operation, package, base, recovery):
            if pending["phase"] == "claimed":
                require_publication_enabled(state, automatic=pending.get("automatic", True), recovery=pending["recovery"])
            return state  # Resume means query, not replay an unknown remote request.
        raise Conflict("An earlier remote write remains unresolved")
    if base != current_id(state):
        raise Conflict("Candidate deployment base is stale, including A-B-A")
    if not state["packages"].get(package, {}).get("complete", False):
        raise Conflict("Package is not fully archived")
    if state["packages"][package].get("failed"):
        raise Conflict("This exact package has a confirmed defect; fix it before publication")
    intent = state["recovery"]
    if intent:
        if (recovery, package, base) != (intent["id"], intent["package"], intent["failed_operation"]):
            raise Conflict("Recorded recovery takes priority over normal publication")
    elif recovery:
        raise Conflict("Recovery intent no longer exists")
    require_publication_enabled(state, automatic=automatic, recovery=recovery)
    state["pending"] = {"operation": operation, "package": package, "base": base,
                        "recovery": recovery, "automatic": automatic, "phase": "claimed", "remote": None}
    return state


def _pending(state: dict, operation: str) -> dict:
    if not state["pending"] or state["pending"]["operation"] != operation:
        raise Conflict("No matching pending operation")
    return state["pending"]


def sending(state: dict, operation: str) -> dict:
    state = deepcopy(state)
    pending = _pending(state, operation)
    if pending["phase"] != "claimed":
        raise Conflict("Already sent or unknown: query instead of replaying")
    intent = state["recovery"]
    if intent and pending["recovery"] != intent["id"]:
        raise Conflict("An Owner recovery request supersedes this unsent publication")
    require_publication_enabled(state, automatic=pending.get("automatic", True), recovery=pending["recovery"])
    pending["phase"] = "sending"
    return state


def bind_remote(state: dict, operation: str, remote: str) -> dict:
    state = deepcopy(state)
    pending = _pending(state, operation)
    if pending["remote"] not in (None, remote):
        raise Conflict("Operation refers to another remote request")
    pending["remote"] = remote
    pending["phase"] = "in_progress"
    return state


def deployed(state: dict, operation: str, remote: str) -> dict:
    state = bind_remote(state, operation, remote)
    pending = state["pending"]
    if current_id(state) == operation:
        pending["phase"] = "confirming"
        return state
    old = state["current"]
    if not pending["recovery"] and old and old.get("health") == "passed" and state["packages"].get(old["package"], {}).get("eligible"):
        state["previous"] = deepcopy(old)
    state["current"] = {"operation": operation, "package": pending["package"], "remote": remote, "health": "unknown"}
    state["packages"][pending["package"]].setdefault("published_at", datetime.now(timezone.utc).isoformat())
    pending["phase"] = "confirming"
    return state


def confirmed(state: dict, operation: str, *, health: str, observed_operation: str) -> dict:
    state = deepcopy(state)
    pending = _pending(state, operation)
    if health not in {"passed", "failed"} or current_id(state) != operation or observed_operation != operation:
        raise Conflict("Confirmation must describe the actual selected deployment")
    state["current"]["health"] = health
    state["packages"][pending["package"]]["eligible"] = health == "passed"
    state["packages"][pending["package"]]["failed"] = health == "failed"
    if health == "passed":
        state["packages"][pending["package"]]["active"] = False
    if pending["recovery"] and health == "passed":
        state["recovery"] = None
    state["pending"] = None
    return state


def no_write(state: dict, operation: str, *, terminal_without_write: bool) -> dict:
    state = deepcopy(state)
    _pending(state, operation)
    if not terminal_without_write or current_id(state) == operation:
        raise Conflict("A missing record does not prove no write occurred")
    state["pending"] = None
    return state  # Queue cancellation does not clear recovery intent.


def end_completed_write(state: dict, operation: str, *, observation: dict, terminal: bool) -> dict:
    """Retain uncertain served content after a proven completed platform write."""
    state = deepcopy(state)
    pending = _pending(state, operation)
    if not terminal or pending["phase"] != "confirming" or current_id(state) != operation:
        raise Conflict("Only the identified completed deployment can end content confirmation")
    if observation.get("state") != "unconfirmed" or not (observation.get("mismatches") or observation.get("platform_status") in {"deployment_failed", "cancelled", "canceled"}):
        raise Conflict("Record the actual unconfirmed/mixed service observation")
    state["current"]["service_observation"] = deepcopy(observation)
    state["current"]["health"] = "unknown"
    state["packages"][pending["package"]]["eligible"] = False
    state["pending"] = None
    return state  # This neither declares a product defect nor decides to restore.


def end_recovery(state: dict, intent: str, *, reason: str) -> dict:
    state = deepcopy(state)
    if state["pending"]:
        raise Conflict("Resolve the actual remote write before clearing intent")
    if not state["recovery"] or state["recovery"]["id"] != intent or not reason.strip():
        raise Conflict("Specify the completed, withdrawn or invalid recovery intent")
    state["recovery"] = None
    return state


def expired_packages(state: dict, now: datetime) -> list[str]:
    protected = {value["package"] for key in ("current", "previous", "pending", "recovery") if (value := state.get(key))}
    expired = []
    for package, value in state["packages"].items():
        if package in protected or value.get("active", True):
            continue
        started = value.get("published_at") or value.get("ended_at")
        if not started:
            continue
        timestamp = datetime.fromisoformat(started.replace("Z", "+00:00"))
        days = 30 if value.get("published_at") else 7
        if now.astimezone(timezone.utc) >= timestamp + timedelta(days=days):
            expired.append(package)
    return expired


def end_candidate(state: dict, package: str, *, reason: str) -> dict:
    """Caller establishes that no active review or diagnosis still needs it."""
    state = deepcopy(state)
    if package not in state["packages"] or not reason.strip():
        raise Conflict("Specify the candidate and its actual completion/cancellation reason")
    if any(value and value["package"] == package for value in (state["pending"], state["recovery"])):
        raise Conflict("The candidate is still involved in an unresolved operation")
    info = state["packages"][package]
    info["active"] = False
    info.setdefault("ended_at", datetime.now(timezone.utc).isoformat())
    return state
