from __future__ import annotations

import asyncio
from typing import Any

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.result import (
    TestResult,
    TestStatus,
)
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.registry import TestRegistry


class TestRunner:
    """
    Exécute les tests RGAA enregistrés.

    Le runner est responsable :
    - de la vérification des capabilities ;
    - de l'exécution des tests ;
    - de l'isolation des erreurs ;
    - de la validation des résultats.

    Il ne contient aucune logique RGAA.
    """

    def __init__(
        self,
        registry: TestRegistry,
        services: Any | None = None,
    ):
        self.registry = registry
        self.services = services

    async def run_all(
        self,
        context: AuditContext,
    ) -> list[TestResult]:
        """
        Exécute tous les tests du registre dans leur ordre d'enregistrement.
        """
        results: list[TestResult] = []

        for test in self.registry:
            result = await self._run_test(
                test,
                context,
            )

            results.append(result)

        return results

    async def _run_test(
        self,
        test: RGAATest,
        context: AuditContext,
    ) -> TestResult:
        """
        Exécute un seul test de manière sécurisée.
        """
        missing_capabilities = self._get_missing_capabilities(
            test,
            context,
        )

        if missing_capabilities:
            return self._build_not_tested_result(
                test,
                missing_capabilities,
            )

        try:
            result = await test.run(
                context,
                self.services,
            )

        except asyncio.CancelledError:
            # Une annulation explicite de la tâche ne doit pas être
            # transformée en simple erreur de test.
            raise

        except Exception as error:
            return self._build_error_result(
                test,
                error,
            )

        validation_error = self._validate_result(
            test,
            result,
        )

        if validation_error is not None:
            return self._build_error_result(
                test,
                validation_error,
            )

        return result

    @staticmethod
    def _get_missing_capabilities(
        test: RGAATest,
        context: AuditContext,
    ) -> set:
        """
        Retourne les capabilities obligatoires absentes du contexte.
        """
        available = context.get_capabilities()

        required = set(test.required_capabilities)

        return required - available

    @staticmethod
    def _build_not_tested_result(
        test: RGAATest,
        missing_capabilities: set,
    ) -> TestResult:
        """
        Produit un résultat NOT_TESTED lorsqu'une donnée indispensable manque.
        """
        missing = sorted(capability.value for capability in missing_capabilities)

        return TestResult(
            test_id=test.test_id,
            criterion_id=test.criterion_id,
            status=TestStatus.NOT_TESTED,
            summary=("Le test n'a pas été exécuté car certaines données nécessaires sont indisponibles."),
            tested_elements=0,
            metadata={
                "missing_capabilities": (missing),
            },
        )

    @staticmethod
    def _build_error_result(
        test: RGAATest,
        error: Exception,
    ) -> TestResult:
        """
        Transforme une erreur individuelle en TestResult.ERROR.

        L'audit global peut ainsi continuer avec les tests suivants.
        """
        return TestResult(
            test_id=test.test_id,
            criterion_id=test.criterion_id,
            status=TestStatus.ERROR,
            summary=("Une erreur est survenue pendant l'exécution du test."),
            tested_elements=0,
            metadata={
                "error_type": (type(error).__name__),
                "error": str(error),
            },
        )

    @staticmethod
    def _validate_result(
        test: RGAATest,
        result: object,
    ) -> Exception | None:
        """
        Vérifie que le résultat respecte le contrat du moteur.
        """
        if not isinstance(
            result,
            TestResult,
        ):
            return TypeError("Le test doit retourner une instance de TestResult.")

        if result.test_id != test.test_id:
            return ValueError("Le test a retourné un test_id différent de celui déclaré dans la classe.")

        if result.criterion_id != test.criterion_id:
            return ValueError("Le test a retourné un criterion_id différent de celui déclaré dans la classe.")

        return None
