"""Service principal d'exécution des audits AccessiCode."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.audit_result import AuditResult
from accessi_code.rgaa.aggregation import ResultAggregator
from accessi_code.rgaa.registry import TestRegistry
from accessi_code.rgaa.runner import TestRunner
from accessi_code.service.audit_services import AuditServices

if TYPE_CHECKING:
    from accessi_code.input.context_enricher import (
        ContextEnricher,
        ContextEnrichmentReport,
    )


logger = logging.getLogger(__name__)


class AuditService:
    """
    Point d'entrée principal du moteur d'audit.

    Le service :
    1. reçoit un AuditContext déjà construit ;
    2. enrichit facultativement le contexte via Playwright ;
    3. exécute les tests RGAA ;
    4. agrège les résultats ;
    5. retourne un AuditResult.

    L'enrichissement n'alimente pas encore les échantillons de contraste.
    Il prépare uniquement des observations techniques.
    """

    def __init__(
        self,
        registry: TestRegistry,
        services: AuditServices | None = None,
        context_enricher: ContextEnricher | None = None,
    ) -> None:
        self.registry = registry

        self.services = services if services is not None else AuditServices()

        self.context_enricher = context_enricher
        self.last_enrichment_report: ContextEnrichmentReport | None = None

        self.runner = TestRunner(
            registry=self.registry,
            services=self.services,
        )

        self.aggregator = ResultAggregator()

    async def audit(
        self,
        context: AuditContext,
    ) -> AuditResult:
        """
        Exécute un audit complet.

        L'enrichissement Playwright, lorsqu'il est configuré, est
        exécuté avant les tests RGAA. Une erreur d'enrichissement
        est journalisée sans interrompre l'audit.
        """

        # Éviter de conserver le rapport d'un audit précédent.
        self.last_enrichment_report = None

        if self.context_enricher is not None:
            try:
                report = await self.context_enricher.enrich(context)

                self.last_enrichment_report = report

                if report.error is not None:
                    logger.warning(
                        "Enrichissement du contexte incomplet : %s",
                        report.error,
                    )
                else:
                    logger.info(
                        "Styles calculés : %s observations, "
                        "%s candidates, %s à vérifier.",
                        report.total,
                        report.usable_count,
                        report.review_count,
                    )

            except Exception:
                logger.exception(
                    "Erreur inattendue pendant "
                    "l'enrichissement du contexte."
                )

        test_results = await self.runner.run_all(context)

        return self.aggregator.aggregate(
            context,
            test_results,
        )   