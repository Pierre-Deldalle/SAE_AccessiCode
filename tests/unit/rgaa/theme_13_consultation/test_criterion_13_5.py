"""Critères RGAA 13.5 et 13.6 : contenus cryptiques (jugés par l'IA)."""

import asyncio

import pytest
from tests.ai_fakes import relevance, text_services
from bs4 import BeautifulSoup

from accessi_code.analysis.cryptic import ASCII_ART_KIND, EMOTICON_KIND, SYNTAX_KIND, find_cryptic_contents
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_5 import Test1351
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_6 import Test1361

ASCII_ART = "<pre>\n  /\\_/\\   ##\n ( o.o )  ==\n  > ^ <  ~~**\n /|   |\\ //\\\\\n</pre>"


def _kinds(html: str) -> list[tuple[str, str]]:
    return [(item.kind, item.text) for item in find_cryptic_contents(BeautifulSoup(html, "html.parser"))]


def test_detection_of_cryptic_contents():
    assert _kinds("<p>Merci :-) et à bientôt ;)</p>") == [(EMOTICON_KIND, ":-)"), (EMOTICON_KIND, ";)")]
    assert _kinds("<p>Bonne soirée @+</p>") == [(SYNTAX_KIND, "@+")]
    assert _kinds(ASCII_ART)[0][0] == ASCII_ART_KIND


@pytest.mark.parametrize(
    "html",
    [
        "<a href='r.pdf'>Rapport annuel (PDF, 2 Mo)</a>",
        "<p>La SNCF et la RATP. Prix TTC : 10 €. Voir l'annexe x)</p>",
        "<p>Horaires : 9h-12h (sauf lundi).</p>",
        "<p>Lien : https://exemple.fr/page</p>",
        "<pre><code>if (a) { b(); }</code></pre>",
    ],
)
def test_ordinary_text_is_not_cryptic(html):
    assert _kinds(html) == []


# 13.5.1 ---------------------------------------------------------------------


def test_1351_no_cryptic_content_is_not_applicable(context_factory, run_rgaa):
    html = "<p>La SNCF publie son rapport (PDF).</p>"
    assert run_rgaa(Test1351(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_1351_title_passes_without_ai(context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test1351(), context_factory('<p>Merci <span title="sourire">:-)</span></p>'), ai)
    assert result.status == Status.PASS
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_1351_context_is_judged_by_ai(context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test1351(), context_factory("<p>Résultat du test : :(</p>"), ai)
    assert result.status == Status.PASS
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "cryptic_context"
    assert items[0].text == ":("
    assert items[0].context == "Résultat du test : :("
    assert items[0].details == {"kind": EMOTICON_KIND}


def test_1351_ai_says_no_definition_fails(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    result = run_rgaa(Test1351(), context_factory("<p>@+</p>"), ai)
    assert result.status == Status.FAIL
    assert "ni attribut title" in result.findings[0].message


def test_1351_uncertain_or_missing_ai_needs_review(context_factory, run_rgaa):
    html = "<p>Bravo ^^</p>"
    low = text_services(relevance_answer=relevance(False, confidence="low"))
    assert run_rgaa(Test1351(), context_factory(html), low).status == Status.NEEDS_REVIEW
    assert run_rgaa(Test1351(), context_factory(html)).status == Status.NEEDS_REVIEW


def test_1351_ai_error_gives_error(context_factory, run_rgaa):
    ai = text_services(relevance_answer=RuntimeError("panne"))
    assert run_rgaa(Test1351(), context_factory("<p>Bravo ^^</p>"), ai).status == Status.ERROR


# 13.6.1 ---------------------------------------------------------------------


def test_1361_only_contents_with_title_are_concerned(context_factory, run_rgaa):
    ai = text_services()
    assert run_rgaa(Test1361(), context_factory("<p>Bravo ^^</p>"), ai).status == Status.NOT_APPLICABLE
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_1361_title_is_judged_by_ai(context_factory, run_rgaa):
    ai = text_services()
    html = '<p>À demain <abbr title="à plus tard">@+</abbr></p>'
    assert run_rgaa(Test1361(), context_factory(html), ai).status == Status.PASS
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "cryptic_alternative"
    assert items[0].text == "à plus tard"
    assert items[0].details["cryptic_content"] == "@+"


def test_1361_aria_label_on_ascii_art_is_an_alternative(context_factory, run_rgaa):
    html = ASCII_ART.replace("<pre>", '<pre role="img" aria-label="Un chat">')
    ai = text_services(relevance_answer=relevance(False))
    result = run_rgaa(Test1361(), context_factory(html), ai)
    assert result.status == Status.FAIL
    assert result.findings[0].evidence["source"] == "aria-label"
    assert run_rgaa(Test1351(), context_factory(html), ai).status == Status.PASS


def test_1361_without_ai_needs_review(context_factory, run_rgaa):
    html = '<span title="banane">:-)</span>'
    assert run_rgaa(Test1361(), context_factory(html)).status == Status.NEEDS_REVIEW


@pytest.mark.parametrize("test", [Test1351(), Test1361()])
def test_13_5_missing_dom_raises_error(test, context_factory):
    context = context_factory("<p>x</p>")
    context.dom = None
    with pytest.raises(ValueError, match="nécessite un DOM"):
        asyncio.run(test.run(context))
