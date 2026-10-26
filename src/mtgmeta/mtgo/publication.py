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


def _validate_owner_classification_acceptance(record: Mapping[str, Any], format_id: str | None = None) -> None:
    from .review_submission import validate_classification_acceptance
    validate_classification_acceptance(dict(record), format_id)
    for key in ("accepted_classifier_subject", "classification_review_digest"):
        value = record.get(key)
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise PublicationError(f"invalid data admission {key}")
    if date.fromisoformat(record["accepted_on"]) <= (
        week_monday(record["week"]) + timedelta(days=6)
    ):
        raise PublicationError("data acceptance precedes the complete natural week")


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


def _resolve_scope(repository_root: str | Path, format_id: str, *, through_week: str | None = None):
    root = Path(repository_root).resolve()
    from ..config import load_format_registry
    definition = load_format_registry(root / "configs/formats.yaml").require_mtgo(format_id)
    if not definition.public:
        raise PublicationError("non-public format has no public admission scope")
    try:
        document = yaml.safe_load((root / ADMISSION_PATH).read_text(encoding="utf-8"))
        if document.get("schema_version") != "1.2.0":
            raise PublicationError("explicit data-admission contract is required")
        admissions = document["data_admissions"]
        if admissions["schema_version"] != "1.0.0":
            raise PublicationError("unsupported data-admission version")
        config = admissions["formats"][format_id]
        initial = config["initial"]
        initial_kind = initial.get("kind")
        if initial_kind == "owner_accepted_initial_public_scope":
            _validate_owner_classification_acceptance(initial, format_id)
        elif initial_kind != "grandfathered_existing_public_scope":
            raise PublicationError("unsupported initial public scope admission")
        reviews = config["weekly_acceptances"]
        if not isinstance(reviews, list):
            raise PublicationError("weekly acceptances must be a list")
        if through_week is not None:
            # Historical content uses its original admission prefix, never the
            # latest frontier. The caller must verify the retained scope digest.
            cutoff = week_monday(through_week)
            if week_monday(initial["week"]) > cutoff:
                raise PublicationError("retained admission predates the available initial scope")
            reviews = [record for record in reviews if week_monday(record["week"]) <= cutoff]
        for review in reviews:
            if review.get("kind") != "owner_accepted_full_classification":
                raise PublicationError("a completion is not a classification admission")
            _validate_owner_classification_acceptance(review, format_id)
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
                       _digest({"format": format_id, "week": frontier.isoformat(), "events": manifest})), sources


def resolve_scope(repository_root: str | Path, format_id: str) -> PublicScope:
    # Every independent call obtains fresh inputs, including final write checks.
    root = Path(repository_root).resolve()
    return _resolve_scope(root, format_id)[0]


