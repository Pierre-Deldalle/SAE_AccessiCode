from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_2 import Test821


@pytest.mark.unit
class TestTest821:
    """Tests unitaires pour le test 8.2.1."""

    def test_test_id_and_criterion_id(self) -> None:
        """Vérifie que les identifiants du test sont corrects."""
        test = Test821()
        assert test.test_id == "8.2.1"
        assert test.criterion_id == "8.2"

    def test_required_capabilities(self) -> None:
        """Vérifie que les capacités requises sont correctement déclarées."""
        test = Test821()
        assert test.required_capabilities == frozenset({Capability.HTML_SOURCE})

    @pytest.mark.asyncio
    async def test_run_valid_html(self) -> None:
        """Test du cas où le HTML est valide."""
        test = Test821()

        # Mock du contexte avec du HTML valide
        context = Mock(spec=AuditContext)
        context.html_source = "<!DOCTYPE html><html><head><title>Test</title></head><body><p>Contenu valide</p></body></html>"

        # Mock du service de validation retournant un résultat valide
        services = Mock()
        mock_validator = AsyncMock()
        mock_validation_result = Mock()
        mock_validation_result.is_valid = True
        mock_validation_result.errors = []
        mock_validator.validate_html.return_value = mock_validation_result
        services.html_validator = mock_validator

        result = await test.run(context, services)

        assert result.test_id == "8.2.1"
        assert result.criterion_id == "8.2"
        assert result.status == TestStatus.PASS
        assert "valide" in result.summary.lower()
        assert result.tested_elements == 1
        mock_validator.validate_html.assert_called_once_with(context.html_source)

    @pytest.mark.asyncio
    async def test_run_invalid_html(self) -> None:
        """Test du cas où le HTML contient des erreurs."""
        test = Test821()

        # Mock du contexte avec du HTML invalide
        context = Mock(spec=AuditContext)
        context.html_source = "<!DOCTYPE html><html><head><title>Test</title></head><body><p>Contenu invalide<div></p></body></html>"

        # Mock du service de validation retournant des erreurs
        services = Mock()
        mock_validator = AsyncMock()
        mock_validation_result = Mock()
        mock_validation_result.is_valid = False
        mock_validation_result.errors = [
            Mock(line=5, message="Balise de fermeture inattendue pour p"),
            Mock(line=6, message="Balise div non fermée")
        ]
        mock_validator.validate_html.return_value = mock_validation_result
        services.html_validator = mock_validator

        result = await test.run(context, services)

        assert result.test_id == "8.2.1"
        assert result.criterion_id == "8.2"
        assert result.status == TestStatus.FAIL
        assert "2 erreur(s)" in result.summary
        assert "Balise de fermeture inattendue" in result.summary
        assert result.tested_elements == 1
        mock_validator.validate_html.assert_called_once_with(context.html_source)

    @pytest.mark.asyncio
    async def test_run_html_validator_service_unavailable(self) -> None:
        """Test du cas où le service de validation HTML n'est pas disponible."""
        test = Test821()

        # Mock du contexte
        context = Mock(spec=AuditContext)
        context.html_source = "<!DOCTYPE html><html><head><title>Test</title></head><body><p>Contenu</p></body></html>"

        # Services sans validator HTML
        services = Mock()
        del services.html_validator  # Supprimer l'attribut s'il existe

        result = await test.run(context, services)

        assert result.test_id == "8.2.1"
        assert result.criterion_id == "8.2"
        assert result.status == TestStatus.NOT_TESTED
        assert "non disponible" in result.summary.lower()
        assert result.tested_elements == 0

    @pytest.mark.asyncio
    async def test_run_no_services_provided(self) -> None:
        """Test du cas où aucun service n'est fourni."""
        test = Test821()

        # Mock du contexte
        context = Mock(spec=AuditContext)
        context.html_source = "<!DOCTYPE html><html><head><title>Test</title></head><body><p>Contenu</p></body></html>"

        result = await test.run(context, None)

        assert result.test_id == "8.2.1"
        assert result.criterion_id == "8.2"
        assert result.status == TestStatus.NOT_TESTED
        assert "non disponible" in result.summary.lower()
        assert result.tested_elements == 0