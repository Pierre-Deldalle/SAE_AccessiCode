"""Lecture des scripts : masquage, déclencheur d'un appel, minuteurs et écoutes d'événements."""

import pytest
from bs4 import BeautifulSoup

from accessi_code.analysis.scripts import (
    ScriptSource,
    Trigger,
    event_listeners,
    listener_target,
    mask_code,
    numeric_value,
    page_scripts,
    timer_calls,
    trigger_at,
)


def _trigger(code: str, target: str = "window.open", html: str = "") -> Trigger:
    source = ScriptSource("s", code)
    soup = BeautifulSoup(html, "html.parser") if html else None
    return trigger_at([source], source, code.index(target), soup).trigger


def test_mask_code_neutralizes_comments_and_braces_in_strings():
    masked = mask_code("var s = '{(;'; // fin }\nf();")
    assert len(masked) == len("var s = '{(;'; // fin }\nf();")
    assert "{" not in masked and "fin" not in masked
    assert "f()" in masked


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("window.open('x');", Trigger.LOAD),
        ("b.addEventListener('click', f);\nwindow.open('x');", Trigger.LOAD),
        ("window.onload = function () { window.open('x'); };", Trigger.LOAD),
        ("document.addEventListener('DOMContentLoaded', () => { window.open('x') });", Trigger.LOAD),
        ("btn.addEventListener('click', function () { window.open('x') });", Trigger.USER),
        ("btn.addEventListener('click', () => window.open('x'));", Trigger.USER),
        ("$('#b').on('click', function () { window.open('x') });", Trigger.USER),
        ("setTimeout(function () { window.open('x') }, 3000);", Trigger.TIMER),
        ("function pub() { window.open('x') }\npub();", Trigger.LOAD),
        ("function pub() { window.open('x') }", Trigger.UNKNOWN),
        ("window.addEventListener('scroll', () => { window.open('x') });", Trigger.UNKNOWN),
    ],
)
def test_trigger_at(code, expected):
    assert _trigger(code) is expected


def test_trigger_follows_named_function_into_iife():
    code = (
        "(function () { function openPopup() { window.open('/aide') }"
        " document.getElementById('b').addEventListener('click', openPopup); })();"
    )
    assert _trigger(code) is Trigger.USER


def test_trigger_follows_method_and_concise_arrow():
    code = "class P { show() { window.open('x') } } const p = new P(); btn.onclick = () => p.show();"
    assert _trigger(code) is Trigger.USER


def test_trigger_uses_inline_attribute_handlers():
    html = '<button onclick="pub()">Ouvrir</button>'
    assert _trigger("function pub() { window.open('x') }", html=html) is Trigger.USER


def test_condition_is_reported():
    source = ScriptSource("s", "window.onload = () => { if (promo) { window.open('x') } };")
    info = trigger_at([source], source, source.code.index("window.open"))
    assert info.trigger is Trigger.LOAD and info.conditional


@pytest.mark.parametrize(("expression", "value"), [("5000", 5000), ("30 * 1000", 30000), ("2e3", 2000), ("x", None)])
def test_numeric_value(expression, value):
    assert numeric_value(expression) == value


def test_timer_calls_resolve_named_callback_and_delay():
    source = ScriptSource("s", "function go() { location.reload() }\nsetInterval(go, 60 * 1000);")
    [call] = timer_calls([source])
    assert call.kind == "setInterval"
    assert call.delay_ms == 60000
    assert "location.reload" in call.callback


def test_event_listeners_cover_scripts_properties_and_attributes():
    soup = BeautifulSoup('<div onmousedown="del()"></div>', "html.parser")
    source = ScriptSource("s", "a.addEventListener('pointerdown', (e) => { go() }); b.onmousedown = stop;")
    listeners = event_listeners([source], soup, {"pointerdown", "mousedown"})
    assert [(item.event, item.label) for item in listeners] == [
        ("pointerdown", "s"),
        ("mousedown", "s"),
        ("mousedown", "attribut onmousedown"),
    ]


def test_page_scripts_reads_inline_and_local_files(context_factory):
    html = '<script src="app.js"></script><script>inline()</script><script type="application/json">{}</script>'
    context = context_factory(html, resources={"app.js": "fichier()"})
    assert [source.label for source in page_scripts(context)] == ["app.js", "script[index=1]"]


def test_listener_target_resolves_ids_selectors_and_variables():
    soup = BeautifulSoup('<div id="a"></div><div class="b"></div>', "html.parser")
    code = (
        'const x = document.getElementById("a");\n'
        'x.addEventListener("keydown", k);\n'
        'document.querySelector(".b").onclick = go;\n'
        'document.addEventListener("keyup", f);\n'
        'foo().bar.addEventListener("click", g);'
    )
    source = ScriptSource("s", code)
    listeners = event_listeners([source], soup, {"keydown", "click", "keyup"})
    targets = [(listener.event, listener_target([source], soup, listener)) for listener in listeners]
    assert targets == [
        ("keydown", soup.find(id="a")),
        ("keyup", "document"),
        ("click", None),
        ("click", soup.find(class_="b")),
    ]


def test_inline_script_location_is_a_line_of_the_page(context_factory):
    html = "<html><body>\n<p>x</p>\n<script>\nvar a = 1;\nwindow.open('pub.html');\n</script></body></html>"
    [source] = page_scripts(context_factory(html))
    assert source.location(source.code.index("window.open")) == {
        "file": None,
        "line": 5,
        "snippet": "window.open('pub.html');",
    }


def test_script_file_location_is_a_line_of_that_file(context_factory):
    code = "// Publicité\n\nwindow.open('pub.html');\n"
    context = context_factory('<script src="js/pub.js"></script>', resources={"js/pub.js": code})
    [source] = page_scripts(context)
    assert source.location(source.code.index("window.open")) == {
        "file": "pub.js",
        "line": 3,
        "snippet": "window.open('pub.html');",
    }
