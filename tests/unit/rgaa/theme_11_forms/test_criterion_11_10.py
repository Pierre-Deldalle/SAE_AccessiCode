import pytest

from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_10 import (
    Test11101,
    Test11102,
    Test11103,
    Test11104,
    Test11105,
    Test11106,
    Test11107,
)


@pytest.mark.parametrize(('test', 'html', 'expected'), [
    (Test11101, '<form></form>', TestStatus.NOT_APPLICABLE),
    (Test11101, '<form><input required></form>', TestStatus.PASS),
    (Test11101, '<form><input required><input></form>', TestStatus.NEEDS_REVIEW),
    (Test11102, '<form><input></form>', TestStatus.NOT_APPLICABLE),
    (Test11102, '<form><label>Obligatoire <input required></label></form>', TestStatus.NEEDS_REVIEW),
    (Test11103, '<form><input required></form>', TestStatus.NOT_APPLICABLE),
    (Test11103, '<form><input required aria-invalid="true"></form>', TestStatus.PASS),
    (Test11104, '<form><input required></form>', TestStatus.NOT_APPLICABLE),
    (Test11104, '<form><input required aria-invalid="true"></form>', TestStatus.NEEDS_REVIEW),
    (Test11105, '<form><input></form>', TestStatus.NOT_APPLICABLE),
    (Test11105, '<form><input type="email" required></form>', TestStatus.NEEDS_REVIEW),
    (Test11106, '<form><input type="email"></form>', TestStatus.NOT_APPLICABLE),
    (Test11106, '<form><input type="email" aria-invalid="true"></form>', TestStatus.PASS),
    (Test11107, '<form><input></form>', TestStatus.NOT_APPLICABLE),
    (Test11107, '<form><input type="email" aria-invalid="true"></form>', TestStatus.NEEDS_REVIEW),
])
def test_cases(context_factory, run_rgaa, test, html, expected):
    assert run_rgaa(test(), context_factory(html)).status == expected
