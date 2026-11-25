"""Critère RGAA 5.3 : tableaux de mise en forme (role="presentation" et contenu linéarisé)."""

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_05_tables.criterion_5_3 import Test531
from tests.ai_fakes import relevance, text_services

LAYOUT = """
<table role="presentation" id="mise-en-page">
    <tr><td>Bienvenue sur le site de la médiathèque.</td><td>Horaires : du mardi au samedi.</td></tr>
</table>
"""
WITHOUT_ROLE = LAYOUT.replace(' role="presentation"', "")


def test_data_table_is_not_applicable(context_factory, run_rgaa):
    html = "<table><tr><th>Nom</th></tr><tr><td>Dupont</td></tr></table>"
    assert run_rgaa(Test531(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_table_with_caption_is_a_data_table(context_factory, run_rgaa):
    html = "<table><caption>Tarifs</caption><tr><td>Adulte</td><td>5 €</td></tr></table>"
    assert run_rgaa(Test531(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_missing_presentation_role_fails_without_ai(context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test531(), context_factory(WITHOUT_ROLE), ai)
    assert result.status == Status.FAIL
    assert 'role="presentation"' in result.findings[0].message
    assert result.findings[0].line == 2
    assert result.findings[0].snippet == " ".join(WITHOUT_ROLE.split())
    assert result.findings[0].recommendation.endswith(
        'Exemple : <table id="mise-en-page"> → <table id="mise-en-page" role="presentation">'
    )
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_presentation_role_example_replaces_another_role(context_factory, run_rgaa):
    html = '<table role="table" class="grille"><tr><td>Logo</td><td>Menu</td></tr></table>'
    result = run_rgaa(Test531(), context_factory(html), text_services())
    assert result.status == Status.FAIL
    assert result.findings[0].recommendation.endswith(
        'Exemple : <table role="table" class="grille"> → <table role="presentation" class="grille">'
    )


def test_incomprehensible_content_has_no_example_nor_proposal(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False, suggestion="Texte réordonné"))
    result = run_rgaa(Test531(), context_factory(LAYOUT), ai)
    assert result.status == Status.FAIL
    assert result.findings[0].recommendation == (
        "Réorganiser le tableau pour que le contenu, lu cellule par cellule, garde son sens."
    )


def test_comprehensible_content_passes(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(True))
    result = run_rgaa(Test531(), context_factory(LAYOUT), ai)
    assert result.status == Status.PASS
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "layout_table_linearized"
    assert items[0].text == "Bienvenue sur le site de la médiathèque.\nHoraires : du mardi au samedi."


def test_incomprehensible_content_fails(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    result = run_rgaa(Test531(), context_factory(LAYOUT), ai)
    assert result.status == Status.FAIL
    assert result.findings[0].element == "table#mise-en-page"
    assert "n'est pas compréhensible" in result.findings[0].message
    assert result.findings[0].line == 2
    assert result.findings[0].snippet.startswith('<table role="presentation" id="mise-en-page"> <tr><td>Bienvenue')


def test_empty_layout_table_passes_without_ai(context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test531(), context_factory('<table role="presentation"><tr><td></td></tr></table>'), ai)
    assert result.status == Status.PASS
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_low_confidence_needs_review(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False, confidence="low"))
    assert run_rgaa(Test531(), context_factory(LAYOUT), ai).status == Status.NEEDS_REVIEW


def test_unknown_answer_needs_review(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(None))
    assert run_rgaa(Test531(), context_factory(LAYOUT), ai).status == Status.NEEDS_REVIEW


def test_without_ai_needs_review(context_factory, run_rgaa):
    assert run_rgaa(Test531(), context_factory(LAYOUT)).status == Status.NEEDS_REVIEW


def test_ai_exception_gives_error(context_factory, run_rgaa):
    ai = text_services(relevance_answer=RuntimeError("panne"))
    assert run_rgaa(Test531(), context_factory(LAYOUT), ai).status == Status.ERROR


def test_mixed_fail_and_needs_review(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(None))
    result = run_rgaa(Test531(), context_factory(LAYOUT + WITHOUT_ROLE), ai)
    assert result.status == Status.FAIL
    assert result.metadata["statuses"]["needs_review"] == 1
    assert result.metadata["statuses"]["fail"] == 1
