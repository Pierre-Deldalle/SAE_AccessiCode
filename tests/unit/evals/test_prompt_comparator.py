import pytest

from evals.comparison.comparator import (
    PromptComparator,
)
from evals.models.report import EvalReport
from evals.models.result import (
    EvalResult,
    EvalStatus,
)


def create_result(
    case_id: str,
    *,
    status: EvalStatus,
    score: float,
    expected: bool | None = True,
    actual: bool | None = True,
    confidence: str | None = "high",
    issues: tuple[str, ...] = (),
) -> EvalResult:
    return EvalResult(
        task_name="title",
        case_id=case_id,
        status=status,
        expected={
            "relevant": expected,
        },
        actual=(
            {
                "relevant": actual,
                "confidence": confidence,
            }
            if status != EvalStatus.ERROR
            else None
        ),
        expected_decision=expected,
        actual_decision=(
            actual
            if status != EvalStatus.ERROR
            else None
        ),
        confidence=(
            confidence
            if status != EvalStatus.ERROR
            else None
        ),
        decision_score=score,
        decision_issues=issues,
        integrity_score=100.0,
        integrity_issues=(),
    )


def create_report(
    results: list[EvalResult],
) -> EvalReport:
    return EvalReport.from_results(
        task_name="title",
        dataset_name="train",
        results=results,
    )


def test_comparator_detects_incorrect_to_correct_improvement():
    baseline_results = [
        create_result(
            "title_001",
            status=EvalStatus.INCORRECT,
            score=20.0,
            expected=False,
            actual=True,
            confidence="low",
            issues=("wrong_verdict",),
        ),
    ]

    candidate_results = [
        create_result(
            "title_001",
            status=EvalStatus.CORRECT,
            score=100.0,
            expected=False,
            actual=False,
            confidence="high",
        ),
    ]

    comparison = PromptComparator().compare(
        baseline_name="production",
        baseline_results=baseline_results,
        baseline_report=create_report(
            baseline_results
        ),
        candidate_name="candidate_001",
        candidate_results=candidate_results,
        candidate_report=create_report(
            candidate_results
        ),
    )

    assert len(
        comparison.improvements
    ) == 1

    assert (
        comparison.improvements[0].case_id
        == "title_001"
    )

    assert comparison.regressions == []

    assert (
        comparison.improvements[0].score_delta
        == 80.0
    )


def test_comparator_detects_correct_to_incorrect_regression():
    baseline_results = [
        create_result(
            "title_001",
            status=EvalStatus.CORRECT,
            score=100.0,
        ),
    ]

    candidate_results = [
        create_result(
            "title_001",
            status=EvalStatus.INCORRECT,
            score=20.0,
            expected=True,
            actual=False,
            confidence="low",
            issues=("wrong_verdict",),
        ),
    ]

    comparison = PromptComparator().compare(
        baseline_name="production",
        baseline_results=baseline_results,
        baseline_report=create_report(
            baseline_results
        ),
        candidate_name="candidate_001",
        candidate_results=candidate_results,
        candidate_report=create_report(
            candidate_results
        ),
    )

    assert len(
        comparison.regressions
    ) == 1

    regression = comparison.regressions[
        0
    ]

    assert regression.case_id == "title_001"

    assert (
        regression.baseline_status
        == "correct"
    )

    assert (
        regression.candidate_status
        == "incorrect"
    )

    assert regression.score_delta == -80.0


def test_comparator_detects_score_improvement_without_status_change():
    baseline_results = [
        create_result(
            "title_001",
            status=EvalStatus.CORRECT,
            score=75.0,
            confidence="low",
            issues=(
                "unnecessary_low_confidence",
            ),
        ),
    ]

    candidate_results = [
        create_result(
            "title_001",
            status=EvalStatus.CORRECT,
            score=100.0,
            confidence="high",
        ),
    ]

    comparison = PromptComparator().compare(
        baseline_name="production",
        baseline_results=baseline_results,
        baseline_report=create_report(
            baseline_results
        ),
        candidate_name="candidate_001",
        candidate_results=candidate_results,
        candidate_report=create_report(
            candidate_results
        ),
    )

    assert comparison.improvements == []
    assert comparison.regressions == []

    assert len(
        comparison.score_improvements
    ) == 1

    improvement = (
        comparison.score_improvements[0]
    )

    assert improvement.case_id == "title_001"
    assert improvement.baseline_score == 75.0
    assert improvement.candidate_score == 100.0
    assert improvement.score_delta == 25.0


def test_comparator_detects_score_regression_without_status_change():
    baseline_results = [
        create_result(
            "title_001",
            status=EvalStatus.CORRECT,
            score=100.0,
            confidence="high",
        ),
    ]

    candidate_results = [
        create_result(
            "title_001",
            status=EvalStatus.CORRECT,
            score=75.0,
            confidence="low",
            issues=(
                "unnecessary_low_confidence",
            ),
        ),
    ]

    comparison = PromptComparator().compare(
        baseline_name="production",
        baseline_results=baseline_results,
        baseline_report=create_report(
            baseline_results
        ),
        candidate_name="candidate_001",
        candidate_results=candidate_results,
        candidate_report=create_report(
            candidate_results
        ),
    )

    assert comparison.improvements == []
    assert comparison.regressions == []

    assert len(
        comparison.score_regressions
    ) == 1

    regression = (
        comparison.score_regressions[0]
    )

    assert regression.score_delta == -25.0


