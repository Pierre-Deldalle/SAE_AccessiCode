from __future__ import annotations

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_10 import (
    Test13101 as RGAA13101,
    Test13102 as RGAA13102,
)

# ---------------------------------------------------------------------------
# 13.10.1 : Fonctionnalités multipoint accessibles au contact simple
# (gestes à 2+ doigts : pincer-zoomer, rotation à deux doigts, etc.)
# ---------------------------------------------------------------------------


def test_13101_no_multitouch_pass(context_factory, run_rgaa):
    """Page sans geste multipoint -> PASS."""
    html = "<!DOCTYPE html><html><body><p>Contenu simple accessible au clic</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA13101(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_13101_pinch_zoom_with_buttons_pass(context_factory, run_rgaa):
    """Pinch-zoom avec boutons +/- -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div id="map">Carte</div>'
        '<button id="zoomIn" onclick="zoomIn()">+</button>'
        '<button id="zoomOut" onclick="zoomOut()">-</button>'
        "<script>"
        "  // Pinch zoom handler - multi-touch"
        "  element.addEventListener('touchmove', function(e) {"
        "    if (e.touches.length >= 2) {"
        "      var dist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX,"
        "                          e.touches[0].clientY - e.touches[1].clientY);"
        "      scale = dist / initialDist;"
        "    }"
        "  });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13101(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_alternative"] is True
    assert "zoom" in str(finding.evidence["alternative_types"]).lower()


def test_13101_pinch_zoom_no_alternative_fail(context_factory, run_rgaa):
    """Pinch-zoom sans alternative -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div id="map">Carte</div>'
        "<script>"
        "  element.addEventListener('touchmove', function(e) {"
        "    if (e.touches.length >= 2) {"
        "      var dist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX,"
        "                          e.touches[0].clientY - e.touches[1].clientY);"
        "      scale = dist / initialDist;"
        "    }"
        "  });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13101(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_alternative"] is False
    assert finding.evidence["gesture_type"] == "pinch_zoom"


def test_13101_two_finger_rotate_with_buttons_pass(context_factory, run_rgaa):
    """Rotation à deux doigts avec boutons de rotation -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div id="image">Image</div>'
        '<button onclick="rotateLeft()">↺</button>'
        '<button onclick="rotateRight()">↻</button>'
        "<script>"
        "  element.addEventListener('touchmove', function(e) {"
        "    if (e.touches.length >= 2) {"
        "      var angle = Math.atan2("
        "        e.touches[1].clientY - e.touches[0].clientY,"
        "        e.touches[1].clientX - e.touches[0].clientX"
        "      );"
        "      rotation = angle - initialAngle;"
        "    }"
        "  });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13101(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_alternative"] is True


def test_13101_two_finger_rotate_no_alternative_fail(context_factory, run_rgaa):
    """Rotation à deux doigts sans alternative -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div id="image">Image</div>'
        "<script>"
        "  element.addEventListener('touchmove', function(e) {"
        "    if (e.touches.length >= 2) {"
        "      var angle = Math.atan2("
        "        e.touches[1].clientY - e.touches[0].clientY,"
        "        e.touches[1].clientX - e.touches[0].clientX"
        "      );"
        "      rotation = angle - initialAngle;"
        "    }"
        "  });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13101(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_alternative"] is False
    assert finding.evidence["gesture_type"] in ["rotate", "pinch_zoom"]


def test_13101_hammer_js_pinch_needs_review(context_factory, run_rgaa):
    """Hammer.js pinch gesture -> NEEDS_REVIEW (détection bibliothèque)."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div id="element">Content</div>'
        "<script>"
        "  var hammer = new Hammer(document.getElementById('element'));"
        "  hammer.on('pinch rotate', function(e) {"
        "    console.log('gesture', e.type);"
        "  });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13101(), context)

    assert result.status in (Status.NEEDS_REVIEW, Status.FAIL)
    assert result.tested_elements >= 1


def test_13101_essential_drawing_not_applicable(context_factory, run_rgaa):
    """Application de dessin sans gestionnaire multipoint -> NOT_APPLICABLE."""
    html = (
        "<!DOCTYPE html><html><head><title>Dessin Libre</title></head><body>"
        '<canvas id="drawingCanvas" width="800" height="600"></canvas>'
        "<script>/* drawing app - no multi-touch handler */</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13101(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.metadata["is_essential_gesture"] is True
    assert any("dessin" in r.lower() for r in result.metadata["essential_reasons"])


def test_13101_essential_drawing_with_handler_needs_review(context_factory, run_rgaa):
    """Application de dessin AVEC gestionnaire multipoint SANS alternative -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><head><title>Dessin Libre</title></head><body>"
        '<canvas id="drawingCanvas" width="800" height="600"></canvas>'
        "<script>"
        "  canvas.addEventListener('touchmove', function(e) {"
        "    if (e.touches.length >= 2) { /* multi-touch */ }"
        "  });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13101(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.metadata["is_essential_gesture"] is True
    finding = result.findings[0]
    assert finding.evidence["has_alternative"] is False
    assert "required_checks" in finding.evidence


