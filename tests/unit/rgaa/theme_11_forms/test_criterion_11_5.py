from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_5 import Test1151


def test_empty(context_factory, run_rgaa):
    assert run_rgaa(Test1151(), context_factory('<form></form>')).status == TestStatus.NOT_APPLICABLE


def test_radio_group_pass(context_factory, run_rgaa):
    html = '<form><fieldset><legend>Choix</legend><input type="radio" name="x"><input type="radio" name="x"></fieldset></form>'
    assert run_rgaa(Test1151(), context_factory(html)).status == TestStatus.PASS


def test_radio_group_fail(context_factory, run_rgaa):
    html = '<form><input type="radio" name="x"><input type="radio" name="x"></form>'
    result = run_rgaa(Test1151(), context_factory(html))
    assert result.status == TestStatus.FAIL and result.findings


def test_single_field_no_group(context_factory, run_rgaa):
    assert run_rgaa(Test1151(), context_factory('<form><input name="address"></form>')).status == TestStatus.NOT_APPLICABLE


def test_multiple_unclassified_fields_still_review(context_factory, run_rgaa):
    assert run_rgaa(Test1151(), context_factory('<form><input name="street"><input name="city"></form>')).status == TestStatus.NEEDS_REVIEW
