from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_03_colors.criterion_3_1 import (
    Test311 as RGAA311,
)
from accessi_code.rgaa.tests.theme_03_colors.criterion_3_1 import (
    Test312 as RGAA312,
)
from accessi_code.rgaa.tests.theme_03_colors.criterion_3_1 import (
    Test313 as RGAA313,
)
from accessi_code.rgaa.tests.theme_03_colors.criterion_3_1 import (
    Test314 as RGAA314,
)
from accessi_code.rgaa.tests.theme_03_colors.criterion_3_1 import (
    Test315 as RGAA315,
)
from accessi_code.rgaa.tests.theme_03_colors.criterion_3_1 import (
    Test316 as RGAA316,
)

# ---------------------------------------------------------------------------
# 3.1.1
# ---------------------------------------------------------------------------


def test_311_inline_colored_text_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<p style="color: red;">Attention</p>'
    )

    result = run_rgaa(RGAA311(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert len(result.findings) == 1


def test_311_background_color_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<span style="background-color: yellow;">Information</span>'
    )

    result = run_rgaa(RGAA311(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_311_without_inline_color_still_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<p class="warning">Attention</p>'
    )

    result = run_rgaa(RGAA311(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 0
    assert (
        result.metadata["computed_styles_available"]
        is False
    )


def test_311_multiple_colored_elements_are_reported(
    context_factory,
    run_rgaa,
):
    html = """
    <p style="color: red;">Erreur</p>
    <span style="color: green;">Succès</span>
    """

    context = context_factory(html)

    result = run_rgaa(RGAA311(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 2
    assert len(result.findings) == 2


# ---------------------------------------------------------------------------
# 3.1.2
# ---------------------------------------------------------------------------


def test_312_page_with_text_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        "<p>Les champs en rouge sont obligatoires.</p>"
    )

    result = run_rgaa(RGAA312(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert len(result.findings) == 1


def test_312_empty_page_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        "<main></main>"
    )

    result = run_rgaa(RGAA312(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_312_whitespace_only_page_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        "<main>     </main>"
    )

    result = run_rgaa(RGAA312(), context)

    assert result.status == Status.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# 3.1.3
# ---------------------------------------------------------------------------


def test_313_image_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<img src="chart.png" alt="Résultats">'
    )

    result = run_rgaa(RGAA313(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert len(result.findings) == 1


def test_313_role_img_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<div role="img" aria-label="Graphique"></div>'
    )

    result = run_rgaa(RGAA313(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_313_svg_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        """
        <svg aria-label="Graphique">
            <circle cx="10" cy="10" r="5"></circle>
        </svg>
        """
    )

    result = run_rgaa(RGAA313(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_313_without_image_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        "<main><p>Texte seulement.</p></main>"
    )

    result = run_rgaa(RGAA313(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


# ---------------------------------------------------------------------------
# 3.1.4
# ---------------------------------------------------------------------------


def test_314_css_color_property_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<p style="color: #ff0000;">Erreur</p>'
    )

    result = run_rgaa(RGAA314(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_314_border_color_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<input style="border-color: red;">'
    )

    result = run_rgaa(RGAA314(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_314_without_inline_color_still_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<p class="error">Erreur</p>'
    )

    result = run_rgaa(RGAA314(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 0
    assert (
        result.metadata["computed_styles_available"]
        is False
    )


# ---------------------------------------------------------------------------
# 3.1.5
# ---------------------------------------------------------------------------


def test_315_video_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<video src="tutorial.mp4"></video>'
    )

    result = run_rgaa(RGAA315(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_315_audio_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<audio src="instructions.mp3"></audio>'
    )

    result = run_rgaa(RGAA315(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_315_multiple_temporal_media_are_counted(
    context_factory,
    run_rgaa,
):
    html = """
    <video src="video.mp4"></video>
    <audio src="audio.mp3"></audio>
    """

    context = context_factory(html)

    result = run_rgaa(RGAA315(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 2
    assert len(result.findings) == 2


def test_315_without_temporal_media_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        "<main><p>Texte.</p></main>"
    )

    result = run_rgaa(RGAA315(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


# ---------------------------------------------------------------------------
# 3.1.6
# ---------------------------------------------------------------------------


def test_316_object_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<object data="diagram.pdf"></object>'
    )

    result = run_rgaa(RGAA316(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_316_embed_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<embed src="diagram.svg">'
    )

    result = run_rgaa(RGAA316(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_316_canvas_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        '<canvas id="chart"></canvas>'
    )

    result = run_rgaa(RGAA316(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_316_svg_requires_review(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        """
        <svg>
            <rect width="100" height="50"></rect>
        </svg>
        """
    )

    result = run_rgaa(RGAA316(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_316_without_non_temporal_media_is_not_applicable(
    context_factory,
    run_rgaa,
):
    context = context_factory(
        "<main><p>Texte uniquement.</p></main>"
    )

    result = run_rgaa(RGAA316(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
