"""Critère RGAA 11.2 : pertinence des étiquettes."""

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_2 import (
    Test1121,
    Test1122,
    Test1123,
    Test1124,
    Test1125,
    Test1126,
)
from tests.ai_fakes import relevance, text_services

LABEL = '<form><label for="m">Adresse e-mail</label><input id="m" type="email" name="mail"></form>'


@pytest.mark.parametrize("cls", [Test1121, Test1122, Test1123, Test1124, Test1125, Test1126])
def test_no_field_is_not_applicable(cls, context_factory, run_rgaa):
    assert run_rgaa(cls(), context_factory("<p>Texte</p>"), text_services()).status == Status.NOT_APPLICABLE


@pytest.mark.parametrize(
    ("cls", "html"),
    [
        (Test1121, LABEL),
        (Test1121, '<label>Adresse e-mail<input type="email"></label>'),
        (Test1122, '<input type="email" title="Adresse e-mail">'),
        (Test1123, '<input type="email" aria-label="Adresse e-mail">'),
        (Test1124, '<span id="a">Adresse</span><span id="b">e-mail</span><input type="email" aria-labelledby="a b">'),
    ],
)
def test_relevant_label_passes(cls, html, context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(True))
    assert run_rgaa(cls(), context_factory(html), ai).status == Status.PASS
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "form_label"
    assert items[0].text == "Adresse e-mail"
    assert items[0].details["type"] == "email"


