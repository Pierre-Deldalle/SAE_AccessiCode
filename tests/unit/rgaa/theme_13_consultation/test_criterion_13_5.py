"""Critères RGAA 13.5 et 13.6 : contenus cryptiques (jugés par l'IA)."""

import asyncio

import pytest
from ai_fakes import relevance, text_services
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


def test_1351_failure_is_located_on_the_cryptic_content(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    result = run_rgaa(Test1351(), context_factory("<h1>Messages</h1>\n\n<p>@+</p>"), ai)
    assert result.status == Status.FAIL
    assert (result.findings[0].line, result.findings[0].snippet) == (3, "<p>@+</p>")


def test_1361_failure_is_located_on_the_cryptic_content(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    html = '<p>Messages</p>\n<span title="banane">:-)</span>'
    result = run_rgaa(Test1361(), context_factory(html), ai)
    assert result.status == Status.FAIL
    assert (result.findings[0].line, result.findings[0].snippet) == (2, '<span title="banane">:-)</span>')


# Propositions de l'IA et exemples de correction -------------------------------


def test_1351_fail_shows_the_ai_proposal_in_the_example(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False, suggestion="à plus tard"))
    result = run_rgaa(Test1351(), context_factory("<p>Bonne soirée @+</p>"), ai)
    assert result.status == Status.FAIL
    assert result.findings[0].recommendation.endswith(
        'Proposition : « à plus tard ». Exemple : @+ → <span title="à plus tard">@+</span>'
    )


def test_1351_fail_without_proposal_uses_a_placeholder(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    result = run_rgaa(Test1351(), context_factory("<p>Bonne soirée @+</p>"), ai)
    assert "Proposition" not in result.findings[0].recommendation
    assert result.findings[0].recommendation.endswith('Exemple : @+ → <span title="[sens du contenu]">@+</span>')


def test_1351_ascii_art_example_becomes_an_image(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False, suggestion="Un chat"))
    result = run_rgaa(Test1351(), context_factory(ASCII_ART.replace("<pre>", '<pre class="art">')), ai)
    assert result.findings[0].recommendation.endswith(
        'Exemple : <pre class="art"> → <pre class="art" role="img" aria-label="Un chat">'
    )


@pytest.mark.parametrize("test", [Test1351(), Test1361()])
def test_proposal_is_ignored_on_pass_and_low_confidence(test, context_factory, run_rgaa):
    html = '<p>À demain <span title="bof">@+</span></p>' if isinstance(test, Test1361) else "<p>Bravo ^^</p>"
    on_pass = run_rgaa(test, context_factory(html), text_services(relevance_answer=relevance(True, suggestion="x")))
    assert on_pass.status == Status.PASS
    assert on_pass.findings == []
    unsure = text_services(relevance_answer=relevance(False, confidence="low", suggestion="à plus tard"))
    result = run_rgaa(test, context_factory(html), unsure)
    assert result.status == Status.NEEDS_REVIEW
    assert "Proposition" not in result.findings[0].recommendation
    assert "Exemple" not in result.findings[0].recommendation


def test_1361_fail_corrects_the_attribute_that_carries_the_alternative(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False, suggestion="à plus tard"))
    html = '<p>À demain <abbr class="c" title="bof"><b>@+</b></abbr></p>'
    result = run_rgaa(Test1361(), context_factory(html), ai)
    assert result.status == Status.FAIL
    assert result.findings[0].recommendation.endswith(
        'Proposition : « à plus tard ». Exemple : <abbr class="c" title="bof"> → <abbr class="c" title="à plus tard">'
    )


def test_1361_aria_label_alternative_is_corrected_in_place(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    html = ASCII_ART.replace("<pre>", '<pre role="img" aria-label="Dessin">')
    result = run_rgaa(Test1361(), context_factory(html), ai)
    assert result.findings[0].recommendation.endswith(
        'Exemple : <pre role="img" aria-label="Dessin"> → <pre role="img" aria-label="[sens du contenu]">'
    )


@pytest.mark.parametrize("test", [Test1351(), Test1361()])
def test_13_5_missing_dom_raises_error(test, context_factory):
    context = context_factory("<p>x</p>")
    context.dom = None
    with pytest.raises(ValueError, match="nécessite un DOM"):
        asyncio.run(test.run(context))
