"""Offline acceptance experiment for PR 459; NOT a production maintenance run.

Uses retained site resources and synthetic decisions/publication state only.
Writes an isolated copy plus a compact, shareable evidence report. No network.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from tools import weekly_maintenance as flow
from tools import review_submission as review_cli
from tools.delivery import packages
from mtgmeta.mtgo import review_submission as review, landing_editorial as editorial


def run(base, output):
    started = perf_counter()
    if output.exists():
        raise ValueError("Use a new isolated experiment directory")
    output.mkdir(parents=True)
    root = output / "repository"
    protected = [ROOT / "configs/mtgo_weekly_review_completions.yaml",
                 *(ROOT / "my_archetypes").glob("*.yaml"),
                 *(ROOT / "stats").glob("*/mtgo/landing/review/2026-W39.yaml")]
    before = {str(p.relative_to(ROOT)): review.hashlib_sha(p) for p in protected}
    for directory in ("configs", "data", "my_archetypes", "stats", "reports", "schemas", "assets"):
        shutil.copytree(ROOT / directory, root / directory, copy_function=flow.link_or_copy)
    cumulative = base
    accepted = {}
    report = {"kind": "isolated-contract-experiment", "synthetic_decisions": True,
              "synthetic_publication_state": True, "remote_operations": 0, "formats": {}}
    for fmt in ("standard", "modern", "pauper", "pioneer"):
        out = output / fmt
        facts_dir = out / "facts"
        facts_dir.mkdir(parents=True)
        facts_result = flow.prepare_facts(root, fmt, "2026-W39", facts_dir)
        source = flow.read(facts_dir / "source.json")
        source["review"] = flow.read(root / f"stats/{fmt}/mtgo/landing/review/2026-W39.yaml")["review"]
        preview = out / "preview"
        preview.mkdir()
        flow.prepare(root, source, cumulative, preview, flow.read(facts_dir / "facts.json"))
        packet = flow.read(preview / "preview.json")
        receipt = review.record_decision(packet, None, ["final_page"],
            evidence="SYNTHETIC OFFLINE CONTRACT TEST, not an Owner decision",
            accepted_on="2026-10-01", entrypoint="https://example.invalid/isolated-contract")
        envelope = {"submission": packet, "decisions": receipt}
        flow.write(out / "synthetic-acceptance.json", envelope)
        final_source = flow.finalize_source(root, flow.read(preview / "source.json"), preview / "site",
                                             envelope, flow.read(preview / "facts.json"))
        flow.write(out / "synthetic-source.json", final_source)
        adoption = flow.adopt_content(root, final_source, preview)
        loaded = editorial.load_review_document(Path(adoption["source"]), root / editorial.DEFAULT_REVIEW_SCHEMA)
        actual = review.content_packet(root, loaded)
        review.require_accepted(loaded["acceptance"]["submission"], loaded["acceptance"]["decisions"], current=actual)
        assert actual["bindings"]["material_digest"] == final_source["acceptance"]["submission"]["bindings"]["material_digest"]
        if fmt == "pauper":
            normal = editorial.build_admitted_content_facts(root, fmt, "2026-W39")
            technical = deepcopy(normal)
            technical["page"]["classifier"]["digest"] = "f" * 64
            technical["page"]["review_binding"]["machine_fact_digest"] = "e" * 64
            with patch.object(editorial, "build_admitted_content_facts", return_value=technical):
                current = review.content_packet(root, loaded)
                assert review.packet_validity(loaded["acceptance"]["submission"], current)["state"] == "equivalent"
            technical["review_facts"]["observations"].append({"synthetic_changed_fact": True})
            with patch.object(editorial, "build_admitted_content_facts", return_value=technical):
                try:
                    review.content_packet(root, loaded)
                except ValueError:
                    report["real_material_change_rejected"] = True
                else:
                    raise AssertionError("Changed material was accepted")
            report["technical_change_reused_by_existing_reader"] = True
        accepted[fmt] = envelope
        cumulative = preview / "site"
        report["formats"][fmt] = {"pending_event_ids_excluded": facts_result["pending_event_ids"],
            "content_material_digest": actual["bindings"]["material_digest"], "importer_schema": loaded["schema_version"],
            "preview_digest": packet["digest"]}
    for fmt, envelope in accepted.items():
        final = review.preview_packet(cumulative, fmt)
        receipt = review.reuse_decisions(final, envelope)
        review.require_accepted(final, receipt)
        report["formats"][fmt]["cumulative_preview_reused"] = True
        # All data products, including the retained Landing week dependencies,
        # must remain byte-identical; only the four editorial paths may differ.
    unchanged = 0
    for path in (base / "stats").rglob("*.json"):
        relative = path.relative_to(base)
        if "/landing/current.json" in relative.as_posix() or "/landing/features/" in relative.as_posix():
            continue
        assert path.read_bytes() == (cumulative / relative).read_bytes(), str(relative)
        unchanged += 1
    report["unchanged_data_files"] = unchanged
    package_dir = output / "synthetic-package"
    manifest = packages.prepare(cumulative, package_dir, target="Jacelber/mtgo-data", source="synthetic-offline-contract")
    state = output / "synthetic-state.json"
    flow.write(state, {"pending": None, "current": {"health": "passed", "operation": "SYNTHETIC-NOT-PUBLISHED", "package": manifest["id"]}})
    for fmt in accepted:
        completed = output / fmt / "synthetic-completion.json"
        args = ["review_submission", "--root", str(cumulative), "completion", "--acceptance",
            str(output / fmt / "synthetic-acceptance.json"), "--candidate", str(package_dir),
            "--publication-state", str(state), "--output", str(completed)]
        with patch.object(sys, "argv", args):
            review_cli.main()
        review.validate_completion(cumulative, fmt, "2026-W39", {"preview_acceptance": flow.read(completed)})
        report["formats"][fmt]["existing_completion_contract_passed"] = True
    assert all(review.hashlib_sha(ROOT / path) == sha for path, sha in before.items())
    report.update(protected_originals_unchanged=True, isolated_root_has_git=False,
                  seconds=round(perf_counter() - started, 4))
    flow.write(output / "evidence.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-site", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with patch("urllib.request.urlopen", side_effect=AssertionError("Network prohibited in this experiment")):
        print(json.dumps(run(args.base_site.resolve(), args.output.resolve()), indent=2))