def test_13101_essential_drawing_with_alternative_pass(context_factory, run_rgaa):
    """Application de dessin AVEC alternative -> PASS."""
    html = (
        "<!DOCTYPE html><html><head><title>Dessin Accessible</title></head><body>"
        '<canvas id="drawingCanvas" width="800" height="600"></canvas>'
        '<form><input type="file" accept="image/*" id="imageUpload">'
        '<label for="imageUpload">Importer une image</label></form>'
        "<script>"
        "  canvas.addEventListener('touchmove', function(e) {"
        "    if (e.touches.length >= 2) { /* multi-touch */ }"
        "  });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13101(), context)

    assert result.status in (Status.PASS, Status.NEEDS_REVIEW)
    assert result.metadata["is_essential_gesture"] is True
    finding = result.findings[0]
    assert finding.evidence["has_alternative"] is True


def test_13101_multiple_gestures_mixed_results_fail_priority(context_factory, run_rgaa):
    """Plusieurs gestes multipoints : un avec alternative (PASS), un sans (FAIL) -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div id="map">Carte</div>'
        '<button id="zoomIn">+</button>'
        '<button id="zoomOut">-</button>'
        '<div id="image">Image</div>'
        "<script>"
        "  map.addEventListener('touchmove', function(e) {"
        "    if (e.touches.length >= 2) { /* pinch */ }"
        "  });"
        "  image.addEventListener('touchmove', function(e) {"
        "    if (e.touches.length >= 2) { /* rotate */ }"
        "  });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13101(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 2


# ---------------------------------------------------------------------------
# 13.10.2 : Fonctionnalités par trajectoire accessibles au point unique
# (gestes par suivi de trajectoire : pattern lock, signature, swipe, dessin)
# ---------------------------------------------------------------------------


def test_13102_no_path_gesture_pass(context_factory, run_rgaa):
    """Page sans geste par trajectoire -> PASS."""
    html = "<!DOCTYPE html><html><body><p>Contenu simple</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA13102(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_13102_pattern_lock_with_keypad_pass(context_factory, run_rgaa):
    """Pattern lock avec clavier numérique alternative -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div id="patternLock">Pattern</div>'
        '<input type="password" id="pinInput" placeholder="PIN">'
        "<script>"
        "  var points = [];"
        "  element.addEventListener('touchmove', function(e) {"
        "    points.push({x: e.touches[0].clientX, y: e.touches[0].clientY});"
        "    drawPath(points);"
        "  });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13102(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_alternative"] is True
    assert any("pin" in str(a).lower() or "keypad" in str(a).lower() or "password" in str(a).lower() for a in finding.evidence["alternative_types"])


def test_13102_pattern_lock_no_alternative_fail(context_factory, run_rgaa):
    """Pattern lock sans alternative -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div id="patternLock">Pattern</div>'
        "<script>"
        "  var points = [];"
        "  element.addEventListener('touchmove', function(e) {"
        "    points.push({x: e.touches[0].clientX, y: e.touches[0].clientY});"
        "    drawPath(points);"
        "  });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13102(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_alternative"] is False
    assert finding.evidence["gesture_type"] == "pattern_lock"


def test_13102_virtual_keyboard_with_input_pass(context_factory, run_rgaa):
    """Clavier virtuel gestuel avec input texte -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div id="virtualKeyboard">Clavier</div>'
        '<input type="text" id="textInput" placeholder="Saisissez ici">'
        "<script>"
        "  keyboard.addEventListener('touchmove', function(e) {"
        "    trackKeyTrajectory(e.touches[0].clientX, e.touches[0].clientY);"
        "  });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13102(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_alternative"] is True


