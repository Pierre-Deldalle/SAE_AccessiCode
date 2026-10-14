"""Tests unitaires de la conversion des observations CSS."""

import pytest

from accessi_code.input.contrast_sample_builder import ContrastSampleBuilder
from accessi_code.input.extractors.computed_styles import TextStyleObservation
from accessi_code.models.color_style import TextContrastSample


def make_observation(
    *,
    text: str = "Texte de test",
    color: str = "rgb(0, 0, 0)",
    background_color: str | None = "rgb(255, 255, 255)",
    font_size_px: float = 16.0,
    font_weight: int = 400,
    review_reason: str | None = None,
) -> TextStyleObservation:
    """Construit une observation CSS pour les tests."""

    return TextStyleObservation(
        element="html > body > p",
        text=text,
        color=color,
        background_color=background_color,
        font_size_px=font_size_px,
        font_weight=font_weight,
        review_reason=review_reason,
    )


def test_valid_observation_creates_sample() -> None:
    """Une observation simple produit un échantillon de contraste."""

    observation = make_observation()

    result = ContrastSampleBuilder().build([observation])

    assert result.accepted_count == 1
    assert result.rejected_count == 0
    assert result.rejection_reasons == []

    sample = result.samples[0]

    assert isinstance(sample, TextContrastSample)
    assert sample.element == observation.element
    assert sample.text == observation.text
    assert sample.color == observation.color
    assert sample.background_color == observation.background_color
    assert sample.font_size_px == 16.0
    assert sample.font_weight == 400


@pytest.mark.parametrize(
    ("color", "expected"),
    [
        ("rgb(0, 0, 0)", True),
        ("rgb(255, 255, 255)", True),
        ("rgb(31, 58, 95)", True),
        ("rgb(256, 0, 0)", False),
        ("rgb(-1, 0, 0)", False),
        ("rgba(0, 0, 0, 0)", False),
        ("rgba(0, 0, 0, 0.5)", False),
        ("transparent", False),
        ("red", False),
        ("", False),
        (None, False),
    ],
)
def test_opaque_rgb_validation(
    color: str | None,
    expected: bool,
) -> None:
    """Seules les couleurs RGB opaques valides sont acceptées."""

    assert ContrastSampleBuilder._is_opaque_rgb(color) is expected


@pytest.mark.parametrize(
    ("changes", "expected_reason"),
    [
        ({"text": "  "}, "Texte vide."),
        (
            {"color": "rgba(0, 0, 0, 0.5)"},
            "Couleur du texte absente ou non opaque.",
        ),
        (
            {"background_color": None},
            "Couleur de fond absente ou non opaque.",
        ),
        (
            {"background_color": "rgba(0, 0, 0, 0)"},
            "Couleur de fond absente ou non opaque.",
        ),
        (
            {"font_size_px": 0},
            "Taille de police invalide.",
        ),
        (
            {"font_size_px": -10},
            "Taille de police invalide.",
        ),
        (
            {"font_size_px": float("nan")},
            "Taille de police non finie.",
        ),
        (
            {"font_size_px": float("inf")},
            "Taille de police non finie.",
        ),
        (
            {"font_weight": 0},
            "Graisse de police invalide.",
        ),
        (
            {"font_weight": 1001},
            "Graisse de police invalide.",
        ),
        (
            {"review_reason": "Fond complexe"},
            "Fond complexe",
        ),
    ],
)
def test_invalid_observation_is_rejected(
    changes: dict,
    expected_reason: str,
) -> None:
    """Les données invalides ou incertaines sont rejetées."""

    observation = make_observation(**changes)

    result = ContrastSampleBuilder().build([observation])

    assert result.accepted_count == 0
    assert result.rejected_count == 1
    assert result.rejected_observations == [observation]
    assert result.rejection_reasons == [expected_reason]


def test_mixed_observations() -> None:
    """Les observations valides et invalides sont séparées."""

    valid = make_observation(text="Contraste calculable")
    unknown_background = make_observation(
        text="Fond inconnu",
        background_color=None,
    )
    complex_background = make_observation(
        text="Fond complexe",
        review_reason="Image de fond",
    )

    result = ContrastSampleBuilder().build([valid, unknown_background, complex_background])

    assert result.accepted_count == 1
    assert result.rejected_count == 2
    assert len(result.samples) == 1
    assert result.rejected_observations == [
        unknown_background,
        complex_background,
    ]


def test_empty_observations() -> None:
    """Une liste vide ne produit aucun échantillon."""

    result = ContrastSampleBuilder().build([])

    assert result.accepted_count == 0
    assert result.rejected_count == 0
    assert result.samples == []
    assert result.rejection_reasons == []
