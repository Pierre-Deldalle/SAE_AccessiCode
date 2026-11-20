"""Tests unitaires du critère RGAA 3.3."""

import pytest

from accessi_code.models.audit_context import UnresolvedNonTextContrast
from accessi_code.models.color_style import NonTextContrastSample
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_03_colors.criterion_3_3 import (
    Test331 as RGAA331,
)
from accessi_code.rgaa.tests.theme_03_colors.criterion_3_3 import (
    Test332 as RGAA332,
)
from accessi_code.rgaa.tests.theme_03_colors.criterion_3_3 import (
    Test333 as RGAA333,
)
from accessi_code.rgaa.tests.theme_03_colors.criterion_3_3 import (
    Test334 as RGAA334,
)


def non_text_sample(
    *,
    element: str = "button",
    kind: str = "component",
    comparison: str = "background",
    foreground_color: str = "#000000",
    background_color: str = "#ffffff",
    state: str | None = None,
    exempt: bool = False,
) -> NonTextContrastSample:
    """Construit un échantillon de contraste non textuel validé."""

    return NonTextContrastSample(
        element=element,
        kind=kind,
        comparison=comparison,
        foreground_color=foreground_color,
        background_color=background_color,
        state=state,
        exempt=exempt,
    )


def unresolved_non_text(
    *,
    element: str = "input#email",
    kind: str = "component",
    comparison: str = "background",
    foreground_color: str | None = "rgb(102, 102, 102)",
    background_color: str | None = "rgb(250, 250, 250)",
    state: str | None = "default",
    reason: str = "Applicabilité de la bordure à confirmer",
) -> UnresolvedNonTextContrast:
    """Construit une observation CSS non textuelle incertaine."""

    return UnresolvedNonTextContrast(
        element=element,
        kind=kind,
        comparison=comparison,
        foreground_color=foreground_color,
        background_color=background_color,
        state=state,
        reason=reason,
    )


# ---------------------------------------------------------------------------
# 3.3.1 : composants d'interface
# ---------------------------------------------------------------------------


