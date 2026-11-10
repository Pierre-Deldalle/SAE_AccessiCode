from __future__ import annotations

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_5 import (
    Test1051 as RGAA1051,
)
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_5 import (
    Test1052 as RGAA1052,
)
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_5 import (
    Test1053 as RGAA1053,
)

# =============================================================================
# Tests for Test1051 - color sans background-color
# =============================================================================


def test_1051_no_text_elements_passes(context_factory, run_rgaa):
    """Test 10.5.1: Page sans élément textuel passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><div></div></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1051(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 0
    assert "Aucun risque" in result.summary


def test_1051_normal_text_no_risks_passes(context_factory, run_rgaa):
    """Test 10.5.1: Texte normal sans color explicite passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <h1>Titre principal</h1>
        <p>Paragraphe de contenu normal.</p>
        <ul>
            <li>Élément de liste</li>
            <li>Autre élément</li>
        </ul>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1051(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements >= 3  # h1, p, 2 li
    assert "Aucun risque" in result.summary


def test_1051_color_with_background_color_on_same_element_passes(context_factory, run_rgaa):
    """Test 10.5.1: color + background-color sur le même élément passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="color: #333; background-color: #fff;">Texte avec fond.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1051(), context)

    assert result.status == Status.PASS
    assert result.findings == []


def test_1051_color_with_inherited_background_color_passes(context_factory, run_rgaa):
    """Test 10.5.1: color avec background-color hérité d'un parent passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="background-color: #fff;">
            <p style="color: #333;">Texte avec fond hérité.</p>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1051(), context)

    assert result.status == Status.PASS
    assert result.findings == []


def test_1051_color_without_background_color_fails(context_factory, run_rgaa):
    """Test 10.5.1: color sans background-color échoue."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="color: #333;">Texte sans fond défini.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1051(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1
    color_findings = [f for f in result.findings if f.evidence.get("risk_type") == "color_without_background"]
    assert len(color_findings) >= 1
    assert "color" in color_findings[0].message.lower()
    assert "background-color" in color_findings[0].message.lower()


def test_1051_transparent_background_not_counted_fails(context_factory, run_rgaa):
    """Test 10.5.1: background-color: transparent ne compte pas comme fallback."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="color: #333; background-color: transparent;">Texte avec fond transparent.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1051(), context)

    # transparent ne compte pas comme background-color explicite
    assert result.status == Status.FAIL
    color_findings = [f for f in result.findings if f.evidence.get("risk_type") == "color_without_background"]
    assert len(color_findings) >= 1


def test_1051_inherit_background_not_counted_fails(context_factory, run_rgaa):
    """Test 10.5.1: background-color: inherit ne compte pas comme fallback explicite."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="color: #333; background-color: inherit;">Texte avec fond hérité explicite.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1051(), context)

    # inherit ne compte pas comme background-color explicite
    assert result.status == Status.FAIL
    color_findings = [f for f in result.findings if f.evidence.get("risk_type") == "color_without_background"]
    assert len(color_findings) >= 1


def test_1051_currentcolor_not_counted_fails(context_factory, run_rgaa):
    """Test 10.5.1: color: currentColor ne compte pas comme color explicite."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="color: currentColor;">Texte avec currentColor.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1051(), context)

    # currentColor ne compte pas comme color explicite
    assert result.status == Status.PASS
    assert result.findings == []


def test_1051_stylesheet_color_without_background_needs_review(context_factory, run_rgaa):
    """Test 10.5.1: color sans background-color dans <style> -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>
            .message { color: #333; }
        </style>
    </head>
    <body>
        <p class="message">Un message</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1051(), context)

    # Les règles de stylesheet ne sont pas des risques certains -> NEEDS_REVIEW
    assert result.status == Status.NEEDS_REVIEW
    stylesheet_findings = [
        f for f in result.findings if f.evidence.get("risk_type") == "stylesheet_color_without_background"
    ]
    assert len(stylesheet_findings) >= 1
    assert "Règle CSS" in stylesheet_findings[0].message


def test_1051_multiple_risks_fails(context_factory, run_rgaa):
    """Test 10.5.1: Plusieurs color sans background-color -> FAIL."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="color: #333;">Texte 1 sans fond</p>
        <div style="color: #666;">
            <span>Texte 2 sans fond</span>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1051(), context)

    assert result.status == Status.FAIL
    inline_risks = [f for f in result.findings if f.evidence.get("risk_type") == "color_without_background"]
    assert len(inline_risks) >= 2
    assert result.tested_elements >= 2


