import pytest

from accessi_code.models.audit_context import UnresolvedTextContrast
from accessi_code.models.color_style import TextContrastSample
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_03_colors.criterion_3_2 import (
    Test321 as RGAA321,
)
from accessi_code.rgaa.tests.theme_03_colors.criterion_3_2 import (
    Test322 as RGAA322,
)
from accessi_code.rgaa.tests.theme_03_colors.criterion_3_2 import (
    Test323 as RGAA323,
)
from accessi_code.rgaa.tests.theme_03_colors.criterion_3_2 import (
    Test324 as RGAA324,
)
from accessi_code.rgaa.tests.theme_03_colors.criterion_3_2 import (
    Test325 as RGAA325,
)


def text_sample(
    *,
    element: str = "p",
    text: str = "Texte",
    color: str = "#000000",
    background_color: str = "#ffffff",
    font_size_px: float = 16,
    font_weight: int = 400,
    is_image_text: bool = False,
    exempt: bool = False,
    is_contrast_mechanism: bool = False,
) -> TextContrastSample:
    return TextContrastSample(
        element=element,
        text=text,
        color=color,
        background_color=background_color,
        font_size_px=font_size_px,
        font_weight=font_weight,
        is_image_text=is_image_text,
        exempt=exempt,
        is_contrast_mechanism=is_contrast_mechanism,
    )


# ---------------------------------------------------------------------------

# 3.2.1

# ---------------------------------------------------------------------------


def test_321_small_normal_text_with_sufficient_contrast_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory("<p>Texte</p>")
    context.text_contrast_samples = [
        text_sample(
            color="#000000",
            background_color="#ffffff",
            font_size_px=16,
            font_weight=400,
        )
    ]
    result = run_rgaa(RGAA321(), context)
    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert result.findings == []


def test_321_small_normal_text_with_insufficient_contrast_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory("<p>Texte</p>")
    context.text_contrast_samples = [
        text_sample(
            color="#777777",
            background_color="#ffffff",
            font_size_px=16,
            font_weight=400,
        )
    ]
    result = run_rgaa(RGAA321(), context)
    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert len(result.findings) == 1
    assert result.findings[0].element == "p"


def test_321_large_text_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<p>Grand texte</p>")
    context.text_contrast_samples = [
        text_sample(
            font_size_px=24,
            font_weight=400,
        )
    ]
    result = run_rgaa(RGAA321(), context)
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_321_unparseable_color_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory("<p>Texte</p>")
    context.text_contrast_samples = [
        text_sample(
            color="transparent",
            background_color="#ffffff",
            font_size_px=16,
            font_weight=400,
        )
    ]
    result = run_rgaa(RGAA321(), context)
    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert len(result.findings) == 1


def test_321_exempt_text_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<p>Texte</p>")
    context.text_contrast_samples = [
        text_sample(
            font_size_px=16,
            font_weight=400,
            exempt=True,
        )
    ]
    result = run_rgaa(RGAA321(), context)
    assert result.status == Status.NOT_APPLICABLE


