from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_8 import Test881


@pytest.mark.unit
class TestTest881:
    """Tests unitaires pour le test 8.8.1."""

    def test_test_id_and_criterion_id(self) -> None:
        """Vérifie que les identifiants du test sont corrects."""
        test = Test881()
        assert test.test_id == "8.8.1"
        assert test.criterion_id == "8.8"

    def test_required_capabilities(self) -> None:
        """Vérifie que les capacités requises sont correctement déclarées."""
        test = Test881()
        assert test.required_capabilities == frozenset({Capability.DOM})

    @pytest.mark.asyncio
    async def test_run_all_language_codes_valid_and_relevant(self) -> None:
        """Test du cas où tous les codes de langue sont valides et pertinents."""
        test = Test881()

        # Mock du contexte
        context = Mock(spec=AuditContext)
        context.dom = Mock()
        context.html_source = "<html><body>Contenu</body></html>"

        # Mock du service d'analyse de langue retournant aucun erreur
        services = Mock()
        mock_analyzer = AsyncMock()
        mock_analysis_result = Mock()
        mock_analysis_result.has_errors = False
        mock_analysis_result.explanation = "Tous les codes de langue utilisés pour les changements de langue sont valides et pertinents."
        mock_analysis_result.total_changes_checked = 3
        mock_analysis_result.findings = []
        mock_analysis_result.confidence = "high"
        mock_analyzer.analyze_language_validity.return_value = mock_analysis_result
        services.language_validity_analyzer = mock_analyzer

        result = await test.run(context, services)

        assert result.test_id == "8.8.1"
        assert result.criterion_id == "8.8"
        assert result.status == TestStatus.PASS
        assert "valides et pertinents" in result.summary
        assert result.tested_elements == 3
        assert result.findings == []
        mock_analyzer.analyze_language_validity.assert_called_once_with(
            context.dom,
            context.html_source
        )

    @pytest.mark.asyncio
    async def test_run_some_language_codes_invalid_or_irrelevant(self) -> None:
        """Test du cas où certains codes de langue sont invalides ou non pertinents."""
        test = Test881()

        # Mock du contexte
        context = Mock(spec=AuditContext)
        context.dom = Mock()
        context.html_source = "<html><body>Contenu</body></html>"

        # Mock du service d'analyse de langue retournant des erreurs
        services = Mock()
        mock_analyzer = AsyncMock()
        mock_analysis_result = Mock()
        mock_analysis_result.has_errors = True
        mock_analysis_result.explanation = "2 codes de langue utilisés pour les changements de langue sont invalides ou non pertinents."
        mock_analysis_result.total_changes_checked = 5
        mock_analysis_result.findings = [
            Mock(
                element="p[index=1]",
                message="Le code de langue 'xx' n'est pas un code ISO valide",
                evidence={"language_code": "xx", "text": "some text"}
            ),
            Mock(
                element="span[index=3]",
                message="Le code de langue 'en' n'est pas pertinent pour ce texte français",
                evidence={"language_code": "en", "text": "bonjour"}
            )
        ]
        mock_analysis_result.confidence = "high"
        mock_analyzer.analyze_language_validity.return_value = mock_analysis_result
        services.language_validity_analyzer = mock_analyzer

        result = await test.run(context, services)

        assert result.test_id == "8.8.1"
        assert result.criterion_id == "8.8"
        assert result.status == TestStatus.FAIL
        assert "invalides ou non pertinents" in result.summary
        assert result.tested_elements == 5
        assert len(result.findings) == 2
        assert result.findings[0].element == "p[index=1]"
        assert result.findings[1].element == "span[index=3]"
        mock_analyzer.analyze_language_validity.assert_called_once_with(
            context.dom,
            context.html_source
        )

    @pytest.mark.asyncio
    async def test_run_language_analyzer_low_confidence(self) -> None:
        """Test du cas où l'analyseur retourne un faible niveau de confiance."""
        test = Test881()

        # Mock du contexte
        context = Mock(spec=AuditContext)
        context.dom = Mock()
        context.html_source = "<html><body>Contenu</body></html>"

        # Mock du service d'analyse de langue retournant faible confiance
        services = Mock()
        mock_analyzer = AsyncMock()
        mock_analysis_result = Mock()
        mock_analysis_result.has_errors = False  # Peu importe, confiance faible prime
        mock_analysis_result.explanation = "L'analyse automatique de la validité/pertinence des codes de langue n'est pas suffisamment fiable."
        mock_analysis_result.total_changes_checked = 0
        mock_analysis_result.findings = []
        mock_analysis_result.confidence = "low"
        mock_analyzer.analyze_language_validity.return_value = mock_analysis_result
        services.language_validity_analyzer = mock_analyzer

        result = await test.run(context, services)

        assert result.test_id == "8.8.1"
        assert result.criterion_id == "8.8"
        assert result.status == TestStatus.NEEDS_REVIEW
        assert "pas suffisamment fiable" in result.summary
        assert result.tested_elements == 0
        mock_analyzer.analyze_language_validity.assert_called_once_with(
            context.dom,
            context.html_source
        )

    @pytest.mark.asyncio
    async def test_run_language_analyzer_exception(self) -> None:
        """Test du cas où l'analyseur lève une exception."""
        test = Test881()

        # Mock du contexte
        context = Mock(spec=AuditContext)
        context.dom = Mock()
        context.html_source = "<html><body>Contenu</body></html>"

        # Mock du service d'analyse de langue qui lève une exception
        services = Mock()
        mock_analyzer = AsyncMock()
        mock_analyzer.analyze_language_validity.side_effect = Exception("Erreur d'analyse")
        services.language_validity_analyzer = mock_analyzer

        result = await test.run(context, services)

        assert result.test_id == "8.8.1"
        assert result.criterion_id == "8.8"
        assert result.status == TestStatus.ERROR
        assert "L'analyse de validité/pertinence des codes de langue a échoué" in result.summary
        assert result.tested_elements == 0
        assert "Erreur d'analyse" in result.summary
        mock_analyzer.analyze_language_validity.assert_called_once_with(
            context.dom,
            context.html_source
        )

    @pytest.mark.asyncio
    async def test_run_no_language_validity_service(self) -> None:
        """Test du cas où le service d'analyse de validité des codes de langue n'est pas disponible."""
        test = Test881()

        # Mock du contexte
        context = Mock(spec=AuditContext)
        context.dom = Mock()
        context.html_source = "<html><body>Contenu</body></html>"

        # Services sans analyseur de validité de langue
        services = Mock()
        # S'assurer que l'attribut n'existe pas
        if hasattr(services, 'language_validity_analyzer'):
            delattr(services, 'language_validity_analyzer')

        result = await test.run(context, services)

        assert result.test_id == "8.8.1"
        assert result.criterion_id == "8.8"
        assert result.status == TestStatus.NOT_TESTED
        assert "non disponible" in result.summary.lower()
        assert result.tested_elements == 0

    @pytest.mark.asyncio
    async def test_run_no_services_provided(self) -> None:
        """Test du cas où aucun service n'est fourni."""
        test = Test881()

        # Mock du contexte
        context = Mock(spec=AuditContext)
        context.dom = Mock()
        context.html_source = "<html><body>Contenu</body></html>"

        result = await test.run(context, None)

        assert result.test_id == "8.8.1"
        assert result.criterion_id == "8.8"
        assert result.status == TestStatus.NOT_TESTED
        assert "non disponible" in result.summary.lower()
        assert result.tested_elements == 0

    @pytest.mark.asyncio
    async def test_run_dom_not_available(self) -> None:
        """Test du cas où le DOM n'est pas disponible."""
        test = Test881()

        # Mock du contexte sans DOM
        context = Mock(spec=AuditContext)
        context.dom = None

        result = await test.run(context, None)

        assert result.test_id == "8.8.1"
        assert result.criterion_id == "8.8"
        assert result.status == TestStatus.ERROR
        assert "Le DOM n'est pas disponible" in result.summary
        assert result.tested_elements == 0