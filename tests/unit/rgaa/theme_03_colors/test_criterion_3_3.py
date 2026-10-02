from accessi_code.models.color_style import NonTextContrastSample
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_03_colors.criterion_3_3 import (
    Test331 as RGAA331,
    Test332 as RGAA332,
    Test333 as RGAA333,
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
    return NonTextContrastSample(
        element=element,
        kind=kind,
        comparison=comparison,
        foreground_color=foreground_color,
        background_color=background_color,
        state=state,
        exempt=exempt,
    )


# ---------------------------------------------------------------------------
# 3.3.1
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
    context.non_text_contrast_samples = [
        non_text_sample(
            exempt=True,
        )
    ]

    result = run_rgaa(RGAA331(), context)

    assert result.status == Status.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# 3.3.2
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
# 3.3.3
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
# 3.3.4
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
