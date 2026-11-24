"""Critère RGAA 9.4 : citations."""

import pytest
from ai_fakes import structure, text_services

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_09_structuration_information.criterion_9_4 import Test941, Test942

INLINE = "<p>Comme le disait la directrice, « l'accessibilité profite à tout le monde », lors du salon.</p>"
BLOCK = "<p>« Nous avons rendu notre site accessible en trois mois grâce à un audit complet et une formation. »</p>"


@pytest.mark.parametrize("cls", [Test941, Test942])
def test_no_quote_is_not_applicable(cls, context_factory, run_rgaa):
    assert run_rgaa(cls(), context_factory("<p>Texte</p>"), text_services()).status == Status.NOT_APPLICABLE


def test_941_q_element_passes(context_factory, run_rgaa):
    assert (
        run_rgaa(Test941(), context_factory("<p>Il a dit <q>bonjour</q>.</p>"), text_services()).status == Status.PASS
    )


def test_941_empty_q_fails(context_factory, run_rgaa):
    assert run_rgaa(Test941(), context_factory("<p><q></q></p>"), text_services()).status == Status.FAIL


def test_941_unmarked_inline_quote_confirmed_fails(context_factory, run_rgaa):
    ai = text_services(structure_answer=structure(True))
    result = run_rgaa(Test941(), context_factory(INLINE), ai)
    assert result.status == Status.FAIL
    kind, items = ai.structure_analyzer.classify_candidates.call_args.args
    assert kind == "quote"
    assert items[0].text == "l'accessibilité profite à tout le monde"


def test_941_quotes_that_are_not_a_citation(context_factory, run_rgaa):
    ai = text_services(structure_answer=structure(False))
    assert run_rgaa(Test941(), context_factory(INLINE), ai).status == Status.NOT_APPLICABLE


def test_941_without_ai_and_error(context_factory, run_rgaa):
    assert run_rgaa(Test941(), context_factory(INLINE)).status == Status.NEEDS_REVIEW
    broken = text_services(structure_answer=RuntimeError("panne"))
    assert run_rgaa(Test941(), context_factory(INLINE), broken).status == Status.ERROR


def test_942_blockquote_passes(context_factory, run_rgaa):
    html = "<blockquote><p>Une longue citation.</p></blockquote>"
    assert run_rgaa(Test942(), context_factory(html), text_services()).status == Status.PASS


def test_942_empty_blockquote_fails(context_factory, run_rgaa):
    assert run_rgaa(Test942(), context_factory("<blockquote></blockquote>"), text_services()).status == Status.FAIL


def test_942_unmarked_block_quote(context_factory, run_rgaa):
    ai = text_services(structure_answer=structure(True))
    assert run_rgaa(Test942(), context_factory(BLOCK), ai).status == Status.FAIL
    # Un bloc entièrement cité ne relève pas de 9.4.1.
    assert run_rgaa(Test941(), context_factory(BLOCK), ai).status == Status.NOT_APPLICABLE


def test_942_quote_class(context_factory, run_rgaa):
    html = '<div class="temoignage">Grâce à AccessiCode, notre équipe a appris à corriger ses pages en autonomie.</div>'
    ai = text_services(structure_answer=structure(True, confidence="low"))
    assert run_rgaa(Test942(), context_factory(html), ai).status == Status.NEEDS_REVIEW


# ---- Emplacement des observations ------------------------------------


def test_941_empty_q_is_located(context_factory, run_rgaa):
    finding = run_rgaa(Test941(), context_factory("<p>Texte</p>\n<p><q></q></p>"), text_services()).findings[0]
    assert (finding.line, finding.snippet) == (2, "<q></q>")


def test_941_unmarked_inline_quote_is_located(context_factory, run_rgaa):
    ai = text_services(structure_answer=structure(True))
    finding = run_rgaa(Test941(), context_factory("<h1>Salon</h1>\n" + INLINE), ai).findings[0]
    assert (finding.line, finding.snippet) == (2, INLINE)


def test_942_empty_blockquote_is_located(context_factory, run_rgaa):
    html = "<p>Texte</p>\n<blockquote></blockquote>"
    finding = run_rgaa(Test942(), context_factory(html), text_services()).findings[0]
    assert (finding.line, finding.snippet) == (2, "<blockquote></blockquote>")


def test_942_unmarked_block_quote_is_located(context_factory, run_rgaa):
    ai = text_services(structure_answer=structure(True))
    finding = run_rgaa(Test942(), context_factory("<h1>Avis</h1>\n" + BLOCK), ai).findings[0]
    assert (finding.line, finding.snippet) == (2, BLOCK)


# ---- Corrections proposées -------------------------------------------


def test_941_example_marks_the_real_quote(context_factory, run_rgaa):
    finding = run_rgaa(Test941(), context_factory(INLINE), text_services(structure_answer=structure(True))).findings[0]
    assert finding.recommendation == (
        "Baliser chaque citation courte avec <q>. Exemple : « l'accessibilité profite à tout le monde » → "
        "<q>l'accessibilité profite à tout le monde</q>"
    )


def test_941_example_keeps_straight_quotes(context_factory, run_rgaa):
    html = '<p>Il a dit "ceci est une phrase citée par quelqu\'un" hier soir au salon de Lille.</p>'
    finding = run_rgaa(Test941(), context_factory(html), text_services(structure_answer=structure(True))).findings[0]
    assert finding.recommendation.endswith(
        "Exemple : \"ceci est une phrase citée par quelqu'un\" → <q>ceci est une phrase citée par quelqu'un</q>"
    )


def test_942_example_wraps_the_block(context_factory, run_rgaa):
    finding = run_rgaa(Test942(), context_factory(BLOCK), text_services(structure_answer=structure(True))).findings[0]
    assert finding.recommendation.endswith(
        "Exemple : <p>« Nous avons rendu notre site accessible en trois mois grâc…</p> → "
        "<blockquote><p>« Nous avons rendu notre site accessible en trois mois grâc…</p></blockquote>"
    )


def test_no_quote_example_when_unsure_or_for_an_empty_tag(context_factory, run_rgaa):
    assert "Exemple" not in run_rgaa(Test941(), context_factory(INLINE)).findings[0].recommendation
    empty = run_rgaa(Test942(), context_factory("<blockquote></blockquote>"), text_services()).findings[0]
    assert "Exemple" not in empty.recommendation