def test_321_failure_has_priority_over_unknown_contrast(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main></main>")
    context.text_contrast_samples = [
        text_sample(
            element="p#failure",
            color="#777777",
            background_color="#ffffff",
            font_size_px=16,
            font_weight=400,
        ),
        text_sample(
            element="p#unknown",
            color="transparent",
            background_color="#ffffff",
            font_size_px=16,
            font_weight=400,
        ),
    ]
    result = run_rgaa(RGAA321(), context)
    assert result.status == Status.FAIL
    assert result.tested_elements == 2
    assert len(result.findings) == 2


# ---------------------------------------------------------------------------

# 3.2.2

# ---------------------------------------------------------------------------


def test_322_small_bold_text_with_sufficient_contrast_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory("<strong>Texte</strong>")
    context.text_contrast_samples = [
        text_sample(
            element="strong",
            color="#000000",
            background_color="#ffffff",
            font_size_px=18,
            font_weight=700,
        )
    ]
    result = run_rgaa(RGAA322(), context)
    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_322_small_bold_text_with_insufficient_contrast_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory("<strong>Texte</strong>")
    context.text_contrast_samples = [
        text_sample(
            element="strong",
            color="#777777",
            background_color="#ffffff",
            font_size_px=18,
            font_weight=700,
        )
    ]
    result = run_rgaa(RGAA322(), context)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1


def test_322_bold_text_at_large_threshold_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<strong>Grand texte</strong>")
    context.text_contrast_samples = [
        text_sample(
            font_size_px=18.5,
            font_weight=700,
        )
    ]
    result = run_rgaa(RGAA322(), context)
    assert result.status == Status.NOT_APPLICABLE


def test_322_normal_weight_text_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<p>Texte</p>")
    context.text_contrast_samples = [
        text_sample(
            font_size_px=18,
            font_weight=400,
        )
    ]
    result = run_rgaa(RGAA322(), context)
    assert result.status == Status.NOT_APPLICABLE


# ---------------------------------------------------------------------------

# 3.2.3

# ---------------------------------------------------------------------------


def test_323_large_normal_text_with_ratio_above_three_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory("<p>Grand texte</p>")
    context.text_contrast_samples = [
        text_sample(
            color="#595959",
            background_color="#ffffff",
            font_size_px=24,
            font_weight=400,
        )
    ]
    result = run_rgaa(RGAA323(), context)
    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_323_large_normal_text_with_insufficient_contrast_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory("<p>Grand texte</p>")
    context.text_contrast_samples = [
        text_sample(
            color="#aaaaaa",
            background_color="#ffffff",
            font_size_px=24,
            font_weight=400,
        )
    ]
    result = run_rgaa(RGAA323(), context)
    assert result.status == Status.FAIL


def test_323_small_normal_text_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<p>Texte</p>")
    context.text_contrast_samples = [
        text_sample(
            font_size_px=23,
            font_weight=400,
        )
    ]
    result = run_rgaa(RGAA323(), context)
    assert result.status == Status.NOT_APPLICABLE


# ---------------------------------------------------------------------------

# 3.2.4

# ---------------------------------------------------------------------------


def test_324_large_bold_text_with_sufficient_contrast_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory("<strong>Grand texte</strong>")
    context.text_contrast_samples = [
        text_sample(
            color="#595959",
            background_color="#ffffff",
            font_size_px=18.5,
            font_weight=700,
        )
    ]
    result = run_rgaa(RGAA324(), context)
    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_324_large_bold_text_with_insufficient_contrast_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory("<strong>Grand texte</strong>")
    context.text_contrast_samples = [
        text_sample(
            color="#aaaaaa",
            background_color="#ffffff",
            font_size_px=18.5,
            font_weight=700,
        )
    ]
    result = run_rgaa(RGAA324(), context)
    assert result.status == Status.FAIL


def test_324_small_bold_text_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<strong>Texte</strong>")
    context.text_contrast_samples = [
        text_sample(
            font_size_px=18,
            font_weight=700,
        )
    ]
    result = run_rgaa(RGAA324(), context)
    assert result.status == Status.NOT_APPLICABLE


# ---------------------------------------------------------------------------

# 3.2.5

# ---------------------------------------------------------------------------


def test_325_contrast_mechanism_with_sufficient_contrast_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main></main>")
    context.text_contrast_samples = [
        text_sample(
            element="body.high-contrast p",
            color="#000000",
            background_color="#ffffff",
            font_size_px=16,
            font_weight=400,
            is_contrast_mechanism=True,
        )
    ]
    result = run_rgaa(RGAA325(), context)
    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert result.findings == []


def test_325_contrast_mechanism_with_insufficient_contrast_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main></main>")
    context.text_contrast_samples = [
        text_sample(
            element="body.high-contrast p",
            color="#aaaaaa",
            background_color="#ffffff",
            font_size_px=16,
            font_weight=400,
            is_contrast_mechanism=True,
        )
    ]
    result = run_rgaa(RGAA325(), context)
    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert len(result.findings) == 1


def test_325_large_text_mechanism_uses_three_to_one_threshold(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main></main>")
    context.text_contrast_samples = [
        text_sample(
            element="body.high-contrast p",
            color="#595959",
            background_color="#ffffff",
            font_size_px=24,
            font_weight=400,
            is_contrast_mechanism=True,
        )
    ]
    result = run_rgaa(RGAA325(), context)
    assert result.status == Status.PASS


def test_325_unparseable_mechanism_color_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main></main>")
    context.text_contrast_samples = [
        text_sample(
            element="body.high-contrast p",
            color="transparent",
            background_color="#ffffff",
            font_size_px=16,
            font_weight=400,
            is_contrast_mechanism=True,
        )
    ]
    result = run_rgaa(RGAA325(), context)
    assert result.status == Status.NEEDS_REVIEW
    assert len(result.findings) == 1


def test_325_without_contrast_mechanism_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<p>Texte</p>")
    context.text_contrast_samples = [
        text_sample(
            is_contrast_mechanism=False,
        )
    ]
    result = run_rgaa(RGAA325(), context)
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_325_failure_has_priority_over_unknown_contrast(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main></main>")
    context.text_contrast_samples = [
        text_sample(
            element="p#failure",
            color="#aaaaaa",
            background_color="#ffffff",
            is_contrast_mechanism=True,
        ),
        text_sample(
            element="p#unknown",
            color="transparent",
            background_color="#ffffff",
            is_contrast_mechanism=True,
        ),
    ]
    result = run_rgaa(RGAA325(), context)
    assert result.status == Status.FAIL
    assert result.tested_elements == 2


# ---------------------------------------------------------------------------

# Couverture partielle des contrastes extraits automatiquement

# ---------------------------------------------------------------------------


def test_321_partial_extraction_with_sufficient_contrast_requires_review(
    context_factory,
    run_rgaa,
):
    """Un bon contraste observé ne prouve pas la conformité de toute la page."""
    context = context_factory("<p>Texte suffisamment contrasté</p>")
    context.text_contrast_samples = [
        text_sample(
            element="p",
            color="#000000",
            background_color="#ffffff",
            font_size_px=16,
            font_weight=400,
        )
    ]
    context.text_contrast_extraction_attempted = True
    context.text_contrast_coverage_complete = False
    context.text_contrast_unresolved_count = 1
    result = run_rgaa(RGAA321(), context)
    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert result.findings == []
    assert result.metadata["text_contrast_extraction_attempted"] is True
    assert result.metadata["text_contrast_coverage_complete"] is False
    assert result.metadata["text_contrast_unresolved_count"] == 1


def test_321_partial_extraction_with_insufficient_contrast_fails(
    context_factory,
    run_rgaa,
):
    """Un défaut mesuré reste prioritaire sur l'incertitude de couverture."""
    context = context_factory("<p>Contraste insuffisant</p>")
    context.text_contrast_samples = [
        text_sample(
            element="p#failure",
            color="#aaaaaa",
            background_color="#ffffff",
            font_size_px=16,
            font_weight=400,
        )
    ]
    context.text_contrast_extraction_attempted = True
    context.text_contrast_coverage_complete = False
    result = run_rgaa(RGAA321(), context)
    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert len(result.findings) == 1
    assert result.findings[0].element == "p#failure"
    assert result.metadata["failed_elements"] == 1
    assert result.metadata["text_contrast_coverage_complete"] is False


def test_321_partial_extraction_without_applicable_text_requires_review(
    context_factory,
    run_rgaa,
):
    """L'absence d'échantillon applicable n'est pas une preuve d'absence."""
    context = context_factory("<strong>Grand texte</strong>")
    context.text_contrast_samples = [
        text_sample(
            element="strong",
            color="#000000",
            background_color="#ffffff",
            font_size_px=24,
            font_weight=700,
        )
    ]
    context.text_contrast_extraction_attempted = True
    context.text_contrast_coverage_complete = False
    result = run_rgaa(RGAA321(), context)
    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 0
    assert result.metadata["applicable_elements"] == 0


def test_322_partial_extraction_with_sufficient_contrast_requires_review(
    context_factory,
    run_rgaa,
):
    """Le contrôle des petits textes gras respecte la couverture partielle."""
    context = context_factory("<strong>Texte gras</strong>")
    context.text_contrast_samples = [
        text_sample(
            element="strong",
            color="#000000",
            background_color="#ffffff",
            font_size_px=17,
            font_weight=700,
        )
    ]
    context.text_contrast_extraction_attempted = True
    context.text_contrast_coverage_complete = False
    result = run_rgaa(RGAA322(), context)
    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_323_and_324_partial_extraction_require_review(
    context_factory,
    run_rgaa,
):
    """Les grands textes normaux et gras restent soumis à la couverture."""
    cases = [
        (
            RGAA323(),
            text_sample(
                element="p#large-normal",
                color="#595959",
                background_color="#ffffff",
                font_size_px=26,
                font_weight=400,
            ),
        ),
        (
            RGAA324(),
            text_sample(
                element="p#large-bold",
                color="#595959",
                background_color="#ffffff",
                font_size_px=20,
                font_weight=700,
            ),
        ),
    ]
    for test, sample in cases:
        context = context_factory("<p>Grand texte</p>")
        context.text_contrast_samples = [sample]
        context.text_contrast_extraction_attempted = True
        context.text_contrast_coverage_complete = False
        result = run_rgaa(test, context)
        assert result.status == Status.NEEDS_REVIEW
        assert result.tested_elements == 1


def test_325_partial_extraction_without_mechanism_requires_review(
    context_factory,
    run_rgaa,
):
    """Un mécanisme absent des observations n'est pas nécessairement absent."""
    context = context_factory("<p>Texte normal</p>")
    context.text_contrast_samples = [
        text_sample(
            element="p",
            color="#000000",
            background_color="#ffffff",
            is_contrast_mechanism=False,
        )
    ]
    context.text_contrast_extraction_attempted = True
    context.text_contrast_coverage_complete = False
    result = run_rgaa(RGAA325(), context)
    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 0
    assert result.metadata["mechanisms"] == 0


def test_321_complete_or_manual_context_preserves_pass(
    context_factory,
    run_rgaa,
):
    """Les contextes manuels et ceux à couverture prouvée gardent PASS."""
    for attempted, complete in [
        (False, False),
        (True, True),
    ]:
        context = context_factory("<p>Texte conforme</p>")
        context.text_contrast_samples = [
            text_sample(
                element="p",
                color="#000000",
                background_color="#ffffff",
                font_size_px=16,
                font_weight=400,
            )
        ]
        context.text_contrast_extraction_attempted = attempted
        context.text_contrast_coverage_complete = complete
        result = run_rgaa(RGAA321(), context)
        assert result.status == Status.PASS
        assert result.tested_elements == 1


# ---------------------------------------------------------------------------
# Observations dont le contraste reste à vérifier
# ---------------------------------------------------------------------------


def unresolved_observation(
    *,
    element: str = "label",
    text: str = "Nom",
    reason: str = "Pseudo-élément susceptible de modifier le rendu",
    font_size_px: float | None = 16.0,
    font_weight: int | None = 400,
) -> UnresolvedTextContrast:
    """Crée une observation de contraste non résolue."""
    return UnresolvedTextContrast(
        element=element,
        text=text,
        reason=reason,
        font_size_px=font_size_px,
        font_weight=font_weight,
    )


@pytest.mark.parametrize(
    ("test_class", "font_size_px", "font_weight", "test_id"),
    [
        (RGAA321, 16.0, 400, "3.2.1"),
        (RGAA322, 18.0, 700, "3.2.2"),
        (RGAA323, 24.0, 400, "3.2.3"),
        (RGAA324, 18.5, 700, "3.2.4"),
    ],
)
def test_unresolved_typography_is_reported_in_matching_test_only(
    context_factory,
    run_rgaa,
    test_class,
    font_size_px,
    font_weight,
    test_id,
):
    """Un texte rejeté figure uniquement dans son sous-test typographique."""
    context = context_factory("<p>Contraste à vérifier</p>")
    context.text_contrast_samples = [text_sample()]
    context.unresolved_text_contrasts = [
        unresolved_observation(
            font_size_px=font_size_px,
            font_weight=font_weight,
        )
    ]
    context.text_contrast_extraction_attempted = True
    context.text_contrast_coverage_complete = False
    context.text_contrast_unresolved_count = 1
    results = [run_rgaa(test(), context) for test in (RGAA321, RGAA322, RGAA323, RGAA324)]
    review_findings = [
        (result.test_id, finding)
        for result in results
        for finding in result.findings
        if finding.evidence.get("requires_manual_review") is True
    ]
    assert len(review_findings) == 1
    assigned_id, finding = review_findings[0]
    assert assigned_id == test_id
    assert finding.element == "label"
    assert finding.evidence["text"] == "Nom"
    assert finding.evidence["font_size_px"] == font_size_px
    assert finding.evidence["font_weight"] == font_weight
    assert finding.evidence["contrast_ratio"] is None
    assert finding.evidence["reason"] == ("Pseudo-élément susceptible de modifier le rendu")
    assert finding.evidence["classification"] == "typography"
    assert results[(RGAA321, RGAA322, RGAA323, RGAA324).index(test_class)].status == Status.NEEDS_REVIEW


def test_unclassified_unresolved_observation_is_visible_once(
    context_factory,
    run_rgaa,
):
    """Une typographie inconnue reste visible sans sous-test inventé."""
    context = context_factory("<p>Texte ambigu</p>")
    context.text_contrast_samples = [text_sample()]
    context.unresolved_text_contrasts = [
        unresolved_observation(
            element="p#ambiguous",
            text="Texte ambigu",
            font_size_px=None,
            font_weight=400,
        )
    ]
    context.text_contrast_unresolved_count = 1
    results = [run_rgaa(test(), context) for test in (RGAA321, RGAA322, RGAA323, RGAA324)]
    review_findings = [
        (result.test_id, finding)
        for result in results
        for finding in result.findings
        if finding.evidence.get("requires_manual_review") is True
    ]
    assert len(review_findings) == 1
    test_id, finding = review_findings[0]
    assert test_id == "3.2.1"  # Point d'affichage des observations générales.
    assert finding.element == "p#ambiguous"
    assert finding.evidence["classification"] == "unclassified"
    assert finding.evidence["typography_valid"] is False
    assert finding.evidence["contrast_ratio"] is None
    assert "non classée" in finding.message
    assert results[0].metadata["unresolved_unclassified_displayed"] == 1


def test_confirmed_contrast_failure_keeps_priority_with_unresolved_observation(
    context_factory,
    run_rgaa,
):
    """Une incertitude ne masque pas un défaut de contraste mesuré."""
    context = context_factory("<p>Texte</p>")
    context.text_contrast_samples = [
        text_sample(
            element="p#failure",
            color="#aaaaaa",
            background_color="#ffffff",
            font_size_px=16,
            font_weight=400,
        )
    ]
    context.unresolved_text_contrasts = [unresolved_observation()]
    context.text_contrast_unresolved_count = 1
    result = run_rgaa(RGAA321(), context)
    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert result.metadata["failed_elements"] == 1
    assert len(result.findings) == 2
    assert {finding.element for finding in result.findings} == {
        "p#failure",
        "label",
    }
    assert sum(finding.evidence.get("requires_manual_review") is True for finding in result.findings) == 1


def test_unresolved_only_is_not_counted_as_measured_element(
    context_factory,
    run_rgaa,
):
    """Un rejet ne gonfle pas le nombre d'échantillons mesurables."""
    context = context_factory("<p>Texte</p>")
    # On fournit un échantillon exploitable relevant d'un autre sous-test :
    # le TestRunner peut ainsi exécuter 3.2.1 sans capacité manquante.
    context.text_contrast_samples = [text_sample(font_size_px=24, font_weight=400)]
    context.unresolved_text_contrasts = [unresolved_observation()]
    context.text_contrast_extraction_attempted = True
    context.text_contrast_coverage_complete = False
    context.text_contrast_unresolved_count = 1
    result = run_rgaa(RGAA321(), context)
    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 0
    assert result.metadata["applicable_elements"] == 0
    assert result.metadata["unresolved_assigned_to_test"] == 1
    assert len(result.findings) == 1
    assert result.findings[0].evidence["contrast_ratio"] is None


def test_unresolved_text_is_not_attributed_to_contrast_mechanism(
    context_factory,
    run_rgaa,
):
    """Sans indication de mécanisme, aucun rejet n'est attribué à 3.2.5."""
    context = context_factory("<p>Texte</p>")
    context.text_contrast_samples = [text_sample()]
    context.unresolved_text_contrasts = [unresolved_observation()]
    context.text_contrast_unresolved_count = 1
    result = run_rgaa(RGAA325(), context)
    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 0
    assert result.findings == []
