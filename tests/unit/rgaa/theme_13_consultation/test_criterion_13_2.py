from __future__ import annotations

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_2 import (
    Test1321 as RGAA1321,
)

# ---------------------------------------------------------------------------
# 13.2.1 : Ouverture de nouvelle fenêtre sans action utilisateur
# ---------------------------------------------------------------------------


def test_1321_no_window_open_not_applicable(context_factory, run_rgaa):
    """Aucun window.open() détecté -> NOT_APPLICABLE."""
    html = "<!DOCTYPE html><html><body><p>Contenu</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1321(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1321_window_open_onload_fails(context_factory, run_rgaa):
    """window.open() dans window.onload -> FAIL (exécution automatique)."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<script>window.onload = function() { window.open("https://example.com"); };</script>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1321(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert any("automatique" in f.message for f in result.findings)
    assert any(f.evidence.get("violation") == "auto_window_open" for f in result.findings)


def test_1321_window_open_domcontentloaded_fails(context_factory, run_rgaa):
    """window.open() dans DOMContentLoaded -> FAIL (exécution automatique)."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<script>document.addEventListener("DOMContentLoaded", '
        'function() { window.open("https://example.com"); });</script>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1321(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert any("automatique" in f.message for f in result.findings)


def test_1321_window_open_window_load_event_fails(context_factory, run_rgaa):
    """window.open() dans window.addEventListener('load') -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<script>window.addEventListener("load", function() { window.open("https://example.com"); });</script>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1321(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1


def test_1321_window_open_iife_fails(context_factory, run_rgaa):
    """window.open() dans IIFE -> FAIL (exécution immédiate)."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<script>(function() { window.open("https://example.com"); })();</script>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1321(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    assert any("automatique" in f.message for f in result.findings)


