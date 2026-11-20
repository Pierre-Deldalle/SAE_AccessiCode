"""Tests unitaires du service principal d'audit AccessiCode."""

from unittest.mock import AsyncMock

import pytest

from accessi_code.input.context_enricher import (
    ContextEnrichmentReport,
)
from accessi_code.input.extractors.computed_styles import (
    TextStyleObservation,
)
from accessi_code.models.audit_context import AuditContext
from accessi_code.models.audit_result import AuditResult
from accessi_code.models.result import TestResult as Result
from accessi_code.models.result import TestStatus as Status
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.registry import TestRegistry as Registry
from accessi_code.service.audit_service import AuditService


class PassingTest(RGAATest):
    test_id = "fake.1"
    criterion_id = "fake"

    async def run(
        self,
        context,
        services=None,
    ):
        return Result(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=Status.PASS,
            summary="OK",
        )


class FailingTest(RGAATest):
    test_id = "fake.2"
    criterion_id = "fake"

    async def run(
        self,
        context,
        services=None,
    ):
        return Result(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=Status.FAIL,
            summary="Échec volontaire.",
        )


class OrderedTest(RGAATest):
    """Test fictif permettant de contrôler l'ordre des opérations."""

    test_id = "fake.order"
    criterion_id = "fake"

    def __init__(self, events: list[str]) -> None:
        self.events = events

    async def run(
        self,
        context,
        services=None,
    ):
        self.events.append("test")

        return Result(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=Status.PASS,
            summary="Test exécuté.",
        )


def make_context(tmp_path):
    """Construit un contexte minimal pour les tests."""

    return AuditContext(
        audit_id="audit-test",
        workspace_path=tmp_path,
    )


def make_observation() -> TextStyleObservation:
    """Construit une observation CSS fictive."""

    return TextStyleObservation(
        element="html > body > p",
        text="Texte de test",
        color="rgb(0, 0, 0)",
        background_color="rgb(255, 255, 255)",
        font_size_px=16.0,
        font_weight=400,
    )


@pytest.mark.asyncio
async def test_audit_service_runs_and_aggregates(tmp_path):
    """Le fonctionnement historique du service reste inchangé."""

    registry = Registry(
        [
            PassingTest(),
            FailingTest(),
        ]
    )

    service = AuditService(registry=registry)
    context = make_context(tmp_path)

    result = await service.audit(context)

    assert isinstance(result, AuditResult)
    assert result.audit_id == "audit-test"
    assert result.status == Status.FAIL
    assert result.statistics.total_tests == 2
    assert result.statistics.passed_tests == 1
    assert result.statistics.failed_tests == 1
    assert len(result.criteria) == 1

    # Aucun enrichisseur n'a été fourni au service.
    assert service.last_enrichment_report is None


@pytest.mark.asyncio
async def test_audit_service_without_enricher(tmp_path):
    """Le service fonctionne normalement sans Playwright."""

    service = AuditService(
        registry=Registry([PassingTest()]),
    )

    result = await service.audit(make_context(tmp_path))

    assert result.status == Status.PASS
    assert result.statistics.total_tests == 1
    assert service.last_enrichment_report is None


@pytest.mark.asyncio
async def test_audit_service_enriches_before_running_tests(tmp_path):
    """L'enrichissement doit avoir lieu avant les tests RGAA."""

    events: list[str] = []

    async def fake_enrich(context):
        events.append("enrichissement")

        return ContextEnrichmentReport(
            observations=[make_observation()],
            usable_observations=[make_observation()],
        )

    enricher = AsyncMock()
    enricher.enrich.side_effect = fake_enrich

    service = AuditService(
        registry=Registry([OrderedTest(events)]),
        context_enricher=enricher,
    )

    context = make_context(tmp_path)
    result = await service.audit(context)

    assert events == ["enrichissement", "test"]
    enricher.enrich.assert_awaited_once_with(context)

    assert result.status == Status.PASS
    assert service.last_enrichment_report is not None
    assert service.last_enrichment_report.total == 1
    assert service.last_enrichment_report.usable_count == 1


@pytest.mark.asyncio
async def test_audit_service_handles_enrichment_report_error(tmp_path):
    """Une erreur signalée dans le rapport ne bloque pas l'audit."""

    enricher = AsyncMock()
    enricher.enrich.return_value = ContextEnrichmentReport(
        error="Chromium indisponible",
    )

    service = AuditService(
        registry=Registry([PassingTest()]),
        context_enricher=enricher,
    )

    result = await service.audit(make_context(tmp_path))

    assert result.status == Status.PASS
    assert result.statistics.passed_tests == 1

    assert service.last_enrichment_report is not None
    assert service.last_enrichment_report.error == "Chromium indisponible"


@pytest.mark.asyncio
async def test_audit_service_handles_unexpected_enrichment_exception(
    tmp_path,
):
    """Une exception Playwright ne doit pas interrompre les tests RGAA."""

    enricher = AsyncMock()
    enricher.enrich.side_effect = RuntimeError("Erreur de démarrage du navigateur")

    service = AuditService(
        registry=Registry([PassingTest()]),
        context_enricher=enricher,
    )

    result = await service.audit(make_context(tmp_path))

    assert result.status == Status.PASS
    assert result.statistics.total_tests == 1
    assert service.last_enrichment_report is None


@pytest.mark.asyncio
async def test_audit_service_resets_previous_enrichment_report(tmp_path):
    """Un nouvel audit ne doit pas conserver le rapport précédent."""

    enricher = AsyncMock()

    enricher.enrich.side_effect = [
        ContextEnrichmentReport(
            observations=[make_observation()],
        ),
        ContextEnrichmentReport(
            error="Deuxième extraction impossible",
        ),
    ]

    service = AuditService(
        registry=Registry([PassingTest()]),
        context_enricher=enricher,
    )

    first_result = await service.audit(make_context(tmp_path))

    assert first_result.status == Status.PASS
    assert service.last_enrichment_report is not None
    assert service.last_enrichment_report.total == 1

    second_result = await service.audit(make_context(tmp_path))

    assert second_result.status == Status.PASS
    assert service.last_enrichment_report is not None
    assert service.last_enrichment_report.total == 0
    assert service.last_enrichment_report.error == "Deuxième extraction impossible"

    assert enricher.enrich.await_count == 2


@pytest.mark.asyncio
async def test_audit_service_does_not_generate_contrast_samples(tmp_path):
    """Les observations Playwright ne deviennent pas encore des verdicts RGAA."""

    enricher = AsyncMock()
    enricher.enrich.return_value = ContextEnrichmentReport(
        observations=[make_observation()],
        usable_observations=[make_observation()],
    )

    service = AuditService(
        registry=Registry([PassingTest()]),
        context_enricher=enricher,
    )

    context = make_context(tmp_path)
    await service.audit(context)

    assert context.text_contrast_samples == []
    assert context.non_text_contrast_samples == []