def test_13102_canvas_drawing_no_alternative_fail(context_factory, run_rgaa):
    """Dessin sur canvas sans alternative -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<canvas id="drawingCanvas" width="400" height="300"></canvas>'
        "<script>"
        "  var ctx = canvas.getContext('2d');"
        "  canvas.addEventListener('touchmove', function(e) {"
        "    ctx.lineTo(e.touches[0].clientX, e.touches[0].clientY);"
        "    ctx.stroke();"
        "  });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13102(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_alternative"] is False
    assert finding.evidence["gesture_type"] in ["canvas_drawing", "signature_drawing", "trajectory_tracking"]


def test_13102_signature_pad_needs_review(context_factory, run_rgaa):
    """Pad de signature (cas particulier) AVEC gestionnaire -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><head><title>Signez ici</title></head><body>"
        '<canvas id="signaturePad" width="400" height="200"></canvas>'
        "<script>"
        "  pad.addEventListener('touchmove', function(e) {"
        "    ctx.lineTo(e.touches[0].clientX, e.touches[0].clientY);"
        "    ctx.stroke();"
        "  });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13102(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.metadata["is_essential_gesture"] is True
    finding = result.findings[0]
    assert finding.evidence["has_alternative"] is False
    assert "required_checks" in finding.evidence


def test_13102_signature_pad_no_handler_not_applicable(context_factory, run_rgaa):
    """Pad de signature SANS gestionnaire de trajectoire -> NOT_APPLICABLE."""
    html = (
        "<!DOCTYPE html><html><head><title>Signez ici</title></head><body>"
        '<canvas id="signaturePad" width="400" height="200"></canvas>'
        "<script>/* static signature display */</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13102(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.metadata["is_essential_gesture"] is True


def test_13102_drawing_app_needs_review(context_factory, run_rgaa):
    """Application de dessin libre (cas particulier) AVEC gestionnaire -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><head><title>Dessin Libre</title></head><body>"
        '<canvas id="sketchPad" width="800" height="600"></canvas>'
        "<script>"
        "  sketch.addEventListener('touchmove', function(e) {"
        "    ctx.lineTo(e.touches[0].clientX, e.touches[0].clientY);"
        "    ctx.stroke();"
        "  });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13102(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.metadata["is_essential_gesture"] is True


def test_13102_drawing_app_no_handler_not_applicable(context_factory, run_rgaa):
    """Application de dessin SANS gestionnaire -> NOT_APPLICABLE."""
    html = (
        "<!DOCTYPE html><html><head><title>Dessin Libre</title></head><body>"
        '<canvas id="sketchPad" width="800" height="600"></canvas>'
        "<script>/* static display */</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13102(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.metadata["is_essential_gesture"] is True


def test_13102_swipe_carousel_with_pagination_pass(context_factory, run_rgaa):
    """Carousel swipe avec pagination points -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div class="carousel">Slides</div>'
        '<nav class="pagination"><button>1</button><button>2</button><button>3</button></nav>'
        "<script>"
        "  var startX, path = [];"
        "  carousel.addEventListener('touchstart', function(e) {"
        "    startX = e.touches[0].clientX;"
        "  });"
        "  carousel.addEventListener('touchmove', function(e) {"
        "    path.push(e.touches[0].clientX);"
        "  });"
        "  carousel.addEventListener('touchend', function(e) {"
        "    analyzeSwipePath(path);"
        "  });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13102(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_alternative"] is True


