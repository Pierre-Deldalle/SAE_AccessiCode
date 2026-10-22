"""Tests unitaires du critère RGAA 8.10 (8.10.1 et 8.10.2)."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestStatus
from accessi_code.rgaa.tests.theme_08_mandatory.criterion_8_10 import (
    Test8101,
    Test8102,
)


def _context(*, dom_available: bool = True) -> Mock:
    """Construit un AuditContext simulé sans lancer le moteur d'audit."""
    context = Mock(spec=AuditContext)
    context.dom = Mock() if dom_available else None
    context.html_source = "<html><body>Contenu</body></html>"
    return context


def _services(
    analyzer_name: str, method_name: str, analysis: Mock
) -> tuple[Mock, AsyncMock]:
    """Construit un service IA asynchrone entièrement simulé."""
    services = Mock()
    analyzer = Mock()
    method = AsyncMock(return_value=analysis)
    setattr(analyzer, method_name, method)
    setattr(services, analyzer_name, analyzer)
    return services, method


def _presence_analysis(
    *,
    missing_dir_count: int | None = 0,
    total_rtl_segments_checked: int = 3,
    confidence: str = "high",
    explanation: str = "Tous les segments RTL possèdent un attribut dir.",
    findings: list[dict[str, object]] | None = None,
) -> Mock:
    return Mock(
        missing_dir_count=missing_dir_count,
        total_rtl_segments_checked=total_rtl_segments_checked,
        confidence=confidence,
        explanation=explanation,
        findings=findings if findings is not None else [],
        metadata={},
    )


def _validity_analysis(
    *,
    has_errors: bool | None = False,
    total_dir_attributes_checked: int = 4,
    confidence: str = "high",
    explanation: str = "Tous les attributs dir sont valides et pertinents.",
    findings: list[dict[str, object]] | None = None,
) -> Mock:
    return Mock(
        has_errors=has_errors,
        total_dir_attributes_checked=total_dir_attributes_checked,
        confidence=confidence,
        explanation=explanation,
        findings=findings if findings is not None else [],
        metadata={},
    )


@pytest.mark.unit
class TestTest8101:
    """Tests unitaires de la présence de dir (8.10.1)."""

    def test_test_id_and_criterion_id(self) -> None:
        test = Test8101()
        assert test.test_id == "8.10.1"
        assert test.criterion_id == "8.10"

    def test_required_capabilities(self) -> None:
        assert Test8101.required_capabilities == frozenset({Capability.DOM})

    @pytest.mark.asyncio
    async def test_run_all_rtl_segments_have_dir_attribute(self) -> None:
        context = _context()
        services, method = _services(
            "text_direction_analyzer", "analyze_text_direction_presence",
            _presence_analysis(),
        )
        result = await Test8101().run(context, services)
        assert result.status == TestStatus.PASS
        assert result.tested_elements == 3
        assert result.findings == []
        method.assert_awaited_once_with(context.dom, context.html_source)

    @pytest.mark.asyncio
    async def test_run_some_rtl_segments_missing_dir_attribute(self) -> None:
        context = _context()
        findings = [
            {"element": "span[index=2]", "message": "Attribut dir manquant.",
             "evidence": {"text": "مرحبا"}},
            {"element": "div[index=4]", "message": "Attribut dir manquant.",
             "evidence": {"text": "שלום"}},
        ]
        services, method = _services(
            "text_direction_analyzer", "analyze_text_direction_presence",
            _presence_analysis(
                missing_dir_count=2,
                total_rtl_segments_checked=5,
                explanation="2 segments RTL manquent d'attribut dir.",
                findings=findings,
            ),
        )
        result = await Test8101().run(context, services)
        assert result.status == TestStatus.FAIL
        assert result.tested_elements == 5
        assert len(result.findings) == 2
        assert result.findings[0].element == "span[index=2]"
        assert result.findings[1].element == "div[index=4]"
        method.assert_awaited_once_with(context.dom, context.html_source)

    @pytest.mark.asyncio
    async def test_run_analyzer_low_confidence(self) -> None:
        services, _ = _services(
            "text_direction_analyzer", "analyze_text_direction_presence",
            _presence_analysis(confidence="low", missing_dir_count=2),
        )
        result = await Test8101().run(_context(), services)
        assert result.status == TestStatus.NEEDS_REVIEW
        assert result.tested_elements == 0

    @pytest.mark.asyncio
    async def test_run_analyzer_no_conclusion(self) -> None:
        services, _ = _services(
            "text_direction_analyzer", "analyze_text_direction_presence",
            _presence_analysis(missing_dir_count=None),
        )
        result = await Test8101().run(_context(), services)
        assert result.status == TestStatus.NEEDS_REVIEW

    @pytest.mark.asyncio
    async def test_run_no_rtl_segment(self) -> None:
        services, _ = _services(
            "text_direction_analyzer", "analyze_text_direction_presence",
            _presence_analysis(total_rtl_segments_checked=0),
        )
        result = await Test8101().run(_context(), services)
        assert result.status == TestStatus.NOT_APPLICABLE
        assert result.tested_elements == 0

    @pytest.mark.asyncio
    async def test_run_analyzer_exception(self) -> None:
        services, method = _services(
            "text_direction_analyzer", "analyze_text_direction_presence",
            _presence_analysis(),
        )
        method.side_effect = RuntimeError("Erreur d'analyse")
        result = await Test8101().run(_context(), services)
        assert result.status == TestStatus.ERROR
        assert "Erreur d'analyse" in result.summary
        assert result.tested_elements == 0

    @pytest.mark.asyncio
    async def test_run_invalid_response(self) -> None:
        services, method = _services(
            "text_direction_analyzer", "analyze_text_direction_presence",
            _presence_analysis(),
        )
        method.return_value = None
        result = await Test8101().run(_context(), services)
        assert result.status == TestStatus.ERROR

    @pytest.mark.asyncio
    async def test_run_no_analyzer(self) -> None:
        services = Mock()
        services.text_direction_analyzer = None
        result = await Test8101().run(_context(), services)
        assert result.status == TestStatus.NEEDS_REVIEW
        assert result.tested_elements == 0

    @pytest.mark.asyncio
    async def test_run_no_services(self) -> None:
        result = await Test8101().run(_context(), None)
        assert result.status == TestStatus.NEEDS_REVIEW

    @pytest.mark.asyncio
    async def test_run_dom_not_available(self) -> None:
        result = await Test8101().run(_context(dom_available=False))
        assert result.status == TestStatus.ERROR
        assert "DOM" in result.summary


