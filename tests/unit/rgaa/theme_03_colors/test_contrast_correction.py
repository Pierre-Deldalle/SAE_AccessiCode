"""Couleur corrigée proposée pour un contraste insuffisant (critères 3.2 et 3.3)."""

import pytest

from accessi_code.analysis.colors import contrast_ratio
from accessi_code.rgaa.tests.theme_03_colors._contrast import contrast_example, corrected_color, hex_color


@pytest.mark.parametrize(
    ("color", "background", "threshold"),
    [
        ("#999999", "#ffffff", 4.5),
        ("#ff0000", "#ffffff", 4.5),
        ("rgb(0, 128, 255)", "rgb(255, 255, 255)", 4.5),
        ("#555555", "#222222", 4.5),
        ("#cccccc", "#ffffff", 3),
        ("#3355aa", "#000000", 7),
    ],
)
def test_corrected_color_reaches_the_threshold(color, background, threshold):
    fixed = corrected_color(color, background, threshold)
    assert fixed is not None
    assert contrast_ratio(hex_color(fixed), background) >= threshold


def test_correction_is_the_smallest_change():
    # #767676 est le gris le plus clair qui atteint 4.5:1 sur blanc ; #777777 n'y arrive pas.
    assert hex_color(corrected_color("#999999", "#ffffff", 4.5)) == "#767676"
    assert contrast_ratio("#777777", "#ffffff") < 4.5


def test_dark_background_gives_a_lighter_color():
    fixed = corrected_color("#555555", "#222222", 4.5)
    assert fixed is not None and fixed[0] > 0x55


@pytest.mark.parametrize(
    ("color", "background", "threshold"),
    [("#777777", "#777777", 21), ("transparent", "#ffffff", 4.5), ("#000000", "inconnue", 4.5)],
    ids=["seuil impossible", "couleur illisible", "fond illisible"],
)
def test_no_example_when_no_correction(color, background, threshold):
    assert contrast_example(color, background, threshold) == ""
