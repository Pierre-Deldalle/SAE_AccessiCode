from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CaseChange:
    """
    Évolution d'un cas entre le prompt de référence
    et un prompt candidat.
    """

    case_id: str

    baseline_status: str
    candidate_status: str

    baseline_score: float
    candidate_score: float

    score_delta: float


@dataclass(slots=True)
class PromptComparison:
    """
    Comparaison d'un candidat avec le prompt de référence.
    """

    baseline_name: str
    candidate_name: str

    baseline_accuracy: float
    candidate_accuracy: float

    baseline_score: float
    candidate_score: float

    accuracy_delta: float
    score_delta: float

    baseline_critical_errors: int
    candidate_critical_errors: int

    improvements: list[CaseChange] = field(
        default_factory=list
    )

    regressions: list[CaseChange] = field(
        default_factory=list
    )

    score_improvements: list[CaseChange] = field(
        default_factory=list
    )

    score_regressions: list[CaseChange] = field(
        default_factory=list
    )