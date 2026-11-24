"""Critère RGAA 5.2 : pertinence du résumé des tableaux de données complexes."""

from tests.ai_fakes import relevance, text_services

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_2 import Test521

HEADERS = """
    <thead>
        <tr><th rowspan="2" scope="col">Produit</th><th colspan="2" scope="colgroup">Semestre</th></tr>
        <tr><th scope="col">S1</th><th scope="col">S2</th></tr>
    </thead>
    <tbody><tr><th scope="row">Ordinateurs</th><td>150</td><td>200</td></tr></tbody>
"""
COMPLEX = f"<table id='ventes'><caption>Ventes par produit, puis par semestre en colonnes</caption>{HEADERS}</table>"
DESCRIBED = (
    "<p id='res'>Chaque ligne est un produit ; les colonnes regroupent les deux semestres.</p>"
    f"<table aria-describedby='res'>{HEADERS}</table>"
)


def test_simple_table_is_not_applicable(context_factory, run_rgaa):
    html = "<table><caption>Liste</caption><tr><th>Nom</th></tr><tr><td>A</td></tr></table>"
    assert run_rgaa(Test521(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_complex_table_without_summary_is_not_applicable(context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test521(), context_factory(f"<table>{HEADERS}</table>"), ai)
    assert result.status == Status.NOT_APPLICABLE
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_relevant_summary_passes(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(True))
    result = run_rgaa(Test521(), context_factory(COMPLEX), ai)
    assert result.status == Status.PASS
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "table_summary"
    assert "Ventes par produit" in items[0].text
    assert "Produit | Semestre" in items[0].context


def test_described_summary_is_submitted(context_factory, run_rgaa):
    ai = text_services()
    run_rgaa(Test521(), context_factory(DESCRIBED), ai)
    _, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert items[0].text.startswith("aria-describedby : Chaque ligne")


def test_legacy_summary_attribute_only_outside_html5(context_factory, run_rgaa):
    html = f'<table summary="Produits en lignes, semestres en colonnes">{HEADERS}</table>'
    html5 = run_rgaa(Test521(), context_factory("<!DOCTYPE html>" + html), text_services())
    assert html5.status == Status.NOT_APPLICABLE
    legacy = run_rgaa(Test521(), context_factory(html, doctype=None), text_services())
    assert legacy.status == Status.PASS


def test_irrelevant_summary_fails(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    result = run_rgaa(Test521(), context_factory(COMPLEX), ai)
    assert result.status == Status.FAIL
    assert result.findings[0].element == "table#ventes"
    assert "n'est pas pertinent" in result.findings[0].message


def test_low_confidence_needs_review(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False, confidence="low"))
    assert run_rgaa(Test521(), context_factory(COMPLEX), ai).status == Status.NEEDS_REVIEW


def test_unknown_relevance_needs_review(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(None))
    assert run_rgaa(Test521(), context_factory(COMPLEX), ai).status == Status.NEEDS_REVIEW


def test_without_ai_needs_review(context_factory, run_rgaa):
    result = run_rgaa(Test521(), context_factory(COMPLEX))
    assert result.status == Status.NEEDS_REVIEW
    assert "IA n'est pas disponible" in result.findings[0].message


def test_ai_exception_gives_error(context_factory, run_rgaa):
    ai = text_services(relevance_answer=RuntimeError("panne"))
    assert run_rgaa(Test521(), context_factory(COMPLEX), ai).status == Status.ERROR


def test_mixed_results(context_factory, run_rgaa):
    ai = text_services(relevance_answer=[relevance(True), relevance(False)])
    result = run_rgaa(Test521(), context_factory(COMPLEX + DESCRIBED), ai)
    assert result.status == Status.FAIL
    assert result.metadata["statuses"]["pass"] == 1
    assert result.metadata["statuses"]["fail"] == 1
