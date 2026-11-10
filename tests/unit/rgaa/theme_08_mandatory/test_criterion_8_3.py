from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

from bs4 import BeautifulSoup

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_3 import Test831


@pytest.mark.unit
class TestTest831:
    """Tests unitaires pour le test 8.3.1."""

    def test_test_id_and_criterion_id(self) -> None:
        """Vérifie que les identifiants du test sont corrects."""
        test = Test831()
        assert test.test_id == "8.3.1"
        assert test.criterion_id == "8.3"

    def test_required_capabilities(self) -> None:
        """Vérifie que les capacités requises sont correctement déclarées."""
        test = Test831()
        assert test.required_capabilities == frozenset({Capability.DOM})

    @pytest.mark.asyncio
    async def test_run_html_lang_present(self) -> None:
        """Test du cas où l'attribut lang est présent sur l'élément html."""
        test = Test831()

        # Créer un contexte avec un DOM contenant lang sur html
        html_content = '<html lang="fr"><head><title>Test</title></head><body><p>Bonjour</p></body></html>'
        soup = BeautifulSoup(html_content, 'html.parser')

        context = Mock(spec=AuditContext)
        context.dom = soup

        result = await test.run(context, None)

        assert result.test_id == "8.3.1"
        assert result.criterion_id == "8.3"
        assert result.status == TestStatus.PASS
        assert "Langue déclarée sur l'élément html" in result.summary
        assert result.tested_elements == 1

    @pytest.mark.asyncio
    async def test_run_xml_lang_present(self) -> None:
        """Test du cas où l'attribut xml:lang est présent sur l'élément html."""
        test = Test831()

        # Créer un contexte avec un DOM contenant xml:lang sur html
        html_content = '<html xml:lang="fr"><head><title>Test</title></head><body><p>Bonjour</p></body></html>'
        soup = BeautifulSoup(html_content, 'xml')  # Using xml parser for xml:lang

        context = Mock(spec=AuditContext)
        context.dom = soup

        result = await test.run(context, None)

        assert result.test_id == "8.3.1"
        assert result.criterion_id == "8.3"
        assert result.status == TestStatus.PASS
        assert "Langue déclarée sur l'élément html" in result.summary
        assert result.tested_elements == 1

    @pytest.mark.asyncio
    async def test_run_no_html_lang_but_text_elements_have_lang_via_parent(self) -> None:
        """Test du cas où pas de lang sur html mais les éléments de texte ont lang via un parent."""
        test = Test831()

        # Créer un contexte avec un div ayant lang, contenant du texte
        html_content = '<html><head><title>Test</title></head><body><div lang="fr"><p>Bonjour</p></div></body></html>'
        soup = BeautifulSoup(html_content, 'html.parser')

        context = Mock(spec=AuditContext)
        context.dom = soup

        result = await test.run(context, None)

        assert result.test_id == "8.3.1"
        assert result.criterion_id == "8.3"
        assert result.status == TestStatus.PASS
        assert "éléments de texte ont une indication de langue" in result.summary
        assert result.tested_elements == 1  # Un seul élément de texte significatif ("Bonjour")

    @pytest.mark.asyncio
    async def test_run_no_html_lang_and_some_text_elements_missing_lang(self) -> None:
        """Test du cas où pas de lang sur html et certains éléments de texte manquants de lang."""
        test = Test831()

        # Créer un contexte avec un élément de texte sans lang et un autre avec lang via parent
        html_content = '''
        <html>
            <head><title>Test</title></head>
            <body>
                <p>Texte sans lang</p>
                <div lang="fr"><p>Texte avec lang via parent</p></div>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html_content, 'html.parser')

        context = Mock(spec=AuditContext)
        context.dom = soup

        result = await test.run(context, None)

        assert result.test_id == "8.3.1"
        assert result.criterion_id == "8.3"
        assert result.status == TestStatus.FAIL
        assert "n'ont pas d'indication de langue" in result.summary
        assert result.tested_elements == 2  # Deux éléments de texte significatifs

    @pytest.mark.asyncio
    async def test_run_no_text_elements(self) -> None:
        """Test du cas où il n'y a pas d'éléments de texte significatifs."""
        test = Test831()

        # Créer un contexte avec seulement des éléments scripts/styles (pas de texte significatif)
        html_content = '''
        <html>
            <head>
                <title>Test</title>
                <script>console.log("test");</script>
                <style>body { color: red; }</style>
            </head>
            <body></body>
        </html>
        '''
        soup = BeautifulSoup(html_content, 'html.parser')

        context = Mock(spec=AuditContext)
        context.dom = soup

        result = await test.run(context, None)

        assert result.test_id == "8.3.1"
        assert result.criterion_id == "8.3"
        assert result.status == TestStatus.NOT_APPLICABLE
        assert "Aucun élément de texte significatif trouvé" in result.summary
        assert result.tested_elements == 0

    @pytest.mark.asyncio
    async def test_run_no_html_element(self) -> None:
        """Test du cas où il n'y a pas d'élément html."""
        test = Test831()

        # Créer un contexte avec un DOM sans élément html
        html_content = '<head><title>Test</title></head><body><p>Bonjour</p></body>'
        soup = BeautifulSoup(html_content, 'html.parser')

        context = Mock(spec=AuditContext)
        context.dom = soup

        result = await test.run(context, None)

        assert result.test_id == "8.3.1"
        assert result.criterion_id == "8.3"
        assert result.status == TestStatus.FAIL
        assert "Aucun élément html trouvé" in result.summary
        assert result.tested_elements == 0

    @pytest.mark.asyncio
    async def test_run_dom_not_beautifulsoup(self) -> None:
        """Test du cas où le DOM n'est pas un objet BeautifulSoup."""
        test = Test831()

        context = Mock(spec=AuditContext)
        context.dom = "ce n'est pas un BeautifulSoup"

        result = await test.run(context, None)

        assert result.test_id == "8.3.1"
        assert result.criterion_id == "8.3"
        assert result.status == TestStatus.ERROR
        assert "Le DOM n'est pas disponible ou n'est pas un objet BeautifulSoup" in result.summary
        assert result.tested_elements == 0