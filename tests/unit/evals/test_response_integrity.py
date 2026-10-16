from evals.graders.response_integrity import (
    ResponseIntegrityGrader,
)


def test_clean_response_has_perfect_integrity():
    result = ResponseIntegrityGrader().grade(
        {
            "explanation": (
                "Le titre correspond clairement "
                "au contenu de la page."
            ),
            "uncertainties": [],
            "contradictions": [],
        }
    )

    assert result.score == 100.0
    assert result.issues == ()


def test_fallback_explanation_is_detected():
    result = ResponseIntegrityGrader().grade(
        {
            "explanation": (
                "La pertinence du titre "
                "n'a pas pu être déterminée."
            ),
            "uncertainties": [],
            "contradictions": [],
        }
    )

    assert (
        "fallback_explanation"
        in result.issues
    )


def test_meta_generation_is_detected():
    result = ResponseIntegrityGrader().grade(
        {
            "explanation": (
                "The user's prompt is in French "
                "and I should answer..."
            ),
        }
    )

    assert (
        "meta_generation_marker"
        in result.issues
    )


def test_repetition_is_detected():
    result = ResponseIntegrityGrader().grade(
        {
            "explanation": "Explication.",
            "uncertainties": [
                (
                    "Mismatch Mismatch Mismatch "
                    "Mismatch Mismatch"
                )
            ],
        }
    )

    assert (
        "excessive_repetition"
        in result.issues
    )


def test_truncated_explanation_is_detected():
    result = ResponseIntegrityGrader().grade(
        {
            "explanation": (
                "Le titre semble trop générique ("
            ),
        }
    )

    assert (
        "truncated_explanation"
        in result.issues
    )
