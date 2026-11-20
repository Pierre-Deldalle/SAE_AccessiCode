from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_13 import (
    Test10131 as RGAA10131,
)
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_13 import (
    Test10132 as RGAA10132,
)
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_13 import (
    Test10133 as RGAA10133,
)

# Test 10.13.1 tests


def test_10131_no_hover_focus_content_passes(context_factory, run_rgaa):
    """Test 10.13.1: Page sans contenu additionnel au survol/focus doit passer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .normal-content { color: blue; }
        </style>
    </head>
    <body>
        <h1>Titre principal</h1>
        <p>Paragraphe de contenu normal.</p>
        <button>Bouton simple</button>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10131(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 0
    assert "Aucun contenu additionnel au survol/focus détecté" in result.summary


def test_10131_tooltip_with_title_attribute_passes(context_factory, run_rgaa):
    """Test 10.13.1: title natif (agent utilisateur) est exempté."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <h1>Titre principal</h1>
        <button title="Info-bulle native">Bouton avec title</button>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10131(), context)

    # Le title natif est exempté, donc pas de contenu additionnel détecté
    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10131_custom_tooltip_no_dismiss_fails(context_factory, run_rgaa):
    """Test 10.13.1: Infobulle personnalisée sans mécanisme de masquage doit échouer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .tooltip { display: none; position: absolute; background: black; color: white; }
            .trigger:hover .tooltip { display: block; }
        </style>
    </head>
    <body>
        <h1>Titre principal</h1>
        <div class="trigger">
            Survoler moi
            <div class="tooltip">Contenu de l'infobulle</div>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10131(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1
    assert result.tested_elements >= 1
    # Vérifier que le finding mentionne l'absence de mécanisme de masquage
    finding = result.findings[0]
    assert "masquage" in finding.message.lower() or "dismiss" in finding.message.lower()
    assert "Echap" in finding.recommendation or "Escape" in finding.recommendation


def test_10131_custom_tooltip_with_escape_passes(context_factory, run_rgaa):
    """Test 10.13.1: Infobulle personnalisée avec gestion Echap doit passer (ou NEEDS_REVIEW)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .tooltip { display: none; position: absolute; background: black; color: white; }
            .trigger:hover .tooltip { display: block; }
        </style>
        <script>
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    // Fermer les tooltips
                }
            });
        </script>
    </head>
    <body>
        <h1>Titre principal</h1>
        <div class="trigger">
            Survoler moi
            <div class="tooltip">Contenu de l'infobulle</div>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10131(), context)

    # Avec script de gestion Echap, devrait être PASS ou NEEDS_REVIEW
    assert result.status in [Status.PASS, Status.NEEDS_REVIEW]
    assert result.tested_elements >= 1


def test_10131_dialog_role_exempted(context_factory, run_rgaa):
    """Test 10.13.1: Dialogue modal (role=dialog) est exempté."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <h1>Titre principal</h1>
        <button aria-haspopup="dialog" aria-controls="mydialog">Ouvrir dialogue</button>
        <div role="dialog" id="mydialog" aria-modal="true">
            <h2>Dialogue</h2>
            <button>Fermer</button>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10131(), context)

    # Le dialogue est exempté (activation utilisateur)
    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10131_details_summary_exempted(context_factory, run_rgaa):
    """Test 10.13.1: details/summary natif est exempté (activation)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <h1>Titre principal</h1>
        <details>
            <summary>Cliquer pour ouvrir</summary>
            <p>Contenu détaillé</p>
        </details>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10131(), context)

    # details/summary est exempté
    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10131_form_validation_native_exempted(context_factory, run_rgaa):
    """Test 10.13.1: Validation native de formulaire est exemptée."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <h1>Titre principal</h1>
        <form>
            <input type="text" required title="Champ requis">
            <input type="submit">
        </form>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10131(), context)

    # Validation native exemptée
    assert result.status == Status.PASS
    assert result.tested_elements == 0


def test_10131_multiple_tooltips_with_global_escape(context_factory, run_rgaa):
    """Test 10.13.1: Plusieurs infobulles avec gestionnaire Echap global."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .tooltip { display: none; position: absolute; background: black; color: white; }
            .trigger:hover .tooltip { display: block; }
            .trigger2:hover .tooltip2 { display: block; }
        </style>
        <script>
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    // Gestionnaire global Echap pour toutes les infobulles
                }
            });
        </script>
    </head>
    <body>
        <h1>Titre principal</h1>
        <div class="trigger">
            Survoler moi 1
            <div class="tooltip">Infobulle 1</div>
        </div>
        <div class="trigger2">
            Survoler moi 2
            <div class="tooltip2">Infobulle 2</div>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10131(), context)

    # Un gestionnaire Echap global est détecté et s'applique à toutes les infobulles
    # Le test passe car un mécanisme de masquage est détecté
    assert result.status in [Status.PASS, Status.NEEDS_REVIEW]
    assert result.tested_elements >= 1


