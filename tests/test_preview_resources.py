"""Direct-entry selection and evidence-based legacy projection, without browser gates."""
from copy import deepcopy
from hashlib import sha256
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


def test_content_version_reference_binds_actual_renderer_bytes(tmp_path):
    entry(tmp_path)
    path = "assets/js/phase8/app.js"
    version = sha256((tmp_path / path).read_bytes()).hexdigest()[:12]
    html = (tmp_path / "index.html").read_text()
    write(tmp_path, "index.html", html.replace(path, f"{path}?v={version}"))
    assert path in select(tmp_path)
    write(tmp_path, path, "different renderer")
    with pytest.raises(ValueError, match="renderer version"):
        select(tmp_path)


@pytest.mark.parametrize("query", ["v=000000000000", "v=1", "v=synthetic", "v=000000000000&other=1"])
def test_renderer_query_must_be_the_exact_content_version(tmp_path, query):
    entry(tmp_path)
    path = "assets/js/phase8/app.js"
    html = (tmp_path / "index.html").read_text()
    write(tmp_path, "index.html", html.replace(path, f"{path}?{query}"))
    with pytest.raises(ValueError, match="renderer version"):
        select(tmp_path)


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


@pytest.mark.parametrize("change", [None, "no_proof", "hash", "scope", "product", "image", "binding", "entry", "evidence"])
def test_renderer_repair_preserves_original_acceptance_and_all_other_material(tmp_path, change):
    entry(tmp_path)
    old = packet(tmp_path)
    decisions = review.record_decision(old, None, ["final_page"], evidence="synthetic Owner acceptance",
        accepted_on="2026-09-21", entrypoint="https://example.invalid/preview")
    original = deepcopy(decisions)
    write(tmp_path, "assets/js/phase8/app.js", "fixed renderer")
    current = packet(tmp_path)
    proof = {"method": "same-display-renderer-repair-v1", "format": "standard", "week": "2026-W38",
        "product_digest": "product", "before": deepcopy(old["bindings"]["renderer_resources"]),
        "after": deepcopy(current["bindings"]["renderer_resources"]),
        "evidence": "synthetic before/after display comparison", "verification_sha256": "a" * 64}
    if change == "hash": proof["after"]["assets/js/phase8/app.js"] = "b" * 64
    if change == "scope": proof["week"] = "2026-W39"
    if change == "evidence": proof["verification_sha256"] = ""
    if change == "product": current["dimensions"]["final_page"]["product_digest"] = "changed"
    if change == "image": current["dimensions"]["final_page"]["selected_local_images"]["card.jpg"] = "changed"
    if change == "binding": current["bindings"]["bundle_digest"] = "changed"
    if change == "entry":
        for mapping in (current["bindings"]["renderer_resources"], current["dimensions"]["final_page"]["renderer_resources"], proof["after"]):
            mapping["index.html"] = "b" * 64
    resign(current)
    if change != "no_proof": decisions["renderer_repair"] = proof
    assert review.packet_validity(old, current)["state"] == "changed"
    if change is None:
        review.require_accepted(old, decisions, current=current)
        assert review.preview_validity(old, current, dimensions_only=True, renderer_repair=proof)["state"] == "equivalent"
    else:
        with pytest.raises(ValueError): review.require_accepted(old, decisions, current=current)
    assert decisions["decisions"] == original["decisions"]


@pytest.mark.parametrize("change", [None, "line_endings", "wrong_version", "markup", "unbound_html", "no_entry_proof"])
def test_renderer_repair_accepts_only_bound_cache_version_entry_changes(tmp_path, change):
    entry(tmp_path)
    before_html = (tmp_path / "index.html").read_text()
    old = packet(tmp_path)
    decisions = review.record_decision(old, None, ["final_page"], evidence="synthetic Owner acceptance",
        accepted_on="2026-09-21", entrypoint="https://example.invalid/preview")
    write(tmp_path, "assets/js/phase8/app.js", "fixed renderer")
    version = sha256(b"fixed renderer").hexdigest()[:12]
    after_html = before_html.replace("app.js\"", f"app.js?v={version}\"")
    if change == "line_endings":
        before_html += "\r\n"
        (tmp_path / "index.html").write_bytes(before_html.encode("utf-8"))
        old = packet(tmp_path)
        decisions = review.record_decision(old, None, ["final_page"], evidence="synthetic Owner acceptance",
            accepted_on="2026-09-21", entrypoint="https://example.invalid/preview")
        after_html += "\n"
    (tmp_path / "index.html").write_bytes(after_html.encode("utf-8"))
    current = packet(tmp_path)
    if change == "wrong_version":
        after_html = after_html.replace(version, "0" * 12)
    if change == "markup":
        after_html += "<p>Changed user content</p>"
    if change in {"wrong_version", "markup"}:
        for mapping in (current["bindings"]["renderer_resources"], current["dimensions"]["final_page"]["renderer_resources"]):
            mapping["index.html"] = sha256(after_html.encode()).hexdigest()
        resign(current)
    proof = {"method": "same-display-renderer-repair-v1", "format": "standard", "week": "2026-W38",
        "product_digest": "product", "before": deepcopy(old["bindings"]["renderer_resources"]),
        "after": deepcopy(current["bindings"]["renderer_resources"]),
        "evidence": "synthetic unchanged display with cache version update", "verification_sha256": "a" * 64,
        "entry_version_repair": {"before_html": before_html, "after_html": after_html}}
    if change == "unbound_html": proof["entry_version_repair"]["before_html"] += " "
    if change == "no_entry_proof": proof.pop("entry_version_repair")
    decisions["renderer_repair"] = proof
    if change in {None, "line_endings"}:
        review.require_accepted(old, decisions, current=current)
    else:
        with pytest.raises(ValueError): review.require_accepted(old, decisions, current=current)
