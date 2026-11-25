"""Critère RGAA 7.5 : messages de statut (catégorie confirmée par l'IA, rôle vérifié sans IA)."""

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_07_scripts.criterion_7_5 import Test751, Test752, Test753
from tests.ai_fakes import structure, text_services

SUCCESS = '<div id="msg">Votre message a été envoyé.</div>'
ERROR = '<p id="err">Erreur : le champ e-mail est obligatoire.</p>'
PROGRESS = '<div id="up">Chargement en cours…</div>'


def submitted(ai, kind):
    called_kind, items = ai.structure_analyzer.classify_candidates.call_args.args
    assert called_kind == kind
    return items


@pytest.mark.parametrize("test_class", [Test751, Test752, Test753])
def test_no_candidate_is_not_applicable(test_class, context_factory, run_rgaa):
    ai = text_services()
    assert run_rgaa(test_class(), context_factory("<p>Bienvenue.</p>"), ai).status == Status.NOT_APPLICABLE
    ai.structure_analyzer.classify_candidates.assert_not_called()


@pytest.mark.parametrize(
    ("test_class", "html", "kind"),
    [
        (Test751, SUCCESS, "status_success"),
        (Test752, ERROR, "status_error"),
        (Test753, PROGRESS, "status_progress"),
    ],
)
def test_unmarked_status_message_fails(test_class, html, kind, context_factory, run_rgaa):
    ai = text_services(structure_answer=structure(True))
    result = run_rgaa(test_class(), context_factory(html), ai)
    assert result.status == Status.FAIL
    assert "Aucun marquage de région dynamique" in submitted(ai, kind)[0].context


@pytest.mark.parametrize(
    ("test_class", "html"),
    [
        (Test751, '<div role="status">Votre message a été envoyé.</div>'),
        (Test751, '<div aria-live="polite" aria-atomic="true">Article ajouté au panier.</div>'),
        (Test751, "<output>3 résultats</output>"),
        (Test752, '<p role="alert">Erreur : champ obligatoire.</p>'),
        (Test752, '<p aria-live="assertive" aria-atomic="true">Mot de passe invalide.</p>'),
        (Test753, '<div role="log">Étape 2 sur 4</div>'),
        (Test753, '<progress value="40" max="100">40 %</progress>'),
        (Test753, '<div aria-live="polite">Chargement en cours</div>'),
    ],
)
def test_expected_marking_passes_without_ai(test_class, html, context_factory, run_rgaa):
    ai = text_services()
    assert run_rgaa(test_class(), context_factory(html), ai).status == Status.PASS
    ai.structure_analyzer.classify_candidates.assert_not_called()


def test_other_category_marking_is_judged(context_factory, run_rgaa):
    """Un message d'erreur marqué role=status doit porter role=alert (7.5.2)."""
    ai = text_services(structure_answer=structure(True))
    html = '<p role="status">Erreur : paiement refusé.</p>'
    result = run_rgaa(Test752(), context_factory(html), ai)
    assert result.status == Status.FAIL
    assert result.findings[0].evidence["role"] == "status"


def test_static_text_is_not_a_status_message(context_factory, run_rgaa):
    ai = text_services(structure_answer=structure(False))
    html = "<p>Les champs marqués d'un astérisque sont obligatoires.</p>"
    assert run_rgaa(Test752(), context_factory(html), ai).status == Status.NOT_APPLICABLE


def test_headings_buttons_and_links_are_not_candidates(context_factory, run_rgaa):
    html = "<h2>Erreurs fréquentes</h2><button>Erreur</button><a href='/e'>Erreur</a>"
    assert run_rgaa(Test752(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_children_of_a_live_region_are_not_repeated(context_factory, run_rgaa):
    ai = text_services(structure_answer=structure(True))
    html = '<div role="alert"><p>Votre message a été envoyé.</p></div>'
    result = run_rgaa(Test751(), context_factory(html), ai)
    assert len(submitted(ai, "status_success")) == 1
    assert result.findings[0].element == "div[index=0]"


def test_uncertain_answer_needs_review(context_factory, run_rgaa):
    ai = text_services(structure_answer=structure(True, confidence="low"))
    assert run_rgaa(Test751(), context_factory(SUCCESS), ai).status == Status.NEEDS_REVIEW


def test_without_ai_needs_review(context_factory, run_rgaa):
    result = run_rgaa(Test751(), context_factory(SUCCESS))
    assert result.status == Status.NEEDS_REVIEW
    assert "IA n'est pas disponible" in result.findings[0].message


def test_ai_exception_gives_error(context_factory, run_rgaa):
    ai = text_services(structure_answer=RuntimeError("panne"))
    assert run_rgaa(Test751(), context_factory(SUCCESS), ai).status == Status.ERROR


# Emplacement des observations (ligne et extrait HTML)


@pytest.mark.parametrize(("test_class", "html"), [(Test751, SUCCESS), (Test752, ERROR), (Test753, PROGRESS)])
def test_unmarked_status_message_gives_line_and_snippet(test_class, html, context_factory, run_rgaa):
    ai = text_services(structure_answer=structure(True))
    result = run_rgaa(test_class(), context_factory(f"<h1>Contact</h1>\n{html}"), ai)
    assert result.status == Status.FAIL
    assert (result.findings[0].line, result.findings[0].snippet) == (2, html)


# Correction concrète : exemple « avant → après »


@pytest.mark.parametrize(
    ("test_class", "html", "after"),
    [
        (Test751, SUCCESS, '<div id="msg" role="status">'),
        (Test752, ERROR, '<p id="err" role="alert">'),
        (Test753, PROGRESS, '<div id="up" role="status">'),
    ],
)
def test_unmarked_status_message_shows_the_role_to_add(test_class, html, after, context_factory, run_rgaa):
    ai = text_services(structure_answer=structure(True))
    result = run_rgaa(test_class(), context_factory(html), ai)
    assert result.findings[0].recommendation.endswith(f"→ {after}")


def test_uncertain_status_message_has_no_example(context_factory, run_rgaa):
    ai = text_services(structure_answer=structure(True, confidence="low"))
    result = run_rgaa(Test751(), context_factory(SUCCESS), ai)
    assert result.status == Status.NEEDS_REVIEW
    assert "Exemple" not in result.findings[0].recommendation
