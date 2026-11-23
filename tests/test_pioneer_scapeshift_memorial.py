"""Owner's utility-land boundary is scoped to optional Scapeshift kicker use."""

from mtgmeta.classifier_cards import deck_colors


PROFILE = "pioneer-scapeshift-memorial-v1"
MAIN = {
    "Lotus Field": 4, "Scapeshift": 4, "Spelunking": 4,
    "Forest": 4, "Island": 4, "Plains": 4, "Opt": 1,
    "Temporary Lockdown": 1, "Memorial to Folly": 1,
}


def test_memorial_only_kicker_is_scoped_without_erasing_real_black_uses():
    side = {"Tear Asunder": 2}
    assert deck_colors(MAIN, side).colors == {"white", "blue", "black", "green"}
    scoped = deck_colors(MAIN, side, profile=PROFILE)
    assert scoped.colors == {"white", "blue", "green"}
    assert next(c for c in scoped.contributions if c.card == "Tear Asunder").colors == ("green",)
    assert deck_colors(MAIN | {"Swamp": 1}, side, profile=PROFILE).colors == {
        "white", "blue", "black", "green",
    }
    assert deck_colors(MAIN | {"Morlun, Devourer of Spiders": 1}, side, profile=PROFILE).colors == {
        "white", "blue", "black", "green",
    }


def test_green_lessons_with_ordinary_green_lands_keep_their_color():
    main = {"Island": 8, "Mountain": 8, "Willowrush Verge": 4,
            "Thornspire Verge": 4, "Divide by Zero": 4, "Pop Quiz": 3,
            "Gran-Gran": 4, "Accumulate Wisdom": 3, "Firebending Lesson": 4}
    assert deck_colors(main, {"Origin of Metalbending": 4}).colors == {"blue", "red", "green"}
    without_green = {k: v for k, v in main.items() if k not in {"Willowrush Verge", "Thornspire Verge"}}
    assert deck_colors(without_green, {"Origin of Metalbending": 4}).colors == {"blue", "red"}
