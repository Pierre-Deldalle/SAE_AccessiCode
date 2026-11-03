from __future__ import annotations

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_11 import (
    Test10111 as RGAA10111,
)
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_11 import (
    Test10112 as RGAA10112,
)

# =============================================================================
# Tests for Test10111 - Reflow horizontal à 320px
# =============================================================================


def test_10111_no_fixed_width_passes(context_factory, run_rgaa):
    """Test 10.11.1: Page sans largeur fixe > 320px passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="max-width: 100%;">Contenu responsive</div>
        <p>Texte qui s'adapte.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0
    assert "Aucun problème évident" in result.summary


def test_10111_fixed_width_over_320px_needs_review(context_factory, run_rgaa):
    """Test 10.11.1: Élément avec width fixe > 320px -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="width: 500px;">Conteneur trop large</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "fixed_width_prevents_reflow"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert findings[0].evidence["check_type"] == "fixed_width_over_320px"
    assert "> 320px" in findings[0].evidence["style_details"]


def test_10111_min_width_over_320px_needs_review(context_factory, run_rgaa):
    """Test 10.11.1: Élément avec min-width > 320px -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="min-width: 400px;">Conteneur avec min-width</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "fixed_width_prevents_reflow"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert "min-width" in findings[0].evidence["style_details"]


def test_10111_max_width_over_320px_needs_review(context_factory, run_rgaa):
    """Test 10.11.1: Élément avec max-width > 320px -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="max-width: 600px;">Conteneur avec max-width</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "fixed_width_prevents_reflow"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert "max-width" in findings[0].evidence["style_details"]


def test_10111_horizontal_overflow_needs_review(context_factory, run_rgaa):
    """Test 10.11.1: Élément avec overflow-x: scroll -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="overflow-x: scroll;">Conteneur avec scroll horizontal</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "horizontal_overflow_prevents_reflow"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert findings[0].evidence["check_type"] == "horizontal_overflow"
    assert "overflow-x" in findings[0].evidence["style_details"]


def test_10111_overflow_auto_needs_review(context_factory, run_rgaa):
    """Test 10.11.1: Élément avec overflow: auto -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="overflow: auto;">Conteneur avec overflow auto</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "horizontal_overflow_prevents_reflow"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert "overflow" in findings[0].evidence["style_details"]


def test_10111_white_space_nowrap_long_text_needs_review(context_factory, run_rgaa):
    """Test 10.11.1: Élément avec white-space: nowrap et texte long -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="white-space: nowrap;">
            Ceci est un texte très long qui ne peut pas revenir à la ligne
            et qui va dépasser 320 pixels de large facilement
        </p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "nowrap_prevents_reflow"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert findings[0].evidence["check_type"] == "white_space_nowrap"
    assert "nowrap" in findings[0].evidence["style_details"]


def test_10111_white_space_nowrap_short_text_passes(context_factory, run_rgaa):
    """Test 10.11.1: Élément avec white-space: nowrap mais texte court -> PAS signalé."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <button style="white-space: nowrap;">OK</button>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    # Texte court (< 50 caractères) -> pas de problème signalé
    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10111_image_exception_not_reported(context_factory, run_rgaa):
    """Test 10.11.1: Image avec width > 320px -> PAS signalée (cas particulier)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <img src="large.jpg" style="width: 800px;" alt="Grande image">
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    # Image = cas particulier, ne doit pas être signalée
    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10111_video_exception_not_reported(context_factory, run_rgaa):
    """Test 10.11.1: Vidéo avec width > 320px -> PAS signalée (cas particulier)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <video src="video.mp4" style="width: 600px;"></video>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10111_canvas_exception_not_reported(context_factory, run_rgaa):
    """Test 10.11.1: Canvas avec width > 320px -> PAS signalé (cas particulier)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <canvas style="width: 500px;"></canvas>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10111_svg_exception_not_reported(context_factory, run_rgaa):
    """Test 10.11.1: SVG avec width > 320px -> PAS signalé (cas particulier)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <svg style="width: 500px;"></svg>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10111_data_table_exception_not_reported(context_factory, run_rgaa):
    """Test 10.11.1: Tableau de données avec width > 320px -> PAS signalé (cas particulier)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <table style="width: 600px;">
            <thead><tr><th>Colonne 1</th><th>Colonne 2</th></tr></thead>
            <tbody><tr><td>Donnée 1</td><td>Donnée 2</td></tr></tbody>
        </table>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    # Tableau de données (avec thead/th) = cas particulier
    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10111_layout_table_without_th_reported(context_factory, run_rgaa):
    """Test 10.11.1: Tableau de mise en page (sans th) avec width > 320px -> signalé."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <table style="width: 600px;">
            <tr><td>Cellule 1</td><td>Cellule 2</td></tr>
        </table>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    # Tableau sans th/thead = tableau de mise en page, pas exempté
    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "fixed_width_prevents_reflow"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1


