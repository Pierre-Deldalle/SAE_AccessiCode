"""Critère RGAA 11.11 : suggestions de correction des erreurs de saisie."""

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_11 import Test11111, Test11112
from tests.ai_fakes import relevance, text_services

ERROR = (
    "<form><label for='d'>Date</label><input id='d' type='date' aria-invalid='true' aria-describedby='e'>"
    "<p id='e' role='alert'>Erreur : date invalide</p></form>"
)


@pytest.mark.parametrize("cls", [Test11111, Test11112])
def test_no_error_message_is_not_applicable(cls, context_factory, run_rgaa):
    html = "<form><label for='d'>Date</label><input id='d' type='date'></form>"
    assert run_rgaa(cls(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


@pytest.mark.parametrize(
    ("cls", "kind"), [(Test11111, "error_suggestion_format"), (Test11112, "error_suggestion_example")]
)
def test_suggestion_judged_by_ai(cls, kind, context_factory, run_rgaa):
    ok = text_services(relevance_answer=relevance(True))
    assert run_rgaa(cls(), context_factory(ERROR), ok).status == Status.PASS
    called_kind, items = ok.text_relevance_analyzer.analyze_relevance.call_args.args
    assert called_kind == kind
    assert items[0].text == "Erreur : date invalide"
    ko = text_services(relevance_answer=relevance(False))
    assert run_rgaa(cls(), context_factory(ERROR), ko).status == Status.FAIL


def test_error_message_without_aria_invalid_is_found(context_factory, run_rgaa):
    html = "<form><input aria-label='Code'><span class='error'>Code invalide</span></form>"
    assert run_rgaa(Test11111(), context_factory(html), text_services()).status == Status.PASS


def test_11111_pattern_with_title_passes_without_ai(context_factory, run_rgaa):
    ai = text_services()
    html = "<form><input aria-label='Code postal' pattern='[0-9]{5}' title='5 chiffres, ex. 59000'></form>"
    assert run_rgaa(Test11111(), context_factory(html), ai).status == Status.PASS
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_low_confidence_no_ai_and_error(context_factory, run_rgaa):
    low = text_services(relevance_answer=relevance(True, confidence="low"))
    assert run_rgaa(Test11111(), context_factory(ERROR), low).status == Status.NEEDS_REVIEW
    assert run_rgaa(Test11111(), context_factory(ERROR)).status == Status.NEEDS_REVIEW
    broken = text_services(relevance_answer=RuntimeError("panne"))
    assert run_rgaa(Test11111(), context_factory(ERROR), broken).status == Status.ERROR


def test_fail_gives_line_and_snippet(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    finding = run_rgaa(Test11112(), context_factory(ERROR.replace("<input", "\n<input")), ai).findings[0]
    assert finding.line == 2
    assert finding.snippet.startswith('<input id="d" type="date"')


def test_ai_suggestion_is_proposed_on_fail(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False, suggestion="Erreur : date invalide, format jj/mm/aaaa."))
    finding = run_rgaa(Test11112(), context_factory(ERROR), ai).findings[0]
    assert finding.recommendation.endswith("Proposition : « Erreur : date invalide, format jj/mm/aaaa. ».")
