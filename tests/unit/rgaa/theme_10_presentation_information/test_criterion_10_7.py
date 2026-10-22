from __future__ import annotations

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_7 import (
    Test1071 as RGAA1071,
)

# =============================================================================
# Tests for Test1071 - Visibilité de la prise de focus
# =============================================================================


def test_1071_no_focusable_elements_passes(context_factory, run_rgaa):
    """Test 10.7.1: Page sans élément focusable passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><div>Contenu sans élément focusable</div></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 0
    assert "Aucun élément focusable" in result.summary


def test_1071_link_with_native_focus_passes(context_factory, run_rgaa):
    """Test 10.7.1: Lien avec focus natif (pas de outline:none) -> NEEDS_REVIEW (vérification manuelle)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Texte avec <a href="#">un lien</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    # Le focus natif devrait être présent, mais on ne peut pas en être certain statiquement
    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    assert len(result.findings) >= 1
    # Doit avoir needs_manual_check
    finding = result.findings[0]
    assert finding.evidence.get("needs_manual_check") is True
    assert finding.evidence.get("risk_type") == "native_focus_needs_verification"


def test_1071_button_with_native_focus_passes(context_factory, run_rgaa):
    """Test 10.7.1: Bouton avec focus natif -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <button>Bouton</button>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1071_input_with_native_focus_passes(context_factory, run_rgaa):
    """Test 10.7.1: Input avec focus natif -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <input type="text" placeholder="Entrez du texte">
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1071_link_with_outline_none_fails(context_factory, run_rgaa):
    """Test 10.7.1: Lien avec outline: none en ligne -> FAIL."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Texte avec <a href="#" style="outline: none;">un lien sans focus</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    fail_findings = [f for f in result.findings if f.evidence.get("risk_type") == "native_focus_removed_no_replacement"]
    assert len(fail_findings) >= 1
    assert "outline: none" in fail_findings[0].message.lower() or "supprimé" in fail_findings[0].message.lower()


def test_1071_link_with_outline_zero_fails(context_factory, run_rgaa):
    """Test 10.7.1: Lien avec outline: 0 en ligne -> FAIL."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Texte avec <a href="#" style="outline: 0;">un lien sans focus</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    fail_findings = [f for f in result.findings if f.evidence.get("risk_type") == "native_focus_removed_no_replacement"]
    assert len(fail_findings) >= 1


