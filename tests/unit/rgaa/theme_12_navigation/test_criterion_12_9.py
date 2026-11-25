import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_8 import Test1281, Test1282
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_9 import Test1291


@pytest.mark.parametrize("value,expected", [(True, Status.PASS), (False, Status.FAIL), (None, Status.NEEDS_REVIEW)])
def test_1281(context_factory, run_rgaa, value, expected):
    c = context_factory('<button>Ouvrir</button><a href="#x">Lien</a>')
    if value is not None:
        c.navigation_evidence["12.8.1"] = {"tab_order_coherent": value}
    assert run_rgaa(Test1281(), c).status == expected


@pytest.mark.parametrize("value,expected", [(True, Status.PASS), (False, Status.FAIL), (None, Status.NEEDS_REVIEW)])
def test_1282(context_factory, run_rgaa, value, expected):
    c = context_factory('<button aria-expanded="false">Ouvrir</button><script>/* dynamic */</script>')
    if value is not None:
        c.navigation_evidence["12.8.2"] = {"dynamic_tab_order_coherent": value}
    assert run_rgaa(Test1282(), c).status == expected


def test_1282_na(context_factory, run_rgaa):
    assert run_rgaa(Test1282(), context_factory("<p>Texte</p>")).status == Status.NOT_APPLICABLE


def test_1281_fail_is_located_on_the_first_focusable(context_factory, run_rgaa):
    c = context_factory('<p>Texte</p>\n<button>Ouvrir</button>\n<a href="#x">Lien</a>')
    c.navigation_evidence["12.8.1"] = {"tab_order_coherent": False}
    [note] = run_rgaa(Test1281(), c).findings
    assert (note.element, note.line, note.snippet) == ("button[index=1]", 2, "<button>Ouvrir</button>")


@pytest.mark.parametrize("value,expected", [(True, Status.PASS), (False, Status.FAIL), (None, Status.NEEDS_REVIEW)])
def test_1291(context_factory, run_rgaa, value, expected):
    c = context_factory('<button>Ouvrir</button><a href="#x">Lien</a>')
    if value is not None:
        c.navigation_evidence["12.9.1"] = {"no_keyboard_trap": value}
    assert run_rgaa(Test1291(), c).status == expected


def test_1291_fail_is_located_on_the_first_focusable(context_factory, run_rgaa):
    c = context_factory('<p>Texte</p>\n<a href="#x">Lien</a>')
    c.navigation_evidence["12.9.1"] = {"no_keyboard_trap": False}
    [note] = run_rgaa(Test1291(), c).findings
    assert (note.line, note.snippet) == (2, '<a href="#x">Lien</a>')


def test_1281_positive_tabindex_shows_the_fix(context_factory, run_rgaa):
    c = context_factory('<a href="/" tabindex="5">Accueil</a>')
    c.navigation_evidence["12.8.1"] = {"tab_order_coherent": True}
    [note] = run_rgaa(Test1281(), c).findings
    assert note.recommendation == (
        'Contrôler Tab et Maj+Tab et privilégier l\'ordre DOM. Exemple : <a href="/" tabindex="5"> → <a href="/">'
    )
