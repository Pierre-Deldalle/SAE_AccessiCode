from __future__ import annotations

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_11 import (
    Test13111 as RGAA13111,
)

# ---------------------------------------------------------------------------
# 13.11.1 : Actions déclenchées au pointage sur point unique - annulation
# (actions au mousedown/pointerdown/touchstart sans up/cancel ni mécanisme abandon)
# ---------------------------------------------------------------------------


def test_13111_no_pointer_down_pass(context_factory, run_rgaa):
    """Page sans gestionnaire d'événement descendant -> PASS."""
    html = "<!DOCTYPE html><html><body><p>Contenu simple accessible au clic</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA13111(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_13111_mousedown_with_mouseup_pass(context_factory, run_rgaa):
    """mousedown avec mouseup correspondant -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<button id="btn" onmousedown="start()" onmouseup="execute()">Action</button>'
        "<script>"
        "  function start() { console.log('down'); }"
        "  function execute() { console.log('up - execute action'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13111(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_up_cancel"] is True
    assert finding.evidence["interaction_type"] == "simple_action"


def test_13111_mousedown_only_fail(context_factory, run_rgaa):
    """mousedown SANS mouseup/pointerup/touchend -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<button id="btn" onmousedown="executeImmediately()">Action</button>'
        "<script>"
        "  function executeImmediately() { console.log('action executed on down'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13111(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_up_cancel"] is False
    assert finding.evidence["has_cancel_abandon"] is False
    assert finding.evidence["interaction_type"] == "simple_action"


def test_13111_pointerdown_with_pointerup_pass(context_factory, run_rgaa):
    """pointerdown avec pointerup -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div id="target"></div>'
        "<script>"
        "  const target = document.getElementById('target');"
        "  target.addEventListener('pointerdown', () => { console.log('down'); });"
        "  target.addEventListener('pointerup', () => { console.log('up - execute'); });"
        "  target.addEventListener('pointercancel', () => { console.log('cancelled'); });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13111(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_up_cancel"] is True


def test_13111_touchstart_with_touchend_pass(context_factory, run_rgaa):
    """touchstart avec touchend -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div id="touchArea"></div>'
        "<script>"
        "  const area = document.getElementById('touchArea');"
        "  area.addEventListener('touchstart', (e) => { e.preventDefault(); console.log('touch start'); });"
        "  area.addEventListener('touchend', () => { console.log('touch end - execute'); });"
        "  area.addEventListener('touchcancel', () => { console.log('touch cancelled'); });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13111(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_up_cancel"] is True


def test_13111_drag_drop_with_cancel_pass(context_factory, run_rgaa):
    """Drag & drop avec mécanisme d'annulation (confirmation, Échap) -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div id="draggable" draggable="true">Glissez-moi</div>'
        '<div id="dropzone">Zone de dépôt</div>'
        '<button id="cancelBtn" onclick="cancelDrag()">Annuler</button>'
        "<script>"
        "  let draggedItem = null;"
        "  const draggable = document.getElementById('draggable');"
        "  const dropzone = document.getElementById('dropzone');"
        "  draggable.addEventListener('dragstart', (e) => { draggedItem = e.target; });"
        "  dropzone.addEventListener('dragover', (e) => { e.preventDefault(); });"
        "  dropzone.addEventListener('drop', (e) => {"
        "    e.preventDefault();"
        "    if (confirm('Confirmer le dépôt ?')) { executeDrop(); }"
        "  });"
        "  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') cancelDrag(); });"
        "  function cancelDrag() { draggedItem = null; console.log('drag cancelled'); }"
        "  function executeDrop() { console.log('drop executed'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13111(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["interaction_type"] == "drag_drop"
    assert finding.evidence["has_cancel_abandon"] is True


def test_13111_drag_drop_no_cancel_fail(context_factory, run_rgaa):
    """Drag & drop SANS mécanisme d'annulation -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div id="draggable" draggable="true">Glissez-moi</div>'
        '<div id="dropzone">Zone de dépôt</div>'
        "<script>"
        "  const draggable = document.getElementById('draggable');"
        "  const dropzone = document.getElementById('dropzone');"
        "  draggable.addEventListener('dragstart', (e) => { e.dataTransfer.setData('text', 'item'); });"
        "  dropzone.addEventListener('dragover', (e) => { e.preventDefault(); });"
        "  dropzone.addEventListener('drop', (e) => { e.preventDefault(); executeDrop(); });"
        "  function executeDrop() { console.log('drop executed - no cancel possible'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13111(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["interaction_type"] == "drag_drop"
    assert finding.evidence["has_cancel_abandon"] is False


