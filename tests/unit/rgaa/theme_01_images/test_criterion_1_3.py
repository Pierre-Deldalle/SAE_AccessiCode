"""Critère RGAA 1.3 : pertinence et concision des alternatives textuelles."""

import pytest
from tests.unit.rgaa.theme_01_images.image_fakes import alternative, profile, services

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_01_images.criterion_1_3 import (
    Test131,
    Test132,
    Test133,
    Test134,
    Test135,
    Test136,
    Test137,
    Test138,
    Test139,
)

ALL = [Test131, Test132, Test133, Test134, Test135, Test136, Test137, Test138, Test139]
IMG = '<img src="ventes.png" alt="Ventes 2025">'


@pytest.mark.parametrize("cls", ALL)
def test_no_element_is_not_applicable(cls, context_factory, run_rgaa):
    assert run_rgaa(cls(), context_factory("<p>Texte</p>"), services()).status == Status.NOT_APPLICABLE


def test_131_relevant_alternative_passes(context_factory, run_rgaa):
    ai = services(alternative_analysis=alternative(relevant=True))
    assert run_rgaa(Test131(), context_factory(IMG), ai).status == Status.PASS
    kwargs = ai.image_analyzer.analyze_alternative.await_args.kwargs
    assert kwargs["mode"] == "alternative"
    assert "alt : Ventes 2025" in kwargs["alternative"]
    assert kwargs["image"] is not None  # le fichier local est transmis au VLM


def test_131_irrelevant_alternative_fails(context_factory, run_rgaa):
    ai = services(alternative_analysis=alternative(relevant=False))
    result = run_rgaa(Test131(), context_factory('<img src="ventes.png" alt="image1.png">'), ai)
    assert result.status == Status.FAIL
    assert result.findings[0].evidence["alternatives"] == {"alt": "image1.png"}


def test_131_low_confidence_needs_review(context_factory, run_rgaa):
    ai = services(alternative_analysis=alternative(relevant=False, confidence="low"))
    assert run_rgaa(Test131(), context_factory(IMG), ai).status == Status.NEEDS_REVIEW


def test_131_unknown_relevance_needs_review(context_factory, run_rgaa):
    ai = services(alternative_analysis=alternative(relevant=None))
    assert run_rgaa(Test131(), context_factory(IMG), ai).status == Status.NEEDS_REVIEW


def test_131_without_ai_needs_review(context_factory, run_rgaa):
    assert run_rgaa(Test131(), context_factory(IMG)).status == Status.NEEDS_REVIEW


def test_131_ai_exception_gives_error(context_factory, run_rgaa):
    ai = services(alternative_analysis=RuntimeError("panne"))
    assert run_rgaa(Test131(), context_factory(IMG), ai).status == Status.ERROR


def test_131_decorative_image_is_not_applicable(context_factory, run_rgaa):
    ai = services(image_profile=profile(informative=False))
    assert run_rgaa(Test131(), context_factory(IMG), ai).status == Status.NOT_APPLICABLE
    ai.image_analyzer.analyze_alternative.assert_not_called()


def test_131_captcha_is_left_to_criterion_1_4(context_factory, run_rgaa):
    ai = services()
    html = '<img class="captcha" src="c.png" alt="Code de sécurité">'
    assert run_rgaa(Test131(), context_factory(html), ai).status == Status.NOT_APPLICABLE
    ai.image_analyzer.analyze_alternative.assert_not_called()


def test_131_image_without_alternative_is_out_of_scope(context_factory, run_rgaa):
    assert run_rgaa(Test131(), context_factory('<img src="a.png">'), services()).status == Status.NOT_APPLICABLE


def test_131_mixed_results(context_factory, run_rgaa):
    ai = services()
    ai.image_analyzer.analyze_alternative.side_effect = [alternative(relevant=True), alternative(relevant=False)]
    html = '<img src="a.png" alt="Graphique des ventes"><img src="b.png" alt="photo"></p>'
    result = run_rgaa(Test131(), context_factory(html), ai)
    assert result.status == Status.FAIL
    assert result.metadata["statuses"]["pass"] == 1


def test_131_verified_evidence_has_priority(context_factory, run_rgaa):
    ai = services(alternative_analysis=alternative(relevant=True))
    context = context_factory(
        '<img id="v" src="a.png" alt="Ventes">',
        image_evidence={"img#v": {"verified": True, "information_bearing": True, "alternative_relevant": False}},
    )
    assert run_rgaa(Test131(), context, ai).status == Status.FAIL
    ai.image_analyzer.analyze_alternative.assert_not_called()


def test_136_svg_title_is_evaluated_without_image_file(context_factory, run_rgaa):
    ai = services()
    html = '<svg role="img"><title>Plan d\'accès</title></svg>'
    assert run_rgaa(Test136(), context_factory(html), ai).status == Status.PASS
    kwargs = ai.image_analyzer.analyze_alternative.await_args.kwargs
    assert kwargs["image"] is None
    assert "svg-title : Plan d'accès" in kwargs["alternative"]


def test_133_image_button_is_informative_even_if_profile_says_otherwise(context_factory, run_rgaa):
    # Le profil sert seulement à écarter les CAPTCHA : un bouton image est toujours porteur d'information.
    ai = services(image_profile=profile(informative=False))
    html = '<input type="image" src="ok.png" alt="Rechercher">'
    assert run_rgaa(Test133(), context_factory(html), ai).status == Status.PASS
    ai.image_analyzer.profile.assert_awaited_once()
    ai.image_analyzer.analyze_alternative.assert_awaited_once()


def test_138_canvas_restitution_needs_review(context_factory, run_rgaa):
    result = run_rgaa(Test138(), context_factory("<canvas>Ventes en hausse</canvas>"), services())
    assert result.status == Status.NEEDS_REVIEW
    assert "lecteur d'écran" in result.findings[0].message


def test_138_documented_restitution(context_factory, run_rgaa):
    context = context_factory(
        '<canvas id="c">Ventes</canvas>', image_evidence={"canvas#c": {"verified": True, "correctly_exposed": True}}
    )
    assert run_rgaa(Test138(), context, services()).status == Status.PASS


def test_139_concise_alternative(context_factory, run_rgaa):
    ok = services(alternative_analysis=alternative(concise=True))
    ko = services(alternative_analysis=alternative(concise=False))
    assert run_rgaa(Test139(), context_factory(IMG), ok).status == Status.PASS
    result = run_rgaa(Test139(), context_factory(IMG), ko)
    assert result.status == Status.FAIL
    assert "courte et concise" in result.findings[0].message
