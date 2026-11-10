import pytest

from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_8 import Test1181, Test1182, Test1183


@pytest.mark.parametrize(('test', 'html', 'expected'), [
    (Test1181, '<form></form>', TestStatus.NOT_APPLICABLE),
    (Test1181, '<select><option>A</option><option>B</option></select>', TestStatus.NEEDS_REVIEW),
    (Test1181, '<select><optgroup label="A"><option>A</option></optgroup></select>', TestStatus.PASS),
    (Test1182, '<select></select>', TestStatus.NOT_APPLICABLE),
    (Test1182, '<select><optgroup label="G"><option>A</option></optgroup></select>', TestStatus.PASS),
    (Test1182, '<select><optgroup><option>A</option></optgroup></select>', TestStatus.FAIL),
    (Test1183, '<select></select>', TestStatus.NOT_APPLICABLE),
    (Test1183, '<select><optgroup label=""><option>A</option></optgroup></select>', TestStatus.FAIL),
    (Test1183, '<select><optgroup label="Pays"><option>France</option></optgroup></select>', TestStatus.NEEDS_REVIEW),
])
def test_cases(context_factory, run_rgaa, test, html, expected):
    assert run_rgaa(test(), context_factory(html)).status == expected
