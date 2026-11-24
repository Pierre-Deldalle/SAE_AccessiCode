"""Critère RGAA 8.9 : balises utilisées uniquement pour la présentation."""

import pytest
from tests.ai_fakes import structure, text_services

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_9 import Test891


def test_clean_page_passes(context_factory, run_rgaa):
    html = "<h1>Titre</h1><p>Texte<br>suite</p><p><img src='a.png' alt='Plan'></p>"
    ai = text_services()
    result = run_rgaa(Test891(), context_factory(html), ai)
    assert result.status == Status.PASS
    ai.structure_analyzer.classify_candidates.assert_not_called()


@pytest.mark.parametrize(
    ("html", "usage"),
    [
        ("<p>Texte</p><p>&nbsp;</p><p>Suite</p>", "empty_element"),
        ("<h2></h2>", "empty_element"),
        ("<p>Ligne<br><br>Autre ligne</p>", "repeated_br"),
        ("<p>Ligne<br>\n  <br>\n<br>Autre</p>", "repeated_br"),
    ],
)
def test_spacing_usages_fail_without_ai(html, usage, context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test891(), context_factory(html), ai)
    assert result.status == Status.FAIL
    assert [finding.evidence["usage"] for finding in result.findings] == [usage]
    ai.structure_analyzer.classify_candidates.assert_not_called()


def test_hidden_empty_paragraph_is_ignored(context_factory, run_rgaa):
    assert run_rgaa(Test891(), context_factory("<div hidden><p></p></div>")).status == Status.PASS


def test_real_quote_passes(context_factory, run_rgaa):
    ai = text_services(structure_answer=structure(True))
    html = "<blockquote>« Le mieux est l'ennemi du bien. » — Voltaire</blockquote>"
    assert run_rgaa(Test891(), context_factory(html), ai).status == Status.PASS
    kind, _items = ai.structure_analyzer.classify_candidates.call_args.args
    assert kind == "quote"


def test_blockquote_used_for_indentation_fails(context_factory, run_rgaa):
    ai = text_services(structure_answer=structure(False))
    result = run_rgaa(Test891(), context_factory("<blockquote><p>Horaires : 9 h - 18 h</p></blockquote>"), ai)
    assert result.status == Status.FAIL
    assert "indenter" in result.findings[0].message


def test_blockquote_without_ai_needs_review(context_factory, run_rgaa):
    assert run_rgaa(Test891(), context_factory("<blockquote>Texte</blockquote>")).status == Status.NEEDS_REVIEW


def test_ai_exception_gives_error(context_factory, run_rgaa):
    ai = text_services(structure_answer=RuntimeError("panne"))
    assert run_rgaa(Test891(), context_factory("<blockquote>Texte</blockquote>"), ai).status == Status.ERROR
