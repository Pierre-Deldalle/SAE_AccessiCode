"""Critère RGAA 11.8 : regroupement des items de listes de choix."""

import pytest
from ai_fakes import relevance, text_services

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_8 import Test1181, Test1182, Test1183

MIXED = "<select><option>Paris</option><option>Lyon</option><option>Madrid</option><option>Séville</option></select>"
GROUPED = (
    '<select><optgroup label="France"><option>Paris</option><option>Lyon</option></optgroup>'
    '<optgroup label="Espagne"><option>Madrid</option></optgroup></select>'
)


@pytest.mark.parametrize("cls", [Test1181, Test1182, Test1183])
def test_no_list_is_not_applicable(cls, context_factory, run_rgaa):
    assert run_rgaa(cls(), context_factory("<p>Texte</p>"), text_services()).status == Status.NOT_APPLICABLE


def test_1181_short_list_passes_without_ai(context_factory, run_rgaa):
    ai = text_services()
    html = "<select><option>Oui</option><option>Non</option></select>"
    assert run_rgaa(Test1181(), context_factory(html), ai).status == Status.PASS
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_1181_grouped_list_passes(context_factory, run_rgaa):
    assert run_rgaa(Test1181(), context_factory(GROUPED), text_services()).status == Status.PASS


def test_1181_categories_without_optgroup_fail(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    assert run_rgaa(Test1181(), context_factory(MIXED), ai).status == Status.FAIL
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "option_grouping"
    assert "- Madrid" in items[0].text


def test_1181_homogeneous_options_pass(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(True))
    assert run_rgaa(Test1181(), context_factory(MIXED), ai).status == Status.PASS


def test_1181_listbox_needing_groups_fails(context_factory, run_rgaa):
    html = '<ul role="listbox">' + "".join(f'<li role="option">{c}</li>' for c in "ABCDE") + "</ul>"
    result = run_rgaa(Test1181(), context_factory(html), text_services(relevance_answer=relevance(False)))
    assert result.status == Status.FAIL
    assert "listbox" in result.findings[0].message


def test_1181_low_confidence_no_ai_and_error(context_factory, run_rgaa):
    low = text_services(relevance_answer=relevance(False, confidence="low"))
    assert run_rgaa(Test1181(), context_factory(MIXED), low).status == Status.NEEDS_REVIEW
    assert run_rgaa(Test1181(), context_factory(MIXED)).status == Status.NEEDS_REVIEW
    broken = text_services(relevance_answer=RuntimeError("panne"))
    assert run_rgaa(Test1181(), context_factory(MIXED), broken).status == Status.ERROR


def test_1182_optgroup_label(context_factory, run_rgaa):
    assert run_rgaa(Test1182(), context_factory(GROUPED)).status == Status.PASS
    html = "<select><optgroup><option>A</option></optgroup></select>"
    assert run_rgaa(Test1182(), context_factory(html)).status == Status.FAIL


def test_1183_relevant_and_irrelevant_labels(context_factory, run_rgaa):
    ok = text_services(relevance_answer=relevance(True))
    ko = text_services(relevance_answer=[relevance(True), relevance(False)])
    assert run_rgaa(Test1183(), context_factory(GROUPED), ok).status == Status.PASS
    assert run_rgaa(Test1183(), context_factory(GROUPED), ko).status == Status.FAIL
    kind, items = ok.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "optgroup_label"
    assert items[0].text == "France"
    assert "- Paris" in items[0].context


def test_1183_empty_label_fails_without_ai(context_factory, run_rgaa):
    ai = text_services()
    html = '<select><optgroup label=" "><option>A</option></optgroup></select>'
    assert run_rgaa(Test1183(), context_factory(html), ai).status == Status.FAIL
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()
