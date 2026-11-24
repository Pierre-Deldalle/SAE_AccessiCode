"""Critère RGAA 1.4 : alternative des CAPTCHA et images-tests."""

import pytest
from tests.unit.rgaa.theme_01_images.image_fakes import alternative, profile, services

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_01_images.criterion_1_4 import (
    Test141,
    Test142,
    Test143,
    Test144,
    Test145,
    Test146,
    Test147,
)

ALL = [Test141, Test142, Test143, Test144, Test145, Test146, Test147]
CAPTCHA = '<img id="captcha" src="captcha.png" alt="Code de sécurité à recopier">'


@pytest.mark.parametrize("cls", ALL)
def test_no_element_is_not_applicable(cls, context_factory, run_rgaa):
    assert run_rgaa(cls(), context_factory("<p>Texte</p>"), services()).status == Status.NOT_APPLICABLE


def test_141_relevant_captcha_alternative_passes(context_factory, run_rgaa):
    ai = services(alternative_analysis=alternative(relevant=True))
    assert run_rgaa(Test141(), context_factory(CAPTCHA), ai).status == Status.PASS
    assert ai.image_analyzer.analyze_alternative.await_args.kwargs["mode"] == "captcha"


def test_141_irrelevant_captcha_alternative_fails(context_factory, run_rgaa):
    ai = services(alternative_analysis=alternative(relevant=False))
    assert run_rgaa(Test141(), context_factory(CAPTCHA), ai).status == Status.FAIL


def test_141_low_confidence_needs_review(context_factory, run_rgaa):
    ai = services(alternative_analysis=alternative(relevant=True, confidence="low"))
    assert run_rgaa(Test141(), context_factory(CAPTCHA), ai).status == Status.NEEDS_REVIEW


def test_141_without_ai_needs_review(context_factory, run_rgaa):
    assert run_rgaa(Test141(), context_factory(CAPTCHA)).status == Status.NEEDS_REVIEW


def test_141_ai_exception_gives_error(context_factory, run_rgaa):
    ai = services(alternative_analysis=RuntimeError("panne"))
    assert run_rgaa(Test141(), context_factory(CAPTCHA), ai).status == Status.ERROR


def test_141_captcha_detected_by_ai_profile(context_factory, run_rgaa):
    ai = services(image_profile=profile(captcha=True), alternative_analysis=alternative(relevant=False))
    assert run_rgaa(Test141(), context_factory('<img src="x.png" alt="x7Kp2">'), ai).status == Status.FAIL


def test_141_ordinary_image_is_not_applicable(context_factory, run_rgaa):
    ai = services(image_profile=profile(captcha=False))
    assert run_rgaa(Test141(), context_factory('<img src="x.png" alt="Logo">'), ai).status == Status.NOT_APPLICABLE
    ai.image_analyzer.analyze_alternative.assert_not_called()


def test_141_captcha_without_alternative_is_out_of_scope(context_factory, run_rgaa):
    html = '<img class="captcha" src="c.png">'
    assert run_rgaa(Test141(), context_factory(html), services()).status == Status.NOT_APPLICABLE


def test_143_captcha_image_button(context_factory, run_rgaa):
    html = '<input type="image" class="captcha" src="c.png" alt="Valider le code de sécurité">'
    assert run_rgaa(Test143(), context_factory(html), services()).status == Status.PASS
