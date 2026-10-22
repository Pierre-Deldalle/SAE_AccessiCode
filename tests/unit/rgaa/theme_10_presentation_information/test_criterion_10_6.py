from __future__ import annotations

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_6 import (
    Test1061 as RGAA1061,
)

# =============================================================================
# Tests for Test1061 - Liens signalés uniquement par la couleur
# =============================================================================


def test_1061_no_links_passes(context_factory, run_rgaa):
    """Test 10.6.1: Page sans lien passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><div>Contenu sans lien</div></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 0
    assert "Aucun lien" in result.summary


def test_1061_link_with_underline_passes(context_factory, run_rgaa):
    """Test 10.6.1: Lien avec soulignement (indicateur visuel) n'entre pas dans le périmètre."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Texte avec <a href="#" style="text-decoration: underline;">un lien souligné</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    # Le lien a un indicateur visuel (underline) -> ne devrait pas être signalé
    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert "respectent les 3 conditions" in result.summary or "Aucun lien" in result.summary


def test_1061_link_with_border_passes(context_factory, run_rgaa):
    """Test 10.6.1: Lien avec bordure (indicateur visuel) n'entre pas dans le périmètre."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Texte avec <a href="#" style="border-bottom: 1px solid #000;">un lien bordé</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_1061_link_color_only_no_surrounding_color_needs_review(context_factory, run_rgaa):
    """Test 10.6.1: Lien couleur seule sans couleur environnante -> NEEDS_REVIEW pour contraste."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Texte avec <a href="#" style="color: #0066cc;">un lien bleu</a> sans soulignement.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    # Le lien n'a pas d'indicateur visuel, mais on ne peut pas vérifier le contraste automatiquement
    # (pas de couleur sur le parent) -> NEEDS_REVIEW
    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert len(result.findings) >= 3  # contraste + hover + focus

    # Vérifier les 3 conditions
    contrast_findings = [f for f in result.findings if f.evidence.get("condition") == "contrast"]
    hover_findings = [f for f in result.findings if f.evidence.get("condition") == "hover"]
    focus_findings = [f for f in result.findings if f.evidence.get("condition") == "focus"]

    assert len(contrast_findings) >= 1
    assert len(hover_findings) >= 1
    assert len(focus_findings) >= 1

    # Le contraste devrait être NEEDS_REVIEW (pas de couleur parent)
    assert contrast_findings[0].evidence.get("needs_manual_check") is True
    # Hover et focus devraient être NEEDS_REVIEW (pas de règles CSS correspondantes)
    assert hover_findings[0].evidence.get("needs_manual_check") is True
    assert focus_findings[0].evidence.get("needs_manual_check") is True


def test_1061_link_color_only_with_sufficient_contrast_passes_contrast(context_factory, run_rgaa):
    """Test 10.6.1: Lien couleur seule avec contraste suffisant -> PASS pour contraste."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="color: #000000;">Texte noir avec <a href="#" style="color: #0066cc;">un lien bleu</a> sans soulignement.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    # Le lien a un contraste suffisant (bleu #0066cc sur noir #000000 = ~8.59:1)
    # Mais pas d'indicateurs hover/focus -> FAIL global
    contrast_findings = [f for f in result.findings if f.evidence.get("condition") == "contrast"]
    assert len(contrast_findings) >= 1
    assert contrast_findings[0].evidence.get("passed") is True
    assert contrast_findings[0].evidence.get("contrast_ratio", 0) >= 3.0


def test_1061_link_color_only_insufficient_contrast_fails(context_factory, run_rgaa):
    """Test 10.6.1: Lien couleur seule avec contraste insuffisant -> FAIL."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="color: #333333;">Texte gris foncé avec <a href="#" style="color: #666666;">un lien gris</a> sans soulignement.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    # Contraste insuffisant (gris #666666 sur gris #333333 = ~2.3:1 < 3:1)
    assert result.status == Status.FAIL
    contrast_findings = [f for f in result.findings if f.evidence.get("condition") == "contrast"]
    assert len(contrast_findings) >= 1
    assert contrast_findings[0].evidence.get("passed") is False
    assert contrast_findings[0].evidence.get("contrast_ratio", 10) < 3.0


