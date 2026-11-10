from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_9 import Test891


@pytest.mark.unit
class TestTest891:
    """Tests unitaires pour le test 8.9.1."""

    def test_test_id_and_criterion_id(self) -> None:
        """Vérifie que les identifiants du test sont corrects."""
        test = Test891()
        assert test.test_id == "8.9.1"
        assert test.criterion_id == "8.9"

    def test_required_capabilities(self) -> None:
        """Vérifie que les capacités requises sont correctement déclarées."""
        test = Test891()
        assert test.required_capabilities == frozenset({Capability.DOM})

    @pytest.mark.asyncio
    async def test_run_no_presentation_violations(self) -> None:
        """Test du cas où aucune violation d'utilisation sémantique à des fins de présentation n'est détectée."""
        test = Test891()

        # Mock du contexte
        context = Mock(spec=AuditContext)
        context.dom = Mock()
        context.html_source = "<html><body><h1>Titre</h1><p>Paragraphe</p></body></html>"

        # Mock du service d'analyse retournant aucune violation
        services = Mock()
        mock_analyzer = AsyncMock()
        mock_analysis_result = Mock()
        mock_analysis_result.has_violations = False
        mock_analysis_result.explanation = "Toutes les balises sémantiques sont utilisées de manière appropriée (pas uniquement pour présentation)."
        mock_analysis_result.total_elements_checked = 5
        mock_analysis_result.findings = []
        mock_analysis_result.confidence = "high"
        mock_analyzer.analyze_semantic_presentation.return_value = mock_analysis_result
        services.semantic_presentation_analyzer = mock_analyzer

        result = await test.run(context, services)

        assert result.test_id == "8.9.1"
        assert result.criterion_id == "8.9"
        assert result.status == TestStatus.PASS
        assert "appropriée" in result.summary
        assert result.tested_elements == 5
        assert result.findings == []
        mock_analyzer.analyze_semantic_presentation.assert_called_once_with(
            context.dom,
            context.html_source
        )

    @pytest.mark.asyncio
    async def test_run_presentation_violations_detected(self) -> None:
        """Test du cas où des violations d'utilisation sémantique à des fins de présentation sont détectées."""
        test = Test891()

        # Mock du contexte
        context = Mock(spec=AuditContext)
        context.dom = Mock()
        context.html_source = "<html><body><h1></h1><div style='height:20px;'></div></body></html>"

        # Mock du service d'analyse retournant des violations
        services = Mock()
        mock_analyzer = AsyncMock()
        mock_analysis_result = Mock()
        mock_analysis_result.has_violations = True
        mock_analysis_result.explanation = "Certaines balises sémantiques sont utilisées uniquement à des fins de présentation sans justification appropriée."
        mock_analysis_result.total_elements_checked = 8
        mock_analysis_result.findings = [
            Mock(
                element="h1[index=0]",
                message="L'élément h1 vide est utilisé uniquement pour créer de l'espace vertical",
                evidence={"type": "empty_header", "suggested_alternative": "Utiliser CSS margin/padding à la place"}
            ),
            Mock(
                element="div[index=1]",
                message="L'élément div avec hauteur fixe est utilisé comme espaceur de présentation",
                evidence={"type": "spacer_div", "suggested_alternative": "Utiliser CSS margin/padding à la place"}
            )
        ]
        mock_analysis_result.confidence = "high"
        mock_analyzer.analyze_semantic_presentation.return_value = mock_analysis_result
        services.semantic_presentation_analyzer = mock_analyzer

        result = await test.run(context, services)

        assert result.test_id == "8.9.1"
        assert result.criterion_id == "8.9"
        assert result.status == TestStatus.FAIL
        assert "sans justification appropriée" in result.summary
        assert result.tested_elements == 8
        assert len(result.findings) == 2
        assert result.findings[0].element == "h1[index=0]"
        assert result.findings[1].element == "div[index=1]"
        mock_analyzer.analyze_semantic_presentation.assert_called_once_with(
            context.dom,
            context.html_source
        )

    @pytest.mark.asyncio
    async def test_run_analyzer_low_confidence(self) -> None:
        """Test du cas où l'analyseur retourne un faible niveau de confiance."""
        test = Test891()

        # Mock du contexte
        context = Mock(spec=AuditContext)
        context.dom = Mock()
        context.html_source = "<html><body>Contenu</body></html>"

        # Mock du service d'analyse retournant faible confiance
        services = Mock()
        mock_analyzer = AsyncMock()
        mock_analysis_result = Mock()
        mock_analysis_result.has_violations = False  # Peu importe, confiance faible prime
        mock_analysis_result.explanation = "L'analyse automatique de l'utilisation sémantique des balises n'est pas suffisamment fiable."
        mock_analysis_result.total_elements_checked = 0
        mock_analysis_result.findings = []
        mock_analysis_result.confidence = "low"
        mock_analyzer.analyze_semantic_presentation.return_value = mock_analysis_result
        services.semantic_presentation_analyzer = mock_analyzer

        result = await test.run(context, services)

        assert result.test_id == "8.9.1"
        assert result.criterion_id == "8.9"
        assert result.status == TestStatus.NEEDS_REVIEW
        assert "pas suffisamment fiable" in result.summary
        assert result.tested_elements == 0
        mock_analyzer.analyze_semantic_presentation.assert_called_once_with(
            context.dom,
            context.html_source
        )

    @pytest.mark.asyncio
    async def test_run_analyzer_exception(self) -> None:
        """Test du cas où l'analyseur lève une exception."""
        test = Test891()

        # Mock du contexte
        context = Mock(spec=AuditContext)
        context.dom = Mock()
        context.html_source = "<html><body>Contenu</body></html>"

        # Mock du service d'analyse qui lève une exception
        services = Mock()
        mock_analyzer = AsyncMock()
        mock_analyzer.analyze_semantic_presentation.side_effect = Exception("Erreur d'analyse")
        services.semantic_presentation_analyzer = mock_analyzer

        result = await test.run(context, services)

        assert result.test_id == "8.9.1"
        assert result.criterion_id == "8.9"
        assert result.status == TestStatus.ERROR
        assert "L'analyse de l'utilisation sémantique des balises a échoué" in result.summary
        assert result.tested_elements == 0
        assert "Erreur d'analyse" in result.summary
        mock_analyzer.analyze_semantic_presentation.assert_called_once_with(
            context.dom,
            context.html_source
        )

    @pytest.mark.asyncio
    async def test_run_no_semantic_presentation_service(self) -> None:
        """Test du cas où le service d'analyse de présentation sémantique n'est pas disponible."""
        test = Test891()

        # Mock du contexte
        context = Mock(spec=AuditContext)
        context.dom = Mock()
        context.html_source = "<html><body>Contenu</body></html>"

        # Services sans analyseur de présentation sémantique
        services = Mock()
        # S'assurer que l'attribut n'existe pas
        if hasattr(services, 'semantic_presentation_analyzer'):
            delattr(services, 'semantic_presentation_analyzer')

        result = await test.run(context, services)

        assert result.test_id == "8.9.1"
        assert result.criterion_id == "8.9"
        assert result.status == TestStatus.NOT_TESTED
        assert "non disponible" in result.summary.lower()
        assert result.tested_elements == 0

    @pytest.mark.asyncio
    async def test_run_no_services_provided(self) -> None:
        """Test du cas où aucun service n'est fourni."""
        test = Test891()

        # Mock du contexte
        context = Mock(spec=AuditContext)
        context.dom = Mock()
        context.html_source = "<html><body>Contenu</body></html>"

        result = await test.run(context, None)

        assert result.test_id == "8.9.1"
        assert result.criterion_id == "8.9"
        assert result.status == TestStatus.NOT_TESTED
        assert "non disponible" in result.summary.lower()
        assert result.tested_elements == 0

    @pytest.mark.asyncio
    async def test_run_dom_not_available(self) -> None:
        """Test du cas où le DOM n'est pas disponible."""
        test = Test891()

        # Mock du contexte sans DOM
        context = Mock(spec=AuditContext)
        context.dom = None

        result = await test.run(context, None)

        assert result.test_id == "8.9.1"
        assert result.criterion_id == "8.9"
        assert result.status == TestStatus.ERROR
        assert "Le DOM n'est pas disponible" in result.summary
        assert result.tested_elements == 0