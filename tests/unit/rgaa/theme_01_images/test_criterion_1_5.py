"""Critère RGAA 1.5 : solution d'accès alternative aux CAPTCHA."""

import pytest
from tests.unit.rgaa.theme_01_images.image_fakes import profile, services

from accessi_code.ai.schemas import RelevanceAnalysis
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_01_images.criterion_1_5 import Test151, Test152

CAPTCHA = '<form><img class="captcha" src="c.png" alt="Code de sécurité"></form>'
WITH_AUDIO = (
    '<form><img class="captcha" src="c.png" alt="Code de sécurité"><a href="captcha.mp3">Écouter le code</a></form>'
)


@pytest.mark.parametrize("cls", [Test151, Test152])
def test_no_captcha_is_not_applicable(cls, context_factory, run_rgaa):
    ai = services(image_profile=profile(captcha=False))
    assert run_rgaa(cls(), context_factory('<img src="a.png" alt="Logo">'), ai).status == Status.NOT_APPLICABLE


def test_151_captcha_without_any_alternative_fails(context_factory, run_rgaa):
    ai = services()
    assert run_rgaa(Test151(), context_factory(CAPTCHA), ai).status == Status.FAIL
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_151_relevant_alternative_passes(context_factory, run_rgaa):
    ai = services(relevance=[RelevanceAnalysis(True, "CAPTCHA audio.", confidence="high")])
    assert run_rgaa(Test151(), context_factory(WITH_AUDIO), ai).status == Status.PASS
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "captcha_alternative"
    assert items[0].text == "Écouter le code"


def test_151_irrelevant_alternative_fails(context_factory, run_rgaa):
    ai = services(relevance=[RelevanceAnalysis(False, "Recharge seulement l'image.", confidence="high")])
    assert run_rgaa(Test151(), context_factory(WITH_AUDIO), ai).status == Status.FAIL


def test_151_low_confidence_needs_review(context_factory, run_rgaa):
    ai = services(relevance=[RelevanceAnalysis(True, "?", confidence="low")])
    assert run_rgaa(Test151(), context_factory(WITH_AUDIO), ai).status == Status.NEEDS_REVIEW


def test_151_without_ai_needs_review(context_factory, run_rgaa):
    assert run_rgaa(Test151(), context_factory(WITH_AUDIO)).status == Status.NEEDS_REVIEW


def test_151_ai_exception_gives_error(context_factory, run_rgaa):
    ai = services(relevance=RuntimeError("panne"))
    assert run_rgaa(Test151(), context_factory(WITH_AUDIO), ai).status == Status.ERROR


def test_151_audio_element_is_a_candidate(context_factory, run_rgaa):
    html = '<form><img class="captcha" src="c.png" alt="Code"><audio src="code.mp3" controls></audio></form>'
    ai = services()
    assert run_rgaa(Test151(), context_factory(html), ai).status == Status.PASS


def test_152_captcha_image_button(context_factory, run_rgaa):
    html = '<form><input type="image" class="captcha" src="c.png" alt="Valider"></form>'
    assert run_rgaa(Test152(), context_factory(html), services()).status == Status.FAIL


def test_151_documented_evidence(context_factory, run_rgaa):
    context = context_factory(
        '<img id="c" class="captcha" src="c.png" alt="Code">',
        image_evidence={"img#c": {"verified": True, "accessible_captcha_alternative": True}},
    )
    assert run_rgaa(Test151(), context, services()).status == Status.PASS
