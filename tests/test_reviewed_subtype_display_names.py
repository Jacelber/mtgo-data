import pytest

from mtgmeta.mtgo.landing_editorial import _display_english


@pytest.mark.parametrize("parent,subtype,expected", [
    ("Dimir Control", "Dimir Splash Red Control", "Dimir Splash Red Control"),
    ("Azorius Familiars", "Jeskai Familiars", "Jeskai Familiars"),
    ("Golgari Gardens", "Jund Garden", "Jund Garden"),
    ("Jeskai Ephemerate", "Four-Color", "Four-Color Ephemerate"),
    ("Lifegain", "Orzhov", "Orzhov Lifegain"),
])
def test_reviewed_full_names_and_existing_color_abbreviations(parent, subtype, expected):
    assert _display_english(parent, subtype) == expected
