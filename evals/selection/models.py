from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RankedPromptCandidate:
    rank: int
    name: str
    prompt_path: Path

    eligible: bool
    reasons: tuple[str, ...]

    validation_accuracy: float
    validation_accuracy_delta: float

    validation_score: float
    validation_score_delta: float

    validation_critical_errors: int
    validation_critical_errors_delta: int

    validation_improvements: int
    validation_regressions: int

    train_accuracy: float
    train_accuracy_delta: float

    train_score: float
    train_score_delta: float

    train_regressions: int


@dataclass(frozen=True, slots=True)
class PromptSelectionResult:
    recommended_candidate: (
        RankedPromptCandidate | None
    )

    keep_production: bool

    ranking: tuple[
        RankedPromptCandidate,
        ...
    ]

    summary: str