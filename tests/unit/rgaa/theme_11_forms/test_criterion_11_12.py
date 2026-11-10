import pytest
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_12 import Test11121, Test11122


@pytest.mark.parametrize('test', [Test11121, Test11122])
def test_empty(context_factory, run_rgaa, test):
    assert run_rgaa(test(), context_factory('<p>Bonjour</p>')).status == TestStatus.NOT_APPLICABLE


@pytest.mark.parametrize('test', [Test11121, Test11122])
def test_no_proof_review(context_factory, run_rgaa, test):
    assert run_rgaa(test(), context_factory('<form><input></form>')).status == TestStatus.NEEDS_REVIEW


@pytest.mark.parametrize(('test', 'proof', 'expected'), [
    (Test11121, {'in_scope': True, 'reversible': True}, TestStatus.PASS),
    (Test11121, {'in_scope': True, 'reversible': False, 'review_and_correct': False, 'explicit_confirmation': False}, TestStatus.FAIL),
    (Test11121, {'in_scope': True}, TestStatus.NEEDS_REVIEW),
    (Test11122, {'in_scope': True, 'modifies_sensitive_data': True, 'recoverable': True}, TestStatus.PASS),
    (Test11122, {'in_scope': True, 'modifies_sensitive_data': True, 'recoverable': False, 'explicit_confirmation': False}, TestStatus.FAIL),
    (Test11122, {'in_scope': True, 'modifies_sensitive_data': True}, TestStatus.NEEDS_REVIEW),
    (Test11122, {'in_scope': False}, TestStatus.NOT_APPLICABLE),
])
def test_proof(context_factory, run_rgaa, test, proof, expected):
    context = context_factory('<form><input></form>')
    context.form_transaction_evidence = {0: proof}
    assert run_rgaa(test(), context).status == expected
