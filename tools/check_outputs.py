"""Check changed generated outputs, without executing unrelated mechanism suites."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.delivery.gitfacts import changed_files
from validate_schemas import validate_manifest, schema_timeout_seconds
from validate_output_invariants import validate_repository_output


def check(root: Path, paths: list[str], *, timeout_seconds: float | None = None) -> dict:
    resource = "src/mtgmeta/data/classifier_card_facts.json"
    selected = {path for path in paths if path.endswith(".json") and (root / path).is_file()
                and (path == resource or path.startswith(("stats/", "reports/")) or
                     (path.startswith("data/") and "/melee/" in path))}
    deadline = monotonic() + schema_timeout_seconds(timeout_seconds)
    failures = []
    checked = 0
    manifests = ["schemas/manifest.json", "schemas/melee-data-manifest.json"]
    if resource in selected:
        manifests.append("schemas/classifier-data-manifest.json")
    mapped: set[str] = set()
    for manifest in manifests:
        spec = json.loads((root / manifest).read_text(encoding="utf-8"))
        for mapping in spec["mappings"]:
            mapped.update(path.relative_to(root).as_posix() for path in root.glob(mapping["pattern"])
                          if path.relative_to(root).as_posix() in selected)
        count, errors = validate_manifest(root, root / manifest, selected, timeout_seconds=max(0.001, deadline - monotonic()))
        checked += count
        failures.extend(f"{error.path} {error.location}: {error.message}" for error in errors)
    failures.extend(f"{path}: required output has no schema mapping" for path in sorted(selected - mapped))
    formats = {parts[1] for path in selected
               if len(parts := path.split("/")) >= 4 and parts[0] == "stats" and parts[2] == "mtgo"}
    if formats:
        failures.extend(validate_repository_output(root, formats=sorted(formats)))
    return {"state": "failed" if failures else "passed" if checked else "not_required",
            "schema_outputs": checked, "mtgo_formats": sorted(formats), "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema-timeout-seconds", type=float)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--changed-from", required=True)
    args = parser.parse_args()
    try:
        result = check(args.root, changed_files(args.root, args.changed_from), timeout_seconds=args.schema_timeout_seconds)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result["state"] == "failed" else 0
    except (OSError, ValueError, RuntimeError) as error:
        print(json.dumps({"state": "execution_failed", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
