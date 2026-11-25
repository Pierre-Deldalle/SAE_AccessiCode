"""Critère RGAA 11.12 : confirmation, correction ou récupération des données."""

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_12 import Test11121, Test11122
from tests.ai_fakes import relevance, text_services

ORDER = "<h2>Paiement</h2><form><label for='c'>Numéro de carte</label><input id='c'><button>Payer</button></form>"
ORDER_CONFIRMED = (
    "<h2>Paiement</h2><form><label for='c'>Numéro de carte</label><input id='c'>"
    "<input type='checkbox' id='ok'><label for='ok'>Je confirme ma commande</label><button>Payer</button></form>"
)


@pytest.mark.parametrize("cls", [Test11121, Test11122])
def test_no_form_is_not_applicable(cls, context_factory, run_rgaa):
    assert run_rgaa(cls(), context_factory("<p>Texte</p>"), text_services()).status == Status.NOT_APPLICABLE


@pytest.mark.parametrize("cls", [Test11121, Test11122])
def test_search_form_is_excluded_without_ai(cls, context_factory, run_rgaa):
    ai = text_services()
    html = "<form role='search'><input type='search' aria-label='Rechercher'><button>OK</button></form>"
    assert run_rgaa(cls(), context_factory(html), ai).status == Status.NOT_APPLICABLE
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_out_of_scope_form_is_not_applicable(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(False))
    html = (
        "<h2>Contact</h2><form><label for='m'>Message</label><textarea id='m'></textarea>"
        "<button>Envoyer</button></form>"
    )
    assert run_rgaa(Test11121(), context_factory(html), ai).status == Status.NOT_APPLICABLE
    kind, items = ai.text_relevance_analyzer.analyze_relevance.call_args.args
    assert kind == "transaction_scope"
    assert "Titre : Contact" in items[0].text


def test_in_scope_form_with_confirmation_passes(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(True))
    assert run_rgaa(Test11121(), context_factory(ORDER_CONFIRMED), ai).status == Status.PASS


def test_in_scope_form_without_visible_mechanism_needs_review(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(True))
    result = run_rgaa(Test11121(), context_factory(ORDER), ai)
    assert result.status == Status.NEEDS_REVIEW
    assert "après la validation" in result.findings[0].message


def test_11122_uses_its_own_scope_question(context_factory, run_rgaa):
    ai = text_services(relevance_answer=relevance(True))
    run_rgaa(Test11122(), context_factory(ORDER_CONFIRMED), ai)
    assert ai.text_relevance_analyzer.analyze_relevance.call_args.args[0] == "sensitive_data_modification"


def test_unknown_scope_no_ai_and_error(context_factory, run_rgaa):
    low = text_services(relevance_answer=relevance(True, confidence="low"))
    assert run_rgaa(Test11121(), context_factory(ORDER), low).status == Status.NEEDS_REVIEW
    assert run_rgaa(Test11121(), context_factory(ORDER)).status == Status.NEEDS_REVIEW
    broken = text_services(relevance_answer=RuntimeError("panne"))
    assert run_rgaa(Test11121(), context_factory(ORDER), broken).status == Status.ERROR


@pytest.mark.parametrize(
    ("cls", "proof", "expected"),
    [
        (Test11121, {"in_scope": False}, Status.NOT_APPLICABLE),
        (Test11121, {"in_scope": True, "reversible": True}, Status.PASS),
        (Test11121, {"in_scope": True, "reversible": False, "review_and_correct": False,
                     "explicit_confirmation": False}, Status.FAIL),
        (Test11122, {"modifies_sensitive_data": False}, Status.NOT_APPLICABLE),
        (Test11122, {"modifies_sensitive_data": True, "recoverable": True}, Status.PASS),
    ],
)  # fmt: skip
def test_documented_evidence_has_priority(cls, proof, expected, context_factory, run_rgaa):
    ai = text_services()
    context = context_factory(ORDER)
    context.form_transaction_evidence = {0: proof}
    assert run_rgaa(cls(), context, ai).status == expected
    ai.text_relevance_analyzer.analyze_relevance.assert_not_called()


def test_fail_gives_line_and_snippet(context_factory, run_rgaa):
    context = context_factory(ORDER.replace("<form>", '\n<form id="paiement">'))
    context.form_transaction_evidence = {
        0: {"in_scope": True, "reversible": False, "review_and_correct": False, "explicit_confirmation": False}
    }
    finding = run_rgaa(Test11121(), context, text_services()).findings[0]
    assert finding.line == 2
    assert finding.snippet.startswith('<form id="paiement">')
