
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TestStatus(str, Enum):
    # Statuts communs utilisés par tous les tests d'accessibilité.
    PASS = "pass"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"
    NOT_TESTED = "not_tested"
    INCONCLUSIVE = "inconclusive"


@dataclass
class Finding:
    """Un problème ou une observation concernant un élément."""

    # L'élément identifie la cible concernée par l'observation.
    element: str
    message: str
    recommendation: str | None = None
    # Les preuves facilitent l'explication et la vérification du résultat.
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Résultat d'un test RGAA."""

    # Les identifiants permettent de relier le résultat au test et au critère.
    test_id: str
    criterion_id: str
    status: TestStatus
    summary: str
    findings: list[Finding] = field(default_factory=list)
    tested_elements: int = 0
    # Les métadonnées accueillent les détails propres à chaque implémentation.
    metadata: dict[str, Any] = field(default_factory=dict)