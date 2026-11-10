import pytest
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_13 import Test11131


@pytest.mark.parametrize(('html', 'expected'), [
    ('<form></form>', TestStatus.NOT_APPLICABLE),
    ('<form><label for="a">Courriel</label><input id="a" autocomplete="email"></form>', TestStatus.PASS),
    ('<form><label for="a">Courriel</label><input id="a"></form>', TestStatus.FAIL),
    ('<form><label for="a">Courriel</label><input id="a" autocomplete="nonsense"></form>', TestStatus.FAIL),
    ('<form><label for="a">Courriel</label><input id="a" autocomplete="shipping email"></form>', TestStatus.PASS),
    ('<form><label for="a">Nom</label><input id="a" autocomplete="email"></form>', TestStatus.NEEDS_REVIEW),
    ('<form><label for="a">Champ inconnu</label><input id="a"></form>', TestStatus.NEEDS_REVIEW),
])
def test_cases(context_factory, run_rgaa, html, expected):
    assert run_rgaa(Test11131(), context_factory(html)).status == expected
