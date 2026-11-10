import pytest

from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_11 import Test11111, Test11112


@pytest.mark.parametrize(('test', 'html', 'expected'), [
    (Test11111, '<form><input type="email"></form>', TestStatus.NOT_APPLICABLE),
    (Test11111, '<form><input type="email" aria-invalid="true"></form>', TestStatus.NEEDS_REVIEW),
    (Test11112, '<form><input></form>', TestStatus.NOT_APPLICABLE),
    (Test11112, '<form><input aria-invalid="true"></form>', TestStatus.NEEDS_REVIEW),
])
def test_cases(context_factory, run_rgaa, test, html, expected):
    assert run_rgaa(test(), context_factory(html)).status == expected