def test_1051_missing_dom_returns_not_tested(context_factory, run_rgaa):
    """Test 10.5.1: DOM manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    test = RGAA1051()
    context = SimpleNamespace(dom=None, html_source="<p>Texte</p>")

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_dom"


def test_1051_missing_html_source_returns_not_tested(context_factory, run_rgaa):
    """Test 10.5.1: HTML source manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    from bs4 import BeautifulSoup

    test = RGAA1051()
    context = SimpleNamespace(
        dom=BeautifulSoup("<p>Texte</p>", "html.parser"),
        html_source="",
    )

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_html_source"


def test_1051_metadata_contains_manual_checks(context_factory, run_rgaa):
    """Test 10.5.1: Les métadonnées contiennent les vérifications manuelles requises."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><p>Texte</p></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1051(), context)

    assert result.metadata["browser_check_required"] is True
    assert "vérifier le contraste texte/fond dans le navigateur" in result.metadata["required_manual_checks"]
    assert result.metadata["manual_check_for"] == "color sans background-color (critère 10.5.1)"


# =============================================================================
# Tests for Test1052 - background-color sans color
# =============================================================================


def test_1052_no_text_elements_passes(context_factory, run_rgaa):
    """Test 10.5.2: Page sans élément textuel passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><div></div></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1052(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 0
    assert "Aucun risque" in result.summary


def test_1052_normal_text_no_risks_passes(context_factory, run_rgaa):
    """Test 10.5.2: Texte normal sans background-color explicite passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <h1>Titre principal</h1>
        <p>Paragraphe de contenu normal.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1052(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements >= 2


def test_1052_background_color_with_color_on_same_element_passes(context_factory, run_rgaa):
    """Test 10.5.2: background-color + color sur le même élément passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="background-color: #fff; color: #333;">Texte avec couleur.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1052(), context)

    assert result.status == Status.PASS
    assert result.findings == []


def test_1052_background_color_with_inherited_color_passes(context_factory, run_rgaa):
    """Test 10.5.2: background-color avec color hérité d'un parent passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="color: #333;">
            <p style="background-color: #fff;">Texte avec couleur héritée.</p>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1052(), context)

    assert result.status == Status.PASS
    assert result.findings == []


def test_1052_background_color_without_color_fails(context_factory, run_rgaa):
    """Test 10.5.2: background-color sans color échoue."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="background-color: #fff;">Texte sans couleur de police définie.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1052(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1
    bg_findings = [f for f in result.findings if f.evidence.get("risk_type") == "background_without_color"]
    assert len(bg_findings) >= 1
    assert "background-color" in bg_findings[0].message.lower()
    assert "color" in bg_findings[0].message.lower()


def test_1052_transparent_background_not_counted(context_factory, run_rgaa):
    """Test 10.5.2: background-color: transparent ne déclenche pas le test."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="background-color: transparent;">Texte avec fond transparent.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1052(), context)

    # transparent ne compte pas comme background-color explicite
    assert result.status == Status.PASS
    assert result.findings == []


def test_1052_inherit_background_not_counted(context_factory, run_rgaa):
    """Test 10.5.2: background-color: inherit ne déclenche pas le test."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="background-color: inherit;">Texte avec fond hérité explicite.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1052(), context)

    # inherit ne compte pas comme background-color explicite
    assert result.status == Status.PASS
    assert result.findings == []


def test_1052_stylesheet_background_without_color_needs_review(context_factory, run_rgaa):
    """Test 10.5.2: background-color sans color dans <style> -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>
            .box { background-color: #fff; }
        </style>
    </head>
    <body>
        <p class="box">Une boîte</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1052(), context)

    # Les règles de stylesheet ne sont pas des risques certains -> NEEDS_REVIEW
    assert result.status == Status.NEEDS_REVIEW
    stylesheet_findings = [
        f for f in result.findings if f.evidence.get("risk_type") == "stylesheet_background_without_color"
    ]
    assert len(stylesheet_findings) >= 1
    assert "Règle CSS" in stylesheet_findings[0].message


def test_1052_multiple_risks_fails(context_factory, run_rgaa):
    """Test 10.5.2: Plusieurs background-color sans color -> FAIL."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="background-color: #fff;">Texte 1 sans couleur</p>
        <div style="background-color: #eee;">
            <span>Texte 2 sans couleur</span>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1052(), context)

    assert result.status == Status.FAIL
    inline_risks = [f for f in result.findings if f.evidence.get("risk_type") == "background_without_color"]
    assert len(inline_risks) >= 2
    assert result.tested_elements >= 2