def test_331_component_with_sufficient_contrast_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory("<button>Envoyer</button>")
    context.non_text_contrast_samples = [
        non_text_sample(
            element="button",
            kind="component",
            comparison="background",
            foreground_color="#000000",
            background_color="#ffffff",
        )
    ]

    result = run_rgaa(RGAA331(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert result.findings == []


def test_331_component_with_insufficient_contrast_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory("<button>Envoyer</button>")
    context.non_text_contrast_samples = [
        non_text_sample(
            element="button",
            kind="component",
            comparison="background",
            foreground_color="#aaaaaa",
            background_color="#ffffff",
        )
    ]

    result = run_rgaa(RGAA331(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert len(result.findings) == 1
    assert result.findings[0].element == "button"


def test_331_unparseable_component_color_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory("<button>Envoyer</button>")
    context.non_text_contrast_samples = [
        non_text_sample(
            foreground_color="transparent",
            background_color="#ffffff",
        )
    ]

    result = run_rgaa(RGAA331(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert len(result.findings) == 1


def test_331_graphic_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<svg></svg>")
    context.non_text_contrast_samples = [
        non_text_sample(
            kind="graphic",
            comparison="background",
        )
    ]

    result = run_rgaa(RGAA331(), context)

    assert result.status == Status.NOT_APPLICABLE


def test_331_exempt_component_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<button>Envoyer</button>")
    context.non_text_contrast_samples = [non_text_sample(exempt=True)]

    result = run_rgaa(RGAA331(), context)

    assert result.status == Status.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# 3.3.2 : graphiques et arrière-plan
# ---------------------------------------------------------------------------


def test_332_graphic_against_background_with_sufficient_contrast_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory("<svg></svg>")
    context.non_text_contrast_samples = [
        non_text_sample(
            element="svg#chart",
            kind="graphic",
            comparison="background",
            foreground_color="#000000",
            background_color="#ffffff",
        )
    ]

    result = run_rgaa(RGAA332(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_332_graphic_against_background_with_insufficient_contrast_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory("<svg></svg>")
    context.non_text_contrast_samples = [
        non_text_sample(
            element="svg#chart",
            kind="graphic",
            comparison="background",
            foreground_color="#bbbbbb",
            background_color="#ffffff",
        )
    ]

    result = run_rgaa(RGAA332(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1


def test_332_component_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<button>Envoyer</button>")
    context.non_text_contrast_samples = [
        non_text_sample(
            kind="component",
            comparison="background",
        )
    ]

    result = run_rgaa(RGAA332(), context)

    assert result.status == Status.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# 3.3.3 : couleurs graphiques adjacentes
# ---------------------------------------------------------------------------


def test_333_adjacent_graphic_colors_with_sufficient_contrast_pass(
    context_factory,
    run_rgaa,
):
    context = context_factory("<svg></svg>")
    context.non_text_contrast_samples = [
        non_text_sample(
            element="svg#chart rect[1]",
            kind="graphic",
            comparison="adjacent",
            foreground_color="#000000",
            background_color="#ffffff",
        )
    ]

    result = run_rgaa(RGAA333(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_333_adjacent_graphic_colors_with_insufficient_contrast_fail(
    context_factory,
    run_rgaa,
):
    context = context_factory("<svg></svg>")
    context.non_text_contrast_samples = [
        non_text_sample(
            element="svg#chart rect[1]",
            kind="graphic",
            comparison="adjacent",
            foreground_color="#aaaaaa",
            background_color="#ffffff",
        )
    ]

    result = run_rgaa(RGAA333(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1


def test_333_background_comparison_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<svg></svg>")
    context.non_text_contrast_samples = [
        non_text_sample(
            kind="graphic",
            comparison="background",
        )
    ]

    result = run_rgaa(RGAA333(), context)

    assert result.status == Status.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# 3.3.4 : mécanismes de contraste
# ---------------------------------------------------------------------------


def test_334_mechanism_with_sufficient_contrast_passes(
    context_factory,
    run_rgaa,
):
    context = context_factory("<button>Contraste élevé</button>")
    context.non_text_contrast_samples = [
        non_text_sample(
            element="button#high-contrast",
            kind="mechanism",
            comparison="background",
            foreground_color="#000000",
            background_color="#ffffff",
        )
    ]

    result = run_rgaa(RGAA334(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_334_mechanism_with_insufficient_contrast_fails(
    context_factory,
    run_rgaa,
):
    context = context_factory("<button>Contraste élevé</button>")
    context.non_text_contrast_samples = [
        non_text_sample(
            element="button#high-contrast",
            kind="mechanism",
            comparison="background",
            foreground_color="#aaaaaa",
            background_color="#ffffff",
        )
    ]

    result = run_rgaa(RGAA334(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1


def test_334_without_mechanism_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory("<button>Envoyer</button>")
    context.non_text_contrast_samples = [
        non_text_sample(
            kind="component",
            comparison="background",
        )
    ]

    result = run_rgaa(RGAA334(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_334_unparseable_mechanism_color_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory("<button>Contraste élevé</button>")
    context.non_text_contrast_samples = [
        non_text_sample(
            element="button#high-contrast",
            kind="mechanism",
            comparison="background",
            foreground_color="transparent",
            background_color="#ffffff",
        )
    ]

    result = run_rgaa(RGAA334(), context)

    assert result.status == Status.NEEDS_REVIEW


# ---------------------------------------------------------------------------
# Résultats mixtes
# ---------------------------------------------------------------------------


def test_331_failure_has_priority_over_unknown_contrast(
    context_factory,
    run_rgaa,
):
    context = context_factory("<main></main>")
    context.non_text_contrast_samples = [
        non_text_sample(
            element="button#failure",
            foreground_color="#aaaaaa",
            background_color="#ffffff",
        ),
        non_text_sample(
            element="button#unknown",
            foreground_color="transparent",
            background_color="#ffffff",
        ),
    ]

    result = run_rgaa(RGAA331(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 2
    assert len(result.findings) == 2


def test_332_multiple_valid_graphics_all_pass(
    context_factory,
    run_rgaa,
):
    context = context_factory("<svg></svg>")
    context.non_text_contrast_samples = [
        non_text_sample(
            element="svg#chart rect[1]",
            kind="graphic",
            comparison="background",
            foreground_color="#000000",
            background_color="#ffffff",
        ),
        non_text_sample(
            element="svg#chart rect[2]",
            kind="graphic",
            comparison="background",
            foreground_color="#333333",
            background_color="#ffffff",
        ),
    ]

    result = run_rgaa(RGAA332(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 2
    assert result.findings == []


# ---------------------------------------------------------------------------
# Nouveaux tests : observations non textuelles incertaines
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("element", "foreground_color", "expected_ratio"),
    [
        ("input#email-ok", "rgb(102, 102, 102)", 5.50),
        ("input#email-ko", "rgb(220, 220, 220)", 1.31),
    ],
)
def test_331_uncertain_css_candidate_requires_review(
    context_factory,
    run_rgaa,
    element,
    foreground_color,
    expected_ratio,
):
    """
    Un contraste CSS candidat ne doit jamais déclencher
    PASS ou FAIL lorsqu'il reste une incertitude.
    """
    context = context_factory("<input type='email'>")
    context.unresolved_non_text_contrasts = [
        unresolved_non_text(
            element=element,
            foreground_color=foreground_color,
        )
    ]

    result = run_rgaa(RGAA331(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 0
    assert len(result.findings) == 1

    finding = result.findings[0]

    assert finding.element == element
    assert finding.evidence["requires_manual_review"] is True
    assert finding.evidence["measurement_validated"] is False
    assert finding.evidence["candidate_ratio"] == pytest.approx(
        expected_ratio,
        abs=0.01,
    )


def test_331_uncertain_observation_preserves_reason_and_colors(
    context_factory,
    run_rgaa,
):
    """Les preuves destinées à la vérification humaine sont conservées."""
    context = context_factory("<input type='email'>")
    context.unresolved_non_text_contrasts = [
        unresolved_non_text(
            element="input#email-ko",
            foreground_color="rgb(220, 220, 220)",
            background_color="rgb(250, 250, 250)",
            reason="Surface réellement adjacente à confirmer",
        )
    ]

    result = run_rgaa(RGAA331(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert len(result.findings) == 1

    evidence = result.findings[0].evidence

    assert evidence["kind"] == "component"
    assert evidence["comparison"] == "background"
    assert evidence["foreground_color"] == "rgb(220, 220, 220)"
    assert evidence["background_color"] == "rgb(250, 250, 250)"
    assert evidence["state"] == "default"
    assert evidence["reason"] == "Surface réellement adjacente à confirmer"
    assert evidence["required_ratio"] == 3.0
    assert evidence["requires_manual_review"] is True


def test_331_confirmed_failure_has_priority_over_uncertain_observation(
    context_factory,
    run_rgaa,
):
    """Un défaut fiable reste FAIL même si une autre mesure est incertaine."""
    context = context_factory("<main></main>")

    context.non_text_contrast_samples = [
        non_text_sample(
            element="button#failure",
            foreground_color="#aaaaaa",
            background_color="#ffffff",
        )
    ]

    context.unresolved_non_text_contrasts = [
        unresolved_non_text(
            element="input#email-ko",
            foreground_color="rgb(220, 220, 220)",
        )
    ]

    result = run_rgaa(RGAA331(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert len(result.findings) == 2
    assert result.metadata["failed_elements"] == 1
    assert result.metadata["unresolved_assigned_to_test"] == 1


def test_331_uncertain_observation_is_not_counted_as_validated_sample(
    context_factory,
    run_rgaa,
):
    """Une observation incertaine n'augmente pas tested_elements."""
    context = context_factory("<main></main>")

    context.non_text_contrast_samples = [
        non_text_sample(
            element="input#confirmed",
            foreground_color="#000000",
            background_color="#ffffff",
        )
    ]

    context.unresolved_non_text_contrasts = [
        unresolved_non_text(
            element="input#candidate",
            foreground_color="rgb(102, 102, 102)",
        )
    ]

    result = run_rgaa(RGAA331(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert len(result.findings) == 1
    assert result.metadata["applicable_elements"] == 1
    assert result.metadata["unresolved_assigned_to_test"] == 1
    assert result.metadata["non_text_coverage_partial"] is True


def test_331_uncertain_observation_without_calculable_colors(
    context_factory,
    run_rgaa,
):
    """Une couleur manquante doit produire une vérification, pas un défaut."""
    context = context_factory("<input type='email'>")

    context.unresolved_non_text_contrasts = [
        unresolved_non_text(
            foreground_color=None,
            background_color="rgb(250, 250, 250)",
            reason="Bordure non interprétable",
        )
    ]

    result = run_rgaa(RGAA331(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert len(result.findings) == 1
    assert result.findings[0].evidence["candidate_ratio"] is None
    assert result.findings[0].evidence["measurement_validated"] is False


def test_other_33_tests_require_review_when_coverage_is_uncertain(
    context_factory,
    run_rgaa,
):
    """
    Une observation de composant ne prouve pas que les graphiques
    et mécanismes de la page ont été exhaustivement contrôlés.
    """
    context = context_factory("<input type='email'>")

    context.unresolved_non_text_contrasts = [
        unresolved_non_text(
            element="input#email",
        )
    ]

    for test_class in (RGAA332, RGAA333, RGAA334):
        result = run_rgaa(test_class(), context)

        assert result.status == Status.NEEDS_REVIEW
        assert result.tested_elements == 0
        assert result.metadata["non_text_coverage_partial"] is True
