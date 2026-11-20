"""Critère RGAA 10.3 : contenu compréhensible dans l'ordre du code (sans feuille de style)."""

from pathlib import Path

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_3 import Test1031


def test_no_css_passes(context_factory, run_rgaa):
    result = run_rgaa(Test1031(), context_factory("<main><h1>Titre</h1><p>Texte</p></main>"))
    assert result.status == Status.PASS


@pytest.mark.parametrize(
    "rule",
    [
        ".a { order: 2 }",
        ".a { flex-direction: row-reverse }",
        ".a { flex-flow: column-reverse wrap }",
        ".a { grid-row: 1 }",
        ".a { grid-template-areas: 'b a' }",
        ".a { position: absolute; top: 0 }",
        ".a { float: right }",
        "@media (max-width: 600px) { .a { order: -1 } }",
    ],
)
def test_reordering_rule_needs_review(rule, context_factory, run_rgaa):
    result = run_rgaa(Test1031(), context_factory(f'<style>{rule}</style><div class="a">Bloc</div>'))
    assert result.status == Status.NEEDS_REVIEW
    assert result.findings[0].element == ".a"
    assert "ordre différent de celui du code" in result.findings[0].message


@pytest.mark.parametrize(
    "rule",
    [
        ".a { order: 0; flex-direction: row; float: left; position: relative }",
        ".sr-only { position: absolute; width: 1px; height: 1px; clip: rect(0 0 0 0) }",
        ".a::before { position: absolute; content: '' }",
        ".absent { order: 3 }",
    ],
)
def test_non_reordering_rules_pass(rule, context_factory, run_rgaa):
    html = f'<style>{rule}</style><div class="a sr-only">Bloc</div>'
    assert run_rgaa(Test1031(), context_factory(html)).status == Status.PASS


def test_inline_style_needs_review(context_factory, run_rgaa):
    result = run_rgaa(Test1031(), context_factory('<div id="pub" style="position: fixed; bottom: 0">Pub</div>'))
    assert result.status == Status.NEEDS_REVIEW
    assert result.findings[0].element == "div#pub"


def test_external_stylesheet_is_read(context_factory, run_rgaa):
    context = context_factory('<div class="a">Bloc</div>')
    context.css_sources = {Path("site.css"): ".a { order: 2 }"}
    result = run_rgaa(Test1031(), context)
    assert result.status == Status.NEEDS_REVIEW
    assert result.findings[0].evidence["source"] == "external:site.css"


def test_hover_rule_matches_element(context_factory, run_rgaa):
    html = '<style>.menu:hover .sous { position: absolute }</style><ul class="menu"><li class="sous">x</li></ul>'
    assert run_rgaa(Test1031(), context_factory(html)).status == Status.NEEDS_REVIEW
