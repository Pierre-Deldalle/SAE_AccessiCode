import pytest
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_8 import Test1281, Test1282


@pytest.mark.parametrize('value,expected', [(True,Status.PASS),(False,Status.FAIL),(None,Status.NEEDS_REVIEW)])
def test_1281(context_factory, run_rgaa, value, expected):
    c = context_factory('<button>Ouvrir</button><a href="#x">Lien</a>')
    if value is not None:
        c.navigation_evidence['12.8.1'] = {'tab_order_coherent': value}
    assert run_rgaa(Test1281(), c).status == expected


@pytest.mark.parametrize('value,expected', [(True,Status.PASS),(False,Status.FAIL),(None,Status.NEEDS_REVIEW)])
def test_1282(context_factory, run_rgaa, value, expected):
    c = context_factory('<button aria-expanded="false">Ouvrir</button><script>/* dynamic */</script>')
    if value is not None:
        c.navigation_evidence['12.8.2'] = {'dynamic_tab_order_coherent': value}
    assert run_rgaa(Test1282(), c).status == expected


def test_1282_na(context_factory, run_rgaa):
    assert run_rgaa(Test1282(), context_factory('<p>Texte</p>')).status == Status.NOT_APPLICABLE
