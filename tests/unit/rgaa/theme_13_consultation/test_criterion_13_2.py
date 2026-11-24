"""Critère RGAA 13.2 : ouverture de nouvelles fenêtres sans action de l'utilisateur."""

import asyncio

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_2 import Test1321


def _script(code: str, body: str = "") -> str:
    return f"<html><body>{body}<script>{code}</script></body></html>"


def test_1321_no_window_open_is_not_applicable(context_factory, run_rgaa):
    html = '<a href="/x" target="_blank">Ouvrir</a>'
    assert run_rgaa(Test1321(), context_factory(html)).status == Status.NOT_APPLICABLE


@pytest.mark.parametrize(
    "code",
    [
        "window.open('/pub');",
        "window.onload = function () { window.open('/pub'); };",
        "document.addEventListener('DOMContentLoaded', () => { window.open('/pub') });",
        "b.addEventListener('click', f);\nwindow.open('/pub');",
        "function pub() { window.open('/pub') }\npub();",
    ],
)
def test_1321_opening_at_load_fails(code, context_factory, run_rgaa):
    result = run_rgaa(Test1321(), context_factory(_script(code)))
    assert result.status == Status.FAIL
    assert result.findings[0].evidence["trigger"] == "load"


@pytest.mark.parametrize(
    "code",
    [
        "btn.addEventListener('click', () => { window.open('/aide') });",
        "(function () { function openPopup() { window.open('/aide') } b.addEventListener('click', openPopup); })();",
        "$('#b').on('click', function () { window.open('/aide') });",
    ],
)
def test_1321_opening_after_user_action_passes(code, context_factory, run_rgaa):
    result = run_rgaa(Test1321(), context_factory(_script(code)))
    assert result.status == Status.PASS
    assert result.findings == []


def test_1321_function_called_from_onclick_attribute_passes(context_factory, run_rgaa):
    html = _script("function aide() { window.open('/aide') }", body='<button onclick="aide()">Aide</button>')
    assert run_rgaa(Test1321(), context_factory(html)).status == Status.PASS


@pytest.mark.parametrize(
    "code",
    [
        "setTimeout(() => { window.open('/pub') }, 5000);",
        "window.onload = () => { if (promo) { window.open('/pub') } };",
        "function pub() { window.open('/pub') }",
    ],
)
def test_1321_uncertain_trigger_needs_review(code, context_factory, run_rgaa):
    assert run_rgaa(Test1321(), context_factory(_script(code))).status == Status.NEEDS_REVIEW


def test_1321_inline_attributes(context_factory, run_rgaa):
    click = "<button onclick=\"window.open('/a')\">Ouvrir</button>"
    assert run_rgaa(Test1321(), context_factory(click)).status == Status.PASS
    focus = "<input onfocus=\"window.open('/pub')\">"
    assert run_rgaa(Test1321(), context_factory(focus)).status == Status.NEEDS_REVIEW
    load = "<body onload=\"window.open('/pub')\"></body>"
    result = run_rgaa(Test1321(), context_factory(load))
    assert result.status == Status.FAIL
    assert result.findings[0].element == "body[index=0]"


def test_1321_reads_external_script_files(context_factory, run_rgaa):
    context = context_factory('<script src="pub.js"></script>', resources={"pub.js": "window.open('/pub');"})
    result = run_rgaa(Test1321(), context)
    assert result.status == Status.FAIL
    assert result.findings[0].element == "pub.js"


def test_1321_missing_dom_raises_error(context_factory):
    context = context_factory("<p>x</p>")
    context.dom = None
    with pytest.raises(ValueError, match="13.2.1 nécessite un DOM"):
        asyncio.run(Test1321().run(context))
