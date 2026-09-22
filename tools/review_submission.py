"""Prepare scoped private review material, record actual decisions and resume."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from mtgmeta.mtgo import review_submission as review
from mtgmeta.mtgo.copy_links import validate_card_tokens
from mtgmeta.mtgo.publication import require_private_output


def read(path):
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write(root, path, value):
    require_private_output(root, path.resolve())
    if path.exists():
        raise ValueError("Use a new output file; retain the earlier handoff")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    classification = commands.add_parser("classification", help="Prepare all explicitly requested group members")
    classification.add_argument("--materials", type=Path, required=True)
    classification.add_argument("--requests", type=Path, required=True)
    content = commands.add_parser("content", help="Prepare proposed bilingual content, names and visuals")
    content.add_argument("--input", type=Path, required=True)
    content.add_argument("--localization", type=Path, required=True,
                         help="Canonical bilingual card lookup used to reject mismatched card tokens")
    workbook = commands.add_parser("workbook", help="Extract workbook content for the same review path")
    workbook.add_argument("--input", type=Path, required=True)
    preview = commands.add_parser("preview", help="Bind the actual generated Landing and its dependencies")
    preview.add_argument("--format", required=True)
    preview.add_argument("--entrypoint", required=True, help="Actual final page submitted for Owner review")
    for command in (classification, content, workbook, preview):
        command.add_argument("--output", type=Path, required=True)
        command.add_argument("--decisions", type=Path, help="Reuse applicable decisions; changed dimensions remain pending")
    decide = commands.add_parser("record", help="Record only the scopes actually accepted in conversation")
    decide.add_argument("--submission", type=Path, required=True)
    decide.add_argument("--previous", type=Path)
    decide.add_argument("--dimension", action="append", required=True)
    decide.add_argument("--evidence", required=True)
    decide.add_argument("--accepted-on", required=True)
    decide.add_argument("--entrypoint", required=True)
    decide.add_argument("--output", type=Path, required=True)
    completion = commands.add_parser("completion", help="Verify the accepted preview inside the actually confirmed package")
    completion.add_argument("--acceptance", type=Path, required=True)
    completion.add_argument("--candidate", type=Path, required=True)
    completion.add_argument("--publication-state", type=Path, required=True)
    completion.add_argument("--output", type=Path, required=True)
    supplement = commands.add_parser("supplement-completion", help="Export one verified append-only late-event completion fact")
    supplement.add_argument("--format", required=True)
    supplement.add_argument("--week", required=True)
    supplement.add_argument("--candidate", type=Path, required=True)
    supplement.add_argument("--publication-state", type=Path, required=True)
    supplement.add_argument("--completed-on", required=True)
    supplement.add_argument("--evidence", required=True)
    supplement.add_argument("--preview-acceptance", type=Path)
    supplement.add_argument("--output", type=Path, required=True)
    resume = commands.add_parser("resume", help="Derive scoped state without assuming publication")
    resume.add_argument("--format", required=True)
    resume.add_argument("--week", required=True)
    resume.add_argument("--acceptance", type=Path)
    resume.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "supplement-completion":
        from mtgmeta.mtgo import supplement_completion
        registry = read(root / "configs/mtgo_weekly_review_completions.yaml")
        records = [item for item in registry["records"] if item["week"] == args.week
                   and args.format in item.get("formats", {})]
        if len(records) != 1:
            raise ValueError("Supplement requires exactly one original format/week completion")
        result = supplement_completion.build(root, records[0], args.format, candidate=args.candidate,
            state=read(args.publication_state), completed_on=args.completed_on, evidence=args.evidence,
            preview_acceptance=read(args.preview_acceptance) if args.preview_acceptance else None)
        write(root, args.output, result)
        return
    if args.command == "completion":
        import tempfile
        from tools.delivery import packages
        envelope = read(args.acceptance)
        packet = envelope["submission"]
        manifest = read(args.candidate / "manifest.json")
        state = read(args.publication_state)
        current = state.get("current") or {}
        if (current.get("health") != "passed" or current.get("package") != manifest["id"]
                or state.get("pending") or not current.get("operation")):
            raise ValueError("Publication has not confirmed this exact package")
        require_private_output(root, args.output.resolve())
        # Read only data from the verified archive; never execute its old tools.
        with tempfile.TemporaryDirectory(prefix="review-publication-") as directory:
            extracted = Path(directory) / "site"
            packages.extract(args.candidate / "product.tar.gz", manifest, extracted, target="Jacelber/mtgo-data")
            actual = review.preview_packet(extracted, packet["format"])
            review.require_accepted(packet, envelope["decisions"], current=actual)
        envelope["publication"] = {**current, "preview_digest": packet["digest"]}
        write(root, args.output, envelope)
        return
    if args.command == "resume":
        result = review.resume_summary(root, args.format, args.week,
                                       envelope=read(args.acceptance) if args.acceptance else None)
        if args.output:
            write(root, args.output, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.command == "record":
        packet = read(args.submission)
        receipt = review.record_decision(packet, read(args.previous)["decisions"] if args.previous else None,
                                         args.dimension, evidence=args.evidence,
                                         accepted_on=args.accepted_on, entrypoint=args.entrypoint)
        write(root, args.output, {"submission": packet, "decisions": receipt})
        return
    require_private_output(root, args.output.resolve() / "index.html")
    if args.command == "workbook":
        from mtgmeta.mtgo import landing_editorial as editorial
        result = editorial._validated_workbook_subject(root, args.input)
        for (format_id, week), source in result["reviews"].items():
            write(root, args.output / f"{format_id}-{week}.json", source)
        return
    if args.command == "classification":
        packet = review.classification_packet(read(args.materials), read(args.requests))
    elif args.command == "content":
        source = read(args.input)
        validate_card_tokens(source["review"], read(args.localization))
        packet = review.content_packet(root, source)
    else:
        packet = review.preview_packet(root, args.format)
    receipt = review.reuse_decisions(packet, read(args.decisions)) if args.decisions else None
    review.write_materials(packet, args.output, receipt, preview_entrypoint=getattr(args, "entrypoint", None))
    print(json.dumps({"material": str(args.output / "index.html"),
                      **review.decision_state(packet, receipt)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
