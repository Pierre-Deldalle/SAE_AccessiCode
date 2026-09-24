from __future__ import annotations

import asyncio

from debug_context import (
    build_debug_context,
)

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.capabilities import Capability
from accessi_code.models.result import TestResult, TestStatus
from accessi_code.rgaa.base import RGAATest
from accessi_code.rgaa.registry import TestRegistry
from accessi_code.service.audit_service import AuditService


class FakeHtmlTest(RGAATest):
    """
    Vérifie que le moteur reçoit correctement le DOM
    construit par l'US 0.0.1.
    """

    test_id = "debug.1"
    criterion_id = "debug"

    required_capabilities = frozenset(
        {
            Capability.DOM,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services=None,
    ) -> TestResult:
        images = context.dom.find_all("img")
        forms = context.dom.find_all("form")
        inputs = context.dom.find_all("input")

        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=TestStatus.PASS,
            summary=(
                f"DOM reçu correctement : {len(images)} image(s), {len(forms)} formulaire(s), {len(inputs)} input(s)."
            ),
            tested_elements=(len(images) + len(forms) + len(inputs)),
        )


class FakeMissingCapabilityTest(RGAATest):
    """
    Vérifie que le moteur retourne automatiquement NOT_TESTED
    lorsqu'une capability obligatoire n'est pas disponible.
    """

    test_id = "debug.2"
    criterion_id = "debug"

    required_capabilities = frozenset(
        {
            Capability.SCREENSHOT,
        }
    )

    async def run(
        self,
        context: AuditContext,
        services=None,
    ) -> TestResult:
        raise AssertionError("Ce test ne devrait jamais être exécuté.")


class FakeCrashingTest(RGAATest):
    """
    Vérifie qu'une exception dans un test devient ERROR
    sans arrêter l'audit.
    """

    test_id = "debug.3"
    criterion_id = "debug"

    async def run(
        self,
        context: AuditContext,
        services=None,
    ) -> TestResult:
        raise RuntimeError("Erreur volontaire pour tester le moteur.")


class FakeSecondPassingTest(RGAATest):
    """
    Vérifie que le moteur continue après un test en erreur.
    """

    test_id = "debug.4"
    criterion_id = "debug"

    async def run(
        self,
        context: AuditContext,
        services=None,
    ) -> TestResult:
        return TestResult(
            test_id=self.test_id,
            criterion_id=self.criterion_id,
            status=TestStatus.PASS,
            summary=("Le moteur a continué après l'erreur."),
        )


async def main() -> None:
    # -------------------------------------------------
    # US 0.0.1 : vrai AuditContext
    # -------------------------------------------------

    context = build_debug_context()

    # -------------------------------------------------
    # US 0.0.3 : moteur de tests
    # -------------------------------------------------

    registry = TestRegistry(
        [
            FakeHtmlTest(),
            FakeMissingCapabilityTest(),
            FakeCrashingTest(),
            FakeSecondPassingTest(),
        ]
    )

    service = AuditService(registry=registry)

    result = await service.audit(context)

    # -------------------------------------------------
    # Affichage
    # -------------------------------------------------

    print()
    print("=== AUDIT CONTEXT ===")
    print(f"Audit ID : {context.audit_id}")
    print(f"Workspace : {context.workspace_path}")
    print(f"HTML : {context.html_path}")

    print()
    print("=== CAPABILITIES ===")

    for capability in sorted(
        context.get_capabilities(),
        key=lambda item: item.value,
    ):
        print(f"- {capability.value}")

    print()
    print("=== RESULTAT GLOBAL ===")
    print(f"Statut : {result.status.value}")

    print()
    print("=== STATISTIQUES ===")
    print(f"Tests              : {result.statistics.total_tests}")
    print(f"Critères           : {result.statistics.total_criteria}")
    print(f"PASS               : {result.statistics.passed_tests}")
    print(f"FAIL               : {result.statistics.failed_tests}")
    print(f"NOT_APPLICABLE     : {result.statistics.not_applicable_tests}")
    print(f"NOT_TESTED         : {result.statistics.not_tested_tests}")
    print(f"NEEDS_REVIEW       : {result.statistics.needs_review_tests}")
    print(f"ERROR              : {result.statistics.error_tests}")

    print()
    print("=== CRITERES ===")

    for criterion in result.criteria:
        print()

        print(f"Critère {criterion.criterion_id} -> {criterion.status.value}")

        for test in criterion.tests:
            print(f"  {test.test_id:<10} {test.status.value:<16} {test.summary}")


if __name__ == "__main__":
    asyncio.run(main())
