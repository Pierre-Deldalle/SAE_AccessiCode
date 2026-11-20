"""Critère RGAA 13.9 : consultation dans les deux orientations de l'écran."""

import asyncio

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_9 import Test1391


def _styled(css: str, body: str = "<main><p>Contenu</p></main>") -> str:
    return f"<html><head><style>{css}</style></head><body>{body}</body></html>"


def test_1391_page_without_restriction_passes(context_factory, run_rgaa):
    result = run_rgaa(Test1391(), context_factory("<p>Contenu</p>"))
    assert result.status == Status.PASS
    assert result.summary == "Aucun blocage de l'orientation de l'écran repéré."


def test_1391_layout_adaptation_passes(context_factory, run_rgaa):
    html = _styled("@media (orientation: landscape) { .col { width: 50% } }")
    assert run_rgaa(Test1391(), context_factory(html)).status == Status.PASS


def test_1391_orientation_lock_fails(context_factory, run_rgaa):
    result = run_rgaa(Test1391(), context_factory("<script>screen.orientation.lock('landscape');</script>"))
    assert result.status == Status.FAIL
    assert "essentielle" in result.findings[0].message


@pytest.mark.parametrize(
    "css",
    [
        "@media screen and (orientation: portrait) { body { display: none } }",
        "@media (orientation: portrait) { html { transform: rotate(90deg) } }",
        "/* paysage */ @media (orientation:landscape) { main, .x { visibility: hidden } }",
    ],
)
def test_1391_whole_page_hidden_or_rotated_fails(css, context_factory, run_rgaa):
    assert run_rgaa(Test1391(), context_factory(_styled(css))).status == Status.FAIL


def test_1391_partial_hiding_needs_review(context_factory, run_rgaa):
    result = run_rgaa(
        Test1391(), context_factory(_styled("@media (orientation: portrait) { .aside { display: none } }"))
    )
    assert result.status == Status.NEEDS_REVIEW
    assert "portrait" in result.findings[0].message


def test_1391_rotate_message_needs_review(context_factory, run_rgaa):
    html = "<p>Veuillez tourner votre appareil pour continuer.</p>"
    assert run_rgaa(Test1391(), context_factory(html)).status == Status.NEEDS_REVIEW


def test_1391_external_stylesheet(context_factory, run_rgaa):
    context = context_factory("<p>x</p>")
    context.css_sources = {context.workspace_path / "s.css": "@media (orientation: portrait) { body { display:none } }"}
    result = run_rgaa(Test1391(), context)
    assert result.status == Status.FAIL
    assert result.findings[0].element.startswith("s.css")


def test_1391_missing_dom_raises_error(context_factory):
    context = context_factory("<p>x</p>")
    context.dom = None
    with pytest.raises(ValueError, match="13.9.1 nécessite un DOM"):
        asyncio.run(Test1391().run(context))
