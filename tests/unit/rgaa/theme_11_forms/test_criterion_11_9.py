import pytest

from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_11_forms.criterion_11_9 import Test1191, Test1192


@pytest.mark.parametrize(('test', 'html', 'expected'), [
    (Test1191, '<form></form>', TestStatus.NOT_APPLICABLE),
    (Test1191, '<form><button>Envoyer</button></form>', TestStatus.PASS),
    (Test1191, '<form><button></button></form>', TestStatus.FAIL),
    (Test1191, '<form><button>Effectuer une opération complexe</button></form>', TestStatus.NEEDS_REVIEW),
    (Test1192, '<form></form>', TestStatus.NOT_APPLICABLE),
    (Test1192, '<form><button>Envoyer</button></form>', TestStatus.PASS),
    (Test1192, '<form><button aria-label="Fermer">Envoyer</button></form>', TestStatus.NEEDS_REVIEW),
    (Test1192, '<form><input type="image" alt="Valider"></form>', TestStatus.NEEDS_REVIEW),
])
def test_cases(context_factory, run_rgaa, test, html, expected):
    assert run_rgaa(test(), context_factory(html)).status == expected
