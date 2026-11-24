"""Critère RGAA 11.3 : cohérence des étiquettes de champs de même fonction."""

from bs4 import BeautifulSoup

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_3 import Test1131, Test1132
from tests.ai_fakes import relevance, text_services

SAME = (
    '<label for="a">Courriel</label><input id="a" type="email" autocomplete="email">'
    '<label for="b">courriel</label><input id="b" type="email" autocomplete="email">'
)
DIFFERENT = (
    '<label for="a">Courriel</label><input id="a" autocomplete="email">'
    '<label for="b">Adresse e-mail</label><input id="b" autocomplete="email">'
)


def dom(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def test_1131_no_repeated_function_is_not_applicable(context_factory, run_rgaa):
    html = '<label for="a">Nom</label><input id="a" name="nom">'
    assert run_rgaa(Test1131(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_1131_identical_labels_pass_without_ai(context_factory, run_rgaa):
    ai = text_services()
    assert run_rgaa(Test1131(), context_factory(SAME), ai).status == Status.PASS
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_1131_different_labels_judged_coherent(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(True))
    assert run_rgaa(Test1131(), context_factory(DIFFERENT), ai).status == Status.PASS
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "label_consistency"
    assert items[0].text == "« Courriel » / « Adresse e-mail »"


def test_1131_different_labels_judged_incoherent(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    assert run_rgaa(Test1131(), context_factory(DIFFERENT), ai).status == Status.FAIL


def test_1131_low_confidence_no_ai_and_error(context_factory, run_rgaa):
    low = text_services(relevance_answer=relevance(False, confidence="low"))
    assert run_rgaa(Test1131(), context_factory(DIFFERENT), low).status == Status.NEEDS_REVIEW
    assert run_rgaa(Test1131(), context_factory(DIFFERENT)).status == Status.NEEDS_REVIEW
    broken = text_services(relevance_answer=RuntimeError("panne"))
    assert run_rgaa(Test1131(), context_factory(DIFFERENT), broken).status == Status.ERROR


def test_1131_missing_labels_are_left_to_11_1(context_factory, run_rgaa):
    html = '<input autocomplete="email"><label for="b">Courriel</label><input id="b" autocomplete="email">'
    assert run_rgaa(Test1131(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_1132_compares_labels_across_pages(context_factory, run_rgaa):
    context = context_factory("<p>Accueil</p>")
    context.page_doms = {
        "index.html": dom('<label for="a">Courriel</label><input id="a" autocomplete="email">'),
        "contact.html": dom('<label for="b">Téléphone</label><input id="b" autocomplete="email">'),
    }
    result = run_rgaa(Test1132(), context, text_services(relevance_answer=relevance(False)))
    assert result.status == Status.FAIL
    assert result.metadata["pages_analyzed"] == 2


def test_1132_identical_labels_across_pages_pass(context_factory, run_rgaa):
    context = context_factory("<p>Accueil</p>")
    page = '<label for="a">Courriel</label><input id="a" autocomplete="email">'
    context.page_doms = {"index.html": dom(page), "contact.html": dom(page)}
    assert run_rgaa(Test1132(), context, text_services()).status == Status.PASS


def test_1132_single_page_not_tested(context_factory, run_rgaa):
    context = context_factory(SAME)
    context.page_doms = {"index.html": context.dom}
    assert run_rgaa(Test1132(), context, text_services()).status == Status.NOT_TESTED


def test_1132_single_page_site_is_not_applicable(context_factory, run_rgaa):
    context = context_factory(SAME)
    context.page_doms = {"index.html": context.dom}
    context.site_inventory_complete = True
    assert run_rgaa(Test1132(), context, text_services()).status == Status.NOT_APPLICABLE