def public_events(repository_root: str | Path, format_id: str):
    root = Path(repository_root).resolve()
    scope, events = _resolve_scope(root, format_id)
    return [(source, event) for source, event in events
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
    admitted_melee: set[str] | None = None
    for relative in artifact_paths(root, format_id):
        document = json.loads((root / relative).read_text(encoding="utf-8"))
        if not referenced_event_ids(document) <= admitted:
            issues.append(f"{relative}: unadmitted public event reference")
        melee_ids = referenced_event_ids(document, source="melee")
        if melee_ids:
            if admitted_melee is None:
                from ..melee.config import load_melee_event_registry
                registry = load_melee_event_registry(root / "configs/melee_events.yaml")
                catalog = json.loads((root / "stats" / format_id / "melee/index.json").read_text(encoding="utf-8"))
                admitted_melee = set()
                for entry in catalog["events"]:
                    event_id = str(entry["event_id"])
                    event = registry.require_fetchable(event_id)
                    if event.format == format_id:
                        admitted_melee.add(event_id)
            if not melee_ids <= admitted_melee:
                issues.append(f"{relative}: unadmitted public Melee event reference")
        if relative.startswith(f"reports/{format_id}/mtgo/") and (
            document.get("scope") != "all_admitted_events" or document.get("event_count") != len(admitted)
        ):
            issues.append(f"{relative}: public report population differs from approved scope")
    return issues


def referenced_event_ids(value: Any, *, source: str = "mtgo", _inherited_source: str = "mtgo") -> set[str]:
    """Keep nested Tabletop references separate from the MTGO admission scope."""
    result: set[str] = set()
    if isinstance(value, dict):
        current_source = value.get("source", _inherited_source)
        if not isinstance(current_source, str) or current_source not in {"mtgo", "melee"}:
            current_source = _inherited_source
        for key, child in value.items():
            if key == "event_id" and child is not None:
                if current_source == source:
                    result.add(str(child))
            elif key in {"event_ids", "source_event_ids"} and isinstance(child, list):
                if current_source == source:
                    result.update(str(item) for item in child)
            else:
                result.update(referenced_event_ids(child, source=source, _inherited_source=current_source))
    elif isinstance(value, list):
        for child in value:
            result.update(referenced_event_ids(child, source=source, _inherited_source=_inherited_source))
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
    from ..config import load_format_registry
    parts = Path(relative).parts
    if len(parts) >= 2 and parts[0] in {"stats", "reports"}:
        registry = load_format_registry(root / "configs/formats.yaml")
        private_formats = {item.id for item in registry.formats if not item.public}
        if parts[1] in private_formats:
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


_MTGO_CLOSURE_FAMILIES = (
    "mtgo_statistics", "mtgo_matchups", "mtgo_top8", "mtgo_hierarchy",
    "mtgo_landing", "public_archetype_names", "classification_reports",
    "mtgo_publication",
)


def _staged_mtgo_closure_issues(closure: Mapping[str, Any]) -> dict[str, str | None]:
    if closure.get("state") == "CURRENT":
        return {}
    families = closure.get("families")
    if not isinstance(families, Mapping):
        return {"closure": "missing families"}
    issues = {}
    for name in _MTGO_CLOSURE_FAMILIES:
        family = families.get(name)
        state = family.get("state") if isinstance(family, Mapping) else None
        if state != "CURRENT":
            issues[name] = state
    return issues


def _prepare_validation_index(root: Path, stage: Path) -> None:
    """Seed local inventory and share objects before hashing candidate bytes."""
    import subprocess
    subprocess.run(["git", "init", "--quiet", str(stage)], check=True)
    subprocess.run(["git", "-C", str(stage), "config", "core.autocrlf", "false"], check=True)
    if (root / ".git").exists():
        def fact(*args):
            return subprocess.run(["git", "-C", str(root), "rev-parse", *args],
                                  check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip()
        objects = fact("--path-format=absolute", "--git-path", "objects")
        if not Path(objects).is_dir() or "\n" in objects or "\r" in objects:
            raise PublicationError("Source Git objects are unavailable")
        # An LF-only alternates file is required by Git on Windows too. No
        # source index is changed, and no refs, remotes or credentials are copied.
        (stage / ".git/objects/info/alternates").write_bytes(Path(objects).as_posix().encode("utf-8") + b"\n")
        import shutil
        shutil.copyfile(fact("--path-format=absolute", "--git-path", "index"), stage / ".git/index")


def _index_validation_candidate(stage: Path) -> None:
    """Compare bytes in Python; ask Git to store only changed blobs.

    Copying an index alone cannot establish equality: copied files have new
    filesystem identities, and equal size/mtime can conceal an actual change.
    """
    import subprocess
    def git(*args, **kwargs):
        return subprocess.run(["git", "-C", str(stage), *args], check=True, capture_output=True, **kwargs).stdout
    indexed = {}
    for record in git("ls-files", "--stage", "-z").split(b"\0"):
        if record:
            entry, name = record.split(b"\t", 1)
            mode, object_id, number = entry.split()
            if number != b"0":
                raise PublicationError("Unmerged source index cannot seed a candidate")
            indexed[name.decode("utf-8")] = object_id
    algorithm = git("rev-parse", "--show-object-format").decode().strip()
    changed, present = [], []
    names = git("ls-files", "--cached", "--others", "--exclude-standard", "-z")
    for name in sorted({item.decode("utf-8") for item in names.split(b"\0") if item}):
        path = stage / name
        if path.is_symlink():
            raise PublicationError("Candidate contains a link")
        if not path.is_file():
            changed.append(name)
            continue
        digest = hashlib.new(algorithm)
        digest.update(f"blob {path.stat().st_size}\0".encode("ascii"))
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        if digest.hexdigest().encode("ascii") != indexed.get(name):
            changed.append(name)
            present.append(name)
    removed = [name for name in changed if name in indexed]
    if removed:
        git("update-index", "--force-remove", "-z", "--stdin", input=b"".join(name.encode("utf-8") + b"\0" for name in removed))
    if present:
        git("add", "--all", "--pathspec-from-file=-", "--pathspec-file-nul",
            input=b"".join(b":(literal)" + name.encode("utf-8") + b"\0" for name in present))


def _validation_snapshot(stage: Path) -> dict[str, str]:
    from ..classifier_closure import _sha256
    return {p.relative_to(stage).as_posix(): _sha256(p) for p in stage.rglob("*")
            if p.is_file() and not {".git", "__pycache__"}.intersection(p.relative_to(stage).parts)}


def _restate_retained_landing(root: Path, stage: Path, format_id: str, week: str) -> None:
    """Rebind this same week's classifier without changing accepted content."""
    import shutil
    from ..classifier_closure import _inspect_landing
    from ..classifier import classifier_digest
    from .normalize import load_rules_for_format
    from . import landing
    relative = Path("stats") / format_id / "mtgo/landing"
    if not (root / relative / "current.json").is_file():
        return
    shutil.copytree(root / relative, stage / relative, dirs_exist_ok=True)
    path = stage / relative / "current.json"
    before = json.loads(path.read_text(encoding="utf-8"))
    if before.get("week", {}).get("id") != week:
        return  # Older admitted weeks retain their original pinned resources.
    desired = classifier_digest(load_rules_for_format(stage, format_id))
    if before.get("classifier", {}).get("digest") in {None, desired}:
        return
    if _inspect_landing(stage, format_id, desired)["state"] != "STALE_REGENERABLE":
        return
    history = {p: json.loads(p.read_text(encoding="utf-8"))
               for p in (stage / relative / "features").glob("*.json")}
    result = landing.generate(stage, format_id, allow_classifier_restatement=True)
    if result["status"] in {"stale_review_required", "summary_review_required"}:
        raise PublicationError(f"BLOCKED_OWNER_REVIEW: retained {format_id} Landing material changed")
    after = json.loads(path.read_text(encoding="utf-8"))
    technical = {"classifier", "review_binding", "data_files"}
    if ({k: v for k, v in before.items() if k not in technical}
            != {k: v for k, v in after.items() if k not in technical}):
        raise PublicationError(f"BLOCKED_OWNER_REVIEW: retained {format_id} Landing content changed")
    for archived, original in history.items():
        current = json.loads(archived.read_text(encoding="utf-8"))
        if ({k: v for k, v in original.items() if k != "classifier_digest"}
                != {k: v for k, v in current.items() if k != "classifier_digest"}):
            raise PublicationError(f"BLOCKED_OWNER_REVIEW: retained Feature content changed: {archived.name}")


def stage_publications(
    root: Path,
    format_ids: Sequence[str],
    *,
    include_landing: bool = False,
    execute: bool = False,
    resume_stage: str | Path | None = None,
) -> dict[str, Any]:
    """Stage one or more accepted formats and materialize them atomically."""
    import os
    import subprocess
    import sys
    from time import perf_counter
    from ..classifier_closure import (
        _copy_repository_to_stage,
        _materialize_with_rollback,
        _protected_input_fingerprints,
        inspect_format,
    )
    from ..classification_reports_cli import generate_reports
    from ..catalog import write_catalog
    from . import completeness, landing, landing_editorial, matchup, metadata, stats, top8

    formats = tuple(format_ids)
    if not formats or len(formats) != len(set(formats)):
        raise PublicationError("publication staging requires unique formats")
    root = root.resolve()
    if resume_stage is None:
        from ..classifier_preparation import prepare_repository_facts
        prepare_repository_facts(root, formats)
    subjects = {format_id: resolve_scope(root, format_id) for format_id in formats}
    protected = {
        format_id: _protected_input_fingerprints(root, format_id)
        for format_id in formats
    }
    from ..generation_progress import GenerationProgress, COMMON, files, implementation
    from ..resource_progress import save
    import shutil
    identity = {"root": str(root), "formats": list(formats), "landing": include_landing}
    locator = root.parent / (root.name + ".publication-" + "-".join(formats) + ".json")
    if resume_stage is None and locator.exists():
        previous = json.loads(locator.read_text(encoding="utf-8"))
        if previous["identity"] != identity:
            raise PublicationError("Existing publication belongs to another scope")
        resume_stage = previous["stage"]
    stage_started = perf_counter()
    if resume_stage is not None:
        stage = Path(resume_stage).resolve()
        if stage == root or stage.is_relative_to(root) or not stage.is_dir():
            raise PublicationError("Resume stage must be an existing external directory")
        # Resume runs current producers on the original mutable staging area.
        # Individual checkpoints decide which generated products remain valid.
        refreshed = ["src", "configs", "my_archetypes", "schemas", *(f"data/{f}" for f in formats),
                     *(f"stats/{f}/melee" for f in formats),
                     *(f"stats/{f}/mtgo/landing/review" for f in formats)]
        for relative in refreshed:
            if (root / relative).is_dir() or (stage / relative).is_dir():
                destination = (stage / relative).resolve()
                if not destination.is_relative_to(stage) or destination == stage:
                    raise PublicationError("Input synchronization escapes the retained stage")
                # Mirror only owned input files, including deletions. Never
                # recursively remove a computed tree or another task's outputs.
                for old in destination.rglob("*"):
                    if old.is_symlink():
                        raise PublicationError("Input synchronization encountered a link")
                    if old.is_file() and not (root / relative / old.relative_to(destination)).is_file():
                        old.unlink()
                if (root / relative).is_dir():
                    shutil.copytree(root / relative, stage / relative, dirs_exist_ok=True)
        for name in ("validate_schemas.py", "validate_output_invariants.py"):
            if (root / name).is_file():
                shutil.copy2(root / name, stage / name)
    else:
        stage = _copy_repository_to_stage(
            root, f"mtgo-publication-{'-'.join(formats)}-"
        )
    save(locator, {"identity": identity, "stage": str(stage)})
    progress = GenerationProgress(stage.with_name(stage.name + ".progress.json"), identity)
    print(
        json.dumps(
            {
                "formats": list(formats),
                "operation": "mtgo-publication-progress",
                "phase": "reuse-stage" if resume_stage is not None else "copy-stage",
                "seconds": round(perf_counter() - stage_started, 3),
            },
            sort_keys=True,
        ),
        file=sys.stderr,
        flush=True,
    )
    # A separate local index gives the existing read-only repository validator
    # its tracked inventory without creating any commit or remote publication.
    index_started = perf_counter()
    _prepare_validation_index(root, stage)
    index_seconds = perf_counter() - index_started
    before_paths = {
        format_id: artifact_paths(root, format_id) for format_id in formats
    }
    before: dict[str, str] = {}
    for format_id in formats:
        for path in (
            *before_paths[format_id],
            f"stats/{format_id}/mtgo/meta.json",
            f"stats/{format_id}/archetype_names.json",
        ):
            before[path] = hashlib.sha256((root / path).read_bytes()).hexdigest()
    for path in ("stats/catalog.json",):
        before[path] = hashlib.sha256((root / path).read_bytes()).hexdigest()
    for format_id in formats:
        prefix = f"stats/{format_id}/mtgo/"
        rules_updated = metadata.rules_last_commit_iso(root, root / "my_archetypes" / f"{format_id}.yaml")
        def landing_step():
            result = landing.generate(stage, format_id)
            if result["status"] in {"stale_review_required", "summary_review_required"}:
                raise PublicationError(f"BLOCKED_OWNER_REVIEW: {format_id}: {result['status']}; stage retained at {stage}")
        steps = [
            ("stats", ["mtgo/stats"], [prefix + "range_*", prefix + "decks_*", prefix + "index.json"], lambda: stats.build_all_stats(stage, format_id)),
            ("matchup", ["mtgo/matchup", "mtgo/stats"], [prefix + "matchup_*.json"], lambda: matchup.build_all_matchups(stage, format_id)),
            ("completeness", ["mtgo/completeness", "mtgo/stats", "mtgo/matchup"], [prefix + "completeness/**/*.json"], lambda: completeness.build_all_completeness(stage, format_id)),
            ("top8", ["mtgo/top8", "mtgo/stats", "mtgo/week_lifecycle"], [prefix + "top8/**/*.json"], lambda: top8.build_all_top8(stage, format_id)),
            ("hierarchy", ["mtgo/metadata", "mtgo/stats", "mtgo/matchup"], [prefix + "archetype_hierarchy.json"], lambda: metadata.generate_hierarchy_catalog(stage, format_id, rules_updated=rules_updated)),
            ("names", ["mtgo/landing_editorial", "mtgo/review_submission", "review_workbook"], [f"stats/{format_id}/archetype_names.json"], lambda: landing_editorial.generate_public_name_contract(stage, format_id)),
            ("reports", ["classification_reports_cli", "reports"], [f"reports/{format_id}/**/*"], lambda: generate_reports(stage, format_id)),
        ]
        if include_landing:
            steps.append(("landing", ["mtgo/landing", "mtgo/landing_editorial", "mtgo/landing_tabletop", "mtgo/landing_screening", "mtgo/review_submission", "mtgo/stats", "mtgo/matchup", "mtgo/top8", "mtgo/week_lifecycle", "review_workbook"], [prefix + "landing/**/*.json"], landing_step))
        else:
            progress.run(f"{format_id}/retained-landing", {
                "inputs": protected[format_id], "scope": subjects[format_id].subject_digest,
                "retained": files(root, [prefix + "landing/**/*.json"]),
                "code": implementation(root, COMMON + ["src/mtgmeta/mtgo/landing*.py", "src/mtgmeta/mtgo/publication.py"])},
                stage, [prefix + "landing/**/*.json"],
                lambda: _restate_retained_landing(root, stage, format_id, subjects[format_id].week.strftime("%G-W%V")))
        for name, modules, outputs, producer in steps:
            inputs = protected[format_id] if name in {"landing", "names"} else {
                p: sha for p, sha in protected[format_id].items() if "/landing/review/" not in p
                and p not in {"configs/mtgo_landing_visuals.yaml", "configs/mtgo_archetype_names.yaml"}}
            basis = {"inputs": inputs, "code": implementation(root, COMMON + [f"src/mtgmeta/{m}.py" for m in modules]),
                     "scope": subjects[format_id].subject_digest}
            if name == "hierarchy":
                basis["rules_updated"] = rules_updated
            progress.run(f"{format_id}/{name}", basis, stage, outputs, producer)
        # Metadata binds all final products; its basis therefore includes their bytes.
        progress.run(f"{format_id}/metadata", {"inputs": protected[format_id],
            "code": implementation(root, COMMON + ["src/mtgmeta/mtgo/metadata.py", "src/mtgmeta/mtgo/publication.py", "src/mtgmeta/mtgo/stats.py", "src/mtgmeta/mtgo/matchup.py"]),
            "products": files(stage, artifact_paths(stage, format_id)),
            "rules_updated": rules_updated}, stage, [prefix + "meta.json"],
            lambda: metadata.generate_metadata(stage, format_id, rules_updated=rules_updated))
    progress.run("catalog", {"meta": files(stage, ["stats/*/mtgo/meta.json", "stats/*/melee/index.json"]),
        "code": implementation(root, ["src/mtgmeta/catalog.py", "src/mtgmeta/config.py"]), "config": files(root, ["configs/formats.yaml"])},
        stage, ["stats/catalog.json"], lambda: write_catalog(stage))
    for format_id in formats:
        issues = inspect_publication(stage, format_id)
        if issues:
            raise PublicationError(
                f"invalid staged publication for {format_id}: {issues}; {stage}"
            )
        closure = inspect_format(stage, format_id)
        stale = _staged_mtgo_closure_issues(closure)
        if stale:
            raise PublicationError(
                f"BLOCKED_OWNER_REVIEW: staged MTGO classifier closure {stale}; {stage}"
            )
        if _protected_input_fingerprints(stage, format_id) != protected[format_id]:
            raise PublicationError(
                f"staging changed a protected input for {format_id}; {stage}"
            )
    index_started = perf_counter()
    _index_validation_candidate(stage)
    index_seconds = round(index_seconds + perf_counter() - index_started, 4)
    print(json.dumps({"operation": "mtgo-publication-progress", "phase": "validation-index",
                      "seconds": index_seconds}), file=sys.stderr, flush=True)
    pythonpath = str(stage / "src")
    inherited_pythonpath = os.environ.get("PYTHONPATH")
    if inherited_pythonpath:
        pythonpath += os.pathsep + inherited_pythonpath
    environment = dict(os.environ, PYTHONPATH=pythonpath)
    # Validate this generated result. Data publication does not modify the
    # classifier engine or execute every other format's regression suite.
    selected_json = sorted({
        "stats/catalog.json",
        *(path for format_id in formats for path in (
            *artifact_paths(stage, format_id), f"stats/{format_id}/mtgo/meta.json",
            f"stats/{format_id}/archetype_names.json"))
    })
    selected_json = [path for path in selected_json if (stage / path).is_file()
                     and (not (root / path).is_file() or (stage / path).read_bytes() != (root / path).read_bytes())]
    commands = []
    if selected_json:
        commands.append(("validate_schemas.py", [arg for path in selected_json for arg in ("--path", path)]))
    commands.append(("validate_output_invariants.py", [arg for fmt in formats for arg in ("--format", fmt)]))
    validated_bytes = _validation_snapshot(stage)
    for script, arguments in commands:
        subprocess.run([sys.executable, "-B", str(stage / script), *arguments],
                       cwd=stage, env=environment, check=True)
    if _validation_snapshot(stage) != validated_bytes:
        raise PublicationError("Read-only validation changed the staged candidate")
    # No final target has been changed if any preceding operation fails.
    final_subject_changed = any(
        artifact_paths(root, format_id) != before_paths[format_id]
        or resolve_scope(root, format_id) != subjects[format_id]
        or _protected_input_fingerprints(root, format_id) != protected[format_id]
        for format_id in formats
    )
    if final_subject_changed or any(
        hashlib.sha256((root / path).read_bytes()).hexdigest() != sha
        for path, sha in before.items()
    ):
        raise PublicationError(f"final subject changed during staging; {stage}")
    progress.validated()
    paths = sorted(
        {
            "stats/catalog.json",
            *(
                path
                for format_id in formats
                for path in (
                    *artifact_paths(stage, format_id),
                    f"stats/{format_id}/mtgo/meta.json",
                    f"stats/{format_id}/archetype_names.json",
                )
            ),
        }
    )
    changed = [path for path in paths if not (root / path).is_file()
               or (root / path).read_bytes() != (stage / path).read_bytes()]
    if execute:
        def validate_final():
            failures = {
                format_id: issues
                for format_id in formats
                if (issues := inspect_publication(root, format_id))
            }
            if failures:
                raise PublicationError(str(failures))
        _materialize_with_rollback(root, stage, changed, validate_final=validate_final)
    return {"formats": list(formats), "stage": str(stage), "executed": execute,
            "publication_node": "landing_content" if include_landing else "reviewed_data",
            "scope_digests": {
                format_id: subjects[format_id].subject_digest
                for format_id in formats
            },
            "changed_paths": changed, "generation_progress": str(progress.path),
            "reused_steps": progress.reused, "executed_steps": progress.executed,
            "index_seconds": index_seconds}


def stage_publication(root: Path, format_id: str, *, include_landing: bool = False,
                      execute: bool = False, resume_stage: str | Path | None = None) -> dict[str, Any]:
    """Backward-compatible single-format publication staging."""
    result = stage_publications(
        root,
        (format_id,),
        include_landing=include_landing,
        execute=execute, resume_stage=resume_stage,
    )
    return {
        "format": format_id,
        "stage": result["stage"],
        "executed": result["executed"],
        "publication_node": result["publication_node"],
        "scope_digest": result["scope_digests"][format_id],
        "changed_paths": result["changed_paths"],
    }


def intentional_unknowns(
    root: Path,
    formats: tuple[str, ...] | None = None,
) -> dict[str, dict[tuple[str, str, str], dict[str, str]]]:
    """Read the existing random-card-pile policy, without expanding its scope."""
    config = yaml.safe_load((root / "configs/mtgo_intentional_unknowns.yaml").read_text(encoding="utf-8"))
    if config.get("schema_version") != "1.0.0":
        raise ValueError("Intentional Unknown registry has an unsupported schema version")
    records = config.get("records")
    if not isinstance(records, list):
        raise ValueError("Intentional Unknown registry has no records list")
    if formats is None:
        formats = ("standard", "modern")
    if not formats or len(formats) != len(set(formats)):
        raise ValueError("Intentional Unknown format scope is empty or duplicated")
    result: dict[str, dict[tuple[str, str, str], dict[str, str]]] = {
        format_name: {} for format_name in formats
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
        if format_name not in result:
            continue
        if not event_id.isdigit() or not deck_id or not source_file:
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
    accepted_unknown = intentional_unknowns(root, (format_id,))[format_id]
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
