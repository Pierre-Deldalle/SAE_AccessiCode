from unittest.mock import AsyncMock

import pytest
from fakes import FakeModel, batch

from accessi_code.ai.analyzers.sensory_analyzer import OllamaSensoryAnalyzer
from accessi_code.ai.schemas import SensoryCandidate, VisualObservation
from accessi_code.analysis.images import ImageInfo

ONLY_COLOR = {
    "conveys_information": True,
    "relies_only_on_sensory": True,
    "alternative_relevant": None,
    "characteristics": ["couleur"],
    "explanation": "Les champs obligatoires sont signalés uniquement en rouge.",
    "confidence": "high",
}

WITH_TEXT = {
    "conveys_information": True,
    "relies_only_on_sensory": False,
    "alternative_relevant": True,
    "characteristics": ["position"],
    "explanation": "La colonne est aussi nommée.",
    "confidence": "medium",
}


@pytest.mark.asyncio
async def test_analyze_texts_reads_each_result() -> None:
    llm = FakeModel(batch(ONLY_COLOR | {"suggestion": "Préciser quels champs sont obligatoires."}, WITH_TEXT))
    analyzer = OllamaSensoryAnalyzer(llm)

    results = await analyzer.analyze_texts(
        "color",
        [SensoryCandidate("Les champs en rouge sont obligatoires"), SensoryCandidate("Voir la colonne Tarifs")],
    )

    assert results[0].relies_only_on_sensory is True
    assert results[0].characteristics == ["couleur"]
    assert results[0].suggestion is None
    assert results[1].alternative_relevant is True
    assert "RGAA 3.1" in llm.prompts[0]
    assert '"suggestion"' not in llm.prompts[0]


@pytest.mark.asyncio
async def test_shape_size_position_uses_rule_10_9() -> None:
    llm = FakeModel(batch(WITH_TEXT))
    analyzer = OllamaSensoryAnalyzer(llm)

    await analyzer.analyze_texts("shape_size_position", [SensoryCandidate("Cliquez sur le bouton rond")])

    assert "RGAA 10.9" in llm.prompts[0]
    assert '"suggestion"' in llm.prompts[0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({}, "Sélectionnez Payer pour valider."),
        ({"relies_only_on_sensory": True, "alternative_relevant": None}, "Sélectionnez Payer pour valider."),
        ({"suggestion": None}, None),
        ({"suggestion": ["Payer"]}, None),
        ({"suggestion": "  "}, None),
        ({"alternative_relevant": True}, None),
        ({"confidence": "low"}, None),
        ({"conveys_information": False}, None),
        ({"relies_only_on_sensory": None}, None),
    ],
)
async def test_shape_suggestion_depends_on_findings_and_confidence(overrides, expected) -> None:
    reply = WITH_TEXT | {"alternative_relevant": False, "suggestion": " Sélectionnez Payer pour valider. "} | overrides
    llm = FakeModel(batch(reply))
    analyzer = OllamaSensoryAnalyzer(llm)

    [result] = await analyzer.analyze_texts("shape_size_position", [SensoryCandidate("Sélectionnez le bouton rond.")])

    assert result.suggestion == expected
    assert result.conveys_information is reply["conveys_information"]
    assert result.relies_only_on_sensory is reply["relies_only_on_sensory"]
    assert result.alternative_relevant is reply["alternative_relevant"]
    assert result.confidence == reply["confidence"]


@pytest.mark.asyncio
async def test_shape_without_suggestion_keeps_analysis() -> None:
    llm = FakeModel(batch(WITH_TEXT | {"alternative_relevant": False}))
    analyzer = OllamaSensoryAnalyzer(llm)
    [result] = await analyzer.analyze_texts("shape_size_position", [SensoryCandidate("Voir la colonne à gauche.")])
    assert result.alternative_relevant is False
    assert result.suggestion is None


@pytest.mark.asyncio
async def test_unknown_kind_raises() -> None:
    with pytest.raises(ValueError):
        await OllamaSensoryAnalyzer(FakeModel()).analyze_texts("son", [SensoryCandidate("x")])


@pytest.mark.asyncio
async def test_analyze_image_reuses_image_analyzer_observation() -> None:
    image_analyzer = AsyncMock()
    image_analyzer.observe.return_value = VisualObservation(summary="Légende de graphique en couleurs")
    llm = FakeModel(ONLY_COLOR)
    analyzer = OllamaSensoryAnalyzer(llm, image_analyzer)
    image = ImageInfo(src="graph.png", alt="Graphique", element_html='<img src="graph.png">', image_data=b"x")

    first = await analyzer.analyze_image("color", image)
    second = await analyzer.analyze_image("color", image)

    assert first.relies_only_on_sensory is True
    assert second == first
    image_analyzer.observe.assert_awaited_once()
    assert llm.call_count == 1
    assert "Légende de graphique en couleurs" in llm.prompts[0]


@pytest.mark.asyncio
async def test_shape_image_parses_suggestion() -> None:
    image_analyzer = AsyncMock()
    image_analyzer.observe.return_value = VisualObservation(summary="Le guichet se trouve à l’entrée nord.")
    suggestion = "Guichet des inscriptions à l’entrée nord."
    llm = FakeModel(WITH_TEXT | {"alternative_relevant": False, "suggestion": suggestion})
    analyzer = OllamaSensoryAnalyzer(llm, image_analyzer)
    image = ImageInfo(src="plan.png", alt="Plan", element_html='<img src="plan.png" alt="Plan">')

    result = await analyzer.analyze_image("shape_size_position", image)

    assert result.suggestion == suggestion
    assert '"suggestion"' in llm.prompts[0]


@pytest.mark.asyncio
async def test_analyze_image_without_image_analyzer_raises() -> None:
    analyzer = OllamaSensoryAnalyzer(FakeModel())
    image = ImageInfo(src="a.png", alt=None, element_html="<img>")

    with pytest.raises(RuntimeError):
        await analyzer.analyze_image("color", image)
