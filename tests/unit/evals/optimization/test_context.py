from evals.models.case import EvalCase
from evals.models.report import EvalReport
from evals.models.result import (
    EvalResult,
    EvalStatus,
)
from evals.optimization.context import (
    OptimizationContextBuilder,
)


def create_case(
    case_id: str,
    *,
    expected: bool | None,
    category: str,
) -> EvalCase:
    return EvalCase(
        id=case_id,
        input_data={
            "title": f"Titre {case_id}",
            "heading": f"Heading {case_id}",
            "content": f"Contenu {case_id}",
        },
        expected={
            "relevant": expected,
        },
        metadata={
            "category": category,
        },
    )


def create_result(
    case_id: str,
    *,
    status: EvalStatus,
    expected: bool | None,
    actual: bool | None,
    confidence: str,
    score: float,
    decision_issues: tuple[str, ...] = (),
    integrity_issues: tuple[str, ...] = (),
    explanation: str = "Explication.",
) -> EvalResult:
    return EvalResult(
        task_name="title",
        case_id=case_id,
        status=status,
        expected={
            "relevant": expected,
        },
        actual={
            "relevant": actual,
            "confidence": confidence,
            "explanation": explanation,
            "contradictions": [],
            "uncertainties": [],
        },
        expected_decision=expected,
        actual_decision=actual,
        confidence=confidence,
        decision_score=score,
        decision_issues=decision_issues,
        integrity_score=(
            100.0
            if not integrity_issues
            else 70.0
        ),
        integrity_issues=integrity_issues,
    )


def test_context_contains_problematic_cases_and_protected_examples():
    cases = [
        create_case(
            "bad_case",
            expected=False,
            category="wrong_verdict",
        ),
        create_case(
            "low_confidence_case",
            expected=True,
            category="low_confidence",
        ),
        create_case(
            "anchor_case",
            expected=True,
            category="easy",
        ),
    ]

    results = [
        create_result(
            "bad_case",
            status=EvalStatus.INCORRECT,
            expected=False,
            actual=True,
            confidence="low",
            score=20.0,
            decision_issues=(
                "wrong_verdict",
            ),
        ),
        create_result(
            "low_confidence_case",
            status=EvalStatus.CORRECT,
            expected=True,
            actual=True,
            confidence="low",
            score=75.0,
            decision_issues=(
                "unnecessary_low_confidence",
            ),
        ),
        create_result(
            "anchor_case",
            status=EvalStatus.CORRECT,
            expected=True,
            actual=True,
            confidence="high",
            score=100.0,
        ),
    ]

    report = EvalReport.from_results(
        task_name="title",
        dataset_name="train",
        results=results,
    )

    context = OptimizationContextBuilder().build(
        task_name="title",
        production_prompt="PROMPT DE PRODUCTION",
        cases=cases,
        results=results,
        report=report,
    )

    assert context["task"] == "title"

    assert (
        context["production_prompt"]
        == "PROMPT DE PRODUCTION"
    )

    problematic_ids = {
        case["id"]
        for case in context[
            "problematic_cases"
        ]
    }

    assert problematic_ids == {
        "bad_case",
        "low_confidence_case",
    }

    protected_ids = {
        case["id"]
        for case in context[
            "protected_examples"
        ]
    }

    assert protected_ids == {
        "anchor_case",
    }


def test_context_prioritizes_critical_errors():
    cases = [
        create_case(
            "normal_error",
            expected=False,
            category="normal",
        ),
        create_case(
            "critical_error",
            expected=None,
            category="critical",
        ),
    ]

    results = [
        create_result(
            "normal_error",
            status=EvalStatus.INCORRECT,
            expected=False,
            actual=True,
            confidence="low",
            score=20.0,
            decision_issues=(
                "wrong_verdict",
            ),
        ),
        create_result(
            "critical_error",
            status=EvalStatus.INCORRECT,
            expected=None,
            actual=True,
            confidence="high",
            score=0.0,
            decision_issues=(
                "forced_verdict",
                "critical_confidence_error",
            ),
        ),
    ]

    report = EvalReport.from_results(
        task_name="title",
        dataset_name="train",
        results=results,
    )

    context = OptimizationContextBuilder().build(
        task_name="title",
        production_prompt="PROMPT",
        cases=cases,
        results=results,
        report=report,
    )

    assert (
        context["problematic_cases"][0]["id"]
        == "critical_error"
    )


def test_context_does_not_include_model_explanation():
    case = create_case(
        "bad_case",
        expected=False,
        category="wrong",
    )

    result = create_result(
        "bad_case",
        status=EvalStatus.INCORRECT,
        expected=False,
        actual=True,
        confidence="low",
        score=20.0,
        decision_issues=(
            "wrong_verdict",
        ),
        explanation=(
            "Mismatch-" * 500
        ),
    )

    report = EvalReport.from_results(
        task_name="title",
        dataset_name="train",
        results=[result],
    )

    context = (
        OptimizationContextBuilder()
        .build(
            task_name="title",
            production_prompt="PROMPT",
            cases=[case],
            results=[result],
            report=report,
        )
    )

    problematic = (
        context[
            "problematic_cases"
        ][0]
    )

    assert (
        "explanation"
        not in problematic
    )

    assert (
        "Mismatch"
        not in str(problematic)
    )


def test_context_contains_baseline_metrics():
    case = create_case(
        "case",
        expected=True,
        category="test",
    )

    result = create_result(
        "case",
        status=EvalStatus.CORRECT,
        expected=True,
        actual=True,
        confidence="high",
        score=100.0,
    )

    report = EvalReport.from_results(
        task_name="title",
        dataset_name="train",
        results=[result],
    )

    context = OptimizationContextBuilder().build(
        task_name="title",
        production_prompt="PROMPT",
        cases=[case],
        results=[result],
        report=report,
    )

    metrics = context[
        "baseline_metrics"
    ]

    assert metrics["accuracy"] == 1.0

    assert (
        metrics["average_decision_score"]
        == 100.0
    )

    assert metrics["true_accuracy"] == 1.0