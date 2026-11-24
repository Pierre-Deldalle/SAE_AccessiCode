"""Critère RGAA 1.9 : légendes d'images reliées à leur image."""

import pytest
from image_fakes import services

from accessi_code.ai.schemas import StructureCandidateAnalysis
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_01_images.criterion_1_9 import (
    Test191,
    Test192,
    Test193,
    Test194,
    Test195,
)

ALL = [Test191, Test192, Test193, Test194, Test195]
GOOD_FIGURE = (
    '<figure role="figure" aria-label="Évolution des ventes">'
    '<img src="g.png" alt="Graphique"><figcaption>Évolution des ventes</figcaption></figure>'
)
LOOSE_CAPTION = '<div><img src="g.png" alt="Graphique"><p class="legende">Figure 1 : ventes 2025</p></div>'


@pytest.mark.parametrize("cls", ALL)
def test_no_caption_is_not_applicable(cls, context_factory, run_rgaa):
    assert run_rgaa(cls(), context_factory('<img src="a.png" alt="A">'), services()).status == Status.NOT_APPLICABLE


def test_191_correct_figure_passes_without_ai(context_factory, run_rgaa):
    ai = services()
    assert run_rgaa(Test191(), context_factory(GOOD_FIGURE), ai).status == Status.PASS
    ai.structure_analyzer.classify_candidates.assert_not_called()


def test_191_figure_without_role_fails(context_factory, run_rgaa):
    figure = '<figure aria-label="Ventes">\n<img alt="G" src="g.png"/>\n<figcaption>Ventes</figcaption></figure>'
    html = f"<p>Ventes</p>\n{figure}"
    result = run_rgaa(Test191(), context_factory(html), services())
    assert result.status == Status.FAIL
    assert 'role="figure"' in result.findings[0].message
    assert (result.findings[0].line, result.findings[0].snippet) == (2, figure)


def test_191_aria_label_different_from_caption_fails(context_factory, run_rgaa):
    html = '<figure role="group" aria-label="Autre"><img src="g.png" alt="G"><figcaption>Ventes</figcaption></figure>'
    result = run_rgaa(Test191(), context_factory(html), services())
    assert result.status == Status.FAIL
    assert "aria-label" in result.findings[0].message
    assert 'Avant : <figure aria-label="Autre" role="group">' in result.findings[0].recommendation
    assert 'Après : <figure aria-label="Ventes" role="group">' in result.findings[0].recommendation


def test_191_unlinked_caption_confirmed_by_ai_fails(context_factory, run_rgaa):
    ai = services(caption=StructureCandidateAnalysis(True, "Légende de figure.", confidence="high"))
    result = run_rgaa(Test191(), context_factory(LOOSE_CAPTION), ai)
    assert result.status == Status.FAIL
    assert 'Après : <figure role="figure" aria-label="Figure 1 : ventes 2025">' in result.findings[0].recommendation
    assert "<figcaption>Figure 1 : ventes 2025</figcaption>" in result.findings[0].recommendation
    kind, items = ai.structure_analyzer.classify_candidates.call_args.args
    assert kind == "caption"
    assert items[0].text == "Figure 1 : ventes 2025"


def test_191_adjacent_text_that_is_not_a_caption(context_factory, run_rgaa):
    ai = services(caption=StructureCandidateAnalysis(False, "Paragraphe.", confidence="high"))
    assert run_rgaa(Test191(), context_factory(LOOSE_CAPTION), ai).status == Status.NOT_APPLICABLE


def test_191_low_confidence_needs_review(context_factory, run_rgaa):
    ai = services(caption=StructureCandidateAnalysis(True, "?", confidence="low"))
    assert run_rgaa(Test191(), context_factory(LOOSE_CAPTION), ai).status == Status.NEEDS_REVIEW


def test_191_without_ai_needs_review(context_factory, run_rgaa):
    assert run_rgaa(Test191(), context_factory(LOOSE_CAPTION)).status == Status.NEEDS_REVIEW


def test_191_ai_exception_gives_error(context_factory, run_rgaa):
    ai = services(caption=RuntimeError("panne"))
    assert run_rgaa(Test191(), context_factory(LOOSE_CAPTION), ai).status == Status.ERROR


def test_191_image_button_in_figure(context_factory, run_rgaa):
    html = (
        '<figure role="figure" aria-label="Valider"><input type="image" src="ok.png" alt="OK">'
        "<figcaption>Valider</figcaption></figure>"
    )
    assert run_rgaa(Test191(), context_factory(html), services()).status == Status.PASS


def test_194_svg_in_figure(context_factory, run_rgaa):
    html = '<figure><svg role="img" aria-label="Plan"></svg><figcaption>Plan du site</figcaption></figure>'
    assert run_rgaa(Test194(), context_factory(html), services()).status == Status.FAIL
