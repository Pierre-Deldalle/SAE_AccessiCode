"""Critère RGAA 1.8 : images texte remplaçables par du texte stylé."""

import pytest
from image_fakes import profile, services

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_01_images.criterion_1_8 import (
    Test181,
    Test182,
    Test183,
    Test184,
    Test185,
    Test186,
)

ALL = [Test181, Test182, Test183, Test184, Test185, Test186]
IMG = '<img src="promo.png" alt="Soldes -50 %">'
TEXT_IMAGE = profile(text=True, replaceable=True, text_content="Soldes -50 %")


@pytest.mark.parametrize("cls", ALL)
def test_no_element_is_not_applicable(cls, context_factory, run_rgaa):
    assert run_rgaa(cls(), context_factory("<p>Texte</p>"), services()).status == Status.NOT_APPLICABLE


def test_181_replaceable_text_image_fails(context_factory, run_rgaa):
    context = context_factory(f"<p>Offre</p>\n{IMG}")
    result = run_rgaa(Test181(), context, services(image_profile=TEXT_IMAGE))
    assert result.status == Status.FAIL
    assert "Soldes -50 %" in result.findings[0].message
    assert result.findings[0].line == 2
    assert result.findings[0].snippet == str(context.dom.img)


def test_181_image_without_text_is_not_applicable(context_factory, run_rgaa):
    ai = services(image_profile=profile(text=False))
    assert run_rgaa(Test181(), context_factory(IMG), ai).status == Status.NOT_APPLICABLE


def test_181_non_reproducible_text_passes(context_factory, run_rgaa):
    ai = services(image_profile=profile(text=True, replaceable=False))
    assert run_rgaa(Test181(), context_factory(IMG), ai).status == Status.PASS


def test_181_replacement_mechanism_passes(context_factory, run_rgaa):
    html = IMG + '<button type="button">Afficher en texte</button>'
    assert run_rgaa(Test181(), context_factory(html), services(image_profile=TEXT_IMAGE)).status == Status.PASS


def test_181_logo_is_a_special_case(context_factory, run_rgaa):
    ai = services(image_profile=TEXT_IMAGE)
    html = '<img class="logo" src="logo.png" alt="AccessiCode">'
    assert run_rgaa(Test181(), context_factory(html), ai).status == Status.NOT_APPLICABLE
    ai.image_analyzer.profile.assert_not_called()


def test_181_captcha_is_a_special_case(context_factory, run_rgaa):
    html = '<img class="captcha" src="c.png" alt="Code">'
    assert (
        run_rgaa(Test181(), context_factory(html), services(image_profile=TEXT_IMAGE)).status == Status.NOT_APPLICABLE
    )


def test_181_low_confidence_needs_review(context_factory, run_rgaa):
    ai = services(image_profile=profile(text=True, replaceable=True, confidence="low"))
    assert run_rgaa(Test181(), context_factory(IMG), ai).status == Status.NEEDS_REVIEW


def test_181_unknown_replaceability_needs_review(context_factory, run_rgaa):
    ai = services(image_profile=profile(text=True, replaceable=None))
    assert run_rgaa(Test181(), context_factory(IMG), ai).status == Status.NEEDS_REVIEW


def test_181_without_ai_needs_review(context_factory, run_rgaa):
    assert run_rgaa(Test181(), context_factory(IMG)).status == Status.NEEDS_REVIEW


def test_181_ai_exception_gives_error(context_factory, run_rgaa):
    assert run_rgaa(Test181(), context_factory(IMG), services(image_profile=RuntimeError("x"))).status == Status.ERROR


def test_186_svg_with_real_text_is_not_applicable(context_factory, run_rgaa):
    html = '<svg role="img" aria-label="Titre"><text x="0" y="10">Titre</text></svg>'
    assert (
        run_rgaa(Test186(), context_factory(html), services(image_profile=TEXT_IMAGE)).status == Status.NOT_APPLICABLE
    )


def test_186_svg_with_paths_is_evaluated(context_factory, run_rgaa):
    html = '<svg role="img" aria-label="Titre"><path d="M0 0"/></svg>'
    assert run_rgaa(Test186(), context_factory(html), services(image_profile=TEXT_IMAGE)).status == Status.FAIL


def test_182_image_button(context_factory, run_rgaa):
    html = '<input type="image" src="envoyer.png" alt="Envoyer">'
    assert run_rgaa(Test182(), context_factory(html), services(image_profile=TEXT_IMAGE)).status == Status.FAIL