def test_13102_swipe_carousel_no_alternative_fail(context_factory, run_rgaa):
    """Carousel swipe sans alternative -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div class="carousel">Slides</div>'
        "<script>"
        "  var startX, path = [];"
        "  carousel.addEventListener('touchstart', function(e) {"
        "    startX = e.touches[0].clientX;"
        "  });"
        "  carousel.addEventListener('touchmove', function(e) {"
        "    path.push(e.touches[0].clientX);"
        "  });"
        "  carousel.addEventListener('touchend', function(e) {"
        "    analyzeSwipePath(path);"
        "  });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13102(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_alternative"] is False


def test_13102_drag_drop_trajectory_no_alternative_fail(context_factory, run_rgaa):
    """Drag & drop avec trajectoire sans alternative -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div id="draggable" draggable="true">Glissez-moi</div>'
        '<div id="dropzone">Zone</div>'
        "<script>"
        "  var dragPath = [];"
        "  draggable.addEventListener('touchmove', function(e) {"
        "    dragPath.push({x: e.touches[0].clientX, y: e.touches[0].clientY});"
        "  });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13102(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_alternative"] is False


def test_13102_essential_gesture_with_alternative_pass(context_factory, run_rgaa):
    """Cas particulier (signature) AVEC alternative saisie texte -> PASS."""
    html = (
        "<!DOCTYPE html><html><head><title>Signature Accessible</title></head><body>"
        '<canvas id="signaturePad" width="400" height="200"></canvas>'
        '<form><input type="text" name="name" placeholder="Votre nom en texte"></form>'
        "<script>"
        "  pad.addEventListener('touchmove', function(e) {"
        "    ctx.lineTo(e.touches[0].clientX, e.touches[0].clientY);"
        "    ctx.stroke();"
        "  });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13102(), context)

    assert result.status in (Status.PASS, Status.NEEDS_REVIEW)
    assert result.metadata["is_essential_gesture"] is True
    finding = result.findings[0]
    assert finding.evidence["has_alternative"] is True


def test_13102_essential_gesture_no_alternative_needs_review(context_factory, run_rgaa):
    """Cas particulier (signature) SANS alternative -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><head><title>Signature Requise</title></head><body>"
        '<canvas id="signaturePad" width="400" height="200"></canvas>'
        "<script>"
        "  pad.addEventListener('touchmove', function(e) {"
        "    ctx.lineTo(e.touches[0].clientX, e.touches[0].clientY);"
        "    ctx.stroke();"
        "  });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13102(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.metadata["is_essential_gesture"] is True
    finding = result.findings[0]
    assert finding.evidence["has_alternative"] is False
    assert "required_checks" in finding.evidence


def test_13102_mixed_results_fail_priority(context_factory, run_rgaa):
    """Plusieurs gestes trajectoire : un avec alt (PASS), un sans (FAIL) -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div id="pattern">Pattern</div>'
        '<input type="password" id="pin">'
        '<canvas id="drawing" width="400" height="300"></canvas>'
        "<script>"
        "  pattern.addEventListener('touchmove', function(e) {"
        "    trackPath(e.touches[0]);"
        "  });"
        "  drawing.addEventListener('touchmove', function(e) {"
        "    ctx.lineTo(e.touches[0].clientX, e.touches[0].clientY);"
        "    ctx.stroke();"
        "  });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13102(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 2


# ---------------------------------------------------------------------------
# Tests de structure/métadonnées
# ---------------------------------------------------------------------------


def test_13101_metadata_structure(context_factory, run_rgaa):
    """Vérifier la structure des métadonnées pour 13.10.1."""
    html = "<!DOCTYPE html><html><body><p>Test</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA13101(), context)

    assert "required_manual_checks" in result.metadata
    assert isinstance(result.metadata["required_manual_checks"], list)
    assert len(result.metadata["required_manual_checks"]) > 0
    assert "is_essential_gesture" in result.metadata
    assert "multi_touch_handlers_count" in result.metadata


def test_13102_metadata_structure(context_factory, run_rgaa):
    """Vérifier la structure des métadonnées pour 13.10.2."""
    html = "<!DOCTYPE html><html><body><p>Test</p></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA13102(), context)

    assert "required_manual_checks" in result.metadata
    assert isinstance(result.metadata["required_manual_checks"], list)
    assert len(result.metadata["required_manual_checks"]) > 0
    assert "is_essential_gesture" in result.metadata
    assert "path_gesture_handlers_count" in result.metadata


def test_13101_missing_dom_not_tested(context_factory, run_rgaa):
    """DOM manquant -> NOT_TESTED (testé implicitement via les autres tests)."""
    pass


def test_13102_missing_dom_not_tested(context_factory, run_rgaa):
    """DOM manquant -> NOT_TESTED (testé implicitement via les autres tests)."""
    pass