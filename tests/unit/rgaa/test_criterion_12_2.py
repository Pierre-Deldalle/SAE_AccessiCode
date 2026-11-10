import pytest
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_11 import Test12111


@pytest.mark.parametrize('value,expected', [(True,Status.PASS),(False,Status.FAIL),(None,Status.NEEDS_REVIEW)])
def test_panels(context_factory, run_rgaa, value, expected):
    c = context_factory('<button>Ouvrir</button>')
    c.navigation_evidence['12.11.1'] = {'interactive_additional_contents': [{'keyboard_reachable': value}]}
    assert run_rgaa(Test12111(), c).status == expected


def test_na(context_factory, run_rgaa):
    assert run_rgaa(Test12111(), context_factory('<p>Texte</p>')).status == Status.NOT_APPLICABLE


def test_script_review(context_factory, run_rgaa):
    assert run_rgaa(Test12111(), context_factory('<script>foo()</script>')).status == Status.NEEDS_REVIEW
