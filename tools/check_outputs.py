"""Check changed generated outputs, without executing unrelated mechanism suites."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.delivery.gitfacts import changed_files
from validate_schemas import validate_manifest
from validate_output_invariants import validate_repository_output


def check(root: Path, paths: list[str]) -> dict:
    selected = {path for path in paths if path.endswith(".json") and (root / path).is_file()
                and (path.startswith(("stats/", "reports/")) or
                     (path.startswith("data/") and "/melee/" in path))}
    failures = []
    checked = 0
    for manifest in ("schemas/manifest.json", "schemas/melee-data-manifest.json"):
        count, errors = validate_manifest(root, root / manifest, selected)
        checked += count
        failures.extend(f"{error.path} {error.location}: {error.message}" for error in errors)
    formats = {parts[1] for path in selected
               if len(parts := path.split("/")) >= 4 and parts[0] == "stats" and parts[2] == "mtgo"}
    if formats:
        failures.extend(validate_repository_output(root, formats=sorted(formats)))
    return {"state": "failed" if failures else "passed" if checked else "not_required",
            "schema_outputs": checked, "mtgo_formats": sorted(formats), "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--changed-from", required=True)
    args = parser.parse_args()
    try:
        result = check(args.root, changed_files(args.root, args.changed_from))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result["state"] == "failed" else 0
    except (OSError, ValueError, RuntimeError) as error:
        print(json.dumps({"state": "execution_failed", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
