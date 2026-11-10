from __future__ import annotations

from typing import Any

from evals.models.case import EvalCase
from evals.models.report import EvalReport
from evals.models.result import (
    EvalResult,
    EvalStatus,
)


class OptimizationContextBuilder:
    def __init__(
        self,
        *,
        max_problem_cases: int = 12,
        max_anchor_cases: int = 3,
    ):
        if max_problem_cases < 1:
            raise ValueError(
                "max_problem_cases doit être supérieur ou égal à 1."
            )

        if max_anchor_cases < 0:
            raise ValueError(
                "max_anchor_cases doit être supérieur ou égal à 0."
            )

        self.max_problem_cases = (
            max_problem_cases
        )

        self.max_anchor_cases = (
            max_anchor_cases
        )

    def build(
        self,
        *,
        task_name: str,
        production_prompt: str,
        cases: list[EvalCase],
        results: list[EvalResult],
        report: EvalReport,
    ) -> dict[str, Any]:
        cases_by_id = {
            case.id: case
            for case in cases
        }

        usable_results = [
            result
            for result in results
            if (
                result.status
                is not EvalStatus.ERROR
                and result.case_id
                in cases_by_id
            )
        ]

        problematic_results = [
            result
            for result in usable_results
            if (
                result.status
                is EvalStatus.INCORRECT
                or bool(
                    result.decision_issues
                )
                or bool(
                    result.integrity_issues
                )
            )
        ]

        problematic_results.sort(
            key=self._problem_priority
        )

        protected_results = [
            result
            for result in usable_results
            if (
                result.status
                is EvalStatus.CORRECT
                and result.decision_score
                == 100.0
                and not result.decision_issues
                and not result.integrity_issues
            )
        ]

        problematic_cases = [
            self._serialize_case(
                cases_by_id[result.case_id],
                result,
            )
            for result in (
                problematic_results[
                    : self.max_problem_cases
                ]
            )
        ]

        protected_examples = [
            self._serialize_case(
                cases_by_id[result.case_id],
                result,
            )
            for result in (
                protected_results[
                    : self.max_anchor_cases
                ]
            )
        ]

        return {
            "task": task_name,
            "production_prompt": (
                production_prompt
            ),
            "baseline_metrics": {
                "accuracy": (
                    report.accuracy
                ),
                "average_decision_score": (
                    report.average_decision_score
                ),
                "critical_errors": (
                    report.critical_errors
                ),
                "forced_verdicts": (
                    report.forced_verdicts
                ),
                "unnecessary_abstentions": (
                    report.unnecessary_abstentions
                ),
                "unnecessary_low_confidence": (
                    report.unnecessary_low_confidence
                ),
                "true_accuracy": (
                    self._ratio(
                        report.true_correct,
                        report.true_total,
                    )
                ),
                "false_accuracy": (
                    self._ratio(
                        report.false_correct,
                        report.false_total,
                    )
                ),
                "null_accuracy": (
                    self._ratio(
                        report.null_correct,
                        report.null_total,
                    )
                ),
            },
            "problematic_cases": (
                problematic_cases
            ),
            "protected_examples": (
                protected_examples
            ),
        }

    @staticmethod
    def _problem_priority(
        result: EvalResult,
    ) -> tuple[int, str]:
        if (
            "critical_confidence_error"
            in result.decision_issues
        ):
            priority = 0

        elif (
            result.status
            is EvalStatus.INCORRECT
        ):
            priority = 1

        elif result.decision_issues:
            priority = 2

        elif result.integrity_issues:
            priority = 3

        else:
            priority = 4

        return (
            priority,
            result.case_id,
        )

    @staticmethod
    def _serialize_case(
        case: EvalCase,
        result: EvalResult,
    ) -> dict[str, Any]:
        serialized: dict[str, Any] = {
            "input": (
                OptimizationContextBuilder
                ._sanitize_input(
                    case.input_data
                )
            ),
            "expected": (
                result.expected_decision
            ),
            "actual": (
                result.actual_decision
            ),
            "confidence": (
                result.confidence
            ),
            "decision_score": (
                result.decision_score
            ),
            "decision_issues": list(
                result.decision_issues
            ),
            "integrity_issues": list(
                result.integrity_issues
            ),
        }

        category = case.metadata.get(
            "category"
        )

        if category is not None:
            serialized["category"] = (
                category
            )

        return serialized

    @staticmethod
    def _sanitize_input(
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}

        for key, value in (
            input_data.items()
        ):
            if isinstance(
                value,
                str,
            ):
                sanitized[key] = (
                    OptimizationContextBuilder
                    ._truncate(
                        value,
                        700,
                    )
                )

            else:
                sanitized[key] = value

        return sanitized

    @staticmethod
    def _truncate(
        value: str,
        limit: int,
    ) -> str:
        if len(value) <= limit:
            return value

        return (
            value[:limit]
            + "..."
        )

    @staticmethod
    def _ratio(
        correct: int,
        total: int,
    ) -> float | None:
        if total == 0:
            return None

        return (
            correct
            / total
        )