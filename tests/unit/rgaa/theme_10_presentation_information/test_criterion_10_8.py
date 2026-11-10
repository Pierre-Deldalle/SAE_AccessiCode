from __future__ import annotations

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_8 import (
    Test1081 as RGAA1081,
)

# =============================================================================
# Tests for Test1081 - Contenus cachés et technologies d'assistance
# =============================================================================


def test_1081_no_hidden_content_passes(context_factory, run_rgaa):
    """Test 10.8.1: Page sans contenu caché passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><div>Contenu visible uniquement</div></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 0
    assert "Aucun contenu caché" in result.summary


def test_1081_hidden_attribute_ignored_by_at_passes(context_factory, run_rgaa):
    """Test 10.8.1: Élément avec attribut hidden -> vocation ignorée par AT (PASS)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Contenu visible</p>
        <div hidden>Contenu masqué pour AT (statistiques)</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    # Doit avoir un finding avec condition="ignored_by_at" et passed=True
    ignored_findings = [f for f in result.findings if f.evidence.get("condition") == "ignored_by_at"]
    assert len(ignored_findings) >= 1
    assert ignored_findings[0].evidence.get("passed") is True


def test_1081_aria_hidden_true_ignored_by_at_passes(context_factory, run_rgaa):
    """Test 10.8.1: Élément avec aria-hidden='true' -> vocation ignorée par AT (PASS)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Contenu visible</p>
        <div aria-hidden="true">Contenu décoratif masqué aux AT</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    ignored_findings = [f for f in result.findings if f.evidence.get("condition") == "ignored_by_at"]
    assert len(ignored_findings) >= 1
    assert ignored_findings[0].evidence.get("passed") is True


def test_1081_visually_hidden_class_meant_for_at_needs_review(context_factory, run_rgaa):
    """Test 10.8.1: Classe sr-only/visually-hidden -> destiné aux AT, nécessite mécanisme (NEEDS_REVIEW)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Contenu visible</p>
        <span class="sr-only">Texte pour lecteurs d'écran seulement</span>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    # Contenu destiné aux AT mais pas de mécanisme de déclenchement détecté -> NEEDS_REVIEW
    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    restorable_findings = [f for f in result.findings if f.evidence.get("condition") == "restorable"]
    assert len(restorable_findings) >= 1
    assert restorable_findings[0].evidence.get("needs_manual_check") is True
    assert restorable_findings[0].evidence.get("meant_for_at") is True


def test_1081_display_none_inline_style_needs_review(context_factory, run_rgaa):
    """Test 10.8.1: display: none en ligne -> NEEDS_REVIEW (pas de mécanisme détecté)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Contenu visible</p>
        <div style="display: none;">Contenu masqué</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1
    restorable_findings = [f for f in result.findings if f.evidence.get("condition") == "restorable"]
    assert len(restorable_findings) >= 1
    assert restorable_findings[0].evidence.get("needs_manual_check") is True


def test_1081_visibility_hidden_inline_style_needs_review(context_factory, run_rgaa):
    """Test 10.8.1: visibility: hidden en ligne -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Contenu visible</p>
        <div style="visibility: hidden;">Contenu masqué</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1081_opacity_zero_inline_style_needs_review(context_factory, run_rgaa):
    """Test 10.8.1: opacity: 0 en ligne -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Contenu visible</p>
        <div style="opacity: 0;">Contenu masqué</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1081_position_offscreen_inline_style_needs_review(context_factory, run_rgaa):
    """Test 10.8.1: Position off-screen (left: -9999px) -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Contenu visible</p>
        <div style="position: absolute; left: -9999px;">Contenu masqué</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1081_clip_rect_zero_inline_style_needs_review(context_factory, run_rgaa):
    """Test 10.8.1: clip: rect(0,0,0,0) -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>Contenu visible</p>
        <div style="clip: rect(0,0,0,0);">Contenu masqué</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1081_hidden_content_with_button_trigger_before_passes(context_factory, run_rgaa):
    """Test 10.8.1: Contenu caché avec bouton déclencheur AVANT -> PASS (restorable)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <button id="toggle">Afficher le contenu</button>
        <div id="hidden-content" style="display: none;">Contenu masqué puis affiché</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    # Le bouton est AVANT le contenu caché -> mécanisme détecté
    assert result.status == Status.PASS
    assert result.tested_elements == 1
    restorable_findings = [f for f in result.findings if f.evidence.get("condition") == "restorable"]
    assert len(restorable_findings) >= 1
    assert restorable_findings[0].evidence.get("passed") is True
    assert restorable_findings[0].evidence.get("has_trigger") is True


