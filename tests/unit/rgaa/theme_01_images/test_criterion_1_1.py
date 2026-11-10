"""Non-régressions du critère RGAA 1.1."""
import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_01_images.criterion_1_1 import (
    Test111,
    Test112,
    Test113,
    Test114,
    Test115,
    Test116,
    Test117,
    Test118,
)


@pytest.mark.parametrize("cls", [
    Test111,
    Test112,
    Test113,
    Test114,
    Test115,
    Test116,
    Test117,
    Test118,
])
def test_absent_elements_not_applicable(cls, context_factory, run_rgaa):
    result = run_rgaa(cls(), context_factory("<html></html>"))
    assert result.status == Status.NOT_APPLICABLE


def test_img_alt_passes_without_ollama(context_factory, run_rgaa):
    assert run_rgaa(Test111(), context_factory('<img alt="Logo" src="logo.png">')).status == Status.PASS

def test_functional_image_missing_alt_fails(context_factory, run_rgaa):
    assert run_rgaa(Test111(), context_factory('<a href="/x"><img src="x.png"></a>')).status == Status.FAIL

def test_area_with_alt_passes(context_factory, run_rgaa):
    assert run_rgaa(Test112(), context_factory('<map><area href="/a" alt="A"></map>')).status == Status.PASS

def test_area_missing_alt_fails(context_factory, run_rgaa):
    assert run_rgaa(Test112(), context_factory('<map><area href="/a"></map>')).status == Status.FAIL

def test_input_image_alt_passes(context_factory, run_rgaa):
    assert run_rgaa(Test113(), context_factory('<input type="image" alt="Envoyer">')).status == Status.PASS

def test_ismap_requires_verified_equivalence(context_factory, run_rgaa):
    html = '<a href="/map"><img id="map" src="map.png" ismap></a>'
    assert run_rgaa(Test114(), context_factory(html)).status == Status.NEEDS_REVIEW
    assert run_rgaa(Test114(), context_factory(html, image_evidence={'img#map': {'verified':True, 'equivalent_destinations':True}})).status == Status.PASS

def test_svg_informative_missing_role_fails(context_factory, run_rgaa):
    html = '<svg id="s" aria-label="Graphique"><path d="M0 0"/></svg>'
    ctx=context_factory(html, image_evidence={'svg#s': {'verified':True, 'information_bearing':True}})
    assert run_rgaa(Test115(), ctx).status == Status.FAIL

def test_svg_role_and_alt_pass(context_factory, run_rgaa):
    assert run_rgaa(Test115(), context_factory('<svg role="img" aria-label="Diagramme"></svg>')).status == Status.PASS

def test_object_image_with_role_and_alt_pass(context_factory, run_rgaa):
    html='<object type="image/svg+xml" role="img" aria-label="Logo"></object>'
    ctx=context_factory(html, image_evidence={'object[index=0]': {'verified':True, 'information_bearing':True}})
    assert run_rgaa(Test116(), ctx).status == Status.PASS

def test_canvas_with_fallback_pass(context_factory, run_rgaa):
    html='<canvas id="c">Graphique: 2, 3, 4</canvas>'
    ctx=context_factory(html, image_evidence={'canvas#c': {'verified':True, 'information_bearing':True}})
    assert run_rgaa(Test118(), ctx).status == Status.PASS

def test_embed_role_alt_passes(context_factory, run_rgaa):
    html='<embed type="image/png" role="img" aria-label="Illustration">'
    assert run_rgaa(Test117(), context_factory(html)).status == Status.PASS

def test_role_img_title_alone_is_not_valid_alternative(context_factory, run_rgaa):
    html='<div role="img" title="Logo"></div>'
    assert run_rgaa(Test111(), context_factory(html)).status == Status.FAIL

def test_canvas_labelledby_is_valid(context_factory, run_rgaa):
    html='<p id="c-title">Résultats</p><canvas role="img" aria-labelledby="c-title"></canvas>'
    assert run_rgaa(Test118(), context_factory(html)).status == Status.PASS
