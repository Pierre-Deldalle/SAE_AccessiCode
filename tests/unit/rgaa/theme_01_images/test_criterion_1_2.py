from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_01_images.criterion_1_2 import (
    Test121 as RGAA121,
)


def make_context(html: str):
    return SimpleNamespace(
        dom=BeautifulSoup(html, "html.parser"),
    )


@pytest.mark.asyncio
async def test_no_decorative_images_returns_not_applicable():
    context = make_context(
        """
        <html>
            <body>
                <img src="photo.jpg" alt="Photo de Bastien">
            </body>
        </html>
        """
    )

    result = await RGAA121().run(context, None)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


@pytest.mark.asyncio
async def test_empty_alt_is_pass():
    context = make_context(
        '<img src="decoration.png" alt="">'
    )

    result = await RGAA121().run(context, None)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


@pytest.mark.asyncio
async def test_aria_hidden_true_is_pass():
    context = make_context(
        '<img src="decoration.png" aria-hidden="true">'
    )

    result = await RGAA121().run(context, None)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


@pytest.mark.asyncio
async def test_role_presentation_is_pass():
    context = make_context(
        '<img src="decoration.png" role="presentation">'
    )

    result = await RGAA121().run(context, None)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


@pytest.mark.asyncio
async def test_alt_empty_with_title_is_fail():
    context = make_context(
        '<img src="decoration.png" alt="" title="Décoration">'
    )

    result = await RGAA121().run(context, None)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert len(result.findings) == 1


@pytest.mark.asyncio
async def test_alt_empty_with_aria_label_is_fail():
    context = make_context(
        '<img src="decoration.png" alt="" aria-label="Décoration">'
    )

    result = await RGAA121().run(context, None)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1


@pytest.mark.asyncio
async def test_alt_empty_with_aria_labelledby_is_fail():
    context = make_context(
        '<img src="decoration.png" alt="" aria-labelledby="description">'
    )

    result = await RGAA121().run(context, None)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1


@pytest.mark.asyncio
async def test_aria_hidden_with_title_is_fail():
    context = make_context(
        '<img src="decoration.png" aria-hidden="true" title="Décoration">'
    )

    result = await RGAA121().run(context, None)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1


@pytest.mark.asyncio
async def test_role_presentation_with_aria_label_is_fail():
    context = make_context(
        '<img src="decoration.png" role="presentation" aria-label="Décoration">'
    )

    result = await RGAA121().run(context, None)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1


@pytest.mark.asyncio
async def test_image_with_caption_is_not_tested():
    context = make_context(
        """
        <figure>
            <img src="decoration.png" alt="" title="Image">
            <figcaption>Légende</figcaption>
        </figure>
        """
    )

    result = await RGAA121().run(context, None)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


@pytest.mark.asyncio
async def test_mixed_images_returns_fail():
    context = make_context(
        """
        <img src="ok.png" alt="">
        <img src="ko.png" alt="" aria-label="Image décorative">
        """
    )

    result = await RGAA121().run(context, None)

    assert result.status == Status.FAIL
    assert result.tested_elements == 2
    assert len(result.findings) == 1


@pytest.mark.asyncio
async def test_role_with_multiple_values_containing_presentation_is_pass():
    context = make_context(
        '<img src="decoration.png" role="presentation img">'
    )

    result = await RGAA121().run(context, None)

    assert result.status == Status.PASS
    assert result.tested_elements == 1