"""Protected Pages writer. Product construction and archive upload happen earlier."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.delivery.github import APIError, GitHub  # noqa: E402
from tools.delivery.platform import Pages, observe_content  # noqa: E402
from tools.delivery import packages, state as transitions  # noqa: E402


def context(target: str):
    if target not in {"Jacelber/mtgo-data", "Jacelber/mtgo-data-governance-verification"}:
        raise ValueError("Unsupported deployment target")
    path = "state/pages.json" if target == "Jacelber/mtgo-data" else "state/verification-pages.json"
    credential = "ARCHIVE_TOKEN" if os.environ.get("GITHUB_ACTIONS") == "true" or os.environ.get("ARCHIVE_TOKEN") else None
    return GitHub("Jacelber/mtgo-data-releases", token_env=credential, state_path=path), Pages(target)


def resume_completed(archive, pages, state: dict, sha: str, *, target: str,
                     operation: str, candidate: Path | None = None) -> dict:
    """Confirm an ended write; never claim, dispatch or send another deployment."""
    if state["pending"] or transitions.current_id(state) != operation:
        raise transitions.Conflict("Resolve the changed or pending operation before confirming this product")
    current = state["current"]
    if current.get("health") == "passed":
        return {"state": "already_confirmed", "current": current}
    info = state["packages"][current["package"]]
    if current.get("health") == "failed" or info.get("failed"):
        # Matching bytes cannot disprove an independently established product defect.
        return {"state": "failed", "current": current}
    remote = current["remote"]
    remote_status = pages.query(remote["pages_id"])
    pages.current(expected=remote["deployment_id"])
    if remote_status.get("status") != "succeed":
        return {"state": "unknown", "current": current, "remote_status": remote_status}
    if not info.get("complete") or info.get("target") != target:
        raise transitions.Conflict("The recorded product is not completely archived for this target")
    with tempfile.TemporaryDirectory(prefix="resume-product-") as temporary:
        if candidate is None:
            manifest = archive.retrieve(current["package"], Path(temporary) / "candidate", target=target)
        else:
            manifest = json.loads((candidate / "manifest.json").read_text(encoding="utf-8"))
            packages.verify(candidate / "product.tar.gz", manifest, target=target)
        if manifest["id"] != current["package"]:
            raise transitions.Conflict("Confirmation refers to another product")
        observation = observe_content(pages.site_url(), manifest, operation)
    if observation["state"] != "matching":
        return {"state": "unconfirmed", "current": current, "service": observation}
    # A subsequent supported writer changes the control SHA. External writes
    # are checked again after observation; neither may be silently overwritten.
    pages.current(expected=remote["deployment_id"])
    updated = deepcopy(state)
    updated["current"].update(health="passed", platform_status="succeed", service_observation=observation)
    updated["packages"][current["package"]].update(eligible=True, failed=False, active=False)
    if updated["recovery"] and updated["recovery"]["id"] == operation:
        updated["recovery"] = None
    archive.save_state(updated, sha)
    return {"state": "confirmed", "operation": operation, "package": current["package"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default="Jacelber/mtgo-data")
    parser.add_argument("--operation", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    request = sub.add_parser("request", help="Register recovery intent before entering the writer queue")
    request.add_argument("--package", required=True)
    request.add_argument("--base", default="")
    request.add_argument("--recovery", action="store_true")
    request.add_argument("--reason", default="")
    request.add_argument("--automatic", action="store_true")
    claim = sub.add_parser("claim", help="Claim the target, retrieve the archived package, and extract it")
    claim.add_argument("--package", required=True)
    claim.add_argument("--base", default="")
    claim.add_argument("--recovery", action="store_true")
    claim.add_argument("--automatic", action="store_true")
    claim.add_argument("--output", type=Path, required=True)
    send = sub.add_parser("send", help="Send once; a later failure resumes querying this operation")
    send.add_argument("--artifact-id", required=True, type=int)
    resume = sub.add_parser("resume", help="Query and confirm the existing operation without rebuilding or resending")
    resume.add_argument("--candidate", type=Path, required=True)
    resume.add_argument("--wait-seconds", type=int, default=0)
    sub.add_parser("status", help="Read control and remote operation state")
    sub.add_parser("cancel", help="Request remote cancellation; retain unresolved state")
    sub.add_parser("settle-unsent", help="Clear a completed attempt only when the platform proves it never sent")
    settled = sub.add_parser("settle-completed", help="Record uncertain served content after a proven completed write; never decide rollback")
    settled.add_argument("--candidate", type=Path, required=True)
    end = sub.add_parser("end-recovery", help="End a resolved, withdrawn or inapplicable recovery intent")
    end.add_argument("--reason", required=True)
    problem = sub.add_parser("problem", help="Record a confirmed defect of the actual current product")
    problem.add_argument("--candidate", type=Path, required=True)
    problem.add_argument("--reason", required=True)
    args = parser.parse_args()
    try:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", args.operation):
            raise ValueError("Operation must be a short stable identifier, not a path")
        archive, pages = context(args.target)
        archive.private()
        state, sha = archive.load_state()
        pending = state["pending"]
        if (args.command in {"request", "claim"} and args.automatic and not args.recovery
                and state.get("automatic_publication_pause")
                and not (pending and pending["operation"] == args.operation and pending["phase"] != "claimed")):
            # An intentional pause is a normal result, not a product/CI failure.
            if output := os.environ.get("GITHUB_OUTPUT"):
                with Path(output).open("a") as handle:
                    handle.write("phase=paused\nallowed=false\n")
            print(json.dumps({"state": "publication_paused", "pause": state["automatic_publication_pause"]}, ensure_ascii=False))
            return 0
        if args.command == "request":
            info = state["packages"].get(args.package, {})
            if not info.get("complete") or info.get("target") != args.target:
                raise transitions.Conflict("Candidate must be completely archived for this target before queueing")
            if args.recovery:
                state = transitions.request_recovery(state, intent=args.operation, failed_operation=args.base,
                                                     package=args.package, reason=args.reason)
                archive.save_state(state, sha)
            else:
                transitions.require_publication_enabled(state, automatic=args.automatic)
            result = {"state": "requested", "operation": args.operation}
            if output := os.environ.get("GITHUB_OUTPUT"):
                with Path(output).open("a") as handle:
                    handle.write("allowed=true\n")
        elif args.command == "claim":
            if state["packages"].get(args.package, {}).get("target") != args.target:
                raise transitions.Conflict("Candidate belongs to a different deployment target")
            current = state["current"]
            remote = current.get("remote", {}) if current else {}
            expected = remote.get("deployment_id") if isinstance(remote, dict) else remote
            if not state["pending"]:
                actual = pages.current(expected=expected, own_run=os.environ.get("GITHUB_RUN_ID"))
                if not current and actual:
                    raise transitions.Conflict("An existing live deployment requires an explicit initial baseline")
            updated = transitions.claim(state, operation=args.operation, package=args.package, base=args.base or None,
                                        recovery=(state["pending"]["recovery"] if state["pending"] and state["pending"]["operation"] == args.operation
                                                  else args.operation if args.recovery else None), automatic=args.automatic)
            old = state["pending"]
            run, attempt = os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_RUN_ATTEMPT"]
            if old and old["phase"] == "claimed" and (old.get("run"), old.get("attempt")) != (run, attempt):
                if not pages.attempt_never_sent(old["run"], old["attempt"]):
                    raise transitions.Conflict("Original claimed attempt may still send; resolve it before continuing")
                updated["pending"].update(run=run, attempt=attempt)
            elif not old:
                updated["pending"].update(run=os.environ["GITHUB_RUN_ID"], attempt=os.environ["GITHUB_RUN_ATTEMPT"])
            if updated != state:
                archive.save_state(updated, sha)
            candidate = args.output.parent / f"candidate-{args.operation}"
            if candidate.exists():
                manifest = json.loads((candidate / "manifest.json").read_text())
                if manifest["id"] != args.package:
                    raise ValueError("Local candidate differs from selected package")
                packages.verify(candidate / "product.tar.gz", manifest, target=args.target)
            else:
                manifest = archive.retrieve(args.package, candidate, target=args.target)
            transport = args.output / "artifact.tar"
            if transport.exists():
                if packages.inspect(transport) != packages.inspect(candidate / "product.tar.gz"):
                    raise ValueError("Existing transport does not describe the selected candidate")
                # Compare the full tar, not just its entry-point probes.
                import gzip
                import hashlib
                with gzip.open(candidate / "product.tar.gz", "rb") as handle:
                    expected_tar = hashlib.file_digest(handle, "sha256").hexdigest()
                if packages.sha256(transport) != expected_tar:
                    raise ValueError("Existing transport differs from the selected complete tar")
            else:
                packages.pages_transport(candidate / "product.tar.gz", manifest, transport, target=args.target)
            result = {"state": "claimed", "candidate": str(candidate), "transport": str(transport)}
            if output := os.environ.get("GITHUB_OUTPUT"):
                with Path(output).open("a") as handle:
                    handle.write(f"candidate={candidate}\ntransport={transport}\nphase={updated['pending']['phase']}\n")
        elif args.command == "send":
            updated = transitions.sending(state, args.operation)
            archive.save_state(updated, sha)
            remote = pages.create(args.artifact_id)
            state, sha = archive.load_state()
            state = transitions.bind_remote(state, args.operation, remote)
            archive.save_state(state, sha)
            result = {"state": "sent", "operation": args.operation, "remote": remote}
        elif args.command == "settle-unsent":
            pending = state["pending"]
            if not pending or pending["operation"] != args.operation or pending["phase"] != "claimed":
                raise transitions.Conflict("Only a never-sent claimed operation can use this resolution")
            if not pages.attempt_never_sent(pending["run"], pending["attempt"]):
                raise transitions.Conflict("The original attempt is not proven completed without a send")
            state = transitions.no_write(state, args.operation, terminal_without_write=True)
            archive.save_state(state, sha)
            result = {"state": "not_sent", "operation": args.operation, "recovery": state["recovery"]}
        elif args.command == "settle-completed":
            pending = state["pending"]
            if not pending or pending["operation"] != args.operation or not pending.get("remote"):
                raise transitions.Conflict("The actual remote request must already be identified")
            remote = pending["remote"]
            platform_status = pages.query(remote["pages_id"]).get("status")
            if platform_status not in {"succeed", "deployment_failed", "cancelled", "canceled"}:
                raise transitions.Conflict("Remote write is not proven complete")
            record = pages.operation_record(pending["run"], pending["attempt"])
            if not record or (remote.get("deployment_id") and record != remote["deployment_id"]):
                raise transitions.Conflict("Completed write does not match the recorded operation")
            pages.current(expected=record, own_run=os.environ.get("GITHUB_RUN_ID"))
            manifest = json.loads((args.candidate / "manifest.json").read_text(encoding="utf-8"))
            packages.verify(args.candidate / "product.tar.gz", manifest, target=args.target)
            if manifest["id"] != pending["package"]:
                raise transitions.Conflict("Observation refers to a different candidate")
            observation = observe_content(pages.site_url(), manifest, args.operation)
            bound = {**remote, "deployment_id": record}
            state["pending"]["remote"] = bound  # Enrich the same identified request, as normal confirmation does.
            state = transitions.deployed(state, args.operation, bound)
            state["current"]["platform_status"] = platform_status
            if platform_status == "succeed" and observation["state"] == "matching":
                state = transitions.confirmed(state, args.operation, health="passed", observed_operation=args.operation)
            else:
                if platform_status != "succeed":
                    observation = {"state": "unconfirmed", "platform_status": platform_status, "served": observation}
                state = transitions.end_completed_write(state, args.operation, observation=observation, terminal=True)
            archive.save_state(state, sha)
            result = {"state": "write_completed", "platform_status": platform_status, "service": observation, "rollback_requested": False}
        elif args.command == "end-recovery":
            state = transitions.end_recovery(state, args.operation, reason=args.reason)
            archive.save_state(state, sha)
            result = {"state": "recovery_ended", "reason": args.reason}
        elif args.command == "problem":
            current = state["current"]
            if not current or current["operation"] != args.operation or not args.reason.strip():
                raise transitions.Conflict("Specify the actual current operation and a confirmed defect")
            pages.current(expected=current["remote"]["deployment_id"], own_run=os.environ.get("GITHUB_RUN_ID"))
            manifest = json.loads((args.candidate / "manifest.json").read_text())
            packages.verify(args.candidate / "product.tar.gz", manifest, target=args.target)
            if manifest["id"] != current["package"]:
                raise ValueError("Defect evidence refers to another product")
            if observe_content(pages.site_url(), manifest, args.operation)["state"] != "matching":
                raise transitions.Conflict("Actual served object is not yet established; do not classify unknown as defect")
            if state["pending"]:
                state = transitions.confirmed(state, args.operation, health="failed", observed_operation=args.operation)
            else:
                state["current"]["health"] = "failed"
                state["packages"][current["package"]]["eligible"] = False
                state["packages"][current["package"]]["failed"] = True
            state["current"]["defect"] = args.reason
            archive.save_state(state, sha)
            result = {"state": "defect_recorded", "operation": args.operation}
        elif args.command in {"resume", "status", "cancel"}:
            pending = state["pending"]
            if not pending or pending["operation"] != args.operation:
                if args.command == "status":
                    result = state
                elif args.command == "resume" and transitions.current_id(state) == args.operation:
                    result = resume_completed(archive, pages, state, sha, target=args.target,
                                              operation=args.operation, candidate=args.candidate)
                else:
                    raise transitions.Conflict("No matching pending operation")
            elif not pending["remote"]:
                result = {"state": "unknown", "operation": args.operation,
                          "run": pending.get("run"), "attempt": pending.get("attempt"),
                          "next": "Resolve original request from platform facts; do not resend"}
            elif args.command == "cancel":
                pages.cancel(pending["remote"]["pages_id"])
                result = {"state": "cancel_requested", "remote_stopped": False}
            else:
                deadline = time.monotonic() + (max(0, min(args.wait_seconds, 600)) if args.command == "resume" else 0)
                manifest = None
                if args.command == "resume":
                    manifest = json.loads((args.candidate / "manifest.json").read_text())
                    packages.verify(args.candidate / "product.tar.gz", manifest, target=args.target)
                    if manifest["id"] != pending["package"]:
                        raise ValueError("Confirmation refers to another package")
                while True:
                    remote_status = pages.query(pending["remote"]["pages_id"])
                    result = {"state": "unconfirmed", "remote_status": remote_status}
                    if args.command == "status":
                        result = {"control": state, "remote_status": remote_status}
                        break  # Read-only queries never mutate the control record.
                    if remote_status.get("status") == "succeed":
                        record = pages.operation_record(pending["run"], pending["attempt"])
                        if not record:
                            raise transitions.Conflict("Completed Pages request has no identifiable deployment record yet")
                        bound = {**pending["remote"], "deployment_id": record}
                        state, sha = archive.load_state()
                        if not state["pending"] or state["pending"]["operation"] != args.operation:
                            raise transitions.Conflict("Operation state changed during the remote query")
                        if state["pending"]["remote"]["pages_id"] != bound["pages_id"]:
                            raise transitions.Conflict("Remote request changed during the query")
                        # Enrich the same known request with its environment record.
                        original = json.dumps(state, sort_keys=True)
                        state["pending"]["remote"] = bound
                        state = transitions.deployed(state, args.operation, bound)
                        if json.dumps(state, sort_keys=True) != original:
                            sha = archive.save_state(state, sha)
                        observation = observe_content(pages.site_url(), manifest, args.operation)
                        result = {"state": "unconfirmed", **observation}
                        if observation["state"] == "matching":
                            state = transitions.confirmed(state, args.operation, health="passed", observed_operation=args.operation)
                            archive.save_state(state, sha)
                            result = {"state": "confirmed", "operation": args.operation, "package": manifest["id"]}
                            break
                    if remote_status.get("status") in {"deployment_failed", "cancelled", "canceled"} or time.monotonic() >= deadline:
                        break
                    time.sleep(5)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return {"unknown": 3, "unconfirmed": 3, "cancel_requested": 3, "failed": 1}.get(result.get("state"), 0)
    except (APIError, OSError, ValueError, KeyError) as error:
        print(json.dumps({"state": "execution_failed", "error": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
