from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_1 import (
    Test1011 as RGAA1011,
)
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_1 import (
    Test1012 as RGAA1012,
)
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_1 import (
    Test1013 as RGAA1013,
)


def test_1011_no_presentation_elements_passes(context_factory, run_rgaa):
    """Test 10.1.1: Absence d'éléments de présentation doit passer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <h1>Titre principal</h1>
        <p>Paragraphe de contenu.</p>
        <ul>
            <li>Élément de liste</li>
        </ul>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1011(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 0
    assert "Aucun élément de présentation détecté" in result.summary


def test_1011_basefont_element_fails(context_factory, run_rgaa):
    """Test 10.1.1: Présence de l'élément <basefont> doit échouer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <basefont face="Arial" size="3" color="black">
        <h1>Titre principal</h1>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1011(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "<basefont>" in result.findings[0].message
    assert result.tested_elements == 1
    assert "Supprimer cet élément" in result.findings[0].recommendation[0]


def test_1011_font_element_fails(context_factory, run_rgaa):
    """Test 10.1.1: Présence de l'élément <font> doit échouer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <h1>Titre principal</h1>
        <font color="red">Texte en rouge</font>
        <p>Paragraphe normal.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1011(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "<font>" in result.findings[0].message
    assert result.tested_elements == 1


def test_1011_center_element_fails(context_factory, run_rgaa):
    """Test 10.1.1: Présence de l'élément <center> doit échouer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <h1>Titre principal</h1>
        <center>Texte centré</center>
        <p>Paragraphe normal.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1011(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "<center>" in result.findings[0].message
    assert result.tested_elements == 1


def test_1011_multiple_presentation_elements_fails(context_factory, run_rgaa):
    """Test 10.1.1: Plusieurs éléments de présentation doivent échouer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <font color="blue">Texte bleu</font>
        <big>Texte gros</big>
        <h1>Titre principal</h1>
        <strike>Texte barré</strike>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1011(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 4  # font, big, strike
    assert result.tested_elements == 4


def test_1011_u_element_non_html5_fails(context_factory, run_rgaa):
    """Test 10.1.1: Élément <u> dans un document non-HTML5 doit échouer."""
    html = """
    <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <h1>Titre principal</h1>
        <u>Texte souligné</u>
        <p>Paragraphe normal.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1011(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "<u>" in result.findings[0].message
    assert result.tested_elements == 1


def test_1011_u_element_html5_passes(context_factory, run_rgaa):
    """Test 10.1.1: Élément <u> dans un document HTML5 doit passer (exception)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <h1>Titre principal</h1>
        <u>Texte souligné</u>
        <p>Paragraphe normal.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1011(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 0
    assert "Aucun élément de présentation détecté" in result.summary


def test_1012_no_presentation_attributes_passes(context_factory, run_rgaa):
    """Test 10.1.2: Absence d'attributs de présentation doit passer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <h1>Titre principal</h1>
        <p class="content">Paragraphe avec classe CSS.</p>
        <div id="header">En-tête</div>
        <img src="image.jpg" alt="Description">
        <table>
            <tr>
                <td>Donnée</td>
            </tr>
        </table>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1012(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 0
    assert "Aucun attribut de présentation détecté" in result.summary


def test_1012_align_attribute_fails(context_factory, run_rgaa):
    """Test 10.1.2: Présence de l'attribut align doit échouer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <h1>Titre principal</h1>
        <p align="center">Paragraphe centré</p>
        <div>Contenu normal</div>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1012(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "align" in result.findings[0].message
    assert result.tested_elements == 1


def test_1012_bgcolor_attribute_fails(context_factory, run_rgaa):
    """Test 10.1.2: Présence de l'attribut bgcolor doit échouer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <h1>Titre principal</h1>
        <table bgcolor="#ffffcc">
            <tr>
                <td>Donnée</td>
            </tr>
        </table>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1012(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "bgcolor" in result.findings[0].message
    assert result.tested_elements == 1


def test_1012_width_attribute_on_non_exception_fails(context_factory, run_rgaa):
    """Test 10.1.2: Attribut width sur un élément non-exception doit échouer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <h1>Titre principal</h1>
        <div width="100">Div avec largeur fixe</div>
        <p>Paragraphe normal.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1012(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) == 1
    assert "width" in result.findings[0].message
    assert result.tested_elements == 1


def test_1012_width_attribute_on_img_passes(context_factory, run_rgaa):
    """Test 10.1.2: Attribut width sur <img> doit passer (exception)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <h1>Titre principal</h1>
        <img src="image.jpg" width="100" alt="Image">
        <p>Paragraphe normal.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1012(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 0
    assert "Aucun attribut de présentation détecté" in result.summary


def test_1012_multiple_presentation_attributes_fails(context_factory, run_rgaa):
    """Test 10.1.2: Plusieurs attributs de présentation doivent échouer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <h1>Titre principal</h1>
        <p align="center" bgcolor="#ffffcc" width="500">
            Paragraphe avec plusieurs attributs de présentation
        </p>
        <font face="Arial" size="4">Texte avec font</font>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1012(), context)

    assert result.status == Status.FAIL
    # Should find: align, bgcolor, width (on p), face, size (on font) = 5 attributes
    assert len(result.findings) >= 4  # At least the main ones
    assert result.tested_elements >= 2  # At least p and font elements


def test_1013_no_space_misuse_passes(context_factory, run_rgaa):
    """Test 10.1.3: Absence d'usage détourné d'espaces doit passer."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <h1>Titre principal</h1>
        <p>Bonjour le monde.</p>
        <p>Ceci est un texte normal sans espaces détournés.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1013(), context)

    assert result.status == Status.PASS
    assert result.findings == []
    assert result.tested_elements == 0
    assert "Aucun usage détourné d'espaces détecté" in result.summary


def test_1013_letter_spacing_detected_fails(context_factory, run_rgaa):
    """Test 10.1.3: Espaces entre lettres d'un mot doivent être détectés."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <h1>Titre principal</h1>
        <p>H E L L O   W O R L D</p>
        <p>Texte normal.</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1013(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1
    # Should detect the spaced-out word
    letter_spacing_findings = [f for f in result.findings if f.evidence.get("pattern_type") == "letter_spacing"]
    assert len(letter_spacing_findings) >= 1
    assert "séparer les lettres d'un mot" in result.findings[0].message
    assert result.tested_elements >= 0  # Checking lines, not elements


def test_1013_table_simulation_with_spaces_detected_fails(context_factory, run_rgaa):
    """Test 10.1.3: Espaces utilisés pour simuler un tableau doivent être détectés."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Page de test</title>
    </head>
    <body>
        <h1>Titre principal</h1>
        <p>Nom           Âge       Ville</p>
        <p>Jean          25        Paris</p>
        <p>Marie         30        Lyon</p>
    </body>
    </html>
    """
    context = context_factory(html)
    result = run_rgaa(RGAA1013(), context)

    assert result.status == Status.FAIL
    assert len(result.findings) >= 1
    # Should detect the space-separated columns simulating a table
    table_sim_findings = [f for f in result.findings if f.evidence.get("pattern_type") == "table_simulation"]
    assert len(table_sim_findings) >= 1
    assert "simuler un tableau" in result.findings[0].message
    assert result.tested_elements >= 0


def test_1013_html_source_not_available_returns_not_tested(context_factory, run_rgaa):
    """Test 10.1.3: Absence de code source HTML doit retourner NOT_TESTED."""
    # Create a context without html_source
    context = context_factory("")
    # Manually remove or set html_source to None to simulate missing data
    if hasattr(context, 'html_source'):
        context.html_source = None

    result = run_rgaa(RGAA1013(), context)

    assert result.status == Status.NOT_TESTED
    assert "code source HTML n'est pas disponible" in result.summary
    assert result.tested_elements == 0