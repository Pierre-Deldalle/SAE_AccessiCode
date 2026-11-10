from __future__ import annotations

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_4 import (
    Test1041 as RGAA1041,
)
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_4 import (
    Test1042 as RGAA1042,
)

# =============================================================================
# Tests for Test1041 - Perte d'information à 200 %
# =============================================================================


def test_1041_no_text_elements_passes(context_factory, run_rgaa):
    """Test 10.4.1: Page sans élément textuel passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><div></div></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1041(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 0
    assert "Aucun risque" in result.summary


def test_1041_normal_text_no_risks_passes(context_factory, run_rgaa):
    """Test 10.4.1: Texte normal sans styles risqués passe."""
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
    result = run_rgaa(RGAA1041(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements >= 3  # h1, p, 2 li
    assert "Aucun risque" in result.summary


def test_1041_fixed_width_on_text_container_fails(context_factory, run_rgaa):
    """Test 10.4.1: Largeur fixe en px sur conteneur de texte échoue."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="width: 200px;">
            <p>Texte qui risque d'être coupé si la taille augmente.</p>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1041(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1
    fixed_dim_findings = [f for f in result.findings if f.evidence.get("risk_type") == "fixed_dimension"]
    assert len(fixed_dim_findings) >= 1
    assert "dimension fixe" in fixed_dim_findings[0].message.lower()
    assert result.tested_elements >= 1


def test_1041_fixed_height_on_text_container_fails(context_factory, run_rgaa):
    """Test 10.4.1: Hauteur fixe en px sur conteneur de texte échoue."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="height: 50px;">
            <p>Texte dans un conteneur à hauteur fixe.</p>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1041(), context)

    assert result.status == Status.FAIL
    fixed_dim_findings = [f for f in result.findings if f.evidence.get("risk_type") == "fixed_dimension"]
    assert len(fixed_dim_findings) >= 1
    assert "height" in fixed_dim_findings[0].evidence.get("property", "")


def test_1041_overflow_hidden_on_text_container_fails(context_factory, run_rgaa):
    """Test 10.4.1: overflow:hidden sur conteneur de texte échoue."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="width: 150px; overflow: hidden;">
            <p>Un texte assez long pour être masqué par le overflow hidden.</p>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1041(), context)

    assert result.status == Status.FAIL
    overflow_findings = [f for f in result.findings if f.evidence.get("risk_type") == "clipped_overflow"]
    assert len(overflow_findings) >= 1
    assert "overflow" in overflow_findings[0].message.lower()


def test_1041_nowrap_on_text_container_fails(context_factory, run_rgaa):
    """Test 10.4.1: white-space:nowrap sur conteneur de texte échoue."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="white-space: nowrap;">Ce texte ne revient pas à la ligne.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1041(), context)

    assert result.status == Status.FAIL
    nowrap_findings = [f for f in result.findings if f.evidence.get("risk_type") == "nowrap"]
    assert len(nowrap_findings) >= 1
    assert "nowrap" in nowrap_findings[0].message.lower()


def test_1041_absolute_position_with_fixed_dimension_fails(context_factory, run_rgaa):
    """Test 10.4.1: Position absolute/fixed + dimension fixe échoue."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="position: absolute; top: 10px; left: 10px; width: 100px; height: 50px;">
            <p>Texte positionné absolument dans boîte fixe.</p>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1041(), context)

    assert result.status == Status.FAIL
    positioned_findings = [f for f in result.findings if f.evidence.get("risk_type") == "positioned_fixed_box"]
    assert len(positioned_findings) >= 1
    assert "absolute" in positioned_findings[0].message.lower() or "fixed" in positioned_findings[0].message.lower()


