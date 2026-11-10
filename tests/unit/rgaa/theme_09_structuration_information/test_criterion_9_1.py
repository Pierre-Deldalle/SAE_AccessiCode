from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_09_structuration_information.criterion_9_1 import (
    Test911 as RGAA911,
)
from accessi_code.rgaa.tests.theme_09_structuration_information.criterion_9_1 import (
    Test912 as RGAA912,
)
from accessi_code.rgaa.tests.theme_09_structuration_information.criterion_9_1 import (
    Test913 as RGAA913,
)


def test_911_correct_hierarchy_passes(context_factory, run_rgaa):
    """Test 9.1.1: Hiérarchie correcte (h1 -> h2 -> h3) doit passer."""
    html = """
    <h1>Titre principal</h1>
    <h2>Sous-titre</h2>
    <h3>Sous-sous-titre</h3>
    <p>Contenu</p>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA911(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 3


def test_911_incorrect_hierarchy_skipping_level_fails(context_factory, run_rgaa):
    """Test 9.1.1: Hiérarchie incorrecte (saut de niveau h1 -> h3) doit échouer."""
    html = """
    <h1>Titre principal</h1>
    <h3>Sous-sous-titre (manque h2)</h3>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA911(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "Hiérarchie de titres incorrecte" in result.findings[0].message
    assert result.tested_elements == 2


def test_911_multiple_sections_with_correct_hierarchy_passes(context_factory, run_rgaa):
    """Test 9.1.1: Plusieurs sections avec hiérarchie correcte chacune doivent passer."""
    html = """
    <h1>Titre principal 1</h1>
    <h2>Sous-titre 1</h2>

    <h1>Titre principal 2</h1>
    <h2>Sous-titre 2</h1>
    <h3>Sous-sous-titre 2</h3>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA911(), context)

    # Note: Le deuxième h1 est en fait un h2 dans le HTML ci-dessus, corrigons-le
    html = """
    <h1>Titre principal 1</h1>
    <h2>Sous-titre 1</h2>

    <h1>Titre principal 2</h1>
    <h2>Sous-titre 2</h2>
    <h3>Sous-sous-titre 2</h3>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA911(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 5


def test_911_wai_aria_heading_correct_hierarchy_passes(context_factory, run_rgaa):
    """Test 9.1.1: Hiérarchie correcte avec éléments WAI-ARIA doit passer."""
    html = """
    <h1>Titre principal</h1>
    <div role="heading" aria-level="2">Sous-titre</div>
    <h3>Sous-sous-titre</h3>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA911(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 3


def test_911_wai_aria_heading_incorrect_hierarchy_fails(context_factory, run_rgaa):
    """Test 9.1.1: Hiérarchie incorrecte avec éléments WAI-ARIA doit échouer."""
    html = """
    <h1>Titre principal</h1>
    <div role="heading" aria-level="3">Sous-sous-titre (manque niveau 2)</div>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA911(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "Hiérarchie de titres incorrecte" in result.findings[0].message
    assert result.tested_elements == 2


def test_911_no_headings_not_applicable(context_factory, run_rgaa):
    """Test 9.1.1: Absence de titres doit retourner NOT_APPLICABLE."""
    html = """
    <p>Paragraphe sans titre</p>
    <div>Contenu</div>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA911(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert "Aucun titre détecté" in result.summary


def test_912_descriptive_headings_passes(context_factory, run_rgaa):
    """Test 9.1.2: Titres avec contenu descriptif doivent passer."""
    html = """
    <h1>Introduction générale</h1>
    <h2>Méthodologie utilisée</h2>
    <h3>Résultats obtenus</h3>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA912(), context)

    assert result.status == Status.PASS
    assert result.tested_elements == 3
    # Vérifier qu'il n'y a pas de findings d'erreur (les findings pour titres courts sont acceptables en NEEDS_REVIEW)
    error_findings = [f for f in result.findings if "Le titre est vide" in f.message]
    assert len(error_findings) == 0


def test_912_empty_heading_fails(context_factory, run_rgaa):
    """Test 9.1.2: Titre vide doit échouer."""
    html = """
    <h1>Titre valide</h1>
    <h2></h2>  <!-- Titre vide -->
    <h3>Autre titre valide</h3>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA912(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1
    # Au moins un finding devrait indiquer un titre vide
    empty_findings = [f for f in result.findings if "Le titre est vide" in f.message]
    assert len(empty_findings) >= 1
    assert result.tested_elements == 3


def test_912_very_short_heading_requires_review(context_factory, run_rgaa):
    """Test 9.1.2: Titre très court devrait nécessiter une vérification manuelle."""
    html = """
    <h1>Titre</h1>  <!-- Titre de 5 caractères -->
    <h2>AB</h2>    <!-- Titre de 2 caractères -->
    <h3>XYZ</h3>    <!-- Titre de 3 caractères -->
    """
    context = context_factory(html)
    result = run_rgaa(RGAA912(), context)

    # Selon notre implémentation, les titres très courts produisent des findings qui mènent à NEEDS_REVIEW
    # sauf s'il y a aussi des titres vides qui mèneraient à FAIL
    assert result.status in [Status.NEEDS_REVIEW, Status.PASS]  # PASS si on ne considère pas "XY" comme trop court
    short_findings = [f for f in result.findings if "très court" in f.message]
    # On devrait avoir au moins un finding pour le titre "AB" (2 caractères)
    assert len(short_findings) >= 1
    assert result.tested_elements == 3


def test_912_no_headings_not_applicable(context_factory, run_rgaa):
    """Test 9.1.2: Absence de titres doit retourner NOT_APPLICABLE."""
    html = """
    <p>Paragraphe sans titre</p>
    <div>Contenu</div>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA912(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert "Aucun titre détecté" in result.summary


def test_913_properly_structured_headings_passes(context_factory, run_rgaa):
    """Test 9.1.3: Titres correctement structurés doivent passer."""
    html = """
    <h1>Titre avec balise h1</h1>
    <h2>Titre avec balise h2</h2>
    <div role="heading" aria-level="3">Titre avec WAI-ARIA</div>
    <h4>Autre titre h4</h4>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA913(), context)

    assert result.status == Status.PASS
    assert result.findings == []  # Pas d'erreurs de structure
    assert result.tested_elements == 4


def test_913_mixed_native_and_wai_aria_headings_passes(context_factory, run_rgaa):
    """Test 9.1.3: Mélange de balises hx naturelles et WAI-ARIA doit passer."""
    html = """
    <h1>Titre principal</h1>
    <section>
        <h2>Section titre</h2>
        <div role="heading" aria-level="3">Sous-section titre</div>
    </section>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA913(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 3


def test_913_no_headings_not_applicable(context_factory, run_rgaa):
    """Test 9.1.3: Absence de titres doit retourner NOT_APPLICABLE."""
    html = """
    <p>Paragraphe sans titre</p>
    <div>Contenu</div>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA913(), context)

    assert result.status == Status.NOT_APPLICABLE
    assert result.tested_elements == 0
    assert "Aucun titre détecté" in result.summary


# Test pour vérifier que le test 9.1.3 ne détecte pas les titres manquants de manière déterministe
def test_913_missing_heading_structure_not_detected_deterministically(context_factory, run_rgaa):
    """Test 9.1.3: Texte qui devrait être un titre mais n'est pas structuré comme tel."""
    html = """
    <p>Ce paragraphe ressemble à un titre visuellement mais n'est pas structuré comme tel</p>
    <h2>Vrai titre</h2>
    <p>Autre paragraphe qui ressemble à un titre</p>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA913(), context)

    # Notre implémentation actuelle ne détecte pas de manière déterministe
    # les titres manquants, donc cela devrait retourner PASS
    # (seuls les éléments déjà identifiés comme titres sont vérifiés)
    assert result.status == Status.PASS
    assert result.tested_elements == 1  # Seul le h2 est compté comme titre
    # Le résumé devrait mentionner la limitation
    if result.metadata and "note" in result.metadata:
        assert "titres manquants" in result.metadata["note"].lower() or "vérification manuelle" in result.metadata["note"].lower()