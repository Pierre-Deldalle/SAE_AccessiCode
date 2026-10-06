from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from accessi_code.ai.schemas import ImageRoleAnalysis
from accessi_code.models.result import TestStatus as Status

from accessi_code.rgaa.tests.theme_01_images.criterion_1_9 import (
    Test191 as RGAA191,
)

def role(
    information_bearing: bool | None,
    *,
    confidence: str = "high",
) -> ImageRoleAnalysis:
    return ImageRoleAnalysis(
        information_bearing=information_bearing,
        explanation="Analyse simulée.",
        uncertainties=[],
        confidence=confidence,
    )

def test_191_valid_figure_passes(context_factory, run_rgaa):
    html = """
    <figure
        role="figure"
        aria-label="Photo du coucher de soleil"
    >
        <img src="sunset.jpg" alt="Coucher de soleil">
        <figcaption>Photo du coucher de soleil</figcaption>
    </figure>
    """

    result = run_rgaa(RGAA191(), context_factory(html))

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert result.findings == []


@pytest.mark.parametrize("role", ["figure", "group"])
def test_191_allowed_figure_roles_pass(
    role,
    context_factory,
    run_rgaa,
):
    html = f"""
    <figure
        role="{role}"
        aria-label="Photo du coucher de soleil"
    >
        <img src="sunset.jpg" alt="Coucher de soleil">
        <figcaption>Photo du coucher de soleil</figcaption>
    </figure>
    """

    result = run_rgaa(RGAA191(), context_factory(html))

    assert result.status == Status.PASS


def test_191_no_caption_is_not_applicable(
    context_factory,
    run_rgaa,
):
    html = """
    <img src="photo.jpg" alt="Une photo">
    """

    result = run_rgaa(RGAA191(), context_factory(html))

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_191_missing_figure_fails(
    context_factory,
    run_rgaa,
):
    html = """
    <img src="photo.jpg" alt="Une photo">
    <figcaption>Photo de paysage</figcaption>
    """

    result = run_rgaa(RGAA191(), context_factory(html))

    assert result.status == Status.FAIL
    assert result.tested_elements == 1


def test_191_missing_role_fails(
    context_factory,
    run_rgaa,
):
    html = """
    <figure aria-label="Photo de paysage">
        <img src="photo.jpg" alt="Une photo">
        <figcaption>Photo de paysage</figcaption>
    </figure>
    """

    result = run_rgaa(RGAA191(), context_factory(html))

    assert result.status == Status.FAIL


def test_191_invalid_role_fails(
    context_factory,
    run_rgaa,
):
    html = """
    <figure
        role="group-invalid"
        aria-label="Photo de paysage"
    >
        <img src="photo.jpg" alt="Une photo">
        <figcaption>Photo de paysage</figcaption>
    </figure>
    """

    result = run_rgaa(RGAA191(), context_factory(html))

    assert result.status == Status.FAIL


def test_191_missing_aria_label_fails(
    context_factory,
    run_rgaa,
):
    html = """
    <figure role="figure">
        <img src="photo.jpg" alt="Une photo">
        <figcaption>Photo de paysage</figcaption>
    </figure>
    """

    result = run_rgaa(RGAA191(), context_factory(html))

    assert result.status == Status.FAIL


def test_191_different_aria_label_fails(
    context_factory,
    run_rgaa,
):
    html = """
    <figure
        role="figure"
        aria-label="Une autre description"
    >
        <img src="photo.jpg" alt="Une photo">
        <figcaption>Photo de paysage</figcaption>
    </figure>
    """

    result = run_rgaa(RGAA191(), context_factory(html))

    assert result.status == Status.FAIL


def test_191_missing_figcaption_fails(
    context_factory,
    run_rgaa,
):
    html = """
    <figure
        role="figure"
        aria-label="Photo de paysage"
    >
        <img src="photo.jpg" alt="Une photo">
        <p>Photo de paysage</p>
    </figure>
    """

    result = run_rgaa(RGAA191(), context_factory(html))

    assert result.status == Status.FAIL


@pytest.mark.parametrize(
    "html",
    [
        """
        <figure role="figure" aria-label="Photo">
            <input type="image" src="photo.jpg">
            <figcaption>Photo</figcaption>
        </figure>
        """,
        """
        <figure role="group" aria-label="Photo">
            <div role="img" aria-label="Photo"></div>
            <figcaption>Photo</figcaption>
        </figure>
        """,
    ],
)
def test_191_supports_all_required_image_types(
    html,
    context_factory,
    run_rgaa,
):
    result = run_rgaa(RGAA191(), context_factory(html))

    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_191_multiple_images_one_invalid_fails(
    context_factory,
    run_rgaa,
):
    html = """
    <figure role="figure" aria-label="Première photo">
        <img src="one.jpg" alt="Première">
        <figcaption>Première photo</figcaption>
    </figure>

    <figure role="figure" aria-label="Mauvaise légende">
        <img src="two.jpg" alt="Deuxième">
        <figcaption>Deuxième photo</figcaption>
    </figure>
    """

    result = run_rgaa(RGAA191(), context_factory(html))

    assert result.status == Status.FAIL
    assert result.tested_elements == 2
    assert len(result.findings) == 1