def test_1041_stylesheet_rules_flagged_needs_review(context_factory, run_rgaa):
    """Test 10.4.1: Règles CSS dans <style> sont signalées en NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>
            .message { height: 30px; overflow: hidden; }
        </style>
    </head>
    <body>
        <p class="message">Un message</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1041(), context)

    # Les règles de stylesheet ne sont pas des risques certains -> NEEDS_REVIEW
    assert result.status == Status.NEEDS_REVIEW
    stylesheet_findings = [f for f in result.findings if f.evidence.get("risk_type") == "stylesheet_layout_risk"]
    assert len(stylesheet_findings) >= 1
    assert "Règle CSS" in stylesheet_findings[0].message


def test_1041_multiple_risks_fails(context_factory, run_rgaa):
    """Test 10.4.1: Plusieurs risques détectés -> FAIL."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="width: 200px; overflow: hidden;">
            <p>Texte risqué 1</p>
        </div>
        <div style="height: 40px;">
            <p>Texte risqué 2</p>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1041(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 2
    assert result.tested_elements >= 2


def test_1041_missing_dom_returns_not_tested(context_factory, run_rgaa):
    """Test 10.4.1: DOM manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    test = RGAA1041()
    context = SimpleNamespace(dom=None, html_source="<p>Texte</p>")

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_dom"


def test_1041_missing_html_source_returns_not_tested(context_factory, run_rgaa):
    """Test 10.4.1: HTML source manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    from bs4 import BeautifulSoup

    test = RGAA1041()
    context = SimpleNamespace(
        dom=BeautifulSoup("<p>Texte</p>", "html.parser"),
        html_source="",
    )

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_html_source"


def test_1041_exempt_elements_counted(context_factory, run_rgaa):
    """Test 10.4.1: Les éléments exempts sont comptés dans les métadonnées."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <canvas>Texte dans canvas</canvas>
        <img src="image.jpg" alt="Image avec texte possible">
        <video><track kind="subtitles"></video>
        <p>Texte HTML normal</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1041(), context)

    assert result.metadata["exceptions_to_review"]["canvas"] == 1
    assert result.metadata["exceptions_to_review"]["images_with_text_possible"] == 1
    assert result.metadata["exceptions_to_review"]["video_subtitles_not_verifiable_from_dom"] == 1
    # Les éléments (textuels + conteneurs) sont examinés
    assert result.metadata["elements_examined"] >= 1


def test_1041_metadata_contains_manual_checks(context_factory, run_rgaa):
    """Test 10.4.1: Les métadonnées contiennent les vérifications manuelles requises."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><p>Texte</p></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1041(), context)

    assert result.metadata["browser_zoom_test_performed"] is False
    assert "zoom texte du navigateur à 200 %" in result.metadata["required_manual_checks"]
    assert "zoom graphique du navigateur à 200 %" in result.metadata["required_manual_checks"]
    assert result.metadata["manual_check_for"] == "perte d'information à 200 %"


# =============================================================================
# Tests for Test1042 - Agrandissement effectif du texte à 200 %
# =============================================================================


def test_1042_no_text_elements_passes(context_factory, run_rgaa):
    """Test 10.4.2: Page sans élément textuel passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><div></div></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1042(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 0
    assert "Aucune taille de police fixe" in result.summary


def test_1042_normal_text_no_fixed_font_size_passes(context_factory, run_rgaa):
    """Test 10.4.2: Texte normal sans font-size fixe passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <h1>Titre principal</h1>
        <p>Paragraphe avec taille relative.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1042(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements >= 2


def test_1042_fixed_font_size_px_inline_fails(context_factory, run_rgaa):
    """Test 10.4.2: font-size en px en ligne échoue."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="font-size: 14px;">Texte avec taille fixe en pixels.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1042(), context)

    assert result.status == Status.FAIL
    fixed_font_findings = [f for f in result.findings if f.evidence.get("risk_type") == "fixed_font_size"]
    assert len(fixed_font_findings) >= 1
    assert "px" in fixed_font_findings[0].evidence.get("value", "")


def test_1042_fixed_font_size_pt_inline_fails(context_factory, run_rgaa):
    """Test 10.4.2: font-size en pt en ligne échoue."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="font-size: 12pt;">Texte avec taille fixe en points.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1042(), context)

    assert result.status == Status.FAIL
    fixed_font_findings = [f for f in result.findings if f.evidence.get("risk_type") == "fixed_font_size"]
    assert len(fixed_font_findings) >= 1
    assert "pt" in fixed_font_findings[0].evidence.get("value", "")


def test_1042_relative_font_size_passes(context_factory, run_rgaa):
    """Test 10.4.2: font-size en em/rem/% passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="font-size: 1.2em;">Taille relative en em.</p>
        <p style="font-size: 120%;">Taille relative en pourcent.</p>
        <p style="font-size: 1.5rem;">Taille relative en rem.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1042(), context)

    assert result.status == Status.PASS
    assert result.findings == []


def test_1042_stylesheet_fixed_font_size_needs_review(context_factory, run_rgaa):
    """Test 10.4.2: font-size fixe dans <style> -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>
            .fixed-text { font-size: 16px; }
        </style>
    </head>
    <body>
        <p class="fixed-text">Texte avec taille fixe via CSS.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1042(), context)

    # Risque dans stylesheet seulement -> NEEDS_REVIEW
    assert result.status == Status.NEEDS_REVIEW
    stylesheet_findings = [f for f in result.findings if f.evidence.get("risk_type") == "fixed_font_size_stylesheet"]
    assert len(stylesheet_findings) >= 1
    assert "font-size" in stylesheet_findings[0].message.lower()


def test_1042_multiple_fixed_font_sizes_fails(context_factory, run_rgaa):
    """Test 10.4.2: Plusieurs font-size fixes en ligne -> FAIL."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="font-size: 14px;">Texte 1</p>
        <span style="font-size: 12pt;">Texte 2</span>
        <div style="font-size: 10px;">Texte 3</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1042(), context)

    assert result.status == Status.FAIL
    inline_risks = [f for f in result.findings if f.evidence.get("risk_type") == "fixed_font_size"]
    assert len(inline_risks) >= 3
    assert result.tested_elements >= 3


def test_1042_missing_dom_returns_not_tested(context_factory, run_rgaa):
    """Test 10.4.2: DOM manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    test = RGAA1042()
    context = SimpleNamespace(dom=None, html_source="<p>Texte</p>")

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_dom"


def test_1042_missing_html_source_returns_not_tested(context_factory, run_rgaa):
    """Test 10.4.2: HTML source manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    from bs4 import BeautifulSoup

    test = RGAA1042()
    context = SimpleNamespace(
        dom=BeautifulSoup("<p>Texte</p>", "html.parser"),
        html_source="",
    )

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_html_source"


def test_1042_exempt_elements_counted(context_factory, run_rgaa):
    """Test 10.4.2: Les éléments exempts sont comptés dans les métadonnées."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <canvas>Texte dessiné</canvas>
        <p>Texte HTML</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1042(), context)

    assert result.metadata["exceptions_to_review"]["canvas"] == 1
    assert result.metadata["elements_examined"] >= 1


