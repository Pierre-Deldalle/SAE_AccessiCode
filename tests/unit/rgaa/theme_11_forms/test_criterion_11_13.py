"""Critère RGAA 11.13 : finalité des champs concernant l'utilisateur (autocomplete)."""

import pytest
from ai_fakes import relevance, text_services

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_13 import Test11131, parse_autocomplete


def field(label: str, attributes: str = "") -> str:
    return f"<form><label for='f'>{label}</label><input id='f' {attributes}></form>"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("email", "email"),
        ("section-a shipping street-address", "street-address"),
        ("work tel", "tel"),
        ("billing work email", "email"),
        ("work given-name", None),
        ("given-name family-name", None),
        ("nom", None),
        ("", None),
    ],
)
def test_parse_autocomplete(value, expected):
    assert parse_autocomplete(value) == expected


def test_no_field_is_not_applicable(context_factory, run_rgaa):
    assert run_rgaa(Test11131(), context_factory("<p>Texte</p>"), text_services()).status == Status.NOT_APPLICABLE


def test_obvious_user_field_with_matching_value_passes_without_ai(context_factory, run_rgaa):
    ai = text_services()
    html = field("Courriel", "type='email' autocomplete='email'")
    assert run_rgaa(Test11131(), context_factory(html), ai).status == Status.PASS
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_obvious_user_field_without_autocomplete_fails(context_factory, run_rgaa):
    result = run_rgaa(Test11131(), context_factory(field("Code postal")), text_services())
    assert result.status == Status.FAIL
    assert 'autocomplete="postal-code"' in result.findings[0].recommendation


def test_invalid_autocomplete_value_fails(context_factory, run_rgaa):
    html = field("Prénom", "autocomplete='work given-name'")
    assert run_rgaa(Test11131(), context_factory(html), text_services()).status == Status.FAIL


def test_field_judged_as_user_data_by_ai(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(True))
    result = run_rgaa(Test11131(), context_factory(field("Votre numéro de portable")), ai)
    assert result.status == Status.FAIL
    assert ai.text_relevance_analyzer.analyze_relevance.call_args_list[0].args[0] == "user_data_field"


def test_field_not_about_the_user_is_not_applicable(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    assert run_rgaa(Test11131(), context_factory(field("Quantité")), ai).status == Status.NOT_APPLICABLE


def test_autocomplete_value_relevance_judged_by_ai(context_factory, run_rgaa):
    html = field("Nom", "autocomplete='email'")
    ai = text_services(relevance_answer=[relevance(True)])
    ai.text_relevance_analyzer.analyze_relevance.side_effect = lambda kind, items: (
        [relevance(True)] * len(items) if kind == "user_data_field" else [relevance(False)] * len(items)
    )
    result = run_rgaa(Test11131(), context_factory(html), ai)
    assert result.status == Status.FAIL
    assert "« email »" in result.findings[0].message


def test_search_field_is_excluded(context_factory, run_rgaa):
    html = "<form role='search'><input type='search' aria-label='Rechercher'></form>"
    assert run_rgaa(Test11131(), context_factory(html), text_services()).status == Status.NOT_APPLICABLE


def test_low_confidence_no_ai_and_error(context_factory, run_rgaa):
    html = field("Votre numéro de portable")
    low = text_services(relevance_answer=relevance(True, confidence="low"))
    assert run_rgaa(Test11131(), context_factory(html), low).status == Status.NEEDS_REVIEW
    assert run_rgaa(Test11131(), context_factory(html)).status == Status.NEEDS_REVIEW
    broken = text_services(relevance_answer=RuntimeError("panne"))
    assert run_rgaa(Test11131(), context_factory(html), broken).status == Status.ERROR