def test_1121_irrelevant_label_fails(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    result = run_rgaa(Test1121(), context_factory('<label for="a">Champ 1</label><input id="a">'), ai)
    assert result.status == Status.FAIL
    assert "« Champ 1 »" in result.findings[0].message


def test_1121_empty_label_fails_without_ai(context_factory, run_rgaa):
    ai = text_services()
    result = run_rgaa(Test1121(), context_factory('<label for="a"></label><input id="a">'), ai)
    assert result.status == Status.FAIL
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_1122_title_is_judged_even_with_a_label(context_factory, run_rgaa):
    ai = text_services()
    html = '<label for="a">Nom</label><input id="a" title="Votre nom de famille">'
    assert run_rgaa(Test1122(), context_factory(html), ai).status == Status.PASS
    assert ai.text_relevance_analyzer.analyze_relevance.call_args.args[1][0].text == "Votre nom de famille"


def test_1124_broken_reference_fails(context_factory, run_rgaa):
    result = run_rgaa(Test1124(), context_factory('<input aria-labelledby="absent">'), text_services())
    assert result.status == Status.FAIL


def test_low_confidence_no_ai_and_error(context_factory, run_rgaa):
    low = text_services(relevance_answer=relevance(True, confidence="low"))
    assert run_rgaa(Test1121(), context_factory(LABEL), low).status == Status.NEEDS_REVIEW
    assert run_rgaa(Test1121(), context_factory(LABEL)).status == Status.NEEDS_REVIEW
    broken = text_services(relevance_answer=RuntimeError("panne"))
    assert run_rgaa(Test1121(), context_factory(LABEL), broken).status == Status.ERROR


def test_mixed_fields_fail_over_review(context_factory, run_rgaa):
    html = '<label for="a">Nom</label><input id="a"><label for="b"></label><input id="b">'
    ai = text_services(relevance_answer=relevance(None))
    result = run_rgaa(Test1121(), context_factory(html), ai)
    assert result.status == Status.FAIL
    assert result.metadata["statuses"]["needs_review"] == 1


# ---- 11.2.5 (déterministe) -------------------------------------------


def test_1125_visible_label_included_in_accessible_name(context_factory, run_rgaa):
    html = '<label for="a">Nom</label><input id="a" aria-label="Nom de famille">'
    assert run_rgaa(Test1125(), context_factory(html)).status == Status.PASS


def test_1125_visible_label_missing_from_accessible_name(context_factory, run_rgaa):
    html = '<label for="a">Nom</label><input id="a" aria-label="Identifiant">'
    assert run_rgaa(Test1125(), context_factory(html)).status == Status.FAIL


# ---- 11.2.6 ----------------------------------------------------------

SEARCH = '<form><input type="search" aria-label="Rechercher"><button>Rechercher</button></form>'


def test_1126_adjacent_button_label_relevant(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(True))
    assert run_rgaa(Test1126(), context_factory(SEARCH), ai).status == Status.PASS
    assert ai.text_relevance_analyzer.analyze_relevance.call_args.args[1][0].text == "Rechercher"


def test_1126_adjacent_button_label_irrelevant(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    html = '<form><input type="search" aria-label="Rechercher"><button>OK</button></form>'
    assert run_rgaa(Test1126(), context_factory(html), ai).status == Status.FAIL


def test_1126_field_with_visible_label_is_out_of_scope(context_factory, run_rgaa):
    html = '<form><label for="q">Recherche</label><input id="q"><button>OK</button></form>'
    assert run_rgaa(Test1126(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_1126_empty_button_fails(context_factory, run_rgaa):
    html = '<form><input type="search" aria-label="Rechercher"><button></button></form>'
    assert run_rgaa(Test1126(), context_factory(html), text_services()).status == Status.FAIL


def test_empty_label_fail_gives_line_and_snippet(context_factory, run_rgaa):
    html = '<form>\n<label for="m"></label>\n<input id="m" type="email">\n</form>'
    finding = run_rgaa(Test1121(), context_factory(html), text_services()).findings[0]
    assert (finding.line, finding.snippet) == (3, '<input id="m" type="email">')


def test_ai_fail_gives_line_and_snippet(context_factory, run_rgaa):
    html = '<form>\n<input id="q" title="Champ">\n</form>'
    ai = text_services(relevance_answer=relevance(False))
    finding = run_rgaa(Test1122(), context_factory(html), ai).findings[0]
    assert (finding.line, finding.snippet) == (2, '<input id="q" title="Champ">')


def test_adjacent_button_fail_points_to_the_field(context_factory, run_rgaa):
    html = '<form>\n<input id="s" type="search" aria-label="Recherche"><button></button>\n</form>'
    finding = run_rgaa(Test1126(), context_factory(html), text_services()).findings[0]
    assert (finding.line, finding.snippet) == (2, '<input id="s" type="search" aria-label="Recherche">')


# Proposition de l'IA -------------------------------------------------------------------------------------------------

BASE = "Rédiger une étiquette qui indique précisément la donnée attendue dans le champ."


def test_ai_suggestion_is_shown_in_the_attribute_on_fail(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False, suggestion="Rechercher un produit"))
    finding = run_rgaa(Test1122(), context_factory('<form><input id="q" title="Champ"></form>'), ai).findings[0]
    assert finding.recommendation == (
        f"{BASE} Proposition : « Rechercher un produit ». "
        'Exemple : <input id="q" title="Champ"> → <input id="q" title="Rechercher un produit">'
    )


def test_ai_suggestion_for_a_label_element_has_no_example(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False, suggestion="Adresse e-mail"))
    html = '<form><label for="m">Champ 1</label><input id="m" type="email"></form>'
    finding = run_rgaa(Test1121(), context_factory(html), ai).findings[0]
    assert finding.recommendation == f"{BASE} Proposition : « Adresse e-mail »."


@pytest.mark.parametrize(
    ("answer", "status"),
    [
        (relevance(False, confidence="low", suggestion="Nom de famille"), Status.NEEDS_REVIEW),
        (relevance(False), Status.FAIL),
    ],
    ids=["confiance faible", "sans suggestion"],
)
def test_no_proposition_without_a_certain_suggestion(answer, status, context_factory, run_rgaa):
    ai = text_services(relevance_answer=answer)
    result = run_rgaa(Test1122(), context_factory('<form><input id="q" title="Champ"></form>'), ai)
    assert result.status == status
    assert result.findings[0].recommendation == BASE


def test_suggestion_on_pass_is_ignored(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(True, suggestion="Autre"))
    result = run_rgaa(Test1122(), context_factory('<form><input id="q" title="Nom de famille"></form>'), ai)
    assert (result.status, result.findings) == (Status.PASS, [])
