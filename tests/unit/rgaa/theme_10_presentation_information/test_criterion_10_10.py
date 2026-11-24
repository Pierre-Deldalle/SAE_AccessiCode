"""Critère RGAA 10.10 : pertinence du moyen qui complète la forme, la taille ou la position (jugée par l'IA)."""

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_10 import (
    Test10101,
    Test10102,
    Test10103,
    Test10104,
)
from tests.ai_fakes import sensory, text_services

POSITION_TEXT = '<p id="consigne">Cliquez sur le bouton « Valider », à droite.</p>'


@pytest.mark.parametrize("test_class", [Test10101, Test10102, Test10103, Test10104])
def test_no_candidate_is_not_applicable(test_class, context_factory, run_rgaa):
    assert run_rgaa(test_class(), context_factory("<p>Bienvenue.</p>"), text_services()).status == (
        Status.NOT_APPLICABLE
    )


def test_relevant_alternative_passes(context_factory, run_rgaa):
    ai = text_services(sensory_answer=sensory(relies_only=False, alternative=True))
    assert run_rgaa(Test10101(), context_factory(POSITION_TEXT), ai).status == Status.PASS


def test_irrelevant_alternative_fails(context_factory, run_rgaa):
    ai = text_services(sensory_answer=sensory(relies_only=False, alternative=False))
    result = run_rgaa(Test10101(), context_factory(POSITION_TEXT), ai)
    assert result.status == Status.FAIL
    assert "n'est pas pertinent" in result.findings[0].message


def test_without_alternative_is_left_to_10_9(context_factory, run_rgaa):
    ai = text_services(sensory_answer=sensory(relies_only=True, alternative=None))
    assert run_rgaa(Test10101(), context_factory(POSITION_TEXT), ai).status == Status.NOT_APPLICABLE


@pytest.mark.parametrize("answer", [sensory(alternative=None), sensory(alternative=False, confidence="low")])
def test_uncertain_alternative_needs_review(answer, context_factory, run_rgaa):
    ai = text_services(sensory_answer=answer)
    assert run_rgaa(Test10101(), context_factory(POSITION_TEXT), ai).status == Status.NEEDS_REVIEW


def test_shares_candidates_and_kind_with_10_9(context_factory, run_rgaa):
    ai = text_services()
    run_rgaa(Test10101(), context_factory(POSITION_TEXT), ai)
    kind, items = ai.sensory_analyzer.analyze_texts.call_args.args
    assert kind == "shape_size_position"
    assert items[0].text == "Cliquez sur le bouton « Valider », à droite."


def test_image_alternative_is_judged(context_factory, run_rgaa):
    ai = text_services(sensory_image_answer=sensory(relies_only=False, alternative=False))
    result = run_rgaa(Test10102(), context_factory('<img src="plan.png" alt="Plan">'), ai)
    assert result.status == Status.FAIL


def test_media_need_review(context_factory, run_rgaa):
    assert run_rgaa(Test10103(), context_factory('<audio src="a.mp3"></audio>'), text_services()).status == (
        Status.NEEDS_REVIEW
    )
    assert run_rgaa(Test10104(), context_factory('<object data="a.swf"></object>'), text_services()).status == (
        Status.NEEDS_REVIEW
    )
