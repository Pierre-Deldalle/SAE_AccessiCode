from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_7 import Test871


@pytest.mark.unit
class TestTest871:
    """Tests unitaires pour le test 8.7.1."""

    def test_test_id_and_criterion_id(self) -> None:
        """Vérifie que les identifiants du test sont corrects."""
        test = Test871()
        assert test.test_id == "8.7.1"
        assert test.criterion_id == "8.7"

    def test_required_capabilities(self) -> None:
        """Vérifie que les capacités requises sont correctement déclarées."""
        test = Test871()
        assert test.required_capabilities == frozenset({Capability.DOM})

    @pytest.mark.asyncio
    async def test_run_language_changes_detected_and_marked(self) -> None:
        """Test du cas où des changements de langue sont détectés et correctement marqués."""
        test = Test871()

        # Mock du contexte
        context = Mock(spec=AuditContext)
        context.dom = Mock()
        context.html_source = "<html><body>Contenu</body></html>"

        # Mock du service d'analyse de langue retournant aucun violation
        services = Mock()
        mock_analyzer = AsyncMock()
        mock_analysis_result = Mock()
        mock_analysis_result.has_violations = False
        mock_analysis_result.explanation = "Tous les passages de texte en langue étrangère sont correctement identifiés."
        mock_analysis_result.total_elements_checked = 5
        mock_analysis_result.findings = []
        mock_analysis_result.confidence = "high"
        mock_analyzer.analyze_language_changes.return_value = mock_analysis_result
        services.language_change_analyzer = mock_analyzer

        result = await test.run(context, services)

        assert result.test_id == "8.7.1"
        assert result.criterion_id == "8.7"
        assert result.status == TestStatus.PASS
        assert "correctement identifiés" in result.summary
        assert result.tested_elements == 5
        assert result.findings == []
        mock_analyzer.analyze_language_changes.assert_called_once_with(
            context.dom,
            context.html_source
        )

    @pytest.mark.asyncio
    async def test_run_language_changes_detected_and_missing_marking(self) -> None:
        """Test du cas où des changements de langue sont détectés mais manquants de marquage."""
        test = Test871()

        # Mock du contexte
        context = Mock(spec=AuditContext)
        context.dom = Mock()
        context.html_source = "<html><body>Contenu</body></html>"

        # Mock du service d'analyse de langue retournant des violations
        services = Mock()
        mock_analyzer = AsyncMock()
        mock_analysis_result = Mock()
        mock_analysis_result.has_violations = True
        mock_analysis_result.explanation = "3 passages de texte en langue étrangère manque d'indication de langue."
        mock_analysis_result.total_elements_checked = 10
        mock_analysis_result.findings = [
            Mock(
                element="p[index=2]",
                message="Le texte 'Hello world' devrait avoir un attribut lang='en'",
                evidence={"text": "Hello world", "language": "en"}
            )
        ]
        mock_analysis_result.confidence = "high"
        mock_analyzer.analyze_language_changes.return_value = mock_analysis_result
        services.language_change_analyzer = mock_analyzer

        result = await test.run(context, services)

        assert result.test_id == "8.7.1"
        assert result.criterion_id == "8.7"
        assert result.status == TestStatus.FAIL
        assert "manque d'indication de langue" in result.summary
        assert result.tested_elements == 10
        assert len(result.findings) == 1
        assert result.findings[0].element == "p[index=2]"
        mock_analyzer.analyze_language_changes.assert_called_once_with(
            context.dom,
            context.html_source
        )

    @pytest.mark.asyncio
    async def test_run_language_analyzer_low_confidence(self) -> None:
        """Test du cas où l'analyseur retourne un faible niveau de confiance."""
        test = Test871()

        # Mock du contexte
        context = Mock(spec=AuditContext)
        context.dom = Mock()
        context.html_source = "<html><body>Contenu</body></html>"

        # Mock du service d'analyse de langue retournant faible confiance
        services = Mock()
        mock_analyzer = AsyncMock()
        mock_analysis_result = Mock()
        mock_analysis_result.has_violations = False  # Peu importe, confiance faible prime
        mock_analysis_result.explanation = "L'analyse automatique des changements de langue n'est pas suffisamment fiable."
        mock_analysis_result.total_elements_checked = 0
        mock_analysis_result.findings = []
        mock_analysis_result.confidence = "low"
        mock_analyzer.analyze_language_changes.return_value = mock_analysis_result
        services.language_change_analyzer = mock_analyzer

        result = await test.run(context, services)

        assert result.test_id == "8.7.1"
        assert result.criterion_id == "8.7"
        assert result.status == TestStatus.NEEDS_REVIEW
        assert "pas suffisamment fiable" in result.summary
        assert result.tested_elements == 0
        mock_analyzer.analyze_language_changes.assert_called_once_with(
            context.dom,
            context.html_source
        )

    @pytest.mark.asyncio
    async def test_run_language_analyzer_exception(self) -> None:
        """Test du cas où l'analyseur lève une exception."""
        test = Test871()

        # Mock du contexte
        context = Mock(spec=AuditContext)
        context.dom = Mock()
        context.html_source = "<html><body>Contenu</body></html>"

        # Mock du service d'analyse de langue qui lève une exception
        services = Mock()
        mock_analyzer = AsyncMock()
        mock_analyzer.analyze_language_changes.side_effect = Exception("Erreur d'analyse")
        services.language_change_analyzer = mock_analyzer

        result = await test.run(context, services)

        assert result.test_id == "8.7.1"
        assert result.criterion_id == "8.7"
        assert result.status == TestStatus.ERROR
        assert "L'analyse des changements de langue a échoué" in result.summary
        assert result.tested_elements == 0
        assert "Erreur d'analyse" in result.summary
        mock_analyzer.analyze_language_changes.assert_called_once_with(
            context.dom,
            context.html_source
        )

    @pytest.mark.asyncio
    async def test_run_no_language_change_service(self) -> None:
        """Test du cas où le service d'analyse de changement de langue n'est pas disponible."""
        test = Test871()

        # Mock du contexte
        context = Mock(spec=AuditContext)
        context.dom = Mock()
        context.html_source = "<html><body>Contenu</body></html>"

        # Services sans analyseur de changement de langue
        services = Mock()
        # S'assurer que l'attribut n'existe pas
        if hasattr(services, 'language_change_analyzer'):
            delattr(services, 'language_change_analyzer')

        result = await test.run(context, services)

        assert result.test_id == "8.7.1"
        assert result.criterion_id == "8.7"
        assert result.status == TestStatus.NOT_TESTED
        assert "non disponible" in result.summary.lower()
        assert result.tested_elements == 0

    @pytest.mark.asyncio
    async def test_run_no_services_provided(self) -> None:
        """Test du cas où aucun service n'est fourni."""
        test = Test871()

        # Mock du contexte
        context = Mock(spec=AuditContext)
        context.dom = Mock()
        context.html_source = "<html><body>Contenu</body></html>"

        result = await test.run(context, None)

        assert result.test_id == "8.7.1"
        assert result.criterion_id == "8.7"
        assert result.status == TestStatus.NOT_TESTED
        assert "non disponible" in result.summary.lower()
        assert result.tested_elements == 0

    @pytest.mark.asyncio
    async def test_run_dom_not_available(self) -> None:
        """Test du cas où le DOM n'est pas disponible."""
        test = Test871()

        # Mock du contexte sans DOM
        context = Mock(spec=AuditContext)
        context.dom = None

        result = await test.run(context, None)

        assert result.test_id == "8.7.1"
        assert result.criterion_id == "8.7"
        assert result.status == TestStatus.ERROR
        assert "Le DOM n'est pas disponible" in result.summary
        assert result.tested_elements == 0