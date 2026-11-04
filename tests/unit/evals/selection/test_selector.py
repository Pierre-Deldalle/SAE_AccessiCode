from pathlib import Path
from types import SimpleNamespace

from evals.selection.selector import PromptSelector


def make_evaluation(
    name: str,
    *,
    validation_accuracy: float = 0.80,
    validation_accuracy_delta: float = 0.0,
    validation_score: float = 70.0,
    validation_score_delta: float = 0.0,
    validation_critical_errors: int = 1,
    validation_errors: int = 0,
    validation_improvements: int = 0,
    validation_regressions: int = 0,
    train_accuracy: float = 0.80,
    train_accuracy_delta: float = 0.0,
    train_score: float = 70.0,
    train_score_delta: float = 0.0,
    train_regressions: int = 0,
):
    return SimpleNamespace(
        candidate=SimpleNamespace(
            name=name,
        ),
        prompt_path=Path(
            f"{name}.txt"
        ),
        validation_report=SimpleNamespace(
            accuracy=validation_accuracy,
            average_decision_score=(
                validation_score
            ),
            critical_errors=(
                validation_critical_errors
            ),
            errors=validation_errors,
        ),
        validation_comparison=SimpleNamespace(
            accuracy_delta=(
                validation_accuracy_delta
            ),
            score_delta=(
                validation_score_delta
            ),
            improvements=[
                object()
                for _ in range(
                    validation_improvements
                )
            ],
            regressions=[
                object()
                for _ in range(
                    validation_regressions
                )
            ],
        ),
        train_report=SimpleNamespace(
            accuracy=train_accuracy,
            average_decision_score=(
                train_score
            ),
        ),
        train_comparison=SimpleNamespace(
            accuracy_delta=(
                train_accuracy_delta
            ),
            score_delta=(
                train_score_delta
            ),
            regressions=[
                object()
                for _ in range(
                    train_regressions
                )
            ],
        ),
    )


def make_result(
    *candidates,
    baseline_critical_errors: int = 1,
):
    return SimpleNamespace(
        baseline_validation_report=(
            SimpleNamespace(
                critical_errors=(
                    baseline_critical_errors
                )
            )
        ),
        candidates=list(
            candidates
        ),
    )


def test_selector_recommends_improved_candidate():
    candidate = make_evaluation(
        "candidate_001",
        validation_accuracy=0.84,
        validation_accuracy_delta=0.04,
        validation_score=78.4,
        validation_score_delta=7.0,
        validation_critical_errors=1,
        validation_improvements=1,
    )

    result = make_result(
        candidate,
        baseline_critical_errors=1,
    )

    selection = PromptSelector().select(
        result
    )

    assert (
        selection.keep_production
        is False
    )

    assert (
        selection.recommended_candidate
        is not None
    )

    assert (
        selection.recommended_candidate.name
        == "candidate_001"
    )

    assert (
        selection.ranking[0].eligible
        is True
    )


def test_selector_rejects_candidate_with_more_critical_errors():
    candidate = make_evaluation(
        "candidate_001",
        validation_accuracy=0.90,
        validation_accuracy_delta=0.10,
        validation_score=90.0,
        validation_score_delta=20.0,
        validation_critical_errors=2,
    )

    result = make_result(
        candidate,
        baseline_critical_errors=1,
    )

    selection = PromptSelector().select(
        result
    )

    assert (
        selection.keep_production
        is True
    )

    assert (
        selection.recommended_candidate
        is None
    )

    ranked = selection.ranking[0]

    assert ranked.eligible is False

    assert any(
        "critical errors"
        in reason
        for reason in ranked.reasons
    )


def test_selector_keeps_production_when_no_candidate_is_eligible():
    candidate_001 = make_evaluation(
        "candidate_001",
        validation_accuracy_delta=0.0,
        validation_score_delta=0.0,
        validation_critical_errors=1,
    )

    candidate_002 = make_evaluation(
        "candidate_002",
        validation_accuracy_delta=0.05,
        validation_score_delta=5.0,
        validation_critical_errors=2,
    )

    result = make_result(
        candidate_001,
        candidate_002,
        baseline_critical_errors=1,
    )

    selection = PromptSelector().select(
        result
    )

    assert (
        selection.keep_production
        is True
    )

    assert (
        selection.recommended_candidate
        is None
    )

    assert all(
        not candidate.eligible
        for candidate in selection.ranking
    )


