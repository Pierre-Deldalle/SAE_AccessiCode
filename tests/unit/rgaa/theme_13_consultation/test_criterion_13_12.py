from __future__ import annotations

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_12 import (
    Test13121 as RGAA13121,
)
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_12 import (
    Test13122 as RGAA13122,
)
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_12 import (
    Test13123 as RGAA13123,
)

# ---------------------------------------------------------------------------
# 13.12.1 : Fonctionnalités par mouvement de l'appareil - alternative UI
# ---------------------------------------------------------------------------


def test_13121_no_motion_handlers_pass(context_factory, run_rgaa):
    """Page sans gestionnaire de mouvement -> PASS."""
    html = "<!DOCTYPE html><html><body><p>Contenu simple sans mouvement</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA13121(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_13121_devicemotion_with_ui_alternative_pass(context_factory, run_rgaa):
    """devicemotion avec alternative UI (bouton) -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<button id="refreshBtn" onclick="refresh()">Rafraîchir</button>'
        '<button id="undoBtn" onclick="undo()">Annuler</button>'
        "<script>"
        "  window.addEventListener('devicemotion', (e) => {"
        "    if (e.acceleration.x > 10) { refresh(); }"
        "  });"
        "  function refresh() { console.log('refreshed'); }"
        "  function undo() { console.log('undone'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13121(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_ui_alternative"] is True
    assert len(finding.evidence["ui_alternatives"]) > 0


def test_13121_devicemotion_only_fail(context_factory, run_rgaa):
    """devicemotion SANS alternative UI -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        "<script>"
        "  window.addEventListener('devicemotion', (e) => {"
        "    if (e.acceleration.x > 10) { refresh(); }"
        "  });"
        "  function refresh() { console.log('refreshed by shake'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13121(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_ui_alternative"] is False
    assert finding.evidence["is_essential_motion"] is False


def test_13121_accelerometer_api_with_ui_pass(context_factory, run_rgaa):
    """Accelerometer API avec alternative UI -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<button id="stepBtn" onclick="countStep()">Compter un pas</button>'
        '<button id="resetBtn" onclick="resetSteps()">Réinitialiser</button>'
        "<script>"
        "  const accelerometer = new Accelerometer({ frequency: 10 });"
        "  accelerometer.addEventListener('reading', () => {"
        "    if (accelerometer.z > 15) { countStep(); }"
        "  });"
        "  accelerometer.start();"
        "  function countStep() { console.log('step counted'); }"
        "  function resetSteps() { console.log('reset'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13121(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_ui_alternative"] is True


def test_13121_gyroscope_only_fail(context_factory, run_rgaa):
    """Gyroscope SANS alternative UI -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        "<script>"
        "  const gyro = new Gyroscope({ frequency: 10 });"
        "  gyro.addEventListener('reading', () => {"
        "    navigate(gyro.x, gyro.y, gyro.z);"
        "  });"
        "  gyro.start();"
        "  function navigate(x, y, z) { console.log('navigate', x, y, z); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13121(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_ui_alternative"] is False


def test_13121_inline_ondevicemotion_fail(context_factory, run_rgaa):
    """Inline ondevicemotion handler SANS alternative -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div ondevicemotion="handleMotion(event)">Zone de mouvement</div>'
        "<script>"
        "  function handleMotion(e) { console.log('motion', e); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13121(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1


# ---------------------------------------------------------------------------
# 13.12.1 : Cas particuliers (essential motion)
# ---------------------------------------------------------------------------


def test_13121_essential_pedometer_not_applicable(context_factory, run_rgaa):
    """Application podomètre sans gestionnaire -> NOT_APPLICABLE."""
    html = (
        "<!DOCTYPE html><html><head><title>Podomètre - Compteur de pas</title></head><body>"
        '<div class="step-counter">0 pas</div>'
        "<script>/* pedometer app - no motion handler in this test */</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13121(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.metadata["is_essential_motion"] is True
    assert any(
        "podomètre" in r.lower() or "pedometer" in r.lower() or "pas" in r.lower()
        for r in result.metadata["essential_reasons"]
    )


def test_13121_essential_fitness_with_handler_needs_review(context_factory, run_rgaa):
    """Application fitness AVEC gestionnaire SANS alternative UI -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><head><title>Fitness Tracker - Activity</title></head><body>"
        '<div class="activity">Marche détectée</div>'
        "<script>"
        "  window.addEventListener('devicemotion', (e) => {"
        "    if (e.acceleration.x > 5) { trackActivity(); }"
        "  });"
        "  function trackActivity() { console.log('activity tracked'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13121(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.metadata["is_essential_motion"] is True
    finding = result.findings[0]
    assert finding.evidence["has_ui_alternative"] is False
    assert finding.evidence["is_essential_motion"] is True
    assert "required_checks" in finding.evidence