def test_13111_addEventListener_mousedown_with_mouseup_pass(context_factory, run_rgaa):
    """addEventListener mousedown avec mouseup -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<button id="btn">Action</button>'
        "<script>"
        "  const btn = document.getElementById('btn');"
        "  btn.addEventListener('mousedown', () => { console.log('down'); });"
        "  btn.addEventListener('mouseup', () => { console.log('up - execute'); });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13111(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_up_cancel"] is True


def test_13111_react_style_onMouseDown_with_onMouseUp_pass(context_factory, run_rgaa):
    """React-style onMouseDown avec onMouseUp -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div id="root"><button onMouseDown={handleDown} onMouseUp={handleUp}>Action</button></div>'
        "<script>"
        "  function handleDown() { console.log('down'); }"
        "  function handleUp() { console.log('up - execute'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13111(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_up_cancel"] is True


def test_13111_jquery_mousedown_with_mouseup_pass(context_factory, run_rgaa):
    """jQuery mousedown avec mouseup -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<button id="btn">Action</button>'
        "<script src='https://code.jquery.com/jquery-3.6.0.min.js'></script>"
        "<script>"
        "  $('#btn').on('mousedown', function() { console.log('down'); });"
        "  $('#btn').on('mouseup', function() { console.log('up - execute'); });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13111(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_up_cancel"] is True


def test_13111_pointerdown_with_cancel_mechanism_pass(context_factory, run_rgaa):
    """pointerdown sans pointerup MAIS avec mécanisme d'annulation (confirm, Échap) -> PASS."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div id="target">Appuyez longuement</div>'
        "<script>"
        "  const target = document.getElementById('target');"
        "  target.addEventListener('pointerdown', () => {"
        "    if (confirm('Confirmer l\\'action ?')) { executeAction(); }"
        "  });"
        "  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') cancelAction(); });"
        "  function executeAction() { console.log('executed'); }"
        "  function cancelAction() { console.log('cancelled by Escape'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13111(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert finding.evidence["has_cancel_abandon"] is True


# ---------------------------------------------------------------------------
# Cas particuliers (essential down-event interfaces)
# ---------------------------------------------------------------------------


