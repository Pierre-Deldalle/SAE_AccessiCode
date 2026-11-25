"""Critère RGAA 10.9 : information donnée uniquement par la forme, la taille ou la position (jugée par l'IA)."""

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_9 import (
    Test1091,
    Test1092,
    Test1093,
    Test1094,
)
from tests.ai_fakes import sensory, text_services

POSITION_TEXT = '<p id="consigne">Cliquez sur le bouton à droite pour valider.</p>'


def submitted(ai):
    kind, items = ai.sensory_analyzer.analyze_texts.call_args.args
    assert kind == "shape_size_position"
    return items


@pytest.mark.parametrize("test_class", [Test1091, Test1092, Test1093, Test1094])
def test_no_candidate_is_not_applicable(test_class, context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(test_class(), context_factory("<p>Bienvenue.</p>"), ai)
    assert result.status == Status.NOT_APPLICABLE
    ai.sensory_analyzer.analyze_texts.assert_not_called()


@pytest.mark.parametrize(
    "text",
    [
        "Appuyez sur le bouton rond.",
        "Voir la colonne de droite.",
        "Les informations ci-dessous sont importantes.",
        "Les éléments en gros caractères sont obligatoires.",
        "Utilisez la flèche pour continuer.",
    ],
)
def test_1091_shape_size_position_phrases_are_candidates(text, context_factory, run_rgaa):
    ai = text_services()
    run_rgaa(Test1091(), context_factory(f"<p>{text}</p>"), ai)
    assert submitted(ai)[0].text == text


@pytest.mark.parametrize(
    "text",
    [
        "Le premier rendez-vous a lieu avant midi, entre amis.",
        "Le tableau est en rouge.",
        "Nous sommes situés en haute montagne.",
    ],
)
def test_1091_common_words_and_colors_are_not_candidates(text, context_factory, run_rgaa):
    assert run_rgaa(Test1091(), context_factory(f"<p>{text}</p>"), text_services()).status == Status.NOT_APPLICABLE


def test_1091_expressions_and_context_are_kept(context_factory, run_rgaa):
    proposal = "Sélectionnez Payer pour valider."
    ai = text_services(sensory_answer=sensory(relies_only=True, suggestion=proposal))
    html = f"<form><h2>Paiement</h2>\n{POSITION_TEXT}<button>Payer</button></form>"
    result = run_rgaa(Test1091(), context_factory(html), ai)
    assert "Titre de la section : Paiement" in submitted(ai)[0].context
    assert result.status == Status.FAIL
    assert result.findings[0].element == "p#consigne"
    assert result.findings[0].evidence["expressions"] == ["à droite"]
    assert (result.findings[0].line, result.findings[0].snippet) == (2, POSITION_TEXT)
    assert result.findings[0].recommendation.endswith(f" Proposition : « {proposal} ».")


def test_1091_other_means_passes(context_factory, run_rgaa):
    ai = text_services(sensory_answer=sensory(relies_only=False, suggestion="Sélectionnez Payer."))
    result = run_rgaa(Test1091(), context_factory(POSITION_TEXT), ai)
    assert result.status == Status.PASS
    assert result.findings == []


def test_1091_no_information_is_not_applicable(context_factory, run_rgaa):
    ai = text_services(sensory_answer=sensory(conveys=False))
    assert run_rgaa(Test1091(), context_factory(POSITION_TEXT), ai).status == Status.NOT_APPLICABLE


def test_1091_hidden_text_is_ignored(context_factory, run_rgaa):
    html = "<div hidden><p>Cliquez à droite.</p></div>"
    assert run_rgaa(Test1091(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_1092_image_goes_to_vlm(context_factory, run_rgaa):
    proposal = "Guichet des inscriptions à l’entrée nord."
    ai = text_services(sensory_image_answer=sensory(relies_only=True, suggestion=proposal))
    result = run_rgaa(Test1092(), context_factory('\n<img src="plan.png" alt="Plan d\'accès">'), ai)
    assert result.status == Status.FAIL
    kind, _image = ai.sensory_analyzer.analyze_image.call_args.args
    assert kind == "shape_size_position"
    [finding] = result.findings
    assert (finding.line, finding.snippet) == (2, '<img src="plan.png" alt="Plan d\'accès">')
    assert finding.recommendation.endswith(f" Proposition : « {proposal} ».")


def test_1093_audio_and_video_need_review(context_factory, run_rgaa):
    html = '<video src="a.mp4"></video>\n<audio src="b.mp3"></audio>'
    result = run_rgaa(Test1093(), context_factory(html), text_services())
    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 2
    assert [(finding.line, finding.snippet) for finding in result.findings] == [
        (1, '<video src="a.mp4"></video>'),
        (2, '<audio src="b.mp3"></audio>'),
    ]


def test_1094_object_needs_review(context_factory, run_rgaa):
    html = '<embed src="anim.swf" type="application/x-shockwave-flash">'
    assert run_rgaa(Test1094(), context_factory(html), text_services()).status == Status.NEEDS_REVIEW


def test_without_ai_needs_review(context_factory, run_rgaa):
    result = run_rgaa(Test1091(), context_factory(POSITION_TEXT))
    assert result.status == Status.NEEDS_REVIEW
    assert "IA n'est pas disponible" in result.findings[0].message


def test_low_confidence_needs_review(context_factory, run_rgaa):
    ai = text_services(sensory_answer=sensory(relies_only=True, confidence="low", suggestion="Sélectionnez Payer."))
    result = run_rgaa(Test1091(), context_factory(POSITION_TEXT), ai)
    assert result.status == Status.NEEDS_REVIEW
    [finding] = result.findings
    assert "Proposition :" not in finding.recommendation
    assert "suggestion" not in finding.evidence["analysis"]


def test_ai_exception_gives_error(context_factory, run_rgaa):
    ai = text_services(sensory_answer=RuntimeError("panne"))
    result = run_rgaa(Test1091(), context_factory(f"\n{POSITION_TEXT}"), ai)
    assert result.status == Status.ERROR
    [finding] = result.findings
    assert (finding.line, finding.snippet) == (2, POSITION_TEXT)