def test_1321_window_open_arrow_iife_fails(context_factory, run_rgaa):
    """window.open() dans IIEF arrow function -> FAIL."""
    html = (
        '<!DOCTYPE html><html><body><script>(() => { window.open("https://example.com"); })();</script></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1321(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1


def test_1321_window_open_onclick_passes(context_factory, run_rgaa):
    """window.open() dans onclick -> PASS (action utilisateur)."""
    html = (
        "<!DOCTYPE html><html><body>"
        "<button onclick=\"window.open('https://example.com')\">Ouvrir</button>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1321(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    # Check for inline event handler message
    assert any("événement inline" in f.message for f in result.findings)
    assert any(f.evidence.get("likely_compliant") is True for f in result.findings)


def test_1321_window_open_addEventListener_click_passes(context_factory, run_rgaa):
    """window.open() dans addEventListener click -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<button id="btn">Ouvrir</button>'
        '<script>document.getElementById("btn").addEventListener('
        '"click", function() { window.open("https://example.com"); });</script>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1321(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    # Check for JS event handler message
    assert any("événement JS" in f.message for f in result.findings)


def test_1321_window_open_unknown_context_needs_review(context_factory, run_rgaa):
    """window.open() au niveau global (contexte indéterminé) -> NEEDS_REVIEW."""
    html = '<!DOCTYPE html><html><body><script>window.open("https://example.com");</script></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1321(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("indéterminé" in f.message for f in result.findings)
    assert any(f.evidence.get("needs_manual_check") is True for f in result.findings)


def test_1321_window_open_in_function_needs_review(context_factory, run_rgaa):
    """window.open() dans une fonction (contexte indéterminé) -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<script>function openPopup() { window.open("https://example.com"); }</script>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1321(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("indéterminé" in f.message for f in result.findings)


def test_1321_multiple_window_opens_mixed(context_factory, run_rgaa):
    """Plusieurs window.open : un auto (FAIL), un click (PASS) -> FAIL (priorité FAIL)."""
    html = (
        "<!DOCTYPE html><html><body>"
        "<button onclick=\"window.open('https://example.com')\">User</button>"
        '<script>window.onload = function() { window.open("https://auto.com"); };</script>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1321(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 2
    # Should have one FAIL finding and one PASS finding
    assert any(f.evidence.get("violation") == "auto_window_open" for f in result.findings)
    assert any(f.evidence.get("likely_compliant") is True for f in result.findings)
    # Check for both message types
    assert any("événement inline" in f.message or "événement JS" in f.message for f in result.findings)
    assert any("automatique" in f.message for f in result.findings)


def test_1321_window_open_case_insensitive(context_factory, run_rgaa):
    """window.open() insensible à la casse."""
    html = '<!DOCTYPE html><html><body><script>WINDOW.OPEN("https://example.com");</script></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1321(), context)

    assert result.status == Status.NEEDS_REVIEW  # global context
    assert result.tested_elements == 1


def test_1321_window_open_with_parameters(context_factory, run_rgaa):
    """window.open() avec paramètres (url, name, features)."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<script>window.open("https://example.com", "popup", "width=400,height=300");</script>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1321(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1321_window_open_various_event_handlers(context_factory, run_rgaa):
    """Divers gestionnaires d'événements utilisateur -> PASS."""
    events = [
        "onclick",
        "onmousedown",
        "onmouseup",
        "onkeydown",
        "onkeyup",
        "onkeypress",
        "onsubmit",
        "onchange",
    ]

    for event in events:
        html = f"<!DOCTYPE html><html><body><button {event}=\"window.open('https://example.com')\">Test</button></body></html>"
        context = context_factory(html)

        result = run_rgaa(RGAA1321(), context)

        assert result.status == Status.PASS, f"Failed for event: {event}"
        assert result.tested_elements == 1
        assert any("événement inline" in f.message for f in result.findings)


def test_1321_window_open_addEventListener_various_events(context_factory, run_rgaa):
    """addEventListener avec divers événements utilisateur -> PASS."""
    events = [
        "click",
        "mousedown",
        "mouseup",
        "keydown",
        "keyup",
        "keypress",
        "submit",
        "change",
    ]

    for event in events:
        html = (
            f"<!DOCTYPE html><html><body>"
            f'<button id="btn">Test</button>'
            f'<script>document.getElementById("btn").addEventListener('
            f'"{event}", function() {{ window.open("https://example.com"); }});</script>'
            f"</body></html>"
        )
        context = context_factory(html)

        result = run_rgaa(RGAA1321(), context)

        assert result.status == Status.PASS, f"Failed for event: {event}"
        assert result.tested_elements == 1
        assert any("événement JS" in f.message for f in result.findings)


def test_1321_window_open_not_triggered_by_focus(context_factory, run_rgaa):
    """window.open() dans onfocus -> devrait être détecté
    (focus n'est pas action utilisateur explicite pour ouvrir fenêtre)."""
    # Note: onfocus peut être déclenché sans action utilisateur explicite
    # Selon WCAG 3.2.1, le focus ne doit pas déclencher de changement de contexte
    html = "<!DOCTYPE html><html><body><input onfocus=\"window.open('https://example.com')\"></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1321(), context)

    # onfocus n'est pas dans nos patterns d'événements utilisateur explicites
    # donc cela devrait être NEEDS_REVIEW ou FAIL selon le contexte
    assert result.tested_elements == 1


# ---------------------------------------------------------------------------
# Tests de régression : parsing robuste
# ---------------------------------------------------------------------------


def test_1321_window_open_single_quotes(context_factory, run_rgaa):
    """window.open() avec guillemets simples."""
    html = "<!DOCTYPE html><html><body><script>window.open('https://example.com');</script></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1321(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1321_window_open_double_quotes(context_factory, run_rgaa):
    """window.open() avec guillemets doubles."""
    html = '<!DOCTYPE html><html><body><script>window.open("https://example.com");</script></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1321(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1321_window_open_no_params(context_factory, run_rgaa):
    """window.open() sans paramètres."""
    html = "<!DOCTYPE html><html><body><script>window.open();</script></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1321(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1321_multiple_scripts_only_one_with_window_open(context_factory, run_rgaa):
    """Plusieurs scripts, un seul avec window.open()."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<script>console.log("autre script");</script>'
        '<script>window.open("https://example.com");</script>'
        "<script>var x = 1;</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1321(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    # Should find the correct script
    assert "window.open" in result.findings[0].element or "script" in result.findings[0].element
