"""Critère RGAA 8.7 : changements de langue indiqués (segments jugés par l'IA)."""

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_7 import Test871
from tests.ai_fakes import relevance, text_services

PAGE = """<html lang="fr"><body>
<h1>Contact</h1>
<p id="intro">Écrivez-nous, nous répondons sous 48 heures.</p>
<p>Pour nos clients : <span lang="en">please contact us</span> par e-mail.</p>
<div lang="de"><p>Willkommen auf unserer Seite.</p></div>
</body></html>"""


def submitted(ai):
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "text_language"
    return items


def test_no_text_is_not_applicable(context_factory, run_rgaa):
    assert (
        run_rgaa(
            Test871(), context_factory('<html lang="fr"><body><img src="a.png" alt=""></body></html>'), text_services()
        ).status
        == Status.NOT_APPLICABLE
    )


def test_segments_by_inherited_language(context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test871(), context_factory(PAGE), ai)
    assert result.status == Status.PASS
    items = submitted(ai)
    assert [item.details["declared_language"] for item in items] == ["fr", "de"]
    assert items[0].text == (
        "Contact / Écrivez-nous, nous répondons sous 48 heures. / Pour nos clients : [passage balisé] par e-mail."
    )
    assert items[1].text == "Willkommen auf unserer Seite."


def test_long_text_is_split(context_factory, run_rgaa):
    paragraphs = "".join(f"<p>{'mot ' * 100}{index}</p>" for index in range(6))
    ai = text_services()
    run_rgaa(Test871(), context_factory(f'<html lang="fr"><body>{paragraphs}</body></html>'), ai)
    assert len(submitted(ai)) > 1
    assert all(len(item.text) <= 1300 for item in submitted(ai))


def test_unmarked_change_fails_with_passages(context_factory, run_rgaa):
    suggestion = 'Entourer « please contact us » avec <span lang="en"> et </span>.'
    ai = text_services(relevance_answer=relevance(False, problems=["« please contact us »"], suggestion=suggestion))
    passage = '<p id="p1">Pour nos clients : please contact us.</p>'
    html = f'<html lang="fr"><body>\n{passage}\n</body></html>'
    result = run_rgaa(Test871(), context_factory(html), ai)
    assert result.status == Status.FAIL
    [finding] = result.findings
    assert finding.element == "p#p1"
    assert "« please contact us »" in finding.message
    assert (finding.line, finding.snippet) == (2, passage)
    assert finding.recommendation.endswith(f" Proposition : « {suggestion} ».")


def test_missing_default_language_is_sent_as_undeclared(context_factory, run_rgaa):
    ai = text_services()
    run_rgaa(Test871(), context_factory("<html><body><p>Bonjour à tous.</p></body></html>"), ai)
    assert submitted(ai)[0].details["declared_language"] == "non déclarée"


def test_without_ai_needs_review(context_factory, run_rgaa):
    result = run_rgaa(Test871(), context_factory(PAGE))
    assert result.status == Status.NEEDS_REVIEW
    assert [(finding.line, finding.snippet) for finding in result.findings] == [
        (2, "<h1>Contact</h1>"),
        (5, "<p>Willkommen auf unserer Seite.</p>"),
    ]


def test_ai_exception_gives_error(context_factory, run_rgaa):
    ai = text_services(relevance_answer=RuntimeError("panne"))
    assert run_rgaa(Test871(), context_factory(PAGE), ai).status == Status.ERROR


def test_low_confidence_needs_review(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False, confidence="low", suggestion='Ajouter lang="en".'))
    result = run_rgaa(Test871(), context_factory(PAGE), ai)
    assert result.status == Status.NEEDS_REVIEW
    assert all("Proposition :" not in finding.recommendation for finding in result.findings)
    assert all("suggestion" not in finding.evidence["analysis"] for finding in result.findings)
