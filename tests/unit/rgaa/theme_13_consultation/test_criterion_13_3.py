"""Critères RGAA 13.3 et 13.4 : documents bureautiques et versions accessibles."""

import asyncio

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_3 import Test1331
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_4 import Test1341

WITH_ALTERNATIVE = """
<ul>
  <li><a href="docs/rapport.pdf">Rapport annuel (PDF, 2 Mo)</a> –
      <a href="rapport.html">version HTML</a></li>
</ul>
"""


def test_1331_no_document_is_not_applicable(context_factory, run_rgaa):
    html = '<a href="/contact">Contact</a><a href="photo.jpg">Photo</a>'
    assert run_rgaa(Test1331(), context_factory(html)).status == Status.NOT_APPLICABLE


def test_1331_document_without_alternative_needs_review(context_factory, run_rgaa):
    result = run_rgaa(Test1331(), context_factory('<p><a href="rapport.pdf?v=2">Rapport annuel</a></p>'))
    assert result.status == Status.NEEDS_REVIEW
    assert result.findings[0].evidence["format"] == "PDF"


@pytest.mark.parametrize(
    "html",
    [
        WITH_ALTERNATIVE,
        '<p><a href="guide.docx">Guide</a></p><p><a href="/guide">Guide (version accessible)</a></p>',
        '<a href="guide.odt">Guide</a> <a href="guide.html">Lire en ligne</a>',
        '<a href="guide-accessible.pdf">Guide – version accessible (PDF balisé)</a>',
    ],
)
def test_1331_accessible_version_passes(html, context_factory, run_rgaa):
    result = run_rgaa(Test1331(), context_factory(html))
    assert result.status == Status.PASS
    assert result.findings == []


def test_1331_unrelated_neighbour_link_is_not_an_alternative(context_factory, run_rgaa):
    html = '<p><a href="tarifs.xlsx">Tarifs</a> ou <a href="/contact">contactez-nous</a></p>'
    assert run_rgaa(Test1331(), context_factory(html)).status == Status.NEEDS_REVIEW


def test_1341_pairs_need_review(context_factory, run_rgaa):
    result = run_rgaa(Test1341(), context_factory(WITH_ALTERNATIVE))
    assert result.status == Status.NEEDS_REVIEW
    assert result.findings[0].evidence["alternative_href"] == "rapport.html"


def test_1341_without_alternative_is_not_applicable(context_factory, run_rgaa):
    html = '<a href="rapport.pdf">Rapport</a>'
    assert run_rgaa(Test1341(), context_factory(html)).status == Status.NOT_APPLICABLE


@pytest.mark.parametrize("test", [Test1331(), Test1341()])
def test_13_3_missing_dom_raises_error(test, context_factory):
    context = context_factory("<p>x</p>")
    context.dom = None
    with pytest.raises(ValueError, match="nécessite un DOM"):
        asyncio.run(test.run(context))
