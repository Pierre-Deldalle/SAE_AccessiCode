"""Critère RGAA 8.8 : code de langue valide (sans IA) et pertinent (IA)."""

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_8 import Test881
from tests.ai_fakes import relevance, text_services


def page(body: str) -> str:
    return f'<html lang="fr"><body>{body}</body></html>'


def test_no_language_change_is_not_applicable(context_factory, run_rgaa):
    result = run_rgaa(Test881(), context_factory(page("<p>Bonjour</p>")), text_services())
    assert result.status == Status.NOT_APPLICABLE


def test_empty_element_is_ignored(context_factory, run_rgaa):
    result = run_rgaa(Test881(), context_factory(page('<span lang="en"></span>')), text_services())
    assert result.status == Status.NOT_APPLICABLE


@pytest.mark.parametrize("code", ["english", "e", "xx", ""])
def test_invalid_code_fails_without_ai(code, context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test881(), context_factory(page(f'<span id="c" lang="{code}">Hello</span>')), ai)
    assert result.status == Status.FAIL
    assert "n'est pas valide" in result.findings[0].message
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_valid_code_is_judged(context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test881(), context_factory(page('<span lang="en-GB">Hello world</span>')), ai)
    assert result.status == Status.PASS
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "language_change"
    assert items[0].text == "Hello world"
    assert items[0].details == {"declared_language": "en-GB"}


def test_nested_change_is_masked(context_factory, run_rgaa):
    ai = text_services()
    html = page('<p lang="en">Hello <span lang="de">Guten Tag</span> friends</p>')
    run_rgaa(Test881(), context_factory(html), ai)
    _, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert [item.text for item in items] == ["Hello [passage balisé] friends", "Guten Tag"]


def test_irrelevant_code_fails(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    result = run_rgaa(Test881(), context_factory(page('<span lang="en">Hola amigos</span>')), ai)
    assert result.status == Status.FAIL
    assert "ne correspond pas" in result.findings[0].message


def test_html_lang_is_not_a_change(context_factory, run_rgaa):
    assert run_rgaa(Test881(), context_factory(page("<p>Texte</p>")), text_services()).status == (Status.NOT_APPLICABLE)


def test_without_ai_needs_review(context_factory, run_rgaa):
    result = run_rgaa(Test881(), context_factory(page('<span lang="en">Hello</span>')))
    assert result.status == Status.NEEDS_REVIEW


def test_ai_exception_gives_error(context_factory, run_rgaa):
    ai = text_services(relevance_answer=RuntimeError("panne"))
    result = run_rgaa(Test881(), context_factory(page('<span lang="en">Hello</span>')), ai)
    assert result.status == Status.ERROR
