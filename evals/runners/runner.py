from __future__ import annotations

import asyncio

from evals.graders.decision import (
    DecisionGrader,
)
from evals.graders.response_integrity import (
    ResponseIntegrityGrader,
)
from evals.models.case import EvalCase
from evals.models.result import (
    EvalResult,
    EvalStatus,
)
from evals.tasks.base import EvalTask


class EvalRunner:
    """
    Exécute un ensemble de cas sur une même fonctionnalité IA.
    """

    def __init__(
        self,
        *,
        decision_grader: DecisionGrader | None = None,
        integrity_grader: ResponseIntegrityGrader | None = None,
    ):
        self.decision_grader = decision_grader or DecisionGrader()

        self.integrity_grader = integrity_grader or ResponseIntegrityGrader()

    async def run(
        self,
        task: EvalTask,
        cases: list[EvalCase],
    ) -> list[EvalResult]:
        results: list[EvalResult] = []

        for case in cases:
            result = await self.run_one(
                task=task,
                case=case,
            )

            results.append(result)

        return results

    async def run_one(
        self,
        task: EvalTask,
        case: EvalCase,
    ) -> EvalResult:
        expected_decision: bool | None = None

        try:
            expected_decision = task.get_expected_decision(
                case,
            )

            actual = await task.execute(
                case,
            )

            actual_decision = task.get_actual_decision(
                actual,
            )

            confidence = task.get_confidence(
                actual,
            )

            decision_grade = self.decision_grader.grade(
                expected=expected_decision,
                actual=actual_decision,
                confidence=confidence,
            )

            integrity_grade = self.integrity_grader.grade(
                actual,
            )

            status = EvalStatus.CORRECT if decision_grade.correct else EvalStatus.INCORRECT

            return EvalResult(
                task_name=task.name,
                case_id=case.id,
                status=status,
                expected=case.expected,
                actual=actual,
                expected_decision=expected_decision,
                actual_decision=actual_decision,
                confidence=confidence,
                decision_score=decision_grade.score,
                decision_issues=decision_grade.issues,
                integrity_score=integrity_grade.score,
                integrity_issues=integrity_grade.issues,
            )

        except asyncio.CancelledError:
            raise

        except Exception as error:
            return EvalResult(
                task_name=task.name,
                case_id=case.id,
                status=EvalStatus.ERROR,
                expected=case.expected,
                actual=None,
                expected_decision=expected_decision,
                actual_decision=None,
                confidence=None,
                decision_score=0.0,
                decision_issues=("evaluation_error",),
                integrity_score=None,
                integrity_issues=(),
                error_type=type(error).__name__,
                error_message=str(error),
            )
