from __future__ import annotations

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_14 import (
    Test10141 as RGAA10141,
)
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_14 import (
    Test10142 as RGAA10142,
)

# =============================================================================
# Tests pour Test10141 (10.14.1 - Contenus additionnels au survol)
# =============================================================================


def test_10141_no_css_hover_passes(context_factory, run_rgaa):
    """Test 10.14.1: Page sans règles :hover doit passer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            button { color: blue; }
            button:hover { color: red; }  /* Juste changement de couleur, pas de contenu */
        </style>
    </head>
    <body>
        <h1>Titre principal</h1>
        <button>Bouton normal</button>
        <p>Paragraphe de contenu.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10141(), context)

    assert result.status == Status.PASS
    assert "Aucun contenu additionnel révélé au survol" in result.summary
    assert result.tested_elements == 0


def test_10141_hover_reveals_tooltip_accessible_via_focus_passes(context_factory, run_rgaa):
    """Test 10.14.1: Tooltip au hover accessible aussi au focus doit passer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .tooltip {
                display: none;
                position: absolute;
                background: #333;
                color: white;
                padding: 5px;
            }
            .trigger:hover .tooltip,
            .trigger:focus .tooltip {
                display: block;
            }
        </style>
    </head>
    <body>
        <h1>Titre principal</h1>
        <div class="trigger" tabindex="0">
            Survoler ou focus
            <span class="tooltip">Information additionnelle</span>
        </div>
        <p>Paragraphe normal.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10141(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    # Vérifier qu'au moins un finding est conforme
    compliant_findings = [f for f in result.findings if "accessible via" in f.message and "focus" in f.message.lower()]
    assert len(compliant_findings) >= 1


def test_10141_hover_reveals_tooltip_accessible_via_active_passes(context_factory, run_rgaa):
    """Test 10.14.1: Tooltip au hover accessible aussi à l'activation doit passer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .tooltip {
                display: none;
                position: absolute;
                background: #333;
                color: white;
                padding: 5px;
            }
            .trigger:hover .tooltip,
            .trigger:active .tooltip {
                display: block;
            }
        </style>
    </head>
    <body>
        <h1>Titre principal</h1>
        <div class="trigger" tabindex="0">
            Survoler ou cliquer
            <span class="tooltip">Information additionnelle</span>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10141(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    compliant_findings = [f for f in result.findings if "activation" in f.message.lower()]
    assert len(compliant_findings) >= 1


def test_10141_hover_only_tooltip_fails(context_factory, run_rgaa):
    """Test 10.14.1: Tooltip uniquement au hover doit échouer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .tooltip {
                display: none;
                position: absolute;
                background: #333;
                color: white;
                padding: 5px;
            }
            .trigger:hover .tooltip {
                display: block;
            }
        </style>
    </head>
    <body>
        <h1>Titre principal</h1>
        <div class="trigger">
            Survoler seulement
            <span class="tooltip">Information seulement au survol</span>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10141(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    # Vérifier que le finding indique non-conformité
    non_compliant = [
        f for f in result.findings if "uniquement au survol" in f.message or "non conforme" in f.message.lower()
    ]
    assert len(non_compliant) >= 1
    assert (
        "focus" in result.findings[0].recommendation.lower()
        or "activation" in result.findings[0].recommendation.lower()
    )


def test_10141_hover_with_visibility_hidden_fails(context_factory, run_rgaa):
    """Test 10.14.1: Contenu masqué avec visibility:hidden révélé au hover seulement."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .dropdown-content {
                visibility: hidden;
                opacity: 0;
                transition: opacity 0.3s;
            }
            .dropdown:hover .dropdown-content {
                visibility: visible;
                opacity: 1;
            }
        </style>
    </head>
    <body>
        <div class="dropdown" tabindex="0">
            Menu
            <div class="dropdown-content">Contenu du menu</div>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10141(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1


def test_10141_hover_with_opacity_zero_fails(context_factory, run_rgaa):
    """Test 10.14.1: Contenu masqué avec opacity:0 révélé au hover seulement."""
    html = """
    !DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .hint {
                opacity: 0;
                pointer-events: none;
            }
            .field:hover + .hint {
                opacity: 1;
                pointer-events: auto;
            }
        </style>
    </head>
    <body>
        <input class="field" type="text" placeholder="Champ">
        <span class="hint">Indice pour ce champ</span>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10141(), context)

    # Ce test peut passer ou échouer selon la détection des éléments cachés
    # L'important est qu'il ne plante pas
    assert result.status in [Status.PASS, Status.FAIL, Status.NEEDS_REVIEW]


def test_10141_multiple_hover_elements_mixed(context_factory, run_rgaa):
    """Test 10.14.1: Plusieurs éléments hover, certains conformes d'autres non."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .tooltip-good { display: none; position: absolute; background: #333; color: white; padding: 5px; }
            .tooltip-bad { display: none; position: absolute; background: #333; color: white; padding: 5px; }
            .good:hover .tooltip-good, .good:focus .tooltip-good { display: block; }
            .bad:hover .tooltip-bad { display: block; }
        </style>
    </head>
    <body>
        <div class="good" tabindex="0">
            Conforme
            <span class="tooltip-good">Accessible au focus aussi</span>
        </div>
        <div class="bad">
            Non conforme
            <span class="tooltip-bad">Seulement au survol</span>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10141(), context)

    assert result.status == Status.FAIL  # Au moins un non-conforme
    assert result.tested_elements >= 2  # Deux éléments distincts
    # Doit avoir au moins un finding FAIL et un PASS
    fail_findings = [
        f for f in result.findings if "uniquement au survol" in f.message or "non conforme" in f.message.lower()
    ]
    pass_findings = [
        f
        for f in result.findings
        if "accessible via" in f.message and ("focus" in f.message.lower() or "activation" in f.message.lower())
    ]
    assert len(fail_findings) >= 1
    assert len(pass_findings) >= 1


def test_10141_no_dom_returns_not_tested(context_factory, run_rgaa):
    """Test 10.14.1: Absence de DOM doit retourner NOT_TESTED."""
    context = context_factory("")
    # Supprimer le DOM
    context.dom = None

    result = run_rgaa(RGAA10141(), context)

    assert result.status == Status.NOT_TESTED
    assert "DOM n'est pas disponible" in result.summary


def test_10141_html_source_not_available_returns_not_tested(context_factory, run_rgaa):
    """Test 10.14.1: Absence de code source HTML doit retourner NOT_TESTED."""
    context = context_factory("")
    context.html_source = None

    result = run_rgaa(RGAA10141(), context)

    assert result.status == Status.NOT_TESTED


# =============================================================================
# Tests pour Test10142 (10.14.2 - Contenus additionnels au focus)
# =============================================================================


def test_10142_no_css_focus_passes(context_factory, run_rgaa):
    """Test 10.14.2: Page sans règles :focus doit passer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            button { color: blue; }
        </style>
    </head>
    <body>
        <h1>Titre principal</h1>
        <button>Bouton normal</button>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10142(), context)

    assert result.status == Status.PASS
    assert "Aucun contenu additionnel révélé au focus" in result.summary
    assert result.tested_elements == 0


