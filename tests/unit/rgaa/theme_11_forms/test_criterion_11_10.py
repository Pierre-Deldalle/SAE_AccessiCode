"""Critère RGAA 11.10 : contrôle de saisie."""

import pytest
from ai_fakes import relevance, text_services

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_10 import (
    Test11101,
    Test11102,
    Test11103,
    Test11104,
    Test11105,
    Test11106,
    Test11107,
)

ALL = [Test11101, Test11102, Test11103, Test11104, Test11105, Test11106, Test11107]
TWO_FIELDS = "<form><label for='a'>Nom (obligatoire)</label><input id='a' required>{second}</form>"
ERROR = (
    "<form><label for='a'>Courriel</label><input id='a' type='email' required aria-describedby='e'>"
    "<p id='e' class='error'>{message}</p></form>"
)


@pytest.mark.parametrize("cls", ALL)
def test_no_field_is_not_applicable(cls, context_factory, run_rgaa):
    assert run_rgaa(cls(), context_factory("<p>Texte</p>"), text_services()).status == Status.NOT_APPLICABLE


# ---- 11.10.1 / 11.10.2 -----------------------------------------------


def test_11101_single_field_form_is_exempt(context_factory, run_rgaa):
    assert run_rgaa(Test11101(), context_factory("<form><input required></form>")).status == Status.NOT_APPLICABLE


def test_11101_required_fields_signalled(context_factory, run_rgaa):
    html = TWO_FIELDS.format(second="<label for='b'>Ville *</label><input id='b'>")
    assert run_rgaa(Test11101(), context_factory(html)).status == Status.PASS


def test_11101_optional_fields_indicated_is_exempt(context_factory, run_rgaa):
    html = TWO_FIELDS.format(second="<label for='b'>Ville (facultatif)</label><input id='b'>")
    assert run_rgaa(Test11101(), context_factory(html)).status == Status.NOT_APPLICABLE


def test_11101_no_field_signalled_needs_review(context_factory, run_rgaa):
    html = "<form><label for='a'>Nom</label><input id='a'><label for='b'>Ville</label><input id='b'></form>"
    assert run_rgaa(Test11101(), context_factory(html)).status == Status.NEEDS_REVIEW


def test_11102_required_field_with_visible_mention_passes(context_factory, run_rgaa):
    html = TWO_FIELDS.format(second="<label for='b'>Ville</label><input id='b'>")
    assert run_rgaa(Test11102(), context_factory(html)).status == Status.PASS


def test_11102_required_attribute_without_visible_mention_fails(context_factory, run_rgaa):
    html = "<form><label for='a'>Nom</label><input id='a' required><label for='b'>Ville</label><input id='b'></form>"
    assert run_rgaa(Test11102(), context_factory(html)).status == Status.FAIL


def test_11102_global_notice_passes(context_factory, run_rgaa):
    html = (
        "<form><p>Tous les champs sont obligatoires.</p><label for='a'>Nom</label><input id='a' required>"
        "<label for='b'>Ville</label><input id='b' required></form>"
    )
    assert run_rgaa(Test11102(), context_factory(html)).status == Status.PASS


# ---- 11.10.3 / 11.10.6 -----------------------------------------------


def test_11103_aria_invalid_passes(context_factory, run_rgaa):
    html = "<form><input required aria-invalid='true' aria-label='Nom'></form>"
    assert run_rgaa(Test11103(), context_factory(html), text_services()).status == Status.PASS


def test_11103_error_message_identifying_field(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(True))
    html = ERROR.format(message="Le courriel est obligatoire.")
    assert run_rgaa(Test11103(), context_factory(html), ai).status == Status.PASS
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "error_identification"
    assert items[0].text == "Le courriel est obligatoire."
    assert items[0].context == "Courriel"


def test_11103_generic_error_message_fails(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    assert run_rgaa(Test11103(), context_factory(ERROR.format(message="Erreur")), ai).status == Status.FAIL


def test_11103_without_error_in_dom_is_not_applicable(context_factory, run_rgaa):
    html = "<form><input required aria-label='Nom'></form>"
    assert run_rgaa(Test11103(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_11106_format_error_message_uncertain(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(None))
    html = ERROR.format(message="Format invalide")
    assert run_rgaa(Test11106(), context_factory(html), ai).status == Status.NEEDS_REVIEW


# ---- 11.10.4 ---------------------------------------------------------


def test_11104_associated_error_message_passes(context_factory, run_rgaa):
    html = "<form><input required aria-invalid='true' aria-describedby='e'><p id='e'>Erreur : nom manquant</p></form>"
    assert run_rgaa(Test11104(), context_factory(html)).status == Status.PASS


def test_11104_error_without_associated_message_fails(context_factory, run_rgaa):
    html = "<form><input required aria-invalid='true' aria-label='Nom'></form>"
    assert run_rgaa(Test11104(), context_factory(html)).status == Status.FAIL


# ---- 11.10.5 / 11.10.7 -----------------------------------------------


def test_11105_format_instruction_judged_by_ai(context_factory, run_rgaa):
    html = "<form><label for='d'>Date (jj/mm/aaaa)</label><input id='d' type='date' required></form>"
    ok = text_services(relevance_answer=relevance(True))
    assert run_rgaa(Test11105(), context_factory(html), ok).status == Status.PASS
    kind, items = ok.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "format_instruction"
    assert items[0].details["type"] == "date"
    ko = text_services(relevance_answer=relevance(False))
    assert run_rgaa(Test11105(), context_factory(html), ko).status == Status.FAIL


def test_11107_invalid_field_with_format(context_factory, run_rgaa):
    html = "<form><label for='c'>Code postal</label><input id='c' pattern='[0-9]{5}' aria-invalid='true'></form>"
    assert run_rgaa(Test11107(), context_factory(html)).status == Status.NEEDS_REVIEW
    broken = text_services(relevance_answer=RuntimeError("panne"))
    assert run_rgaa(Test11107(), context_factory(html), broken).status == Status.ERROR
