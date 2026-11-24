"""Critère RGAA 1.6 : description détaillée si nécessaire."""

import pytest
from image_fakes import profile, services

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

ALL = [Test161, Test162, Test163, Test164, Test165, Test166, Test167, Test168, Test169, Test1610]
COMPLEX = profile(informative=True, needs_description=True)


@pytest.mark.parametrize("cls", ALL)
def test_no_element_is_not_applicable(cls, context_factory, run_rgaa):
    assert run_rgaa(cls(), context_factory("<p>Texte</p>"), services()).status == Status.NOT_APPLICABLE


@pytest.mark.parametrize(
    "html",
    [
        '<img src="g.png" alt="Ventes" longdesc="desc.html">',
        '<img src="g.png" alt="Ventes" aria-describedby="d"><p id="d">Les ventes ont doublé.</p>',
        '<p><img src="g.png" alt="Ventes"><a href="desc.html">Description détaillée du graphique</a></p>',
        '<img src="g.png" alt="Ventes, description détaillée ci-dessous">',
    ],
)
def test_161_description_mechanism_passes_without_ai(html, context_factory, run_rgaa):
    ai = services(image_profile=COMPLEX)
    assert run_rgaa(Test161(), context_factory(html), ai).status == Status.PASS
    ai.image_analyzer.profile.assert_not_called()


def test_161_complex_image_without_description_fails(context_factory, run_rgaa):
    result = run_rgaa(Test161(), context_factory('<img src="g.png" alt="Ventes">'), services(image_profile=COMPLEX))
    assert result.status == Status.FAIL


def test_161_unrelated_adjacent_link_is_not_a_description(context_factory, run_rgaa):
    html = '<p><img src="g.png" alt="Ventes"><a href="/contact">Contact</a></p>'
    assert run_rgaa(Test161(), context_factory(html), services(image_profile=COMPLEX)).status == Status.FAIL


def test_161_simple_image_is_not_applicable(context_factory, run_rgaa):
    ai = services(image_profile=profile(informative=True, needs_description=False))
    assert run_rgaa(Test161(), context_factory('<img src="logo.png" alt="Logo">'), ai).status == Status.NOT_APPLICABLE


def test_161_decorative_image_is_not_applicable(context_factory, run_rgaa):
    ai = services(image_profile=profile(informative=False, needs_description=True))
    assert run_rgaa(Test161(), context_factory('<img src="d.png" alt="x">'), ai).status == Status.NOT_APPLICABLE


def test_161_low_confidence_needs_review(context_factory, run_rgaa):
    ai = services(image_profile=profile(needs_description=True, confidence="low"))
    assert run_rgaa(Test161(), context_factory('<img src="g.png" alt="x">'), ai).status == Status.NEEDS_REVIEW


def test_161_without_ai_needs_review(context_factory, run_rgaa):
    assert run_rgaa(Test161(), context_factory('<img src="g.png" alt="x">')).status == Status.NEEDS_REVIEW


def test_161_ai_exception_gives_error(context_factory, run_rgaa):
    ai = services(image_profile=RuntimeError("panne"))
    assert run_rgaa(Test161(), context_factory('<img src="g.png" alt="x">'), ai).status == Status.ERROR


def test_165_svg_aria_labelledby_two_passages_passes(context_factory, run_rgaa):
    html = '<p id="t">Ventes</p><p id="d">Hausse continue.</p><svg role="img" aria-labelledby="t d"></svg>'
    assert run_rgaa(Test165(), context_factory(html), services(image_profile=COMPLEX)).status == Status.PASS


def test_1610_role_img_without_description_fails(context_factory, run_rgaa):
    html = '<div role="img" aria-label="Carte des agences"></div>'
    assert run_rgaa(Test1610(), context_factory(html), services(image_profile=COMPLEX)).status == Status.FAIL


def test_166_svg_description_restitution_needs_review(context_factory, run_rgaa):
    html = '<svg role="img" aria-label="Ventes" aria-describedby="d"></svg><p id="d">Hausse de 10 %.</p>'
    assert run_rgaa(Test166(), context_factory(html), services()).status == Status.NEEDS_REVIEW


def test_168_canvas_content_description_restitution(context_factory, run_rgaa):
    long_text = "Ventes mensuelles détaillées : " + "janvier 10, février 12, mars 15, " * 6
    result = run_rgaa(Test168(), context_factory(f"<canvas>{long_text}</canvas>"), services())
    assert result.status == Status.NEEDS_REVIEW


def test_169_broken_aria_describedby_fails(context_factory, run_rgaa):
    result = run_rgaa(Test169(), context_factory('<img src="g.png" alt="x" aria-describedby="absent">'), services())
    assert result.status == Status.FAIL
    assert "Avant :" not in result.findings[0].recommendation


def test_169_example_keeps_existing_description_reference(context_factory, run_rgaa):
    html = '<img src="g.png" alt="G" aria-describedby="absent legende"><p id="legende">Les ventes ont doublé.</p>'
    result = run_rgaa(Test169(), context_factory(html))

    assert result.status == Status.FAIL
    assert 'aria-describedby="absent legende"' in result.findings[0].recommendation
    assert 'Après : <img alt="G" aria-describedby="legende" src="g.png"/>' in result.findings[0].recommendation


def test_169_valid_aria_describedby_needs_screen_reader_check(context_factory, run_rgaa):
    html = '<img src="g.png" alt="x" aria-describedby="d"><p id="d">Description.</p>'
    assert run_rgaa(Test169(), context_factory(html), services()).status == Status.NEEDS_REVIEW


def test_169_documented_restitution(context_factory, run_rgaa):
    html = '<img id="g" src="g.png" alt="x" aria-describedby="d"><p id="d">Description.</p>'
    context = context_factory(html, image_evidence={"img#g": {"verified": True, "correctly_exposed": True}})
    assert run_rgaa(Test169(), context, services()).status == Status.PASS
