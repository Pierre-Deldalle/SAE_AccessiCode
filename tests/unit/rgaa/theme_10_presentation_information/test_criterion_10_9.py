from __future__ import annotations

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_9 import (
    Test1091 as RGAA1091,
)
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_9 import (
    Test1092 as RGAA1092,
)
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_9 import (
    Test1093 as RGAA1093,
)
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_9 import (
    Test1094 as RGAA1094,
)

# =============================================================================
# Tests for Test1091 - Textes et caractéristiques sensorielles
# =============================================================================


def test_1091_no_sensory_text_passes(context_factory, run_rgaa):
    """Test 10.9.1: Page sans texte référençant des caractéristiques sensorielles passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Bienvenue sur notre site web.</p>
        <button>Valider</button>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1091(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0
    assert "Aucun texte faisant référence" in result.summary


def test_1091_text_references_shape_needs_review(context_factory, run_rgaa):
    """Test 10.9.1: Texte référençant la forme d'un bouton -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Cliquez sur le bouton rond pour valider.</p>
        <button>Valider</button>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1091(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "sensory_reference_without_text_alternative"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert "forme" in findings[0].evidence["sensory_types"]


def test_1091_text_references_size_needs_review(context_factory, run_rgaa):
    """Test 10.9.1: Texte référençant la taille -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Sélectionnez la grande boîte à gauche.</p>
        <div class="box">Contenu</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1091(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "sensory_reference_without_text_alternative"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert "taille" in findings[0].evidence["sensory_types"]


def test_1091_text_references_position_needs_review(context_factory, run_rgaa):
    """Test 10.9.1: Texte référençant la position -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Le menu se trouve en haut à droite.</p>
        <nav>Navigation</nav>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1091(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "sensory_reference_without_text_alternative"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert "position" in findings[0].evidence["sensory_types"]


def test_1091_text_references_color_needs_review(context_factory, run_rgaa):
    """Test 10.9.1: Texte référençant la couleur -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Appuyez sur le bouton vert pour continuer.</p>
        <button>Continuer</button>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1091(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "sensory_reference_without_text_alternative"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert "couleur" in findings[0].evidence["sensory_types"]


def test_1091_text_no_ui_reference_passes(context_factory, run_rgaa):
    """Test 10.9.1: Texte avec référence sensorielle mais pas d'élément UI -> PASS (hors périmètre)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Le ciel est bleu et les nuages sont blancs.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1091(), context)

    # Pas de référence à un élément d'interface
    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_1091_multiple_sensory_references(context_factory, run_rgaa):
    """Test 10.9.1: Plusieurs références sensorielles dans la page."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Cliquez sur le gros bouton rouge à gauche.</p>
        <button>Action 1</button>
        <p>Le petit lien en bas de page.</p>
        <a href="#">Lien</a>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1091(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 2


def test_1091_short_text_ignored(context_factory, run_rgaa):
    """Test 10.9.1: Textes trop courts sont ignorés."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Rond.</p>
        <button>OK</button>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1091(), context)

    # Texte trop court (< 10 caractères) -> ignoré
    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_1091_missing_dom_returns_not_tested(context_factory, run_rgaa):
    """Test 10.9.1: DOM manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    test = RGAA1091()
    context = SimpleNamespace(dom=None)

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_dom"


def test_1091_metadata_contains_manual_checks(context_factory, run_rgaa):
    """Test 10.9.1: Les métadonnées contiennent les vérifications manuelles requises."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><p>Cliquez sur le bouton rond.</p><button>OK</button></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1091(), context)

    assert result.metadata["browser_check_required"] is True
    checks = result.metadata["required_manual_checks"]
    assert any("alternative textuelle" in c for c in checks)
    assert any("transmise uniquement visuellement" in c for c in checks)
    assert result.metadata["manual_check_for"] == "critère 10.9.1 - information par forme/taille/position (textes)"


# =============================================================================
# Tests for Test1092 - Images et caractéristiques sensorielles
# =============================================================================


def test_1092_no_images_passes(context_factory, run_rgaa):
    """Test 10.9.2: Page sans images passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><p>Contenu textuel uniquement.</p></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1092(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0
    assert "Aucune image" in result.summary


def test_1092_image_without_alt_sensory_context_needs_review(context_factory, run_rgaa):
    """Test 10.9.2: Image sans alt dans contexte sensoriel -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Voyez l'icône ronde à gauche.</p>
        <img src="icon.png">
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1092(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    findings = [f for f in result.findings if f.evidence.get("condition") == "image_sensory_info_without_alt"]
    assert len(findings) >= 1
    assert findings[0].evidence["has_alt"] is False


def test_1092_image_with_empty_alt_decorative_passes(context_factory, run_rgaa):
    """Test 10.9.2: Image avec alt='' (décorative) -> PAS détectée comme problème."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Voyez l'icône ronde à gauche.</p>
        <img src="icon.png" alt="">
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1092(), context)

    # alt="" indique décoratif, pas de problème signalé
    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_1092_image_with_alt_missing_sensory_desc_needs_review(context_factory, run_rgaa):
    """Test 10.9.2: Image avec alt mais ne décrivant pas l'info sensorielle -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Cliquez sur le gros bouton vert.</p>
        <img src="button.png" alt="Bouton">
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1092(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    findings = [f for f in result.findings if f.evidence.get("condition") == "image_alt_missing_sensory_description"]
    assert len(findings) >= 1
    assert findings[0].evidence["has_alt"] is True
    assert "taille" in findings[0].evidence["context_sensory_types"]
    assert "couleur" in findings[0].evidence["context_sensory_types"]


def test_1092_image_with_good_alt_passes(context_factory, run_rgaa):
    """Test 10.9.2: Image avec alt décrivant l'info sensorielle -> PASS."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Cliquez sur le gros bouton vert.</p>
        <img src="button.png" alt="Gros bouton vert pour valider">
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1092(), context)

    # L'alt décrit bien les caractéristiques sensorielles
    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_1092_image_no_sensory_context_passes(context_factory, run_rgaa):
    """Test 10.9.2: Image sans contexte sensoriel -> PASS (même sans alt)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Bienvenue sur notre site.</p>
        <img src="logo.png">
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1092(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_1092_multiple_images_some_issues(context_factory, run_rgaa):
    """Test 10.9.2: Plusieurs images, certaines avec problèmes."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>L'icône carrée en haut.</p>
        <img src="icon1.png">
        <p>Photo de l'équipe.</p>
        <img src="team.jpg" alt="Équipe au complet">
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1092(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1  # Seule la première a un problème


def test_1092_missing_dom_returns_not_tested(context_factory, run_rgaa):
    """Test 10.9.2: DOM manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    test = RGAA1092()
    context = SimpleNamespace(dom=None)

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_dom"


def test_1092_metadata_contains_manual_checks(context_factory, run_rgaa):
    """Test 10.9.2: Les métadonnées contiennent les vérifications manuelles requises."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><p>Voyez l'icône ronde.</p><img src="icon.png"></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1092(), context)

    assert result.metadata["browser_check_required"] is True
    checks = result.metadata["required_manual_checks"]
    assert any("alt descriptif" in c for c in checks)
    assert any("forme/taille/position" in c for c in checks)
    assert any('alt=""' in c for c in checks)
    assert result.metadata["manual_check_for"] == "critère 10.9.2 - information par forme/taille/position (images)"


# =============================================================================
# Tests for Test1093 - Médias temporels et caractéristiques sensorielles
# =============================================================================


def test_1093_no_time_media_passes(context_factory, run_rgaa):
    """Test 10.9.3: Page sans médias temporels passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><p>Contenu sans vidéo ni audio.</p></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1093(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0
    assert "Aucun média temporel" in result.summary


def test_1093_video_without_alternative_sensory_context_needs_review(context_factory, run_rgaa):
    """Test 10.9.3: Vidéo sans alternative dans contexte sensoriel -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Regardez la vidéo carrée en haut à droite.</p>
        <video src="video.mp4"></video>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1093(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "time_media_sensory_info_without_alternative"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert findings[0].evidence["media_type"] == "video"
    assert "forme" in findings[0].evidence["sensory_types"]
    assert "position" in findings[0].evidence["sensory_types"]


def test_1093_video_with_track_passes(context_factory, run_rgaa):
    """Test 10.9.3: Vidéo avec track (sous-titres) -> PASS."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Regardez la vidéo carrée.</p>
        <video src="video.mp4"><track kind="captions" src="subs.vtt"></video>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1093(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_1093_video_with_aria_label_passes(context_factory, run_rgaa):
    """Test 10.9.3: Vidéo avec aria-label -> PASS."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Regardez la vidéo carrée.</p>
        <video src="video.mp4" aria-label="Vidéo carrée de démonstration"></video>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1093(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_1093_audio_without_alternative_sensory_context_needs_review(context_factory, run_rgaa):
    """Test 10.9.3: Audio sans alternative dans contexte sensoriel -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Écoutez le gros fichier audio au centre.</p>
        <audio src="audio.mp3"></audio>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1093(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "time_media_sensory_info_without_alternative"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert findings[0].evidence["media_type"] == "audio"
    assert "taille" in findings[0].evidence["sensory_types"]
    assert "position" in findings[0].evidence["sensory_types"]


def test_1093_media_no_sensory_context_passes(context_factory, run_rgaa):
    """Test 10.9.3: Média sans contexte sensoriel -> PASS."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Bienvenue.</p>
        <video src="video.mp4"></video>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1093(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_1093_missing_dom_returns_not_tested(context_factory, run_rgaa):
    """Test 10.9.3: DOM manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    test = RGAA1093()
    context = SimpleNamespace(dom=None)

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_dom"


def test_1093_metadata_contains_manual_checks(context_factory, run_rgaa):
    """Test 10.9.3: Les métadonnées contiennent les vérifications manuelles requises."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><p>Regardez la vidéo ronde.</p><video src="v.mp4"></video></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1093(), context)

    assert result.metadata["browser_check_required"] is True
    checks = result.metadata["required_manual_checks"]
    assert any("sous-titres" in c or "transcription" in c for c in checks)
    assert any("aria-label" in c or "aria-describedby" in c for c in checks)
    assert any("forme/taille/position" in c for c in checks)
    expected = "critère 10.9.3 - information par forme/taille/position (médias temporels)"
    assert result.metadata["manual_check_for"] == expected


# =============================================================================
# Tests for Test1094 - Médias non temporels et caractéristiques sensorielles
# =============================================================================


def test_1094_no_non_time_media_passes(context_factory, run_rgaa):
    """Test 10.9.4: Page sans médias non temporels passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><p>Contenu sans canvas, svg, object, embed, iframe.</p></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1094(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0
    assert "Aucun média non temporel" in result.summary


def test_1094_canvas_without_alternative_sensory_context_needs_review(context_factory, run_rgaa):
    """Test 10.9.4: Canvas sans alternative dans contexte sensoriel -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Voyez le graphique circulaire à gauche.</p>
        <canvas id="chart"></canvas>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1094(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "non_time_media_sensory_info_without_alternative"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert findings[0].evidence["media_type"] == "canvas"
    assert "forme" in findings[0].evidence["sensory_types"]
    assert "position" in findings[0].evidence["sensory_types"]


def test_1094_canvas_with_fallback_passes(context_factory, run_rgaa):
    """Test 10.9.4: Canvas avec contenu de fallback -> PASS."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Voyez le graphique circulaire.</p>
        <canvas id="chart">Graphique circulaire montrant 60% de satisfaction</canvas>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1094(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_1094_canvas_with_aria_label_passes(context_factory, run_rgaa):
    """Test 10.9.4: Canvas avec aria-label -> PASS."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Voyez le graphique circulaire.</p>
        <canvas id="chart" aria-label="Graphique circulaire de satisfaction"></canvas>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1094(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_1094_svg_with_role_img_passes(context_factory, run_rgaa):
    """Test 10.9.4: SVG avec role=img -> PASS."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>L'icône triangulaire en haut.</p>
        <svg role="img" aria-label="Icône triangulaire de navigation"></svg>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1094(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_1094_object_without_alternative_needs_review(context_factory, run_rgaa):
    """Test 10.9.4: Object sans alternative dans contexte sensoriel -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Le document PDF rectangulaire au centre.</p>
        <object data="doc.pdf" type="application/pdf"></object>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1094(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    condition = "non_time_media_sensory_info_without_alternative"
    findings = [f for f in result.findings if f.evidence.get("condition") == condition]
    assert len(findings) >= 1
    assert findings[0].evidence["media_type"] == "object"


def test_1094_embed_without_alternative_needs_review(context_factory, run_rgaa):
    """Test 10.9.4: Embed sans alternative dans contexte sensoriel -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>L'animation carrée en bas.</p>
        <embed src="anim.swf" type="application/x-shockwave-flash">
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1094(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1094_iframe_without_alternative_needs_review(context_factory, run_rgaa):
    """Test 10.9.4: Iframe sans alternative dans contexte sensoriel -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>La carte interactive grande à droite.</p>
        <iframe src="map.html"></iframe>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1094(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1094_media_no_sensory_context_passes(context_factory, run_rgaa):
    """Test 10.9.4: Média sans contexte sensoriel -> PASS."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Bienvenue.</p>
        <canvas id="chart"></canvas>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1094(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_1094_missing_dom_returns_not_tested(context_factory, run_rgaa):
    """Test 10.9.4: DOM manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    test = RGAA1094()
    context = SimpleNamespace(dom=None)

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_dom"


def test_1094_metadata_contains_manual_checks(context_factory, run_rgaa):
    """Test 10.9.4: Les métadonnées contiennent les vérifications manuelles requises."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><p>Voyez le canvas rond.</p><canvas id="c"></canvas></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1094(), context)

    assert result.metadata["browser_check_required"] is True
    checks = result.metadata["required_manual_checks"]
    assert any("aria-label" in c or "aria-describedby" in c for c in checks)
    assert any("role" in c and "img" in c for c in checks)
    assert any("fallback" in c or "canvas" in c for c in checks)
    assert any("forme/taille/position" in c for c in checks)
    expected = "critère 10.9.4 - information par forme/taille/position (médias non temporels)"
    assert result.metadata["manual_check_for"] == expected