# Test 10.13.2 tests


def test_10132_no_hover_content_passes(context_factory, run_rgaa):
    """Test 10.13.2: Page sans contenu additionnel au survol doit passer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <h1>Titre principal</h1>
        <p>Paragraphe normal.</p>
        <button>Bouton</button>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10132(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 0
    assert "Aucun contenu additionnel au survol détecté" in result.summary


def test_10132_tooltip_child_structure_passes(context_factory, run_rgaa):
    """Test 10.13.2: Infobulle enfant du déclencheur (structure correcte) doit passer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .tooltip { display: none; position: absolute; background: black; color: white; }
            .trigger:hover .tooltip { display: block; }
        </style>
    </head>
    <body>
        <h1>Titre principal</h1>
        <div class="trigger">
            Survoler moi
            <div class="tooltip">Infobulle enfant</div>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10132(), context)

    # Structure parent/enfant détectée comme survolable
    assert result.status in [Status.PASS, Status.NEEDS_REVIEW]
    assert result.tested_elements >= 1


def test_10132_tooltip_sibling_structure(context_factory, run_rgaa):
    """Test 10.13.2: Infobulle en frère adjacent (structure CSS sibling)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .tooltip { display: none; position: absolute; background: black; color: white; }
            .trigger:hover + .tooltip { display: block; }
        </style>
    </head>
    <body>
        <h1>Titre principal</h1>
        <button class="trigger">Survoler moi</button>
        <div class="tooltip">Infobulle sœur</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10132(), context)

    # Structure sibling adjacente détectée par le sélecteur CSS
    # L'analyse statique ne peut pas garantir l'absence de gap
    # Le statut peut être PASS (détecté comme survolable) ou NEEDS_REVIEW
    assert result.status in [Status.PASS, Status.NEEDS_REVIEW]
    assert result.tested_elements >= 1


def test_10132_tooltip_child_structure_with_gap(context_factory, run_rgaa):
    """Test 10.13.2: Infobulle enfant avec espace (gap) dans le déclencheur."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .tooltip { display: none; position: absolute; top: 50px; left: 0; background: black; color: white; }
            .trigger:hover .tooltip { display: block; }
        </style>
    </head>
    <body>
        <h1>Titre principal</h1>
        <div class="trigger">
            Survoler moi
            <div style="height: 30px;"></div>
            <div class="tooltip">Infobulle avec gap</div>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10132(), context)

    # Structure enfant détectée, mais l'analyse statique ne peut pas
    # détecter le gap visuel. Le statut peut être PASS ou NEEDS_REVIEW.
    # Une vérification manuelle est nécessaire pour confirmer.
    assert result.status in [Status.PASS, Status.NEEDS_REVIEW]
    assert result.tested_elements >= 1


# Test 10.13.3 tests


def test_10133_no_hover_focus_content_passes(context_factory, run_rgaa):
    """Test 10.13.3: Page sans contenu additionnel doit passer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <h1>Titre principal</h1>
        <p>Paragraphe normal.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10133(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 0
    assert "Aucun contenu additionnel au survol/focus détecté" in result.summary


def test_10133_tooltip_with_timeout_fails(context_factory, run_rgaa):
    """Test 10.13.3: Infobulle avec timeout de masquage automatique doit échouer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .tooltip { display: none; position: absolute; background: black; color: white; }
            .trigger:hover .tooltip { display: block; }
        </style>
        <script>
            document.querySelector('.trigger').addEventListener('mouseleave', function() {
                setTimeout(function() {
                    document.querySelector('.tooltip').style.display = 'none';
                }, 500);
            });
        </script>
    </head>
    <body>
        <h1>Titre principal</h1>
        <div class="trigger">
            Survoler moi
            <div class="tooltip">Infobulle avec timeout</div>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10133(), context)

    assert result.status == Status.FAIL
    assert result.tested_elements >= 1
    finding = result.findings[0]
    assert "disparaître" in finding.message or "persist" in finding.message.lower()


