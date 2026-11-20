"""Critère RGAA 5.5 : pertinence du titre des tableaux de données."""

from ai_fakes import relevance, text_services

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_5 import Test551

ROWS = "<tr><th>Ville</th><th>Habitants</th></tr><tr><td>Lille</td><td>236 000</td></tr>"
CAPTIONED = f"<table id='pop'><caption>Population des villes du Nord</caption>{ROWS}</table>"


def test_table_without_title_is_not_applicable(context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test551(), context_factory(f"<table>{ROWS}</table>"), ai)
    assert result.status == Status.NOT_APPLICABLE
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_presentation_table_is_ignored(context_factory, run_rgaa):
    html = '<table role="presentation" title="Mise en page"><tr><td>A</td></tr></table>'
    assert run_rgaa(Test551(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_relevant_caption_passes(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(True))
    result = run_rgaa(Test551(), context_factory(CAPTIONED), ai)
    assert result.status == Status.PASS
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "table_title"
    assert items[0].text == "Population des villes du Nord"
    assert items[0].details == {"source": "caption"}
    assert "Ville | Habitants" in items[0].context


def test_every_title_mechanism_is_judged(context_factory, run_rgaa):
    html = (
        "<h3 id='t'>Population 2024</h3>"
        f"<table title='Villes' aria-label='Population par ville' aria-labelledby='t'>{ROWS}</table>"
    )
    ai = text_services()
    run_rgaa(Test551(), context_factory(html), ai)
    _, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert [item.details["source"] for item in items] == ["title", "aria-label", "aria-labelledby"]
    assert items[2].text == "Population 2024"


def test_irrelevant_title_fails(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    html = CAPTIONED.replace("Population des villes du Nord", "Tableau")
    result = run_rgaa(Test551(), context_factory(html), ai)
    assert result.status == Status.FAIL
    assert result.findings[0].element == "table#pop"
    assert "« Tableau » (caption) n'est pas pertinent" in result.findings[0].message


def test_low_confidence_needs_review(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(True, confidence="low"))
    assert run_rgaa(Test551(), context_factory(CAPTIONED), ai).status == Status.NEEDS_REVIEW


def test_unknown_relevance_needs_review(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(None))
    assert run_rgaa(Test551(), context_factory(CAPTIONED), ai).status == Status.NEEDS_REVIEW


def test_without_ai_needs_review(context_factory, run_rgaa):
    assert run_rgaa(Test551(), context_factory(CAPTIONED)).status == Status.NEEDS_REVIEW


def test_ai_exception_gives_error(context_factory, run_rgaa):
    ai = text_services(relevance_answer=RuntimeError("panne"))
    assert run_rgaa(Test551(), context_factory(CAPTIONED), ai).status == Status.ERROR


def test_mixed_results(context_factory, run_rgaa):
    html = CAPTIONED + f"<table title='Données'>{ROWS}</table>"
    ai = text_services(relevance_answer=[relevance(True), relevance(False)])
    result = run_rgaa(Test551(), context_factory(html), ai)
    assert result.status == Status.FAIL
    assert len(result.findings) == 1
