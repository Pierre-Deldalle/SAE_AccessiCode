"""Critère RGAA 11.7 : pertinence des légendes de regroupement."""

from ai_fakes import relevance, text_services

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_7 import Test1171

GROUP = (
    "<fieldset><legend>Adresse de livraison</legend>"
    "<label for='r'>Rue</label><input id='r'><label for='v'>Ville</label><input id='v'></fieldset>"
)


def test_no_legend_is_not_applicable(context_factory, run_rgaa):
    html = "<fieldset><input><input></fieldset>"
    assert run_rgaa(Test1171(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_relevant_legend_passes(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(True))
    assert run_rgaa(Test1171(), context_factory(GROUP), ai).status == Status.PASS
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "fieldset_legend"
    assert items[0].text == "Adresse de livraison"
    assert "Rue, Ville" in items[0].context


def test_irrelevant_legend_fails(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    assert run_rgaa(Test1171(), context_factory(GROUP), ai).status == Status.FAIL


def test_low_confidence_no_ai_and_error(context_factory, run_rgaa):
    low = text_services(relevance_answer=relevance(True, confidence="low"))
    assert run_rgaa(Test1171(), context_factory(GROUP), low).status == Status.NEEDS_REVIEW
    assert run_rgaa(Test1171(), context_factory(GROUP)).status == Status.NEEDS_REVIEW
    broken = text_services(relevance_answer=RuntimeError("panne"))
    assert run_rgaa(Test1171(), context_factory(GROUP), broken).status == Status.ERROR
