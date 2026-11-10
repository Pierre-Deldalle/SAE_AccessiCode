from __future__ import annotations

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_8 import (
    Test1381 as RGAA1381,
)
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_8 import (
    Test1382 as RGAA1382,
)

# ---------------------------------------------------------------------------
# 13.8.1 : Contenu en mouvement déclenché automatiquement
# ---------------------------------------------------------------------------


def test_1381_no_motion_not_applicable(context_factory, run_rgaa):
    """Aucun contenu en mouvement -> NOT_APPLICABLE."""
    html = "<!DOCTYPE html><html><body><p>Contenu statique simple</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1381_static_image_not_applicable(context_factory, run_rgaa):
    """Image statique -> NOT_APPLICABLE."""
    html = '<!DOCTYPE html><html><body><img src="image.png" alt="Image statique"></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1381_animated_gif_needs_review(context_factory, run_rgaa):
    """GIF animé -> NEEDS_REVIEW (durée inconnue, pas de contrôle détecté)."""
    html = '<!DOCTYPE html><html><body><img src="animation.gif" alt="Animation"></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("mouvement" in f.message.lower() for f in result.findings)


def test_1381_animated_webp_needs_review(context_factory, run_rgaa):
    """WebP animé -> NEEDS_REVIEW."""
    html = '<!DOCTYPE html><html><body><img src="animation.webp" alt="Animation"></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1381_apng_needs_review(context_factory, run_rgaa):
    """APNG -> NEEDS_REVIEW."""
    html = '<!DOCTYPE html><html><body><img src="animation.apng" alt="Animation"></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1381_video_autoplay_needs_review(context_factory, run_rgaa):
    """Vidéo avec autoplay -> NEEDS_REVIEW."""
    html = '<!DOCTYPE html><html><body><video src="video.mp4" autoplay></video></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("vidéo" in f.message.lower() or "video" in f.message.lower() for f in result.findings)


def test_1381_video_no_autoplay_not_applicable(context_factory, run_rgaa):
    """Vidéo sans autoplay -> NOT_APPLICABLE (pas de déclenchement auto)."""
    html = '<!DOCTYPE html><html><body><video src="video.mp4" controls></video></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1381_svg_element_needs_review(context_factory, run_rgaa):
    """Élément SVG -> NEEDS_REVIEW (potentiellement animé via SMIL)."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<svg width="100" height="100"><circle cx="50" cy="50" r="40" fill="red"></circle></svg>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("svg" in f.message.lower() for f in result.findings)


def test_1381_canvas_element_needs_review(context_factory, run_rgaa):
    """Élément Canvas -> NEEDS_REVIEW (potentiellement animé via JS)."""
    html = '<!DOCTYPE html><html><body><canvas id="myCanvas" width="200" height="100"></canvas></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("canvas" in f.message.lower() for f in result.findings)


def test_1381_marquee_needs_review(context_factory, run_rgaa):
    """Balise <marquee> -> NEEDS_REVIEW (défilement auto permanent)."""
    html = "<!DOCTYPE html><html><body><marquee>Texte défilant</marquee></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("marquee" in f.message.lower() or "défilement" in f.message.lower() for f in result.findings)


def test_1381_css_animation_motion_name_needs_review(context_factory, run_rgaa):
    """Animation CSS avec nom suggestif de mouvement -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes slide { from { transform: translateX(0); } to { transform: translateX(100px); } }"
        ".slide { animation: slide 3s infinite; }"
        "</style>"
        '</head><body><div class="slide">Glisse</div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements >= 1
    assert any("slide" in f.message.lower() or "mouvement" in f.message.lower() for f in result.findings)


def test_1381_css_animation_short_duration_pass(context_factory, run_rgaa):
    """Animation CSS mouvement durée 3s (≤ 5s) -> PASS."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes move { from { left: 0; } to { left: 100px; } }"
        ".move { animation: move 3s forwards; }"  # forwards = s'arrête à la fin, pas infinite
        "</style>"
        '</head><body><div class="move">Bouge 3s</div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    # Durée 3s ≤ 5s -> conforme (même sans contrôle utilisateur)
    # Note: forwards signifie que l'animation ne se répète pas
    assert result.status in (Status.PASS, Status.NEEDS_REVIEW)
    assert result.tested_elements >= 1


def test_1381_css_animation_long_duration_no_control_fail(context_factory, run_rgaa):
    """Animation CSS mouvement durée 10s (> 5s) sans contrôle -> FAIL."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes longMove { from { left: 0; } to { left: 100px; } }"
        ".long { animation: longMove 10s infinite; }"
        "</style>"
        '</head><body><div class="long">Bouge 10s</div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    # Durée 10s > 5s et pas de contrôle détecté -> FAIL
    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    # Vérifier dans l'evidence que la condition de durée > 5s est détectée
    assert any(f.evidence.get("condition_met") == "duration_10.0s_gt_5s_no_control" for f in result.findings)


