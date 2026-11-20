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
    llm = FakeModel(batch(ONLY_COLOR, WITH_TEXT))
    analyzer = OllamaSensoryAnalyzer(llm)

    results = await analyzer.analyze_texts(
        "color",
        [SensoryCandidate("Les champs en rouge sont obligatoires"), SensoryCandidate("Voir la colonne Tarifs")],
    )

    assert results[0].relies_only_on_sensory is True
    assert results[0].characteristics == ["couleur"]
    assert results[1].alternative_relevant is True
    assert "RGAA 3.1" in llm.prompts[0]


@pytest.mark.asyncio
async def test_shape_size_position_uses_rule_10_9() -> None:
    llm = FakeModel(batch(WITH_TEXT))
    analyzer = OllamaSensoryAnalyzer(llm)

    await analyzer.analyze_texts("shape_size_position", [SensoryCandidate("Cliquez sur le bouton rond")])

    assert "RGAA 10.9" in llm.prompts[0]


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
async def test_analyze_image_without_image_analyzer_raises() -> None:
    analyzer = OllamaSensoryAnalyzer(FakeModel())
    image = ImageInfo(src="a.png", alt=None, element_html="<img>")

    with pytest.raises(RuntimeError):
        await analyzer.analyze_image("color", image)
