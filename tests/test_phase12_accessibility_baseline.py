from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_shared_accessibility_tokens_are_not_page_local_exceptions() -> None:
    css = read("assets/css/phase8-base.css")

    assert "--text-xs: .8125rem" in css
    assert "--text-sm: .875rem" in css
    assert "--text-base: 1rem" in css
    assert "--target-min: 24px" in css
    assert "--focus-on-light:" in css
    assert "--focus-on-dark:" in css


def test_both_entries_use_the_same_landmark_and_unavailable_contract() -> None:
    for path in ("index.html", "melee/index.html"):
        html = read(path)
        assert '<div id="view" aria-live="polite">' in html
        assert '<section id="view"' not in html
        assert 'id="unavailable-navigation-description"' in html


def test_composition_interaction_is_a_shared_accessible_primitive() -> None:
    core = read("assets/js/phase8/app-core.js")
    mtgo = read("assets/js/phase8/app-mtgo.js")

    assert "function accessibleCompositionSegment" in core
    assert "accessibleCompositionSegment({" in mtgo
    assert 'class="composition-bar" role="img"' not in mtgo


def test_unavailable_navigation_has_a_programmatic_description() -> None:
    core = read("assets/js/phase8/app-core.js")

    assert 'id="unavailable-navigation-description"' not in core
    assert 'aria-describedby="unavailable-navigation-description"' in core
    assert 't("availability.developing")' in core
