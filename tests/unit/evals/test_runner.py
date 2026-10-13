import asyncio
from typing import Any

import pytest

from evals.models.case import EvalCase
from evals.models.result import EvalStatus
from evals.runners.runner import EvalRunner
from evals.tasks.base import EvalTask


def create_case(
    case_id: str,
    *,
    actual: bool,
    expected: bool,
) -> EvalCase:
    return EvalCase(
        id=case_id,
        input_data={
            "actual": actual,
        },
        expected={
            "relevant": expected,
        },
    )


class RelevantTask(EvalTask):
    name = "relevant"

    async def execute(
        self,
        case: EvalCase,
    ) -> dict[str, Any]:
        return {
            "relevant": case.input_data["actual"],
        }

    def score(
        self,
        case: EvalCase,
        actual: dict[str, Any],
    ) -> float:
        if actual["relevant"] == case.expected["relevant"]:
            return 1.0

        return 0.0


class CrashingTask(EvalTask):
    name = "crashing"

    async def execute(
        self,
        case: EvalCase,
    ) -> dict[str, Any]:
        raise RuntimeError("Erreur volontaire")

    def score(
        self,
        case: EvalCase,
        actual: dict[str, Any],
    ) -> float:
        return 1.0


class MixedTask(EvalTask):
    name = "mixed"

    async def execute(
        self,
        case: EvalCase,
    ) -> dict[str, Any]:
        if case.id == "crash":
            raise RuntimeError("Erreur volontaire")

        return {
            "relevant": True,
        }

    def score(
        self,
        case: EvalCase,
        actual: dict[str, Any],
    ) -> float:
        if actual["relevant"] == case.expected["relevant"]:
            return 1.0

        return 0.0


class InvalidScoreTask(EvalTask):
    name = "invalid_score"

    async def execute(
        self,
        case: EvalCase,
    ) -> dict[str, Any]:
        return {
            "relevant": True,
        }

    def score(
        self,
        case: EvalCase,
        actual: dict[str, Any],
    ) -> float:
        return 1.5


class CancelledTask(EvalTask):
    name = "cancelled"

    async def execute(
        self,
        case: EvalCase,
    ) -> dict[str, Any]:
        raise asyncio.CancelledError

    def score(
        self,
        case: EvalCase,
        actual: dict[str, Any],
    ) -> float:
        return 1.0


def test_runner_marks_correct_answer_as_correct():
    runner = EvalRunner()

    case = create_case(
        "correct",
        actual=True,
        expected=True,
    )

    result = asyncio.run(
        runner.run_one(
            task=RelevantTask(),
            case=case,
        )
    )

    assert result.status == EvalStatus.CORRECT
    assert result.score == 1.0

    assert result.expected == {
        "relevant": True,
    }

    assert result.actual == {
        "relevant": True,
    }

    assert result.error_type is None
    assert result.error_message is None


def test_runner_marks_wrong_answer_as_incorrect():
    runner = EvalRunner()

    case = create_case(
        "incorrect",
        actual=False,
        expected=True,
    )

    result = asyncio.run(
        runner.run_one(
            task=RelevantTask(),
            case=case,
        )
    )

    assert result.status == EvalStatus.INCORRECT
    assert result.score == 0.0

    assert result.expected == {
        "relevant": True,
    }

    assert result.actual == {
        "relevant": False,
    }


def test_runner_converts_exception_to_error():
    runner = EvalRunner()

    case = create_case(
        "crash",
        actual=True,
        expected=True,
    )

    result = asyncio.run(
        runner.run_one(
            task=CrashingTask(),
            case=case,
        )
    )

    assert result.status == EvalStatus.ERROR
    assert result.score == 0.0
    assert result.actual is None

    assert result.error_type == "RuntimeError"
    assert result.error_message == "Erreur volontaire"


def test_runner_continues_after_case_error():
    runner = EvalRunner()

    cases = [
        create_case(
            "crash",
            actual=True,
            expected=True,
        ),
        create_case(
            "passing",
            actual=True,
            expected=True,
        ),
    ]

    results = asyncio.run(
        runner.run(
            task=MixedTask(),
            cases=cases,
        )
    )

    assert len(results) == 2

    assert results[0].case_id == "crash"
    assert results[0].status == EvalStatus.ERROR
    assert results[0].error_type == "RuntimeError"

    assert results[1].case_id == "passing"
    assert results[1].status == EvalStatus.CORRECT
    assert results[1].score == 1.0


def test_runner_converts_invalid_score_to_error():
    runner = EvalRunner()

    case = create_case(
        "invalid-score",
        actual=True,
        expected=True,
    )

    result = asyncio.run(
        runner.run_one(
            task=InvalidScoreTask(),
            case=case,
        )
    )

    assert result.status == EvalStatus.ERROR
    assert result.score == 0.0
    assert result.error_type == "ValueError"


def test_runner_preserves_cancelled_error():
    runner = EvalRunner()

    case = create_case(
        "cancelled",
        actual=True,
        expected=True,
    )

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            runner.run_one(
                task=CancelledTask(),
                case=case,
            )
        )