def test_10133_status_message_passes(context_factory, run_rgaa):
    """Test 10.13.3: Message d'état (aria-live) valide tant qu'actif doit passer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .status { display: none; background: yellow; }
            .trigger:hover .status { display: block; }
        </style>
    </head>
    <body>
        <h1>Titre principal</h1>
        <div class="trigger">
            Survoler pour statut
            <div class="status" aria-live="polite">Statut: Occupé</div>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10133(), context)

    # Message d'état avec aria-live - condition 3 (valide tant que valide)
    assert result.status in [Status.PASS, Status.NEEDS_REVIEW]
    assert result.tested_elements >= 1


def test_10133_error_message_on_focus_passes(context_factory, run_rgaa):
    """Test 10.13.3: Message d'erreur affiché au focus du champ."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .error { display: none; color: red; }
            .field:focus + .error { display: block; }
        </style>
    </head>
    <body>
        <h1>Titre principal</h1>
        <form>
            <input type="email" class="field" required>
            <div class="error" role="alert">Email invalide</div>
            <button type="submit">Envoyer</button>
        </form>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10133(), context)

    # Message d'erreur affiché au focus - condition 3 (valide tant que l'erreur persiste)
    assert result.status in [Status.PASS, Status.NEEDS_REVIEW]
    assert result.tested_elements >= 1


def test_10133_dropdown_menu_persistent(context_factory, run_rgaa):
    """Test 10.13.3: Menu dropdown avec structure correcte."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
        <style>
            .dropdown-menu { display: none; position: absolute; background: white; border: 1px solid #ccc; }
            .dropdown:hover .dropdown-menu { display: block; }
        </style>
    </head>
    <body>
        <h1>Titre principal</h1>
        <div class="dropdown">
            <button>Menu</button>
            <div class="dropdown-menu" role="menu">
                <div role="menuitem">Option 1</div>
                <div role="menuitem">Option 2</div>
            </div>
        </div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA10133(), context)

    assert result.status in [Status.PASS, Status.NEEDS_REVIEW]
    assert result.tested_elements >= 1


# Tests de capabilities manquantes


def test_10131_missing_dom_not_tested(context_factory, run_rgaa):
    """Test 10.13.1: DOM manquant retourne NOT_TESTED."""
    context = context_factory("<html><body>Test</body></html>")
    # Simuler DOM manquant
    context.dom = None

    result = run_rgaa(RGAA10131(), context)

    assert result.status == Status.NOT_TESTED
    assert "DOM n'est pas disponible" in result.summary


def test_10131_missing_html_source_not_tested(context_factory, run_rgaa):
    """Test 10.13.1: HTML source manquant retourne NOT_TESTED."""
    context = context_factory("<html><body>Test</body></html>")
    context.html_source = None

    result = run_rgaa(RGAA10131(), context)

    assert result.status == Status.NOT_TESTED
    assert "code source HTML n'est pas disponible" in result.summary


def test_10132_missing_dom_not_tested(context_factory, run_rgaa):
    """Test 10.13.2: DOM manquant retourne NOT_TESTED."""
    context = context_factory("<html><body>Test</body></html>")
    context.dom = None

    result = run_rgaa(RGAA10132(), context)

    assert result.status == Status.NOT_TESTED


def test_10133_missing_dom_not_tested(context_factory, run_rgaa):
    """Test 10.13.3: DOM manquant retourne NOT_TESTED."""
    context = context_factory("<html><body>Test</body></html>")
    context.dom = None

    result = run_rgaa(RGAA10133(), context)

    assert result.status == Status.NOT_TESTED
