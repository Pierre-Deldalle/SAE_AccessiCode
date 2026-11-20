"""Critère RGAA 7.2 : alternatives aux scripts (7.2.1 jugé par l'IA)."""

import pytest
from ai_fakes import relevance, text_services

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_07_scripts.criterion_7_2 import (
    Test721,
    Test722,
)
from accessi_code.service.audit_services import AuditServices

NOSCRIPT = """
<div id="carte">
  <script src="carte.js"></script>
  <noscript>Consultez la <a href="/agences.html">liste des agences</a>.</noscript>
</div>
"""


def test_721_no_noscript_is_not_applicable(context_factory, run_rgaa):
    html = '<script src="app.js"></script><p>Contenu</p>'
    assert run_rgaa(Test721(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


@pytest.mark.parametrize(
    "html",
    [
        '<html><head><noscript><link rel="stylesheet" href="x.css"></noscript></head><body></body></html>',
        '<noscript><img src="https://stats.example/p.gif" width="1" height="1" alt=""></noscript>',
    ],
)
def test_721_head_and_tracking_noscript_are_ignored(html, context_factory, run_rgaa):
    assert run_rgaa(Test721(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_721_alternative_and_script_context_are_submitted(context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test721(), context_factory(NOSCRIPT), ai)
    assert result.status == Status.PASS
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "script_alternative"
    assert items[0].text == "Consultez la liste des agences ."
    assert "Script voisin : carte.js" in items[0].context


def test_721_empty_noscript_fails_without_ai(context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test721(), context_factory("<script>go()</script><noscript>  </noscript>"), ai)
    assert result.status == Status.FAIL
    assert "vide" in result.findings[0].message
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_721_irrelevant_alternative_fails(context_factory, run_rgaa):
    html = "<script>go()</script><noscript>Activez JavaScript.</noscript>"
    result = run_rgaa(Test721(), context_factory(html), text_services(relevance_answer=relevance(False)))
    assert result.status == Status.FAIL
    assert result.findings[0].element == "noscript[index=0]"


def test_721_without_ai_needs_review(context_factory, run_rgaa):
    assert run_rgaa(Test721(), context_factory(NOSCRIPT)).status == Status.NEEDS_REVIEW


def test_721_ai_exception_gives_error(context_factory, run_rgaa):
    ai = text_services(relevance_answer=RuntimeError("panne"))
    assert run_rgaa(Test721(), context_factory(NOSCRIPT), ai).status == Status.ERROR


def test_721_missing_dom_raises_error(context_factory):
    import asyncio

    context = context_factory("<p>x</p>")
    context.dom = None
    with pytest.raises(ValueError, match="7.2.1 nécessite un DOM"):
        asyncio.run(Test721().run(context, AuditServices()))


# ---------------------------------------------------------------------------
# 7.2.2
# ---------------------------------------------------------------------------


def test_722_not_implemented_yet(context_factory, run_rgaa):
    """Test that 7.2.2 returns NOT_APPLICABLE as it's not yet fully implemented."""
    html = """
    <img id="dynamic-image" src="default.jpg" alt="Default image">
    <script>
        // Script that updates the image source
        function changeImage() {
            document.getElementById('dynamic-image').src = 'new.jpg';
            document.getElementById('dynamic-image').alt = 'New image';
        }
        // Call the function after a delay
        setTimeout(changeImage, 1000);
    </script>
    """
    context = context_factory(html)
    result = run_rgaa(Test722(), context, AuditServices())

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert "nécessite un suivi des changements DOM en temps réel" in result.summary


def test_722_missing_dom_raises_error(context_factory):
    """Test that missing DOM raises ValueError."""
    context = context_factory("<html><body></body></html>")
    context.dom = None

    with pytest.raises(ValueError, match="Le test 7.2.2 nécessite un DOM"):
        import asyncio

        asyncio.run(Test722().run(context, AuditServices()))
