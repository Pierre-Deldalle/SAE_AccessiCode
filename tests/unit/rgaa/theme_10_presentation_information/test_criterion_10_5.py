from __future__ import annotations

from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup

from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_5 import (
    Test1051,
    Test1052,
    Test1053,
)


def make_context(html: str) -> SimpleNamespace:
    return SimpleNamespace(dom=BeautifulSoup(html, "html.parser"), html_source=html)


@pytest.mark.asyncio
async def test_1051_fails_when_text_color_has_no_detectable_background():
    html = '<html><body><p id="notice" style="color: red">Attention</p></body></html>'
    result = await Test1051().run(make_context(html))

    assert result.test_id == "10.5.1"
    assert result.criterion_id == "10.5"
    assert result.status == TestStatus.FAIL
    assert result.findings[0].evidence["risk_type"] == "text_color_without_background"


@pytest.mark.asyncio
async def test_1051_passes_when_ancestor_declares_background():
    html = """
    <html><body>
      <main style="background-color: white">
        <p style="color: #222">Texte</p>
      </main>
    </body></html>
    """
    result = await Test1051().run(make_context(html))

    assert result.status == TestStatus.PASS
    assert result.metadata["ancestor_background_found"] >= 1


@pytest.mark.asyncio
async def test_1051_passes_when_background_is_declared_on_same_element():
    html = '<p style="color: white; background-color: navy">Texte</p>'
    result = await Test1051().run(make_context(html))

    assert result.status == TestStatus.PASS


@pytest.mark.asyncio
async def test_1052_fails_when_background_has_no_detectable_text_color():
    html = '<p id="box" style="background-color: yellow">Texte</p>'
    result = await Test1052().run(make_context(html))

    assert result.status == TestStatus.FAIL
    assert result.findings[0].evidence["risk_type"] == "background_without_text_color"


@pytest.mark.asyncio
async def test_1052_passes_when_ancestor_declares_text_color():
    html = """
    <html><body>
      <section style="color: black">
        <p style="background: #eee">Texte</p>
      </section>
    </body></html>
    """
    result = await Test1052().run(make_context(html))

    assert result.status == TestStatus.PASS
    assert result.metadata["ancestor_text_color_found"] >= 1


@pytest.mark.asyncio
async def test_1052_passes_when_color_is_declared_on_same_element():
    html = '<p style="color: black; background-color: white">Texte</p>'
    result = await Test1052().run(make_context(html))

    assert result.status == TestStatus.PASS


@pytest.mark.asyncio
async def test_1053_fails_when_background_image_has_no_fallback_color():
    html = """
    <p id="banner" style="background-image: url('/images/banner.jpg')">
      Texte du bandeau
    </p>
    """
    result = await Test1053().run(make_context(html))

    assert result.status == TestStatus.FAIL
    assert result.findings[0].evidence["risk_type"] == "background_image_without_fallback"


@pytest.mark.asyncio
async def test_1053_passes_when_fallback_background_color_is_declared():
    html = """
    <p style="background-color: #fff; background-image: url('/images/banner.jpg')">
      Texte du bandeau
    </p>
    """
    result = await Test1053().run(make_context(html))

    assert result.status == TestStatus.PASS


@pytest.mark.asyncio
async def test_1053_detects_background_shorthand_with_image():
    html = """
    <p style="background: url('/images/banner.jpg') center / cover no-repeat">
      Texte du bandeau
    </p>
    """
    result = await Test1053().run(make_context(html))

    assert result.status == TestStatus.FAIL


@pytest.mark.asyncio
async def test_stylesheet_rules_are_considered():
    html = """
    <html>
      <head><style>
        .red-text { color: red; }
        .colored-box { background-color: yellow; }
      </style></head>
      <body>
        <p class="red-text">Texte rouge</p>
        <p class="colored-box">Texte sur fond jaune</p>
      </body>
    </html>
    """
    result_1051 = await Test1051().run(make_context(html))
    result_1052 = await Test1052().run(make_context(html))

    assert result_1051.status == TestStatus.FAIL
    assert result_1052.status == TestStatus.FAIL
    assert result_1051.metadata["stylesheet_rules_examined"] == 2


@pytest.mark.asyncio
async def test_external_stylesheets_are_reported_as_a_limitation():
    html = """
    <html><head><link rel="stylesheet" href="/site.css"></head>
    <body><p>Texte</p></body></html>
    """
    result = await Test1051().run(make_context(html))

    assert result.metadata["external_stylesheets_detected"] == 1
    assert result.metadata["computed_browser_styles_available"] is False


@pytest.mark.asyncio
async def test_missing_dom_returns_not_tested():
    context = SimpleNamespace(dom=None, html_source="<p>Texte</p>")
    result = await Test1051().run(context)

    assert result.status == TestStatus.NOT_TESTED
    assert result.metadata["reason"] == "missing_dom"


@pytest.mark.asyncio
async def test_missing_html_source_returns_not_tested():
    context = SimpleNamespace(dom=BeautifulSoup("<p>Texte</p>", "html.parser"), html_source="")
    result = await Test1052().run(context)

    assert result.status == TestStatus.NOT_TESTED
    assert result.metadata["reason"] == "missing_html_source"


@pytest.mark.asyncio
async def test_default_link_color_is_not_flagged_without_explicit_color():
    html = '<a href="/home">Lien</a>'
    result = await Test1051().run(make_context(html))

    assert result.status == TestStatus.PASS
    assert result.metadata["explicit_text_color_declarations"] == 0


@pytest.mark.asyncio
async def test_no_text_elements_means_no_static_violation_detected():
    html = "<html><body><img src='decorative.svg' alt=''></body></html>"
    result = await Test1053().run(make_context(html))

    assert result.status == TestStatus.PASS
    assert result.metadata["text_elements_examined"] == 0


@pytest.mark.parametrize("test_class", [Test1051, Test1052, Test1053])
@pytest.mark.asyncio
async def test_all_tests_return_criterion_metadata(test_class):
    result = await test_class().run(make_context("<p>Bonjour</p>"))

    assert result.criterion_id == "10.5"
    assert result.test_id in {"10.5.1", "10.5.2", "10.5.3"}
    assert result.metadata["analysis"] == "static_html_css_heuristic"
    assert result.metadata["contrast_ratio_measured"] is False
