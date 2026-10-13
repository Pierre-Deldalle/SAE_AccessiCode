import asyncio

import pytest

from accessi_code.ai.schemas import TitleAnalysis
from evals.models.case import EvalCase
from evals.tasks.title import TitleEvalTask


class FakePageAnalyzer:
    def __init__(
        self,
        analysis: TitleAnalysis,
    ):
        self.analysis = analysis
        self.received: dict[str, str] | None = None

    async def analyze_title(
        self,
        title: str,
        heading: str,
        content: str,
    ) -> TitleAnalysis:
        self.received = {
            "title": title,
            "heading": heading,
            "content": content,
        }

        return self.analysis


def create_title_case(
    *,
    expected_relevant: bool | None,
) -> EvalCase:
    return EvalCase(
        id="title_001",
        input_data={
            "title": "Contact",
            "heading": "Contactez-nous",
            "content": "Retrouvez toutes nos coordonnées.",
        },
        expected={
            "relevant": expected_relevant,
        },
    )


def test_title_task_calls_page_analyzer_with_case_data():
    analyzer = FakePageAnalyzer(
        TitleAnalysis(
            relevant=True,
            explanation="Le titre correspond au contenu.",
            contradictions=[],
            uncertainties=[],
            confidence="high",
        )
    )

    task = TitleEvalTask(
        page_analyzer=analyzer,
    )

    case = create_title_case(
        expected_relevant=True,
    )

    actual = asyncio.run(task.execute(case))

    assert analyzer.received == {
        "title": "Contact",
        "heading": "Contactez-nous",
        "content": "Retrouvez toutes nos coordonnées.",
    }

    assert actual == {
        "relevant": True,
        "explanation": "Le titre correspond au contenu.",
        "contradictions": [],
        "uncertainties": [],
        "confidence": "high",
    }


@pytest.mark.parametrize(
    (
        "expected_relevant",
        "actual_relevant",
        "expected_score",
    ),
    [
        (
            True,
            True,
            1.0,
        ),
        (
            False,
            False,
            1.0,
        ),
        (
            None,
            None,
            1.0,
        ),
        (
            True,
            False,
            0.0,
        ),
        (
            False,
            True,
            0.0,
        ),
        (
            True,
            None,
            0.0,
        ),
    ],
)
def test_title_task_scores_relevant_field(
    expected_relevant,
    actual_relevant,
    expected_score,
):
    analyzer = FakePageAnalyzer(
        TitleAnalysis(
            relevant=actual_relevant,
            explanation="Explication.",
            confidence="high",
        )
    )

    task = TitleEvalTask(
        page_analyzer=analyzer,
    )

    case = create_title_case(
        expected_relevant=expected_relevant,
    )

    actual = asyncio.run(task.execute(case))

    score = task.score(
        case,
        actual,
    )

    assert score == expected_score


def test_title_task_rejects_missing_expected_relevant():
    analyzer = FakePageAnalyzer(
        TitleAnalysis(
            relevant=True,
            explanation="Explication.",
            confidence="high",
        )
    )

    task = TitleEvalTask(
        page_analyzer=analyzer,
    )

    case = EvalCase(
        id="title_001",
        input_data={
            "title": "Contact",
            "heading": "Contactez-nous",
            "content": "Retrouvez toutes nos coordonnées.",
        },
        expected={},
    )

    with pytest.raises(
        ValueError,
        match="ne possède pas de valeur attendue",
    ):
        task.score(
            case,
            {
                "relevant": True,
            },
        )


def test_title_task_rejects_invalid_expected_relevant():
    analyzer = FakePageAnalyzer(
        TitleAnalysis(
            relevant=True,
            explanation="Explication.",
            confidence="high",
        )
    )

    task = TitleEvalTask(
        page_analyzer=analyzer,
    )

    case = EvalCase(
        id="title_001",
        input_data={
            "title": "Contact",
            "heading": "Contactez-nous",
            "content": "Retrouvez toutes nos coordonnées.",
        },
        expected={
            "relevant": "yes",
        },
    )

    with pytest.raises(
        ValueError,
        match="true, false ou null",
    ):
        task.score(
            case,
            {
                "relevant": True,
            },
        )


@pytest.mark.parametrize(
    "missing_field",
    [
        "title",
        "heading",
        "content",
    ],
)
def test_title_task_rejects_missing_input_field(
    missing_field,
):
    analyzer = FakePageAnalyzer(
        TitleAnalysis(
            relevant=True,
            explanation="Explication.",
            confidence="high",
        )
    )

    task = TitleEvalTask(
        page_analyzer=analyzer,
    )

    input_data = {
        "title": "Contact",
        "heading": "Contactez-nous",
        "content": "Retrouvez toutes nos coordonnées.",
    }

    del input_data[missing_field]

    case = EvalCase(
        id="title_001",
        input_data=input_data,
        expected={
            "relevant": True,
        },
    )

    with pytest.raises(
        ValueError,
        match="ne possède pas le champ d'entrée",
    ):
        asyncio.run(task.execute(case))


@pytest.mark.parametrize(
    "invalid_field",
    [
        "title",
        "heading",
        "content",
    ],
)
def test_title_task_rejects_non_string_input(
    invalid_field,
):
    analyzer = FakePageAnalyzer(
        TitleAnalysis(
            relevant=True,
            explanation="Explication.",
            confidence="high",
        )
    )

    task = TitleEvalTask(
        page_analyzer=analyzer,
    )

    input_data = {
        "title": "Contact",
        "heading": "Contactez-nous",
        "content": "Retrouvez toutes nos coordonnées.",
    }

    input_data[invalid_field] = 123

    case = EvalCase(
        id="title_001",
        input_data=input_data,
        expected={
            "relevant": True,
        },
    )

    with pytest.raises(
        ValueError,
        match="doit être une chaîne",
    ):
        asyncio.run(task.execute(case))
