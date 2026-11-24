"""Critère RGAA 1.2 : images de décoration ignorées par les technologies d'assistance."""

import pytest
from image_fakes import profile, services

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_01_images.criterion_1_2 import (
    Test121,
    Test122,
    Test123,
    Test124,
    Test125,
    Test126,
)

ALL = [Test121, Test122, Test123, Test124, Test125, Test126]
DECORATIVE = profile(informative=False)


@pytest.mark.parametrize("cls", ALL)
def test_no_element_is_not_applicable(cls, context_factory, run_rgaa):
    assert run_rgaa(cls(), context_factory("<p>Texte</p>"), services()).status == Status.NOT_APPLICABLE


@pytest.mark.parametrize(
    "html",
    ['<img src="d.png" alt="">', '<img src="d.png" aria-hidden="true">', '<img src="d.png" role="presentation">'],
)
def test_121_correctly_ignored_decorative_image_passes_without_ai(html, context_factory, run_rgaa):
    ai = services()
    assert run_rgaa(Test121(), context_factory(html), ai).status == Status.PASS
    ai.image_analyzer.profile.assert_not_called()


def test_121_empty_alt_with_title_fails(context_factory, run_rgaa):
    ai = services(image_profile=DECORATIVE)
    context = context_factory('<img src="d.png" alt="" title="Fleur">')
    result = run_rgaa(Test121(), context, ai)
    assert result.status == Status.FAIL
    assert 'Avant : <img alt="" src="d.png" title="Fleur"/>' in result.findings[0].recommendation
    assert 'Après : <img alt="" src="d.png"/>' in result.findings[0].recommendation
    assert context.dom.img["title"] == "Fleur"


def test_121_decorative_image_with_filled_alt_fails(context_factory, run_rgaa):
    ai = services(image_profile=DECORATIVE)
    result = run_rgaa(Test121(), context_factory('<img src="d.png" alt="Fleurs décoratives">'), ai)
    assert result.status == Status.FAIL
    assert "alt n'est pas vide" in result.findings[0].message


def test_121_informative_image_is_not_applicable(context_factory, run_rgaa):
    ai = services(image_profile=profile(informative=True))
    assert run_rgaa(Test121(), context_factory('<img src="g.png" alt="Ventes">'), ai).status == Status.NOT_APPLICABLE


def test_121_image_with_caption_is_out_of_scope(context_factory, run_rgaa):
    html = '<figure><img src="d.png" alt="Photo"><figcaption>Légende</figcaption></figure>'
    assert (
        run_rgaa(Test121(), context_factory(html), services(image_profile=DECORATIVE)).status == Status.NOT_APPLICABLE
    )


def test_121_low_confidence_needs_review(context_factory, run_rgaa):
    ai = services(image_profile=profile(informative=False, confidence="low"))
    assert run_rgaa(Test121(), context_factory('<img src="d.png" alt="x">'), ai).status == Status.NEEDS_REVIEW


def test_121_without_ai_unmarked_image_needs_review(context_factory, run_rgaa):
    assert run_rgaa(Test121(), context_factory('<img src="d.png" alt="x">')).status == Status.NEEDS_REVIEW


def test_121_ai_exception_gives_error(context_factory, run_rgaa):
    ai = services(image_profile=RuntimeError("panne"))
    assert run_rgaa(Test121(), context_factory('<img src="d.png" alt="x">'), ai).status == Status.ERROR


def test_122_non_clickable_area(context_factory, run_rgaa):
    assert run_rgaa(Test122(), context_factory('<map><area alt=""></map>'), services()).status == Status.PASS
    result = run_rgaa(Test122(), context_factory('<map><area alt="Zone"></map>'), services(image_profile=DECORATIVE))
    assert result.status == Status.FAIL


def test_123_object(context_factory, run_rgaa):
    ok = '<object type="image/png" data="d.png" aria-hidden="true"></object>'
    ko = '<object type="image/png" data="d.png" aria-hidden="true">Texte de repli</object>'
    assert run_rgaa(Test123(), context_factory(ok), services()).status == Status.PASS
    assert run_rgaa(Test123(), context_factory(ko), services()).status == Status.FAIL


def test_124_svg_hidden_without_alternatives_passes(context_factory, run_rgaa):
    html = '<svg aria-hidden="true"><path d="M0 0"/></svg>'
    assert run_rgaa(Test124(), context_factory(html), services()).status == Status.PASS


def test_124_hidden_svg_with_title_fails(context_factory, run_rgaa):
    svg = '<svg aria-hidden="true"><title>Icône</title></svg>'
    result = run_rgaa(Test124(), context_factory(f"<p>Décoration</p>\n{svg}"), services())
    assert result.status == Status.FAIL
    assert "<title>" in result.findings[0].message
    assert 'Après : <svg aria-hidden="true"></svg>' in result.findings[0].recommendation
    assert (result.findings[0].line, result.findings[0].snippet) == (2, svg)


def test_124_decorative_svg_without_aria_hidden_fails(context_factory, run_rgaa):
    result = run_rgaa(Test124(), context_factory("<svg><path/></svg>"), services(image_profile=DECORATIVE))
    assert result.status == Status.FAIL


def test_125_canvas(context_factory, run_rgaa):
    ok = '<canvas aria-hidden="true"></canvas>'
    ko = '<canvas aria-hidden="true">Texte</canvas>'
    assert run_rgaa(Test125(), context_factory(ok), services()).status == Status.PASS
    assert run_rgaa(Test125(), context_factory(ko), services()).status == Status.FAIL


def test_126_embed(context_factory, run_rgaa):
    ok = '<embed type="image/png" src="d.png" aria-hidden="true">'
    ko = '<embed type="image/png" src="d.png" aria-hidden="true" title="Décor">'
    assert run_rgaa(Test126(), context_factory(ok), services()).status == Status.PASS
    assert run_rgaa(Test126(), context_factory(ko), services()).status == Status.FAIL