def test_1042_metadata_contains_manual_checks(context_factory, run_rgaa):
    """Test 10.4.2: Les métadonnées contiennent les vérifications manuelles requises."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><p>Texte</p></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1042(), context)

    assert result.metadata["browser_zoom_test_performed"] is False
    assert "zoom texte du navigateur à 200 %" in result.metadata["required_manual_checks"]
    assert result.metadata["manual_check_for"] == "agrandissement effectif de l'ensemble du texte à 200 %"


# =============================================================================
# Tests de cas limites et comportements mixtes
# =============================================================================


def test_1041_mixed_pass_and_fail_returns_fail(context_factory, run_rgaa):
    """Test 10.4.1: PASS + FAIL -> FAIL (priorité FAIL)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Texte normal sans risque.</p>
        <div style="width: 100px; overflow: hidden;">
            <p>Texte risqué</p>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1041(), context)

    assert result.status == Status.FAIL
    # Au moins un risque certain doit être détecté
    inline_risks = [f for f in result.findings if f.evidence.get("risk_type") != "stylesheet_layout_risk"]
    assert len(inline_risks) >= 1


def test_1042_mixed_pass_and_fail_returns_fail(context_factory, run_rgaa):
    """Test 10.4.2: PASS + FAIL -> FAIL (priorité FAIL)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="font-size: 1.2em;">Texte OK (relatif)</p>
        <p style="font-size: 14px;">Texte avec taille fixe</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1042(), context)

    assert result.status == Status.FAIL
    inline_risks = [f for f in result.findings if f.evidence.get("risk_type") == "fixed_font_size"]
    assert len(inline_risks) >= 1
