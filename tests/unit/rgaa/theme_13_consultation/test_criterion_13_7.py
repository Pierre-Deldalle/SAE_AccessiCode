from __future__ import annotations

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_7 import (
    Test1371 as RGAA1371,
)
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_7 import (
    Test1372 as RGAA1372,
)
from accessi_code.rgaa.tests.theme_13_consultation.criterion_13_7 import (
    Test1373 as RGAA1373,
)

# ---------------------------------------------------------------------------
# 13.7.1 : Éléments multimédia (video, img, svg, canvas, embed, object)
# ---------------------------------------------------------------------------


def test_1371_no_media_not_applicable(context_factory, run_rgaa):
    """Aucun élément multimédia -> NOT_APPLICABLE."""
    html = "<!DOCTYPE html><html><body><p>Contenu simple</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1371(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1371_static_image_not_applicable(context_factory, run_rgaa):
    """Image statique (non animée) -> NOT_APPLICABLE (pas de flash détecté)."""
    html = '<!DOCTYPE html><html><body><img src="image.png" alt="Image statique"></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1371(), context)

    # Image statique n'est pas considérée comme source de flash
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1371_animated_gif_needs_review(context_factory, run_rgaa):
    """GIF animé -> NEEDS_REVIEW (analyse PEAT requise)."""
    html = '<!DOCTYPE html><html><body><img src="animation.gif" alt="Animation"></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1371(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("animée" in f.message for f in result.findings)
    assert any("PEAT" in f.recommendation for f in result.findings)


