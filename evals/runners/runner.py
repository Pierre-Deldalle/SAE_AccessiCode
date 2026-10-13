from __future__ import annotations

import asyncio

from evals.models.case import EvalCase
from evals.models.result import EvalResult, EvalStatus
from evals.tasks.base import EvalTask


class EvalRunner:
    """
    Exécute un ensemble de cas sur une même fonctionnalité IA.
    """

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
        try:
            actual = await task.execute(case)

            score = task.score(
                case,
                actual,
            )

            if not 0.0 <= score <= 1.0:
                raise ValueError(f"La tâche {task.name!r} a retourné un score invalide : {score}.")

            status = EvalStatus.CORRECT if score == 1.0 else EvalStatus.INCORRECT

            return EvalResult(
                task_name=task.name,
                case_id=case.id,
                status=status,
                expected=case.expected,
                actual=actual,
                score=score,
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
                score=0.0,
                error_type=type(error).__name__,
                error_message=str(error),
            )
