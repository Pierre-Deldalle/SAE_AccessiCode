from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from accessi_code.ai.schemas import AIConfidence


class EvalStatus(str, Enum):
    """
    Statut d'un cas d'évaluation IA.

    Ces statuts sont volontairement différents des statuts RGAA.
    """

    CORRECT = "correct"
    INCORRECT = "incorrect"
    ERROR = "error"


@dataclass(slots=True)
class EvalResult:
    """
    Résultat de l'exécution d'un cas d'évaluation IA.
    """

    task_name: str
    case_id: str
    status: EvalStatus

    expected: dict[str, Any]
    actual: dict[str, Any] | None

    expected_decision: bool | None
    actual_decision: bool | None

    confidence: AIConfidence | None

    decision_score: float
    decision_issues: tuple[str, ...] = ()

    integrity_score: float | None = None
    integrity_issues: tuple[str, ...] = ()

    error_type: str | None = None
    error_message: str | None = None
