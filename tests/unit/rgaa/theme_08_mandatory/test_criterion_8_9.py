"""Critère RGAA 8.9 : balises utilisées uniquement pour la présentation."""

import pytest
from ai_fakes import structure, text_services

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_9 import Test891


def test_clean_page_passes(context_factory, run_rgaa):
    html = "<h1>Titre</h1><p>Texte<br>suite</p><p><img src='a.png' alt='Plan'></p>"
    ai = text_services()
    result = run_rgaa(Test891(), context_factory(html), ai)
    assert result.status == Status.PASS
    ai.structure_analyzer.classify_candidates.assert_not_called()


@pytest.mark.parametrize(
    ("html", "usage", "snippet", "after"),
    [
        ("<p>Texte</p>\n<p>&nbsp;</p><p>Suite</p>", "empty_element", "<p>\xa0</p>", "<!-- Espacement géré en CSS -->"),
        ("\n<h2></h2>", "empty_element", "<h2></h2>", "<!-- Espacement géré en CSS -->"),
        (
            '<p>Ligne\n<br class="suite"><br>Autre ligne</p>',
            "repeated_br",
            '<br class="suite"/>',
            '<br class="suite"/>',
        ),
        ("<p>Ligne\n<br>\n  <br>\n<br>Autre</p>", "repeated_br", "<br/>", "<br/>"),
    ],
)
def test_spacing_usages_fail_without_ai(html, usage, snippet, after, context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test891(), context_factory(html), ai)
    assert result.status == Status.FAIL
    [finding] = result.findings
    assert finding.evidence["usage"] == usage
    assert (finding.line, finding.snippet) == (2, snippet)
    assert f"\nAvant : {snippet}" in finding.recommendation
    assert finding.recommendation.endswith(f"\nAprès : {after}")
    ai.structure_analyzer.classify_candidates.assert_not_called()


def test_hidden_empty_paragraph_is_ignored(context_factory, run_rgaa):
    assert run_rgaa(Test891(), context_factory("<div hidden><p></p></div>")).status == Status.PASS


def test_real_quote_passes(context_factory, run_rgaa):
    ai = text_services(structure_answer=structure(True, suggestion="Utiliser un div."))
    html = "<blockquote>« Le mieux est l'ennemi du bien. » — Voltaire</blockquote>"
    result = run_rgaa(Test891(), context_factory(html), ai)
    assert result.status == Status.PASS
    assert result.findings == []
    kind, _items = ai.structure_analyzer.classify_candidates.call_args.args
    assert kind == "presentation_quote"


def test_blockquote_used_for_indentation_fails(context_factory, run_rgaa):
    suggestion = "Remplacer les balises blockquote par des balises div."
    ai = text_services(structure_answer=structure(False, suggestion=suggestion))
    quote = "<blockquote><p>Horaires : 9 h - 18 h</p></blockquote>"
    result = run_rgaa(Test891(), context_factory(f"<main>\n{quote}\n</main>"), ai)
    assert result.status == Status.FAIL
    [finding] = result.findings
    assert "indenter" in finding.message
    assert (finding.line, finding.snippet) == (2, quote)
    assert finding.recommendation.endswith(f"\nProposition : {suggestion}")


def test_blockquote_without_ai_needs_review(context_factory, run_rgaa):
    assert run_rgaa(Test891(), context_factory("<blockquote>Texte</blockquote>")).status == Status.NEEDS_REVIEW


def test_ai_exception_gives_error(context_factory, run_rgaa):
    ai = text_services(structure_answer=RuntimeError("panne"))
    quote = "<blockquote>Texte</blockquote>"
    result = run_rgaa(Test891(), context_factory(f"<main>\n{quote}\n</main>"), ai)
    assert result.status == Status.ERROR
    [finding] = result.findings
    assert (finding.line, finding.snippet) == (2, quote)