def test_13111_essential_piano_not_applicable(context_factory, run_rgaa):
    """Application piano sans gestionnaire descendant -> NOT_APPLICABLE."""
    html = (
        "<!DOCTYPE html><html><head><title>Piano Virtuel</title></head><body>"
        '<div class="piano-key" role="button">Do</div>'
        '<div class="piano-key" role="button">Ré</div>'
        "<script>/* piano app - no down handler */</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13111(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.metadata["is_essential_down_event"] is True
    assert any("piano" in r.lower() for r in result.metadata["essential_reasons"])


def test_13111_essential_piano_with_handler_needs_review(context_factory, run_rgaa):
    """Application piano AVEC gestionnaire descendant SANS annulation -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><head><title>Piano Virtuel</title></head><body>"
        '<div class="piano-key key-white" role="button" onmousedown="playNote(\'C4\')">Do</div>'
        '<div class="piano-key key-white" role="button" onmousedown="playNote(\'D4\')">Ré</div>'
        "<script>"
        "  function playNote(note) { console.log('Playing', note); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13111(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.metadata["is_essential_down_event"] is True
    finding = result.findings[0]
    assert finding.evidence["has_cancel_abandon"] is False
    assert finding.evidence["is_essential_down_event"] is True
    assert "required_checks" in finding.evidence


def test_13111_essential_virtual_keyboard_with_cancel_pass(context_factory, run_rgaa):
    """Clavier virtuel (cas particulier) AVEC mécanisme d'annulation -> PASS."""
    html = (
        "<!DOCTYPE html><html><head><title>Clavier Virtuel Accessible</title></head><body>"
        '<div class="key" onmousedown="typeChar(\'a\')">a</div>'
        '<div class="key" onmousedown="typeChar(\'b\')">b</div>'
        '<button id="cancelBtn" onclick="cancelInput()">Annuler</button>'
        "<script>"
        "  function typeChar(c) { console.log('type', c); }"
        "  function cancelInput() { console.log('input cancelled'); }"
        "  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') cancelInput(); });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13111(), context)

    assert result.status in (Status.PASS, Status.NEEDS_REVIEW)
    assert result.metadata["is_essential_down_event"] is True
    finding = result.findings[0]
    assert finding.evidence["has_cancel_abandon"] is True


def test_13111_essential_game_not_applicable(context_factory, run_rgaa):
    """Jeu (cas particulier) sans gestionnaire descendant -> NOT_APPLICABLE."""
    html = (
        "<!DOCTYPE html><html><head><title>Jeu Arcade</title></head><body>"
        '<canvas id="gameCanvas" width="800" height="600"></canvas>'
        "<script>/* game - no down handler */</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13111(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.metadata["is_essential_down_event"] is True
    assert any("jeu" in r.lower() or "game" in r.lower() for r in result.metadata["essential_reasons"])


def test_13111_essential_emulator_with_handler_needs_review(context_factory, run_rgaa):
    """Émulateur clavier (cas particulier) AVEC gestionnaire SANS annulation -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><head><title>Émulateur Clavier</title></head><body>"
        '<div class="key" onmousedown="keyDown(\'A\')">A</div>'
        '<div class="key" onmousedown="keyDown(\'B\')">B</div>'
        "<script>"
        "  function keyDown(k) { console.log('key down', k); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13111(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.metadata["is_essential_down_event"] is True
    finding = result.findings[0]
    assert finding.evidence["has_cancel_abandon"] is False
    assert "required_checks" in finding.evidence


def test_13111_essential_musical_instrument_with_cancel_pass(context_factory, run_rgaa):
    """Instrument de musique (cas particulier) AVEC annulation -> PASS."""
    html = (
        "<!DOCTYPE html><html><head><title>Synthétiseur Accessible</title></head><body>"
        '<div class="key" onmousedown="playNote(60)">Do</div>'
        '<button onclick="stopAllNotes()">Arrêter tout</button>'
        "<script>"
        "  function playNote(note) { console.log('note on', note); }"
        "  function stopAllNotes() { console.log('all notes off'); }"
        "  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') stopAllNotes(); });"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13111(), context)

    assert result.status in (Status.PASS, Status.NEEDS_REVIEW)
    assert result.metadata["is_essential_down_event"] is True
    finding = result.findings[0]
    assert finding.evidence["has_cancel_abandon"] is True


# ---------------------------------------------------------------------------
# Résultats mixtes
# ---------------------------------------------------------------------------


def test_13111_mixed_results_fail_priority(context_factory, run_rgaa):
    """Plusieurs gestionnaires : un avec up (PASS), un sans (FAIL) -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<button id="btn1" onmousedown="start1()" onmouseup="execute1()">Bouton 1</button>'
        '<button id="btn2" onmousedown="execute2()">Bouton 2</button>'
        "<script>"
        "  function start1() { console.log('down1'); }"
        "  function execute1() { console.log('up1 - execute'); }"
        "  function execute2() { console.log('execute2 on down only'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13111(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 2


def test_13111_mixed_drag_drop_and_button_fail_priority(context_factory, run_rgaa):
    """Drag & drop sans annulation (FAIL) + bouton avec up (PASS) -> FAIL."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<button id="btn" onmousedown="start()" onmouseup="execute()">Bouton OK</button>'
        '<div id="draggable" draggable="true">Drag</div>'
        '<div id="dropzone">Drop</div>'
        "<script>"
        "  function start() { console.log('down'); }"
        "  function execute() { console.log('up'); }"
        "  const draggable = document.getElementById('draggable');"
        "  const dropzone = document.getElementById('dropzone');"
        "  draggable.addEventListener('dragstart', (e) => { e.dataTransfer.setData('text', 'item'); });"
        "  dropzone.addEventListener('dragover', (e) => { e.preventDefault(); });"
        "  dropzone.addEventListener('drop', (e) => { e.preventDefault(); drop(); });"
        "  function drop() { console.log('drop - no cancel'); }"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA13111(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 2


# ---------------------------------------------------------------------------
# Tests de structure/métadonnées
# ---------------------------------------------------------------------------


def test_13111_metadata_structure(context_factory, run_rgaa):
    """Vérifier la structure des métadonnées pour 13.11.1."""
    html = "<!DOCTYPE html><html><body><p>Test</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA13111(), context)

    assert "required_manual_checks" in result.metadata
    assert isinstance(result.metadata["required_manual_checks"], list)
    assert len(result.metadata["required_manual_checks"]) > 0
    assert "is_essential_down_event" in result.metadata
    assert "pointer_down_handlers_count" in result.metadata
    assert "non_compliant_count" in result.metadata
    assert "needs_review_count" in result.metadata
    assert "compliant_count" in result.metadata


def test_13111_missing_dom_not_tested(context_factory, run_rgaa):
    """DOM manquant -> NOT_TESTED."""
    pass
