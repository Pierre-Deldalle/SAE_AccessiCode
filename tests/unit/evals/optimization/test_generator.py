import json

import pytest

from evals.optimization.generator import (
    PromptCandidateGenerator,
    PromptGenerationError,
)
from evals.optimization.generator import (
    normalize_prompt_template,
)


class FakeLLM:
    def __init__(
        self,
        responses: str | list[str],
    ):
        if isinstance(responses, str):
            self.responses = [
                responses
            ]
        else:
            self.responses = list(
                responses
            )

        self.calls = 0
        self.prompts: list[str] = []
        self.kwargs: list[dict] = []

    async def generate(
        self,
        prompt: str,
        **kwargs,
    ) -> str:
        if (
            self.calls
            >= len(self.responses)
        ):
            raise AssertionError(
                "FakeLLM : aucun résultat "
                "prévu pour cet appel."
            )

        self.prompts.append(
            prompt
        )

        self.kwargs.append(
            kwargs
        )

        response = self.responses[
            self.calls
        ]

        self.calls += 1

        return response

@pytest.mark.asyncio
async def test_generator_creates_candidates():
    llm = FakeLLM(
        [
            json.dumps(
                {
                    "prompt": (
                        "Prompt candidat 1 "
                        "{title} {heading} {content}"
                    )
                }
            ),
            json.dumps(
                {
                    "prompt": (
                        "Prompt candidat 2 "
                        "{title} {heading} {content}"
                    )
                }
            ),
        ]
    )

    generator = PromptCandidateGenerator(
        llm=llm
    )

    candidates = await generator.generate(
        optimization_context={
            "task": "title",
            "problematic_cases": [],
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
        candidates[0].template
        == (
            "Prompt candidat 1 "
            "{title} {heading} {content}"
        )
    )

    assert (
        candidates[1].template
        == (
            "Prompt candidat 2 "
            "{title} {heading} {content}"
        )
    )

    assert (
        candidates[0].rationale
        == ""
    )

    assert (
        candidates[1].rationale
        == ""
    )

    assert llm.calls == 2


@pytest.mark.asyncio
async def test_generator_removes_duplicate_prompts():
    llm = FakeLLM(
        [
            json.dumps(
                {
                    "prompt": "Même prompt"
                }
            ),
            json.dumps(
                {
                    "prompt": "Même prompt"
                }
            ),
            json.dumps(
                {
                    "prompt": "Autre prompt"
                }
            ),
        ]
    )

    generator = PromptCandidateGenerator(
        llm=llm
    )

    candidates = await generator.generate(
        optimization_context={},
        candidate_count=2,
    )

    assert len(candidates) == 2

    assert (
        candidates[0].template
        == "Même prompt"
    )

    assert (
        candidates[1].template
        == "Autre prompt"
    )

    #
    # 1 appel pour candidate_001
    # +
    # 2 appels pour candidate_002,
    # car sa première tentative est un doublon.
    #
    assert llm.calls == 3


@pytest.mark.asyncio
async def test_generator_respects_candidate_count():
    llm = FakeLLM(
        [
            json.dumps(
                {
                    "prompt": "Prompt A"
                }
            ),
            json.dumps(
                {
                    "prompt": "Prompt B"
                }
            ),
            json.dumps(
                {
                    "prompt": "Prompt C"
                }
            ),
        ]
    )

    generator = PromptCandidateGenerator(
        llm=llm
    )

    candidates = await generator.generate(
        optimization_context={},
        candidate_count=2,
    )

    assert len(candidates) == 2

    assert (
        candidates[0].template
        == "Prompt A"
    )

    assert (
        candidates[1].template
        == "Prompt B"
    )

    #
    # Le troisième résultat FakeLLM
    # ne doit jamais être consommé.
    #
    assert llm.calls == 2


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
async def test_generator_rejects_missing_prompt_field():
    generator = PromptCandidateGenerator(
        llm=FakeLLM(
            [
                json.dumps(
                    {
                        "result": "incorrect"
                    }
                ),
                json.dumps(
                    {
                        "result": "toujours incorrect"
                    }
                ),
            ]
        )
    )

    with pytest.raises(
        PromptGenerationError,
        match=(
            "aucun champ 'prompt'"
        ),
    ):
        await generator.generate(
            optimization_context={},
            candidate_count=1,
        )


@pytest.mark.asyncio
async def test_generator_rejects_empty_prompt():
    generator = PromptCandidateGenerator(
        llm=FakeLLM(
            [
                json.dumps(
                    {
                        "prompt": ""
                    }
                ),
                json.dumps(
                    {
                        "prompt": "   "
                    }
                ),
            ]
        )
    )

    with pytest.raises(
        PromptGenerationError,
        match="prompt est vide",
    ):
        await generator.generate(
            optimization_context={},
            candidate_count=1,
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

@pytest.mark.asyncio
async def test_generator_rejects_duplicate_after_retry():
    generator = PromptCandidateGenerator(
        llm=FakeLLM(
            [
                json.dumps(
                    {
                        "prompt": "Même prompt"
                    }
                ),
                json.dumps(
                    {
                        "prompt": "Même prompt"
                    }
                ),
                json.dumps(
                    {
                        "prompt": "Même prompt"
                    }
                ),
            ]
        )
    )

    with pytest.raises(
        PromptGenerationError,
        match=(
            "Échec sur candidate_002"
        ),
    ) as error_info:
        await generator.generate(
            optimization_context={},
            candidate_count=2,
        )

    assert (
        "prompt dupliqué"
        in str(
            error_info.value
        )
    )

@pytest.mark.asyncio
async def test_generator_generates_one_candidate_per_call():
    llm = FakeLLM(
        [
            json.dumps(
                {
                    "prompt": (
                        "Prompt A "
                        "{title} "
                        "{heading} "
                        "{content}"
                    )
                }
            ),
            json.dumps(
                {
                    "prompt": (
                        "Prompt B "
                        "{title} "
                        "{heading} "
                        "{content}"
                    )
                }
            ),
            json.dumps(
                {
                    "prompt": (
                        "Prompt C "
                        "{title} "
                        "{heading} "
                        "{content}"
                    )
                }
            ),
        ]
    )

    generator = PromptCandidateGenerator(
        llm=llm
    )

    candidates = (
        await generator.generate(
            optimization_context={},
            candidate_count=3,
        )
    )

    assert len(candidates) == 3

    assert llm.calls == 3

    assert (
        candidates[0].name
        == "candidate_001"
    )

    assert (
        candidates[1].name
        == "candidate_002"
    )

    assert (
        candidates[2].name
        == "candidate_003"
    )