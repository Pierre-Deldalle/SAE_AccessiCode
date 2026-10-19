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
        *,
        prompt_template: str | None = None,
    ) -> TitleAnalysis:
        self.received = {
            "title": title,
            "heading": heading,
            "content": content,
            "prompt_template": prompt_template,
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
            "content": ("Retrouvez toutes nos coordonnées."),
        },
        expected={
            "relevant": expected_relevant,
        },
    )


def test_title_task_calls_page_analyzer_with_case_data():
    analyzer = FakePageAnalyzer(
        TitleAnalysis(
            relevant=True,
            explanation=("Le titre correspond au contenu."),
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
        "prompt_template": None,
    }

    assert actual["relevant"] is True
    assert actual["confidence"] == "high"


@pytest.mark.parametrize(
    "expected",
    [
        True,
        False,
        None,
    ],
)
def test_title_task_reads_expected_decision(
    expected,
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

    case = create_title_case(
        expected_relevant=expected,
    )

    assert task.get_expected_decision(case) is expected


def test_title_task_reads_actual_decision():
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

    assert (
        task.get_actual_decision(
            {
                "relevant": False,
            }
        )
        is False
    )


def test_title_task_reads_confidence():
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

    assert (
        task.get_confidence(
            {
                "confidence": "medium",
            }
        )
        == "medium"
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
        "content": "Coordonnées.",
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


def test_title_task_forwards_prompt_template():
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

    case = create_title_case(
        expected_relevant=True,
    )

    prompt = """
Titre :
{title}

Titre principal :
{heading}

Contenu :
{content}
""".strip()

    asyncio.run(
        task.execute(
            case,
            prompt_template=prompt,
        )
    )

    assert analyzer.received is not None

    assert (
        analyzer.received["prompt_template"]
        == prompt
    )


def test_title_task_rejects_empty_prompt_template():
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

    with pytest.raises(
        ValueError,
        match="ne peut pas être vide",
    ):
        task.validate_prompt_template(
            "   "
        )


def test_title_task_accepts_valid_prompt_template():
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

    prompt = """
Analyse :

Titre :
{title}

Heading :
{heading}

Contenu :
{content}

Retourne :

{{
  "relevant": true
}}
""".strip()

    task.validate_prompt_template(
        prompt
    )


def test_title_task_rejects_invalid_json_braces_in_prompt():
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

    prompt = """
Titre :
{title}

{
  "relevant": true
}
""".strip()

    with pytest.raises(
        ValueError,
        match="prompt title est invalide",
    ):
        task.validate_prompt_template(
            prompt
        )


def test_title_task_rejects_unknown_prompt_variable():
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

    prompt = """
Titre : {title}
Heading : {heading}
Contenu : {content}
Utilisateur : {username}
""".strip()

    with pytest.raises(
        ValueError,
        match="prompt title est invalide",
    ):
        task.validate_prompt_template(
            prompt
        )