def test_1052_missing_dom_returns_not_tested(context_factory, run_rgaa):
    """Test 10.5.2: DOM manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    test = RGAA1052()
    context = SimpleNamespace(dom=None, html_source="<p>Texte</p>")

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_dom"


def test_1052_missing_html_source_returns_not_tested(context_factory, run_rgaa):
    """Test 10.5.2: HTML source manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    from bs4 import BeautifulSoup

    test = RGAA1052()
    context = SimpleNamespace(
        dom=BeautifulSoup("<p>Texte</p>", "html.parser"),
        html_source="",
    )

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_html_source"


def test_1052_metadata_contains_manual_checks(context_factory, run_rgaa):
    """Test 10.5.2: Les métadonnées contiennent les vérifications manuelles requises."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><p>Texte</p></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1052(), context)

    assert result.metadata["browser_check_required"] is True
    assert "vérifier le contraste texte/fond dans le navigateur" in result.metadata["required_manual_checks"]
    assert result.metadata["manual_check_for"] == "background-color sans color (critère 10.5.2)"


# =============================================================================
# Tests for Test1053 - background-image sans background-color fallback
# =============================================================================


def test_1053_no_text_elements_passes(context_factory, run_rgaa):
    """Test 10.5.3: Page sans élément textuel passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><div></div></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1053(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 0
    assert "Aucun risque" in result.summary


def test_1053_normal_text_no_risks_passes(context_factory, run_rgaa):
    """Test 10.5.3: Texte normal sans background-image passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <h1>Titre principal</h1>
        <p>Paragraphe de contenu normal.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1053(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements >= 2


def test_1053_background_image_with_fallback_passes(context_factory, run_rgaa):
    """Test 10.5.3: background-image + background-color sur le même élément passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="background-image: url('bg.png'); background-color: #fff;
        color: #333;">Texte avec fond image et fallback.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1053(), context)

    assert result.status == Status.PASS
    assert result.findings == []


def test_1053_background_image_with_inherited_fallback_passes(context_factory, run_rgaa):
    """Test 10.5.3: background-image avec background-color hérité d'un parent passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="background-color: #fff;">
            <p style="background-image: url('bg.png'); color: #333;">Texte avec fallback hérité.</p>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1053(), context)

    assert result.status == Status.PASS
    assert result.findings == []


def test_1053_background_image_without_fallback_fails(context_factory, run_rgaa):
    """Test 10.5.3: background-image sans background-color fallback échoue."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="background-image: url('bg.png'); color: #333;">Texte sans fallback.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1053(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1
    bg_img_findings = [f for f in result.findings if f.evidence.get("risk_type") == "background_image_without_fallback"]
    assert len(bg_img_findings) >= 1
    assert "background-image" in bg_img_findings[0].message.lower()
    assert "background-color" in bg_img_findings[0].message.lower()


def test_1053_background_shorthand_with_image_detected(context_factory, run_rgaa):
    """Test 10.5.3: background shorthand avec image détecté."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="background: url('bg.png') no-repeat; color: #333;">Texte avec background shorthand.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1053(), context)

    assert result.status == Status.FAIL
    bg_img_findings = [f for f in result.findings if f.evidence.get("risk_type") == "background_image_without_fallback"]
    assert len(bg_img_findings) >= 1


def test_1053_background_image_none_not_flagged(context_factory, run_rgaa):
    """Test 10.5.3: background-image: none ne déclenche pas le test."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="background-image: none; color: #333;">Texte sans image de fond.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1053(), context)

    assert result.status == Status.PASS
    assert result.findings == []


def test_1053_transparent_fallback_not_counted_fails(context_factory, run_rgaa):
    """Test 10.5.3: background-color: transparent ne compte pas comme fallback."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="background-image: url('bg.png'); background-color: transparent;
        color: #333;">Texte avec fallback transparent.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1053(), context)

    # transparent ne compte pas comme background-color explicite
    assert result.status == Status.FAIL
    bg_img_findings = [f for f in result.findings if f.evidence.get("risk_type") == "background_image_without_fallback"]
    assert len(bg_img_findings) >= 1


def test_1053_stylesheet_background_image_without_fallback_needs_review(context_factory, run_rgaa):
    """Test 10.5.3: background-image sans fallback dans <style> -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>
            .hero { background-image: url('hero.jpg'); }
        </style>
    </head>
    <body>
        <p class="hero">Un héros</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1053(), context)

    # Les règles de stylesheet ne sont pas des risques certains -> NEEDS_REVIEW
    assert result.status == Status.NEEDS_REVIEW
    stylesheet_findings = [
        f for f in result.findings if f.evidence.get("risk_type") == "stylesheet_background_image_without_fallback"
    ]
    assert len(stylesheet_findings) >= 1
    assert "Règle CSS" in stylesheet_findings[0].message