def test_10111_iframe_exception_not_reported(context_factory, run_rgaa):
    """Test 10.11.1: Iframe -> PAS signalé (cas particulier)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <iframe src="page.html" style="width: 800px;"></iframe>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10111_object_exception_not_reported(context_factory, run_rgaa):
    """Test 10.11.1: Object -> PAS signalé (cas particulier)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <object data="doc.pdf" style="width: 600px;"></object>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10111_embed_exception_not_reported(context_factory, run_rgaa):
    """Test 10.11.1: Embed -> PAS signalé (cas particulier)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <embed src="anim.swf" style="width: 500px;">
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10111_multiple_issues(context_factory, run_rgaa):
    """Test 10.11.1: Plusieurs problèmes détectés."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="width: 500px;">Problème 1</div>
        <div style="overflow-x: scroll;">Problème 2</div>
        <p style="white-space: nowrap;">Texte très long qui ne peut pas revenir à la ligne et qui va dépasser</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 3


def test_10111_missing_dom_returns_not_tested(context_factory, run_rgaa):
    """Test 10.11.1: DOM manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    test = RGAA10111()
    context = SimpleNamespace(dom=None)

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_dom"


def test_10111_metadata_contains_manual_checks(context_factory, run_rgaa):
    """Test 10.11.1: Les métadonnées contiennent les vérifications manuelles requises."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><div style="width: 500px;">Test</div></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    assert result.metadata["browser_check_required"] is True
    checks = result.metadata["required_manual_checks"]
    assert any("320px" in c for c in checks)
    assert any("défilement horizontal" in c for c in checks)
    assert any("fonctionnalités restent accessibles" in c for c in checks)
    assert result.metadata["manual_check_for"] == "critère 10.11.1 - reflow horizontal à 320px"
    assert "exceptions" in result.metadata
    assert "images, graphiques, vidéos" in result.metadata["exceptions"]
    assert "tableaux de données" in result.metadata["exceptions"]


def test_10111_percentage_width_passes(context_factory, run_rgaa):
    """Test 10.11.1: Largeur en pourcentage -> PAS signalé."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="width: 100%;">Largeur relative</div>
        <div style="max-width: 100%;">Max-width relative</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10111_vw_units_passes(context_factory, run_rgaa):
    """Test 10.11.1: Largeur en vw -> PAS signalé."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="width: 90vw;">Largeur en vw</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10111_rem_units_passes(context_factory, run_rgaa):
    """Test 10.11.1: Largeur en rem -> PAS signalé."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="width: 20rem;">Largeur en rem</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10111(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


# =============================================================================
# Tests for Test10112 - Reflow vertical à 256px
# =============================================================================


def test_10112_no_fixed_height_passes(context_factory, run_rgaa):
    """Test 10.11.2: Page sans hauteur fixe > 256px passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="min-height: 100vh;">Contenu responsive</div>
        <p>Texte qui s'adapte.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10112(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0
    assert "Aucun problème évident" in result.summary


