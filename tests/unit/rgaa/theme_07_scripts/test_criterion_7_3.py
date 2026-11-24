"""Critère RGAA 7.3 : scripts utilisables au clavier (7.3.1, équivalent jugé par l'IA) et focus conservé (7.3.2)."""

import asyncio

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_07_scripts.criterion_7_3 import Test731, Test732
from tests.ai_fakes import relevance, text_services

LINK = '<a href="/accueil">Accueil</a>'


def submitted(ai):
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "keyboard_equivalent"
    return items


# 7.3.1 ---------------------------------------------------------------------


def test_731_no_event_handler_is_not_applicable(context_factory, run_rgaa):
    html = '<p>Texte</p><img src="a.png" alt="" onload="init()">'
    assert run_rgaa(Test731(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


@pytest.mark.parametrize(
    "html",
    [
        '<button onclick="go()">Valider</button>',
        '<a href="/aide" onclick="track(\'aide\')">Aide</a>',
        '<div role="button" tabindex="0" onclick="go()" onkeydown="touche(event)">Valider</div>',
    ],
)
def test_731_keyboard_usable_elements_pass(html, context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test731(), context_factory(html), ai)
    assert result.status == Status.PASS
    assert result.findings == []
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_731_role_button_without_tabindex_is_not_keyboard_usable(context_factory, run_rgaa):
    # Un rôle ne rend pas l'élément atteignable au clavier (l'ancien test le jugeait conforme).
    html = '<div role="button" onclick="go()">Valider</div>'
    result = run_rgaa(Test731(), context_factory(html), text_services())
    assert result.status == Status.FAIL
    assert "touche Tab" in result.findings[0].message


def test_731_page_without_keyboard_control_fails_without_ai(context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test731(), context_factory('<p>Intro</p>\n<div id="ok" onclick="go()">Valider</div>'), ai)
    finding = result.findings[0]
    assert result.status == Status.FAIL
    assert finding.element == "div#ok"
    assert (finding.line, finding.snippet) == (2, '<div id="ok" onclick="go()">Valider</div>')
    assert finding.recommendation.endswith(
        'Exemple : <div id="ok" onclick="go()"> → <button type="button" id="ok" onclick="go()">'
    )
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_731_navigation_suggests_a_link(context_factory, run_rgaa):
    html = "<span onclick=\"location.href='/aide'\">Aide</span>"
    result = run_rgaa(Test731(), context_factory(html), text_services())
    assert result.findings[0].recommendation.endswith('→ <a href="/aide">')


def test_731_equivalent_is_judged_by_ai_with_keyboard_controls(context_factory, run_rgaa):
    ai = text_services()
    html = f"{LINK}<div onclick=\"location.href='/accueil'\">Accueil</div>"
    assert run_rgaa(Test731(), context_factory(html), ai).status == Status.PASS
    [item] = submitted(ai)
    assert item.text == "Accueil"
    assert item.context == "Contrôles utilisables au clavier : link « Accueil »"
    assert "location.href" in item.details["action"]


def test_731_no_equivalent_fails(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    result = run_rgaa(Test731(), context_factory(f'{LINK}<div onclick="supprimer()">Supprimer</div>'), ai)
    assert result.status == Status.FAIL
    assert "aucun autre élément" in result.findings[0].message


@pytest.mark.parametrize(
    "ai", [None, text_services(relevance_answer=relevance(False, confidence="low"))], ids=["sans IA", "incertaine"]
)
def test_731_unknown_equivalent_needs_review(ai, context_factory, run_rgaa):
    result = run_rgaa(Test731(), context_factory(f'{LINK}<div onclick="go()">Valider</div>'), ai)
    assert result.status == Status.NEEDS_REVIEW


def test_731_focusable_without_keys_and_document_listener_needs_review(context_factory, run_rgaa):
    html = '<div tabindex="0" onclick="go()">Valider</div><script>document.addEventListener("keydown", f)</script>'
    result = run_rgaa(Test731(), context_factory(html), text_services())
    assert result.status == Status.NEEDS_REVIEW
    assert "document" in result.findings[0].message


def test_731_script_listener_is_attached_to_its_element(context_factory, run_rgaa):
    html = '<div id="d">Valider</div><script>document.getElementById("d").addEventListener("click", go)</script>'
    result = run_rgaa(Test731(), context_factory(html), text_services())
    assert result.status == Status.FAIL
    assert result.findings[0].element == "div#d"


def test_731_hover_without_focus_needs_review_with_example(context_factory, run_rgaa):
    result = run_rgaa(Test731(), context_factory('<span onmouseover="bulle()">?</span>'), text_services())
    assert result.status == Status.NEEDS_REVIEW
    assert result.findings[0].recommendation.endswith(
        '<span onmouseover="bulle()"> → <span onmouseover="bulle()" onfocus="bulle()" tabindex="0">'
    )


def test_731_hidden_and_disabled_elements_are_ignored(context_factory, run_rgaa):
    html = '<div hidden onclick="go()">A</div><div aria-disabled="true" onclick="go()">B</div>'
    assert run_rgaa(Test731(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_731_identifiers_are_stable(context_factory, run_rgaa):
    html = '<div onclick="a()">A</div><span onclick="b()">B</span><p onclick="c()">C</p>'
    for _ in range(3):
        result = run_rgaa(Test731(), context_factory(html), text_services())
        assert [finding.element for finding in result.findings] == ["div[index=0]", "span[index=1]", "p[index=2]"]


# 7.3.2 ---------------------------------------------------------------------


def test_732_page_without_script_is_not_applicable(context_factory, run_rgaa):
    assert run_rgaa(Test732(), context_factory("<p>Texte</p>")).status == Status.NOT_APPLICABLE


def test_732_scripts_without_blur_pass(context_factory, run_rgaa):
    result = run_rgaa(Test732(), context_factory('<button onclick="go()">Go</button><script>init()</script>'))
    assert result.status == Status.PASS
    assert result.summary == "Aucun script ne retire le focus d'un élément."


def test_732_onfocus_blur_fails_with_example(context_factory, run_rgaa):
    result = run_rgaa(Test732(), context_factory('<p>x</p>\n<input id="q" onfocus="this.blur()">'))
    finding = result.findings[0]
    assert result.status == Status.FAIL
    assert (finding.line, finding.snippet) == (2, '<input id="q" onfocus="this.blur()">')
    assert finding.recommendation.endswith('Exemple : <input id="q" onfocus="this.blur()"> → <input id="q">')


def test_732_focus_listener_in_script_fails_with_script_line(context_factory, run_rgaa):
    html = (
        '<input id="i">\n<script>\nconst i = document.getElementById("i");\n'
        'i.addEventListener("focus", () => {\n  i.blur();\n});\n</script>'
    )
    result = run_rgaa(Test732(), context_factory(html))
    finding = result.findings[0]
    assert result.status == Status.FAIL
    assert (finding.element, finding.line, finding.file) == ("script[index=0]", 5, None)


def test_732_named_focus_handler_fails(context_factory, run_rgaa):
    html = "<script>function bloquer() { this.blur(); }\nchamp.onfocus = bloquer;</script>"
    assert run_rgaa(Test732(), context_factory(html)).status == Status.FAIL


def test_732_blur_after_click_needs_review(context_factory, run_rgaa):
    html = '<script>b.addEventListener("click", function () { this.blur(); });</script>'
    assert run_rgaa(Test732(), context_factory(html)).status == Status.NEEDS_REVIEW


def test_732_external_script_gives_file_and_line(context_factory, run_rgaa):
    context = context_factory(
        '<script src="js/app.js"></script>',
        resources={"js/app.js": 'init();\nx.addEventListener("focusin", () => x.blur());'},
    )
    finding = run_rgaa(Test732(), context).findings[0]
    assert (finding.element, finding.file, finding.line) == ("app.js", "app.js", 2)


@pytest.mark.parametrize("test", [Test731(), Test732()])
def test_7_3_missing_dom_raises_error(test, context_factory):
    context = context_factory("<p>x</p>")
    context.dom = None
    with pytest.raises(ValueError, match="nécessite un DOM"):
        asyncio.run(test.run(context))


def test_731_role_link_suggests_a_link_to_complete(context_factory, run_rgaa):
    html = '<div role="link" tabindex="0" onclick="allerSection()">Section</div>'
    result = run_rgaa(Test731(), context_factory(html), text_services())
    assert result.findings[0].recommendation.endswith('→ <a href="[adresse de destination]" onclick="allerSection()">')
