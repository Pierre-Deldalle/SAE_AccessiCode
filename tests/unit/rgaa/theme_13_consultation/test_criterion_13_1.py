"""Critère RGAA 13.1 : contrôle des limites de temps (rafraîchissement, redirection, session)."""

import asyncio

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.registry import TestRegistry
from accessi_code.rgaa.runner import TestRunner
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


# Emplacement des observations ------------------------------------------------

TIMER_FILE = "// Rafraîchissement\n\nsetInterval(() => { location.reload() }, 60000);\n"


@pytest.mark.parametrize(
    ("test", "content"),
    [(Test1311(), "30"), (Test1312(), "10; url=/n"), (Test1314(), "600; url=/deconnexion")],
)
def test_13_1_meta_failure_is_located_on_the_meta(test, content, context_factory, run_rgaa):
    html = f'<html><head>\n<title>T</title>\n<meta http-equiv="refresh" content="{content}">\n</head></html>'
    result = run_rgaa(test, context_factory(html))
    assert result.status == Status.FAIL
    assert result.findings[0].line == 3
    assert result.findings[0].snippet == f'<meta http-equiv="refresh" content="{content}">'
    assert result.findings[0].file is None


def test_1313_inline_script_is_located_in_the_page(context_factory, run_rgaa):
    html = "<html><body>\n<script>\nvar x;\nsetTimeout(() => { location.assign('/a') }, 5000);\n</script></body></html>"
    finding = run_rgaa(Test1313(), context_factory(html)).findings[0]
    assert (finding.file, finding.line) == (None, 4)
    assert finding.snippet == "setTimeout(() => { location.assign('/a') }, 5000);"


def test_1311_script_file_is_located_in_that_file(context_factory, run_rgaa):
    context = context_factory('<script src="js/minuteur.js"></script>', resources={"js/minuteur.js": TIMER_FILE})
    finding = run_rgaa(Test1311(), context).findings[0]
    assert (finding.file, finding.line) == ("minuteur.js", 3)
    assert finding.snippet == "setInterval(() => { location.reload() }, 60000);"


def test_13_1_runner_keeps_the_script_file_and_fills_the_page(context_factory):
    html = '<html><head>\n<meta http-equiv="refresh" content="30">\n</head><body><script src="m.js"></script></body>'
    context = context_factory(html, resources={"m.js": TIMER_FILE})
    [result] = asyncio.run(TestRunner(TestRegistry([Test1311()])).run_all(context))
    assert [(finding.file, finding.line) for finding in result.findings] == [("index.html", 2), ("m.js", 3)]


# Exemples de correction --------------------------------------------------------


def test_1311_recommendation_shows_the_refresh_to_remove(context_factory, run_rgaa):
    result = run_rgaa(Test1311(), context_factory(_page('<meta http-equiv="refresh" content="30">')))
    assert result.findings[0].recommendation.endswith(
        'Exemple : <meta http-equiv="refresh" content="30"> → balise supprimée, et dans la page '
        '<button type="button" onclick="location.reload()">Actualiser</button>'
    )


def test_1312_recommendation_makes_the_redirect_immediate(context_factory, run_rgaa):
    result = run_rgaa(Test1312(), context_factory(_page('<meta http-equiv="refresh" content="10; url=/a">')))
    assert result.findings[0].recommendation.endswith(
        'Exemple : <meta http-equiv="refresh" content="10; url=/a"> → <meta http-equiv="refresh" content="0; url=/a">'
    )


def test_13_1_reviews_and_session_limits_have_no_example(context_factory, run_rgaa):
    # Contrôle laissé à l'utilisateur ou fin de session : la correction n'est pas mécanique.
    review = run_rgaa(Test1311(), context_factory(_script("setInterval(() => { location.reload() }, 60000);")))
    session = run_rgaa(Test1314(), context_factory(_page('<meta http-equiv="refresh" content="600; url=/logout">')))
    assert "Exemple" not in review.findings[0].recommendation
    assert "Exemple" not in session.findings[0].recommendation