@pytest.mark.unit
class TestTest8102:
    """Tests unitaires de la validité et pertinence de dir (8.10.2)."""

    def test_test_id_and_criterion_id(self) -> None:
        test = Test8102()
        assert test.test_id == "8.10.2"
        assert test.criterion_id == "8.10"

    def test_required_capabilities(self) -> None:
        assert Test8102.required_capabilities == frozenset({Capability.DOM})

    @pytest.mark.asyncio
    async def test_run_all_dir_attributes_valid_and_relevant(self) -> None:
        context = _context()
        services, method = _services(
            "text_direction_validity_analyzer", "analyze_text_direction_validity",
            _validity_analysis(),
        )
        result = await Test8102().run(context, services)
        assert result.status == TestStatus.PASS
        assert result.tested_elements == 4
        assert result.findings == []
        method.assert_awaited_once_with(context.dom, context.html_source)

    @pytest.mark.asyncio
    async def test_run_some_dir_attributes_invalid_or_irrelevant(self) -> None:
        context = _context()
        findings = [
            {"element": "span[index=1]", "message": "Valeur dir invalide.",
             "evidence": {"dir_value": "xyz"}},
            {"element": "div[index=3]", "message": "Direction non pertinente.",
             "evidence": {"dir_value": "ltr"}},
        ]
        services, method = _services(
            "text_direction_validity_analyzer", "analyze_text_direction_validity",
            _validity_analysis(
                has_errors=True,
                total_dir_attributes_checked=6,
                explanation="2 attributs dir sont invalides ou non pertinents.",
                findings=findings,
            ),
        )
        result = await Test8102().run(context, services)
        assert result.status == TestStatus.FAIL
        assert result.tested_elements == 6
        assert len(result.findings) == 2
        assert result.findings[0].element == "span[index=1]"
        assert result.findings[1].element == "div[index=3]"
        method.assert_awaited_once_with(context.dom, context.html_source)

    @pytest.mark.asyncio
    async def test_run_analyzer_low_confidence(self) -> None:
        services, _ = _services(
            "text_direction_validity_analyzer", "analyze_text_direction_validity",
            _validity_analysis(confidence="low", has_errors=True),
        )
        result = await Test8102().run(_context(), services)
        assert result.status == TestStatus.NEEDS_REVIEW
        assert result.tested_elements == 0

    @pytest.mark.asyncio
    async def test_run_analyzer_no_conclusion(self) -> None:
        services, _ = _services(
            "text_direction_validity_analyzer", "analyze_text_direction_validity",
            _validity_analysis(has_errors=None),
        )
        result = await Test8102().run(_context(), services)
        assert result.status == TestStatus.NEEDS_REVIEW

    @pytest.mark.asyncio
    async def test_run_no_dir_attribute(self) -> None:
        services, _ = _services(
            "text_direction_validity_analyzer", "analyze_text_direction_validity",
            _validity_analysis(total_dir_attributes_checked=0),
        )
        result = await Test8102().run(_context(), services)
        assert result.status == TestStatus.NOT_APPLICABLE
        assert result.tested_elements == 0

    @pytest.mark.asyncio
    async def test_run_analyzer_exception(self) -> None:
        services, method = _services(
            "text_direction_validity_analyzer", "analyze_text_direction_validity",
            _validity_analysis(),
        )
        method.side_effect = RuntimeError("Erreur d'analyse")
        result = await Test8102().run(_context(), services)
        assert result.status == TestStatus.ERROR
        assert "Erreur d'analyse" in result.summary
        assert result.tested_elements == 0

    @pytest.mark.asyncio
    async def test_run_invalid_response(self) -> None:
        services, method = _services(
            "text_direction_validity_analyzer", "analyze_text_direction_validity",
            _validity_analysis(),
        )
        method.return_value = None
        result = await Test8102().run(_context(), services)
        assert result.status == TestStatus.ERROR

    @pytest.mark.asyncio
    async def test_run_no_analyzer(self) -> None:
        services = Mock()
        services.text_direction_validity_analyzer = None
        result = await Test8102().run(_context(), services)
        assert result.status == TestStatus.NEEDS_REVIEW
        assert result.tested_elements == 0

    @pytest.mark.asyncio
    async def test_run_no_services(self) -> None:
        result = await Test8102().run(_context(), None)
        assert result.status == TestStatus.NEEDS_REVIEW

    @pytest.mark.asyncio
    async def test_run_dom_not_available(self) -> None:
        result = await Test8102().run(_context(dom_available=False))
        assert result.status == TestStatus.ERROR
        assert "DOM" in result.summary
