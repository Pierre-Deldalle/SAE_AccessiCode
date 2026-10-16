from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from evals.models.result import (
    EvalResult,
    EvalStatus,
)


@dataclass(slots=True)
class EvalReport:
    """
    Synthèse d'une campagne d'évaluation IA.
    """

    task_name: str
    dataset_name: str

    total_cases: int

    correct: int
    incorrect: int
    errors: int

    accuracy: float
    average_decision_score: float

    true_total: int
    true_correct: int

    false_total: int
    false_correct: int

    null_total: int
    null_correct: int

    critical_errors: int
    forced_verdicts: int
    unnecessary_abstentions: int
    unnecessary_low_confidence: int

    integrity_evaluated: int
    average_integrity_score: float
    integrity_problems: int

    integrity_issue_counts: dict[str, int] = field(
        default_factory=dict
    )

    @classmethod
    def from_results(
        cls,
        *,
        task_name: str,
        dataset_name: str,
        results: list[EvalResult],
    ) -> EvalReport:
        total = len(results)

        correct = sum(
            result.status == EvalStatus.CORRECT
            for result in results
        )

        incorrect = sum(
            result.status == EvalStatus.INCORRECT
            for result in results
        )

        errors = sum(
            result.status == EvalStatus.ERROR
            for result in results
        )

        accuracy = (
            correct / total
            if total
            else 0.0
        )

        average_decision_score = (
            sum(
                result.decision_score
                for result in results
            )
            / total
            if total
            else 0.0
        )

        true_results = [
            result
            for result in results
            if result.expected_decision is True
        ]

        false_results = [
            result
            for result in results
            if result.expected_decision is False
        ]

        null_results = [
            result
            for result in results
            if result.expected_decision is None
            and result.status != EvalStatus.ERROR
        ]

        true_correct = cls._count_correct(
            true_results
        )

        false_correct = cls._count_correct(
            false_results
        )

        null_correct = cls._count_correct(
            null_results
        )

        critical_errors = cls._count_issue(
            results,
            "critical_confidence_error",
        )

        forced_verdicts = cls._count_issue(
            results,
            "forced_verdict",
        )

        unnecessary_abstentions = cls._count_issue(
            results,
            "unnecessary_abstention",
        )

        unnecessary_low_confidence = cls._count_issue(
            results,
            "unnecessary_low_confidence",
        )

        integrity_results = [
            result
            for result in results
            if result.integrity_score is not None
        ]

        integrity_evaluated = len(
            integrity_results
        )

        average_integrity_score = (
            sum(
                result.integrity_score
                for result in integrity_results
                if result.integrity_score is not None
            )
            / integrity_evaluated
            if integrity_evaluated
            else 0.0
        )

        integrity_problems = sum(
            bool(result.integrity_issues)
            for result in integrity_results
        )

        integrity_issue_counts: Counter[str] = Counter()

        for result in integrity_results:
            integrity_issue_counts.update(
                result.integrity_issues
            )

        return cls(
            task_name=task_name,
            dataset_name=dataset_name,
            total_cases=total,
            correct=correct,
            incorrect=incorrect,
            errors=errors,
            accuracy=accuracy,
            average_decision_score=average_decision_score,
            true_total=len(true_results),
            true_correct=true_correct,
            false_total=len(false_results),
            false_correct=false_correct,
            null_total=len(null_results),
            null_correct=null_correct,
            critical_errors=critical_errors,
            forced_verdicts=forced_verdicts,
            unnecessary_abstentions=unnecessary_abstentions,
            unnecessary_low_confidence=unnecessary_low_confidence,
            integrity_evaluated=integrity_evaluated,
            average_integrity_score=average_integrity_score,
            integrity_problems=integrity_problems,
            integrity_issue_counts=dict(
                integrity_issue_counts
            ),
        )

    @staticmethod
    def _count_correct(
        results: list[EvalResult],
    ) -> int:
        return sum(
            result.status == EvalStatus.CORRECT
            for result in results
        )

    @staticmethod
    def _count_issue(
        results: list[EvalResult],
        issue: str,
    ) -> int:
        return sum(
            issue in result.decision_issues
            for result in results
        )

    @staticmethod
    def percentage(
        correct: int,
        total: int,
    ) -> float:
        if total == 0:
            return 0.0

        return (
            correct
            / total
            * 100.0
        )
