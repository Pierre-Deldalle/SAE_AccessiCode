from __future__ import annotations

from dataclasses import dataclass, field

from accessi_code.models.result import (
    TestResult,
    TestStatus,
)


@dataclass(slots=True)
class CriterionResult:
    """
    Résultat agrégé d'un critère RGAA.

    Un critère peut être constitué de plusieurs tests.
    """

    criterion_id: str
    status: TestStatus
    summary: str

    tests: list[TestResult] = field(default_factory=list)


@dataclass(slots=True)
class AuditStatistics:
    """
    Statistiques globales de l'audit.
    """

    total_criteria: int = 0
    total_tests: int = 0

    passed_tests: int = 0
    failed_tests: int = 0

    not_applicable_tests: int = 0
    not_tested_tests: int = 0

    needs_review_tests: int = 0
    error_tests: int = 0


@dataclass(slots=True)
class AuditResult:
    """
    Résultat final produit par le moteur d'audit.

    Cet objet constitue la sortie du moteur et pourra ensuite être
    transformé en JSON, tableau Gradio, rapport HTML, etc.
    """

    audit_id: str

    status: TestStatus

    criteria: list[CriterionResult] = field(default_factory=list)

    statistics: AuditStatistics = field(default_factory=AuditStatistics)