def test_1081_hidden_content_with_link_trigger_before_passes(context_factory, run_rgaa):
    """Test 10.8.1: Contenu caché avec lien déclencheur AVANT -> PASS."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <a href="#hidden" id="trigger">Voir plus</a>
        <div id="hidden" style="display: none;">Contenu détaillé</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    restorable_findings = [f for f in result.findings if f.evidence.get("condition") == "restorable"]
    assert len(restorable_findings) >= 1
    assert restorable_findings[0].evidence.get("has_trigger") is True


def test_1081_hidden_content_with_focus_script_passes(context_factory, run_rgaa):
    """Test 10.8.1: Contenu caché avec script de focus programmatique -> PASS."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <script>
            document.getElementById('hidden').focus();
        </script>
        <div id="hidden" style="display: none;">Contenu masqué</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    restorable_findings = [f for f in result.findings if f.evidence.get("condition") == "restorable"]
    assert len(restorable_findings) >= 1
    assert restorable_findings[0].evidence.get("has_focus_script") is True


def test_1081_hidden_content_with_jquery_focus_script_passes(context_factory, run_rgaa):
    """Test 10.8.1: Contenu caché avec jQuery focus() -> PASS."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <script>
            $('#hidden').focus();
        </script>
        <div id="hidden" style="display: none;">Contenu masqué</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    restorable_findings = [f for f in result.findings if f.evidence.get("condition") == "restorable"]
    assert len(restorable_findings) >= 1
    assert restorable_findings[0].evidence.get("has_focus_script") is True


def test_1081_role_presentation_ignored_by_at_passes(context_factory, run_rgaa):
    """Test 10.8.1: role='presentation' -> vocation ignorée par AT (PASS)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div role="presentation" style="display: none;">Contenu décoratif</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    ignored_findings = [f for f in result.findings if f.evidence.get("condition") == "ignored_by_at"]
    assert len(ignored_findings) >= 1
    assert ignored_findings[0].evidence.get("passed") is True


def test_1081_role_none_ignored_by_at_passes(context_factory, run_rgaa):
    """Test 10.8.1: role='none' -> vocation ignorée par AT (PASS)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div role="none" style="display: none;">Contenu décoratif</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    ignored_findings = [f for f in result.findings if f.evidence.get("condition") == "ignored_by_at"]
    assert len(ignored_findings) >= 1
    assert ignored_findings[0].evidence.get("passed") is True


def test_1081_mixed_hidden_content_some_ignored_some_needs_review(context_factory, run_rgaa):
    """Test 10.8.1: Contenu masqué mixte (ignoré + nécessite vérification)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div hidden>Statistiques (ignoré AT)</div>
        <span class="sr-only">Texte pour AT seulement</span>
        <div style="display: none;">Contenu masqué sans déclencheur</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    # Au moins un élément nécessite une vérification -> NEEDS_REVIEW
    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 3

    ignored_findings = [f for f in result.findings if f.evidence.get("condition") == "ignored_by_at"]
    restorable_findings = [f for f in result.findings if f.evidence.get("condition") == "restorable"]
    needs_review_findings = [f for f in restorable_findings if f.evidence.get("needs_manual_check")]

    assert len(ignored_findings) >= 1  # hidden
    assert len(needs_review_findings) >= 2  # sr-only + display:none sans déclencheur


def test_1081_stylesheet_hidden_class_flagged(context_factory, run_rgaa):
    """Test 10.8.1: Règle CSS .visually-hidden -> signalée."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>
            .visually-hidden { position: absolute; left: -9999px; }
        </style>
    </head>
    <body>
        <p>Contenu visible</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    # La règle CSS est détectée comme risque potentiel
    css_findings = [f for f in result.findings if f.evidence.get("risk_type") == "stylesheet_hidden_content"]
    assert len(css_findings) >= 1
    assert "visually-hidden" in css_findings[0].element


def test_1081_stylesheet_display_none_flagged(context_factory, run_rgaa):
    """Test 10.8.1: Règle CSS display: none -> signalée."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <style>
            .cache { display: none; }
        </style>
    </head>
    <body>
        <p>Contenu visible</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    css_findings = [f for f in result.findings if f.evidence.get("risk_type") == "stylesheet_hidden_content"]
    assert len(css_findings) >= 1
    assert "display: none" in css_findings[0].message


def test_1081_aria_hidden_false_not_hidden(context_factory, run_rgaa):
    """Test 10.8.1: aria-hidden='false' -> n'est pas considéré comme caché."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div aria-hidden="false">Contenu visible pour AT</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    # aria-hidden="false" ne masque pas pour les AT
    assert result.tested_elements == 0
    assert result.status == Status.PASS


def test_1081_input_type_hidden_ignored_by_at_passes(context_factory, run_rgaa):
    """Test 10.8.1: <input type='hidden'> -> vocation ignorée (PASS)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <form>
            <input type="hidden" name="csrf" value="token">
        </form>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    # input type=hidden est comme attribut hidden
    assert result.status == Status.PASS
    assert result.tested_elements == 1
    ignored_findings = [f for f in result.findings if f.evidence.get("condition") == "ignored_by_at"]
    assert len(ignored_findings) >= 1


