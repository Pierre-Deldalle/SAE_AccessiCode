"""Non-régressions du critère RGAA 1.6."""
import pytest
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_01_images.criterion_1_6 import (
    Test161,
    Test162,
    Test163,
    Test164,
    Test165,
    Test166,
    Test167,
    Test168,
    Test169,
    Test1610,
)

@pytest.mark.parametrize("cls", [
    Test161,
    Test162,
    Test163,
    Test164,
    Test165,
    Test166,
    Test167,
    Test168,
    Test169,
    Test1610,
])
def test_absent_elements_not_applicable(cls, context_factory, run_rgaa):
    result = run_rgaa(cls(), context_factory("<html></html>"))
    assert result.status == Status.NOT_APPLICABLE


def test_required_detailed_description_missing_fails(context_factory, run_rgaa):
    html='<img id="chart" alt="Résultats">'
    ctx=context_factory(html, **{'img#chart': {'verified':True,'requires_detailed_description':True}})
    assert run_rgaa(Test161(), ctx).status == Status.FAIL

def test_broken_describedby_fails(context_factory, run_rgaa):
    html='<img alt="Diagramme" aria-describedby="missing">'
    assert run_rgaa(Test169(), context_factory(html)).status == Status.FAIL

def test_svg_description_mechanism(context_factory, run_rgaa):
    html='<p id="d">Données</p><svg id="s" role="img" aria-label="Graphique" aria-describedby="d"></svg>'
    ctx=context_factory(html, **{'svg#s': {'verified':True, 'requires_detailed_description':True, 'description_accessible':True}})
    assert run_rgaa(Test165(), ctx).status == Status.PASS

def test_aria_role_img_detailed_description(context_factory, run_rgaa):
    html='<p id="d">Détails</p><div role="img" aria-label="Diagramme" aria-describedby="d"></div>'
    assert run_rgaa(Test1610(), context_factory(html)).status == Status.PASS
