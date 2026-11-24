import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_12_navigation.criterion_12_10 import Test12101


@pytest.mark.parametrize(
    "item,expected",
    [
        ({"key": "a", "disable": True}, Status.PASS),
        ({"key": "a", "disable": False, "remap_with_modifier": False, "focus_only": False}, Status.FAIL),
        ({"key": "a"}, Status.NEEDS_REVIEW),
    ],
)
def test_shortcuts(context_factory, run_rgaa, item, expected):
    c = context_factory("<button>Action</button>")
    c.navigation_evidence["12.10.1"] = {"single_key_shortcuts": [item]}
    assert run_rgaa(Test12101(), c).status == expected


def test_na(context_factory, run_rgaa):
    assert run_rgaa(Test12101(), context_factory("<p>Texte</p>")).status == Status.NOT_APPLICABLE


def test_script_review(context_factory, run_rgaa):
    assert (
        run_rgaa(Test12101(), context_factory('<script>document.addEventListener("keydown", fn)</script>')).status
        == Status.NEEDS_REVIEW
    )


def test_fail_is_located_on_the_document(context_factory, run_rgaa):
    c = context_factory('<html lang="fr">\n<button>Action</button>\n</html>')
    c.navigation_evidence["12.10.1"] = {
        "single_key_shortcuts": [{"key": "a", "disable": False, "remap_with_modifier": False, "focus_only": False}]
    }
    result = run_rgaa(Test12101(), c)
    assert result.status == Status.FAIL
    assert (result.findings[0].line, result.findings[0].snippet) == (
        1,
        '<html lang="fr"> <button>Action</button> </html>',
    )


def test_review_is_located_on_the_keyboard_handler(context_factory, run_rgaa):
    c = context_factory('<p>Texte</p>\n<div onkeydown="go(event)">Zone</div>')
    [note] = run_rgaa(Test12101(), c).findings
    assert (note.element, note.line, note.snippet) == ("div[index=1]", 2, '<div onkeydown="go(event)">Zone</div>')
