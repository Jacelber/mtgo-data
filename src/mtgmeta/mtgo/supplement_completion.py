"""Append-only completion facts for late events; no registry writes or publication."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
import re
from pathlib import Path
import tempfile

from . import review_submission as review


def origin(record: dict, format_id: str) -> str:
    return review.digest({"week": record["week"], "format": format_id,
        "completed_on": record["completed_on"], "evidence": record["evidence"],
        "review_scope": record.get("review_scope"),
        "subject": {k: v for k, v in record["formats"][format_id].items() if k != "supplements"}})


def event_ids(value) -> set[str]:
    if (not isinstance(value, list) or not value or len(value) != len(set(value))
            or any(not isinstance(item, str) or not item.isdigit() for item in value)):
        raise ValueError("Supplement requires distinct explicit event IDs")
    return set(value)


def coverage(root: Path, record: dict, format_id: str) -> dict:
    """Only validated facts extend coverage; errors never revoke the original fact."""
    subject = record["formats"][format_id]
    review.validate_completion(root, format_id, record["week"], subject, check_current=False)
    covered = event_ids(subject.get("accepted_event_ids"))
    effective = deepcopy(subject)
    effective.pop("supplements", None)
    base = previous = origin(record, format_id)
    completed_on = date.fromisoformat(record["completed_on"])
    problems, valid = [], []
    entries = subject.get("supplements", [])
    if not isinstance(entries, list):
        entries, problems = [], ["supplements must be a list"]
    for index, entry in enumerate(entries):
        try:
            if (entry["schema_version"] != "1.0.0" or entry["format"] != format_id
                    or entry["week"] != record["week"] or entry["base_completion"] != base
                    or entry["previous"] != previous
                    or entry["id"] != review.digest({k: v for k, v in entry.items() if k != "id"})):
                raise ValueError("Supplement identity, original completion or append order changed")
            when = date.fromisoformat(entry["completed_on"])
            if when < completed_on or not isinstance(entry["evidence"], str) or not entry["evidence"].strip():
                raise ValueError("Supplement needs its own completion date and evidence")
            added = event_ids(entry["covered_event_ids"])
            if added & covered:
                raise ValueError("Supplement overlaps previously completed events")
            classification = entry["classification_submission"]
            review.validate_packet(classification)
            binding = classification["dimensions"]["full_classification"]
            if (classification["format"] != format_id or classification["week"] != record["week"]
                    or classification["kind"] != "full_classification"
                    or event_ids(binding["event_ids"]) != covered | added):
                raise ValueError("Supplement classification does not cover the exact accumulated scope")
            admission = entry["classification_admission"]
            review.validate_classification_acceptance(admission, format_id)
            if (admission["week"] != record["week"] or event_ids(admission["event_ids"]) != covered | added
                    or review.packet_validity(admission["classification_acceptance"]["submission"], classification)["state"]
                    not in {"current", "equivalent"}):
                raise ValueError("Supplement classification lacks matching acceptance")
            publication = entry["publication"]
            data = entry["data_publication"]
            if (publication.get("health") != "passed" or not publication.get("operation")
                    or not publication.get("package") or data["package"] != publication["package"]
                    or not (covered | added) <= event_ids(data["event_ids"])
                    or any(not isinstance(data.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", data[key])
                           for key in ("scope_digest", "artifacts_digest"))):
                raise ValueError("Supplement lacks confirmed publication of the covered data")
            actual = entry["preview"]["submission"]
            review.validate_packet(actual)
            if actual["format"] != format_id or actual["kind"] != "preview":
                raise ValueError("Supplement preview belongs to another format")
            if entry["preview"]["mode"] == "retained":
                accepted = effective["preview_acceptance"]
                if (entry["preview"]["retained_from"] != accepted["submission"]["digest"]
                        or actual["week"] != accepted["submission"]["week"]
                        or review.preview_validity(accepted["submission"], actual, dimensions_only=True)["state"] not in {"current", "equivalent"}):
                    raise ValueError("Retained preview actually changed")
            elif entry["preview"]["mode"] == "accepted":
                accepted = entry["preview"]["acceptance"]
                review.require_accepted(accepted["submission"], accepted["decisions"], current=actual)
                content = entry["content_acceptance"]
                current_content = entry["content_submission"]
                if (current_content["kind"] != "content" or current_content["format"] != format_id
                        or current_content["week"] != actual["week"]):
                    raise ValueError("Supplement content belongs to another page")
                review.require_accepted(content["submission"], content["decisions"], current=current_content)
            else:
                raise ValueError("Unknown supplement preview mode")
            landing = entry["landing_content_digest"]
            if not isinstance(landing, str) or not re.fullmatch(r"[0-9a-f]{64}", landing):
                raise ValueError("Supplement lacks its retained week Landing binding")
            effective.update(accepted_event_ids=sorted(covered | added),
                accepted_classifier_subject=binding["classifier"],
                classification_review_digest=binding["classification_review_digest"],
                classification_submission=classification, landing_content_digest=landing,
                preview_acceptance={**accepted, "publication": {**publication,
                    "preview_digest": accepted["submission"]["digest"]}})
            covered |= added
            previous, completed_on = entry["id"], when
            valid.append(entry["id"])
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            problems.append(f"supplement {index + 1}: {exc}")
    return {"covered_event_ids": sorted(covered), "valid_supplements": valid,
            "problems": problems, "effective": effective, "previous": previous}


def validate_current_preview(root: Path, format_id: str, effective: dict) -> None:
    expected = effective["preview_acceptance"]["submission"]
    page = json.loads((root / f"stats/{format_id}/mtgo/landing/current.json").read_text(encoding="utf-8"))
    if page["week"]["id"] == expected["week"]:
        if review.preview_validity(expected, review.preview_packet(root, format_id), dimensions_only=True)["state"] not in {"current", "equivalent"}:
            raise ValueError("Current preview differs from the completed supplement")


def build(root: Path, record: dict, format_id: str, *, candidate: Path,
          state: dict, completed_on: str, evidence: str, preview_acceptance: dict | None = None) -> dict:
    """Verify the real retained package, then produce a new fact without changing history."""
    from mtgmeta.weekly_review import build_mtgo_weekly_review
    from . import publication
    from tools.delivery import packages
    import yaml

    existing = coverage(root, record, format_id)
    if existing["problems"]:
        raise ValueError("Investigate existing supplement evidence: " + "; ".join(existing["problems"]))
    if not review.applies(record["week"]):
        raise ValueError("Legacy completion needs separately established material before supplement export")
    current = build_mtgo_weekly_review(root, format_id, record["week"])
    ids, covered = event_ids(current["event_ids"]), set(existing["covered_event_ids"])
    if not covered <= ids or not ids - covered:
        raise ValueError("Supplement must add events without removing historical coverage")
    registry = yaml.safe_load((root / "configs/mtgo_weekly_review_completions.yaml").read_text(encoding="utf-8"))
    admissions = registry["data_admissions"]["formats"][format_id]["weekly_acceptances"]
    accepted = [item for item in admissions if review.classification_validity(item, current)["state"] in {"current", "equivalent"}]
    if len(accepted) != 1:
        raise ValueError("Supplement requires one matching full classification admission")
    scope = publication.resolve_scope(root, format_id)
    if not ids <= scope.event_ids or publication.inspect_publication(root, format_id):
        raise ValueError("Supplement data admission/publication is not complete")
    binding = publication.publication_binding(root, format_id)
    manifest = json.loads((candidate / "manifest.json").read_text(encoding="utf-8"))
    confirmed = state.get("current") or {}
    if (state.get("pending") or confirmed.get("health") != "passed"
            or confirmed.get("package") != manifest["id"] or not confirmed.get("operation")):
        raise ValueError("Publication has not confirmed this exact supplement package")
    with tempfile.TemporaryDirectory(prefix="supplement-publication-") as directory:
        extracted = Path(directory) / "site"
        packages.extract(candidate / "product.tar.gz", manifest, extracted, target="Jacelber/mtgo-data")
        # Compare the extracted data against already validated local outputs.
        # No archived code execution, refetching or generation is performed.
        if publication.artifact_paths(extracted, format_id) != sorted(binding["artifacts"]):
            raise ValueError("Supplement package has different data artifacts")
        for relative, expected in binding["artifacts"].items():
            if review.hashlib_sha(extracted / relative) != expected:
                raise ValueError("Supplement package does not contain the validated data")
        meta_path = f"stats/{format_id}/mtgo/meta.json"
        if (extracted / meta_path).read_bytes() != (root / meta_path).read_bytes():
            raise ValueError("Supplement package has a different publication binding")
        actual = review.preview_packet(extracted, format_id)
        if actual != review.preview_packet(root, format_id):
            raise ValueError("Supplement package preview differs from the current reviewed product")
    prior = existing["effective"]["preview_acceptance"]
    extra = {}
    if review.preview_validity(prior["submission"], actual, dimensions_only=True)["state"] in {"current", "equivalent"}:
        preview = {"mode": "retained", "submission": actual, "retained_from": prior["submission"]["digest"]}
    else:
        if preview_acceptance is None:
            raise ValueError("Changed supplement page requires its accepted preview and content")
        review.require_accepted(preview_acceptance["submission"], preview_acceptance["decisions"], current=actual)
        source = yaml.safe_load((root / f"stats/{format_id}/mtgo/landing/review/{actual['week']}.yaml").read_text(encoding="utf-8"))
        review.validate_content_acceptance(source)
        content = review.content_packet(root, source)
        review.require_accepted(source["acceptance"]["submission"], source["acceptance"]["decisions"], current=content)
        extra = {"content_acceptance": source["acceptance"], "content_submission": content}
        preview = {"mode": "accepted", "submission": actual, "acceptance": preview_acceptance}
    landing = json.loads((root / f"stats/{format_id}/mtgo/landing/features/{record['week']}.json").read_text(encoding="utf-8"))
    result = {"schema_version": "1.0.0", "format": format_id, "week": record["week"],
        "base_completion": origin(record, format_id), "previous": existing["previous"],
        "completed_on": completed_on, "evidence": evidence, "covered_event_ids": sorted(ids - covered),
        "classification_admission": accepted[0], "classification_submission": review.classification_comparison_packet(current),
        "publication": confirmed, "data_publication": {"package": manifest["id"], "event_ids": sorted(scope.event_ids),
            "scope_digest": binding["scope_digest"], "artifacts_digest": review.digest(binding["artifacts"])},
        "preview": preview, "landing_content_digest": landing["content_digest"], **extra}
    result["id"] = review.digest(result)
    proposed = deepcopy(record)
    proposed["formats"][format_id].setdefault("supplements", []).append(result)
    checked = coverage(root, proposed, format_id)
    if checked["problems"]:
        raise ValueError("; ".join(checked["problems"]))
    return result