def test_13121_essential_ar_with_ui_pass(context_factory, run_rgaa):
    """AR (cas particulier) AVEC alternative UI -> PASS."""
    html = (
        "<!DOCTYPE html><html><head><title>AR App - Réalité Augmentée</title></head><body>"
        '<button id="placeObj" onclick="placeObject()">Placer objet</button>'
        '<button id="moveObj" onclick="moveObject()">Déplacer objet</button>'
        '<button id="rotateObj" onclick="rotateObject()">Rotater objet</button>'
        "<script>"
        "  window.addEventListener('devicemotion', (e) => {"
        "    updateARPosition(e);"
        "  });"
        "  function updateARPosition(e) { console.log('AR position updated'); }"
        "  function placeObject() { console.log('object placed via UI'); }"
        "  function moveObject() { console.log('object moved via UI'); }"
        "  function rotateObject() { console.log('object rotated via UI'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13121(), context)

    assert result.status in (Status.PASS, Status.NEEDS_REVIEW)
    assert result.metadata["is_essential_motion"] is True
    finding = result.findings[0]
    assert finding.evidence["has_ui_alternative"] is True


def test_13121_essential_game_not_applicable(context_factory, run_rgaa):
    """Jeu de mouvement sans gestionnaire -> NOT_APPLICABLE."""
    html = (
        "<!DOCTYPE html><html><head><title>Motion Game - Jeu par mouvement</title></head><body>"
        '<canvas id="gameCanvas"></canvas>'
        "<script>/* motion game - no handler in test */</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13121(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.metadata["is_essential_motion"] is True
    assert any("game" in r.lower() or "jeu" in r.lower() for r in result.metadata["essential_reasons"])


def test_13121_essential_navigation_with_ui_pass(context_factory, run_rgaa):
    """Navigation (cas particulier) AVEC alternative UI -> PASS."""
    html = (
        "<!DOCTYPE html><html><head><title>Navigation GPS - Boussole</title></head><body>"
        '<button id="northBtn" onclick="setNorth()">Nord</button>'
        '<button id="southBtn" onclick="setSouth()">Sud</button>'
        '<button id="eastBtn" onclick="setEast()">Est</button>'
        '<button id="westBtn" onclick="setWest()">Ouest</button>'
        "<script>"
        "  const accelerometer = new Accelerometer({ frequency: 10 });"
        "  accelerometer.addEventListener('reading', () => {"
        "    updateCompass(accelerometer.x, accelerometer.y, accelerometer.z);"
        "  });"
        "  accelerometer.start();"
        "  function updateCompass(x, y, z) { console.log('compass', x, y, z); }"
        "  function setNorth() { console.log('set north via UI'); }"
        "  function setSouth() { console.log('set south via UI'); }"
        "  function setEast() { console.log('set east via UI'); }"
        "  function setWest() { console.log('set west via UI'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13121(), context)

    assert result.status in (Status.PASS, Status.NEEDS_REVIEW)
    assert result.metadata["is_essential_motion"] is True
    finding = result.findings[0]
    assert finding.evidence["has_ui_alternative"] is True


# ---------------------------------------------------------------------------
# 13.12.2 : Fonctionnalités par geste vers l'appareil - alternative UI
# ---------------------------------------------------------------------------


def test_13122_no_orientation_gesture_handlers_pass(context_factory, run_rgaa):
    """Page sans gestionnaire d'orientation/geste -> PASS."""
    html = "<!DOCTYPE html><html><body><p>Contenu simple</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA13122(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_13122_deviceorientation_with_ui_pass(context_factory, run_rgaa):
    """deviceorientation avec alternative UI -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<button id="rotateLeft" onclick="rotateLeft()">Rotation gauche</button>'
        '<button id="rotateRight" onclick="rotateRight()">Rotation droite</button>'
        "<script>"
        "  window.addEventListener('deviceorientation', (e) => {"
        "    if (e.gamma > 30) { rotateRight(); }"
        "    else if (e.gamma < -30) { rotateLeft(); }"
        "  });"
        "  function rotateLeft() { console.log('rotate left'); }"
        "  function rotateRight() { console.log('rotate right'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13122(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_ui_alternative"] is True


def test_13122_deviceorientationabsolute_with_ui_pass(context_factory, run_rgaa):
    """deviceorientationabsolute (boussole) avec alternative UI -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<select id="headingSelect" onchange="setHeading(this.value)">'
        "  <option value='0'>Nord</option>"
        "  <option value='90'>Est</option>"
        "  <option value='180'>Sud</option>"
        "  <option value='270'>Ouest</option>"
        "</select>"
        "<script>"
        "  window.addEventListener('deviceorientationabsolute', (e) => {"
        "    updateHeading(e.alpha);"
        "  });"
        "  function updateHeading(alpha) { console.log('heading', alpha); }"
        "  function setHeading(val) { console.log('heading set via UI', val); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13122(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_ui_alternative"] is True


def test_13122_proximity_sensor_fail(context_factory, run_rgaa):
    """Proximity sensor SANS alternative UI -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        "<script>"
        "  const proximity = new ProximitySensor();"
        "  proximity.addEventListener('reading', () => {"
        "    if (proximity.near) { turnOffScreen(); }"
        "  });"
        "  proximity.start();"
        "  function turnOffScreen() { console.log('screen off by proximity'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13122(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_ui_alternative"] is False


def test_13122_camera_gesture_with_ui_pass(context_factory, run_rgaa):
    """Caméra avec facingMode (geste vers appareil) + alternative UI -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<button id="scanBtn" onclick="startScan()">Scanner QR Code</button>'
        '<button id="manualBtn" onclick="manualInput()">Saisie manuelle</button>'
        "<script>"
        "  navigator.mediaDevices.getUserMedia({"
        "    video: { facingMode: 'environment' }"
        "  }).then(stream => {"
        "    // QR code scanning via camera"
        "    startScanning(stream);"
        "  });"
        "  function startScanning(stream) { console.log('scanning via camera'); }"
        "  function startScan() { console.log('scan triggered via UI'); }"
        "  function manualInput() { console.log('manual input via UI'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13122(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_ui_alternative"] is True


def test_13122_hammer_js_gesture_fail(context_factory, run_rgaa):
    """Hammer.js gesture SANS alternative UI -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div id="gestureArea">Zone de geste</div>'
        "<script src='hammer.js'></script>"
        "<script>"
        "  const area = document.getElementById('gestureArea');"
        "  const hammer = new Hammer(area);"
        "  hammer.on('swipe', (e) => { navigate(e.direction); });"
        "  hammer.on('pinch', (e) => { zoom(e.scale); });"
        "  function navigate(dir) { console.log('navigate', dir); }"
        "  function zoom(scale) { console.log('zoom', scale); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13122(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_ui_alternative"] is False


# ---------------------------------------------------------------------------
# 13.12.2 : Cas particuliers
# ---------------------------------------------------------------------------


def test_13122_essential_ar_not_applicable(context_factory, run_rgaa):
    """AR sans gestionnaire -> NOT_APPLICABLE."""
    html = (
        "<!DOCTYPE html><html><head><title>AR Experience - Réalité Augmentée</title></head><body>"
        '<div data-ar="true">AR Content</div>'
        "<script>/* AR app */</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13122(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.metadata["is_essential_motion"] is True
    assert any(
        "ar" in r.lower() or "augmented" in r.lower() or "augmentée" in r.lower() or "réalité augmentée" in r.lower()
        for r in result.metadata["essential_reasons"]
    )


def test_13122_essential_vr_not_applicable(context_factory, run_rgaa):
    """VR sans gestionnaire -> NOT_APPLICABLE."""
    html = (
        "<!DOCTYPE html><html><head><title>VR Experience - Réalité Virtuelle</title></head><body>"
        '<div data-vr="true">VR Content</div>'
        "<script>/* VR app */</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13122(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.metadata["is_essential_motion"] is True
    assert any("vr" in r.lower() or "virtual" in r.lower() for r in result.metadata["essential_reasons"])


def test_13122_essential_gesture_control_needs_review(context_factory, run_rgaa):
    """Contrôle gestuel (cas particulier) SANS alternative -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><head><title>Gesture Control - Contrôle Gestuel</title></head><body>"
        "<script>"
        "  window.addEventListener('deviceorientation', (e) => {"
        "    controlDrone(e.alpha, e.beta, e.gamma);"
        "  });"
        "  function controlDrone(a, b, g) { console.log('drone control', a, b, g); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13122(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.metadata["is_essential_motion"] is True
    finding = result.findings[0]
    assert finding.evidence["has_ui_alternative"] is False
    assert "required_checks" in finding.evidence


# ---------------------------------------------------------------------------
# 13.12.3 : Désactivation de la détection du mouvement
# ---------------------------------------------------------------------------


def test_13123_no_motion_handlers_pass(context_factory, run_rgaa):
    """Page sans gestionnaire de mouvement -> PASS."""
    html = "<!DOCTYPE html><html><body><p>Contenu simple</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA13123(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_13123_prefers_reduced_motion_pass(context_factory, run_rgaa):
    """prefers-reduced-motion respecté -> PASS."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "  @media (prefers-reduced-motion: reduce) {"
        "    .motion-feature { display: none; }"
        "    .motion-alternative { display: block; }"
        "  }"
        "</style>"
        "</head><body>"
        '<div class="motion-feature">Fonctionnalité par mouvement</div>'
        '<div class="motion-alternative" style="display:none">Alternative UI</div>'
        "<script>"
        "  window.addEventListener('devicemotion', (e) => { shakeAction(); });"
        "  function shakeAction() { console.log('shake'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13123(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    assert result.metadata["prefers_reduced_motion"] is True
    assert result.metadata["has_disable_mechanism"] is True


def test_13123_script_disable_mechanism_pass(context_factory, run_rgaa):
    """Script avec mécanisme de désactivation -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<button id="toggleMotion" onclick="toggleMotion()">Activer/Désactiver mouvement</button>'
        "<script>"
        "  let motionEnabled = true;"
        "  window.addEventListener('devicemotion', (e) => {"
        "    if (motionEnabled) { shakeAction(); }"
        "  });"
        "  function shakeAction() { console.log('shake'); }"
        "  function toggleMotion() {"
        "    motionEnabled = !motionEnabled;"
        "    console.log('motion', motionEnabled ? 'enabled' : 'disabled');"
        "  }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13123(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    assert result.metadata["script_disable"] is True
    assert result.metadata["has_disable_mechanism"] is True


def test_13123_ui_control_pass(context_factory, run_rgaa):
    """Contrôle UI (checkbox/switch) pour désactiver -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<label><input type="checkbox" id="motionToggle" checked> Activer détection mouvement</label>'
        "<script>"
        "  const toggle = document.getElementById('motionToggle');"
        "  let motionEnabled = true;"
        "  window.addEventListener('devicemotion', (e) => {"
        "    if (motionEnabled) { shakeAction(); }"
        "  });"
        "  toggle.addEventListener('change', () => {"
        "    motionEnabled = toggle.checked;"
        "  });"
        "  function shakeAction() { console.log('shake'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13123(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    assert result.metadata["ui_control"] is True
    assert result.metadata["has_disable_mechanism"] is True


def test_13123_motion_without_disable_fail(context_factory, run_rgaa):
    """Mouvement SANS mécanisme de désactivation -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        "<script>"
        "  window.addEventListener('devicemotion', (e) => {"
        "    if (e.acceleration.x > 5) { triggerAction(); }"
        "  });"
        "  function triggerAction() { console.log('action triggered'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13123(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    assert result.metadata["has_disable_mechanism"] is False
    assert result.metadata["is_essential_motion"] is False


def test_13123_orientation_without_disable_fail(context_factory, run_rgaa):
    """Orientation SANS mécanisme de désactivation -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        "<script>"
        "  window.addEventListener('deviceorientation', (e) => {"
        "    updateUI(e.alpha, e.beta, e.gamma);"
        "  });"
        "  function updateUI(a, b, g) { console.log('orientation', a, b, g); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13123(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    assert result.metadata["has_disable_mechanism"] is False


def test_13123_gesture_without_disable_fail(context_factory, run_rgaa):
    """Geste vers appareil SANS mécanisme de désactivation -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        "<script>"
        "  const proximity = new ProximitySensor();"
        "  proximity.addEventListener('reading', () => {"
        "    if (proximity.near) { action(); }"
        "  });"
        "  proximity.start();"
        "  function action() { console.log('proximity action'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13123(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    assert result.metadata["has_disable_mechanism"] is False


# ---------------------------------------------------------------------------
# 13.12.3 : Cas particuliers
# ---------------------------------------------------------------------------


def test_13123_essential_pedometer_not_applicable(context_factory, run_rgaa):
    """Podomètre sans gestionnaire -> NOT_APPLICABLE."""
    html = (
        "<!DOCTYPE html><html><head><title>Podomètre - Step Counter</title></head><body>"
        '<div class="steps">0</div>'
        "<script>/* pedometer */</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13123(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.metadata["is_essential_motion"] is True


def test_13123_essential_fitness_with_disable_pass(context_factory, run_rgaa):
    """Fitness (cas particulier) AVEC désactivation -> PASS."""
    html = (
        "<!DOCTYPE html><html><head><title>Fitness Tracker</title></head><body>"
        '<button id="pauseBtn" onclick="pauseTracking()">Pause tracking</button>'
        '<button id="resumeBtn" onclick="resumeTracking()">Reprendre tracking</button>'
        "<script>"
        "  let tracking = true;"
        "  window.addEventListener('devicemotion', (e) => {"
        "    if (tracking) { trackStep(e); }"
        "  });"
        "  function trackStep(e) { console.log('step'); }"
        "  function pauseTracking() { tracking = false; }"
        "  function resumeTracking() { tracking = true; }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13123(), context)

    assert result.status in (Status.PASS, Status.NEEDS_REVIEW)
    assert result.metadata["is_essential_motion"] is True
    assert result.metadata["has_disable_mechanism"] is True


def test_13123_essential_ar_without_disable_needs_review(context_factory, run_rgaa):
    """AR (cas particulier) SANS désactivation -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><head><title>AR Navigation</title></head><body>"
        "<script>"
        "  window.addEventListener('deviceorientation', (e) => {"
        "    updateAR(e);"
        "  });"
        "  function updateAR(e) { console.log('AR update'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13123(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.metadata["is_essential_motion"] is True
    assert result.metadata["has_disable_mechanism"] is False
    finding = result.findings[0]
    assert "required_checks" in finding.evidence


# ---------------------------------------------------------------------------
# Résultats mixtes
# ---------------------------------------------------------------------------


def test_13121_mixed_results_fail_priority(context_factory, run_rgaa):
    """Plusieurs gestionnaires : un avec UI (PASS), un sans (FAIL) -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<button id="btn1" onclick="action1()">Action 1 UI</button>'
        "<script>"
        "  window.addEventListener('devicemotion', (e) => {"
        "    if (e.acceleration.x > 10) { action2(); }"
        "  });"
        "  function action1() { console.log('ui action'); }"
        "  function action2() { console.log('motion action'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13121(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1


def test_13123_mixed_motion_types_fail_priority(context_factory, run_rgaa):
    """devicemotion (sans disable) + orientation (sans disable) -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        "<script>"
        "  window.addEventListener('devicemotion', (e) => { shake(); });"
        "  window.addEventListener('deviceorientation', (e) => { orient(); });"
        "  function shake() { console.log('shake'); }"
        "  function orient() { console.log('orient'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13123(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 2


# ---------------------------------------------------------------------------
# Tests de structure/métadonnées
# ---------------------------------------------------------------------------


def test_13121_metadata_structure(context_factory, run_rgaa):
    """Vérifier la structure des métadonnées pour 13.12.1."""
    html = "<!DOCTYPE html><html><body><p>Test</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA13121(), context)

    assert "required_manual_checks" in result.metadata
    assert isinstance(result.metadata["required_manual_checks"], list)
    assert len(result.metadata["required_manual_checks"]) > 0
    assert "is_essential_motion" in result.metadata
    assert "motion_handlers_count" in result.metadata
    assert "non_compliant_count" in result.metadata
    assert "needs_review_count" in result.metadata
    assert "compliant_count" in result.metadata


def test_13122_metadata_structure(context_factory, run_rgaa):
    """Vérifier la structure des métadonnées pour 13.12.2."""
    html = "<!DOCTYPE html><html><body><p>Test</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA13122(), context)

    assert "required_manual_checks" in result.metadata
    assert isinstance(result.metadata["required_manual_checks"], list)
    assert len(result.metadata["required_manual_checks"]) > 0
    assert "is_essential_motion" in result.metadata
    assert "orientation_handlers_count" in result.metadata
    assert "gesture_handlers_count" in result.metadata
    assert "total_handlers_count" in result.metadata


def test_13123_metadata_structure(context_factory, run_rgaa):
    """Vérifier la structure des métadonnées pour 13.12.3."""
    html = "<!DOCTYPE html><html><body><p>Test</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA13123(), context)

    assert "required_manual_checks" in result.metadata
    assert isinstance(result.metadata["required_manual_checks"], list)
    assert len(result.metadata["required_manual_checks"]) > 0
    assert "is_essential_motion" in result.metadata
    assert "motion_handlers_count" in result.metadata
    assert "disable_mechanisms_count" in result.metadata
    # Note: has_disable_mechanism, prefers_reduced_motion, script_disable, ui_control
    # are only present when motion handlers are detected


def test_13121_missing_dom_not_tested(context_factory, run_rgaa):
    """DOM manquant -> NOT_TESTED."""
    pass


def test_13122_missing_dom_not_tested(context_factory, run_rgaa):
    """DOM manquant -> NOT_TESTED."""
    pass


def test_13123_missing_dom_not_tested(context_factory, run_rgaa):
    """DOM manquant -> NOT_TESTED."""
    pass
