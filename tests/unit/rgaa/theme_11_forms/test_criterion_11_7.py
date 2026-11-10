from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_7 import Test1171


def test_empty(context_factory, run_rgaa):
    assert run_rgaa(Test1171(), context_factory('<form></form>')).status == TestStatus.NOT_APPLICABLE


def test_named_group_review(context_factory, run_rgaa):
    html = '<fieldset><legend>Coordonnées</legend><input><input></fieldset>'
    result = run_rgaa(Test1171(), context_factory(html))
    assert result.status == TestStatus.NEEDS_REVIEW and result.findings


def test_missing_legend_is_116_not_117(context_factory, run_rgaa):
    assert run_rgaa(Test1171(), context_factory('<fieldset><input></fieldset>')).status == TestStatus.NOT_APPLICABLE
