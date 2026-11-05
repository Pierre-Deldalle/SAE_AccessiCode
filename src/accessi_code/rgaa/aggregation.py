from __future__ import annotations

from collections import Counter

from accessi_code.models.audit_context import AuditContext
from accessi_code.models.audit_result import (
    AuditResult,
    AuditStatistics,
    CriterionResult,
)
from accessi_code.models.result import (
    TestResult,
    TestStatus,
)


class ResultAggregator:
    """
    Transforme une liste de TestResult en résultat d'audit structuré.
    """

    def aggregate(
        self,
        context: AuditContext,
        results: list[TestResult],
    ) -> AuditResult:
        """
        Regroupe les tests par critère et calcule le statut global.
        """
        grouped: dict[
            str,
            list[TestResult],
        ] = {}

        for result in results:
            grouped.setdefault(
                result.criterion_id,
                [],
            ).append(result)

        criteria: list[CriterionResult] = []

        for (
            criterion_id,
            criterion_tests,
        ) in grouped.items():
            criteria.append(
                self._build_criterion_result(
                    criterion_id,
                    criterion_tests,
                )
            )

        overall_status = self._aggregate_status([criterion.status for criterion in criteria])

        statistics = self._build_statistics(
            criteria,
            results,
        )

        return AuditResult(
            audit_id=context.audit_id,
            status=overall_status,
            criteria=criteria,
            statistics=statistics,
        )

    def _build_criterion_result(
        self,
        criterion_id: str,
        tests: list[TestResult],
    ) -> CriterionResult:
        """
        Construit le résultat agrégé d'un critère.
        """
        status = self._aggregate_status([result.status for result in tests])

        counts = Counter(result.status for result in tests)

        summary = (
            f"{len(tests)} test(s) : "
            f"{counts[TestStatus.PASS]} conforme(s), "
            f"{counts[TestStatus.FAIL]} non conforme(s), "
            f"{counts[TestStatus.NEEDS_REVIEW]} à vérifier, "
            f"{counts[TestStatus.NOT_TESTED]} non testé(s), "
            f"{counts[TestStatus.NOT_APPLICABLE]} non applicable(s), "
            f"{counts[TestStatus.ERROR]} erreur(s)."
        )

        return CriterionResult(
            criterion_id=criterion_id,
            status=status,
            summary=summary,
            tests=list(tests),
        )

    @staticmethod
    def _aggregate_status(
        statuses: list[TestStatus],
    ) -> TestStatus:
        """
        Calcule le statut agrégé.

        Ordre de priorité :

        FAIL
        ERROR
        NEEDS_REVIEW
        NOT_TESTED
        PASS
        NOT_APPLICABLE

        PASS + NOT_APPLICABLE donne PASS.
        Tous les tests NOT_APPLICABLE donnent NOT_APPLICABLE.
        """
        if not statuses:
            return TestStatus.NOT_TESTED

        if TestStatus.FAIL in statuses:
            return TestStatus.FAIL

        if TestStatus.ERROR in statuses:
            return TestStatus.ERROR

        if TestStatus.NEEDS_REVIEW in statuses:
            return TestStatus.NEEDS_REVIEW

        if TestStatus.NOT_TESTED in statuses:
            return TestStatus.NOT_TESTED

        if TestStatus.PASS in statuses:
            return TestStatus.PASS

        return TestStatus.NOT_APPLICABLE

    @staticmethod
    def _build_statistics(
        criteria: list[CriterionResult],
        results: list[TestResult],
    ) -> AuditStatistics:
        """
        Calcule les statistiques globales de l'audit.
        """
        counts = Counter(result.status for result in results)

        return AuditStatistics(
            total_criteria=len(criteria),
            total_tests=len(results),
            passed_tests=counts[TestStatus.PASS],
            failed_tests=counts[TestStatus.FAIL],
            not_applicable_tests=counts[TestStatus.NOT_APPLICABLE],
            not_tested_tests=counts[TestStatus.NOT_TESTED],
            needs_review_tests=counts[TestStatus.NEEDS_REVIEW],
            error_tests=counts[TestStatus.ERROR],
        )
