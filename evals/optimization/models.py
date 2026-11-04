from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from evals.models.comparison import PromptComparison
from evals.models.report import EvalReport


@dataclass(frozen=True, slots=True)
class GeneratedPromptCandidate:
    name: str
    template: str
    rationale: str


@dataclass(slots=True)
class CandidateEvaluation:
    candidate: GeneratedPromptCandidate
    prompt_path: Path

    train_report: EvalReport
    train_comparison: PromptComparison

    validation_report: EvalReport
    validation_comparison: PromptComparison


@dataclass(slots=True)
class PromptOptimizationResult:
    task_name: str
    run_id: str
    output_directory: Path

    baseline_train_report: EvalReport
    baseline_validation_report: EvalReport

    candidates: list[CandidateEvaluation]

@dataclass(frozen=True, slots=True)
class CandidateRejection:
    candidate_name: str
    reason: str