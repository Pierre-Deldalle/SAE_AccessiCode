import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_11 import Test12111


@pytest.mark.parametrize("value,expected", [(True, Status.PASS), (False, Status.FAIL), (None, Status.NEEDS_REVIEW)])
def test_panels(context_factory, run_rgaa, value, expected):
    c = context_factory("<button>Ouvrir</button>")
    c.navigation_evidence["12.11.1"] = {"interactive_additional_contents": [{"keyboard_reachable": value}]}
    assert run_rgaa(Test12111(), c).status == expected


def test_na(context_factory, run_rgaa):
    assert run_rgaa(Test12111(), context_factory("<p>Texte</p>")).status == Status.NOT_APPLICABLE


def test_script_review(context_factory, run_rgaa):
    assert run_rgaa(Test12111(), context_factory("<script>foo()</script>")).status == Status.NEEDS_REVIEW


def test_fail_is_located_on_the_document(context_factory, run_rgaa):
    c = context_factory('<html lang="fr">\n<button>Ouvrir</button>\n</html>')
    c.navigation_evidence["12.11.1"] = {"interactive_additional_contents": [{"keyboard_reachable": False}]}
    result = run_rgaa(Test12111(), c)
    assert result.status == Status.FAIL
    assert (result.findings[0].line, result.findings[0].snippet) == (
        1,
        '<html lang="fr"> <button>Ouvrir</button> </html>',
    )


def test_review_is_located_on_the_trigger(context_factory, run_rgaa):
    c = context_factory('<p>Texte</p>\n<button aria-haspopup="menu">Menu</button>\n<script>foo()</script>')
    [note] = run_rgaa(Test12111(), c).findings
    assert (note.line, note.snippet) == (2, '<button aria-haspopup="menu">Menu</button>')
