from __future__ import annotations

from accessi_code.models.audit_context import (
    AuditContext,
)
from accessi_code.models.audit_result import (
    AuditResult,
)
from accessi_code.rgaa.aggregation import (
    ResultAggregator,
)
from accessi_code.rgaa.registry import (
    TestRegistry,
)
from accessi_code.rgaa.runner import (
    TestRunner,
)
from accessi_code.service.audit_services import (
    AuditServices,
)


class AuditService:
    """
    Point d'entrée principal du moteur d'audit.

    Le service :
    1. reçoit un AuditContext déjà construit ;
    2. exécute les tests ;
    3. agrège les résultats ;
    4. retourne un AuditResult.
    """

    def __init__(
        self,
        registry: TestRegistry,
        services: AuditServices | None = None,
    ):
        self.registry = registry

        self.services = services if services is not None else AuditServices()

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
        """
        test_results = await self.runner.run_all(context)

        return self.aggregator.aggregate(
            context,
            test_results,
        )
