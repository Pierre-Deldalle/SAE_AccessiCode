from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult


class RGAATest(ABC):
    """
    Classe de base de tous les tests RGAA.

    Chaque implémentation doit :
    - déclarer son identifiant de test ;
    - déclarer son critère parent ;
    - déclarer les données nécessaires ;
    - retourner un TestResult.
    """

    test_id: ClassVar[str]
    criterion_id: ClassVar[str]

    required_capabilities: ClassVar[frozenset[Capability]] = frozenset()

    optional_capabilities: ClassVar[frozenset[Capability]] = frozenset()

    @abstractmethod
    async def run(
        self,
        context: AuditContext,
        services: Any | None = None,
    ) -> TestResult:
        """
        Exécute le test RGAA.

        Le contexte doit être considéré comme une donnée en lecture seule.
        """
        raise NotImplementedError
