from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_6 import Test1161


def test_empty(context_factory, run_rgaa):
    assert run_rgaa(Test1161(), context_factory('<form></form>')).status == TestStatus.NOT_APPLICABLE


def test_legend(context_factory, run_rgaa):
    html = '<form><fieldset><legend>Identité</legend><input><input></fieldset></form>'
    assert run_rgaa(Test1161(), context_factory(html)).status == TestStatus.PASS


def test_missing_legend(context_factory, run_rgaa):
    html = '<form><fieldset><input><input></fieldset></form>'
    assert run_rgaa(Test1161(), context_factory(html)).status == TestStatus.FAIL


def test_aria_group(context_factory, run_rgaa):
    html = '<form><div role="group" aria-label="Adresse"><input><input></div></form>'
    assert run_rgaa(Test1161(), context_factory(html)).status == TestStatus.PASS


def test_unstructured_radio(context_factory, run_rgaa):
    html = '<form><input type="radio" name="x"><input type="radio" name="x"></form>'
    assert run_rgaa(Test1161(), context_factory(html)).status == TestStatus.NEEDS_REVIEW
