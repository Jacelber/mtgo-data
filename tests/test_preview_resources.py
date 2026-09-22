"""Direct-entry selection and evidence-based legacy projection, without browser gates."""
from copy import deepcopy
from pathlib import Path

import pytest

from mtgmeta.mtgo import review_submission as review
from mtgmeta.mtgo.preview_resources import select, SELECTION


def write(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def entry(root):
    write(root, "index.html", '<script src="assets/js/phase8/app.js"></script>'
        '<script src="assets/js/phase8/archetype-visuals.js"></script>'
        '<link rel="stylesheet" href="assets/css/phase8-base.css">')
    for path in ("assets/js/phase8/app.js", "assets/js/phase8/archetype-visuals.js",
                 "assets/js/phase8/app-tabletop.js", "assets/js/phase8/tabletop-controller.js", "assets/css/phase8-base.css"):
        write(root, path, "synthetic")


def packet(root, *, legacy=False):
    resources = {name: review.hashlib_sha(root / name) for name in select(root)}
    if legacy:
        for name in ("app-tabletop.js", "tabletop-controller.js"):
            path = f"assets/js/phase8/{name}"
            resources[path] = review.hashlib_sha(root / path)
    return review.make_packet("preview", "standard", "2026-W38", {"final_page": {
        "product_digest": "product", "colors": {"test": ["u"]}, "selected_local_images": {"card.jpg": "image"},
        "renderer_resources": resources}}, bindings={"bundle_digest": "bundle", "renderer_resources": resources,
        **({} if legacy else {"renderer_selection": SELECTION})})


def resign(value):
    value["digest"] = review.digest({key: item for key, item in value.items() if key != "digest"})


def test_actual_mtgo_entry_has_no_tabletop_only_renderer():
    paths = select(Path(__file__).resolve().parents[1])
    assert "assets/js/phase8/app-mtgo.js" in paths
    assert "assets/js/phase8/app-tabletop.js" not in paths
    assert "assets/js/phase8/tabletop-controller.js" not in paths
    assert "assets/js/phase8/archetype-visuals.js" not in paths


@pytest.mark.parametrize("reference", ['<script src="https://example.test/code.js"></script>',
    '<script src="../outside.js"></script>', '<script src="%2e%2e/outside.js"></script>',
    '<script src="missing.js"></script>', '<script src="app.js?v=1"></script>',
    '<script src=""></script>', '<link rel="stylesheet">', '<base href="https://example.test/">',
    '<script src="a.js" src="b.js"></script>'])
def test_unsupported_references_fail_instead_of_disappearing(tmp_path, reference):
    entry(tmp_path)
    with (tmp_path / "index.html").open("a", encoding="utf-8") as handle:
        handle.write(reference)
    with pytest.raises(ValueError): select(tmp_path)


@pytest.mark.parametrize("path, expected", [("assets/js/phase8/app-tabletop.js", "current"),
    ("assets/js/phase8/tabletop-controller.js", "current"), ("assets/js/phase8/app.js", "changed"),
    ("assets/css/phase8-base.css", "changed"), ("index.html", "changed")])
def test_loaded_files_and_unloaded_files_have_different_effects(tmp_path, path, expected):
    entry(tmp_path)
    before = packet(tmp_path)
    with (tmp_path / path).open("a", encoding="utf-8") as handle:
        handle.write("<!-- changed -->")
    assert review.packet_validity(before, packet(tmp_path))["state"] == expected


@pytest.mark.parametrize("change, expected", [("extras", "equivalent"), ("entry", "changed"),
    ("script", "changed"), ("missing", "evidence_required"), ("inconsistent", "evidence_required"),
    ("colors", "changed"), ("image", "changed"), ("product", "changed"), ("binding", "changed")])
def test_legacy_projection_needs_unchanged_entry_and_all_material(tmp_path, change, expected):
    entry(tmp_path)
    old = packet(tmp_path, legacy=True)
    current = packet(tmp_path)
    if change == "extras":
        write(tmp_path, "assets/js/phase8/app-tabletop.js", "unrelated change")
        current = packet(tmp_path)
    elif change in {"entry", "script", "missing", "inconsistent"}:
        name = "index.html" if change == "entry" else "assets/js/phase8/app.js"
        if change in {"missing", "inconsistent"}:
            old["bindings"]["renderer_resources"].pop(name)
            if change == "missing": old["dimensions"]["final_page"]["renderer_resources"].pop(name)
            resign(old)
        else:
            with (tmp_path / name).open("a", encoding="utf-8") as handle: handle.write("<!-- change -->")
            current = packet(tmp_path)
    else:
        if change == "colors": current["dimensions"]["final_page"]["colors"]["test"] = ["r"]
        if change == "image": current["dimensions"]["final_page"]["selected_local_images"]["card.jpg"] = "other"
        if change == "product": current["dimensions"]["final_page"]["product_digest"] = "other"
        if change == "binding": current["bindings"]["bundle_digest"] = "other"
        resign(current)
    preserved = deepcopy(old)
    assert review.packet_validity(old, current)["state"] == expected
    assert old == preserved


def test_legacy_decision_reuse_keeps_original_snapshot_and_date(tmp_path):
    entry(tmp_path)
    old = packet(tmp_path, legacy=True)
    decisions = review.record_decision(old, None, ["final_page"], evidence="synthetic Owner decision",
        accepted_on="2026-09-21", entrypoint="https://example.invalid/preview")
    envelope = {"submission": old, "decisions": decisions}
    preserved = deepcopy(envelope)
    current = packet(tmp_path)
    reused = review.reuse_decisions(current, envelope)
    review.require_accepted(current, reused)
    review.require_accepted(old, decisions, current=current)
    assert reused["decisions"] == decisions["decisions"]
    assert reused["equivalent_submission"] == old
    assert envelope == preserved
    current["week"] = "2026-W39"
    resign(current)
    assert review.packet_validity(old, current)["state"] == "changed"


@pytest.mark.parametrize("failure", ["unknown_method", "inconsistent_current_map", "missing_entry"])
def test_unproven_selection_cannot_bypass_completion_comparison(tmp_path, failure):
    entry(tmp_path)
    prior = packet(tmp_path)
    current = packet(tmp_path)
    if failure == "unknown_method": current["bindings"]["renderer_selection"]["method"] = "unknown"
    if failure == "inconsistent_current_map": current["bindings"]["renderer_resources"].pop("assets/js/phase8/app.js")
    if failure == "missing_entry":
        for resources in (current["bindings"]["renderer_resources"], current["dimensions"]["final_page"]["renderer_resources"]):
            resources.pop("index.html")
    resign(current)
    assert review.preview_validity(prior, current, dimensions_only=True)["state"] == "evidence_required"
