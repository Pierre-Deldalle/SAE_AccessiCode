from accessi_code.models.color_style import TextContrastSample
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_03_colors.criterion_3_2 import (
    Test321 as RGAA321,
    Test322 as RGAA322,
    Test323 as RGAA323,
    Test324 as RGAA324,
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
