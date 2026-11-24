"""Critère RGAA 10.3 : contenu compréhensible dans l'ordre du code (sans feuille de style)."""

import pytest

from accessi_code.models.audit_file import AuditFile
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.registry import TestRegistry as Registry
from accessi_code.rgaa.runner import TestRunner as Runner
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
    tag = '<div id="pub" style="position: fixed; bottom: 0">Pub</div>'
    result = run_rgaa(Test1031(), context_factory(f"<main>\n{tag}\n</main>"))
    assert result.status == Status.NEEDS_REVIEW
    [finding] = result.findings
    assert finding.element == "div#pub"
    assert (finding.line, finding.snippet) == (2, tag)


def test_style_tag_reports_the_line_of_the_rule(context_factory, run_rgaa):
    rule = ".a { order: 2 }"
    html = f"""<!doctype html>
<style
  media="screen">
/* Commentaire
   sur deux lignes */
@supports (display: grid) {{
  {rule}
}}
</style>
<div class="a">Bloc</div>"""
    result = run_rgaa(Test1031(), context_factory(html))
    assert result.status == Status.NEEDS_REVIEW
    [finding] = result.findings
    assert (finding.file, finding.line, finding.snippet) == ("index.html", 7, rule)


@pytest.mark.asyncio
async def test_external_stylesheet_keeps_its_original_path_and_lines(context_factory):
    css = """/* Commentaire
   sur deux lignes */
@media (max-width: 600px) {
    .autre { order: 0; }
    .a {
        order: 2;
    }
}
.a { order: 3 }
"""
    context = context_factory(
        '<link rel="stylesheet" href="assets/mise-en-page.css">\n<div class="a">Bloc</div>',
        resources={"source/assets/copie.css": css},
    )
    path = context.workspace_path / "source/assets/copie.css"
    context.files.append(AuditFile("mise-en-page.css", path, ".css"))
    context.css_sources = {path: css}
    [result] = await Runner(Registry([Test1031()])).run_all(context)
    assert result.status == Status.NEEDS_REVIEW
    assert [(finding.file, finding.line, finding.snippet) for finding in result.findings] == [
        ("assets/mise-en-page.css", 5, ".a {\n        order: 2;\n    }"),
        ("assets/mise-en-page.css", 9, ".a { order: 3 }"),
    ]


def test_hover_rule_matches_element(context_factory, run_rgaa):
    html = '<style>.menu:hover .sous { position: absolute }</style><ul class="menu"><li class="sous">x</li></ul>'
    assert run_rgaa(Test1031(), context_factory(html)).status == Status.NEEDS_REVIEW
