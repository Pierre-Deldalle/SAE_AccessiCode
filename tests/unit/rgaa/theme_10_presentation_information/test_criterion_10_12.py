from __future__ import annotations

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_12 import (
    Test10121 as RGAA10121,
)

# =============================================================================
# Tests for Test10121 - Text spacing user override (Critère 10.12.1)
# =============================================================================


def test_10121_no_conflicts_passes(context_factory, run_rgaa):
    """Test 10.12.1: Page sans conflit d'espacement passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="line-height: 1.5;">Contenu avec line-height relatif</div>
        <p style="margin-bottom: 1em;">Paragraphe avec marge relative</p>
        <span style="letter-spacing: normal;">Texte normal</span>
        <span style="word-spacing: normal;">Texte normal</span>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10121(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0
    assert "Aucun conflit évident" in result.summary


def test_10121_line_height_fixed_px_needs_review(context_factory, run_rgaa):
    """Test 10.12.1: line-height fixe en px -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="line-height: 24px;">Contenu avec line-height fixe</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10121(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "line_height_prevents_user_override"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert findings[0].evidence["check_type"] == "line_height_conflict"
    assert "line-height" in findings[0].evidence["style_details"]
    assert "px" in findings[0].evidence["style_details"]


def test_10121_line_height_important_needs_review(context_factory, run_rgaa):
    """Test 10.12.1: line-height avec !important -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="line-height: 1.5 !important;">Contenu avec important</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10121(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "line_height_prevents_user_override"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert "!important" in findings[0].evidence["style_details"]


def test_10121_line_height_unitless_passes(context_factory, run_rgaa):
    """Test 10.12.1: line-height sans unité (ratio) -> PAS signalé."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="line-height: 1.5;">Ratio sans unité</div>
        <div style="line-height: 150%;">Pourcentage</div>
        <div style="line-height: 1.5em;">EM relatif</div>
        <div style="line-height: 1.5rem;">REM relatif</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10121(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10121_margin_bottom_fixed_px_on_p_needs_review(context_factory, run_rgaa):
    """Test 10.12.1: margin-bottom fixe en px sur <p> -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="margin-bottom: 20px;">Paragraphe avec marge fixe</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10121(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "margin_bottom_prevents_user_override"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert findings[0].evidence["check_type"] == "margin_bottom_conflict"
    assert "margin-bottom" in findings[0].evidence["style_details"]
    assert "px" in findings[0].evidence["style_details"]


def test_10121_margin_bottom_relative_on_p_passes(context_factory, run_rgaa):
    """Test 10.12.1: margin-bottom relatif sur <p> -> PAS signalé."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="margin-bottom: 1em;">EM relatif</p>
        <p style="margin-bottom: 2rem;">REM relatif</p>
        <p style="margin-bottom: 10%;">Pourcentage</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10121(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10121_margin_bottom_on_div_not_checked(context_factory, run_rgaa):
    """Test 10.12.1: margin-bottom sur <div> n'est pas vérifié (seul <p> pour ce critère)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="margin-bottom: 50px;">Div avec marge fixe</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10121(), context)

    # margin-bottom n'est vérifié que sur <p> selon le critère
    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10121_letter_spacing_fixed_px_needs_review(context_factory, run_rgaa):
    """Test 10.12.1: letter-spacing fixe en px -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <span style="letter-spacing: 2px;">Texte avec espacement fixe</span>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10121(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "letter_spacing_prevents_user_override"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert findings[0].evidence["check_type"] == "letter_spacing_conflict"
    assert "letter-spacing" in findings[0].evidence["style_details"]
    assert "px" in findings[0].evidence["style_details"]


def test_10121_letter_spacing_normal_passes(context_factory, run_rgaa):
    """Test 10.12.1: letter-spacing: normal -> PAS signalé."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <span style="letter-spacing: normal;">Texte normal</span>
        <span style="letter-spacing: 0.1em;">EM relatif</span>
        <span style="letter-spacing: 0.05rem;">REM relatif</span>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10121(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10121_word_spacing_fixed_px_needs_review(context_factory, run_rgaa):
    """Test 10.12.1: word-spacing fixe en px -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <span style="word-spacing: 5px;">Texte avec espacement fixe</span>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10121(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "word_spacing_prevents_user_override"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert findings[0].evidence["check_type"] == "word_spacing_conflict"
    assert "word-spacing" in findings[0].evidence["style_details"]
    assert "px" in findings[0].evidence["style_details"]


def test_10121_word_spacing_normal_passes(context_factory, run_rgaa):
    """Test 10.12.1: word-spacing: normal -> PAS signalé."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <span style="word-spacing: normal;">Texte normal</span>
        <span style="word-spacing: 0.2em;">EM relatif</span>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10121(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10121_img_exception_not_reported(context_factory, run_rgaa):
    """Test 10.12.1: Image avec line-height fixe -> PAS signalée (cas particulier)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <img src="text.png" style="line-height: 30px;" alt="Image texte">
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10121(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10121_video_exception_not_reported(context_factory, run_rgaa):
    """Test 10.12.1: Vidéo -> PAS signalée (cas particulier sous-titres)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <video src="video.mp4" style="line-height: 30px;"></video>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10121(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10121_canvas_exception_not_reported(context_factory, run_rgaa):
    """Test 10.12.1: Canvas -> PAS signalé (cas particulier)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <canvas style="line-height: 30px;"></canvas>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10121(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10121_svg_exception_not_reported(context_factory, run_rgaa):
    """Test 10.12.1: SVG -> PAS signalé (cas particulier)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <svg style="line-height: 30px;"></svg>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10121(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10121_multiple_conflicts(context_factory, run_rgaa):
    """Test 10.12.1: Plusieurs conflits détectés."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="line-height: 24px;">Conflit 1</div>
        <p style="margin-bottom: 30px;">Conflit 2</p>
        <span style="letter-spacing: 2px;">Conflit 3</span>
        <span style="word-spacing: 4px;">Conflit 4</span>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10121(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 4
    assert result.metadata["line_height_conflicts"] == 1
    assert result.metadata["margin_bottom_conflicts"] == 1
    assert result.metadata["letter_spacing_conflicts"] == 1
    assert result.metadata["word_spacing_conflicts"] == 1


def test_10121_missing_dom_returns_not_tested(context_factory, run_rgaa):
    """Test 10.12.1: DOM manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    test = RGAA10121()
    context = SimpleNamespace(dom=None)

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_dom"


def test_10121_metadata_contains_manual_checks(context_factory, run_rgaa):
    """Test 10.12.1: Les métadonnées contiennent les vérifications manuelles requises."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><div style="line-height: 24px;">Test</div></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10121(), context)

    assert result.metadata["browser_check_required"] is True
    checks = result.metadata["required_manual_checks"]
    assert any("line-height: 1.5" in c for c in checks)
    assert any("margin-bottom: 2em" in c for c in checks)
    assert any("letter-spacing: 0.12em" in c for c in checks)
    assert any("word-spacing: 0.16em" in c for c in checks)
    assert any("texte reste lisible" in c for c in checks)
    assert any("perte de contenu" in c for c in checks)
    expected_manual = "critère 10.12.1 - espacement du texte redéfinissable par l'utilisateur"
    assert result.metadata["manual_check_for"] == expected_manual
    assert "exceptions" in result.metadata
    assert "sous-titres directement intégrés à une vidéo" in result.metadata["exceptions"]
    assert "images texte" in result.metadata["exceptions"]
    assert "texte au sein d'une balise <canvas>" in result.metadata["exceptions"]
    assert "applied_styles" in result.metadata
    assert result.metadata["applied_styles"]["line-height"] == "1.5"
    assert result.metadata["applied_styles"]["margin-bottom (p)"] == "2em"
    assert result.metadata["applied_styles"]["letter-spacing"] == "0.12em"
    assert result.metadata["applied_styles"]["word-spacing"] == "0.16em"
    assert "reference" in result.metadata
    assert "WCAG 1.4.12" in result.metadata["reference"]


def test_10121_script_style_ignored(context_factory, run_rgaa):
    """Test 10.12.1: Les éléments script/style sont ignorés."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>body { line-height: 24px; }</style>
        <script>console.log("test");</script>
    </head>
    <body>
        <p>Contenu</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10121(), context)

    # Les styles dans <style> ne sont pas détectés (inline seulement)
    # Les éléments script/style sont ignorés
    assert result.status == Status.PASS
    assert result.tested_elements == 0
