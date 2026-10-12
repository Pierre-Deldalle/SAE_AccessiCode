from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


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

    score: float

    error_type: str | None = None
    error_message: str | None = None