"""Critère RGAA 11.13 : finalité des champs concernant l'utilisateur (autocomplete)."""

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_13 import Test11131, parse_autocomplete
from tests.ai_fakes import relevance, text_services


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


def test_fail_gives_line_and_snippet(context_factory, run_rgaa):
    html = field("Code postal").replace("<input", "\n<input")
    finding = run_rgaa(Test11131(), context_factory(html), text_services()).findings[0]
    assert (finding.line, finding.snippet) == (2, '<input id="f">')


def user_field_ai(answer):
    """Le champ concerne l'utilisateur ; ``answer`` juge la valeur autocomplete."""
    ai = text_services()
    ai.text_relevance_analyzer.analyze_relevance.side_effect = lambda kind, items: (
        [relevance(True) if kind == "user_data_field" else answer] * len(items)
    )
    return ai


@pytest.mark.parametrize(
    ("html", "after"),
    [
        (field("Code postal"), '<input id="f"> → <input id="f" autocomplete="postal-code">'),
        (
            field("Votre contact", "type='email'"),
            '<input id="f" type="email"> → <input id="f" type="email" autocomplete="email">',
        ),
        (
            field("Votre petit nom", "autocomplete='work given-name'"),
            '<input id="f" autocomplete="work given-name"> → <input id="f" autocomplete="given-name">',
        ),
    ],
    ids=["étiquette connue", "type du champ", "valeur mal formée"],
)
def test_deduced_autocomplete_value_is_shown(html, after, context_factory, run_rgaa):
    finding = run_rgaa(Test11131(), context_factory(html), user_field_ai(relevance(True))).findings[0]
    assert finding.recommendation.endswith(f"Exemple : {after}")


def test_unknown_purpose_has_no_example(context_factory, run_rgaa):
    finding = run_rgaa(Test11131(), context_factory(field("Votre contact")), user_field_ai(relevance(True))).findings[0]
    assert "Exemple" not in finding.recommendation


@pytest.mark.parametrize(
    ("suggestion", "example"),
    [
        ("tel", ' Exemple : <input id="f" autocomplete="email"> → <input id="f" autocomplete="tel">'),
        ("téléphone", ""),
    ],
    ids=["valeur valide", "valeur inventée"],
)
def test_ai_suggestion_is_used_only_when_valid(suggestion, example, context_factory, run_rgaa):
    html = field("Votre numéro de portable", "autocomplete='email'")
    result = run_rgaa(Test11131(), context_factory(html), user_field_ai(relevance(False, suggestion=suggestion)))
    assert result.findings[0].recommendation.endswith(f"Proposition : « {suggestion} ».{example}")
