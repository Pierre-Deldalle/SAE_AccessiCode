import json

import pytest

from evals.optimization.generator import (
    PromptCandidateGenerator,
)
from evals.optimization.generator import (
    normalize_prompt_template,
)


class FakeLLM:
    def __init__(
        self,
        response: str,
    ):
        self.response = response

        self.calls: list[
            dict
        ] = []

    async def generate(
        self,
        prompt: str,
        *,
        format: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        self.calls.append(
            {
                "prompt": prompt,
                "format": format,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )

        return self.response


@pytest.mark.asyncio
async def test_generator_creates_candidates():
    response = json.dumps(
        {
            "candidates": [
                {
                    "prompt": (
                        "Prompt candidat 1 "
                        "{title} {heading} {content}"
                    ),
                },
                {
                    "prompt": (
                        "Prompt candidat 2 "
                        "{title} {heading} {content}"
                    ),
                },
            ]
        }
    )

    llm = FakeLLM(
        response
    )

    generator = PromptCandidateGenerator(
        llm=llm
    )

    candidates = await generator.generate(
        optimization_context={
            "task": "title",
            "problematic_cases": [
                {
                    "id": "title_001",
                }
            ],
        },
        candidate_count=2,
    )

    assert len(candidates) == 2

    assert (
        candidates[0].name
        == "candidate_001"
    )

    assert (
        candidates[1].name
        == "candidate_002"
    )

    assert (
        candidates[0].rationale
        == ""
    )

    assert len(
        llm.calls
    ) == 1

    call = llm.calls[0]

    assert call["format"] == "json"

    assert call["temperature"] == 0

    assert (
        "title_001"
        in call["prompt"]
    )


@pytest.mark.asyncio
async def test_generator_removes_duplicate_prompts():
    response = json.dumps(
        {
            "candidates": [
                {
                    "rationale": "A",
                    "prompt": "Même prompt",
                },
                {
                    "rationale": "B",
                    "prompt": "Même prompt",
                },
                {
                    "rationale": "C",
                    "prompt": "Autre prompt",
                },
            ]
        }
    )

    generator = PromptCandidateGenerator(
        llm=FakeLLM(
            response
        )
    )

    candidates = await generator.generate(
        optimization_context={},
        candidate_count=3,
    )

    assert len(candidates) == 2

    assert [
        candidate.template
        for candidate in candidates
    ] == [
        "Même prompt",
        "Autre prompt",
    ]


@pytest.mark.asyncio
async def test_generator_respects_candidate_count():
    response = json.dumps(
        {
            "candidates": [
                {
                    "rationale": "A",
                    "prompt": "Prompt A",
                },
                {
                    "rationale": "B",
                    "prompt": "Prompt B",
                },
                {
                    "rationale": "C",
                    "prompt": "Prompt C",
                },
            ]
        }
    )

    generator = PromptCandidateGenerator(
        llm=FakeLLM(
            response
        )
    )

    candidates = await generator.generate(
        optimization_context={},
        candidate_count=2,
    )

    assert len(candidates) == 2


@pytest.mark.asyncio
async def test_generator_rejects_invalid_candidate_count():
    generator = PromptCandidateGenerator(
        llm=FakeLLM(
            "{}"
        )
    )

    with pytest.raises(
        ValueError,
        match="supérieur ou égal à 1",
    ):
        await generator.generate(
            optimization_context={},
            candidate_count=0,
        )


@pytest.mark.asyncio
async def test_generator_rejects_missing_candidates_array():
    generator = PromptCandidateGenerator(
        llm=FakeLLM(
            json.dumps(
                {
                    "result": "incorrect"
                }
            )
        )
    )

    with pytest.raises(
        ValueError,
        match="liste 'candidates'",
    ):
        await generator.generate(
            optimization_context={},
            candidate_count=2,
        )


@pytest.mark.asyncio
async def test_generator_rejects_empty_candidates():
    generator = PromptCandidateGenerator(
        llm=FakeLLM(
            json.dumps(
                {
                    "candidates": []
                }
            )
        )
    )

    with pytest.raises(
        ValueError,
        match="aucun prompt candidat",
    ):
        await generator.generate(
            optimization_context={},
            candidate_count=2,
        )
        
def test_normalize_prompt_template_escapes_literal_json_braces():
    prompt = """
Réponds avec :
{
  "relevant": true
}

Titre :
{title}
""".strip()

    normalized = normalize_prompt_template(
        prompt
    )

    assert '{title}' in normalized
    assert '{{\n  "relevant": true\n}}' in normalized


def test_normalize_prompt_template_preserves_already_escaped_braces():
    prompt = """
Réponds avec :
{{
  "relevant": true
}}

Titre :
{title}
""".strip()

    normalized = normalize_prompt_template(
        prompt
    )

    assert normalized == prompt


def test_normalize_prompt_template_fixes_overescaped_placeholders():
    prompt = """
Titre :
{{title}}

Heading :
{{heading}}

Contenu :
{{content}}
""".strip()

    normalized = normalize_prompt_template(
        prompt
    )

    assert "{title}" in normalized
    assert "{heading}" in normalized
    assert "{content}" in normalized

    assert "{{title}}" not in normalized
    assert "{{heading}}" not in normalized
    assert "{{content}}" not in normalized


def test_normalized_prompt_can_be_formatted():
    prompt = """
Réponds :
{
  "relevant": true
}

Titre :
{title}

Heading :
{heading}

Contenu :
{content}
""".strip()

    normalized = normalize_prompt_template(
        prompt
    )

    formatted = normalized.format(
        title="Contact",
        heading="Nous contacter",
        content="Téléphone et e-mail.",
    )

    assert '"relevant": true' in formatted
    assert "Contact" in formatted
    assert "Nous contacter" in formatted
    assert "Téléphone et e-mail." in formatted