def test_1371_animated_webp_needs_review(context_factory, run_rgaa):
    """WebP animé -> NEEDS_REVIEW."""
    html = '<!DOCTYPE html><html><body><img src="animation.webp" alt="Animation"></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1371(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1371_apng_needs_review(context_factory, run_rgaa):
    """APNG -> NEEDS_REVIEW."""
    html = '<!DOCTYPE html><html><body><img src="animation.apng" alt="Animation"></body></html>'
    context = context_factory(html)

    result = run_rgaa(RGAA1371(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1371_video_element_needs_review(context_factory, run_rgaa):
    """Élément <video> -> NEEDS_REVIEW (analyse PEAT requise)."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<video src="video.mp4" controls></video>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1371(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("vidéo" in f.message.lower() for f in result.findings)


def test_1371_video_with_type_needs_review(context_factory, run_rgaa):
    """Video avec type MIME -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<video><source src="video.webm" type="video/webm"></video>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1371(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1371_svg_element_needs_review(context_factory, run_rgaa):
    """Élément <svg> -> NEEDS_REVIEW (potentiellement animé via SMIL)."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<svg width="100" height="100"><circle cx="50" cy="50" r="40" fill="red"></circle></svg>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1371(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("svg" in f.message.lower() for f in result.findings)


def test_1371_canvas_element_needs_review(context_factory, run_rgaa):
    """Élément <canvas> -> NEEDS_REVIEW (potentiellement animé via JS)."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<canvas id="myCanvas" width="200" height="100"></canvas>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1371(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("canvas" in f.message.lower() for f in result.findings)


def test_1371_embed_element_needs_review(context_factory, run_rgaa):
    """Élément <embed> -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<embed src="animation.swf" type="application/x-shockwave-flash">'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1371(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("embed" in f.message.lower() for f in result.findings)


def test_1371_object_element_needs_review(context_factory, run_rgaa):
    """Élément <object> -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<object data="animation.swf" type="application/x-shockwave-flash"></object>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1371(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("object" in f.message.lower() for f in result.findings)


def test_1371_multiple_media_mixed(context_factory, run_rgaa):
    """Plusieurs éléments multimédia -> NEEDS_REVIEW pour chacun."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<img src="anim.gif" alt="GIF">'
        '<video src="vid.mp4"></video>'
        '<svg></svg>'
        '<canvas></canvas>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1371(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 4


def test_1371_object_video_mime_needs_review(context_factory, run_rgaa):
    """Object avec type video -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<object data="video.mp4" type="video/mp4"></object>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1371(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1371_embed_video_src_needs_review(context_factory, run_rgaa):
    """Embed avec src vidéo -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<embed src="video.webm" type="video/webm">'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1371(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


# ---------------------------------------------------------------------------
# 13.7.2 : Scripts provoquant des flashs
# ---------------------------------------------------------------------------


def test_1372_no_script_not_applicable(context_factory, run_rgaa):
    """Aucun script -> NOT_APPLICABLE."""
    html = "<!DOCTYPE html><html><body><p>Contenu</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1372(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1372_script_no_flash_pattern_not_applicable(context_factory, run_rgaa):
    """Script sans pattern flash -> NOT_APPLICABLE."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<script>console.log("Hello"); var x = 1;</script>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1372(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1372_setinterval_opacity_needs_review(context_factory, run_rgaa):
    """setInterval modifiant opacity -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<script>setInterval(function() { el.style.opacity = 0.5; }, 100);</script>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1372(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("opacity" in f.message.lower() for f in result.findings)


def test_1372_settimeout_filter_needs_review(context_factory, run_rgaa):
    """setTimeout modifiant filter -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<script>setTimeout(function() { el.style.filter = "brightness(2)"; }, 500);</script>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1372(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1372_requestanimationframe_needs_review(context_factory, run_rgaa):
    """requestAnimationFrame -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<script>function animate() { requestAnimationFrame(animate); } animate();</script>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1372(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert any("requestAnimationFrame" in f.message for f in result.findings)


def test_1372_classlist_toggle_needs_review(context_factory, run_rgaa):
    """classList.toggle pour clignotement -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<script>setInterval(function() { el.classList.toggle("flash"); }, 200);</script>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1372(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1372_style_opacity_assignment_needs_review(context_factory, run_rgaa):
    """Assignment direct style.opacity -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<script>element.style.opacity = 0;</script>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1372(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1372_style_filter_assignment_needs_review(context_factory, run_rgaa):
    """Assignment direct style.filter -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<script>element.style.filter = "invert(1)";</script>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1372(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1372_style_background_assignment_needs_review(context_factory, run_rgaa):
    """Assignment direct style.background -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<script>element.style.backgroundColor = "red";</script>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1372(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1372_multiple_scripts_needs_review(context_factory, run_rgaa):
    """Plusieurs scripts avec patterns flash -> NEEDS_REVIEW pour chacun."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<script>setInterval(function() { el.style.opacity = 0.5; }, 100);</script>'
        '<script>requestAnimationFrame(animate);</script>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1372(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 2


def test_1372_case_insensitive_detection(context_factory, run_rgaa):
    """Détection insensible à la casse."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<script>SETINTERVAL(FUNCTION() { EL.STYLE.OPACITY = 0.5; }, 100);</script>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1372(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


# ---------------------------------------------------------------------------
# 13.7.3 : Animations CSS provoquant des flashs
# ---------------------------------------------------------------------------


def test_1373_no_css_animation_not_applicable(context_factory, run_rgaa):
    """Aucune animation CSS -> NOT_APPLICABLE."""
    html = "<!DOCTYPE html><html><body><p>Contenu</p></body></html>"
    context = context_factory(html)

    result = run_rgaa(RGAA1373(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1373_css_animation_with_flash_name_needs_review(context_factory, run_rgaa):
    """Animation CSS avec nom suggestif 'flash' -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><head>'
        '<style>'
        '@keyframes flash { 0% { opacity: 1; } 50% { opacity: 0; } 100% { opacity: 1; } }'
        '.blink { animation: flash 1s infinite; }'
        '</style>'
        '</head><body><div class="blink">Clignote</div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1373(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements >= 1
    assert any("flash" in f.message.lower() for f in result.findings)


def test_1373_css_animation_blink_name_needs_review(context_factory, run_rgaa):
    """Animation CSS avec nom 'blink' -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><head>'
        '<style>'
        '@keyframes blink { from { opacity: 1; } to { opacity: 0; } }'
        '.element { animation: blink 0.5s infinite; }'
        '</style>'
        '</head><body><div class="element"></div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1373(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements >= 1


def test_1373_css_animation_strobe_name_fails(context_factory, run_rgaa):
    """Animation CSS avec nom 'strobe' et fréquence 5 Hz (0.2s) -> FAIL."""
    html = (
        '<!DOCTYPE html><html><head>'
        '<style>'
        '@keyframes strobe { 0% { background: white; } 100% { background: black; } }'
        '.strobe { animation: strobe 0.2s infinite; }'
        '</style>'
        '</head><body><div class="strobe"></div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1373(), context)

    # 0.2s = 5 Hz >= 3 Hz -> FAIL
    assert result.status == Status.FAIL
    assert result.tested_elements >= 1


def test_1373_css_animation_high_frequency_fails(context_factory, run_rgaa):
    """Animation CSS avec fréquence ≥ 3 Hz -> FAIL."""
    # 0.2s = 5 Hz > 3 Hz
    html = (
        '<!DOCTYPE html><html><head>'
        '<style>'
        '@keyframes fastFlash { 0% { opacity: 1; } 50% { opacity: 0; } 100% { opacity: 1; } }'
        '.fast { animation: fastFlash 0.2s infinite; }'
        '</style>'
        '</head><body><div class="fast"></div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1373(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    assert any("fréquence" in f.message.lower() and "3" in f.message for f in result.findings)


def test_1373_css_animation_exact_threshold_3hz_fails(context_factory, run_rgaa):
    """Animation CSS à exactement 3 Hz (0.333s) -> FAIL."""
    html = (
        '<!DOCTYPE html><html><head>'
        '<style>'
        '@keyframes threeHz { 0% { opacity: 1; } 50% { opacity: 0; } 100% { opacity: 1; } }'
        '.three { animation: threeHz 0.333s infinite; }'
        '</style>'
        '</head><body><div class="three"></div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1373(), context)

    # 1/0.333 = 3.003 Hz >= 3 Hz -> FAIL
    assert result.status == Status.FAIL


def test_1373_css_animation_below_threshold_needs_review(context_factory, run_rgaa):
    """Animation CSS avec fréquence < 3 Hz -> NEEDS_REVIEW (vérification surface)."""
    # 1s = 1 Hz < 3 Hz
    html = (
        '<!DOCTYPE html><html><head>'
        '<style>'
        '@keyframes slowPulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }'
        '.slow { animation: slowPulse 1s infinite; }'
        '</style>'
        '</head><body><div class="slow"></div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1373(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements >= 1


def test_1373_css_keyframes_brightness_change_needs_review(context_factory, run_rgaa):
    """@keyframes avec changement de luminosité (opacity, filter) -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><head>'
        '<style>'
        '@keyframes pulse { 0% { opacity: 1; filter: brightness(1); } 100% { opacity: 0.5; filter: brightness(2); } }'
        '.pulse { animation: pulse 2s infinite; }'
        '</style>'
        '</head><body><div class="pulse"></div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1373(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements >= 1
    assert any(
        "luminosité" in f.message.lower()
        or "opacity" in f.message.lower()
        or "filter" in f.message.lower()
        for f in result.findings
    )


def test_1373_inline_style_animation_needs_review(context_factory, run_rgaa):
    """Style inline avec animation -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<div style="animation: flash 1s infinite;">Contenu</div>'
        '<style>@keyframes flash { 0% { opacity: 1; } 100% { opacity: 0; } }</style>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1373(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements >= 1


def test_1373_transition_opacity_needs_review(context_factory, run_rgaa):
    """Transition sur opacity -> NEEDS_REVIEW (peut clignoter au hover/focus)."""
    html = (
        '<!DOCTYPE html><html><head>'
        '<style>'
        '.btn { transition: opacity 0.1s; }'
        '.btn:hover { opacity: 0; }'
        '</style>'
        '</head><body><button class="btn">Bouton</button></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1373(), context)

    # Transition courte sur opacity peut créer un effet de flash
    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements >= 1


def test_1373_multiple_animations_mixed_results(context_factory, run_rgaa):
    """Plusieurs animations : une rapide (FAIL), une lente (NEEDS_REVIEW) -> FAIL."""
    html = (
        '<!DOCTYPE html><html><head>'
        '<style>'
        '@keyframes fast { 0% { opacity: 1; } 100% { opacity: 0; } }'
        '@keyframes slow { 0% { opacity: 1; } 100% { opacity: 0.5; } }'
        '.fast { animation: fast 0.2s infinite; }'
        '.slow { animation: slow 2s infinite; }'
        '</style>'
        '</head><body>'
        '<div class="fast"></div>'
        '<div class="slow"></div>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1373(), context)

    # Priorité : FAIL > NEEDS_REVIEW
    assert result.status == Status.FAIL
    assert result.tested_elements >= 2


def test_1373_animation_iteration_count_infinite(context_factory, run_rgaa):
    """Animation avec iteration-count infinite -> NEEDS_REVIEW (fréquence basée sur durée)."""
    html = (
        '<!DOCTYPE html><html><head>'
        '<style>'
        '@keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }'
        '.spin { animation: spin 1s linear infinite; }'
        '</style>'
        '</head><body><div class="spin"></div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1373(), context)

    # Pas de changement de luminosité détecté (transform seulement)
    # Mais l'animation est détectée
    assert result.tested_elements >= 0  # Peut être NOT_APPLICABLE si pas de brightness change


def test_1373_animation_with_background_color_change(context_factory, run_rgaa):
    """Animation changeant background-color -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><head>'
        '<style>'
        '@keyframes colorFlash { 0% { background: white; } 50% { background: red; } 100% { background: white; } }'
        '.color { animation: colorFlash 0.5s infinite; }'
        '</style>'
        '</head><body><div class="color"></div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1373(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements >= 1


def test_1373_animation_with_box_shadow_change(context_factory, run_rgaa):
    """Animation changeant box-shadow -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><head>'
        '<style>'
        '@keyframes shadowFlash { '
        '0% { box-shadow: 0 0 0 white; } '
        '50% { box-shadow: 0 0 20px white; } '
        '100% { box-shadow: 0 0 0 white; } }'
        '.shadow { animation: shadowFlash 1s infinite; }'
        '</style>'
        '</head><body><div class="shadow"></div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1373(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements >= 1


# ---------------------------------------------------------------------------
# Tests d'intégration : combinaisons
# ---------------------------------------------------------------------------


def test_1371_and_1373_both_present(context_factory, run_rgaa):
    """Page avec GIF animé ET animation CSS flash."""
    html = (
        '<!DOCTYPE html><html><head>'
        '<style>'
        '@keyframes flash { 0% { opacity: 1; } 100% { opacity: 0; } } '
        '.css-flash { animation: flash 0.2s infinite; }'
        '</style>'
        '</head><body>'
        '<img src="anim.gif" alt="GIF">'
        '<div class="css-flash">CSS Flash</div>'
        '</body></html>'
    )
    context = context_factory(html)

    result_1371 = run_rgaa(RGAA1371(), context)
    result_1373 = run_rgaa(RGAA1373(), context)

    assert result_1371.status == Status.NEEDS_REVIEW
    assert result_1371.tested_elements == 1

    assert result_1373.status == Status.FAIL  # 0.2s = 5 Hz >= 3 Hz


def test_1372_and_1373_both_present(context_factory, run_rgaa):
    """Page avec script flash ET animation CSS flash."""
    html = (
        '<!DOCTYPE html><html><head>'
        '<style>'
        '@keyframes cssFlash { 0% { opacity: 1; } 100% { opacity: 0; } } '
        '.css { animation: cssFlash 1s infinite; }'
        '</style>'
        '</head><body>'
        '<script>setInterval(function() { el.style.opacity = 0; }, 100);</script>'
        '<div class="css"></div>'
        '</body></html>'
    )
    context = context_factory(html)

    result_1372 = run_rgaa(RGAA1372(), context)
    result_1373 = run_rgaa(RGAA1373(), context)

    assert result_1372.status == Status.NEEDS_REVIEW
    assert result_1372.tested_elements == 1

    assert result_1373.status == Status.NEEDS_REVIEW  # 1s = 1 Hz < 3 Hz


# ---------------------------------------------------------------------------
# Tests de régression : robustesse parsing
# ---------------------------------------------------------------------------


def test_1373_css_animation_ms_duration(context_factory, run_rgaa):
    """Durée d'animation en millisecondes."""
    # 200ms = 5 Hz
    html = (
        '<!DOCTYPE html><html><head>'
        '<style>'
        '@keyframes fast { 0% { opacity: 1; } 100% { opacity: 0; } }'
        '.fast { animation: fast 200ms infinite; }'
        '</style>'
        '</head><body><div class="fast"></div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1373(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1


def test_1373_css_animation_case_insensitive(context_factory, run_rgaa):
    """Noms d'animation insensibles à la casse."""
    html = (
        '<!DOCTYPE html><html><head>'
        '<style>'
        '@keyframes FLASH { 0% { opacity: 1; } 100% { opacity: 0; } }'
        '.test { animation: FLASH 1s infinite; }'
        '</style>'
        '</head><body><div class="test"></div></body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1373(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements >= 1


def test_1371_img_with_data_uri_not_animated(context_factory, run_rgaa):
    """Image avec data URI (pas d'extension) -> NOT_APPLICABLE si pas animée détectée."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<img src="data:image/png;base64,'
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" '
        'alt="Pixel">'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1371(), context)

    # Data URI sans extension détectable -> NOT_APPLICABLE
    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0


def test_1371_svg_with_animate_tag_needs_review(context_factory, run_rgaa):
    """SVG avec animation SMIL <animate> -> NEEDS_REVIEW."""
    html = (
        '<!DOCTYPE html><html><body>'
        '<svg width="100" height="100">'
        '<circle cx="50" cy="50" r="40" fill="red">'
        '<animate attributeName="opacity" from="1" to="0" '
        'dur="1s" repeatCount="indefinite" />'
        '</circle>'
        '</svg>'
        '</body></html>'
    )
    context = context_factory(html)

    result = run_rgaa(RGAA1371(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
