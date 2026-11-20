"""Critère RGAA 7.1 : composants contrôlés par script (7.1.1 et 7.1.2 sans IA, 7.1.3 jugé par l'IA)."""

import pytest
from ai_fakes import relevance, text_services

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_07_scripts.criterion_7_1 import Test711, Test712, Test713

MENU_BUTTON = '<button id="menu" onclick="toggle()" aria-expanded="false">Menu</button>'


def submitted(ai):
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "component_name"
    return items


@pytest.mark.parametrize("test_class", [Test711, Test712, Test713])
def test_no_component_is_not_applicable(test_class, context_factory, run_rgaa):
    html = '<form onsubmit="send()"><p>Texte</p><div role="region">Zone</div></form>'
    assert run_rgaa(test_class(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_hidden_components_are_ignored(context_factory, run_rgaa):
    html = '<div hidden><button onclick="x()">Ok</button></div>'
    assert run_rgaa(Test711(), context_factory(html)).status == Status.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# 7.1.1 — nom, rôle et états
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "html",
    [
        MENU_BUTTON,
        '<div role="button" tabindex="0" onclick="x()">Ouvrir</div>',
        '<label for="q">Recherche</label><input id="q" oninput="suggest()">',
        '<div role="checkbox" aria-checked="false" aria-label="Newsletter"></div>',
        '<input type="checkbox" role="checkbox" onchange="x()" aria-label="Accepter">',
    ],
)
def test_711_name_and_role_pass(html, context_factory, run_rgaa):
    result = run_rgaa(Test711(), context_factory(html))
    assert result.status == Status.PASS, result.findings


def test_711_div_without_role_fails(context_factory, run_rgaa):
    result = run_rgaa(Test711(), context_factory('<div id="ouvrir" onclick="open()">Ouvrir</div>'))
    assert result.status == Status.FAIL
    assert result.findings[0].element == "div#ouvrir"
    assert "aucun rôle" in result.findings[0].message


def test_711_component_without_name_fails(context_factory, run_rgaa):
    result = run_rgaa(Test711(), context_factory('<button onclick="x()"><svg></svg></button>'))
    assert result.status == Status.FAIL
    assert "aucun nom accessible" in result.findings[0].message


def test_711_missing_required_state_fails(context_factory, run_rgaa):
    html = '<div role="switch" tabindex="0" onclick="x()">Mode sombre</div>'
    result = run_rgaa(Test711(), context_factory(html))
    assert result.status == Status.FAIL
    assert result.findings[0].evidence["missing_states"] == ["aria-checked"]


# ---------------------------------------------------------------------------
# 7.1.2 — restitution : vérification humaine
# ---------------------------------------------------------------------------


def test_712_always_needs_review(context_factory, run_rgaa):
    result = run_rgaa(Test712(), context_factory(MENU_BUTTON))
    assert result.status == Status.NEEDS_REVIEW
    assert "technologie d'assistance" in result.findings[0].message


# ---------------------------------------------------------------------------
# 7.1.3 — nom et rôle pertinents
# ---------------------------------------------------------------------------


def test_713_name_role_and_label_are_submitted(context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test713(), context_factory(MENU_BUTTON), ai)
    assert result.status == Status.PASS
    item = submitted(ai)[0]
    assert item.text == "Menu"
    assert item.details == {"role": "button", "visible_label": "Menu", "name_source": "contenu"}


def test_713_label_for_gives_the_name(context_factory, run_rgaa):
    ai = text_services()
    run_rgaa(Test713(), context_factory('<label for="q">Recherche</label><input id="q" oninput="s()">'), ai)
    assert submitted(ai)[0].text == "Recherche"
    assert submitted(ai)[0].details["name_source"] == "label"


def test_713_irrelevant_name_fails(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    result = run_rgaa(Test713(), context_factory(MENU_BUTTON), ai)
    assert result.status == Status.FAIL
    assert "n'est pas pertinent" in result.findings[0].message


@pytest.mark.parametrize(
    ("html", "fragment"),
    [
        ('<div onclick="x()">Ouvrir</div>', "de rôle"),
        ('<button onclick="x()"></button>', "de nom accessible"),
        ('<button onclick="x()" aria-label="Fermer la fenêtre">Annuler</button>', "ne contient pas l'intitulé visible"),
    ],
)
def test_713_deterministic_failures_skip_ai(html, fragment, context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test713(), context_factory(html), ai)
    assert result.status == Status.FAIL
    assert fragment in result.findings[0].message
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_713_punctuation_is_ignored_in_label(context_factory, run_rgaa):
    html = '<label for="q">Recherche :</label><input id="q" aria-label="Champ de recherche" oninput="s()">'
    assert run_rgaa(Test713(), context_factory(html), text_services()).status == Status.PASS


def test_unnamed_menu_container_is_not_required_to_have_a_name(context_factory, run_rgaa):
    html = '<div role="menu"><div role="menuitem" tabindex="-1">Option 1</div></div>'
    assert run_rgaa(Test711(), context_factory(html)).status == Status.PASS
    result = run_rgaa(Test713(), context_factory(html), text_services())
    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_unnamed_progressbar_fails(context_factory, run_rgaa):
    html = '<div role="progressbar" aria-valuenow="60">60%</div>'
    assert run_rgaa(Test711(), context_factory(html)).status == Status.FAIL


def test_713_symbol_label_is_not_required_in_name(context_factory, run_rgaa):
    ai = text_services()
    html = '<button onclick="x()" aria-label="Fermer">×</button>'
    assert run_rgaa(Test713(), context_factory(html), ai).status == Status.PASS


def test_713_without_ai_needs_review(context_factory, run_rgaa):
    result = run_rgaa(Test713(), context_factory(MENU_BUTTON))
    assert result.status == Status.NEEDS_REVIEW


def test_713_ai_exception_gives_error(context_factory, run_rgaa):
    ai = text_services(relevance_answer=RuntimeError("panne"))
    assert run_rgaa(Test713(), context_factory(MENU_BUTTON), ai).status == Status.ERROR


def test_713_low_confidence_needs_review(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False, confidence="low"))
    assert run_rgaa(Test713(), context_factory(MENU_BUTTON), ai).status == Status.NEEDS_REVIEW
