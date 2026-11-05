"""Non-régressions du critère RGAA 1.7."""
import pytest
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_01_images.criterion_1_7 import (
    Test171,
    Test172,
    Test173,
    Test174,
    Test175,
    Test176,
)

@pytest.mark.parametrize("cls", [
    Test171,
    Test172,
    Test173,
    Test174,
    Test175,
    Test176,
])
def test_absent_elements_not_applicable(cls, context_factory, run_rgaa):
    result = run_rgaa(cls(), context_factory("<html></html>"))
    assert result.status == Status.NOT_APPLICABLE


def test_logo_without_description_is_not_applicable(context_factory, run_rgaa):
    assert run_rgaa(Test171(), context_factory('<img alt="Logo" src="logo.png">')).status == Status.NOT_APPLICABLE

def test_detailed_description_relevance_requires_proof(context_factory, run_rgaa):
    html='<p id="detail">Graphique: croissance de 2%</p><img id="chart" alt="Graphique" aria-describedby="detail">'
    assert run_rgaa(Test171(), context_factory(html)).status == Status.NEEDS_REVIEW

def test_svg_detailed_description_requires_relevance(context_factory, run_rgaa):
    html='<p id="d">Détails</p><svg role="img" aria-label="Graphique" aria-describedby="d"></svg>'
    assert run_rgaa(Test175(), context_factory(html)).status == Status.NEEDS_REVIEW