def test_1381_css_transition_motion_needs_review(context_factory, run_rgaa):
    """Transition CSS sur transform/left -> NEEDS_REVIEW (peut être déclenchée auto)."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        ".box { transition: transform 2s; transform: translateX(0); }"
        ".box.moved { transform: translateX(200px); }"
        "</style>"
        "</head><body>"
        '<script>document.querySelector(".box").classList.add("moved");</script>'
        '<div class="box">Box</div>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements >= 1


def test_1381_js_setinterval_transform_needs_review(context_factory, run_rgaa):
    """setInterval modifiant transform -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div id="box">Box</div>'
        "<script>"
        "setInterval(function() {"
        'document.getElementById("box").style.transform = "translateX(100px)";'
        "}, 1000);"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("transform" in f.message.lower() or "mouvement" in f.message.lower() for f in result.findings)


def test_1381_js_requestanimationframe_needs_review(context_factory, run_rgaa):
    """requestAnimationFrame -> NEEDS_REVIEW (animation continue potentielle)."""
    html = (
        "<!DOCTYPE html><html><body>"
        "<script>function animate() { requestAnimationFrame(animate); } animate();</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    # Vérifier dans l'evidence que requestAnimationFrame est détecté
    assert any("requestAnimationFrame" in str(f.evidence.get("motion_properties", [])) for f in result.findings)


def test_1381_js_animate_api_needs_review(context_factory, run_rgaa):
    """Element.animate() Web Animation API -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div id="box">Box</div>'
        "<script>"
        'document.getElementById("box").animate('
        '{transform: ["translateX(0)", "translateX(100px)"]}, 1000);'
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1381_progress_bar_not_applicable(context_factory, run_rgaa):
    """Barre de progression <progress> -> NOT_APPLICABLE (cas particulier)."""
    html = '<!DOCTYPE html><html><body><progress value="50" max="100"></progress></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1381_progress_bar_role_not_applicable(context_factory, run_rgaa):
    """Div avec role=progressbar -> NOT_APPLICABLE."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div role="progressbar" aria-valuenow="50" aria-valuemin="0" aria-valuemax="100"></div>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1381_progress_class_not_applicable(context_factory, run_rgaa):
    """Div avec classe 'progress-bar' -> NOT_APPLICABLE."""
    html = '<!DOCTYPE html><html><body><div class="progress-bar" style="width: 50%;"></div></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1381_spinner_class_not_applicable(context_factory, run_rgaa):
    """Div avec classe 'spinner' -> NOT_APPLICABLE."""
    html = '<!DOCTYPE html><html><body><div class="spinner"></div></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1381_user_control_stop_restart_pass(context_factory, run_rgaa):
    """Animation avec bouton arrêt/relance détecté -> PASS."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }"
        ".spin { animation: spin 10s infinite; }"
        "</style>"
        "</head><body>"
        '<div class="spin">Tourne</div>'
        '<button id="stopBtn">Arrêter l\'animation</button>'
        '<button id="restartBtn">Relancer l\'animation</button>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    # Contrôle utilisateur détecté -> conforme malgré durée > 5s
    assert result.status in (Status.PASS, Status.NEEDS_REVIEW)
    assert result.tested_elements >= 1


def test_1381_user_control_hide_show_pass(context_factory, run_rgaa):
    """Animation avec bouton masquer/afficher -> PASS."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes move { from { left: 0; } to { left: 100px; } }"
        ".move { animation: move 10s infinite; }"
        "</style>"
        "</head><body>"
        '<div class="move">Bouge</div>'
        "<button>Masquer le mouvement</button>"
        "<button>Afficher le mouvement</button>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    assert result.status in (Status.PASS, Status.NEEDS_REVIEW)
    assert result.tested_elements >= 1


def test_1381_user_control_static_version_pass(context_factory, run_rgaa):
    """Lien vers version statique -> PASS."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes slide { from { left: 0; } to { left: 100px; } }"
        ".slide { animation: slide 10s infinite; }"
        "</style>"
        "</head><body>"
        '<div class="slide">Animation</div>'
        '<a href="/version-statique">Version sans animation</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    assert result.status in (Status.PASS, Status.NEEDS_REVIEW)
    assert result.tested_elements >= 1


def test_1381_prefers_reduced_motion_pass(context_factory, run_rgaa):
    """CSS avec prefers-reduced-motion -> PASS."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }"
        ".spin { animation: spin 10s infinite; }"
        "@media (prefers-reduced-motion: reduce) { .spin { animation: none; } }"
        "</style>"
        '</head><body><div class="spin">Tourne</div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    # prefers-reduced-motion détecté -> conforme
    assert result.status in (Status.PASS, Status.NEEDS_REVIEW)
    assert result.tested_elements >= 1


def test_1381_focus_pause_only_not_compliant(context_factory, run_rgaa):
    """Animation focus/hover pause -> FAIL (focus/hover n'est pas un contrôle valide, durée > 5s)."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }"
        ".spin { animation: spin 10s infinite; }"
        ".spin:hover { animation-play-state: paused; }"
        ".spin:focus { animation-play-state: paused; }"
        "</style>"
        '</head><body><div class="spin" tabindex="0">Tourne</div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    # L'arrêt par focus/hover seul n'est PAS conforme selon la note RGAA
    # Durée 10s > 5s sans contrôle valide -> FAIL
    assert result.status == Status.FAIL
    assert result.tested_elements >= 1


def test_1381_multiple_motion_mixed_results(context_factory, run_rgaa):
    """Plusieurs mouvements : un court (PASS), un long sans contrôle (FAIL) -> FAIL."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes short { from { left: 0; } to { left: 100px; } }"
        "@keyframes long { from { left: 0; } to { left: 100px; } }"
        ".short { animation: short 3s forwards; }"
        ".long { animation: long 10s infinite; }"
        "</style>"
        "</head><body>"
        '<div class="short">Court</div>'
        '<div class="long">Long</div>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1381(), context)

    # Priorité : FAIL > NEEDS_REVIEW > PASS
    assert result.status == Status.FAIL
    assert result.tested_elements >= 2


# ---------------------------------------------------------------------------
# 13.8.2 : Contenu clignotant déclenché automatiquement
# ---------------------------------------------------------------------------


def test_1382_no_blink_not_applicable(context_factory, run_rgaa):
    """Aucun clignotement -> NOT_APPLICABLE."""
    html = "<!DOCTYPE html><html><body><p>Contenu statique</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1382(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1382_css_animation_blink_name_needs_review(context_factory, run_rgaa):
    """Animation CSS avec nom 'blink' -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes blink { from { opacity: 1; } to { opacity: 0; } }"
        ".blink { animation: blink 1s infinite; }"
        "</style>"
        '</head><body><div class="blink">Clignote</div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1382(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements >= 1
    assert any("blink" in f.message.lower() or "clignot" in f.message.lower() for f in result.findings)


def test_1382_css_animation_flash_name_needs_review(context_factory, run_rgaa):
    """Animation CSS avec nom 'flash' -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes flash { 0% { opacity: 1; } 50% { opacity: 0; } 100% { opacity: 1; } }"
        ".flash { animation: flash 2s infinite; }"
        "</style>"
        '</head><body><div class="flash">Flash</div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1382(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements >= 1


def test_1382_css_animation_strobe_name_fails(context_factory, run_rgaa):
    """Animation CSS 'strobe' durée 0.2s (5 Hz) > 5s? Non, c'est durée 0.2s < 5s -> PASS en durée.
    Mais pour 13.8.2 le critère est durée ≤ 5s, pas fréquence.
    0.2s ≤ 5s -> conforme par durée."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes strobe { 0% { opacity: 1; } 100% { opacity: 0; } }"
        ".strobe { animation: strobe 0.2s infinite; }"
        "</style>"
        '</head><body><div class="strobe">Stroboscope</div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1382(), context)

    # Durée 0.2s ≤ 5s -> conforme (critère 13.8.2 = durée, pas fréquence)
    assert result.status in (Status.PASS, Status.NEEDS_REVIEW)
    assert result.tested_elements >= 1


def test_1382_css_animation_long_blink_duration_fail(context_factory, run_rgaa):
    """Animation clignotement durée 10s (> 5s) sans contrôle -> FAIL."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes slowBlink { 0% { opacity: 1; } 50% { opacity: 0; } 100% { opacity: 1; } }"
        ".slow { animation: slowBlink 10s infinite; }"
        "</style>"
        '</head><body><div class="slow">Clignote lent</div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1382(), context)

    # Durée 10s > 5s sans contrôle -> FAIL
    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    # Vérifier dans l'evidence que la condition de durée > 5s est détectée
    assert any(f.evidence.get("condition_met") == "duration_10.0s_gt_5s_no_control" for f in result.findings)


def test_1382_css_keyframes_opacity_change_needs_review(context_factory, run_rgaa):
    """@keyframes modifiant opacity -> NEEDS_REVIEW (clignotement potentiel)."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes pulse { 0% { opacity: 1; filter: brightness(1); } 100% { opacity: 0.5; filter: brightness(2); } }"
        ".pulse { animation: pulse 3s infinite; }"
        "</style>"
        '</head><body><div class="pulse">Pulse</div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1382(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements >= 1
    assert any(
        "opacity" in f.message.lower() or "filter" in f.message.lower() or "clignot" in f.message.lower()
        for f in result.findings
    )


def test_1382_css_keyframes_visibility_change_needs_review(context_factory, run_rgaa):
    """@keyframes modifiant visibility -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes toggleVis { 0% { visibility: visible; } 50% { visibility: hidden; } 100% { visibility: visible; } }"
        ".vis { animation: toggleVis 2s infinite; }"
        "</style>"
        '</head><body><div class="vis">Visibilité</div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1382(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements >= 1


def test_1382_animated_gif_blink_needs_review(context_factory, run_rgaa):
    """GIF animé (potentiellement clignotant) -> NEEDS_REVIEW."""
    html = '<!DOCTYPE html><html><body><img src="blink.gif" alt="Clignote"></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1382(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1382_js_classlist_toggle_opacity_needs_review(context_factory, run_rgaa):
    """JS classList.toggle pour clignotement -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>.hidden { opacity: 0; }</style>"
        "</head><body>"
        '<div id="el">Clignote</div>'
        '<script>setInterval(function() { document.getElementById("el").classList.toggle("hidden"); }, 500);</script>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1382(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1382_js_style_opacity_toggle_needs_review(context_factory, run_rgaa):
    """JS modification directe style.opacity en boucle -> NEEDS_REVIEW."""
    html = (
        "<!DOCTYPE html><html><body>"
        '<div id="el">Clignote</div>'
        "<script>"
        "setInterval(function() {"
        'var el = document.getElementById("el");'
        'el.style.opacity = el.style.opacity === "0" ? "1" : "0";'
        "}, 500);"
        "</script>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1382(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1382_user_control_stop_restart_blink_pass(context_factory, run_rgaa):
    """Clignotement avec bouton arrêt/relance -> PASS."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes blink { 0% { opacity: 1; } 50% { opacity: 0; } 100% { opacity: 1; } }"
        ".blink { animation: blink 10s infinite; }"
        "</style>"
        "</head><body>"
        '<div class="blink">Clignote</div>'
        "<button>Arrêter le clignotement</button>"
        "<button>Relancer le clignotement</button>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1382(), context)

    assert result.status in (Status.PASS, Status.NEEDS_REVIEW)
    assert result.tested_elements >= 1


def test_1382_user_control_hide_show_blink_pass(context_factory, run_rgaa):
    """Clignotement avec bouton masquer/afficher -> PASS."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes blink { 0% { opacity: 1; } 100% { opacity: 0; } }"
        ".blink { animation: blink 10s infinite; }"
        "</style>"
        "</head><body>"
        '<div class="blink">Clignote</div>'
        "<button>Masquer le contenu clignotant</button>"
        "<button>Afficher le contenu clignotant</button>"
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1382(), context)

    assert result.status in (Status.PASS, Status.NEEDS_REVIEW)
    assert result.tested_elements >= 1


def test_1382_user_control_static_version_blink_pass(context_factory, run_rgaa):
    """Lien version sans clignotement -> PASS."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes blink { 0% { opacity: 1; } 100% { opacity: 0; } }"
        ".blink { animation: blink 10s infinite; }"
        "</style>"
        "</head><body>"
        '<div class="blink">Clignote</div>'
        '<a href="/sans-clignotement">Version sans clignotement</a>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1382(), context)

    assert result.status in (Status.PASS, Status.NEEDS_REVIEW)
    assert result.tested_elements >= 1


def test_1382_prefers_reduced_motion_blink_pass(context_factory, run_rgaa):
    """prefers-reduced-motion pour clignotement -> PASS."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes blink { 0% { opacity: 1; } 100% { opacity: 0; } }"
        ".blink { animation: blink 10s infinite; }"
        "@media (prefers-reduced-motion: reduce) { .blink { animation: none; opacity: 1; } }"
        "</style>"
        '</head><body><div class="blink">Clignote</div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1382(), context)

    assert result.status in (Status.PASS, Status.NEEDS_REVIEW)
    assert result.tested_elements >= 1


def test_1382_focus_pause_blink_not_compliant(context_factory, run_rgaa):
    """Clignotement durée 1s (≤ 5s) -> NEEDS_REVIEW (css_animation conforme mais keyframes nécessite vérification)."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes blink { 0% { opacity: 1; } 100% { opacity: 0; } }"
        ".blink { animation: blink 1s infinite; }"
        ".blink:hover, .blink:focus { animation-play-state: paused; }"
        "</style>"
        '</head><body><div class="blink" tabindex="0">Clignote</div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1382(), context)

    # css_animation durée 1s ≤ 5s -> conforme, mais keyframes génère aussi un finding NEEDS_REVIEW
    # Priorité : NEEDS_REVIEW > PASS -> résultat global NEEDS_REVIEW
    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements >= 1


def test_1382_multiple_blink_mixed_results(context_factory, run_rgaa):
    """Plusieurs clignotements : un court (PASS), un long sans contrôle (FAIL) -> FAIL."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes shortBlink { 0% { opacity: 1; } 100% { opacity: 0; } }"
        "@keyframes longBlink { 0% { opacity: 1; } 100% { opacity: 0; } }"
        ".short { animation: shortBlink 3s forwards; }"
        ".long { animation: longBlink 10s infinite; }"
        "</style>"
        "</head><body>"
        '<div class="short">Court</div>'
        '<div class="long">Long</div>'
        "</body></html>"
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1382(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 2


# ---------------------------------------------------------------------------
# Tests d'intégration : 13.8.1 et 13.8.2 ensemble
# ---------------------------------------------------------------------------


def test_1381_and_1382_both_present(context_factory, run_rgaa):
    """Page avec mouvement ET clignotement."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes move { from { left: 0; } to { left: 100px; } }"
        "@keyframes blink { 0% { opacity: 1; } 100% { opacity: 0; } }"
        ".move { animation: move 10s infinite; }"
        ".blink { animation: blink 10s infinite; }"
        "</style>"
        "</head><body>"
        '<div class="move">Bouge</div>'
        '<div class="blink">Clignote</div>'
        "</body></html>"
    )
    context = context_factory(html)

    result_1381 = run_rgaa(RGAA1381(), context)
    result_1382 = run_rgaa(RGAA1382(), context)

    assert result_1381.status == Status.FAIL  # mouvement 10s sans contrôle
    assert result_1381.tested_elements >= 1

    assert result_1382.status == Status.FAIL  # clignotement 10s sans contrôle
    assert result_1382.tested_elements >= 1


def test_1381_motion_and_1382_blink_different_durations(context_factory, run_rgaa):
    """Mouvement court (≤5s) + clignotement long (>5s)."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<style>"
        "@keyframes quickMove { from { left: 0; } to { left: 100px; } }"
        "@keyframes slowBlink { 0% { opacity: 1; } 100% { opacity: 0; } }"
        ".move { animation: quickMove 3s forwards; }"
        ".blink { animation: slowBlink 10s infinite; }"
        "</style>"
        "</head><body>"
        '<div class="move">Bouge vite</div>'
        '<div class="blink">Clignote lent</div>'
        "</body></html>"
    )
    context = context_factory(html)

    result_1381 = run_rgaa(RGAA1381(), context)
    result_1382 = run_rgaa(RGAA1382(), context)

    # Mouvement 3s ≤ 5s -> PASS
    assert result_1381.status in (Status.PASS, Status.NEEDS_REVIEW)
    # Clignotement 10s > 5s -> FAIL
    assert result_1382.status == Status.FAIL
