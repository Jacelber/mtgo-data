"""MTGO-only Owner-admitted event selection, separate from weekly completion.

Collection and private review continue to use retained inputs. Public producers
must obtain membership from this module, never from directory growth or a date
cutoff. An accepted classifier can restate this membership, not enlarge it.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from . import load_mtgo_event_collection_context
from .classification import load_mtgo_events_for_format


ADMISSION_PATH = Path("configs/mtgo_weekly_review_completions.yaml")


class PublicationError(ValueError):
    """An unprovable public subject must not replace the last published one."""


def week_monday(value: str) -> date:
    try:
        year, week = value.split("-W")
        result = date.fromisocalendar(int(year), int(week), 1)
    except (AttributeError, TypeError, ValueError) as exc:
        raise PublicationError("invalid ISO publication week") from exc
    if result.strftime("%G-W%V") != value:
        raise PublicationError("publication week must be canonical YYYY-Www")
    return result


def _event_ids(value: Any) -> frozenset[str]:
    if (not isinstance(value, list) or not value
            or any(not isinstance(item, str) or not item.isdigit() for item in value)
            or len(set(value)) != len(value)):
        raise PublicationError("admission requires explicit unique event IDs")
    return frozenset(value)


def resolve_timeline(
    initial: Mapping[str, Any],
    reviews: Sequence[Mapping[str, Any]],
    event_dates: Mapping[str, date],
) -> tuple[date, frozenset[str]]:
    """Resolve one continuous natural-week frontier using explicit membership.

    Empty gaps may be crossed only for the observed retained subject. A later
    arrival never inherits a permit from an empty gap or from a date threshold.
    The operation does not read any completion or Landing state.
    """
    frontier = week_monday(initial["week"])
    ids = _event_ids(initial.get("event_ids"))
    if not ids <= event_dates.keys():
        raise PublicationError("admitted initial source is missing")
    if any(event_dates[item] > frontier + timedelta(days=6) for item in ids):
        raise PublicationError("initial membership exceeds its approved week")
    by_week: dict[date, frozenset[str]] = {}
    observed_empty_weeks: set[date] = set()
    for review in reviews:
        monday = week_monday(review["week"])
        membership = _event_ids(review.get("event_ids"))
        if monday in by_week:
            raise PublicationError("duplicate weekly data admission")
        if not membership <= event_dates.keys():
            raise PublicationError("admitted weekly source is missing")
        if any(not monday <= event_dates[item] <= monday + timedelta(days=6)
               for item in membership):
            raise PublicationError("weekly admission has an event from another week")
        by_week[monday] = membership
        for value in review.get("observed_empty_weeks", []):
            empty = week_monday(value)
            if not frontier < empty < monday:
                raise PublicationError("empty-week evidence is outside its advancement")
            observed_empty_weeks.add(empty)
    # Explicit accepted additions to an earlier week do not rewrite history.
    for monday, membership in by_week.items():
        if monday <= frontier:
            ids |= membership
    target = max(by_week, default=frontier)
    while frontier < target:
        following = frontier + timedelta(days=7)
        if following in by_week:
            ids |= by_week[following]
        elif following not in observed_empty_weeks and any(following <= day <= following + timedelta(days=6)
                 for day in event_dates.values()):
            break
        frontier = following
    return frontier, ids


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PublicScope:
    format_id: str
    week: date
    event_ids: frozenset[str]
    pending_event_ids: frozenset[str]
    source_manifest: tuple[dict[str, str], ...]
    subject_digest: str


def retained_events(root: Path, format_id: str):
    context = load_mtgo_event_collection_context(root, format_id)
    events, excluded = load_mtgo_events_for_format(
        context.paths["events"].glob("*.json"), root, format_id)
    if excluded:
        raise PublicationError("cross-format retained input")
    ids = [str(event.get("event_id", "")) for _, event in events]
    if any(not item.isdigit() for item in ids) or len(set(ids)) != len(ids):
        raise PublicationError("invalid or duplicate retained event identity")
    return events


def resolve_scope(repository_root: str | Path, format_id: str) -> PublicScope:
    root = Path(repository_root).resolve()
    try:
        document = yaml.safe_load((root / ADMISSION_PATH).read_text(encoding="utf-8"))
        if document.get("schema_version") != "1.2.0":
            raise PublicationError("explicit data-admission contract is required")
        admissions = document["data_admissions"]
        if admissions["schema_version"] != "1.0.0":
            raise PublicationError("unsupported data-admission version")
        config = admissions["formats"][format_id]
        initial = config["initial"]
        if initial["kind"] != "grandfathered_existing_public_scope":
            raise PublicationError("initial scope is not a historical review completion")
        reviews = config["weekly_acceptances"]
        if not isinstance(reviews, list):
            raise PublicationError("weekly acceptances must be a list")
        for review in reviews:
            if review.get("kind") != "owner_accepted_full_classification":
                raise PublicationError("a completion is not a classification admission")
            for key in ("accepted_classifier_subject", "classification_review_digest"):
                value = review.get(key)
                if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                    raise PublicationError(f"invalid data admission {key}")
            if date.fromisoformat(review["accepted_on"]) <= week_monday(review["week"]) + timedelta(days=6):
                raise PublicationError("data acceptance precedes the complete natural week")
        records = [initial, *reviews]
        sources = retained_events(root, format_id)
        event_dates = {str(event["event_id"]): date.fromisoformat(event["starttime"][:10])
                       for _, event in sources}
        frontier, ids = resolve_timeline(initial, reviews, event_dates)
        actual = {str(event["event_id"]): {"event_id": str(event["event_id"]),
                  "source_file": source, "sha256": hashlib.sha256((root / source).read_bytes()).hexdigest()}
                  for source, event in sources}
        for record in records:
            if not isinstance(record.get("evidence"), str) or not record["evidence"].strip():
                raise PublicationError("data admission lacks Owner acceptance evidence")
            bound_ids = _event_ids(record["event_ids"])
            expected = record["source_manifest_digest"]
            if _digest([actual[item] for item in sorted(bound_ids, key=int)]) != expected:
                raise PublicationError("accepted retained source binding has changed")
        manifest = tuple(actual[item] for item in sorted(ids, key=int))
    except (AttributeError, KeyError, TypeError, OSError, ValueError, yaml.YAMLError) as exc:
        if isinstance(exc, PublicationError):
            raise
        raise PublicationError(f"invalid data admission for {format_id}: {exc}") from exc
    return PublicScope(format_id, frontier, ids, frozenset(actual) - ids, manifest,
                       _digest({"format": format_id, "week": frontier.isoformat(), "events": manifest}))


def public_events(repository_root: str | Path, format_id: str):
    root = Path(repository_root).resolve()
    scope = resolve_scope(root, format_id)
    return [(source, event) for source, event in retained_events(root, format_id)
            if str(event["event_id"]) in scope.event_ids]


def artifact_paths(root: Path, format_id: str) -> list[str]:
    """Exact MTGO product bytes, including retained compatibility documents.

    This is one format-specific directory contract, not a dependency registry.
    The private Landing review directory is never an output product.
    """
    paths = []
    for directory in (root / "stats" / format_id / "mtgo", root / "reports" / format_id / "mtgo"):
        for path in directory.rglob("*.json"):
            relative = path.relative_to(root).as_posix()
            if relative == f"stats/{format_id}/mtgo/meta.json" or "/landing/review/" in relative:
                continue
            if "/pickup/" in relative and path.name == "known_archetypes.json":
                continue
            if path.is_symlink():
                raise PublicationError("public artifact is a symbolic link")
            paths.append(relative)
    return sorted(paths)


def publication_binding(root: Path, format_id: str) -> dict[str, Any]:
    scope = resolve_scope(root, format_id)
    return {"scope_digest": scope.subject_digest,
            "week": scope.week.strftime("%G-W%V"),
            "artifacts": {relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
                          for relative in artifact_paths(root, format_id)}}


def inspect_publication(root: Path, format_id: str) -> list[str]:
    """Read only: source membership and exact artifact bytes, never regeneration."""
    meta = json.loads((root / "stats" / format_id / "mtgo/meta.json").read_text(encoding="utf-8"))
    expected = publication_binding(root, format_id)
    actual = meta.get("publication")
    if not isinstance(actual, dict):
        return ["missing reviewed-publication binding"]
    issues = []
    if actual.get("scope_digest") != expected["scope_digest"] or actual.get("week") != expected["week"]:
        issues.append("public event scope is stale")
    if actual.get("artifacts") != expected["artifacts"]:
        issues.append("public artifact bytes do not match the validated scope binding")
    for name in ("index.json", "matchup_index.json", "top8/index.json", "completeness/index.json"):
        document = json.loads((root / "stats" / format_id / "mtgo" / name).read_text(encoding="utf-8"))
        if document.get("latest_complete_week") != week_monday(expected["week"]).isoformat():
            issues.append(f"{name}: public calendar frontier differs")
    admitted = resolve_scope(root, format_id).event_ids
    for relative in artifact_paths(root, format_id):
        document = json.loads((root / relative).read_text(encoding="utf-8"))
        if not referenced_event_ids(document) <= admitted:
            issues.append(f"{relative}: unadmitted public event reference")
        if relative.startswith(f"reports/{format_id}/mtgo/") and (
            document.get("scope") != "all_admitted_events" or document.get("event_count") != len(admitted)
        ):
            issues.append(f"{relative}: public report population differs from approved scope")
    return issues


def referenced_event_ids(value: Any) -> set[str]:
    """Read existing MTGO source-reference fields without reclassifying inputs."""
    result: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "event_id" and child is not None:
                result.add(str(child))
            elif key in {"event_ids", "source_event_ids"} and isinstance(child, list):
                result.update(str(item) for item in child)
            else:
                result.update(referenced_event_ids(child))
    elif isinstance(value, list):
        for child in value:
            result.update(referenced_event_ids(child))
    return result


def inspect(repository_root: str | Path, format_id: str) -> dict[str, Any]:
    scope = resolve_scope(repository_root, format_id)
    return {"format": format_id, "public_week": scope.week.strftime("%G-W%V"),
            "public_event_ids": sorted(scope.event_ids, key=int),
            "pending_event_ids": sorted(scope.pending_event_ids, key=int),
            "subject_digest": scope.subject_digest}


def require_private_output(root: Path, output: Path) -> None:
    """Candidate review material must not be written into the Pages allowlist."""
    from fnmatch import fnmatchcase
    target = output.resolve()
    try:
        relative = target.relative_to(root.resolve()).as_posix()
    except ValueError:
        return
    config = json.loads((root / "configs/pages_publication.json").read_text(encoding="utf-8"))
    admitted = relative in config["site_files"] or any(
        relative == directory or relative.startswith(directory + "/")
        for directory in config["site_directories"])
    excluded = any(fnmatchcase(relative, pattern) for pattern in config["excluded_patterns"])
    if admitted and not excluded:
        raise PublicationError("private review output would enter the Pages publication boundary")


def prepare_review(root: Path, format_id: str, week: str, output: Path) -> Path:
    from ..weekly_review import build_mtgo_weekly_review
    require_private_output(root, output)
    document = build_mtgo_weekly_review(root, format_id, week)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return output


def stage_publication(root: Path, format_id: str, *, include_landing: bool = False,
                      execute: bool = False) -> dict[str, Any]:
    """Explicit offline operation; stage and validate before touching final files.

    Reuse the existing classifier-closure file replacement/rollback implementation.
    Neither this operation nor ordinary producer calls create an Owner approval.
    """
    import os
    import shutil
    import subprocess
    import sys
    import tempfile
    from ..classifier_closure import _materialize_with_rollback, _protected_input_fingerprints, inspect_format
    from ..classification_reports_cli import generate_reports
    from ..catalog import write_catalog
    from . import completeness, landing, landing_editorial, matchup, metadata, stats, top8

    root = root.resolve()
    subject = resolve_scope(root, format_id)
    protected = _protected_input_fingerprints(root, format_id)
    stage = Path(tempfile.mkdtemp(prefix=f"mtgo-publication-{format_id}-", dir=root.parent))
    shutil.copytree(root, stage, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", "test-results", "playwright-report"))
    # A separate local index gives the existing read-only repository validator
    # its tracked inventory without creating any commit or remote publication.
    subprocess.run(["git", "init", "--quiet", str(stage)], check=True)
    subprocess.run(["git", "-C", str(stage), "config", "core.autocrlf", "false"], check=True)
    before_paths = artifact_paths(root, format_id)
    before = {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in before_paths}
    meta_path = f"stats/{format_id}/mtgo/meta.json"
    before[meta_path] = hashlib.sha256((root / meta_path).read_bytes()).hexdigest()
    for path in (f"stats/{format_id}/archetype_names.json", "stats/catalog.json"):
        before[path] = hashlib.sha256((root / path).read_bytes()).hexdigest()
    stats.build_all_stats(stage, format_id)
    matchup.build_all_matchups(stage, format_id)
    completeness.build_all_completeness(stage, format_id)
    top8.build_all_top8(stage, format_id)
    metadata.generate_hierarchy_catalog(stage, format_id,
        rules_updated=metadata.rules_last_commit_iso(root, root / "my_archetypes" / f"{format_id}.yaml"))
    landing_editorial.generate_public_name_contract(stage, format_id)
    generate_reports(stage, format_id)
    if include_landing:
        result = landing.generate(stage, format_id)
        if result["status"] in {"stale_review_required", "summary_review_required"}:
            raise PublicationError(f"BLOCKED_OWNER_REVIEW: {result['status']}; stage retained at {stage}")
    metadata.generate_metadata(stage, format_id,
        rules_updated=metadata.rules_last_commit_iso(root, root / "my_archetypes" / f"{format_id}.yaml"))
    write_catalog(stage)
    issues = inspect_publication(stage, format_id)
    if issues:
        raise PublicationError(f"invalid staged publication: {issues}; {stage}")
    closure = inspect_format(stage, format_id)
    if closure["state"] != "CURRENT":
        raise PublicationError(f"BLOCKED_OWNER_REVIEW: staged classifier closure {closure}; {stage}")
    if _protected_input_fingerprints(stage, format_id) != protected:
        raise PublicationError(f"staging changed a protected input; {stage}")
    subprocess.run(["git", "-C", str(stage), "add", "--all"], check=True)
    environment = dict(os.environ, PYTHONPATH=str(stage / "src"))
    for script, arguments in (("validate_repository.py", ["--full"]),
                              ("validate_rules.py", [f"my_archetypes/{format_id}.yaml"]),
                              ("validate_schemas.py", []), ("validate_output_invariants.py", [])):
        subprocess.run([sys.executable, "-B", str(stage / script), *arguments],
                       cwd=stage, env=environment, check=True)
    subprocess.run([sys.executable, "-B", "-m", "pytest", "-q",
                    "tests/test_generated_consumer_contracts.py"],
                   cwd=stage, env=environment, check=True)
    # Use the existing focused production consumer gate. Dependencies must have
    # been installed explicitly before this offline operation; never install/fetch here.
    browser_cli = root / "node_modules/@playwright/test/cli.js"
    environment["NODE_PATH"] = str(root / "node_modules")
    subprocess.run(["node", str(browser_cli), "test", "tests/browser/production-pages.spec.js"],
                   cwd=stage, env=environment, check=True)
    subprocess.run(["git", "-C", str(stage), "diff", "--exit-code"], check=True)
    # No final target has been changed if any preceding operation fails.
    if artifact_paths(root, format_id) != before_paths or resolve_scope(root, format_id) != subject or _protected_input_fingerprints(root, format_id) != protected or any(
        hashlib.sha256((root / path).read_bytes()).hexdigest() != sha for path, sha in before.items()
    ):
        raise PublicationError(f"final subject changed during staging; {stage}")
    paths = [*artifact_paths(stage, format_id), meta_path,
             f"stats/{format_id}/archetype_names.json", "stats/catalog.json"]
    changed = [path for path in paths if not (root / path).is_file()
               or (root / path).read_bytes() != (stage / path).read_bytes()]
    if execute:
        def validate_final():
            failures = inspect_publication(root, format_id)
            if failures:
                raise PublicationError(str(failures))
        _materialize_with_rollback(root, stage, changed, validate_final=validate_final)
    return {"format": format_id, "stage": str(stage), "executed": execute,
            "publication_node": "landing_content" if include_landing else "reviewed_data",
            "scope_digest": subject.subject_digest, "changed_paths": changed}


def intentional_unknowns(root: Path) -> dict[str, dict[tuple[str, str, str], dict[str, str]]]:
    """Read the existing random-card-pile policy, without expanding its scope."""
    config = yaml.safe_load((root / "configs/mtgo_intentional_unknowns.yaml").read_text(encoding="utf-8"))
    if config.get("schema_version") != "1.0.0":
        raise ValueError("Intentional Unknown registry has an unsupported schema version")
    records = config.get("records")
    if not isinstance(records, list):
        raise ValueError("Intentional Unknown registry has no records list")
    result: dict[str, dict[tuple[str, str, str], dict[str, str]]] = {
        format_name: {} for format_name in ("standard", "modern")
    }
    for item in records:
        if not isinstance(item, dict):
            raise ValueError("Intentional Unknown registry contains a non-object")
        format_name = item.get("format")
        event_id = str(item.get("event_id", ""))
        deck_id = str(item.get("deck_id", ""))
        source_file = str(item.get("source_file", ""))
        disposition = item.get("disposition")
        reason_code = item.get("reason_code")
        owner_accepted_on = str(item.get("owner_accepted_on", ""))
        evidence = str(item.get("evidence", ""))
        if format_name not in result or not event_id.isdigit() or not deck_id or not source_file:
            raise ValueError("Intentional Unknown registry contains an invalid identity")
        if disposition != "intentional_unknown" or reason_code != "random_card_pile":
            raise ValueError("Only Owner-accepted random card piles may remain intentional Unknown")
        if not owner_accepted_on or not evidence:
            raise ValueError("Intentional Unknown registry entry lacks acceptance evidence")
        key = (event_id, deck_id, source_file)
        if key in result[format_name]:
            raise ValueError("Intentional Unknown registry contains a duplicate identity")
        result[format_name][key] = {
            "disposition": disposition,
            "reason_code": reason_code,
            "owner_accepted_on": owner_accepted_on,
            "evidence": evidence,
        }
    return result


def acceptance_record(root: Path, format_id: str, week: str, *,
                      expected_review_digest: str, accepted_on: str,
                      evidence: str) -> dict[str, Any]:
    """Prepare only the exact Owner-accepted classification admission, not completion."""
    from ..config import load_rule_set
    from ..reports import build_classification_reports, has_blocking_diagnostics
    from ..weekly_review import build_mtgo_weekly_review
    monday = week_monday(week)
    if monday + timedelta(days=6) >= date.today():
        raise PublicationError("the review week has not ended")
    date.fromisoformat(accepted_on)
    if not evidence.strip():
        raise PublicationError("Owner acceptance evidence is required")
    review = build_mtgo_weekly_review(root, format_id, week)
    if review["classification_review_digest"] != expected_review_digest:
        raise PublicationError("Owner-accepted classification review has changed")
    ids = frozenset(review["event_ids"])
    all_events = retained_events(root, format_id)
    events = [(source, event) for source, event in all_events if str(event["event_id"]) in ids]
    reports = build_classification_reports(events, load_rule_set(root / "my_archetypes" / f"{format_id}.yaml"), format_id=format_id)
    accepted_unknown = intentional_unknowns(root)[format_id]
    if has_blocking_diagnostics(reports) or any(
        (str(item["event_id"]), str(item["deck_id"]), str(item["source_file"])) not in accepted_unknown
        for item in reports["unknown_decks"]["records"]
    ):
        raise PublicationError("BLOCKED_OWNER_REVIEW: existing classification/Unknown policy")
    sources = [{"event_id": str(event["event_id"]), "source_file": source,
                "sha256": hashlib.sha256((root / source).read_bytes()).hexdigest()}
               for source, event in events]
    sources.sort(key=lambda row: int(row["event_id"]))
    current = resolve_scope(root, format_id)
    observed = {week_monday(date.fromisoformat(event["starttime"][:10]).strftime("%G-W%V"))
                for _, event in all_events}
    empty = []
    cursor = current.week + timedelta(days=7)
    while cursor < monday:
        if cursor not in observed:
            empty.append(cursor.strftime("%G-W%V"))
        cursor += timedelta(days=7)
    return {"week": week, "kind": "owner_accepted_full_classification",
            "event_ids": sorted(ids, key=int),
            "source_manifest_digest": _digest(sources),
            "accepted_classifier_subject": review["classifier"]["subject_digest"],
            "classification_review_digest": expected_review_digest,
            "accepted_on": accepted_on, "evidence": evidence,
            "observed_empty_weeks": empty}
