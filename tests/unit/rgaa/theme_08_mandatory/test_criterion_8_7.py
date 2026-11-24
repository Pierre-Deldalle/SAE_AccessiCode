"""Critère RGAA 8.7 : changements de langue indiqués (segments jugés par l'IA)."""

from tests.ai_fakes import relevance, text_services

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_7 import Test871

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
    ai = text_services(relevance_answer=relevance(False, problems=["« please contact us »"]))
    html = '<html lang="fr"><body><p id="p1">Pour nos clients : please contact us.</p></body></html>'
    result = run_rgaa(Test871(), context_factory(html), ai)
    assert result.status == Status.FAIL
    assert result.findings[0].element == "p#p1"
    assert "« please contact us »" in result.findings[0].message


def test_missing_default_language_is_sent_as_undeclared(context_factory, run_rgaa):
    ai = text_services()
    run_rgaa(Test871(), context_factory("<html><body><p>Bonjour à tous.</p></body></html>"), ai)
    assert submitted(ai)[0].details["declared_language"] == "non déclarée"


def test_without_ai_needs_review(context_factory, run_rgaa):
    assert run_rgaa(Test871(), context_factory(PAGE)).status == Status.NEEDS_REVIEW


def test_ai_exception_gives_error(context_factory, run_rgaa):
    ai = text_services(relevance_answer=RuntimeError("panne"))
    assert run_rgaa(Test871(), context_factory(PAGE), ai).status == Status.ERROR


def test_low_confidence_needs_review(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False, confidence="low"))
    assert run_rgaa(Test871(), context_factory(PAGE), ai).status == Status.NEEDS_REVIEW
