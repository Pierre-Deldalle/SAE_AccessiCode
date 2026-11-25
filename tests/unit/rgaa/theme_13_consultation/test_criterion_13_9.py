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


def test_1391_lock_in_script_file_is_located_in_that_file(context_factory, run_rgaa):
    code = "// Jeu\nfunction start() {}\nscreen.orientation.lock('landscape');\n"
    result = run_rgaa(Test1391(), context_factory('<script src="jeu.js"></script>', resources={"jeu.js": code}))
    assert result.status == Status.FAIL
    finding = result.findings[0]
    assert (finding.file, finding.line, finding.snippet) == ("jeu.js", 3, "screen.orientation.lock('landscape');")


def test_1391_rule_in_stylesheet_file_is_located_in_that_file(context_factory, run_rgaa, tmp_path):
    context = context_factory("<main><p>Contenu</p></main>")
    context.css_sources[tmp_path / "css" / "s.css"] = "p { margin: 0 }\n@media (orientation: portrait) {\n  body {\n"
    context.css_sources[tmp_path / "css" / "s.css"] += "    display: none\n  }\n}\n"
    result = run_rgaa(Test1391(), context)
    assert result.status == Status.FAIL
    finding = result.findings[0]
    assert (finding.file, finding.line, finding.snippet) == ("s.css", 3, "body {")


def test_1391_rule_in_style_tag_is_located_in_the_page(context_factory, run_rgaa):
    html = "<html><head>\n<style>\n@media (orientation: portrait) {\n  .pub { display: none }\n}\n</style></head>"
    finding = run_rgaa(Test1391(), context_factory(html)).findings[0]
    assert (finding.file, finding.line, finding.snippet) == (None, 4, ".pub { display: none }")


def test_1391_rotate_message_is_located_on_its_element(context_factory, run_rgaa):
    html = "<body>\n<main>\n<p>Accueil</p>\n<p>Tournez votre appareil</p>\n</main></body>"
    finding = run_rgaa(Test1391(), context_factory(html)).findings[0]
    assert (finding.line, finding.snippet) == (4, "<p>Tournez votre appareil</p>")


def test_1391_lock_example_shows_the_line_to_remove(context_factory, run_rgaa):
    result = run_rgaa(Test1391(), context_factory("<script>\nawait screen.orientation.lock('portrait');\n</script>"))
    assert result.findings[0].recommendation.endswith(
        "Exemple : await screen.orientation.lock('portrait'); → ligne supprimée"
    )


def test_1391_global_rule_example_shows_the_rule_to_remove(context_factory, run_rgaa):
    html = _styled("@media (orientation: portrait) {\n  body {\n    display:  none;\n  }\n}")
    result = run_rgaa(Test1391(), context_factory(html))
    assert result.findings[0].recommendation.endswith(
        "Exemple : @media (orientation: portrait) { body { display: none; } } → règle supprimée"
    )


def test_1391_review_has_no_example(context_factory, run_rgaa):
    html = _styled("@media (orientation: portrait) { .pub { display: none } }")
    result = run_rgaa(Test1391(), context_factory(html))
    assert result.status == Status.NEEDS_REVIEW
    assert "Exemple" not in result.findings[0].recommendation


def test_1391_missing_dom_raises_error(context_factory):
    context = context_factory("<p>x</p>")
    context.dom = None
    with pytest.raises(ValueError, match="13.9.1 nécessite un DOM"):
        asyncio.run(Test1391().run(context))
