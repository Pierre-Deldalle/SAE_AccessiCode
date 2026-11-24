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


# Emplacement des observations (ligne et extrait HTML)


@pytest.mark.parametrize(
    ("test_class", "html", "snippet"),
    [
        (Test711, '<div id="ouvrir" onclick="open()">Ouvrir</div>', '<div id="ouvrir" onclick="open()">Ouvrir</div>'),
        (Test712, MENU_BUTTON, MENU_BUTTON),
        (Test713, '<div onclick="x()">Ouvrir</div>', '<div onclick="x()">Ouvrir</div>'),
        (
            Test713,
            '<button onclick="x()" aria-label="Fermer la fenêtre">Annuler</button>',
            '<button onclick="x()" aria-label="Fermer la fenêtre">Annuler</button>',
        ),
    ],
)
def test_findings_give_line_and_snippet(test_class, html, snippet, context_factory, run_rgaa):
    result = run_rgaa(test_class(), context_factory(f"<p>Introduction</p>\n\n{html}"), text_services())
    assert result.status in {Status.FAIL, Status.NEEDS_REVIEW}
    assert (result.findings[0].line, result.findings[0].snippet) == (3, snippet)


def test_713_ai_failure_gives_line_and_snippet(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    result = run_rgaa(Test713(), context_factory(f"<p>Introduction</p>\n{MENU_BUTTON}"), ai)
    assert result.status == Status.FAIL
    assert (result.findings[0].line, result.findings[0].snippet) == (2, MENU_BUTTON)


# Correction concrète : exemple « avant → après » et proposition de l'IA


@pytest.mark.parametrize(
    ("html", "after"),
    [
        ('<div onclick="ouvrir()">Ouvrir</div>', '<div onclick="ouvrir()" role="button" tabindex="0">'),
        (
            "<span onclick=\"location.href='/aide'\">Aide</span>",
            '<span onclick="location.href=\'/aide\'" role="link" tabindex="0">',
        ),
        (
            '<div role="checkbox" tabindex="0" onclick="t()">Newsletter</div>',
            '<div role="checkbox" tabindex="0" onclick="t()" aria-checked="false">',
        ),
    ],
)
def test_711_recommendation_shows_the_fix(html, after, context_factory, run_rgaa):
    result = run_rgaa(Test711(), context_factory(html))
    assert result.status == Status.FAIL
    assert result.findings[0].recommendation.endswith(f"→ {after}")


def test_711_missing_name_alone_has_no_example(context_factory, run_rgaa):
    result = run_rgaa(Test711(), context_factory('<button onclick="x()"><svg></svg></button>'))
    assert "Exemple" not in result.findings[0].recommendation


def test_713_label_missing_from_name_shows_removal_of_aria_label(context_factory, run_rgaa):
    html = '<button onclick="x()" aria-label="Fermer la fenêtre">Annuler</button>'
    result = run_rgaa(Test713(), context_factory(html), text_services())
    assert result.findings[0].recommendation.endswith(
        'Exemple : <button onclick="x()" aria-label="Fermer la fenêtre"> → <button onclick="x()">'
    )


def test_713_ai_proposal_is_shown_on_fail(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False, suggestion="Ouvrir le menu principal"))
    result = run_rgaa(Test713(), context_factory(MENU_BUTTON), ai)
    assert result.status == Status.FAIL
    recommendation = result.findings[0].recommendation
    assert "Proposition : « Ouvrir le menu principal »." in recommendation
    assert recommendation.endswith(
        '<button id="menu" onclick="toggle()" aria-expanded="false" aria-label="Ouvrir le menu principal">'
    )


def test_713_ai_proposal_is_ignored_when_unsure(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False, confidence="low", suggestion="Ouvrir le menu"))
    result = run_rgaa(Test713(), context_factory(MENU_BUTTON), ai)
    assert result.status == Status.NEEDS_REVIEW
    assert result.findings[0].recommendation == (
        "Donner au composant un nom qui décrit sa fonction et un rôle qui correspond à son comportement."
    )