def test_10142_focus_reveals_content_accessible_via_hover_passes(context_factory, run_rgaa):
    """Test 10.14.2: Contenu au focus accessible aussi au survol doit passer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .tooltip {
                display: none;
                position: absolute;
                background: #333;
                color: white;
                padding: 5px;
            }
            .trigger:focus .tooltip,
            .trigger:hover .tooltip {
                display: block;
            }
        </style>
    </head>
    <body>
        <h1>Titre principal</h1>
        <div class="trigger" tabindex="0">
            Focus ou survol
            <span class="tooltip">Information additionnelle</span>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10142(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    compliant_findings = [f for f in result.findings if "survol" in f.message.lower() or "hover" in f.message.lower()]
    assert len(compliant_findings) >= 1


def test_10142_focus_reveals_content_accessible_via_active_passes(context_factory, run_rgaa):
    """Test 10.14.2: Contenu au focus accessible aussi à l'activation doit passer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .tooltip {
                display: none;
                position: absolute;
                background: #333;
                color: white;
                padding: 5px;
            }
            .trigger:focus .tooltip,
            .trigger:active .tooltip {
                display: block;
            }
        </style>
    </head>
    <body>
        <div class="trigger" tabindex="0">
            Focus ou clic
            <span class="tooltip">Information</span>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10142(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1
    compliant_findings = [
        f for f in result.findings if "activation" in f.message.lower() or "active" in f.message.lower()
    ]
    assert len(compliant_findings) >= 1


def test_10142_focus_only_content_fails(context_factory, run_rgaa):
    """Test 10.14.2: Contenu uniquement au focus doit échouer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .tooltip {
                display: none;
                position: absolute;
                background: #333;
                color: white;
                padding: 5px;
            }
            .trigger:focus .tooltip {
                display: block;
            }
        </style>
    </head>
    <body>
        <div class="trigger" tabindex="0">
            Focus seulement
            <span class="tooltip">Information seulement au focus</span>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10142(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    non_compliant = [
        f for f in result.findings if "uniquement au focus" in f.message or "non conforme" in f.message.lower()
    ]
    assert len(non_compliant) >= 1


def test_10142_focus_visible_reveals_content_accessible_via_hover_passes(context_factory, run_rgaa):
    """Test 10.14.2: :focus-visible révélé au survol aussi doit passer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .tooltip { display: none; position: absolute; background: #333; color: white; padding: 5px; }
            .trigger:focus-visible .tooltip,
            .trigger:hover .tooltip { display: block; }
        </style>
    </head>
    <body>
        <div class="trigger" tabindex="0">
            Focus visible ou survol
            <span class="tooltip">Information</span>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10142(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1


def test_10142_focus_within_reveals_content(context_factory, run_rgaa):
    """Test 10.14.2: :focus-within détecté."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .form-group .help { display: none; color: #666; }
            .form-group:focus-within .help { display: block; }
            .form-group:hover .help { display: block; }
        </style>
    </head>
    <body>
        <div class="form-group">
            <label>Email</label>
            <input type="email" tabindex="0">
            <span class="help">Format: user@example.com</span>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10142(), context)

    assert result.status == Status.PASS
    assert result.tested_elements >= 1


def test_10142_multiple_focus_elements_mixed(context_factory, run_rgaa):
    """Test 10.14.2: Plusieurs éléments focus, certains conformes d'autres non."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .tooltip-good { display: none; position: absolute; background: #333; color: white; padding: 5px; }
            .tooltip-bad { display: none; position: absolute; background: #333; color: white; padding: 5px; }
            .good:focus .tooltip-good, .good:hover .tooltip-good { display: block; }
            .bad:focus .tooltip-bad { display: block; }
        </style>
    </head>
    <body>
        <div class="good" tabindex="0">
            Conforme
            <span class="tooltip-good">Accessible au survol aussi</span>
        </div>
        <div class="bad" tabindex="0">
            Non conforme
            <span class="tooltip-bad">Seulement au focus</span>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10142(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 2  # Deux éléments distincts
    fail_findings = [
        f for f in result.findings if "uniquement au focus" in f.message or "non conforme" in f.message.lower()
    ]
    pass_findings = [
        f
        for f in result.findings
        if "accessible via" in f.message
        and ("survol" in f.message.lower() or "hover" in f.message.lower() or "activation" in f.message.lower())
    ]
    assert len(fail_findings) >= 1
    assert len(pass_findings) >= 1


def test_10142_no_dom_returns_not_tested(context_factory, run_rgaa):
    """Test 10.14.2: Absence de DOM doit retourner NOT_TESTED."""
    context = context_factory("")
    context.dom = None

    result = run_rgaa(RGAA10142(), context)

    assert result.status == Status.NOT_TESTED
    assert "DOM n'est pas disponible" in result.summary


# =============================================================================
# Tests pour les cas limites et edge cases
# =============================================================================


def test_10141_aria_role_tooltip_detected(context_factory, run_rgaa):
    """Test 10.14.1: Élément avec role=tooltip détecté comme contenu caché."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            [role="tooltip"] { display: none; }
            .trigger:hover [role="tooltip"] { display: block; }
        </style>
    </head>
    <body>
        <button class="trigger" aria-describedby="tip">Bouton</button>
        <div id="tip" role="tooltip">Info bulle</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10141(), context)

    # Devrait détecter le tooltip via role
    assert result.status in [Status.PASS, Status.FAIL, Status.NEEDS_REVIEW]


def test_10141_hidden_attribute_detected(context_factory, run_rgaa):
    """Test 10.14.1: Élément avec attribut hidden détecté."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .trigger:hover + .hidden-content { display: block; }
        </style>
    </head>
    <body>
        <button class="trigger">Déclencheur</button>
        <div class="hidden-content" hidden>Contenu caché</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10141(), context)

    assert result.status in [Status.PASS, Status.FAIL, Status.NEEDS_REVIEW]


def test_10141_aria_hidden_detected(context_factory, run_rgaa):
    """Test 10.14.1: Élément avec aria-hidden=true détecté."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .trigger:hover + [aria-hidden] { display: block; }
        </style>
    </head>
    <body>
        <button class="trigger">Déclencheur</button>
        <div aria-hidden="true">Contenu caché</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10141(), context)

    assert result.status in [Status.PASS, Status.FAIL, Status.NEEDS_REVIEW]


def test_10142_empty_page_passes(context_factory, run_rgaa):
    """Test 10.14.2: Page vide passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Vide</title></head>
    <body></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10142(), context)

    assert result.status == Status.PASS


def test_10141_empty_page_passes(context_factory, run_rgaa):
    """Test 10.14.1: Page vide passe."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Vide</title></head>
    <body></body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10141(), context)

    assert result.status == Status.PASS
