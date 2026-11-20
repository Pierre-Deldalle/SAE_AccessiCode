"""Critère RGAA 8.2 : code source valide (contrôle déterministe, sans IA)."""

import pytest

from accessi_code.analysis.html_validation import validate_html
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_2 import Test821

VALID = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><title>Accueil</title></head>
<body>
<p>Un<p>Deux
<ul><li>a<li>b</ul>
<table><tr><td>1<td>2<tr><td>3</table>
<dl><dt>Terme<dd>Définition</dl>
<select><option>1<option>2</select>
<img src="a.png" alt=""><br><input type="text">
<svg viewBox="0 0 10 10"><path d="M0 0"/><circle r="1"/></svg>
</body></html>"""


def test_valid_source_passes(context_factory, run_rgaa):
    result = run_rgaa(Test821(), context_factory(VALID))
    assert result.status == Status.PASS
    assert result.findings == []


@pytest.mark.parametrize(
    ("fragment", "condition", "message"),
    [
        ('<div id="a"></div><p id="a"></p>', "id", "déjà utilisé ligne"),
        ('<span class="a" class="b">x</span>', "attributs", "« class » est doublé"),
        ("<b><i>texte</b></i>", "imbrication", "<i> ouvert"),
        ("<section><div></section>", "imbrication", "<div> ouvert"),
        ("</span>", "fermeture", "ne correspond à aucune balise ouvrante"),
        ("<main><div>", "imbrication", "n'est pas fermé avant </body>"),
        ("<p>a</p></p>", "fermeture", "</p>"),
        ("<br></br>", "fermeture", "élément vide"),
        ("<div/>", "écriture", "auto-fermante"),
        ("<center>x</center>", "écriture", "obsolète"),
        ('<div id="a b"></div>', "écriture", "contient un espace"),
    ],
)
def test_each_condition_is_detected(fragment, condition, message):
    errors = validate_html(f"<!DOCTYPE html><html><body>{fragment}</body></html>")
    assert any(error.condition == condition and message in error.message for error in errors), errors


def test_unclosed_element_at_end_of_document():
    errors = validate_html("<!DOCTYPE html><div><span>texte")
    assert [error.message for error in errors] == [
        "<div> ouvert ligne 1 n'est jamais fermé.",
        "<span> ouvert ligne 1 n'est jamais fermé.",
    ]


def test_error_line_is_reported():
    errors = validate_html("<!DOCTYPE html>\n<html>\n<body>\n<div id='x'></div>\n<div id='x'></div>\n</body></html>")
    assert [(error.line, error.condition) for error in errors] == [(5, "id")]


def test_obsolete_elements_only_for_html5():
    source = "<center>x</center>"
    assert validate_html(source, html5=True)
    assert validate_html(source, html5=False) == []


def test_legacy_void_element_is_only_obsolete():
    errors = validate_html("<!DOCTYPE html><html><body><bgsound src='a.mid'><p>x</p></body></html>")
    assert [error.condition for error in errors] == ["écriture"]


def test_invalid_source_fails_with_findings(context_factory, run_rgaa):
    html = '<!DOCTYPE html><html lang="fr"><body><div id="a"></div><div id="a"></div></body></html>'
    result = run_rgaa(Test821(), context_factory(html))
    assert result.status == Status.FAIL
    assert result.findings[0].element.startswith("ligne 1")
    assert result.metadata["by_condition"] == {"id": 1}


def test_no_ai_service_is_used(context_factory, run_rgaa):
    """D4 : la validation ne dépend plus d'un service."""
    assert run_rgaa(Test821(), context_factory(VALID), None).status == Status.PASS


def test_missing_source_raises(context_factory):
    import asyncio

    context = context_factory(VALID)
    context.html_source = None
    with pytest.raises(ValueError, match="source HTML"):
        asyncio.run(Test821().run(context, None))
