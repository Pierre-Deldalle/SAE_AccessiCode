from __future__ import annotations

from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup

from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_4 import (
    Test1041,
    Test1042,
)


def make_context(html: str) -> SimpleNamespace:
    return SimpleNamespace(
        dom=BeautifulSoup(html, "html.parser"),
        html_source=html,
    )


@pytest.mark.parametrize("test_class", [Test1041, Test1042])
@pytest.mark.asyncio
async def test_returns_needs_review_when_static_analysis_cannot_verify_browser_zoom(
    test_class,
):
    """Un DOM seul ne permet pas de valider le rendu à 200 %."""
    test = test_class()
    result = await test.run(make_context("<html><body><p>Bonjour</p></body></html>"))

    assert result.test_id == test_class.test_id
    assert result.criterion_id == "10.4"
    assert result.status == TestStatus.NEEDS_REVIEW
    assert result.metadata["browser_zoom_test_performed"] is False
    assert result.metadata["text_elements_examined"] >= 1


@pytest.mark.parametrize("test_class", [Test1041, Test1042])
@pytest.mark.asyncio
async def test_reports_fixed_dimensions_and_hidden_overflow(test_class):
    html = """
    <html><body>
      <div id="notice" style="width: 120px; height: 24px; overflow: hidden">
        Un texte important qui risque d'être coupé lorsque la taille augmente.
      </div>
    </body></html>
    """
    result = await test_class().run(make_context(html))

    assert result.status == TestStatus.NEEDS_REVIEW
    risk_types = {finding.evidence.get("risk_type") for finding in result.findings}
    assert "fixed_dimension" in risk_types
    assert "clipped_overflow" in risk_types
    assert result.metadata["potential_layout_risks"] >= 2


@pytest.mark.parametrize("test_class", [Test1041, Test1042])
@pytest.mark.asyncio
async def test_reports_nowrap_inline_style(test_class):
    html = """
    <html><body>
      <p id="single-line" style="white-space: nowrap">Texte qui ne revient pas à la ligne</p>
    </body></html>
    """
    result = await test_class().run(make_context(html))

    assert any(
        finding.evidence.get("risk_type") == "nowrap"
        for finding in result.findings
    )


@pytest.mark.parametrize("test_class", [Test1041, Test1042])
@pytest.mark.asyncio
async def test_reports_risky_stylesheet_rules(test_class):
    html = """
    <html>
      <head>
        <style>
          .message { height: 30px; overflow: hidden; white-space: nowrap; }
        </style>
      </head>
      <body><p class="message">Un message</p></body>
    </html>
    """
    result = await test_class().run(make_context(html))

    assert any(
        finding.evidence.get("risk_type") == "stylesheet_layout_risk"
        for finding in result.findings
    )
    assert result.metadata["stylesheet_risks"] >= 1


@pytest.mark.parametrize("test_class", [Test1041, Test1042])
@pytest.mark.asyncio
async def test_reports_missing_dom_as_not_tested(test_class):
    test = test_class()
    context = SimpleNamespace(dom=None, html_source="<p>Texte</p>")

    result = await test.run(context)

    assert result.status == TestStatus.NOT_TESTED
    assert result.metadata["reason"] == "missing_dom"


@pytest.mark.parametrize("test_class", [Test1041, Test1042])
@pytest.mark.asyncio
async def test_reports_missing_html_source_as_not_tested(test_class):
    test = test_class()
    context = SimpleNamespace(
        dom=BeautifulSoup("<p>Texte</p>", "html.parser"),
        html_source="",
    )

    result = await test.run(context)

    assert result.status == TestStatus.NOT_TESTED
    assert result.metadata["reason"] == "missing_html_source"


@pytest.mark.asyncio
async def test_1041_identifies_information_loss_as_manual_check():
    result = await Test1041().run(
        make_context("<html><body><p>Texte</p></body></html>")
    )

    assert result.metadata["manual_check_for"] == "perte d'information à 200 %"


@pytest.mark.asyncio
async def test_1042_identifies_actual_text_enlargement_as_manual_check():
    result = await Test1042().run(
        make_context("<html><body><p>Texte</p></body></html>")
    )

    assert (
        result.metadata["manual_check_for"]
        == "agrandissement effectif de l'ensemble du texte à 200 %"
    )


@pytest.mark.asyncio
async def test_canvas_is_counted_as_exception_and_not_analyzed_as_text():
    html = "<html><body><canvas>Texte dessiné dans canvas</canvas><p>Texte HTML</p></body></html>"
    result = await Test1041().run(make_context(html))

    assert result.metadata["exceptions_to_review"]["canvas"] == 1
    # Le texte HTML est examiné ; le texte de canvas ne constitue pas du texte DOM
    # que ce contrôle statique puisse valider au titre du critère.
    assert result.metadata["text_elements_examined"] == 1
