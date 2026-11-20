"""Critère RGAA 13.1 : contrôle des limites de temps (rafraîchissement, redirection, session)."""

import asyncio

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_1 import Test1311, Test1312, Test1313, Test1314


def _page(head: str = "", body: str = "") -> str:
    return f"<html><head>{head}</head><body>{body}</body></html>"


def _script(code: str) -> str:
    return _page(body=f"<script>{code}</script>")


# 13.1.1 ---------------------------------------------------------------------


def test_1311_no_refresh_is_not_applicable(context_factory, run_rgaa):
    html = _script("setTimeout(function () { tip.show() }, 300);")
    assert run_rgaa(Test1311(), context_factory(html)).status == Status.NOT_APPLICABLE


def test_1311_meta_refresh_fails(context_factory, run_rgaa):
    result = run_rgaa(Test1311(), context_factory(_page('<meta http-equiv="refresh" content="30">')))
    assert result.status == Status.FAIL
    assert result.findings[0].evidence["delay_seconds"] == 30


def test_1311_meta_refresh_of_twenty_hours_passes(context_factory, run_rgaa):
    html = _page('<meta http-equiv="refresh" content="72000">')
    assert run_rgaa(Test1311(), context_factory(html)).status == Status.PASS


def test_1311_meta_with_url_is_a_redirect_not_a_refresh(context_factory, run_rgaa):
    html = _page('<meta http-equiv="refresh" content="5; url=/nouveau">')
    assert run_rgaa(Test1311(), context_factory(html)).status == Status.NOT_APPLICABLE


def test_1311_script_reload_needs_review(context_factory, run_rgaa):
    result = run_rgaa(Test1311(), context_factory(_script("setInterval(() => { location.reload() }, 60000);")))
    assert result.status == Status.NEEDS_REVIEW
    assert result.findings[0].evidence["delay_ms"] == 60000


# 13.1.2 ---------------------------------------------------------------------


def test_1312_immediate_meta_redirect_passes(context_factory, run_rgaa):
    html = _page('<meta http-equiv="refresh" content="0; url=/nouveau">')
    assert run_rgaa(Test1312(), context_factory(html)).status == Status.PASS


def test_1312_delayed_meta_redirect_fails(context_factory, run_rgaa):
    result = run_rgaa(Test1312(), context_factory(_page("<meta http-equiv='refresh' content=\"10;URL='/n'\">")))
    assert result.status == Status.FAIL
    assert result.findings[0].evidence["url"] == "/n"


def test_1312_refresh_without_url_is_not_applicable(context_factory, run_rgaa):
    html = _page('<meta http-equiv="refresh" content="30">')
    assert run_rgaa(Test1312(), context_factory(html)).status == Status.NOT_APPLICABLE


# 13.1.3 ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "code",
    [
        "setTimeout(() => { location.assign('/accueil') }, 5000);",
        "setTimeout(function () { window.location.href = '/accueil'; }, 5000);",
        "function go() { location.replace('/a') }\nsetTimeout(go, 8000);",
    ],
)
def test_1313_delayed_script_redirect_needs_review(code, context_factory, run_rgaa):
    assert run_rgaa(Test1313(), context_factory(_script(code))).status == Status.NEEDS_REVIEW


def test_1313_immediate_or_long_redirects(context_factory, run_rgaa):
    immediate = _script("setTimeout(() => { location.href = '/a' }, 0);")
    assert run_rgaa(Test1313(), context_factory(immediate)).status == Status.NOT_APPLICABLE
    long = _script("setTimeout(() => { location.href = '/a' }, 20 * 3600 * 1000);")
    assert run_rgaa(Test1313(), context_factory(long)).status == Status.PASS


def test_1313_ignores_unrelated_location_words(context_factory, run_rgaa):
    html = _script("setTimeout(() => { geolocation = null; }, 1000);")
    assert run_rgaa(Test1313(), context_factory(html)).status == Status.NOT_APPLICABLE


# 13.1.4 ---------------------------------------------------------------------


def test_1314_session_timer_needs_review(context_factory, run_rgaa):
    html = _script("setTimeout(function () { window.location.href = '/logout'; }, 900000);")
    result = run_rgaa(Test1314(), context_factory(html))
    assert result.status == Status.NEEDS_REVIEW
    assert "session" in result.findings[0].message


def test_1314_meta_logout_fails(context_factory, run_rgaa):
    html = _page('<meta http-equiv="refresh" content="600; url=/deconnexion">')
    assert run_rgaa(Test1314(), context_factory(html)).status == Status.FAIL


def test_1314_no_session_limit_is_not_applicable(context_factory, run_rgaa):
    assert run_rgaa(Test1314(), context_factory(_page(body="<p>x</p>"))).status == Status.NOT_APPLICABLE


def test_13_1_missing_dom_raises_error(context_factory):
    context = context_factory("<p>x</p>")
    context.dom = None
    with pytest.raises(ValueError, match="13.1.1 nécessite un DOM"):
        asyncio.run(Test1311().run(context))