def test_selector_prioritizes_fewer_critical_errors():
    safer_candidate = make_evaluation(
        "candidate_safe",
        validation_accuracy=0.82,
        validation_accuracy_delta=0.02,
        validation_score=74.0,
        validation_score_delta=3.0,
        validation_critical_errors=0,
    )

    higher_accuracy_candidate = (
        make_evaluation(
            "candidate_accuracy",
            validation_accuracy=0.90,
            validation_accuracy_delta=0.10,
            validation_score=90.0,
            validation_score_delta=19.0,
            validation_critical_errors=1,
        )
    )

    result = make_result(
        higher_accuracy_candidate,
        safer_candidate,
        baseline_critical_errors=1,
    )

    selection = PromptSelector().select(
        result
    )

    assert (
        selection.ranking[0].name
        == "candidate_safe"
    )

    assert (
        selection.recommended_candidate
        is not None
    )

    assert (
        selection.recommended_candidate.name
        == "candidate_safe"
    )


def test_selector_prioritizes_fewer_validation_regressions():
    no_regression = make_evaluation(
        "candidate_no_regression",
        validation_accuracy_delta=0.02,
        validation_score_delta=3.0,
        validation_critical_errors=1,
        validation_regressions=0,
    )

    more_accuracy_but_regressions = (
        make_evaluation(
            "candidate_with_regressions",
            validation_accuracy_delta=0.08,
            validation_score_delta=10.0,
            validation_critical_errors=1,
            validation_regressions=2,
        )
    )

    result = make_result(
        more_accuracy_but_regressions,
        no_regression,
        baseline_critical_errors=1,
    )

    selection = PromptSelector().select(
        result
    )

    assert (
        selection.ranking[0].name
        == "candidate_no_regression"
    )


def test_selector_uses_validation_before_train_performance():
    better_validation = make_evaluation(
        "candidate_validation",
        validation_accuracy_delta=0.06,
        validation_score_delta=5.0,
        validation_critical_errors=1,
        validation_regressions=0,
        train_score_delta=-5.0,
        train_regressions=3,
    )

    better_train = make_evaluation(
        "candidate_train",
        validation_accuracy_delta=0.02,
        validation_score_delta=3.0,
        validation_critical_errors=1,
        validation_regressions=0,
        train_score_delta=15.0,
        train_regressions=0,
    )

    result = make_result(
        better_train,
        better_validation,
        baseline_critical_errors=1,
    )

    selection = PromptSelector().select(
        result
    )

    assert (
        selection.ranking[0].name
        == "candidate_validation"
    )


def test_selector_rejects_candidate_with_evaluation_errors():
    candidate = make_evaluation(
        "candidate_001",
        validation_accuracy_delta=0.10,
        validation_score_delta=10.0,
        validation_critical_errors=0,
        validation_errors=1,
    )

    result = make_result(
        candidate,
        baseline_critical_errors=1,
    )

    selection = PromptSelector().select(
        result
    )

    assert (
        selection.keep_production
        is True
    )

    assert (
        selection.ranking[0].eligible
        is False
    )

    assert any(
        "erreurs techniques"
        in reason
        for reason in (
            selection.ranking[0].reasons
        )
    )


def test_selector_rejects_candidate_without_improvement():
    candidate = make_evaluation(
        "candidate_001",
        validation_accuracy_delta=0.0,
        validation_score_delta=0.0,
        validation_critical_errors=1,
    )

    result = make_result(
        candidate,
        baseline_critical_errors=1,
    )

    selection = PromptSelector().select(
        result
    )

    assert (
        selection.keep_production
        is True
    )

    assert (
        selection.ranking[0].eligible
        is False
    )

    assert any(
        "aucune amélioration"
        in reason
        for reason in (
            selection.ranking[0].reasons
        )
    )


def test_selector_handles_empty_candidate_list():
    result = make_result(
        baseline_critical_errors=1,
    )

    selection = PromptSelector().select(
        result
    )

    assert (
        selection.keep_production
        is True
    )

    assert (
        selection.recommended_candidate
        is None
    )

    assert selection.ranking == ()