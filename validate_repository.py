"""Run deterministic changed-scope or full validation of repository content."""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import subprocess
import tokenize
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import yaml


class InfrastructureError(Exception):
    """Indicate that validation could not be performed reliably."""


@dataclass(frozen=True)
class Failure:
    category: str
    path: str
    message: str
    line: int | None = None
    column: int | None = None


CATEGORY_ORDER = {
    "Python": 0,
    "JavaScript": 1,
    "JSON": 2,
    "YAML": 3,
    "References": 4,
    "Hygiene": 5,
}

FORBIDDEN_TRACKED_PARTS = {"__pycache__", ".pytest_cache", ".venv", "node_modules"}
FORBIDDEN_TRACKED_NAMES = {".ds_store", "thumbs.db"}
FORBIDDEN_TRACKED_SUFFIXES = (".pyc", ".pyo", ".log", ".tmp", ".bak", ".swp")

PHASE8_PRODUCTION_RESOURCES = (
    "assets/css/phase8-base.css",
    "assets/css/phase8-candidate.css",
    "assets/js/phase8/runtime.js",
    "assets/js/phase8/i18n.js",
    "assets/js/phase8/card-localization.js",
    "assets/js/phase8/archetype-names.js",
    "assets/js/phase8/matchup-model.js",
    "assets/js/phase8/mtgo-controller.js",
    "assets/js/phase8/tabletop-controller.js",
    "assets/js/phase8/archetype-visuals.js",
    "assets/js/phase8/app-core.js",
    "assets/js/phase8/app-freshness.js",
    "assets/js/phase8/app-mtgo.js",
    "assets/js/phase8/app-mobile-render.js",
    "assets/js/phase8/app-mobile-interactions.js",
    "assets/js/phase8/app-loading.js",
    "assets/js/phase8/app-card-preview.js",
    "assets/js/phase8/app-metadata.js",
    "assets/js/phase8/app-tabletop.js",
    "assets/js/phase8/app.js",
)
MAINTAINED_JAVASCRIPT = (
    "assets/js/common.js",
    "assets/js/matchup.js",
    "assets/js/mtgo.js",
    "assets/js/phase8/runtime.js",
    "assets/js/phase8/i18n.js",
    "assets/js/phase8/card-localization.js",
    "assets/js/phase8/archetype-names.js",
    "assets/js/phase8/matchup-model.js",
    "assets/js/phase8/mtgo-controller.js",
    "assets/js/phase8/tabletop-controller.js",
    "assets/js/phase8/archetype-visuals.js",
    "assets/js/phase8/app-core.js",
    "assets/js/phase8/app-freshness.js",
    "assets/js/phase8/app-mtgo.js",
    "assets/js/phase8/app-mobile-render.js",
    "assets/js/phase8/app-mobile-interactions.js",
    "assets/js/phase8/app-loading.js",
    "assets/js/phase8/app-card-preview.js",
    "assets/js/phase8/app-metadata.js",
    "assets/js/phase8/app-tabletop.js",
    "assets/js/phase8/app.js",
)
REQUIRED_GOVERNANCE_DOCUMENTS = (
    "AGENTS.md",
    "docs/PROJECT_SCOPE.md",
    "docs/STATISTICS_SPEC.md",
    "docs/DATA_ARCHITECTURE.md",
    "docs/ROADMAP.md",
    "docs/DECISIONS.md",
    "docs/STATUS.yaml",
    "docs/DEVELOPMENT_WORKFLOW.md",
    "docs/history/README.md",
)
TEST_TRIGGER_MATRIX_PATH = "docs/TEST_TRIGGER_MATRIX.md"
ALLOWED_TEST_ORACLES = frozenset(
    {
        "current-candidate-invariant",
        "external-contract",
        "owner-rule-contract",
        "policy",
        "protected-compatibility",
        "schema",
        "synthetic",
        "workflow",
    }
)
TEST_FILE_PATTERN = re.compile(r"tests/(?:[^/]+/)*test_[^/]+\.py")
HISTORICAL_TEST_NAME_PATTERN = re.compile(
    r"(?:^|[_-])w\d{1,2}(?:[_-]|$)|\d{5,}", re.IGNORECASE
)
PUBLIC_PRODUCT_NAMES = {
    "mtgo": "MTGO Environment Trends",
    "tabletop": "Tabletop Major Events",
}
PUBLIC_PRODUCT_ENTRIES = {
    "mtgo": "/index.html",
    "tabletop": "/melee/index.html",
}
CLASSIFIER_NAME_CATALOG = "configs/mtgo_archetype_names.yaml"
PHASE8_FRONTEND_ENTRIES = {
    "index.html": {
        "stylesheets": (
            "assets/css/phase8-base.css",
            "assets/css/phase8-candidate.css",
        ),
        "scripts": (
            "assets/js/phase8/runtime.js",
            "assets/js/phase8/i18n.js",
            "assets/js/phase8/card-localization.js",
            "assets/js/phase8/archetype-names.js",
            "assets/js/phase8/matchup-model.js",
            "assets/js/phase8/mtgo-controller.js",
            "assets/js/phase8/archetype-visuals.js",
            "assets/js/phase8/app-core.js",
            "assets/js/phase8/app-freshness.js",
            "assets/js/phase8/app-mtgo.js",
            "assets/js/phase8/app-mobile-render.js",
            "assets/js/phase8/app-mobile-interactions.js",
            "assets/js/phase8/app-loading.js",
            "assets/js/phase8/app-card-preview.js",
            "assets/js/phase8/app-metadata.js",
            "assets/js/phase8/app.js",
        ),
    },
    "melee/index.html": {
        "stylesheets": (
            "../assets/css/phase8-base.css",
            "../assets/css/phase8-candidate.css",
        ),
        "scripts": (
            "../assets/js/phase8/runtime.js",
            "../assets/js/phase8/i18n.js",
            "../assets/js/phase8/card-localization.js",
            "../assets/js/phase8/archetype-names.js",
            "../assets/js/phase8/matchup-model.js",
            "../assets/js/phase8/mtgo-controller.js",
            "../assets/js/phase8/tabletop-controller.js",
            "../assets/js/phase8/archetype-visuals.js",
            "../assets/js/phase8/app-core.js",
            "../assets/js/phase8/app-freshness.js",
            "../assets/js/phase8/app-mtgo.js",
            "../assets/js/phase8/app-tabletop.js",
            "../assets/js/phase8/app-mobile-render.js",
            "../assets/js/phase8/app-mobile-interactions.js",
            "../assets/js/phase8/app-loading.js",
            "../assets/js/phase8/app-card-preview.js",
            "../assets/js/phase8/app-metadata.js",
            "../assets/js/phase8/app.js",
        ),
    },
}