def test_comparator_calculates_global_deltas():
    baseline_results = [
        create_result(
            "title_001",
            status=EvalStatus.CORRECT,
            score=75.0,
            confidence="low",
        ),
        create_result(
            "title_002",
            status=EvalStatus.INCORRECT,
            score=20.0,
            expected=False,
            actual=True,
            confidence="low",
        ),
    ]

    candidate_results = [
        create_result(
            "title_001",
            status=EvalStatus.CORRECT,
            score=100.0,
            confidence="high",
        ),
        create_result(
            "title_002",
            status=EvalStatus.CORRECT,
            score=100.0,
            expected=False,
            actual=False,
            confidence="high",
        ),
    ]

    baseline_report = create_report(
        baseline_results
    )

    candidate_report = create_report(
        candidate_results
    )

    comparison = PromptComparator().compare(
        baseline_name="production",
        baseline_results=baseline_results,
        baseline_report=baseline_report,
        candidate_name="candidate_001",
        candidate_results=candidate_results,
        candidate_report=candidate_report,
    )

    assert comparison.baseline_accuracy == 0.5
    assert comparison.candidate_accuracy == 1.0

    assert comparison.accuracy_delta == 0.5

    assert comparison.baseline_score == 47.5
    assert comparison.candidate_score == 100.0

    assert comparison.score_delta == 52.5


def test_comparator_compares_critical_errors():
    baseline_results = [
        create_result(
            "title_001",
            status=EvalStatus.INCORRECT,
            score=0.0,
            expected=False,
            actual=True,
            confidence="high",
            issues=(
                "wrong_verdict",
                "critical_confidence_error",
            ),
        ),
    ]

    candidate_results = [
        create_result(
            "title_001",
            status=EvalStatus.CORRECT,
            score=100.0,
            expected=False,
            actual=False,
            confidence="high",
        ),
    ]

    comparison = PromptComparator().compare(
        baseline_name="production",
        baseline_results=baseline_results,
        baseline_report=create_report(
            baseline_results
        ),
        candidate_name="candidate_001",
        candidate_results=candidate_results,
        candidate_report=create_report(
            candidate_results
        ),
    )

    assert (
        comparison.baseline_critical_errors
        == 1
    )

    assert (
        comparison.candidate_critical_errors
        == 0
    )


def test_comparator_rejects_different_case_sets():
    baseline_results = [
        create_result(
            "title_001",
            status=EvalStatus.CORRECT,
            score=100.0,
        ),
    ]

    candidate_results = [
        create_result(
            "title_002",
            status=EvalStatus.CORRECT,
            score=100.0,
        ),
    ]

    with pytest.raises(
        ValueError,
        match="exactement les mêmes cas",
    ):
        PromptComparator().compare(
            baseline_name="production",
            baseline_results=baseline_results,
            baseline_report=create_report(
                baseline_results
            ),
            candidate_name="candidate_001",
            candidate_results=candidate_results,
            candidate_report=create_report(
                candidate_results
            ),
        )


def test_comparator_can_report_improvements_and_regressions_together():
    baseline_results = [
        create_result(
            "fixed_case",
            status=EvalStatus.INCORRECT,
            score=20.0,
            expected=False,
            actual=True,
            confidence="low",
        ),
        create_result(
            "broken_case",
            status=EvalStatus.CORRECT,
            score=100.0,
        ),
        create_result(
            "better_confidence",
            status=EvalStatus.CORRECT,
            score=75.0,
            confidence="low",
        ),
    ]

    candidate_results = [
        create_result(
            "fixed_case",
            status=EvalStatus.CORRECT,
            score=100.0,
            expected=False,
            actual=False,
            confidence="high",
        ),
        create_result(
            "broken_case",
            status=EvalStatus.INCORRECT,
            score=20.0,
            expected=True,
            actual=False,
            confidence="low",
        ),
        create_result(
            "better_confidence",
            status=EvalStatus.CORRECT,
            score=100.0,
            confidence="high",
        ),
    ]

    comparison = PromptComparator().compare(
        baseline_name="production",
        baseline_results=baseline_results,
        baseline_report=create_report(
            baseline_results
        ),
        candidate_name="candidate_001",
        candidate_results=candidate_results,
        candidate_report=create_report(
            candidate_results
        ),
    )

    assert [
        item.case_id
        for item in comparison.improvements
    ] == [
        "fixed_case",
    ]

    assert [
        item.case_id
        for item in comparison.regressions
    ] == [
        "broken_case",
    ]

    assert [
        item.case_id
        for item in comparison.score_improvements
    ] == [
        "better_confidence",
    ]
