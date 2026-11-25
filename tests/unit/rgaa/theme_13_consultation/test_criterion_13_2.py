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


def test_1321_failure_in_inline_script_is_located_in_the_page(context_factory, run_rgaa):
    html = "<html><body>\n<p>Accueil</p>\n<script>\nwindow.open('/pub');\n</script></body></html>"
    result = run_rgaa(Test1321(), context_factory(html))
    assert result.status == Status.FAIL
    finding = result.findings[0]
    assert (finding.file, finding.line, finding.snippet) == (None, 4, "window.open('/pub');")


def test_1321_failure_in_script_file_is_located_in_that_file(context_factory, run_rgaa):
    code = "// Publicité\nvar url = '/pub';\nwindow.open(url);\n"
    result = run_rgaa(Test1321(), context_factory('<script src="pub.js"></script>', resources={"pub.js": code}))
    assert result.status == Status.FAIL
    finding = result.findings[0]
    assert (finding.file, finding.line, finding.snippet) == ("pub.js", 3, "window.open(url);")


def test_1321_failure_in_event_attribute_is_located_on_the_element(context_factory, run_rgaa):
    html = "<html>\n<body onload=\"window.open('/pub')\">\n<p>x</p></body></html>"
    result = run_rgaa(Test1321(), context_factory(html))
    assert result.status == Status.FAIL
    assert result.findings[0].line == 2
    assert result.findings[0].snippet == "<body onload=\"window.open('/pub')\"> <p>x</p></body>"


# Exemples de correction --------------------------------------------------------


def test_1321_script_failure_moves_the_real_call_to_a_button(context_factory, run_rgaa):
    result = run_rgaa(Test1321(), context_factory(_script("window.open('/pub', 'pub');")))
    assert result.findings[0].recommendation.endswith(
        "Exemple : window.open('/pub', 'pub') exécuté au chargement → "
        "<button type=\"button\" onclick=\"window.open('/pub', 'pub')\">[intitulé du bouton]</button>"
    )


def test_1321_attribute_failure_removes_the_attribute(context_factory, run_rgaa):
    result = run_rgaa(Test1321(), context_factory('<body class="p" onload="window.open(\'/pub\')"><p>x</p></body>'))
    assert result.findings[0].recommendation.endswith(
        'Exemple : <body class="p" onload="window.open(\'/pub\')"> → <body class="p"> et '
        '<button type="button" onclick="window.open(\'/pub\')">[intitulé du bouton]</button>'
    )


def test_1321_review_has_no_example(context_factory, run_rgaa):
    result = run_rgaa(Test1321(), context_factory(_script("setTimeout(() => { window.open('/pub') }, 5000);")))
    assert result.status == Status.NEEDS_REVIEW
    assert "Exemple" not in result.findings[0].recommendation