REFERENCE_GROUPS = frozenset(
    {
        "governance",
        "requirements",
        "frontend-templates",
        "phase8-entries",
        "required-standard-files",
        "pickup-indexes",
        "classifier-closure",
        "test-inventory",
    }
)
REQUIREMENT_MANIFESTS = ("requirements.txt", "requirements-dev.txt")
LEGACY_FRONTEND_FILES = (
    "index.html",
    "assets/js/common.js",
    "assets/js/matchup.js",
    "assets/js/mtgo.js",
)
REQUIRED_STANDARD_FILES = (
    "stats/standard/mtgo/meta.json",
    "stats/standard/mtgo/range_1w.json",
    "stats/standard/mtgo/range_4w.json",
    "stats/standard/mtgo/range_12w.json",
    "stats/standard/mtgo/decks_1w.json",
    "stats/standard/mtgo/decks_4w.json",
    "stats/standard/mtgo/decks_12w.json",
    "stats/standard/mtgo/matchup_1w.json",
    "stats/standard/mtgo/matchup_4w.json",
    "stats/standard/mtgo/matchup_12w.json",
)
PUBLIC_PRODUCT_FACT_SOURCES = frozenset(
    {
        "README.md",
        "stats/catalog.json",
        "configs/melee_events.yaml",
    }
)
CATALOG_CONSISTENCY_SOURCES = frozenset(
    {
        "configs/formats.yaml",
        "stats/catalog.json",
        "src/mtgmeta/catalog.py",
    }
)
FRONTEND_REFERENCE_TRIGGERS = frozenset(
    set(PHASE8_PRODUCTION_RESOURCES)
    | set(PHASE8_FRONTEND_ENTRIES)
    | set(LEGACY_FRONTEND_FILES)
)


@dataclass(frozen=True)
class ValidationPlan:
    candidates: tuple[str, ...]
    javascript: tuple[str, ...]
    reference_groups: frozenset[str]
    public_product_facts: bool
    catalog_consistency: bool
    hygiene: tuple[str, ...]


class FrontendAssetParser(HTMLParser):
    """Collect local stylesheet and script references from an HTML entry."""

    def __init__(self) -> None:
        super().__init__()
        self.stylesheets: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        if tag == "link":
            rel = attributes.get("rel", "")
            href = attributes.get("href")
            if href and "stylesheet" in rel.lower().split():
                self.stylesheets.append(href)
        elif tag == "script":
            source = attributes.get("src")
            if source:
                self.scripts.append(source)


def repository_root() -> Path:
    try:
        return Path(__file__).resolve().parent
    except OSError as exc:
        raise InfrastructureError(f"cannot determine repository root: {exc}") from exc