def test_1053_multiple_risks_fails(context_factory, run_rgaa):
    """Test 10.5.3: Plusieurs background-image sans fallback -> FAIL."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="background-image: url('bg1.png'); color: #333;">Texte 1</p>
        <div style="background-image: url('bg2.png');">
            <span style="color: #333;">Texte 2</span>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1053(), context)

    assert result.status == Status.FAIL
    inline_risks = [f for f in result.findings if f.evidence.get("risk_type") == "background_image_without_fallback"]
    assert len(inline_risks) >= 2
    assert result.tested_elements >= 2


def test_1053_missing_dom_returns_not_tested(context_factory, run_rgaa):
    """Test 10.5.3: DOM manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    test = RGAA1053()
    context = SimpleNamespace(dom=None, html_source="<p>Texte</p>")

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_dom"


def test_1053_missing_html_source_returns_not_tested(context_factory, run_rgaa):
    """Test 10.5.3: HTML source manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    from bs4 import BeautifulSoup

    test = RGAA1053()
    context = SimpleNamespace(
        dom=BeautifulSoup("<p>Texte</p>", "html.parser"),
        html_source="",
    )

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_html_source"


def test_1053_metadata_contains_manual_checks(context_factory, run_rgaa):
    """Test 10.5.3: Les métadonnées contiennent les vérifications manuelles requises."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><p>Texte</p></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1053(), context)

    assert result.metadata["browser_check_required"] is True
    assert "vérifier la lisibilité du texte si l'image de fond échoue" in result.metadata["required_manual_checks"]
    assert result.metadata["manual_check_for"] == "background-image sans background-color fallback (critère 10.5.3)"


# =============================================================================
# Tests de cas limites et comportements mixtes
# =============================================================================


def test_1051_mixed_pass_and_fail_returns_fail(context_factory, run_rgaa):
    """Test 10.5.1: PASS + FAIL -> FAIL (priorité FAIL)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="color: #333; background-color: #fff;">Texte OK</p>
        <p style="color: #666;">Texte sans fond</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1051(), context)

    assert result.status == Status.FAIL
    inline_risks = [f for f in result.findings if f.evidence.get("risk_type") == "color_without_background"]
    assert len(inline_risks) >= 1


def test_1052_mixed_pass_and_fail_returns_fail(context_factory, run_rgaa):
    """Test 10.5.2: PASS + FAIL -> FAIL (priorité FAIL)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="background-color: #fff; color: #333;">Texte OK</p>
        <p style="background-color: #eee;">Texte sans couleur</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1052(), context)

    assert result.status == Status.FAIL
    inline_risks = [f for f in result.findings if f.evidence.get("risk_type") == "background_without_color"]
    assert len(inline_risks) >= 1


def test_1053_mixed_pass_and_fail_returns_fail(context_factory, run_rgaa):
    """Test 10.5.3: PASS + FAIL -> FAIL (priorité FAIL)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="background-image: url('bg.png'); background-color: #fff; color: #333;">Texte OK</p>
        <p style="background-image: url('bg2.png'); color: #333;">Texte sans fallback</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1053(), context)

    assert result.status == Status.FAIL
    inline_risks = [f for f in result.findings if f.evidence.get("risk_type") == "background_image_without_fallback"]
    assert len(inline_risks) >= 1
