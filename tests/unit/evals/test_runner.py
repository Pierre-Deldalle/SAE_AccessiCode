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
    actual: bool | None,
    expected: bool | None,
    confidence: str = "high",
) -> EvalCase:
    return EvalCase(
        id=case_id,
        input_data={
            "actual": actual,
            "confidence": confidence,
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
            "confidence": case.input_data["confidence"],
            "explanation": "Explication correcte.",
        }


class CrashingTask(EvalTask):
    name = "crashing"

    async def execute(
        self,
        case: EvalCase,
    ) -> dict[str, Any]:
        raise RuntimeError(
            "Erreur volontaire"
        )


class MixedTask(EvalTask):
    name = "mixed"

    async def execute(
        self,
        case: EvalCase,
    ) -> dict[str, Any]:
        if case.id == "crash":
            raise RuntimeError(
                "Erreur volontaire"
            )

        return {
            "relevant": True,
            "confidence": "high",
            "explanation": "Réponse correcte.",
        }


class InvalidConfidenceTask(EvalTask):
    name = "invalid_confidence"

    async def execute(
        self,
        case: EvalCase,
    ) -> dict[str, Any]:
        return {
            "relevant": True,
            "confidence": "certain",
            "explanation": "Réponse.",
        }


class CancelledTask(EvalTask):
    name = "cancelled"

    async def execute(
        self,
        case: EvalCase,
    ) -> dict[str, Any]:
        raise asyncio.CancelledError


def test_runner_marks_correct_answer_as_correct():
    runner = EvalRunner()

    case = create_case(
        "correct",
        actual=True,
        expected=True,
        confidence="high",
    )

    result = asyncio.run(
        runner.run_one(
            task=RelevantTask(),
            case=case,
        )
    )

    assert result.status == EvalStatus.CORRECT

    assert result.decision_score == 100.0

    assert result.expected_decision is True
    assert result.actual_decision is True

    assert result.confidence == "high"

    assert result.error_type is None
    assert result.error_message is None


def test_runner_marks_wrong_answer_as_incorrect():
    runner = EvalRunner()

    case = create_case(
        "incorrect",
        actual=False,
        expected=True,
        confidence="high",
    )

    result = asyncio.run(
        runner.run_one(
            task=RelevantTask(),
            case=case,
        )
    )

    assert result.status == EvalStatus.INCORRECT

    assert result.decision_score == 0.0

    assert "wrong_verdict" in result.decision_issues

    assert (
        "critical_confidence_error"
        in result.decision_issues
    )


def test_runner_uses_confidence_in_score():
    runner = EvalRunner()

    case = create_case(
        "low-confidence",
        actual=True,
        expected=True,
        confidence="low",
    )

    result = asyncio.run(
        runner.run_one(
            task=RelevantTask(),
            case=case,
        )
    )

    assert result.status == EvalStatus.CORRECT

    assert result.decision_score == 75.0

    assert (
        "unnecessary_low_confidence"
        in result.decision_issues
    )


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

    assert result.decision_score == 0.0

    assert result.actual is None

    assert result.error_type == "RuntimeError"

    assert (
        result.error_message
        == "Erreur volontaire"
    )


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

    assert (
        results[0].status
        == EvalStatus.ERROR
    )

    assert (
        results[1].status
        == EvalStatus.CORRECT
    )

    assert (
        results[1].decision_score
        == 100.0
    )


def test_runner_converts_invalid_confidence_to_error():
    runner = EvalRunner()

    case = create_case(
        "invalid-confidence",
        actual=True,
        expected=True,
    )

    result = asyncio.run(
        runner.run_one(
            task=InvalidConfidenceTask(),
            case=case,
        )
    )

    assert result.status == EvalStatus.ERROR

    assert result.error_type == "ValueError"


def test_runner_preserves_cancelled_error():
    runner = EvalRunner()

    case = create_case(
        "cancelled",
        actual=True,
        expected=True,
    )

    with pytest.raises(
        asyncio.CancelledError
    ):
        asyncio.run(
            runner.run_one(
                task=CancelledTask(),
                case=case,
            )
        )