def tracked_files(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=root, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        deleted_result = subprocess.run(
            ["git", "ls-files", "-z", "--deleted"], cwd=root, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise InfrastructureError(f"cannot obtain tracked-file inventory: {exc}") from exc
    try:
        names = {name for name in result.stdout.decode("utf-8").split("\0") if name}
        deleted = {
            name for name in deleted_result.stdout.decode("utf-8").split("\0") if name
        }
        return sorted(names - deleted)
    except UnicodeDecodeError as exc:
        raise InfrastructureError(f"tracked-file inventory is not UTF-8: {exc}") from exc


def changed_files(root: Path, base: str) -> list[str]:
    """Return committed, staged, working-tree, and untracked paths changed from base."""

    try:
        resolved = subprocess.run(
            ["git", "rev-parse", "--verify", f"{base}^{{commit}}"],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        diff = subprocess.run(
            ["git", "diff", "--name-only", "-z", "--no-renames", resolved, "--"],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        untracked = subprocess.run(
            ["git", "ls-files", "-z", "--others", "--exclude-standard"],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise InfrastructureError(
            f"cannot obtain changed-file inventory from {base!r}: {exc}"
        ) from exc
    try:
        return sorted(
            {
                name
                for name in (diff + untracked).decode("utf-8").split("\0")
                if name
            }
        )
    except UnicodeDecodeError as exc:
        raise InfrastructureError(f"changed-file inventory is not UTF-8: {exc}") from exc


def reference_groups_for_paths(paths: set[str]) -> frozenset[str]:
    groups: set[str] = set()
    if paths.intersection(REQUIRED_GOVERNANCE_DOCUMENTS):
        groups.add("governance")
    if paths.intersection(REQUIREMENT_MANIFESTS):
        groups.add("requirements")
    if paths.intersection(FRONTEND_REFERENCE_TRIGGERS):
        groups.update(("frontend-templates", "phase8-entries"))
    if paths.intersection(REQUIRED_STANDARD_FILES):
        groups.add("required-standard-files")
    if any(
        path.startswith(f"stats/{format_id}/mtgo/pickup/")
        for path in paths
        for format_id in ("standard", "modern")
    ):
        groups.add("pickup-indexes")
    if any(
        path in {
            "configs/formats.yaml",
            "configs/mtgo_archetype_names.yaml",
            "configs/melee_events.yaml",
            "stats/catalog.json",
            "src/mtgmeta/classifier.py",
            "src/mtgmeta/classifier_closure.py",
            "src/mtgmeta/mtgo/publication.py",
            "src/mtgmeta/mtgo/stats.py",
            "src/mtgmeta/mtgo/matchup.py",
            "src/mtgmeta/mtgo/completeness.py",
            "src/mtgmeta/mtgo/top8.py",
            "src/mtgmeta/mtgo/metadata.py",
            "src/mtgmeta/classification_reports_cli.py",
            "configs/mtgo_weekly_review_completions.yaml",
            "src/mtgmeta/reports.py",
            "src/mtgmeta/melee/classification.py",
            "src/mtgmeta/mtgo/landing.py",
            "src/mtgmeta/mtgo/landing_editorial.py",
        }
        or path.startswith("my_archetypes/")
        or path.startswith(("stats/", "reports/"))
        or (path.startswith("data/") and path.count("/") == 2)
        or re.fullmatch(r"data/[^/]+/melee/(classifications|opportunities)/.+", path)
        for path in paths
    ):
        groups.add("classifier-closure")
    if (
        TEST_TRIGGER_MATRIX_PATH in paths
        or "validate_repository.py" in paths
        or any(TEST_FILE_PATTERN.fullmatch(path) for path in paths)
    ):
        groups.add("test-inventory")
    return frozenset(groups)


def changed_validation_plan(changed: list[str], tracked: list[str]) -> ValidationPlan:
    changed_set = set(changed)
    tracked_set = set(tracked)
    existing = changed_set.intersection(tracked_set)
    public_product_facts = any(
        path in PUBLIC_PRODUCT_FACT_SOURCES
        or path == CLASSIFIER_NAME_CATALOG
        or (
            path.startswith("stats/")
            and (
                path.endswith("/archetype_names.json")
                or "/melee/" in path
            )
        )
        for path in changed_set
    )
    return ValidationPlan(
        candidates=tuple(sorted(existing)),
        javascript=tuple(sorted(name for name in existing if name.endswith(".js"))),
        reference_groups=reference_groups_for_paths(changed_set),
        public_product_facts=public_product_facts,
        catalog_consistency=bool(changed_set.intersection(CATALOG_CONSISTENCY_SOURCES)),
        hygiene=tuple(sorted(existing)),
    )


def safe_path(root: Path, name: str) -> Path:
    if "\\" in name or Path(name).is_absolute() or ".." in Path(name).parts:
        raise InfrastructureError(f"unsafe repository path: {name}")
    path = (root / Path(name)).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise InfrastructureError(f"path escapes repository: {name}") from exc
    return path


def read_bytes(root: Path, name: str) -> bytes:
    path = safe_path(root, name)
    try:
        if not path.is_file():
            raise InfrastructureError(f"listed file is not a regular file: {name}")
        return path.read_bytes()
    except OSError as exc:
        raise InfrastructureError(f"cannot safely read {name}: {exc}") from exc


def content_failure(category: str, path: str, exc: Exception) -> Failure:
    line = column = None
    if isinstance(exc, SyntaxError):
        line, column = exc.lineno, exc.offset
    elif isinstance(exc, json.JSONDecodeError):
        line, column = exc.lineno, exc.colno
    elif isinstance(exc, yaml.MarkedYAMLError) and exc.problem_mark is not None:
        line, column = exc.problem_mark.line + 1, exc.problem_mark.column + 1
    return Failure(category, path, f"{type(exc).__name__}: {exc}", line, column)


def decode_python(data: bytes) -> str:
    encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
    return data.decode(encoding)


def validate_test_subprocess_environments(name: str, tree: ast.AST) -> list[Failure]:
    """Require source-tree package subprocesses to declare their import path."""

    parts = Path(name).parts
    if not parts or parts[0] != "tests":
        return []

    def references_package(node: ast.AST) -> bool:
        return any(
            isinstance(value, ast.Constant)
            and isinstance(value.value, str)
            and "mtgmeta" in value.value
            for value in ast.walk(node)
        )

    command_factories = {
        node.name
        for node in getattr(tree, "body", [])
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and references_package(node)
    }
    command_values: set[str] = set()
    for node in getattr(tree, "body", []):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if value is None or not references_package(value):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        command_values.update(
            target.id for target in targets if isinstance(target, ast.Name)
        )

    failures: list[Failure] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
            and node.func.attr == "run"
        ):
            continue
        if not node.args:
            continue
        command = node.args[0]
        invokes_package = (
            references_package(command)
            or any(
                isinstance(value, ast.Name) and value.id in command_values
                for value in ast.walk(command)
            )
            or any(
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Name)
                and value.func.id in command_factories
                for value in ast.walk(command)
            )
        )
        if not invokes_package:
            continue
        explicit_source_path = any(
            keyword.arg == "env"
            and any(
                isinstance(value, ast.Constant) and value.value == "PYTHONPATH"
                for value in ast.walk(keyword.value)
            )
            for keyword in node.keywords
        )
        if not explicit_source_path:
            failures.append(
                Failure(
                    "Python",
                    name,
                    "mtgmeta test subprocess must declare PYTHONPATH in env",
                    node.lineno,
                    node.col_offset + 1,
                )
            )
    return failures


def validate_javascript_syntax(root: Path, names: list[str]) -> list[Failure]:
    """Use Node.js to parse every maintained browser JavaScript file."""

    failures: list[Failure] = []
    for name in names:
        path = safe_path(root, name)
        if not path.is_file():
            failures.append(Failure("JavaScript", name, "missing maintained JavaScript file"))
            continue
        try:
            result = subprocess.run(
                ["node", "--check", str(path)],
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
        except OSError as exc:
            raise InfrastructureError(f"cannot run Node.js syntax check: {exc}") from exc
        if result.returncode:
            detail = (result.stderr or result.stdout).strip().replace("\n", " ")
            failures.append(
                Failure(
                    "JavaScript",
                    name,
                    f"node --check failed: {detail or f'exit status {result.returncode}'}",
                )
            )
    return failures


def validate_files(
    root: Path,
    names: list[str],
    javascript_names: tuple[str, ...] = MAINTAINED_JAVASCRIPT,
) -> tuple[dict[str, int], list[Failure], dict[str, Any]]:
    failures: list[Failure] = []
    parsed_status: dict[str, Any] = {}
    groups = {
        "Python": [n for n in names if n.lower().endswith(".py")],
        "JavaScript": [n for n in javascript_names if n in names],
        "JSON": [n for n in names if n.lower().endswith(".json")],
        "YAML": [n for n in names if n.lower().endswith((".yaml", ".yml"))],
    }
    for name in groups["Python"]:
        try:
            tree = ast.parse(decode_python(read_bytes(root, name)), filename=name)
            failures.extend(validate_test_subprocess_environments(name, tree))
        except SyntaxError as exc:
            failures.append(content_failure("Python", name, exc))
        except (tokenize.TokenError, LookupError, UnicodeError) as exc:
            failures.append(content_failure("Python", name, exc))
    failures.extend(validate_javascript_syntax(root, groups["JavaScript"]))
    for name in groups["JSON"]:
        try:
            json.loads(read_bytes(root, name).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            failures.append(content_failure("JSON", name, exc))
    for name in groups["YAML"]:
        try:
            value = yaml.safe_load(read_bytes(root, name).decode("utf-8"))
            if name == "docs/STATUS.yaml":
                parsed_status[name] = value
        except (yaml.YAMLError, UnicodeDecodeError) as exc:
            failures.append(content_failure("YAML", name, exc))
    counts = {label: len(files) for label, files in groups.items()}
    return counts, failures, parsed_status


def tracked_regular(root: Path, names: set[str], name: str, suffix: str | None = None) -> bool:
    if name not in names or (suffix and not name.lower().endswith(suffix)):
        return False
    return safe_path(root, name).is_file()


def reference_check(failures: list[Failure], path: str, message: str | None) -> None:
    if message:
        failures.append(Failure("References", path, message))


def validate_phase8_frontend_references(
    root: Path, names: list[str]
) -> tuple[int, list[Failure]]:
    """Protect both published entries and their declared Phase 8 resources."""

    failures: list[Failure] = []
    tracked = set(names)
    checked = 0
    for resource in PHASE8_PRODUCTION_RESOURCES:
        checked += 1
        reference_check(
            failures,
            resource,
            None
            if tracked_regular(root, tracked, resource)
            else "missing tracked Phase 8 production resource",
        )
    for entry, expected in PHASE8_FRONTEND_ENTRIES.items():
        checked += 1
        if not tracked_regular(root, tracked, entry):
            reference_check(failures, entry, "missing tracked production HTML entry")
            continue
        try:
            source = read_bytes(root, entry).decode("utf-8")
        except UnicodeDecodeError as exc:
            reference_check(
                failures,
                entry,
                f"production HTML entry is not UTF-8: {exc}",
            )
            continue
        parser = FrontendAssetParser()
        parser.feed(source)
        parser.close()
        if tuple(parser.stylesheets) != expected["stylesheets"]:
            reference_check(
                failures,
                entry,
                "unexpected Phase 8 stylesheet references "
                f"{parser.stylesheets!r}; expected {list(expected['stylesheets'])!r}",
            )
        if tuple(parser.scripts) != expected["scripts"]:
            reference_check(
                failures,
                entry,
                "unexpected Phase 8 script references "
                f"{parser.scripts!r}; expected {list(expected['scripts'])!r}",
            )
    return checked, failures


def validate_public_product_facts(
    root: Path,
    names: list[str],
    *,
    defer_tabletop_readme: bool = False,
) -> tuple[int, list[Failure]]:
    """Require README to match public catalogs, event config, and live entries."""

    failures: list[Failure] = []
    tracked = set(names)
    required = (
        "README.md",
        "stats/catalog.json",
        "configs/melee_events.yaml",
        CLASSIFIER_NAME_CATALOG,
    )
    checked = len(required)
    for name in required:
        if not tracked_regular(root, tracked, name):
            reference_check(failures, name, "missing public-product fact source")
    if failures:
        return checked, failures

    try:
        readme = read_bytes(root, "README.md").decode("utf-8")
        catalog = json.loads(read_bytes(root, "stats/catalog.json").decode("utf-8"))
        event_config = yaml.safe_load(read_bytes(root, "configs/melee_events.yaml"))
        name_catalog = yaml.safe_load(read_bytes(root, CLASSIFIER_NAME_CATALOG))
    except (json.JSONDecodeError, UnicodeDecodeError, yaml.YAMLError) as exc:
        reference_check(failures, "public product facts", f"invalid source: {exc}")
        return checked, failures

    formats = catalog.get("formats") if isinstance(catalog, dict) else None
    approved_names = (
        name_catalog.get("names") if isinstance(name_catalog, dict) else None
    )
    configured_events = (
        event_config.get("events") if isinstance(event_config, dict) else None
    )
    if (
        not isinstance(formats, list)
        or not isinstance(approved_names, list)
        or not isinstance(configured_events, list)
    ):
        reference_check(
            failures,
            "public product facts",
            "missing catalog formats, approved classifier names, or enabled events",
        )
        return checked, failures
    mtgo_entry = PUBLIC_PRODUCT_ENTRIES["mtgo"]
    tabletop_entry = PUBLIC_PRODUCT_ENTRIES["tabletop"]

    labels: dict[str, str] = {}
    catalog_products: dict[str, set[str]] = {}
    tabletop_catalog_paths: dict[str, str] = {}
    for entry in formats:
        if not isinstance(entry, dict):
            continue
        format_id = entry.get("id")
        display_name = entry.get("display_name")
        products = entry.get("products")
        if not isinstance(format_id, str) or not isinstance(display_name, str) or not isinstance(products, list):
            continue
        labels[format_id] = display_name
        catalog_products[format_id] = {
            product["id"]
            for product in products
            if isinstance(product, dict)
            and isinstance(product.get("id"), str)
            and product.get("available") is True
        }
        for product in products:
            if (
                isinstance(product, dict)
                and product.get("id") == "tabletop-major-events"
                and product.get("available") is True
            ):
                path = product.get("path")
                if isinstance(path, str):
                    tabletop_catalog_paths[format_id] = path
                else:
                    reference_check(
                        failures,
                        "stats/catalog.json",
                        f"available Tabletop format {format_id!r} requires a catalog path",
                    )

    mtgo_catalog_formats = tuple(
        format_id for format_id in labels if "mtgo-statistics" in catalog_products[format_id]
    )
    tabletop_catalog_formats = tuple(
        format_id
        for format_id in labels
        if "tabletop-major-events" in catalog_products[format_id]
    )
    public_formats = tuple(
        format_id for format_id in labels if catalog_products[format_id]
    )
    from mtgmeta.mtgo.landing_editorial import (
        MTGOLandingEditorialError,
        build_public_name_contract,
    )

    for format_id in public_formats:
        contract_path = f"stats/{format_id}/archetype_names.json"
        checked += 1
        if not tracked_regular(root, tracked, contract_path):
            reference_check(
                failures,
                contract_path,
                "missing public classifier-name contract",
            )
            continue
        try:
            expected_contract = build_public_name_contract(root, format_id)
        except (MTGOLandingEditorialError, OSError, ValueError) as exc:
            reference_check(
                failures,
                CLASSIFIER_NAME_CATALOG,
                f"invalid approved classifier names: {exc}",
            )
            continue
        try:
            public_contract = json.loads(
                read_bytes(root, contract_path).decode("utf-8")
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            reference_check(
                failures,
                contract_path,
                f"invalid public classifier-name contract: {exc}",
            )
            continue
        if public_contract != expected_contract:
            reference_check(
                failures,
                contract_path,
                "does not match the approved bilingual name catalog",
            )
    event_ids_by_format: dict[str, list[str]] = {
        format_id: [] for format_id in tabletop_catalog_formats
    }
    enabled_tabletop_events = [
        event
        for event in configured_events
        if isinstance(event, dict)
        and event.get("enabled") is True
        and event.get("tabletop") is True
    ]
    configured_event_keys: set[tuple[str, str]] = set()
    for event in enabled_tabletop_events:
        format_id = event.get("format")
        event_id = event.get("id")
        if not isinstance(format_id, str) or not isinstance(event_id, (str, int)):
            reference_check(
                failures,
                "configs/melee_events.yaml",
                "enabled tabletop event requires format and id",
            )
            continue
        if event.get("review_status") == "verified":
            configured_event_keys.add((format_id, str(event_id)))

    for format_id in tabletop_catalog_formats:
        catalog_path = tabletop_catalog_paths.get(format_id)
        if catalog_path is None:
            continue
        checked += 1
        if not tracked_regular(root, tracked, catalog_path):
            reference_check(failures, catalog_path, "missing public event catalog")
            continue
        try:
            event_catalog = json.loads(read_bytes(root, catalog_path).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            reference_check(failures, catalog_path, f"invalid public event catalog: {exc}")
            continue
        catalog_format = (
            event_catalog.get("format") if isinstance(event_catalog, dict) else None
        )
        public_events = (
            event_catalog.get("events") if isinstance(event_catalog, dict) else None
        )
        if catalog_format != format_id or not isinstance(public_events, list):
            reference_check(
                failures,
                catalog_path,
                f"must contain format {format_id!r} and an events list",
            )
            continue
        for event in public_events:
            event_id = event.get("event_id") if isinstance(event, dict) else None
            if not isinstance(event_id, (str, int)):
                reference_check(
                    failures,
                    catalog_path,
                    "public event requires an event_id",
                )
                continue
            rendered_event_id = str(event_id)
            event_ids_by_format[format_id].append(rendered_event_id)
            if (format_id, rendered_event_id) not in configured_event_keys:
                reference_check(
                    failures,
                    catalog_path,
                    f"public event {rendered_event_id!r} requires an enabled, verified Tabletop whitelist entry",
                )
        if not event_ids_by_format[format_id]:
            reference_check(
                failures,
                catalog_path,
                "available Tabletop format requires at least one public event",
            )

    def format_label(format_id: str, event_ids: list[str] | None = None) -> str:
        label = labels[format_id]
        if not event_ids:
            return label
        noun = "event" if len(event_ids) == 1 else "events"
        rendered_ids = ", ".join(f"`{event_id}`" for event_id in event_ids)
        return f"{label} ({noun} {rendered_ids})"

    expected_rows = [
        f"| {PUBLIC_PRODUCT_NAMES['mtgo']} | "
        f"{', '.join(format_label(format_id) for format_id in mtgo_catalog_formats)} | "
        f"`{mtgo_entry}` |",
    ]
    if not defer_tabletop_readme:
        expected_rows.append(
            f"| {PUBLIC_PRODUCT_NAMES['tabletop']} | "
            f"{', '.join(format_label(format_id, event_ids_by_format[format_id]) for format_id in tabletop_catalog_formats)} | "
            f"`{tabletop_entry}` |"
        )
    checked += len(expected_rows) + 2
    for row in expected_rows:
        if row not in readme:
            reference_check(failures, "README.md:Current public products", f"missing or inconsistent row {row!r}")
    return checked, failures


def validate_catalog_consistency(
    root: Path,
    names: list[str],
) -> tuple[int, list[Failure]]:
    """Treat the stored catalog as a derivative of registry state and files."""

    failures: list[Failure] = []
    tracked = set(names)
    required = ("configs/formats.yaml", "stats/catalog.json")
    for name in required:
        if not tracked_regular(root, tracked, name):
            reference_check(failures, name, "missing catalog consistency source")
    if failures:
        return len(required), failures

    try:
        catalog = json.loads(read_bytes(root, "stats/catalog.json").decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        reference_check(
            failures,
            "stats/catalog.json",
            f"invalid catalog consistency source: {exc}",
        )
        return len(required) + 1, failures
    generated = catalog.get("generated") if isinstance(catalog, dict) else None
    if not isinstance(generated, str) or not generated:
        reference_check(
            failures,
            "stats/catalog.json",
            "catalog requires a generated timestamp for deterministic consistency checking",
        )
        return len(required) + 1, failures

    try:
        from mtgmeta.catalog import build_catalog

        expected = build_catalog(root, generated_at=generated)
    except (ImportError, OSError, ValueError) as exc:
        reference_check(
            failures,
            "configs/formats.yaml",
            f"cannot resolve complete public format qualification: {exc}",
        )
        return len(required) + 1, failures
    if catalog != expected:
        reference_check(
            failures,
            "stats/catalog.json",
            "does not match the registry-derived complete public format qualification and product files",
        )
    return len(required) + 1, failures


def _root_path_segment(node: ast.AST) -> str | None:
    segments: list[str] = []
    current = node
    while isinstance(current, ast.BinOp) and isinstance(current.op, ast.Div):
        if not isinstance(current.right, ast.Constant) or not isinstance(
            current.right.value, str
        ):
            return None
        segments.append(current.right.value)
        current = current.left
    if not isinstance(current, ast.Name) or current.id != "ROOT" or not segments:
        return None
    first = segments[-1].replace("\\", "/").split("/", 1)[0]
    return first or None


def _literal_prefix(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr) and node.values:
        first = node.values[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            return first.value
    return None


def _repository_live_roots(source: str) -> set[str]:
    tree = ast.parse(source)
    roots = {
        segment
        for node in ast.walk(tree)
        if isinstance(node, ast.BinOp)
        and (segment := _root_path_segment(node)) is not None
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "_json":
            continue
        prefix = _literal_prefix(node.args[0])
        if prefix:
            roots.add(prefix.replace("\\", "/").split("/", 1)[0])
    return roots


def validate_test_inventory(
    root: Path, names: list[str]
) -> tuple[int, list[Failure]]:
    """Require one independent, trigger-bound contract for every Python test."""

    failures: list[Failure] = []
    tracked = set(names)
    actual = sorted(name for name in tracked if TEST_FILE_PATTERN.fullmatch(name))
    if TEST_TRIGGER_MATRIX_PATH not in tracked:
        return 1, [
            Failure(
                "References",
                TEST_TRIGGER_MATRIX_PATH,
                "missing machine-enforced test trigger matrix",
            )
        ]

    matrix = read_bytes(root, TEST_TRIGGER_MATRIX_PATH).decode("utf-8")
    section_start = matrix.find("## Retained Python tests")
    section_end = matrix.find("\n## ", section_start + 1)
    if section_start < 0 or section_end < 0:
        return 1, [
            Failure(
                "References",
                TEST_TRIGGER_MATRIX_PATH,
                "missing bounded Retained Python tests section",
            )
        ]

    registered: dict[str, tuple[str, int]] = {}
    for line_number, raw in enumerate(matrix[:section_end].splitlines(), 1):
        if line_number <= matrix[:section_start].count("\n") or not raw.startswith("| `tests/test_"):
            continue
        cells = [cell.strip() for cell in raw.strip().strip("|").split("|")]
        if len(cells) != 5:
            failures.append(
                Failure(
                    "References",
                    TEST_TRIGGER_MATRIX_PATH,
                    "each retained Python test row must have five columns",
                    line_number,
                )
            )
            continue
        match = re.fullmatch(r"`(tests/(?:[^/]+/)*test_[^/]+\.py)`", cells[0])
        if match is None:
            failures.append(
                Failure(
                    "References",
                    TEST_TRIGGER_MATRIX_PATH,
                    "test inventory rows must name one complete top-level Python test file",
                    line_number,
                )
            )
            continue
        path = match.group(1)
        if any(not cells[index] for index in (1, 2, 3)):
            failures.append(
                Failure(
                    "References",
                    TEST_TRIGGER_MATRIX_PATH,
                    f"trigger, purpose, and minimum subject are required for {path}",
                    line_number,
                )
            )
        oracle_match = re.fullmatch(r"`([^`]+)`", cells[4])
        oracle = oracle_match.group(1) if oracle_match else ""
        if path in registered:
            failures.append(
                Failure(
                    "References",
                    TEST_TRIGGER_MATRIX_PATH,
                    f"duplicate test registration for {path}",
                    line_number,
                )
            )
            continue
        registered[path] = (oracle, line_number)
        if oracle not in ALLOWED_TEST_ORACLES:
            failures.append(
                Failure(
                    "References",
                    TEST_TRIGGER_MATRIX_PATH,
                    f"invalid independent oracle {oracle!r} for {path}",
                    line_number,
                )
            )

    for path in sorted(set(actual) - set(registered)):
        failures.append(
            Failure(
                "References",
                path,
                "unregistered Python test; declare its trigger, purpose, minimum subject, and independent oracle",
            )
        )
    for path in sorted(set(registered) - set(actual)):
        failures.append(
            Failure(
                "References",
                TEST_TRIGGER_MATRIX_PATH,
                f"stale Python test registration for {path}",
                registered[path][1],
            )
        )

    for path in sorted(set(actual).intersection(registered)):
        stem = Path(path).stem
        if HISTORICAL_TEST_NAME_PATTERN.search(stem):
            failures.append(
                Failure(
                    "References",
                    path,
                    "week- or event-specific Python test files are prohibited; use a stable synthetic contract or one-time acceptance evidence",
                )
            )
        source = read_bytes(root, path).decode("utf-8")
        live_roots = _repository_live_roots(source)
        if live_roots.intersection({"data", "reports"}):
            failures.append(
                Failure(
                    "References",
                    path,
                    "tests must not read repository-live data or reports as an oracle",
                )
            )
        if "stats" in live_roots:
            oracle = registered[path][0]
            if oracle not in {
                "current-candidate-invariant",
                "protected-compatibility",
                "schema",
            }:
                failures.append(
                    Failure(
                        "References",
                        path,
                        "repository-live statistics require a value-independent candidate, protected-compatibility, or Schema oracle",
                    )
                )

    return len(actual) + len(registered), failures


def validate_references(
    root: Path,
    names: list[str],
    enabled_groups: frozenset[str] = REFERENCE_GROUPS,
) -> tuple[int, list[Failure], dict[str, int]]:
    failures: list[Failure] = []
    tracked = set(names)
    breakdown = {
        "authoritative-document paths": 0,
        "requirement includes": 0,
        "front-end templates": 0,
        "Phase 8 production resources": 0,
        "required Standard files": 0,
        "frozen Pickup week entries": 0,
        "classifier-derived artifact closure": 0,
        "test inventory contracts": 0,
    }
    if "governance" in enabled_groups:
        for value in REQUIRED_GOVERNANCE_DOCUMENTS:
            breakdown["authoritative-document paths"] += 1
            reference_check(
                failures,
                value,
                None
                if tracked_regular(root, tracked, value)
                else "missing tracked governance document",
            )
    if "requirements" in enabled_groups:
        for manifest in REQUIREMENT_MANIFESTS:
            if manifest not in tracked:
                reference_check(failures, manifest, "missing tracked requirement manifest")
                continue
            for line_number, raw in enumerate(
                read_bytes(root, manifest).decode("utf-8").splitlines(), 1
            ):
                text = raw.strip()
                target = None
                if text.startswith("-r="):
                    target = text[3:]
                elif text.startswith("-r") and len(text) > 2 and not text[2].isspace():
                    target = text[2:]
                elif text.startswith("-r "):
                    target = text.split(None, 1)[1].strip()
                elif text.startswith("--requirement="):
                    target = text.split("=", 1)[1].strip()
                elif text.startswith("--requirement "):
                    target = text.split(None, 1)[1].strip()
                if target is None:
                    continue
                breakdown["requirement includes"] += 1
                message = None
                if (
                    not target
                    or "\\" in target
                    or Path(target).is_absolute()
                    or ".." in Path(target).parts
                ):
                    message = f"invalid requirement include {target!r}"
                else:
                    resolved = (Path(manifest).parent / target).as_posix()
                    if not tracked_regular(root, tracked, resolved):
                        message = f"missing tracked requirement include {target}"
                reference_check(failures, f"{manifest}:{line_number}", message)
    if "frontend-templates" in enabled_groups:
        templates = (
            "stats/${currentFormat}/mtgo/meta.json",
            "stats/${currentFormat}/mtgo/range_${currentRange}w.json",
            "stats/${currentFormat}/mtgo/decks_${currentRange}w.json",
            "stats/${currentFormat}/mtgo/matchup_${mxRange}w.json",
        )
        if "index.html" not in tracked:
            reference_check(failures, "index.html", "missing tracked index.html")
        else:
            missing_assets = [
                path
                for path in LEGACY_FRONTEND_FILES[1:]
                if not safe_path(root, path).is_file()
            ]
            for path in missing_assets:
                reference_check(failures, path, "missing front-end asset")
            frontend_source = "\n".join(
                read_bytes(root, path).decode("utf-8")
                for path in LEGACY_FRONTEND_FILES
                if safe_path(root, path).is_file()
            )
            for template in templates:
                breakdown["front-end templates"] += 1
                reference_check(
                    failures,
                    "front-end assets",
                    f"missing template {template}"
                    if template not in frontend_source
                    else None,
                )
    if "required-standard-files" in enabled_groups:
        for path in REQUIRED_STANDARD_FILES:
            breakdown["required Standard files"] += 1
            reference_check(
                failures,
                path,
                None
                if tracked_regular(root, tracked, path, ".json")
                else "missing tracked regular JSON file",
            )
    if "pickup-indexes" in enabled_groups:
        for format_id in ("standard", "modern"):
            pickup = f"stats/{format_id}/mtgo/pickup/index.json"
            if not tracked_regular(root, tracked, pickup, ".json"):
                reference_check(failures, pickup, "missing frozen Pickup index")
                continue
            try:
                data = json.loads(read_bytes(root, pickup).decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                reference_check(
                    failures,
                    pickup,
                    f"invalid frozen Pickup index: {type(exc).__name__}: {exc}",
                )
                continue
            weeks = data.get("weeks") if isinstance(data, dict) else None
            if not isinstance(weeks, list):
                reference_check(failures, pickup, "weeks must be a list")
                continue
            for index, entry in enumerate(weeks):
                breakdown["frozen Pickup week entries"] += 1
                value = entry.get("file") if isinstance(entry, dict) else None
                valid = (
                    isinstance(value, str)
                    and bool(value)
                    and value.endswith(".json")
                    and Path(value).name == value
                    and value not in (".", "..")
                    and not Path(value).is_absolute()
                    and "/" not in value
                    and "\\" not in value
                    and tracked_regular(
                        root,
                        tracked,
                        f"stats/{format_id}/mtgo/pickup/{value}",
                        ".json",
                    )
                )
                reference_check(
                    failures,
                    f"{pickup}:weeks[{index}]",
                    None if valid else f"invalid frozen Pickup week file {value!r}",
                )
    if "classifier-closure" in enabled_groups:
        try:
            from mtgmeta.classifier_closure import inspect_repository

            closure = inspect_repository(root)
            for format_report in closure["formats"]:
                for family in format_report["families"].values():
                    breakdown["classifier-derived artifact closure"] += 1
                    if family["state"] == "CURRENT":
                        continue
                    path = (
                        family["artifacts"][0]
                        if family["artifacts"]
                        else "stats/catalog.json"
                    )
                    detail = "; ".join(family["issues"][:3]) or family["state"]
                    reference_check(
                        failures,
                        path,
                        f"classifier closure {format_report['format']}/{family['name']} is {family['state']}: {detail}",
                    )
                if not format_report["families"]:
                    breakdown["classifier-derived artifact closure"] += 1
                    reference_check(
                        failures,
                        "stats/catalog.json",
                        f"classifier closure {format_report['format']} is {format_report['state']}: "
                        + "; ".join(format_report["issues"][:3]),
                    )
        except (ImportError, RuntimeError, OSError, ValueError) as exc:
            breakdown["classifier-derived artifact closure"] += 1
            reference_check(
                failures,
                "stats/catalog.json",
                f"classifier closure inspection failed: {type(exc).__name__}: {exc}",
            )
    if "test-inventory" in enabled_groups:
        inventory_checked, inventory_failures = validate_test_inventory(root, names)
        breakdown["test inventory contracts"] = inventory_checked
        failures.extend(inventory_failures)
    if "phase8-entries" in enabled_groups:
        phase8_checked, phase8_failures = validate_phase8_frontend_references(
            root, names
        )
        breakdown["Phase 8 production resources"] = phase8_checked
        failures.extend(phase8_failures)
    checked = sum(breakdown.values())
    return checked, failures, breakdown


def validate_hygiene(names: list[str]) -> tuple[int, list[Failure]]:
    failures = []
    for name in names:
        path = Path(name)
        lowered_parts = {part.lower() for part in path.parts}
        lowered_name = path.name.lower()
        reason = None
        if FORBIDDEN_TRACKED_PARTS.intersection(lowered_parts):
            reason = "tracked runtime or dependency directory"
        elif lowered_name in FORBIDDEN_TRACKED_NAMES:
            reason = "tracked operating-system artifact"
        elif lowered_name.endswith(FORBIDDEN_TRACKED_SUFFIXES):
            reason = "tracked cache, log, backup, or temporary file"
        if reason:
            failures.append(Failure("Hygiene", name, reason))
    return len(names), failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate changed repository scope or the full repository read-only."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--changed-from",
        metavar="REF",
        help="validate paths changed from REF and directly coupled contracts",
    )
    mode.add_argument(
        "--full",
        action="store_true",
        help="validate the complete repository and all global contracts",
    )
    mode.add_argument(
        "--full-candidate",
        action="store_true",
        help="validate a staged complete Melee candidate while deferring only its Tabletop README publication row",
    )
    args = parser.parse_args()
    try:
        root = repository_root()
        tracked = tracked_files(root)
        changed: list[str] = []
        if args.full or args.full_candidate:
            validation_mode = "full-candidate" if args.full_candidate else "full"
            candidates = sorted(
                set(tracked) | {"validate_repository.py"} | set(MAINTAINED_JAVASCRIPT)
            )
            javascript = MAINTAINED_JAVASCRIPT
            reference_groups = REFERENCE_GROUPS
            validate_facts = True
            validate_catalog = True
            hygiene_names = tracked
        else:
            validation_mode = f"changed-from {args.changed_from}"
            changed = changed_files(root, args.changed_from)
            plan = changed_validation_plan(changed, tracked)
            candidates = list(plan.candidates)
            javascript = plan.javascript
            reference_groups = plan.reference_groups
            validate_facts = plan.public_product_facts
            validate_catalog = plan.catalog_consistency
            hygiene_names = list(plan.hygiene)
        counts, failures, parsed = validate_files(root, candidates, javascript)
        reference_count, reference_failures, breakdown = validate_references(
            root, tracked, reference_groups
        )
        failures.extend(reference_failures)
        fact_count = 0
        fact_failures: list[Failure] = []
        if validate_facts:
            fact_count, fact_failures = validate_public_product_facts(
                root,
                tracked,
                defer_tabletop_readme=args.full_candidate,
            )
        catalog_count = 0
        catalog_failures: list[Failure] = []
        if validate_catalog:
            catalog_count, catalog_failures = validate_catalog_consistency(
                root,
                tracked,
            )
        reference_count += fact_count + catalog_count
        failures.extend(fact_failures)
        failures.extend(catalog_failures)
        all_reference_failures = (
            reference_failures + fact_failures + catalog_failures
        )
        hygiene_count, hygiene_failures = validate_hygiene(hygiene_names)
        failures.extend(hygiene_failures)
        failures.sort(key=lambda f: (CATEGORY_ORDER[f.category], f.path, f.line or 0, f.column or 0, f.message))
        failed_paths = {category: {f.path for f in failures if f.category == category} for category in CATEGORY_ORDER}
        print("Repository validation")
        print(f"Repository root: {root}")
        print(f"Mode: {validation_mode}")
        if changed:
            print(f"Changed paths: {len(changed)}")
            print(
                "Coupled reference groups: "
                + (", ".join(sorted(reference_groups)) or "none")
            )
        for category in ("Python", "JavaScript", "JSON", "YAML"):
            checked = counts[category]
            failed = len(failed_paths[category])
            print(f"{category}: checked={checked} passed={checked - failed} failed={failed}")
        failed_reference_paths = {failure.path for failure in all_reference_failures}
        print(f"References: checked={reference_count} passed={reference_count - len(failed_reference_paths)} failed={len(failed_reference_paths)}")
        print(f"Hygiene: checked={hygiene_count} passed={hygiene_count - len(hygiene_failures)} failed={len(hygiene_failures)}")
        for item in failures:
            location = f" line {item.line}, column {item.column}" if item.line is not None else ""
            print(f"{item.category}: {item.path}{location}: {item.message}")
        print("RESULT: PASS" if not failures else "RESULT: FAIL")
        return 0 if not failures else 1
    except InfrastructureError as exc:
        print(f"Repository validation infrastructure error: {exc}")
        print("RESULT: ERROR")
        return 2
    except Exception as exc:
        print(f"Repository validation infrastructure error: {type(exc).__name__}: {exc}")
        print("RESULT: ERROR")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