def test_1061_link_with_hover_indicator_passes_hover(context_factory, run_rgaa):
    """Test 10.6.1: Lien avec indicateur hover -> PASS pour hover."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <p style="color: #000000;">Texte avec <a href="#" style="color: #0066cc;">un lien</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    hover_findings = [f for f in result.findings if f.evidence.get("condition") == "hover"]
    assert len(hover_findings) >= 1
    assert hover_findings[0].evidence.get("passed") is True


def test_1061_link_with_focus_indicator_passes_focus(context_factory, run_rgaa):
    """Test 10.6.1: Lien avec indicateur focus -> PASS pour focus."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>
            a:focus { outline: 2px solid #000; }
        </style>
    </head>
    <body>
        <p style="color: #000000;">Texte avec <a href="#" style="color: #0066cc;">un lien</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    focus_findings = [f for f in result.findings if f.evidence.get("condition") == "focus"]
    assert len(focus_findings) >= 1
    assert focus_findings[0].evidence.get("passed") is True


def test_1061_link_missing_hover_indicator_needs_review(context_factory, run_rgaa):
    """Test 10.6.1: Lien sans indicateur hover dans le CSS -> NEEDS_REVIEW pour hover."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="color: #000000;">Texte avec <a href="#" style="color: #0066cc;">un lien</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    hover_findings = [f for f in result.findings if f.evidence.get("condition") == "hover"]
    assert len(hover_findings) >= 1
    # Sans règle :hover correspondante, on ne peut pas être certain -> NEEDS_REVIEW
    assert hover_findings[0].evidence.get("needs_manual_check") is True


def test_1061_link_missing_focus_indicator_needs_review(context_factory, run_rgaa):
    """Test 10.6.1: Lien sans indicateur focus dans le CSS -> NEEDS_REVIEW pour focus."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="color: #000000;">Texte avec <a href="#" style="color: #0066cc;">un lien</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    focus_findings = [f for f in result.findings if f.evidence.get("condition") == "focus"]
    assert len(focus_findings) >= 1
    # Sans règle :focus correspondante, on ne peut pas être certain -> NEEDS_REVIEW
    assert focus_findings[0].evidence.get("needs_manual_check") is True


def test_1061_link_with_all_conditions_passes(context_factory, run_rgaa):
    """Test 10.6.1: Lien respectant les 3 conditions -> PASS global."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>
            a:hover { text-decoration: underline; }
            a:focus { outline: 2px solid #000; }
        </style>
    </head>
    <body>
        <p style="color: #000000;">Texte avec <a href="#" style="color: #0066cc;">un lien conforme</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    assert "respectent les 3 conditions" in result.summary

    # Vérifier que les 3 conditions sont passées
    for condition in ["contrast", "hover", "focus"]:
        cond_findings = [f for f in result.findings if f.evidence.get("condition") == condition]
        assert len(cond_findings) >= 1
        assert cond_findings[0].evidence.get("passed") is True


def test_1061_multiple_links_color_only_mixed_results(context_factory, run_rgaa):
    """Test 10.6.1: Plusieurs liens couleur seule avec résultats mixtes."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <p style="color: #333333;">
            <a href="#" style="color: #ffffff;">Lien 1 OK contraste</a>
            et
            <a href="#" style="color: #666666;">Lien 2 contraste insuffisant</a>
        </p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    # Un lien a contraste OK, l'autre FAIL -> global FAIL (priorité FAIL)
    assert result.status == Status.FAIL
    assert result.tested_elements == 2

    # Vérifier qu'on a bien 2 liens analysés
    contrast_findings = [f for f in result.findings if f.evidence.get("condition") == "contrast"]
    passed_contrast = [f for f in contrast_findings if f.evidence.get("passed")]
    failed_contrast = [f for f in contrast_findings if not f.evidence.get("passed")]
    assert len(passed_contrast) >= 1
    assert len(failed_contrast) >= 1


def test_1061_role_link_detected(context_factory, run_rgaa):
    """Test 10.6.1: Élément avec role='link' est détecté comme lien."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="color: #000000;">
            Texte avec <span role="link" tabindex="0" style="color: #0066cc;">un faux lien</span>.
        </p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    assert result.tested_elements == 1
    # Doit être traité comme un lien signalé uniquement par la couleur


def test_1061_a_without_href_not_considered_link(context_factory, run_rgaa):
    """Test 10.6.1: <a> sans href n'est pas considéré comme un lien."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="color: #000000;">
            <a style="color: #0066cc;">Ancre sans href</a>
        </p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    # <a> sans href n'est pas un lien -> 0 lien testé
    assert result.tested_elements == 0
    assert result.status == Status.PASS


def test_1061_stylesheet_link_color_only_flagged(context_factory, run_rgaa):
    """Test 10.6.1: Règle CSS pour lien couleur seule -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>
            a.mon-lien { color: #0066cc; }
        </style>
    </head>
    <body>
        <p style="color: #000000;">
            <a href="#" class="mon-lien">Lien avec classe</a>
        </p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    # La règle CSS est signalée comme risque potentiel
    stylesheet_findings = [f for f in result.findings if f.evidence.get("risk_type") == "stylesheet_link_color_only"]
    assert len(stylesheet_findings) >= 1
    assert "Règle CSS" in stylesheet_findings[0].message


def test_1061_missing_dom_returns_not_tested(context_factory, run_rgaa):
    """Test 10.6.1: DOM manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    test = RGAA1061()
    context = SimpleNamespace(dom=None, html_source="<p><a href='#'>Lien</a></p>")

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_dom"


def test_1061_missing_html_source_returns_not_tested(context_factory, run_rgaa):
    """Test 10.6.1: HTML source manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    from bs4 import BeautifulSoup

    test = RGAA1061()
    context = SimpleNamespace(
        dom=BeautifulSoup("<p><a href='#'>Lien</a></p>", "html.parser"),
        html_source="",
    )

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_html_source"


def test_1061_metadata_contains_manual_checks(context_factory, run_rgaa):
    """Test 10.6.1: Les métadonnées contiennent les vérifications manuelles requises."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><p><a href="#" style="color: #0066cc;">Lien</a></p></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    assert result.metadata["browser_check_required"] is True
    assert "vérifier le contraste lien/texte >= 3:1 pour les liens couleur seule" in result.metadata["required_manual_checks"]
    assert "vérifier l'indicateur visuel au survol (autre que couleur)" in result.metadata["required_manual_checks"]
    assert "vérifier l'indicateur visuel au focus (autre que couleur)" in result.metadata["required_manual_checks"]
    assert result.metadata["manual_check_for"] == "critère 10.6.1 - liens signalés uniquement par la couleur"


def test_1061_link_with_box_shadow_passes(context_factory, run_rgaa):
    """Test 10.6.1: Lien avec box-shadow (indicateur visuel) n'entre pas dans le périmètre."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Texte avec <a href="#" style="box-shadow: 0 2px 0 #000;">un lien avec ombre</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_1061_link_with_background_color_passes(context_factory, run_rgaa):
    """Test 10.6.1: Lien avec background-color (indicateur visuel) n'entre pas dans le périmètre."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Texte avec <a href="#" style="background-color: #ffff00;">un lien surligné</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_1061_link_with_outline_passes(context_factory, run_rgaa):
    """Test 10.6.1: Lien avec outline (indicateur visuel) n'entre pas dans le périmètre."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Texte avec <a href="#" style="outline: 2px solid #000;">un lien avec outline</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


# =============================================================================
# Tests de cas limites et comportements mixtes
# =============================================================================


def test_1061_mixed_pass_and_fail_returns_fail(context_factory, run_rgaa):
    """Test 10.6.1: PASS + FAIL -> FAIL (priorité FAIL)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>
            a:hover { text-decoration: underline; }
            a:focus { outline: 2px solid #000; }
        </style>
    </head>
    <body>
        <p style="color: #333333;">
            <a href="#" style="color: #ffffff;">Lien conforme</a>
            et
            <a href="#" style="color: #666666;">Lien contraste insuffisant</a>
        </p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    assert result.status == Status.FAIL
    # Au moins un échec certain doit être détecté
    fail_findings = [f for f in result.findings if f.evidence.get("condition") == "contrast" and not f.evidence.get("passed", False)]
    assert len(fail_findings) >= 1


def test_1061_link_with_visited_state_not_checked_automatically(context_factory, run_rgaa):
    """Test 10.6.1: L'état :visited ne peut pas être vérifié automatiquement (sécurité navigateur)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>
            a:visited { color: #800080; }  /* Ne peut pas être lu via CSSOM pour des raisons de sécurité */
        </style>
    </head>
    <body>
        <p style="color: #000000;">
            <a href="#" style="color: #0066cc;">Lien</a>
        </p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    # Le test ne doit pas planter et doit continuer à analyser les autres états
    assert result.tested_elements == 1
    # L'état visited ne peut pas être vérifié statiquement (ne pas bloquer le test)


def test_1061_contrast_with_named_colors(context_factory, run_rgaa):
    """Test 10.6.1: Contraste avec couleurs nommées."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="color: black;">Texte noir avec <a href="#" style="color: yellow;">lien jaune</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    contrast_findings = [f for f in result.findings if f.evidence.get("condition") == "contrast"]
    assert len(contrast_findings) >= 1
    # jaune sur noir = contraste élevé
    assert contrast_findings[0].evidence.get("passed") is True
    assert contrast_findings[0].evidence.get("contrast_ratio", 0) >= 3.0


def test_1061_contrast_with_rgb_colors(context_factory, run_rgaa):
    """Test 10.6.1: Contraste avec couleurs RGB."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p style="color: rgb(0, 0, 0);">Texte noir avec <a href="#" style="color: rgb(0, 102, 204);">lien bleu</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1061(), context)

    contrast_findings = [f for f in result.findings if f.evidence.get("condition") == "contrast"]
    assert len(contrast_findings) >= 1
    assert contrast_findings[0].evidence.get("passed") is True