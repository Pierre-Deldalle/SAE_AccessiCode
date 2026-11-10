import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_10 import Test12101


@pytest.mark.parametrize('item,expected', [
    ({'key': 'a', 'disable': True}, Status.PASS),
    ({'key': 'a', 'disable': False, 'remap_with_modifier': False, 'focus_only': False}, Status.FAIL),
    ({'key': 'a'}, Status.NEEDS_REVIEW),
])
def test_shortcuts(context_factory, run_rgaa, item, expected):
    c = context_factory('<button>Action</button>')
    c.navigation_evidence['12.10.1'] = {'single_key_shortcuts': [item]}
    assert run_rgaa(Test12101(), c).status == expected


def test_na(context_factory, run_rgaa):
    assert run_rgaa(Test12101(), context_factory('<p>Texte</p>')).status == Status.NOT_APPLICABLE


def test_script_review(context_factory, run_rgaa):
    assert run_rgaa(Test12101(), context_factory('<script>document.addEventListener("keydown", fn)</script>')).status == Status.NEEDS_REVIEW
