from __future__ import annotations

from evals.models.comparison import (
    CaseChange,
    PromptComparison,
)
from evals.models.report import EvalReport
from evals.models.result import (
    EvalResult,
    EvalStatus,
)


class PromptComparator:
    """
    Compare les résultats obtenus par deux versions d'un même prompt.
    """

    def compare(
        self,
        *,
        baseline_name: str,
        baseline_results: list[EvalResult],
        baseline_report: EvalReport,
        candidate_name: str,
        candidate_results: list[EvalResult],
        candidate_report: EvalReport,
    ) -> PromptComparison:
        baseline_by_id = {
            result.case_id: result
            for result in baseline_results
        }

        candidate_by_id = {
            result.case_id: result
            for result in candidate_results
        }

        if baseline_by_id.keys() != candidate_by_id.keys():
            raise ValueError(
                "Les deux prompts doivent être évalués "
                "sur exactement les mêmes cas."
            )

        improvements: list[CaseChange] = []
        regressions: list[CaseChange] = []

        score_improvements: list[CaseChange] = []
        score_regressions: list[CaseChange] = []

        for case_id in baseline_by_id:
            baseline = baseline_by_id[
                case_id
            ]

            candidate = candidate_by_id[
                case_id
            ]

            change = CaseChange(
                case_id=case_id,
                baseline_status=baseline.status.value,
                candidate_status=candidate.status.value,
                baseline_score=baseline.decision_score,
                candidate_score=candidate.decision_score,
                score_delta=(
                    candidate.decision_score
                    - baseline.decision_score
                ),
            )

            baseline_correct = (
                baseline.status
                == EvalStatus.CORRECT
            )

            candidate_correct = (
                candidate.status
                == EvalStatus.CORRECT
            )

            if (
                not baseline_correct
                and candidate_correct
            ):
                improvements.append(
                    change
                )

            elif (
                baseline_correct
                and not candidate_correct
            ):
                regressions.append(
                    change
                )

            if (
                change.score_delta > 0
                and baseline_correct
                == candidate_correct
            ):
                score_improvements.append(
                    change
                )

            elif (
                change.score_delta < 0
                and baseline_correct
                == candidate_correct
            ):
                score_regressions.append(
                    change
                )

        return PromptComparison(
            baseline_name=baseline_name,
            candidate_name=candidate_name,
            baseline_accuracy=(
                baseline_report.accuracy
            ),
            candidate_accuracy=(
                candidate_report.accuracy
            ),
            baseline_score=(
                baseline_report.average_decision_score
            ),
            candidate_score=(
                candidate_report.average_decision_score
            ),
            accuracy_delta=(
                candidate_report.accuracy
                - baseline_report.accuracy
            ),
            score_delta=(
                candidate_report.average_decision_score
                - baseline_report.average_decision_score
            ),
            baseline_critical_errors=(
                baseline_report.critical_errors
            ),
            candidate_critical_errors=(
                candidate_report.critical_errors
            ),
            improvements=improvements,
            regressions=regressions,
            score_improvements=score_improvements,
            score_regressions=score_regressions,
        )