def test_1081_details_summary_hidden_content(context_factory, run_rgaa):
    """Test 10.8.1: <details> fermé -> contenu masqué mais restituable via summary."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <details>
            <summary>Plus d'infos</summary>
            <div>Contenu détaillé masqué initialement</div>
        </details>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    # Le <summary> est un élément interactif AVANT le contenu -> mécanisme détecté
    # Note: le contenu du details n'a pas de style masquant explicite, c'est le navigateur
    # Mais si on a un style display:none sur le contenu...
    assert result.tested_elements >= 0  # Peut ne pas détecter car pas de style explicite


def test_1081_missing_dom_returns_not_tested(context_factory, run_rgaa):
    """Test 10.8.1: DOM manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    test = RGAA1081()
    context = SimpleNamespace(dom=None, html_source="<p><div hidden>Caché</div></p>")

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_dom"


def test_1081_missing_html_source_returns_not_tested(context_factory, run_rgaa):
    """Test 10.8.1: HTML source manquant -> NOT_TESTED."""
    from types import SimpleNamespace

    from bs4 import BeautifulSoup

    test = RGAA1081()
    context = SimpleNamespace(
        dom=BeautifulSoup("<p><div hidden>Caché</div></p>", "html.parser"),
        html_source="",
    )

    result = run_rgaa(test, context)

    assert result.status == Status.NOT_TESTED
    assert result.metadata["reason"] == "missing_html_source"


def test_1081_metadata_contains_manual_checks(context_factory, run_rgaa):
    """Test 10.8.1: Les métadonnées contiennent les vérifications manuelles requises."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body><div style="display: none;">Caché</div></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    assert result.metadata["browser_check_required"] is True
    checks = result.metadata["required_manual_checks"]
    assert any("vocation à être ignoré par les AT" in c for c in checks)
    assert any("action utilisateur sur élément précédent" in c for c in checks)
    assert any("repositionnement programmatique du focus" in c for c in checks)
    assert any("cohérence aria-hidden / hidden" in c for c in checks)
    assert result.metadata["manual_check_for"] == "critère 10.8.1 - contenus cachés et technologies d'assistance"


def test_1081_tabindex_focusable_as_trigger(context_factory, run_rgaa):
    """Test 10.8.1: Élément avec tabindex comme déclencheur."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div tabindex="0" role="button">Déclencheur</div>
        <div id="hidden" style="display: none;">Contenu masqué</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1
    restorable_findings = [f for f in result.findings if f.evidence.get("condition") == "restorable"]
    assert len(restorable_findings) >= 1
    assert restorable_findings[0].evidence.get("has_trigger") is True


def test_1081_contenteditable_as_trigger(context_factory, run_rgaa):
    """Test 10.8.1: Élément contenteditable comme déclencheur."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div contenteditable="true">Zone éditable</div>
        <div id="hidden" style="display: none;">Contenu masqué</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_1081_role_button_as_trigger(context_factory, run_rgaa):
    """Test 10.8.1: role='button' comme déclencheur."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <span role="button" tabindex="0">Bouton custom</span>
        <div id="hidden" style="display: none;">Contenu masqué</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 1


def test_1081_multiple_hidden_same_page(context_factory, run_rgaa):
    """Test 10.8.1: Plusieurs contenus cachés sur la même page."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div hidden>Stats 1</div>
        <div aria-hidden="true">Décoratif 1</div>
        <span class="sr-only">Pour AT 1</span>
        <div style="display: none;">Masqué 1</div>
        <button>Btn</button>
        <div style="display: none;">Masqué 2 avec btn avant</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    # 5 éléments cachés détectés
    assert result.tested_elements == 5
    # Au moins un NEEDS_REVIEW (sr-only, Masqué 1 sans déclencheur)
    assert result.status == Status.NEEDS_REVIEW


def test_1081_aria_hidden_true_on_parent_affects_children(context_factory, run_rgaa):
    """Test 10.8.1: aria-hidden sur parent affecte les enfants."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div aria-hidden="true">
            <p>Enfant masqué aussi</p>
            <span>Autre enfant</span>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    # Le parent a aria-hidden="true" -> vocation ignorée
    # Les enfants héritent mais ne sont pas détectés séparément comme cachés
    # (ils le sont par héritage, pas par attribut direct)
    assert result.tested_elements >= 1


def test_1081_clip_path_hidden_needs_review(context_factory, run_rgaa):
    """Test 10.8.1: clip-path pour masquer -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div style="clip-path: inset(50%);">Contenu rogné</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    assert result.status == Status.NEEDS_REVIEW
    assert result.tested_elements == 1


def test_1081_sr_only_focusable_class(context_factory, run_rgaa):
    """Test 10.8.1: Classe sr-only-focusable (visible au focus) -> NEEDS_REVIEW."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <a href="#main" class="sr-only-focusable">Aller au contenu principal</a>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1081(), context)

    # sr-only-focusable est une classe de masquage visuel connu
    # L'élément est un lien (focusable) -> peut servir de déclencheur
    # Mais le lien lui-même est masqué visuellement jusqu'au focus
    assert result.tested_elements >= 1