def test_10112_fixed_height_over_256px_needs_review(context_factory, run_rgaa):
    """Test 10.11.2: Élément avec height fixe > 256px -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="height: 400px;">Conteneur trop haut</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10112(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "fixed_height_prevents_reflow"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert findings[0].evidence["check_type"] == "fixed_height_over_256px"
    assert "> 256px" in findings[0].evidence["style_details"]


def test_10112_min_height_over_256px_needs_review(context_factory, run_rgaa):
    """Test 10.11.2: Élément avec min-height > 256px -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="min-height: 300px;">Conteneur avec min-height</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10112(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "fixed_height_prevents_reflow"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert "min-height" in findings[0].evidence["style_details"]


def test_10112_max_height_over_256px_needs_review(context_factory, run_rgaa):
    """Test 10.11.2: Élément avec max-height > 256px -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="max-height: 500px;">Conteneur avec max-height</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10112(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "fixed_height_prevents_reflow"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert "max-height" in findings[0].evidence["style_details"]


def test_10112_vertical_overflow_on_main_container_needs_review(context_factory, run_rgaa):
    """Test 10.11.2: Conteneur principal avec overflow-y: scroll -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <main style="overflow-y: scroll;">Contenu principal</main>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10112(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "vertical_overflow_prevents_reflow"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert findings[0].evidence["check_type"] == "vertical_overflow"
    assert "overflow-y" in findings[0].evidence["style_details"]


def test_10112_overflow_auto_on_body_needs_review(context_factory, run_rgaa):
    """Test 10.11.2: Body avec overflow: auto -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body style="overflow: auto;">
        Contenu
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10112(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "vertical_overflow_prevents_reflow"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert "overflow" in findings[0].evidence["style_details"]


def test_10112_image_exception_not_reported(context_factory, run_rgaa):
    """Test 10.11.2: Image avec height > 256px -> PAS signalée (cas particulier)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <img src="tall.jpg" style="height: 500px;" alt="Grande image">
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10112(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10112_video_exception_not_reported(context_factory, run_rgaa):
    """Test 10.11.2: Vidéo avec height > 256px -> PAS signalée (cas particulier)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <video src="video.mp4" style="height: 400px;"></video>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10112(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10112_table_exception_not_reported(context_factory, run_rgaa):
    """Test 10.11.2: Tableau de données avec height > 256px -> PAS signalé (cas particulier)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <table style="height: 400px;">
            <thead><tr><th>Colonne</th></tr></thead>
            <tbody><tr><td>Donnée</td></tr></tbody>
        </table>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10112(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10112_multiple_issues(context_factory, run_rgaa):
    """Test 10.11.2: Plusieurs problèmes détectés."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="height: 400px;">Problème 1</div>
        <main style="overflow-y: scroll;">Problème 2</main>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10112(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 2


def test_10112_missing_dom_returns_not_tested(context_factory, run_rgaa):
    """Test 10.11.2: DOM manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    test = RGAA10112()
    context = SimpleNamespace(dom=None)

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_dom"


def test_10112_metadata_contains_manual_checks(context_factory, run_rgaa):
    """Test 10.11.2: Les métadonnées contiennent les vérifications manuelles requises."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><div style="height: 400px;">Test</div></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10112(), context)

    assert result.metadata["browser_check_required"] is True
    checks = result.metadata["required_manual_checks"]
    assert any("256px" in c for c in checks)
    assert any("défilement vertical" in c for c in checks)
    assert any("fonctionnalités restent accessibles" in c for c in checks)
    assert result.metadata["manual_check_for"] == "critère 10.11.2 - reflow vertical à 256px"
    assert "exceptions" in result.metadata
    assert "images, graphiques, vidéos" in result.metadata["exceptions"]
    assert "tableaux de données" in result.metadata["exceptions"]
    assert "note" in result.metadata
    assert "sens de lecture est horizontal" in result.metadata["note"]


def test_10112_percentage_height_passes(context_factory, run_rgaa):
    """Test 10.11.2: Hauteur en pourcentage -> PAS signalé."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="height: 100%;">Hauteur relative</div>
        <div style="min-height: 100vh;">Min-height vh</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10112(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10112_vh_units_passes(context_factory, run_rgaa):
    """Test 10.11.2: Hauteur en vh -> PAS signalé."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="height: 90vh;">Hauteur en vh</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10112(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0
