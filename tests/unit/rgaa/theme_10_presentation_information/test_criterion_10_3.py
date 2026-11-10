from __future__ import annotations

import asyncio
from unittest.mock import Mock

import pytest

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_10_presentation_information.criterion_10_3 import (
    Test1031,
)


class TestTest1031:
    """Tests for Test1031 - Reading order when CSS is disabled."""

    @pytest.mark.asyncio
    async def test_no_dom(self):
        """Test when DOM is not available."""
        context = Mock(spec=AuditContext)
        context.dom = None

        test = Test1031()
        with pytest.raises(ValueError, match="nécessite un DOM"):
            await test.run(context)

    @pytest.mark.asyncio
    async def test_proper_reading_order_passes(self):
        """Test with proper reading order and form associations."""
        html_source = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Page de test</title>
        </head>
        <body>
            <h1>Titre principal</h1>
            <p>Paragraphe d'introduction.</p>
            <form>
                <label for="nom">Nom :</label>
                <input type="text" id="nom" name="nom">
                <br>
                <label for="prenom">Prénom :</label>
                <input type="text" id="prenom" name="prenom">
            </form>
            <h2>Sous-titre</h2>
            <table>
                <thead>
                    <tr>
                        <th>Produit</th>
                        <th>Prix</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Ordinateur</td>
                        <td>800€</td>
                    </tr>
                </tbody>
            </table>
            <ul>
                <li>Premier point</li>
                <li>Deuxième point</li>
            </ul>
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        from bs4 import BeautifulSoup
        context.dom = BeautifulSoup(html_source, 'html.parser')

        test = Test1031()
        result = await test.run(context)

        assert result.status == TestStatus.PASS
        assert "ordre du contenu reste compréhensible" in result.summary
        assert result.findings == []
        assert result.tested_elements == 0

    @pytest.mark.asyncio
    async def test_missing_form_labels(self):
        """Test detection of form elements without labels."""
        html_source = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Page de test</title>
        </head>
        <body>
            <h1>Formulaire de contact</h1>
            <form>
                Nom : <input type="text" id="nom" name="nom"><br>
                <input type="email" id="email" name="email"><br>
                <label for="message">Message :</label>
                <textarea id="message" name="message"></textarea>
            </form>
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        from bs4 import BeautifulSoup
        context.dom = BeautifulSoup(html_source, 'html.parser')

        test = Test1031()
        result = await test.run(context)

        assert result.status == TestStatus.FAIL
        assert len(result.findings) == 2  # Nom and email fields missing labels
        # Check that we found the elements with specific IDs
        element_ids_found = [f.evidence.get('element_id') for f in result.findings]
        assert 'nom' in element_ids_found
        assert 'email' in element_ids_found
        assert result.tested_elements == 2

    @pytest.mark.asyncio
    async def test_missing_table_headers(self):
        """Test detection of tables without headers."""
        html_source = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Page de test</title>
        </head>
        <body>
            <h1>Tableau de données</h1>
            <table>
                <tr>
                    <td>Produit</td>
                    <td>Prix</td>
                </tr>
                <tr>
                    <td>Ordinateur</td>
                    <td>800€</td>
                </tr>
            </table>
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        from bs4 import BeautifulSoup
        context.dom = BeautifulSoup(html_source, 'html.parser')

        test = Test1031()
        result = await test.run(context)

        assert result.status == TestStatus.FAIL
        assert len(result.findings) >= 1
        assert any("tableau" in f.message.lower() for f in result.findings)
        assert any("en-tête" in f.message.lower() or "th" in f.message.lower() for f in result.findings)
        assert result.tested_elements >= 1

    @pytest.mark.asyncio
    async def test_empty_list_items(self):
        """Test detection of lists with mostly empty items."""
        html_source = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Page de test</title>
        </head>
        <body>
            <h1>Liste de navigation</h1>
            <ul>
                <li></li>
                <li>   </li>
                <li>&nbsp;</li>
                <li>Accueil</li>
                <li></li>
            </ul>
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        from bs4 import BeautifulSoup
        context.dom = BeautifulSoup(html_source, 'html.parser')

        test = Test1031()
        result = await test.run(context)

        # With 3 out of 5 items being empty/whitespace, this should trigger the finding
        assert result.status == TestStatus.FAIL
        assert any("liste" in f.message.lower() for f in result.findings)
        assert any("vide" in f.message.lower() or "empty" in f.message.lower() for f in result.findings)
        assert result.tested_elements >= 1

    @pytest.mark.asyncio
    async def test_skipped_heading_levels(self):
        """Test detection of skipped heading levels."""
        html_source = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Page de test</title>
        </head>
        <body>
            <h1>Titre principal</h1>
            <h3>Titre de niveau 3 (niveau 2 sauté)</h3>
            <p>Contenu ici.</p>
            <h2>Titre de niveau 2</h2>
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        from bs4 import BeautifulSoup
        context.dom = BeautifulSoup(html_source, 'html.parser')

        test = Test1031()
        result = await test.run(context)

        assert result.status == TestStatus.FAIL
        assert len(result.findings) >= 1
        assert any("titre" in f.message.lower() or "heading" in f.message.lower() for f in result.findings)
        assert any("saut" in f.message.lower() or "skipped" in f.message.lower() for f in result.findings)
        assert result.tested_elements >= 1

    @pytest.mark.asyncio
    async def test_proper_heading_structure(self):
        """Test with proper heading hierarchy."""
        html_source = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Page de test</title>
        </head>
        <body>
            <h1>Titre principal</h1>
            <h2>Section Title</h2>
            <h3>Subsection Title</h3>
            <p>Some content here.</p>
            <h2>Another Section</h2>
            <p>More content.</p>
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        from bs4 import BeautifulSoup
        context.dom = BeautifulSoup(html_source, 'html.parser')

        test = Test1031()
        result = await test.run(context)

        assert result.status == TestStatus.PASS
        assert "ordre du contenu reste compréhensible" in result.summary
        assert result.findings == []
        assert result.tested_elements == 0

    @pytest.mark.asyncio
    async def test_multiple_issues(self):
        """Test detection of multiple reading order issues."""
        html_source = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Page de test</title>
        </head>
        <body>
            <h1>Titre principal</h1>
            <h3>Titre sautant un niveau</h3>
            <form>
                <input type="text" id="champ1" name="champ1"><br>
                <label for="champ2">Champ 2 :</label>
                <input type="text" id="champ2" name="champ2">
            </form>
            <table>
                <tr>
                    <td>Donnée 1</td>
                    <td>Donnée 2</td>
                </tr>
            </table>
            <ul>
                <li></li>
                <li></li>
                <li>Item 2</li>
                <li></li>
                <li></li>
            </ul>
        </body>
        </html>
        """

        context = Mock(spec=AuditContext)
        from bs4 import BeautifulSoup
        context.dom = BeautifulSoup(html_source, 'html.parser')

        test = Test1031()
        result = await test.run(context)

        assert result.status == TestStatus.FAIL
        # Should find multiple issues: heading, form label, table header, list items
        assert len(result.findings) >= 4
        assert result.tested_elements >= 4

        # Check that we have different types of issues
        findings_text = " ".join([f.message.lower() for f in result.findings])
        assert "titre" in findings_text or "heading" in findings_text
        assert "formulaire" in findings_text or "label" in findings_text
        assert "tableau" in findings_text
        assert "liste" in findings_text