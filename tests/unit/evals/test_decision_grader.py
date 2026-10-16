import pytest

from evals.graders.decision import DecisionGrader


@pytest.mark.parametrize(
    (
        "expected",
        "actual",
        "confidence",
        "score",
    ),
    [
        (True, True, "high", 100.0),
        (True, True, "medium", 90.0),
        (True, True, "low", 75.0),

        (True, None, "low", 60.0),
        (True, None, "medium", 50.0),
        (True, None, "high", 40.0),

        (None, True, "low", 30.0),
        (None, True, "medium", 15.0),
        (None, True, "high", 0.0),

        (True, False, "low", 20.0),
        (True, False, "medium", 10.0),
        (True, False, "high", 0.0),
    ],
)
def test_decision_score_matrix(
    expected,
    actual,
    confidence,
    score,
):
    grader = DecisionGrader()

    result = grader.grade(
        expected=expected,
        actual=actual,
        confidence=confidence,
    )

    assert result.score == score


def test_low_confidence_correct_answer_is_flagged():
    result = DecisionGrader().grade(
        expected=True,
        actual=True,
        confidence="low",
    )

    assert result.correct is True

    assert (
        "unnecessary_low_confidence"
        in result.issues
    )


def test_high_confidence_wrong_answer_is_critical():
    result = DecisionGrader().grade(
        expected=False,
        actual=True,
        confidence="high",
    )

    assert result.correct is False

    assert (
        "critical_confidence_error"
        in result.issues
    )


def test_forced_verdict_is_detected():
    result = DecisionGrader().grade(
        expected=None,
        actual=True,
        confidence="medium",
    )

    assert (
        "forced_verdict"
        in result.issues
    )


def test_unnecessary_abstention_is_detected():
    result = DecisionGrader().grade(
        expected=True,
        actual=None,
        confidence="low",
    )

    assert (
        "unnecessary_abstention"
        in result.issues
    )