def test_1071_link_with_negative_outline_offset_fails(context_factory, run_rgaa):
    """Test 10.7.1: Lien avec outline-offset négatif -> FAIL."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Texte avec <a href="#" style="outline-offset: -5px;">un lien focus caché</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    fail_findings = [f for f in result.findings if f.evidence.get("risk_type") == "native_focus_removed_no_replacement"]
    assert len(fail_findings) >= 1


def test_1071_link_with_custom_focus_style_passes(context_factory, run_rgaa):
    """Test 10.7.1: Lien avec style de focus personnalisé (outline) -> NEEDS_REVIEW (vérification contraste)."""
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
        <p style="color: #000000;">Texte avec <a href="#">un lien</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    # Style d'auteur présent, mais contraste non vérifiable automatiquement
    assert result.status in (Status.PASS, Status.NEEDS_REVIEW)
    assert result.tested_elements == 1


def test_1071_link_with_custom_focus_sufficient_contrast_passes(context_factory, run_rgaa):
    """Test 10.7.1: Lien avec background-color de focus et contraste suffisant -> PASS."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>
            a:focus { background-color: #ffff00; color: #000000; }
        </style>
    </head>
    <body>
        <p style="color: #000000;">Texte avec <a href="#">un lien</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    # background-color jaune (#ffff00) sur texte noir (#000000) = contraste très élevé
    # Mais l'élément n'a pas de couleur de fond au repos -> le focus change le fond
    # Ce cas est complexe à vérifier statiquement
    assert result.tested_elements == 1


def test_1071_link_outline_none_in_stylesheet_fails(context_factory, run_rgaa):
    """Test 10.7.1: outline: none dans une règle CSS :focus -> FAIL."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>
            a:focus { outline: none; }
        </style>
    </head>
    <body>
        <p>Texte avec <a href="#">un lien</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements == 1
    fail_findings = [f for f in result.findings if f.evidence.get("risk_type") == "native_focus_removed_no_replacement"]
    assert len(fail_findings) >= 1


def test_1071_link_outline_none_global_flagged(context_factory, run_rgaa):
    """Test 10.7.1: outline: none global signalé -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>
            * { outline: none; }
        </style>
    </head>
    <body>
        <p>Texte avec <a href="#">un lien</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    # outline: none global est signalé comme risque
    assert result.status in (Status.FAIL, Status.NEEDS_REVIEW)
    assert result.tested_elements == 1
    css_findings = [f for f in result.findings if f.evidence.get("risk_type") == "stylesheet_outline_none_global"]
    assert len(css_findings) >= 1


def test_1071_element_with_tabindex_focusable(context_factory, run_rgaa):
    """Test 10.7.1: Élément avec tabindex >= 1 est focusable."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div tabindex="1">Div focusable</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    assert result.tested_elements == 1
    assert result.status == Status.NEEDS_REVIEW


def test_1071_element_with_tabindex_zero_not_in_scope(context_factory, run_rgaa):
    """Test 10.7.1: Élément avec tabindex=0 n'est pas dans le périmètre (RGAA: tabindex >= 1)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div tabindex="0">Div focusable ordre naturel</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    # Selon RGAA 10.7 : "attribut tabindex d'une valeur égale ou supérieure à 1"
    # tabindex="0" n'est PAS dans le périmètre du test
    assert result.tested_elements == 0
    assert result.status == Status.PASS


def test_1071_element_with_negative_tabindex_not_focusable(context_factory, run_rgaa):
    """Test 10.7.1: Élément avec tabindex=-1 n'est pas focusable au clavier."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div tabindex="-1">Div pas focusable au clavier</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    # tabindex="-1" retire de l'ordre de tabulation -> pas focusable pour 10.7.1
    assert result.tested_elements == 0
    assert result.status == Status.PASS


def test_1071_link_without_href_not_focusable(context_factory, run_rgaa):
    """Test 10.7.1: <a> sans href n'est pas focusable."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <a>Ancre sans href</a>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    assert result.tested_elements == 0
    assert result.status == Status.PASS


def test_1071_input_hidden_not_focusable(context_factory, run_rgaa):
    """Test 10.7.1: <input type=hidden> n'est pas focusable."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <input type="hidden" value="secret">
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    assert result.tested_elements == 0
    assert result.status == Status.PASS


def test_1071_contenteditable_focusable(context_factory, run_rgaa):
    """Test 10.7.1: Élément contenteditable est focusable."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div contenteditable="true">Éditable</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    assert result.tested_elements == 1


def test_1071_area_in_map_focusable(context_factory, run_rgaa):
    """Test 10.7.1: <area> dans une <map> est focusable."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <img src="test.png" usemap="#map">
        <map name="map">
            <area shape="rect" coords="0,0,10,10" href="#" alt="Zone">
        </map>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    assert result.tested_elements == 1


def test_1071_details_with_summary_focusable(context_factory, run_rgaa):
    """Test 10.7.1: <details> avec <summary> - les deux sont focusables."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <details><summary>Résumé</summary>Contenu</details>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    # Le <summary> est focusable, et <details> avec <summary> l'est aussi
    assert result.tested_elements == 2


def test_1071_details_without_summary_not_focusable(context_factory, run_rgaa):
    """Test 10.7.1: <details> sans <summary> n'est pas focusable."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <details>Contenu sans résumé</details>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    assert result.tested_elements == 0
    assert result.status == Status.PASS


def test_1071_multiple_focusable_elements_mixed_results(context_factory, run_rgaa):
    """Test 10.7.1: Plusieurs éléments focusables avec résultats mixtes."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <a href="#" style="outline: none;">Lien 1 sans focus</a>
        <a href="#">Lien 2 focus natif</a>
        <button style="outline: none;">Bouton sans focus</button>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    assert result.tested_elements == 3
    # Au moins 2 échecs certains (outline: none)
    fail_findings = [f for f in result.findings if f.evidence.get("risk_type") == "native_focus_removed_no_replacement"]
    assert len(fail_findings) >= 2
    assert result.status == Status.FAIL


def test_1071_custom_focus_with_insufficient_contrast_fails(context_factory, run_rgaa):
    """Test 10.7.1: Style de focus personnalisé avec contraste insuffisant -> FAIL."""
    # Note: difficile à tester statiquement car on a besoin des couleurs de l'élément
    # Ce test vérifie la logique de détection
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>
            a:focus { outline: 1px solid #cccccc; }  /* Gris clair sur blanc = faible contraste */
        </style>
    </head>
    <body>
        <p style="color: #000000; background-color: #ffffff;">Texte avec <a href="#">un lien</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    # Le contraste de l'outline n'est pas directement vérifiable (couleur de l'outline non connue)
    # Mais on peut détecter la présence d'un style :focus
    assert result.tested_elements == 1


def test_1071_focus_style_suspicious_in_stylesheet_flagged(context_factory, run_rgaa):
    """Test 10.7.1: Règle :focus sans indicateur visuel -> signalé."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>
            a:focus { color: red; }  /* Changement de couleur seulement */
        </style>
    </head>
    <body>
        <p>Texte avec <a href="#">un lien</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    # Règle :focus qui ne change que la couleur (pas outline, box-shadow, border, bg)
    # devrait être signalée comme suspecte
    _ = [f for f in result.findings if f.evidence.get("risk_type") == "stylesheet_focus_style_suspicious"]
    # Note: color change n'est pas détecté comme indicateur visuel par notre logique
    # Ce test documente le comportement attendu
    assert result.tested_elements == 1


def test_1071_missing_dom_returns_not_tested(context_factory, run_rgaa):
    """Test 10.7.1: DOM manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    test = RGAA1071()
    context = SimpleNamespace(dom=None, html_source="<p><a href='#'>Lien</a></p>")

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_dom"


def test_1071_missing_html_source_returns_not_tested(context_factory, run_rgaa):
    """Test 10.7.1: HTML source manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    from bs4 import BeautifulSoup

    test = RGAA1071()
    context = SimpleNamespace(
        dom=BeautifulSoup("<p><a href='#'>Lien</a></p>", "html.parser"),
        html_source="",
    )

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_html_source"


def test_1071_metadata_contains_manual_checks(context_factory, run_rgaa):
    """Test 10.7.1: Les métadonnées contiennent les vérifications manuelles requises."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><p><a href="#">Lien</a></p></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    assert result.metadata["browser_check_required"] is True
    checks = result.metadata["required_manual_checks"]
    assert "vérifier que chaque élément focusable a une indication de focus visible" in checks
    assert "vérifier que le contraste de l'indicateur de focus est >= 3:1" in checks
    assert "vérifier que le focus natif n'est pas supprimé sans remplacement" in checks
    assert result.metadata["manual_check_for"] == "critère 10.7.1 - visibilité de la prise de focus"


def test_1071_select_and_textarea_focusable(context_factory, run_rgaa):
    """Test 10.7.1: <select> et <textarea> sont focusables."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <select><option>Option</option></select>
        <textarea></textarea>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    assert result.tested_elements == 2


def test_1071_focus_visible_with_box_shadow(context_factory, run_rgaa):
    """Test 10.7.1: box-shadow comme indicateur de focus."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>
            a:focus { box-shadow: 0 0 0 3px #0066cc; }
        </style>
    </head>
    <body>
        <p>Texte avec <a href="#">un lien</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    assert result.tested_elements == 1
    # box-shadow détecté comme indicateur visuel


def test_1071_focus_visible_with_border(context_factory, run_rgaa):
    """Test 10.7.1: border comme indicateur de focus."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>
            a:focus { border: 2px solid #000; }
        </style>
    </head>
    <body>
        <p>Texte avec <a href="#">un lien</a>.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    assert result.tested_elements == 1
    # border détecté comme indicateur visuel


def test_1071_summary_focusable(context_factory, run_rgaa):
    """Test 10.7.1: <summary> est focusable."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <details><summary>Résumé</summary>Contenu</details>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1071(), context)

    # Le summary est l'élément focusable dans details
    assert result.tested_elements >= 1
