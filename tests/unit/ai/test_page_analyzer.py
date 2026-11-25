import pytest

from accessi_code.ai.analyzers.page_analyzer import OllamaPageAnalyzer
from tests.unit.ai.fakes import FakeModel


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "args"),
    [
        ("analyze_language", ("fr", "Welcome to our services.")),
        ("analyze_title", ("Accueil", "Nos horaires", "Le magasin est ouvert le lundi.")),
    ],
)
@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"suggestion": " Proposition de correction. "}, "Proposition de correction."),
        ({"suggestion": ["Texte"]}, None),
        ({}, None),
        ({"suggestion": "Texte", "relevant": True}, None),
        ({"suggestion": "Texte", "confidence": "low"}, None),
    ],
)
async def test_page_suggestion_is_optional(method, args, payload, expected):
    reply = {"relevant": False, "explanation": "Le texte indiqué est inexact.", "confidence": "high"} | payload
    llm = FakeModel(reply)
    analyzer = OllamaPageAnalyzer(llm)

    result = await getattr(analyzer, method)(*args)

    assert result.suggestion == expected
    assert result.relevant is reply["relevant"]
    assert result.confidence == reply["confidence"]
    assert '"suggestion"' in llm.prompts[0]
